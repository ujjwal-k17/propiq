"""Developer Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DeveloperSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city_hq: str | None = None
    founded_year: int | None = None
    nclt_proceedings: bool
    active_complaint_count: int
    projects_on_time_pct: float | None = None
    financial_stress_score: float | None = None
    mca_filing_status: str
    total_projects_delivered: int


class NewsItemBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    headline: str
    sentiment_label: str
    category: str
    published_at: datetime | None = None
    source_name: str | None = None
    source_url: str | None = None


class ProjectInDeveloper(BaseModel):
    """Minimal project row shown inside DeveloperDetail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str
    micromarket: str
    rera_registration_no: str | None = None
    rera_status: str
    construction_pct: float | None = None
    possession_date_declared: datetime | None = None


class DeveloperDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    mca_cin: str | None = None
    rera_registration_ids: list[Any] | None = None
    city_hq: str | None = None
    founded_year: int | None = None
    website: str | None = None
    logo_url: str | None = None
    total_projects_delivered: int
    projects_on_time_pct: float | None = None
    total_units_delivered: int
    active_complaint_count: int
    resolved_complaint_count: int
    financial_stress_score: float | None = None
    mca_filing_status: str
    nclt_proceedings: bool
    nclt_details: str | None = None
    last_scraped_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Assembled by endpoint
    project_count: int = 0
    avg_risk_score: float | None = None
    projects: list[ProjectInDeveloper] = []
    recent_news: list[NewsItemBrief] = []
