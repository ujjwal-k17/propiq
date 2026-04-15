import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskAppetite(str, enum.Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


class SubscriptionTier(str, enum.Enum):
    free = "free"
    basic = "basic"
    pro = "pro"
    enterprise = "enterprise"


class User(Base):
    """
    A PropIQ platform user — home buyer, investor, or NRI.
    Subscription tier gates report generation and advanced AI features.
    """

    __tablename__ = "users"

    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Auth ──────────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Profile ───────────────────────────────────────────────────────────────
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_nri: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Preferences ───────────────────────────────────────────────────────────
    # ["Mumbai", "Bengaluru"]
    preferred_cities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)  # INR
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_appetite: Mapped[RiskAppetite] = mapped_column(
        SAEnum(RiskAppetite, name="risk_appetite_enum", create_type=True),
        nullable=False,
        default=RiskAppetite.moderate,
    )

    # ── Subscription ──────────────────────────────────────────────────────────
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, name="subscription_tier_enum", create_type=True),
        nullable=False,
        default=SubscriptionTier.free,
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Watchlist ─────────────────────────────────────────────────────────────
    # List of project UUID strings the user is tracking
    watchlist_project_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # ── Account state ─────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
            f"<User id={self.id!s:.8} email={self.email!r} "
            f"tier={self.subscription_tier.value} nri={self.is_nri}>"
        )
