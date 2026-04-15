import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class McaFilingStatus(str, enum.Enum):
    compliant = "compliant"
    delayed = "delayed"
    defaulted = "defaulted"
    unknown = "unknown"


class Developer(Base):
    """
    A real estate developer entity.  Identity is anchored to the MCA CIN
    where available; RERA registrations are stored per-state as JSON.
    """

    __tablename__ = "developers"

    __table_args__ = (
        Index("ix_developers_mca_cin", "mca_cin", unique=True),
        Index("ix_developers_name", "name"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mca_cin: Mapped[str | None] = mapped_column(
        String(21), nullable=True, unique=True
    )  # 21-char MCA Corporate Identification Number

    # ── RERA registrations ────────────────────────────────────────────────────
    # Stored as: [{"state": "Maharashtra", "id": "P51800012345"}, ...]
    rera_registration_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Profile ───────────────────────────────────────────────────────────────
    city_hq: Mapped[str | None] = mapped_column(String(100), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Delivery track record ─────────────────────────────────────────────────
    total_projects_delivered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    projects_on_time_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0–100
    total_units_delivered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # ── Complaint record ──────────────────────────────────────────────────────
    active_complaint_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    resolved_complaint_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # ── Financial health ──────────────────────────────────────────────────────
    # 0 = financially strong, 100 = severe stress
    financial_stress_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mca_filing_status: Mapped[McaFilingStatus] = mapped_column(
        SAEnum(McaFilingStatus, name="mca_filing_status_enum", create_type=True),
        nullable=False,
        default=McaFilingStatus.unknown,
    )

    # ── Legal / insolvency ────────────────────────────────────────────────────
    nclt_proceedings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    nclt_details: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Scrape metadata ───────────────────────────────────────────────────────
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="developer", lazy="select"
    )
    news_items: Mapped[list["NewsItem"]] = relationship(
        "NewsItem",
        back_populates="developer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Developer id={self.id!s:.8} name={self.name!r} "
            f"cin={self.mca_cin!r} nclt={self.nclt_proceedings}>"
        )
