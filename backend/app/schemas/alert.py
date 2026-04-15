"""
Alert schemas
=============
Pydantic models for WebSocket messages and REST history endpoints.

WebSocket protocol (server → client):

  {"type": "connected",  "data": ConnectedPayload}
  {"type": "alert",      "data": AlertMessage}
  {"type": "history",    "data": list[AlertMessage]}
  {"type": "pong"}
  {"type": "error",      "code": str, "message": str}

WebSocket protocol (client → server):

  {"type": "ping"}
  {"type": "subscribe",      "project_ids": [str, ...]}
  {"type": "mark_read",      "alert_ids": [str, ...]}
  {"type": "request_history","limit": int}
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Outbound (server → client) ────────────────────────────────────────────────

class AlertMessage(BaseModel):
    """Serialisable alert payload sent over WebSocket and returned by REST."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    project_name: str | None
    developer_id: str | None
    alert_type: str
    severity: str
    title: str
    message: str
    payload: dict | None
    created_at: str            # ISO-8601
    is_read: bool = False


class ConnectedPayload(BaseModel):
    user_id: str
    watchlist: list[str]
    unread_count: int


class WSOutbound(BaseModel):
    """Top-level wrapper for every server → client message."""
    type: str                  # connected | alert | history | pong | error
    data: Any = None
    code: str | None = None    # only for type=="error"
    message: str | None = None # only for type=="error"


# ── Inbound (client → server) ─────────────────────────────────────────────────

class WSInbound(BaseModel):
    """Top-level wrapper for every client → server message."""
    type: str                                   # ping | subscribe | mark_read | request_history
    project_ids: list[str] | None = None        # for subscribe
    alert_ids: list[str] | None = None          # for mark_read
    limit: int = 20                             # for request_history
