import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ComplaintStatus(str, enum.Enum):
    pending = "pending"
    resolved = "resolved"
    dismissed = "dismissed"
    unknown = "unknown"


class Complaint(Base):
    """
    A RERA complaint filed against a project or developer.

    A single complaint is always linked to a developer (the registered
    promoter) and optionally to a specific project RERA ID.
    """

    __tablename__ = "complaints"

    __table_args__ = (
        Index("ix_complaints_project_id", "project_id"),
        Index("ix_complaints_developer_id", "developer_id"),
        Index("ix_complaints_status", "status"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    developer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Source portal ─────────────────────────────────────────────────────────
    rera_portal: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. 'maharera', 'krera', 'tsrera'

    # ── Complaint details ─────────────────────────────────────────────────────
    complaint_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    complaint_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status_enum", create_type=True),
        nullable=False,
        default=ComplaintStatus.unknown,
    )

    # Category is free-text to accommodate portal variations
    # Common values: 'delay', 'quality', 'refund', 'possession', 'other'
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="complaints", lazy="select"
    )
    developer: Mapped["Developer | None"] = relationship(
        "Developer", foreign_keys=[developer_id], lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<Complaint id={self.id!s:.8} no={self.complaint_no!r} "
            f"portal={self.rera_portal!r} status={self.status.value} "
            f"category={self.category!r}>"
        )
