"""
Developers routes
=================
GET /developers/search               — name search (MUST come before /{id})
GET /developers/{developer_id}       — full detail with projects + news
GET /developers/{developer_id}/projects — project list for one developer
"""
from __future__ import annotations

import uuid
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.developer import Developer
from app.models.news_item import NewsItem
from app.models.project import Project
from app.models.risk_score import RiskScore
from app.schemas.developer import DeveloperDetail, DeveloperSummary, NewsItemBrief, ProjectInDeveloper
from app.schemas.project import ProjectSummary

router = APIRouter(prefix="/developers")


# ── GET /developers/search — MUST be registered before /{developer_id} ───────

@router.get(
    "/search",
    response_model=list[DeveloperSummary],
    summary="Search developers by name (min 3 characters)",
)
async def search_developers(
    name: str = Query(..., min_length=3, description="Developer name to search"),
    db: AsyncSession = Depends(get_db),
) -> list[Developer]:
    rows = list(
        (
            await db.execute(
                select(Developer)
                .where(Developer.name.ilike(f"%{name}%"))
                .order_by(Developer.name)
                .limit(20)
            )
        ).scalars()
    )
    return rows


# ── GET /developers/{developer_id} ───────────────────────────────────────────

@router.get(
    "/{developer_id}",
    response_model=DeveloperDetail,
    summary="Full developer detail with projects, complaints summary, and news",
)
async def get_developer(
    developer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    dev = (
        await db.execute(
            select(Developer)
            .where(Developer.id == developer_id)
            .options(selectinload(Developer.projects))
        )
    ).scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    # Compute average composite risk score across this developer's projects
    project_ids = [p.id for p in dev.projects]
    avg_score: float | None = None
    if project_ids:
        scores = list(
            (
                await db.execute(
                    select(RiskScore.composite_score).where(
                        and_(
                            RiskScore.project_id.in_(project_ids),
                            RiskScore.is_current.is_(True),
                        )
                    )
                )
            ).scalars()
        )
        if scores:
            avg_score = round(mean(scores), 2)

    # Recent news (last 10)
    news_items = list(
        (
            await db.execute(
                select(NewsItem)
                .where(NewsItem.developer_id == developer_id)
                .order_by(NewsItem.published_at.desc().nullslast())
                .limit(10)
            )
        ).scalars()
    )

    return {
        **{
            col: getattr(dev, col)
            for col in [
                "id", "name", "mca_cin", "rera_registration_ids", "city_hq",
                "founded_year", "website", "logo_url", "total_projects_delivered",
                "projects_on_time_pct", "total_units_delivered",
                "active_complaint_count", "resolved_complaint_count",
                "financial_stress_score", "nclt_proceedings", "nclt_details",
                "last_scraped_at", "created_at", "updated_at",
            ]
        },
        "mca_filing_status": dev.mca_filing_status.value,
        "project_count": len(dev.projects),
        "avg_risk_score": avg_score,
        "projects": [ProjectInDeveloper.model_validate(p) for p in dev.projects[:20]],
        "recent_news": [NewsItemBrief.model_validate(n) for n in news_items],
    }


# ── GET /developers/{developer_id}/projects ───────────────────────────────────

@router.get(
    "/{developer_id}/projects",
    response_model=list[ProjectSummary],
    summary="All projects by a developer with optional status filter",
)
async def get_developer_projects(
    developer_id: uuid.UUID,
    rera_status: str | None = Query(None, description="active | lapsed | revoked | completed"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    # Verify developer exists
    dev_exists = (
        await db.execute(select(Developer.id).where(Developer.id == developer_id))
    ).scalar_one_or_none()
    if not dev_exists:
        raise HTTPException(status_code=404, detail="Developer not found")

    q = (
        select(Project)
        .where(Project.developer_id == developer_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if rera_status:
        q = q.where(Project.rera_status == rera_status)

    return list((await db.execute(q)).scalars())
