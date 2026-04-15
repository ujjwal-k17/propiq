"""
Alert Manager
=============
Three collaborating pieces:

1. ``ConnectionManager``
   In-memory registry of active WebSocket connections, keyed by user_id.
   Also maintains a reverse index of project_id → set[user_id] so broadcasts
   are O(1) per project.

2. ``AlertManager``
   Persists ``ProjectAlert`` rows, publishes to Redis pub/sub, and fans out
   live messages to connected clients via ``ConnectionManager``.

3. ``detect_project_changes``
   Pure function: compares a project snapshot taken before a pipeline run
   against the refreshed project and returns a list of
   ``(AlertType, AlertSeverity, title, message, payload)`` tuples.

Redis channel
-------------
All alert messages are published to ``propiq:alerts`` as JSON strings.
A dedicated subscriber task (started in app lifespan) listens on this
channel and calls ``ConnectionManager.broadcast_to_project_watchers``.

Read-state tracking
-------------------
Per-user read state is stored in Redis as a SET of alert-ID strings at key
``propiq:user:{user_id}:read_alerts``.  TTL = 30 days.  No DB rows needed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertSeverity, AlertType, ProjectAlert
from app.models.project import Project
from app.models.risk_score import RiskScore
from app.schemas.alert import AlertMessage

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("propiq.alerts")

REDIS_ALERTS_CHANNEL = "propiq:alerts"
_READ_STATE_TTL = 30 * 24 * 3600   # 30 days
_HISTORY_LIMIT  = 50


# ─── Snapshot helper ─────────────────────────────────────────────────────────

@dataclass
class ProjectSnapshot:
    """Lightweight pre-refresh snapshot of mutable project fields."""
    rera_status: str
    construction_pct: float | None
    possession_date_latest: date | None
    complaint_count: int
    risk_band: str | None
    financial_stress_score: float | None
    nclt_proceedings: bool


# ─── Change detection ─────────────────────────────────────────────────────────

def detect_project_changes(
    before: ProjectSnapshot,
    project: Project,
    complaint_count_after: int,
    risk_score_after: RiskScore | None,
) -> list[tuple[AlertType, AlertSeverity, str, str, dict]]:
    """
    Compare *before* (pre-refresh snapshot) with the refreshed project.
    Returns a list of ``(type, severity, title, message, payload)`` tuples.
    """
    alerts: list[tuple[AlertType, AlertSeverity, str, str, dict]] = []

    # ── RERA status change ────────────────────────────────────────────────────
    new_rera = project.rera_status.value
    if before.rera_status != new_rera:
        severity = (
            AlertSeverity.critical
            if new_rera in ("revoked", "lapsed")
            else AlertSeverity.info
        )
        alerts.append((
            AlertType.rera_status_change,
            severity,
            f"RERA status changed: {before.rera_status.upper()} → {new_rera.upper()}",
            (
                f"{project.name}'s RERA registration status changed from "
                f"{before.rera_status} to {new_rera}. "
                + (
                    "This is a critical regulatory flag — verify before transacting."
                    if new_rera in ("revoked", "lapsed")
                    else "Status is now active."
                )
            ),
            {"old_value": before.rera_status, "new_value": new_rera},
        ))

    # ── New complaints ────────────────────────────────────────────────────────
    new_complaints = complaint_count_after - before.complaint_count
    if new_complaints > 0:
        alerts.append((
            AlertType.new_complaint,
            AlertSeverity.warning,
            f"{new_complaints} new RERA complaint{'s' if new_complaints > 1 else ''} filed",
            (
                f"{project.name} now has {complaint_count_after} total complaints "
                f"({new_complaints} new since last scan). "
                "Review complaint details before making a decision."
            ),
            {"new_complaints": new_complaints, "total_complaints": complaint_count_after},
        ))

    # ── Possession date delay ─────────────────────────────────────────────────
    new_poss = project.possession_date_latest
    if (
        new_poss
        and before.possession_date_latest
        and new_poss > before.possession_date_latest
    ):
        old_str = before.possession_date_latest.strftime("%b %Y")
        new_str = new_poss.strftime("%b %Y")
        delay_months = max(
            0,
            int((new_poss - before.possession_date_latest).days / 30),
        )
        alerts.append((
            AlertType.possession_date_delay,
            AlertSeverity.warning if delay_months < 6 else AlertSeverity.critical,
            f"Possession date pushed by {delay_months} month{'s' if delay_months != 1 else ''}",
            (
                f"{project.name}'s possession date was revised from {old_str} to {new_str} "
                f"({delay_months} month delay). Verify the revised timeline with the developer."
            ),
            {
                "old_date": before.possession_date_latest.isoformat(),
                "new_date": new_poss.isoformat(),
                "delay_months": delay_months,
            },
        ))

    # ── Construction milestone ────────────────────────────────────────────────
    milestones = [25, 50, 75, 90, 100]
    old_pct = before.construction_pct or 0.0
    new_pct = project.construction_pct or 0.0
    for m in milestones:
        if old_pct < m <= new_pct:
            alerts.append((
                AlertType.construction_milestone,
                AlertSeverity.info,
                f"Construction milestone reached: {m}% complete",
                (
                    f"{project.name} has crossed the {m}% construction milestone "
                    f"(was {old_pct:.0f}%, now {new_pct:.0f}%). "
                    + ("Project is ready to move in." if m == 100 else "")
                ),
                {"milestone_pct": m, "old_pct": old_pct, "new_pct": new_pct},
            ))
            break  # emit at most one milestone per refresh

    # ── Risk band change ──────────────────────────────────────────────────────
    if risk_score_after and before.risk_band:
        new_band = risk_score_after.risk_band.value
        if before.risk_band != new_band:
            # Determine direction
            band_rank = {"low": 3, "medium": 2, "high": 1, "critical": 0}
            improved = band_rank.get(new_band, 0) > band_rank.get(before.risk_band, 0)
            severity = (
                AlertSeverity.info
                if improved
                else AlertSeverity.critical if new_band == "critical"
                else AlertSeverity.warning
            )
            direction = "improved" if improved else "worsened"
            alerts.append((
                AlertType.risk_band_change,
                severity,
                f"Risk band {direction}: {before.risk_band.upper()} → {new_band.upper()}",
                (
                    f"{project.name}'s risk band has {direction} from "
                    f"{before.risk_band.upper()} to {new_band.upper()} "
                    f"(score: {risk_score_after.composite_score:.1f}/100). "
                    + (
                        "Review the updated risk breakdown carefully."
                        if not improved
                        else "Positive signal — re-evaluate your watchlist notes."
                    )
                ),
                {
                    "old_band": before.risk_band,
                    "new_band": new_band,
                    "score": risk_score_after.composite_score,
                    "improved": improved,
                },
            ))

    return alerts


# ─── Connection Manager ───────────────────────────────────────────────────────

class ConnectionManager:
    """
    Thread-safe (asyncio-safe) registry of active WebSocket connections.

    Maintains two indices:
    - _user_sockets:  user_id  → set of WebSocket objects
    - _project_users: project_id → set of user_ids watching it

    All mutations go through ``_lock`` to avoid race conditions with
    concurrent connect / disconnect / subscribe operations.
    """

    def __init__(self) -> None:
        self._user_sockets: dict[str, set[Any]] = defaultdict(set)
        self._project_users: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(
        self,
        ws: "WebSocket",
        user_id: str,
        watchlist: list[str],
    ) -> None:
        await ws.accept()
        async with self._lock:
            self._user_sockets[user_id].add(ws)
            for pid in watchlist:
                self._project_users[pid].add(user_id)
        logger.info(
            "WS connected: user=%s watchlist=%d total_connections=%d",
            user_id[:8],
            len(watchlist),
            self.connected_count,
        )

    async def disconnect(self, ws: "WebSocket", user_id: str) -> None:
        async with self._lock:
            self._user_sockets[user_id].discard(ws)
            if not self._user_sockets[user_id]:
                del self._user_sockets[user_id]
                # Prune project index entries for this user
                to_delete = []
                for pid, users in self._project_users.items():
                    users.discard(user_id)
                    if not users:
                        to_delete.append(pid)
                for pid in to_delete:
                    del self._project_users[pid]
        logger.info(
            "WS disconnected: user=%s remaining_connections=%d",
            user_id[:8],
            self.connected_count,
        )

    # ── Subscription updates ──────────────────────────────────────────────────

    async def update_watchlist(
        self,
        user_id: str,
        new_watchlist: list[str],
    ) -> None:
        """Called when a user adds/removes a project from their watchlist."""
        async with self._lock:
            # Remove user from all existing project entries
            for users in self._project_users.values():
                users.discard(user_id)
            # Re-add for the new watchlist
            for pid in new_watchlist:
                self._project_users[pid].add(user_id)

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        sockets = set(self._user_sockets.get(user_id, set()))
        dead: list[Any] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws, user_id)

    async def broadcast_to_project_watchers(
        self,
        project_id: str,
        payload: dict,
    ) -> None:
        """Send *payload* to every connected user who is watching *project_id*."""
        user_ids = set(self._project_users.get(project_id, set()))
        for uid in user_ids:
            await self.send_to_user(uid, payload)

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def connected_count(self) -> int:
        return sum(len(s) for s in self._user_sockets.values())

    def watching_project(self, project_id: str) -> int:
        """Return the number of connected users watching this project."""
        return len(self._project_users.get(project_id, set()))


# Singleton — imported by ws.py and injected into the subscriber task
connection_manager = ConnectionManager()


# ─── Alert Manager ────────────────────────────────────────────────────────────

class AlertManager:
    """
    Persists alerts to the DB and publishes them to Redis for fan-out to
    connected WebSocket clients.
    """

    async def create_and_publish(
        self,
        *,
        project_id: uuid.UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        payload: dict | None,
        project_name: str | None,
        developer_id: uuid.UUID | None,
        db: AsyncSession,
        redis: Any,
    ) -> ProjectAlert:
        """
        1. Persist a ``ProjectAlert`` row.
        2. Publish the serialised alert to Redis pub/sub.
        Returns the newly created alert.
        """
        alert = ProjectAlert(
            project_id=project_id,
            developer_id=developer_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            payload=payload,
            project_name=project_name,
        )
        db.add(alert)
        await db.flush()   # get alert.id without full commit

        msg = self._serialise(alert)
        if redis:
            try:
                await redis.publish(REDIS_ALERTS_CHANNEL, json.dumps(msg))
            except Exception as exc:
                logger.warning("Redis publish failed: %s", exc)

        logger.info(
            "Alert created: type=%s severity=%s project=%s id=%s",
            alert_type.value,
            severity.value,
            str(project_id)[:8],
            str(alert.id)[:8],
        )
        return alert

    async def emit_project_changes(
        self,
        *,
        before: ProjectSnapshot,
        project: Project,
        complaint_count_after: int,
        risk_score_after: RiskScore | None,
        db: AsyncSession,
        redis: Any,
    ) -> list[ProjectAlert]:
        """
        Detect what changed, persist alerts, and publish them.
        Called by the refresh endpoint after the pipeline runs.
        """
        changes = detect_project_changes(
            before, project, complaint_count_after, risk_score_after
        )
        if not changes:
            return []

        created: list[ProjectAlert] = []
        dev_id = project.developer_id

        for atype, severity, title, msg, payload in changes:
            alert = await self.create_and_publish(
                project_id=project.id,
                alert_type=atype,
                severity=severity,
                title=title,
                message=msg,
                payload=payload,
                project_name=project.name,
                developer_id=dev_id,
                db=db,
                redis=redis,
            )
            created.append(alert)

        return created

    # ── Read-state helpers ────────────────────────────────────────────────────

    async def mark_read(
        self,
        user_id: str,
        alert_ids: list[str],
        redis: Any,
    ) -> None:
        if not redis or not alert_ids:
            return
        key = f"propiq:user:{user_id}:read_alerts"
        try:
            await redis.sadd(key, *alert_ids)
            await redis.expire(key, _READ_STATE_TTL)
        except Exception as exc:
            logger.warning("mark_read failed: %s", exc)

    async def get_read_ids(self, user_id: str, redis: Any) -> set[str]:
        if not redis:
            return set()
        key = f"propiq:user:{user_id}:read_alerts"
        try:
            members = await redis.smembers(key)
            return {m for m in members}
        except Exception:
            return set()

    async def unread_count(self, user_id: str, watchlist: list[str], redis: Any, db: AsyncSession) -> int:
        if not watchlist:
            return 0
        read_ids = await self.get_read_ids(user_id, redis)
        # Query recent alerts for the watchlist
        result = await db.execute(
            select(ProjectAlert.id)
            .where(ProjectAlert.project_id.in_(
                [uuid.UUID(p) for p in watchlist if _is_valid_uuid(p)]
            ))
            .order_by(ProjectAlert.created_at.desc())
            .limit(_HISTORY_LIMIT)
        )
        alert_ids = {str(row[0]) for row in result}
        return len(alert_ids - read_ids)

    # ── History query ─────────────────────────────────────────────────────────

    async def get_history(
        self,
        watchlist: list[str],
        user_id: str,
        redis: Any,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[AlertMessage]:
        if not watchlist:
            return []
        valid_ids = [uuid.UUID(p) for p in watchlist if _is_valid_uuid(p)]
        if not valid_ids:
            return []
        result = await db.execute(
            select(ProjectAlert)
            .where(ProjectAlert.project_id.in_(valid_ids))
            .order_by(ProjectAlert.created_at.desc())
            .limit(min(limit, _HISTORY_LIMIT))
        )
        alerts = list(result.scalars())
        read_ids = await self.get_read_ids(user_id, redis)
        return [
            AlertMessage(
                id=str(a.id),
                project_id=str(a.project_id),
                project_name=a.project_name,
                developer_id=str(a.developer_id) if a.developer_id else None,
                alert_type=a.alert_type.value,
                severity=a.severity.value,
                title=a.title,
                message=a.message,
                payload=a.payload,
                created_at=a.created_at.isoformat(),
                is_read=str(a.id) in read_ids,
            )
            for a in alerts
        ]

    # ── Serialisation ─────────────────────────────────────────────────────────

    @staticmethod
    def _serialise(alert: ProjectAlert) -> dict:
        return {
            "id":           str(alert.id),
            "project_id":   str(alert.project_id),
            "project_name": alert.project_name,
            "developer_id": str(alert.developer_id) if alert.developer_id else None,
            "alert_type":   alert.alert_type.value,
            "severity":     alert.severity.value,
            "title":        alert.title,
            "message":      alert.message,
            "payload":      alert.payload,
            "created_at":   alert.created_at.isoformat(),
            "is_read":      False,
        }


# Singleton
alert_manager = AlertManager()


# ─── Redis subscriber task ────────────────────────────────────────────────────

async def alert_subscriber_task(redis_url: str) -> None:
    """
    Long-running background task:
    subscribes to ``propiq:alerts`` and fans out messages to connected
    WebSocket clients via the global ``connection_manager``.

    Uses a *dedicated* Redis connection (pub/sub blocks the connection).
    Reconnects automatically on failure with exponential back-off.
    """
    import redis.asyncio as aioredis

    backoff = 1.0
    while True:
        client: aioredis.Redis | None = None
        try:
            client = aioredis.from_url(redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(REDIS_ALERTS_CHANNEL)
            logger.info("Alert subscriber: listening on %s", REDIS_ALERTS_CHANNEL)
            backoff = 1.0   # reset on successful connect

            async for raw_msg in pubsub.listen():
                if raw_msg["type"] != "message":
                    continue
                try:
                    data: dict = json.loads(raw_msg["data"])
                    project_id: str | None = data.get("project_id")
                    if project_id:
                        await connection_manager.broadcast_to_project_watchers(
                            project_id,
                            {"type": "alert", "data": data},
                        )
                except Exception as exc:
                    logger.warning("Subscriber: message processing error: %s", exc)

        except asyncio.CancelledError:
            logger.info("Alert subscriber task cancelled — shutting down")
            break
        except Exception as exc:
            logger.error("Alert subscriber error: %s — retrying in %.0fs", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
        finally:
            if client:
                try:
                    await client.aclose()
                except Exception:
                    pass


# ─── Utilities ────────────────────────────────────────────────────────────────

def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def take_snapshot(project: Project, complaint_count: int, risk_band: str | None) -> ProjectSnapshot:
    """Convenience helper to snapshot a project before a pipeline run."""
    return ProjectSnapshot(
        rera_status=project.rera_status.value,
        construction_pct=project.construction_pct,
        possession_date_latest=project.possession_date_latest,
        complaint_count=complaint_count,
        risk_band=risk_band,
        financial_stress_score=(
            project.developer.financial_stress_score
            if project.developer
            else None
        ),
        nclt_proceedings=(
            project.developer.nclt_proceedings
            if project.developer
            else False
        ),
    )
