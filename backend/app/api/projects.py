"""
Projects routes
===============
GET  /projects/                    — filtered list with current risk score
GET  /projects/{id}                — full detail (developer, score, txns, complaints, news, appreciation)
GET  /projects/{id}/risk-score     — current risk score; triggers scoring if absent
GET  /projects/{id}/transactions   — transactions + price stats
GET  /projects/{id}/complaints     — complaint summary
POST /projects/{id}/refresh        — re-scrape + re-score (rate-limited per project per 6 h)
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer
from app.models.news_item import NewsItem
from app.models.project import Project, ProjectType, ReraStatus
from app.models.risk_score import RiskScore
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.project import (
    AppreciationEstimate,
    ComplaintBrief,
    ComplaintSummary,
    DeveloperBrief,
    NewsItemBrief,
    ProjectDetail,
    ProjectWithScore,
    RiskScoreDetail,
    TransactionBrief,
    TransactionStats,
)
from app.schemas.risk_score import RiskScoreResponse
from app.services.appreciation_model import AppreciationModel
from app.services.risk_engine import RiskEngine
from app.scrapers.pipeline import DataPipeline
from app.services.alert_manager import alert_manager, take_snapshot

router = APIRouter(prefix="/projects")
_engine = RiskEngine()
_appreciation = AppreciationModel()
_pipeline = DataPipeline()

_REFRESH_TTL_SECONDS = 6 * 3600  # 6 hours


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(project_id: uuid.UUID, db: AsyncSession) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _current_risk_score(
    project_id: uuid.UUID, db: AsyncSession
) -> RiskScore | None:
    return (
        await db.execute(
            select(RiskScore).where(
                RiskScore.project_id == project_id,
                RiskScore.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()


def _build_complaint_summary(
    complaints: list[Complaint],
) -> ComplaintSummary:
    total = len(complaints)
    pending = sum(1 for c in complaints if c.status == ComplaintStatus.pending)
    resolved = sum(1 for c in complaints if c.status == ComplaintStatus.resolved)
    dismissed = sum(1 for c in complaints if c.status == ComplaintStatus.dismissed)
    by_category: dict[str, int] = {}
    for c in complaints:
        key = c.category or "other"
        by_category[key] = by_category.get(key, 0) + 1
    return ComplaintSummary(
        total=total,
        pending=pending,
        resolved=resolved,
        dismissed=dismissed,
        by_category=by_category,
        complaints=[ComplaintBrief.model_validate(c) for c in complaints[:20]],
    )


# ── GET /projects/ ────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[ProjectWithScore],
    summary="List projects with optional filters and current risk score",
)
async def list_projects(
    city: str | None = Query(None),
    micromarket: str | None = Query(None),
    project_type: str | None = Query(None),
    risk_band: str | None = Query(None, description="low | medium | high | critical"),
    min_price: float | None = Query(None, description="Min price per sq ft"),
    max_price: float | None = Query(None, description="Max price per sq ft"),
    possession_before: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # Join Project with current RiskScore (outer join so unscored projects appear)
    q = (
        select(Project, RiskScore, Developer.name.label("developer_name"))
        .outerjoin(
            RiskScore,
            and_(
                RiskScore.project_id == Project.id,
                RiskScore.is_current.is_(True),
            ),
        )
        .outerjoin(Developer, Developer.id == Project.developer_id)
    )

    if city:
        q = q.where(Project.city.ilike(f"%{city}%"))
    if micromarket:
        q = q.where(Project.micromarket.ilike(f"%{micromarket}%"))
    if project_type:
        try:
            q = q.where(Project.project_type == ProjectType(project_type))
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"project_type must be one of: {[t.value for t in ProjectType]}",
            )
    if risk_band:
        q = q.where(RiskScore.risk_band == risk_band)
    if min_price is not None:
        q = q.where(Project.price_psf_min >= min_price)
    if max_price is not None:
        q = q.where(Project.price_psf_max <= max_price)
    if possession_before:
        q = q.where(Project.possession_date_declared <= possession_before)

    # Order by risk score descending (highest score = safest first), NULLs last
    q = (
        q.order_by(RiskScore.composite_score.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )

    rows = (await db.execute(q)).all()

    result = []
    for project, risk_score, dev_name in rows:
        d = {
            "id": project.id,
            "name": project.name,
            "city": project.city,
            "micromarket": project.micromarket,
            "project_type": project.project_type.value,
            "rera_registration_no": project.rera_registration_no,
            "rera_status": project.rera_status.value,
            "oc_status": project.oc_status.value,
            "price_psf_min": project.price_psf_min,
            "price_psf_max": project.price_psf_max,
            "possession_date_declared": project.possession_date_declared,
            "construction_pct": project.construction_pct,
            "total_units": project.total_units,
            "developer_name": dev_name,
            "risk_score": risk_score if risk_score else None,
        }
        result.append(d)

    return result


# ── GET /projects/{id} ────────────────────────────────────────────────────────

@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Full project detail with related data",
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Load project + developer
    project_row = (
        await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.developer))
        )
    ).scalar_one_or_none()
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")

    # Current risk score
    rs = await _current_risk_score(project_id, db)

    # Last 10 transactions
    txns = list(
        (
            await db.execute(
                select(Transaction)
                .where(Transaction.project_id == project_id)
                .order_by(Transaction.transaction_date.desc())
                .limit(10)
            )
        ).scalars()
    )

    # All complaints
    complaints = list(
        (
            await db.execute(
                select(Complaint).where(Complaint.project_id == project_id)
            )
        ).scalars()
    )

    # Last 5 news items
    news = list(
        (
            await db.execute(
                select(NewsItem)
                .where(NewsItem.project_id == project_id)
                .order_by(NewsItem.published_at.desc().nullslast())
                .limit(5)
            )
        ).scalars()
    )

    # Appreciation estimate
    appreciation: AppreciationEstimate | None = None
    if rs:
        try:
            appr_data = await _appreciation.estimate_appreciation(
                project_id=project_id,
                city=project_row.city,
                micromarket=project_row.micromarket,
                price_psf_current=project_row.price_psf_min,
                risk_score=rs.composite_score,
                db=db,
            )
            appreciation = AppreciationEstimate(**appr_data)
        except Exception:
            pass  # non-critical

    return {
        "id": project_row.id,
        "name": project_row.name,
        "city": project_row.city,
        "micromarket": project_row.micromarket,
        "project_type": project_row.project_type.value,
        "rera_registration_no": project_row.rera_registration_no,
        "rera_status": project_row.rera_status.value,
        "oc_status": project_row.oc_status.value,
        "total_units": project_row.total_units,
        "units_sold": project_row.units_sold,
        "carpet_area_min": project_row.carpet_area_min,
        "carpet_area_max": project_row.carpet_area_max,
        "price_psf_min": project_row.price_psf_min,
        "price_psf_max": project_row.price_psf_max,
        "possession_date_declared": project_row.possession_date_declared,
        "possession_date_latest": project_row.possession_date_latest,
        "construction_pct": project_row.construction_pct,
        "latitude": project_row.latitude,
        "longitude": project_row.longitude,
        "amenities": project_row.amenities,
        "source_url": project_row.source_url,
        "created_at": project_row.created_at,
        "updated_at": project_row.updated_at,
        "developer": (
            DeveloperBrief.model_validate(project_row.developer)
            if project_row.developer
            else None
        ),
        "risk_score": RiskScoreDetail.model_validate(rs) if rs else None,
        "recent_transactions": [TransactionBrief.model_validate(t) for t in txns],
        "complaint_summary": _build_complaint_summary(complaints),
        "recent_news": [NewsItemBrief.model_validate(n) for n in news],
        "appreciation": appreciation,
    }


# ── GET /projects/{id}/risk-score ─────────────────────────────────────────────

@router.get(
    "/{project_id}/risk-score",
    response_model=RiskScoreResponse,
    summary="Current risk score; triggers scoring if not yet computed",
)
async def get_risk_score(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskScore:
    await _get_or_404(project_id, db)

    rs = await _current_risk_score(project_id, db)
    if rs is None:
        # Score on demand
        rs = await _engine.score_project(project_id, db)
        await db.commit()

    return rs


# ── GET /projects/{id}/transactions ───────────────────────────────────────────

@router.get(
    "/{project_id}/transactions",
    response_model=TransactionStats,
    summary="Transaction history and price stats",
)
async def get_transactions(
    project_id: uuid.UUID,
    months_back: int = Query(12, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_or_404(project_id, db)

    cutoff = date.today() - timedelta(days=months_back * 30)
    txns = list(
        (
            await db.execute(
                select(Transaction)
                .where(
                    Transaction.project_id == project_id,
                    Transaction.transaction_date >= cutoff,
                )
                .order_by(Transaction.transaction_date.desc())
            )
        ).scalars()
    )

    avg_psf: float | None = None
    price_change_pct: float | None = None

    if txns:
        prices = [t.price_psf for t in txns if t.price_psf]
        if prices:
            avg_psf = sum(prices) / len(prices)

        # 12-month change: compare first half vs second half of the period
        if len(txns) >= 4:
            mid = len(txns) // 2
            early = [t.price_psf for t in txns[mid:] if t.price_psf]  # older
            recent = [t.price_psf for t in txns[:mid] if t.price_psf]  # newer
            if early and recent:
                early_avg = sum(early) / len(early)
                recent_avg = sum(recent) / len(recent)
                if early_avg > 0:
                    price_change_pct = round(
                        (recent_avg - early_avg) / early_avg * 100, 2
                    )

    return {
        "avg_price_psf": round(avg_psf, 2) if avg_psf else None,
        "price_change_pct_12m": price_change_pct,
        "total_count": len(txns),
        "transactions": [TransactionBrief.model_validate(t) for t in txns],
    }


# ── GET /projects/{id}/complaints ─────────────────────────────────────────────

@router.get(
    "/{project_id}/complaints",
    response_model=ComplaintSummary,
    summary="Complaint summary and list",
)
async def get_complaints(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_or_404(project_id, db)

    complaints = list(
        (
            await db.execute(
                select(Complaint)
                .where(Complaint.project_id == project_id)
                .order_by(Complaint.complaint_date.desc().nullslast())
            )
        ).scalars()
    )
    return _build_complaint_summary(complaints)


# ── POST /projects/{id}/refresh ───────────────────────────────────────────────

@router.post(
    "/{project_id}/refresh",
    response_model=RiskScoreResponse,
    summary="Re-scrape and re-score a project (rate-limited: once per 6 h)",
)
async def refresh_project(
    project_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskScore:
    project = await _get_or_404(project_id, db)

    # Rate limit: 1 refresh per project per 6 hours via Redis
    redis = getattr(request.app.state, "redis", None)
    rate_key = f"refresh:project:{project_id}"
    if redis:
        last = await redis.get(rate_key)
        if last:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="This project was refreshed recently. Try again in 6 hours.",
                headers={"Retry-After": str(_REFRESH_TTL_SECONDS)},
            )

    # ── Snapshot before pipeline ──────────────────────────────────────────────
    complaint_count_before = (
        await db.execute(
            select(func.count(Complaint.id)).where(Complaint.project_id == project_id)
        )
    ).scalar_one() or 0
    old_band = await _current_risk_score(project_id, db)
    snapshot = take_snapshot(project, complaint_count_before, old_band.risk_band.value if old_band else None)

    # ── Run pipeline ──────────────────────────────────────────────────────────
    result = await _pipeline.refresh_single_project(project_id, db)
    if not result.success:
        errors = [s.error for s in result.stages if s.error]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Refresh partially failed: {errors}",
        )

    rs = await _current_risk_score(project_id, db)
    if rs is None:
        rs = await _engine.score_project(project_id, db)
        await db.commit()

    # ── Detect changes and emit alerts ────────────────────────────────────────
    await db.refresh(project)  # reload after pipeline mutations
    complaint_count_after = (
        await db.execute(
            select(func.count(Complaint.id)).where(Complaint.project_id == project_id)
        )
    ).scalar_one() or 0

    try:
        await alert_manager.emit_project_changes(
            before=snapshot,
            project=project,
            complaint_count_after=complaint_count_after,
            risk_score_after=rs,
            db=db,
            redis=redis,
        )
        await db.commit()
    except Exception as exc:
        # Alerts are best-effort — never block the refresh response
        import logging
        logging.getLogger("propiq.alerts").warning("Alert emission failed: %s", exc)

    # Set rate-limit key
    if redis:
        await redis.set(rate_key, "1", ex=_REFRESH_TTL_SECONDS)

    return rs
