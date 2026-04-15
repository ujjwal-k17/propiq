"""
Diligence routes
================
GET  /diligence/curated         — personalised curated deals
GET  /diligence/compare         — side-by-side comparison of 2–3 projects
POST /diligence/report/{id}     — generate PDF report (pro tier required)
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user, get_optional_current_user
from app.database import get_db
from app.models.developer import Developer
from app.models.project import Project
from app.models.risk_score import RiskBand, RiskScore
from app.models.user import SubscriptionTier, User
from app.schemas.project import (
    AppreciationEstimate,
    ComparisonReport,
    CuratedDeal,
    DeveloperBrief,
    ProjectComparison,
    ProjectSummary,
    RiskScoreDetail,
)
from app.services.appreciation_model import AppreciationModel
from app.services.deal_curator import get_curated_deals
from app.services.report_generator import ReportGenerator
from app.services.risk_engine import RiskEngine

router = APIRouter(prefix="/diligence")
_appreciation = AppreciationModel()
_engine = RiskEngine()
_report_generator = ReportGenerator()

_REPORT_CACHE_SECONDS = 7 * 24 * 3600  # 7 days


# ── Helper: derive pros/cons from risk score ──────────────────────────────────

def _derive_pros_cons(
    project: Project,
    rs: RiskScore | None,
) -> tuple[list[str], list[str]]:
    pros: list[str] = []
    cons: list[str] = []

    if project.rera_registration_no:
        pros.append("RERA registered")
    else:
        cons.append("No RERA registration")

    if rs:
        if rs.legal_score >= 80:
            pros.append(f"Strong legal standing (score {rs.legal_score:.0f}/100)")
        elif rs.legal_score < 50:
            cons.append(f"Legal risk flags present (score {rs.legal_score:.0f}/100)")
            cons.extend(rs.legal_flags[:2])

        if rs.developer_score >= 75:
            pros.append(f"Reliable developer track record (score {rs.developer_score:.0f}/100)")
        elif rs.developer_score < 50:
            cons.append(f"Developer risk concerns (score {rs.developer_score:.0f}/100)")
            cons.extend(rs.developer_flags[:2])

        if rs.project_score >= 75:
            pros.append(f"Strong project execution (score {rs.project_score:.0f}/100)")
        elif rs.project_score < 50:
            cons.extend(rs.project_flags[:2])

        if rs.appreciation_3yr_base and rs.appreciation_3yr_base >= 10:
            pros.append(f"High appreciation potential (~{rs.appreciation_3yr_base:.1f}% p.a.)")
        if rs.rental_yield_estimate and rs.rental_yield_estimate >= 3:
            pros.append(f"Attractive rental yield (~{rs.rental_yield_estimate:.1f}%)")

    if project.construction_pct and project.construction_pct >= 85:
        pros.append(f"Near-complete construction ({project.construction_pct:.0f}%)")
    elif project.construction_pct and project.construction_pct < 25:
        cons.append(f"Very early construction stage ({project.construction_pct:.0f}%)")

    return pros[:5], cons[:5]


# ── GET /diligence/curated ────────────────────────────────────────────────────

@router.get(
    "/curated",
    response_model=list[CuratedDeal],
    summary="Curated investment opportunities (personalised if logged in)",
)
async def get_curated(
    city: str | None = Query(None),
    risk_appetite: str | None = Query(None, description="conservative | moderate | aggressive"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # If a city param is provided, override user preference temporarily
    effective_user = current_user
    if city and current_user:
        # Shallow override without mutating the ORM object
        class _FakeUser:
            preferred_cities = [city]
            budget_min = current_user.budget_min
            budget_max = current_user.budget_max
        effective_user = _FakeUser()  # type: ignore[assignment]
    elif city:
        class _AnonUser:
            preferred_cities = [city]
            budget_min = None
            budget_max = None
        effective_user = _AnonUser()  # type: ignore[assignment]

    deals = await get_curated_deals(db=db, user=effective_user, limit=limit)

    return [
        {
            "project_id": d.project_id,
            "project_name": d.project_name,
            "developer_name": d.developer_name,
            "city": d.city,
            "micromarket": d.micromarket,
            "risk_band": d.risk_band,
            "composite_score": d.composite_score,
            "price_psf_min": d.price_psf_min,
            "price_psf_max": d.price_psf_max,
            "appreciation_3yr_base": d.appreciation_3yr_base,
            "appreciation_3yr_bull": d.appreciation_3yr_bull,
            "rental_yield_estimate": d.rental_yield_estimate,
            "rera_registration_no": d.rera_registration_no,
            "possession_date_declared": d.possession_date_declared,
            "construction_pct": d.construction_pct,
            "highlight": d.highlight,
            "confidence_level": d.confidence_level,
        }
        for d in deals
    ]


# ── GET /diligence/compare ────────────────────────────────────────────────────

@router.get(
    "/compare",
    response_model=ComparisonReport,
    summary="Side-by-side comparison of 2–3 projects",
)
async def compare_projects(
    project_ids: list[uuid.UUID] = Query(
        ...,
        description="2 or 3 project UUIDs to compare",
        min_length=2,
        max_length=3,
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if len(project_ids) < 2 or len(project_ids) > 3:
        raise HTTPException(
            status_code=422,
            detail="Provide exactly 2 or 3 project IDs for comparison",
        )

    comparisons: list[ProjectComparison] = []

    for pid in project_ids:
        project = (
            await db.execute(
                select(Project)
                .where(Project.id == pid)
                .options(selectinload(Project.developer))
            )
        ).scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project {pid} not found"
            )

        rs = (
            await db.execute(
                select(RiskScore).where(
                    RiskScore.project_id == pid,
                    RiskScore.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()

        # Trigger on-demand scoring if none exists
        if rs is None:
            rs = await _engine.score_project(pid, db)
            await db.commit()

        appr: AppreciationEstimate | None = None
        try:
            appr_data = await _appreciation.estimate_appreciation(
                project_id=pid,
                city=project.city,
                micromarket=project.micromarket,
                price_psf_current=project.price_psf_min,
                risk_score=rs.composite_score,
                db=db,
            )
            appr = AppreciationEstimate(**appr_data)
        except Exception:
            pass

        pros, cons = _derive_pros_cons(project, rs)

        comparisons.append(
            ProjectComparison(
                project=ProjectSummary(
                    id=project.id,
                    name=project.name,
                    city=project.city,
                    micromarket=project.micromarket,
                    project_type=project.project_type.value,
                    rera_registration_no=project.rera_registration_no,
                    rera_status=project.rera_status.value,
                    oc_status=project.oc_status.value,
                    price_psf_min=project.price_psf_min,
                    price_psf_max=project.price_psf_max,
                    possession_date_declared=project.possession_date_declared,
                    construction_pct=project.construction_pct,
                    total_units=project.total_units,
                ),
                developer=(
                    DeveloperBrief.model_validate(project.developer)
                    if project.developer
                    else None
                ),
                risk_score=RiskScoreDetail.model_validate(rs) if rs else None,
                appreciation=appr,
                pros=pros,
                cons=cons,
            )
        )

    return {"projects": comparisons, "generated_at": datetime.now(timezone.utc)}


# ── POST /diligence/report/{project_id} ──────────────────────────────────────

@router.post(
    "/report/{project_id}",
    summary="Generate due-diligence PDF report (pro subscription required)",
)
async def generate_report(
    project_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Subscription gate — pro or enterprise only
    if current_user.subscription_tier not in (
        SubscriptionTier.pro,
        SubscriptionTier.enterprise,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "PDF report generation requires a Pro or Enterprise subscription. "
                "Upgrade at propiq.in/pricing."
            ),
        )

    # Check Redis cache for an already-generated report.
    # PDF bytes are stored base64-encoded because the main Redis client uses
    # decode_responses=True (string mode).  We use a raw (binary) client for
    # report caching to avoid the encoding overhead.
    import base64

    redis = getattr(request.app.state, "redis", None)
    cache_key = f"report:pdf:{project_id}"
    if redis:
        cached_b64: str | None = await redis.get(cache_key)
        if cached_b64:
            try:
                cached_bytes = base64.b64decode(cached_b64)
                return StreamingResponse(
                    io.BytesIO(cached_bytes),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="propiq-report-{project_id}.pdf"'
                        ),
                        "X-Cache": "HIT",
                    },
                )
            except Exception:
                pass  # Corrupt cache entry — regenerate below

    # Generate PDF (loads all data, scores on-demand, persists to /reports/)
    try:
        pdf_bytes, filename = await _report_generator.generate(project_id, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {exc}",
        ) from exc

    # Cache the PDF as base64 for 7 days
    if redis:
        await redis.set(cache_key, base64.b64encode(pdf_bytes).decode(), ex=_REPORT_CACHE_SECONDS)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-File": filename,
        },
    )
