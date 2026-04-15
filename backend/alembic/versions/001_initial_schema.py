"""Initial schema — all PropIQ tables

Revision ID: 001
Revises:
Create Date: 2026-04-15 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── PostgreSQL enum types ─────────────────────────────────────────────────
    project_type_enum = postgresql.ENUM(
        "residential", "commercial", name="project_type_enum", create_type=False
    )
    oc_status_enum = postgresql.ENUM(
        "not_applied", "applied", "received", name="oc_status_enum", create_type=False
    )
    rera_status_enum = postgresql.ENUM(
        "active", "lapsed", "revoked", "completed",
        name="rera_status_enum", create_type=False
    )
    mca_filing_status_enum = postgresql.ENUM(
        "compliant", "delayed", "defaulted", "unknown",
        name="mca_filing_status_enum", create_type=False
    )
    risk_band_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="risk_band_enum", create_type=False
    )
    confidence_level_enum = postgresql.ENUM(
        "high", "medium", "low",
        name="confidence_level_enum", create_type=False
    )
    complaint_status_enum = postgresql.ENUM(
        "pending", "resolved", "dismissed", "unknown",
        name="complaint_status_enum", create_type=False
    )
    sentiment_label_enum = postgresql.ENUM(
        "positive", "neutral", "negative", "critical",
        name="sentiment_label_enum", create_type=False
    )
    news_category_enum = postgresql.ENUM(
        "delay", "financial_stress", "fraud", "nclt", "positive", "general",
        name="news_category_enum", create_type=False
    )
    risk_appetite_enum = postgresql.ENUM(
        "conservative", "moderate", "aggressive",
        name="risk_appetite_enum", create_type=False
    )
    subscription_tier_enum = postgresql.ENUM(
        "free", "basic", "pro", "enterprise",
        name="subscription_tier_enum", create_type=False
    )

    for e in [
        project_type_enum, oc_status_enum, rera_status_enum,
        mca_filing_status_enum, risk_band_enum, confidence_level_enum,
        complaint_status_enum, sentiment_label_enum, news_category_enum,
        risk_appetite_enum, subscription_tier_enum,
    ]:
        e.create(op.get_bind(), checkfirst=True)

    # ── developers ────────────────────────────────────────────────────────────
    op.create_table(
        "developers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("mca_cin", sa.String(21), nullable=True, unique=True),
        sa.Column("rera_registration_ids", postgresql.JSONB(), nullable=True),
        sa.Column("city_hq", sa.String(100), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("logo_url", sa.String(1024), nullable=True),
        sa.Column("total_projects_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("projects_on_time_pct", sa.Float(), nullable=True),
        sa.Column("total_units_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_complaint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_complaint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("financial_stress_score", sa.Float(), nullable=True),
        sa.Column(
            "mca_filing_status",
            postgresql.ENUM(name="mca_filing_status_enum", create_type=False),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("nclt_proceedings", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("nclt_details", sa.String(1024), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_developers_name", "developers", ["name"])
    op.create_index("ix_developers_mca_cin", "developers", ["mca_cin"], unique=True)

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "developer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rera_registration_no", sa.String(100), nullable=True, unique=True),
        sa.Column(
            "project_type",
            postgresql.ENUM(name="project_type_enum", create_type=False),
            nullable=False,
            server_default="residential",
        ),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("micromarket", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("total_units", sa.Integer(), nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=True),
        sa.Column("carpet_area_min", sa.Float(), nullable=True),
        sa.Column("carpet_area_max", sa.Float(), nullable=True),
        sa.Column("price_psf_min", sa.Float(), nullable=True),
        sa.Column("price_psf_max", sa.Float(), nullable=True),
        sa.Column("possession_date_declared", sa.Date(), nullable=True),
        sa.Column("possession_date_latest", sa.Date(), nullable=True),
        sa.Column("construction_pct", sa.Float(), nullable=True),
        sa.Column(
            "oc_status",
            postgresql.ENUM(name="oc_status_enum", create_type=False),
            nullable=False,
            server_default="not_applied",
        ),
        sa.Column(
            "rera_status",
            postgresql.ENUM(name="rera_status_enum", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("amenities", postgresql.JSONB(), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_developer_id", "projects", ["developer_id"])
    op.create_index(
        "ix_projects_rera_registration_no",
        "projects",
        ["rera_registration_no"],
        unique=True,
    )
    op.create_index("ix_projects_city", "projects", ["city"])
    op.create_index("ix_projects_micromarket", "projects", ["micromarket"])
    op.create_index(
        "ix_projects_city_micromarket", "projects", ["city", "micromarket"]
    )

    # ── risk_scores ───────────────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column(
            "risk_band",
            postgresql.ENUM(name="risk_band_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("legal_score", sa.Float(), nullable=False),
        sa.Column("developer_score", sa.Float(), nullable=False),
        sa.Column("project_score", sa.Float(), nullable=False),
        sa.Column("location_score", sa.Float(), nullable=False),
        sa.Column("financial_score", sa.Float(), nullable=False),
        sa.Column("macro_score", sa.Float(), nullable=False),
        sa.Column("legal_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("developer_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("project_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "confidence_level",
            postgresql.ENUM(name="confidence_level_enum", create_type=False),
            nullable=False,
            server_default="low",
        ),
        sa.Column("appreciation_3yr_base", sa.Float(), nullable=True),
        sa.Column("appreciation_3yr_bull", sa.Float(), nullable=True),
        sa.Column("appreciation_3yr_bear", sa.Float(), nullable=True),
        sa.Column("appreciation_5yr_base", sa.Float(), nullable=True),
        sa.Column("rental_yield_estimate", sa.Float(), nullable=True),
        sa.Column("data_freshness", postgresql.JSONB(), nullable=True),
        sa.Column("scoring_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_risk_scores_project_id", "risk_scores", ["project_id"])
    op.create_index("ix_risk_scores_generated_at", "risk_scores", ["generated_at"])
    # Partial unique index: only one current score per project
    op.execute(
        """
        CREATE UNIQUE INDEX uix_risk_scores_project_current
        ON risk_scores (project_id)
        WHERE is_current = TRUE
        """
    )

    # ── transactions ──────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("micromarket", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("price_psf", sa.Float(), nullable=False),
        sa.Column("carpet_area_sqft", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("registration_no", sa.String(100), nullable=True),
        sa.Column("floor_no", sa.Integer(), nullable=True),
        sa.Column("unit_type", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_transactions_project_id", "transactions", ["project_id"])
    op.create_index(
        "ix_transactions_city_micromarket", "transactions", ["city", "micromarket"]
    )
    op.create_index(
        "ix_transactions_transaction_date", "transactions", ["transaction_date"]
    )

    # ── complaints ────────────────────────────────────────────────────────────
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "developer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rera_portal", sa.String(100), nullable=False),
        sa.Column("complaint_no", sa.String(100), nullable=True),
        sa.Column("complaint_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="complaint_status_enum", create_type=False),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("resolution_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_complaints_project_id", "complaints", ["project_id"])
    op.create_index("ix_complaints_developer_id", "complaints", ["developer_id"])
    op.create_index("ix_complaints_status", "complaints", ["status"])

    # ── news_items ────────────────────────────────────────────────────────────
    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "developer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("headline", sa.String(1024), nullable=False),
        sa.Column("summary", sa.String(4096), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column(
            "sentiment_label",
            postgresql.ENUM(name="sentiment_label_enum", create_type=False),
            nullable=False,
            server_default="neutral",
        ),
        sa.Column(
            "category",
            postgresql.ENUM(name="news_category_enum", create_type=False),
            nullable=False,
            server_default="general",
        ),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_news_items_developer_id", "news_items", ["developer_id"])
    op.create_index("ix_news_items_project_id", "news_items", ["project_id"])
    op.create_index("ix_news_items_published_at", "news_items", ["published_at"])
    op.create_index("ix_news_items_category", "news_items", ["category"])

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_nri", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("preferred_cities", postgresql.JSONB(), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column(
            "risk_appetite",
            postgresql.ENUM(name="risk_appetite_enum", create_type=False),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "subscription_tier",
            postgresql.ENUM(name="subscription_tier_enum", create_type=False),
            nullable=False,
            server_default="free",
        ),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "watchlist_project_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("users")
    op.drop_table("news_items")
    op.drop_table("complaints")
    op.drop_table("transactions")
    op.drop_table("risk_scores")
    op.drop_table("projects")
    op.drop_table("developers")

    # Drop enum types
    for enum_name in [
        "subscription_tier_enum",
        "risk_appetite_enum",
        "news_category_enum",
        "sentiment_label_enum",
        "complaint_status_enum",
        "confidence_level_enum",
        "risk_band_enum",
        "mca_filing_status_enum",
        "rera_status_enum",
        "oc_status_enum",
        "project_type_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
