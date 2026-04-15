"""Risk score Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RiskScoreResponse(BaseModel):
    """Full risk score with all dimensions and flags."""
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


class AppreciationEstimate(BaseModel):
    appreciation_3yr_base: float | None = None
    appreciation_3yr_bull: float | None = None
    appreciation_3yr_bear: float | None = None
    appreciation_5yr_base: float | None = None
    rental_yield_estimate: float | None = None
    risk_adjusted_3yr_cagr: float | None = None
    data_points_used: int = 0
