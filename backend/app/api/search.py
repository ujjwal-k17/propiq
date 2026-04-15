"""
Search routes
=============
GET /search              — full-text search across projects + developers
GET /search/suggestions  — autocomplete (max 8, optimised for speed)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.developer import Developer
from app.models.project import Project
from app.schemas.developer import DeveloperSummary
from app.schemas.project import ProjectSummary

router = APIRouter(prefix="/search")


@router.get(
    "",
    summary="Search projects and developers",
)
async def search(
    q: str = Query(..., min_length=2, description="Search term"),
    type: str = Query("all", description="all | project | developer"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Search by project name, micromarket, city, RERA number, or developer name.

    If the query looks like a RERA registration number (contains '/') it is
    matched exactly first; partial matches follow.
    """
    term = f"%{q}%"
    looks_like_rera = "/" in q

    projects: list[Project] = []
    developers: list[Developer] = []

    if type in ("all", "project"):
        if looks_like_rera:
            # RERA exact match first
            exact = (
                await db.execute(
                    select(Project).where(
                        Project.rera_registration_no.ilike(q)
                    ).limit(5)
                )
            ).scalars().all()
            if exact:
                projects = list(exact)
            else:
                # Fall through to partial
                looks_like_rera = False

        if not looks_like_rera:
            projects = list(
                (
                    await db.execute(
                        select(Project)
                        .where(
                            or_(
                                Project.name.ilike(term),
                                Project.micromarket.ilike(term),
                                Project.city.ilike(term),
                                Project.rera_registration_no.ilike(term),
                            )
                        )
                        .order_by(Project.name)
                        .limit(5)
                    )
                ).scalars()
            )

    if type in ("all", "developer"):
        developers = list(
            (
                await db.execute(
                    select(Developer)
                    .where(Developer.name.ilike(term))
                    .order_by(Developer.name)
                    .limit(3)
                )
            ).scalars()
        )

    total = len(projects) + len(developers)

    return {
        "query": q,
        "total_results": total,
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "city": p.city,
                "micromarket": p.micromarket,
                "project_type": p.project_type.value,
                "rera_registration_no": p.rera_registration_no,
                "rera_status": p.rera_status.value,
                "oc_status": p.oc_status.value,
                "price_psf_min": p.price_psf_min,
                "price_psf_max": p.price_psf_max,
                "possession_date_declared": p.possession_date_declared,
                "construction_pct": p.construction_pct,
                "total_units": p.total_units,
            }
            for p in projects
        ],
        "developers": [
            {
                "id": str(d.id),
                "name": d.name,
                "city_hq": d.city_hq,
                "nclt_proceedings": d.nclt_proceedings,
                "active_complaint_count": d.active_complaint_count,
                "projects_on_time_pct": d.projects_on_time_pct,
                "financial_stress_score": d.financial_stress_score,
                "mca_filing_status": d.mca_filing_status.value,
                "total_projects_delivered": d.total_projects_delivered,
                "founded_year": d.founded_year,
            }
            for d in developers
        ],
    }


@router.get(
    "/suggestions",
    response_model=list[str],
    summary="Autocomplete suggestions (project names + developer names, max 8)",
)
async def suggestions(
    q: str = Query(..., min_length=2, description="Partial name to complete"),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """
    Returns up to 8 suggestion strings for use in autocomplete UI.
    Queries the indexed name columns only — fast even on large datasets.
    """
    term = f"{q}%"  # prefix match is index-friendly

    project_names = list(
        (
            await db.execute(
                select(Project.name)
                .where(Project.name.ilike(term))
                .order_by(Project.name)
                .limit(5)
            )
        ).scalars()
    )

    dev_names = list(
        (
            await db.execute(
                select(Developer.name)
                .where(Developer.name.ilike(term))
                .order_by(Developer.name)
                .limit(3)
            )
        ).scalars()
    )

    # Merge, deduplicate, cap at 8
    seen: set[str] = set()
    result: list[str] = []
    for name in project_names + dev_names:
        if name not in seen and len(result) < 8:
            seen.add(name)
            result.append(name)

    return result
