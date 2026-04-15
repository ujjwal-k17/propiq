import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskBand(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ConfidenceLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RiskScore(Base):
    """
    Composite due-diligence risk score for a project.

    A new row is appended every time the engine re-scores a project.
    Exactly one row per project has is_current=True (enforced by a
    partial unique index created in the Alembic migration).

    Score convention: 0–100, higher = safer / lower risk.
    """

    __tablename__ = "risk_scores"

    __table_args__ = (
        Index("ix_risk_scores_project_id", "project_id"),
        Index("ix_risk_scores_generated_at", "generated_at"),
        # Enforces at most one current score per project at the DB level.
        # Only the partial-index variant (WHERE is_current = TRUE) is truly
        # unique; we approximate it here and enforce in application logic.
        UniqueConstraint(
            "project_id",
            name="uq_risk_scores_project_current",
            # NOTE: real partial-unique index added in Alembic migration
        ),
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

    # ── Composite score ───────────────────────────────────────────────────────
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0–100
    risk_band: Mapped[RiskBand] = mapped_column(
        SAEnum(RiskBand, name="risk_band_enum", create_type=True),
        nullable=False,
    )

    # ── Dimension scores (0–100 each) ─────────────────────────────────────────
    legal_score: Mapped[float] = mapped_column(Float, nullable=False)
    developer_score: Mapped[float] = mapped_column(Float, nullable=False)
    project_score: Mapped[float] = mapped_column(Float, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, nullable=False)
    financial_score: Mapped[float] = mapped_column(Float, nullable=False)
    macro_score: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Flags (lists of human-readable strings) ───────────────────────────────
    legal_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    developer_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    project_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel, name="confidence_level_enum", create_type=True),
        nullable=False,
        default=ConfidenceLevel.low,
    )

    # ── Appreciation forecast (percentage CAGR) ───────────────────────────────
    appreciation_3yr_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    appreciation_3yr_bull: Mapped[float | None] = mapped_column(Float, nullable=True)
    appreciation_3yr_bear: Mapped[float | None] = mapped_column(Float, nullable=True)
    appreciation_5yr_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    rental_yield_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Provenance ────────────────────────────────────────────────────────────
    # {"rera": "2026-04-15T10:00:00Z", "mca": "2026-04-14T08:00:00Z", ...}
    data_freshness: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scoring_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0"
    )

    # ── Currency flag ─────────────────────────────────────────────────────────
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(
        "Project", back_populates="risk_scores", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<RiskScore id={self.id!s:.8} project={self.project_id!s:.8} "
            f"score={self.composite_score:.1f} band={self.risk_band.value} "
            f"current={self.is_current}>"
        )
