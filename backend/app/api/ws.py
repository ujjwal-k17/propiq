"""
WebSocket alerts endpoint
=========================
GET /ws/alerts?token=<jwt>

Authentication
--------------
JWT is passed as a query parameter because WebSocket upgrade requests
cannot carry arbitrary HTTP headers in most browser implementations.

Connection lifecycle
--------------------
1. Client connects with ?token=<jwt>
2. Server validates token, loads user + watchlist
3. Adds connection to ConnectionManager
4. Sends {"type": "connected", "data": {...}} + recent alert history
5. Enters read loop: handles ping / subscribe / mark_read / request_history
6. Server sends {"type": "alert", "data": {...}} when pub/sub receives a
   matching alert for any project in the user's watchlist
7. On disconnect: removes connection from ConnectionManager

Heartbeat
---------
The server sends {"type": "pong"} in response to {"type": "ping"} from the
client.  If the client does not send any message within 60 seconds the server
sends an unsolicited {"type": "ping"} and waits 30 s before closing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.database import AsyncSessionLocal
from app.models.alert import ProjectAlert
from app.models.complaint import Complaint
from app.models.project import Project
from app.models.risk_score import RiskScore
from app.models.user import User
from app.schemas.alert import AlertMessage, WSInbound, WSOutbound
from app.services.alert_manager import (
    alert_manager,
    connection_manager,
)

logger = logging.getLogger("propiq.ws")

router = APIRouter(prefix="/ws", tags=["WebSocket"])

_HEARTBEAT_INTERVAL = 30   # seconds between server pings when idle
_HEARTBEAT_TIMEOUT  = 30   # seconds to wait for pong before closing


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _authenticate(token: str) -> User | None:
    """Decode JWT and load the User from DB.  Returns None on any failure."""
    payload = verify_token(token)
    if not payload:
        return None
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()


def _out(type_: str, data=None, *, code: str | None = None, message: str | None = None) -> dict:
    """Build a server → client JSON payload."""
    msg: dict = {"type": type_}
    if data is not None:
        msg["data"] = data
    if code is not None:
        msg["code"] = code
    if message is not None:
        msg["message"] = message
    return msg


async def _get_complaint_count(project_id: uuid.UUID, db: AsyncSession) -> int:
    row = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.project_id == project_id)
    )
    return row.scalar_one() or 0


async def _get_risk_band(project_id: uuid.UUID, db: AsyncSession) -> str | None:
    row = await db.execute(
        select(RiskScore.risk_band)
        .where(RiskScore.project_id == project_id, RiskScore.is_current.is_(True))
    )
    band = row.scalar_one_or_none()
    return band.value if band else None


# ─── Message handler ──────────────────────────────────────────────────────────

async def _handle_message(
    raw: str,
    ws: WebSocket,
    user: User,
    redis,
) -> None:
    """Process a single client → server message."""
    try:
        data = json.loads(raw)
        msg = WSInbound(**data)
    except Exception:
        await ws.send_json(_out("error", code="parse_error", message="Invalid JSON"))
        return

    match msg.type:
        case "ping":
            await ws.send_json(_out("pong"))

        case "subscribe":
            # Update which projects this user is watching in the connection manager
            new_ids: list[str] = msg.project_ids or []
            await connection_manager.update_watchlist(str(user.id), new_ids)
            await ws.send_json(_out("subscribed", data={"project_ids": new_ids}))

        case "mark_read":
            ids = msg.alert_ids or []
            await alert_manager.mark_read(str(user.id), ids, redis)
            await ws.send_json(_out("marked_read", data={"alert_ids": ids}))

        case "request_history":
            async with AsyncSessionLocal() as db:
                watchlist = [str(p) for p in (user.watchlist_project_ids or [])]
                history = await alert_manager.get_history(
                    watchlist=watchlist,
                    user_id=str(user.id),
                    redis=redis,
                    db=db,
                    limit=min(msg.limit, 50),
                )
            await ws.send_json(_out("history", data=[h.model_dump() for h in history]))

        case _:
            await ws.send_json(_out("error", code="unknown_type",
                                    message=f"Unknown message type: {msg.type}"))


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/alerts")
async def ws_alerts(
    websocket: WebSocket,
    token: str = Query(..., description="JWT bearer token"),
) -> None:
    """
    Real-time project alert stream for the authenticated user.

    Query params:
      token — JWT obtained from POST /api/v1/auth/login
    """
    # ── 1. Authenticate ───────────────────────────────────────────────────────
    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id    = str(user.id)
    watchlist  = [str(p) for p in (user.watchlist_project_ids or [])]
    redis      = getattr(websocket.app.state, "redis", None)

    # ── 2. Register connection ────────────────────────────────────────────────
    await connection_manager.connect(websocket, user_id, watchlist)

    try:
        # ── 3. Send connection confirmation + unread count ────────────────────
        async with AsyncSessionLocal() as db:
            unread = await alert_manager.unread_count(user_id, watchlist, redis, db)
            history = await alert_manager.get_history(
                watchlist=watchlist,
                user_id=user_id,
                redis=redis,
                db=db,
                limit=20,
            )

        await websocket.send_json(_out("connected", data={
            "user_id":       user_id,
            "watchlist":     watchlist,
            "unread_count":  unread,
            "connected_at":  datetime.now(timezone.utc).isoformat(),
        }))

        # ── 4. Send recent alert history ──────────────────────────────────────
        if history:
            await websocket.send_json(_out("history", data=[h.model_dump() for h in history]))

        # ── 5. Message receive loop ───────────────────────────────────────────
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_HEARTBEAT_INTERVAL,
                )
                await _handle_message(raw, websocket, user, redis)

            except asyncio.TimeoutError:
                # Client idle — send a ping and give it time to respond
                try:
                    await websocket.send_json(_out("ping"))
                    await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=_HEARTBEAT_TIMEOUT,
                    )
                except (asyncio.TimeoutError, WebSocketDisconnect):
                    logger.info("WS heartbeat timeout — closing user=%s", user_id[:8])
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WS error for user=%s: %s", user_id[:8], exc)
    finally:
        await connection_manager.disconnect(websocket, user_id)
