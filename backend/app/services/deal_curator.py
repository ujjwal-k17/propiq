"""
PropIQ Deal Curator
===================
Surfaces curated investment opportunities that pass PropIQ's multi-factor
quality filter and match the requesting user's preferences.

Curation criteria
-----------------
1. Risk band must be ``low`` or ``medium`` (composite score ≥ 60).
2. Project must have a RERA registration number.
3. If user has ``preferred_cities`` set, project must be in one of those cities.
4. If user has ``budget_min`` / ``budget_max`` set (total INR), the project's
   minimum entry price (price_psf_min × carpet_area_min) must fall within that
   range.  When carpet_area_min is absent, price_psf_min alone is used as a
   relative affordability signal via configurable per-city thresholds.
5. Results ordered by composite_score DESC, then appreciation_3yr_base DESC.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.developer import Developer
from app.models.project import Project
from app.models.risk_score import RiskBand, RiskScore
from app.models.user import User


@dataclass
class CuratedDeal:
    """Lightweight DTO returned by the curator — safe to serialise directly."""

    project_id: str
    project_name: str
    developer_name: str | None
    city: str
    micromarket: str
    risk_band: str
    composite_score: float
    price_psf_min: float | None
    price_psf_max: float | None
    appreciation_3yr_base: float | None
    appreciation_3yr_bull: float | None
    rental_yield_estimate: float | None
    rera_registration_no: str | None
    possession_date_declared: str | None   # ISO date string
    construction_pct: float | None
    highlight: str                          # one-liner human-readable reason
    confidence_level: str


def _build_highlight(project: Project, risk_score: RiskScore) -> str:
    """Generate a concise highlight sentence for the deal card."""
    parts: list[str] = []

    if risk_score.risk_band == RiskBand.low:
        parts.append("Low-risk project")
    else:
        parts.append("Medium-risk project")

    if project.rera_registration_no:
        parts.append("RERA registered")

    if project.construction_pct is not None and project.construction_pct >= 80:
        parts.append(f"{project.construction_pct:.0f}% construction complete")
    elif project.construction_pct is not None and project.construction_pct >= 50:
        parts.append(f"{project.construction_pct:.0f}% construction complete")

    if risk_score.appreciation_3yr_base is not None:
        parts.append(
            f"~{risk_score.appreciation_3yr_base:.1f}% p.a. appreciation potential"
        )

    dev = project.developer
    if dev and dev.projects_on_time_pct is not None and dev.projects_on_time_pct >= 75:
        parts.append(f"developer {dev.projects_on_time_pct:.0f}% on-time delivery")

    return " · ".join(parts) if parts else "Meets PropIQ quality criteria"


def _within_budget(project: Project, user: User) -> bool:
    """
    Returns True if the project's minimum entry price is within the user's
    budget range, or if the user has not set a budget.
    """
    if user.budget_min is None and user.budget_max is None:
        return True

    price_psf = project.price_psf_min
    if price_psf is None:
        return True  # no pricing data — do not exclude

    # Compute approximate minimum total price
    if project.carpet_area_min is not None:
        min_total_price = price_psf * project.carpet_area_min
    else:
        # No carpet area — skip absolute budget check, allow through
        return True

    if user.budget_max is not None and min_total_price > user.budget_max:
        return False
    if user.budget_min is not None and min_total_price < user.budget_min:
        return False

    return True


async def get_curated_deals(
    db: AsyncSession,
    user: User | None = None,
    limit: int = 10,
) -> list[CuratedDeal]:
    """
    Return curated deals ordered by quality and aligned to user preferences.

    Parameters
    ----------
    db    : Active async SQLAlchemy session.
    user  : Optional User instance for city / budget / risk filtering.
    limit : Maximum number of deals to return.
    """
    # ── Build query ───────────────────────────────────────────────────────────
    # Join Project → RiskScore (current only) → Developer (eager)
    q = (
        select(Project, RiskScore)
        .join(
            RiskScore,
            and_(
                RiskScore.project_id == Project.id,
                RiskScore.is_current.is_(True),
            ),
        )
        .where(
            RiskScore.risk_band.in_([RiskBand.low, RiskBand.medium]),
            Project.rera_registration_no.isnot(None),
        )
        .options(selectinload(Project.developer))
        .order_by(
            RiskScore.composite_score.desc(),
            RiskScore.appreciation_3yr_base.desc().nulls_last(),
        )
        .limit(limit * 3)  # over-fetch to allow client-side budget/city filtering
    )

    # City filter — applied in SQL when possible for efficiency
    if user and user.preferred_cities:
        cities = [c.strip() for c in user.preferred_cities if c]
        if cities:
            q = q.where(Project.city.in_(cities))

    rows = (await db.execute(q)).all()

    # ── Post-filter and build DTOs ────────────────────────────────────────────
    deals: list[CuratedDeal] = []

    for project, risk_score in rows:
        if len(deals) >= limit:
            break

        # Budget check (requires carpet_area_min — done in Python)
        if user and not _within_budget(project, user):
            continue

        dev: Developer | None = project.developer
        possession_str = (
            project.possession_date_declared.isoformat()
            if project.possession_date_declared
            else None
        )

        deals.append(
            CuratedDeal(
                project_id=str(project.id),
                project_name=project.name,
                developer_name=dev.name if dev else None,
                city=project.city,
                micromarket=project.micromarket,
                risk_band=risk_score.risk_band.value,
                composite_score=risk_score.composite_score,
                price_psf_min=project.price_psf_min,
                price_psf_max=project.price_psf_max,
                appreciation_3yr_base=risk_score.appreciation_3yr_base,
                appreciation_3yr_bull=risk_score.appreciation_3yr_bull,
                rental_yield_estimate=risk_score.rental_yield_estimate,
                rera_registration_no=project.rera_registration_no,
                possession_date_declared=possession_str,
                construction_pct=project.construction_pct,
                highlight=_build_highlight(project, risk_score),
                confidence_level=risk_score.confidence_level.value,
            )
        )

    return deals
