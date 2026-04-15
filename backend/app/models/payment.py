import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentStatus(str, enum.Enum):
    created = "created"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"
    refunded = "refunded"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    annual = "annual"


class Payment(Base):
    """
    Tracks every Razorpay order created on the platform.

    Lifecycle: created → (authorized) → captured | failed
    On captured: user.subscription_tier and subscription_expires_at are updated.
    """

    __tablename__ = "payments"

    __table_args__ = (
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_razorpay_order_id", "razorpay_order_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── User reference (denormalised — no FK cascade to avoid complexity) ─────
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ── Razorpay identifiers ──────────────────────────────────────────────────
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    razorpay_signature: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    # ── What was purchased ────────────────────────────────────────────────────
    plan: Mapped[str] = mapped_column(String(20), nullable=False)   # "basic" | "pro"
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        SAEnum(BillingCycle, name="billing_cycle_enum", create_type=True),
        nullable=False,
    )

    # ── Amount (always in paise, currency always INR) ─────────────────────────
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum", create_type=True),
        nullable=False,
        default=PaymentStatus.created,
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id!s:.8} order={self.razorpay_order_id!r} "
            f"plan={self.plan} status={self.status.value}>"
        )
