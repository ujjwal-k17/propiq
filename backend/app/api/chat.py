"""
Chat routes
===========
POST /chat/ask — non-streaming Q&A with PropIQ's AI assistant

Uses Anthropic Claude. Context is enriched with project + developer +
risk score data when a project_id is provided.

Rate limiting (Redis):
  - Free tier:       20 messages/day
  - Pro / Enterprise: unlimited
"""
from __future__ import annotations

import uuid
from datetime import date

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.developer import Developer
from app.models.project import Project
from app.models.risk_score import RiskScore
from app.models.user import SubscriptionTier, User

router = APIRouter(prefix="/chat")

_FREE_TIER_DAILY_LIMIT = 20
_CLAUDE_MODEL = "claude-opus-4-6"

_SYSTEM_BASE = """You are PropIQ's AI assistant — an expert in Indian real estate due diligence.

Your role:
- Help investors and home buyers evaluate real estate projects and developers in India
- Analyse RERA registrations, construction progress, developer track records, and market trends
- Highlight risks prominently and clearly; do not downplay red flags
- Base all answers strictly on the data provided in the context
- Never speculate beyond what the data supports; say "data not available" when needed
- Use Indian property market conventions (₹ INR, sq ft, CAGR %)
- Be concise and structured; use bullet points for risk items

Always end responses that involve risk with: "⚠️ This is an AI-generated analysis for informational purposes only. Conduct independent legal and financial verification before investing."
"""


def _build_project_context(
    project: Project,
    rs: RiskScore | None,
) -> str:
    dev = project.developer
    lines = [
        f"## Project Data Context",
        f"**Project:** {project.name}",
        f"**City / Micromarket:** {project.city} / {project.micromarket}",
        f"**RERA No:** {project.rera_registration_no or 'Not registered'} (Status: {project.rera_status.value})",
        f"**Developer:** {dev.name if dev else 'Unknown'}",
        f"**Total Units:** {project.total_units} | Sold: {project.units_sold or 'N/A'}",
        f"**Price Range:** ₹{project.price_psf_min or 'N/A'} – ₹{project.price_psf_max or 'N/A'} per sq ft",
        f"**Construction Progress:** {project.construction_pct or 'N/A'}%",
        f"**Possession Date (Declared):** {project.possession_date_declared or 'N/A'}",
        f"**Possession Date (Latest):** {project.possession_date_latest or 'N/A'}",
        f"**OC Status:** {project.oc_status.value}",
    ]

    if dev:
        lines += [
            f"",
            f"**Developer Profile:**",
            f"- NCLT Proceedings: {'YES ⚠️' if dev.nclt_proceedings else 'No'}",
            f"- Projects on-time: {dev.projects_on_time_pct or 'N/A'}%",
            f"- Financial Stress: {dev.financial_stress_score or 'N/A'}/100",
            f"- MCA Filing: {dev.mca_filing_status.value}",
            f"- Active Complaints: {dev.active_complaint_count}",
        ]
        if dev.nclt_details:
            lines.append(f"- NCLT Details: {dev.nclt_details}")

    if rs:
        lines += [
            f"",
            f"**Risk Score:** {rs.composite_score:.1f}/100 — {rs.risk_band.value.upper()} RISK",
            f"- Legal: {rs.legal_score:.1f} | Developer: {rs.developer_score:.1f}",
            f"- Project: {rs.project_score:.1f} | Location: {rs.location_score:.1f}",
            f"- Financial: {rs.financial_score:.1f} | Macro: {rs.macro_score:.1f}",
        ]
        all_flags = rs.legal_flags + rs.developer_flags + rs.project_flags
        if all_flags:
            lines.append(f"**Risk Flags:**")
            for flag in all_flags:
                lines.append(f"  - {flag}")
        if rs.appreciation_3yr_base:
            lines.append(
                f"**Appreciation Forecast (3yr base):** {rs.appreciation_3yr_base:.1f}% p.a."
            )
        if rs.rental_yield_estimate:
            lines.append(f"**Rental Yield Estimate:** {rs.rental_yield_estimate:.1f}%")

    return "\n".join(lines)


# ── Request / response schemas ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    project_id: uuid.UUID | None = None
    conversation_history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    project_id: uuid.UUID | None = None


# ── POST /chat/ask ────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Ask PropIQ's AI assistant a due-diligence question",
)
async def ask(
    payload: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # ── Rate limiting (free tier only) ────────────────────────────────────────
    redis = getattr(request.app.state, "redis", None)
    if (
        current_user.subscription_tier == SubscriptionTier.free
        and redis
    ):
        rate_key = f"chat:daily:{current_user.id}:{date.today().isoformat()}"
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 86400)  # 24-hour TTL
        if count > _FREE_TIER_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Free tier limit: {_FREE_TIER_DAILY_LIMIT} messages per day. "
                    "Upgrade to Pro for unlimited access."
                ),
            )

    # ── Fetch project context if provided ─────────────────────────────────────
    system_prompt = _SYSTEM_BASE
    sources: list[str] = []

    if payload.project_id:
        project = (
            await db.execute(
                select(Project)
                .where(Project.id == payload.project_id)
                .options(selectinload(Project.developer))
            )
        ).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        rs = (
            await db.execute(
                select(RiskScore).where(
                    RiskScore.project_id == payload.project_id,
                    RiskScore.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()

        context = _build_project_context(project, rs)
        system_prompt = f"{_SYSTEM_BASE}\n\n{context}"

        sources.append(f"Project: {project.name}")
        if project.rera_registration_no:
            sources.append(f"RERA: {project.rera_registration_no}")
        if project.developer:
            sources.append(f"Developer: {project.developer.name}")
        if rs:
            sources.append(f"Risk Score: {rs.composite_score:.1f}/100 ({rs.risk_band.value})")

    # ── Build message history ─────────────────────────────────────────────────
    messages = [
        {"role": m.role, "content": m.content}
        for m in payload.conversation_history
        if m.role in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": payload.message})

    # ── Call Anthropic ────────────────────────────────────────────────────────
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured. Set ANTHROPIC_API_KEY in .env",
        )

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=messages,
        )
        answer = response.content[0].text
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {exc}",
        )

    return {
        "response": answer,
        "sources": sources,
        "project_id": payload.project_id,
    }
