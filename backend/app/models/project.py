import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectType(str, enum.Enum):
    residential = "residential"
    commercial = "commercial"


class OcStatus(str, enum.Enum):
    not_applied = "not_applied"
    applied = "applied"
    received = "received"


class ReraStatus(str, enum.Enum):
    active = "active"
    lapsed = "lapsed"
    revoked = "revoked"
    completed = "completed"


class Project(Base):
    """
    A RERA-registered real estate project (residential apartment complex
    or commercial office building) in India.
    """

    __tablename__ = "projects"

    __table_args__ = (
        Index("ix_projects_city_micromarket", "city", "micromarket"),
        Index("ix_projects_developer_id", "developer_id"),
        Index("ix_projects_rera_registration_no", "rera_registration_no", unique=True),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    developer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rera_registration_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )

    # ── Classification ────────────────────────────────────────────────────────
    project_type: Mapped[ProjectType] = mapped_column(
        SAEnum(ProjectType, name="project_type_enum", create_type=True),
        nullable=False,
        default=ProjectType.residential,
    )

    # ── Location ──────────────────────────────────────────────────────────────
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    micromarket: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Scale ─────────────────────────────────────────────────────────────────
    total_units: Mapped[int] = mapped_column(Integer, nullable=False)
    units_sold: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Size ──────────────────────────────────────────────────────────────────
    carpet_area_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    carpet_area_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Pricing ───────────────────────────────────────────────────────────────
    price_psf_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_psf_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Timeline ──────────────────────────────────────────────────────────────
    possession_date_declared: Mapped[date | None] = mapped_column(Date, nullable=True)
    possession_date_latest: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Construction ──────────────────────────────────────────────────────────
    construction_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0–100

    # ── Regulatory status ─────────────────────────────────────────────────────
    oc_status: Mapped[OcStatus] = mapped_column(
        SAEnum(OcStatus, name="oc_status_enum", create_type=True),
        nullable=False,
        default=OcStatus.not_applied,
    )
    rera_status: Mapped[ReraStatus] = mapped_column(
        SAEnum(ReraStatus, name="rera_status_enum", create_type=True),
        nullable=False,
        default=ReraStatus.active,
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    amenities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
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
    developer: Mapped["Developer"] = relationship(
        "Developer", back_populates="projects", lazy="select"
    )
    risk_scores: Mapped[list["RiskScore"]] = relationship(
        "RiskScore",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="RiskScore.generated_at.desc()",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        "Complaint",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    news_items: Mapped[list["NewsItem"]] = relationship(
        "NewsItem",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Project id={self.id!s:.8} name={self.name!r} "
            f"city={self.city!r} rera={self.rera_registration_no!r}>"
        )
