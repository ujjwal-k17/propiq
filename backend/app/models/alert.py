"""
ProjectAlert ORM model
======================
One row per detected change event (RERA status change, new complaint, etc.).
Alerts are immutable once created — they are never updated, only read and
optionally marked read by users via Redis (no per-user DB rows needed).

Score convention: higher composite_score_after = safer.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, enum.Enum):
    rera_status_change     = "rera_status_change"
    new_complaint          = "new_complaint"
    possession_date_delay  = "possession_date_delay"
    construction_milestone = "construction_milestone"
    risk_band_change       = "risk_band_change"
    developer_nclt         = "developer_nclt"
    developer_stress_spike = "developer_stress_spike"
    price_change           = "price_change"


class AlertSeverity(str, enum.Enum):
    info     = "info"
    warning  = "warning"
    critical = "critical"


class ProjectAlert(Base):
    """
    An immutable event record representing a significant change detected
    for a project.  Persisted for history queries; pushed live over WebSocket.
    """

    __tablename__ = "project_alerts"

    __table_args__ = (
        Index("ix_project_alerts_project_id",   "project_id"),
        Index("ix_project_alerts_created_at",   "created_at"),
        Index("ix_project_alerts_alert_type",   "alert_type"),
        Index("ix_project_alerts_severity",     "severity"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    developer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Classification ────────────────────────────────────────────────────────
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type_enum", create_type=True),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity, name="alert_severity_enum", create_type=True),
        nullable=False,
        default=AlertSeverity.info,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Extra structured data: {"old_value": "active", "new_value": "lapsed"}
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Denormalised for fast reads without join
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship("Project", lazy="select")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<ProjectAlert id={self.id!s:.8} type={self.alert_type.value} "
            f"severity={self.severity.value} project={self.project_id!s:.8}>"
        )
