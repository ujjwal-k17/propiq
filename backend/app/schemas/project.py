"""
Project Pydantic schemas.
Field names mirror SQLAlchemy models so model_validate(orm_obj) works directly.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Building blocks ───────────────────────────────────────────────────────────

class RiskScoreSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    composite_score: float
    risk_band: str
    confidence_level: str
    legal_score: float
    developer_score: float
    project_score: float
    location_score: float
    financial_score: float
    macro_score: float
    generated_at: datetime


class RiskScoreDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    composite_score: float
    risk_band: str
    confidence_level: str
    legal_score: float
    developer_score: float
    project_score: float
    location_score: float
    financial_score: float
    macro_score: float
    legal_flags: list[str]
    developer_flags: list[str]
    project_flags: list[str]
    appreciation_3yr_base: float | None = None
    appreciation_3yr_bull: float | None = None
    appreciation_3yr_bear: float | None = None
    appreciation_5yr_base: float | None = None
    rental_yield_estimate: float | None = None
    data_freshness: dict[str, Any] | None = None
    scoring_version: str
    is_current: bool
    generated_at: datetime


class DeveloperBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city_hq: str | None = None
    founded_year: int | None = None
    website: str | None = None
    logo_url: str | None = None
    nclt_proceedings: bool
    projects_on_time_pct: float | None = None
    total_projects_delivered: int
    total_units_delivered: int
    active_complaint_count: int
    resolved_complaint_count: int
    financial_stress_score: float | None = None
    mca_filing_status: str


class TransactionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_date: date
    price_psf: float
    carpet_area_sqft: float
    total_price: float
    source: str


class ComplaintBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_no: str | None = None
    complaint_date: date | None = None
    status: str
    category: str | None = None
    rera_portal: str
    resolution_date: date | None = None


class NewsItemBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    headline: str
    sentiment_label: str
    category: str
    published_at: datetime | None = None
    source_name: str | None = None
    source_url: str | None = None


class AppreciationEstimate(BaseModel):
    appreciation_3yr_base: float | None = None
    appreciation_3yr_bull: float | None = None
    appreciation_3yr_bear: float | None = None
    appreciation_5yr_base: float | None = None
    rental_yield_estimate: float | None = None
    risk_adjusted_3yr_cagr: float | None = None
    data_points_used: int = 0


class ComplaintSummary(BaseModel):
    total: int
    pending: int
    resolved: int
    dismissed: int
    by_category: dict[str, int]
    complaints: list[ComplaintBrief]


class TransactionStats(BaseModel):
    avg_price_psf: float | None
    price_change_pct_12m: float | None
    total_count: int
    transactions: list[TransactionBrief]


# ── List / card views ─────────────────────────────────────────────────────────

class ProjectSummary(BaseModel):
    """Minimal card used in search results and lists."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str
    micromarket: str
    project_type: str
    rera_registration_no: str | None = None
    rera_status: str
    oc_status: str
    price_psf_min: float | None = None
    price_psf_max: float | None = None
    possession_date_declared: date | None = None
    construction_pct: float | None = None
    total_units: int


class ProjectWithScore(ProjectSummary):
    """Summary + current risk score, used in listing pages."""
    developer_name: str | None = None
    risk_score: RiskScoreSummary | None = None


# ── Full detail ───────────────────────────────────────────────────────────────

class ProjectDetail(BaseModel):
    """Full project response assembled from multiple queries."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str
    micromarket: str
    project_type: str
    rera_registration_no: str | None = None
    rera_status: str
    oc_status: str
    total_units: int
    units_sold: int | None = None
    carpet_area_min: float | None = None
    carpet_area_max: float | None = None
    price_psf_min: float | None = None
    price_psf_max: float | None = None
    possession_date_declared: date | None = None
    possession_date_latest: date | None = None
    construction_pct: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    amenities: dict[str, Any] | None = None
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime

    # Assembled by endpoint
    developer: DeveloperBrief | None = None
    risk_score: RiskScoreDetail | None = None
    recent_transactions: list[TransactionBrief] = []
    complaint_summary: ComplaintSummary | None = None
    recent_news: list[NewsItemBrief] = []
    appreciation: AppreciationEstimate | None = None


# ── Curated deal ──────────────────────────────────────────────────────────────

class CuratedDeal(BaseModel):
    project_id: str
    project_name: str
    developer_name: str | None = None
    city: str
    micromarket: str
    risk_band: str
    composite_score: float
    price_psf_min: float | None = None
    price_psf_max: float | None = None
    appreciation_3yr_base: float | None = None
    appreciation_3yr_bull: float | None = None
    rental_yield_estimate: float | None = None
    rera_registration_no: str | None = None
    possession_date_declared: str | None = None
    construction_pct: float | None = None
    highlight: str
    confidence_level: str


# ── Comparison ────────────────────────────────────────────────────────────────

class ProjectComparison(BaseModel):
    project: ProjectSummary
    developer: DeveloperBrief | None = None
    risk_score: RiskScoreDetail | None = None
    appreciation: AppreciationEstimate | None = None
    pros: list[str]
    cons: list[str]


class ComparisonReport(BaseModel):
    projects: list[ProjectComparison]
    generated_at: datetime
