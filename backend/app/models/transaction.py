import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    """
    A registered property sale deed sourced from state IGR / registration
    department portals (e.g. IGR Maharashtra, Kaveri Karnataka).

    Transactions are the ground-truth price signal used to calibrate
    the appreciation model and validate developer pricing claims.
    """

    __tablename__ = "transactions"

    __table_args__ = (
        Index("ix_transactions_project_id", "project_id"),
        Index("ix_transactions_city_micromarket", "city", "micromarket"),
        Index("ix_transactions_transaction_date", "transaction_date"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign key (nullable — transactions may arrive before project match) ─
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Location ──────────────────────────────────────────────────────────────
    micromarket: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Price ─────────────────────────────────────────────────────────────────
    price_psf: Mapped[float] = mapped_column(Float, nullable=False)
    carpet_area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)  # INR

    # ── Date ──────────────────────────────────────────────────────────────────
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Registration details ──────────────────────────────────────────────────
    registration_no: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Unit details ──────────────────────────────────────────────────────────
    floor_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. '2BHK', 'studio', 'office'

    # ── Provenance ────────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. 'igr_maharashtra', 'kaveri_karnataka'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="transactions", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id!s:.8} city={self.city!r} "
            f"micromarket={self.micromarket!r} psf={self.price_psf:.0f} "
            f"date={self.transaction_date}>"
        )
