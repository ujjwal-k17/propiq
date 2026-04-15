"""User and auth Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str | None = None
    is_nri: bool = False
    preferred_cities: list[str] | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    preferred_cities: list[str] | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    risk_appetite: str | None = None
    is_nri: bool | None = None


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    is_nri: bool
    preferred_cities: list | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    risk_appetite: str
    subscription_tier: str
    subscription_expires_at: datetime | None = None
    watchlist_project_ids: list
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # seconds
    user: UserProfile


class TokenPayload(BaseModel):
    sub: str  # user UUID as string
    exp: int
