import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SentimentLabel(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    critical = "critical"


class NewsCategory(str, enum.Enum):
    delay = "delay"
    financial_stress = "financial_stress"
    fraud = "fraud"
    nclt = "nclt"
    positive = "positive"
    general = "general"


class NewsItem(Base):
    """
    A news article or press mention related to a project or developer,
    AI-scored for sentiment and due-diligence relevance.
    """

    __tablename__ = "news_items"

    __table_args__ = (
        Index("ix_news_items_developer_id", "developer_id"),
        Index("ix_news_items_project_id", "project_id"),
        Index("ix_news_items_published_at", "published_at"),
        Index("ix_news_items_category", "category"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign keys (both nullable — an item may relate to one or both) ──────
    developer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # ── AI scoring ────────────────────────────────────────────────────────────
    # -1.0 (most negative) → +1.0 (most positive)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[SentimentLabel] = mapped_column(
        SAEnum(SentimentLabel, name="sentiment_label_enum", create_type=True),
        nullable=False,
        default=SentimentLabel.neutral,
    )
    category: Mapped[NewsCategory] = mapped_column(
        SAEnum(NewsCategory, name="news_category_enum", create_type=True),
        nullable=False,
        default=NewsCategory.general,
    )

    # ── Source ────────────────────────────────────────────────────────────────
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    developer: Mapped["Developer | None"] = relationship(
        "Developer", back_populates="news_items", lazy="select"
    )
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="news_items", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<NewsItem id={self.id!s:.8} "
            f"sentiment={self.sentiment_label.value} "
            f"category={self.category.value} "
            f"headline={self.headline[:60]!r}>"
        )
