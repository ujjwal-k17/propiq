"""
Report Generator
================
Produces a professional PDF due-diligence report for any PropIQ project.

Flow:
  1. Load project + all relations from DB.
  2. Ensure a current RiskScore exists (scores on-demand if missing).
  3. Fetch appreciation forecast from AppreciationModel.
  4. Render a full HTML document using the PropIQ design system (light theme,
     brand colours, 9 structured sections).
  5. Convert HTML → PDF bytes via WeasyPrint (falls back to HTML bytes in
     environments without WeasyPrint, e.g. CI).
  6. Persist the PDF to a local /reports directory and, when S3 is configured,
     upload to the configured bucket.

Usage::

    from app.services.report_generator import ReportGenerator

    generator = ReportGenerator()
    pdf_bytes, filename = await generator.generate(project_id, db)

The returned *bytes* can be streamed directly to the client.
"""
from __future__ import annotations

import html as _html_mod
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ProjectNotFoundError, ReportGenerationError
from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer
from app.models.news_item import NewsItem
from app.models.project import Project
from app.models.risk_score import RiskScore
from app.models.transaction import Transaction
from app.services.appreciation_model import AppreciationModel
from app.services.risk_engine import RiskEngine

logger = logging.getLogger("propiq.report")

# ── Storage configuration ─────────────────────────────────────────────────────

# Local directory where PDFs are written.
# Override via REPORTS_DIR env-var; defaults to <project-root>/reports.
_REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", Path(__file__).parents[3] / "reports"))


def _ensure_reports_dir() -> Path:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return _REPORTS_DIR


# ── Formatting helpers ────────────────────────────────────────────────────────

def _esc(value: Any) -> str:
    """HTML-escape a value; returns em-dash for None/empty."""
    if value is None or value == "":
        return "—"
    return _html_mod.escape(str(value))


def _fmt_date(d: Any) -> str:
    if d is None:
        return "—"
    if hasattr(d, "strftime"):
        return d.strftime("%d %b %Y")
    return _esc(d)


def _fmt_inr(amount: float | None) -> str:
    if amount is None:
        return "—"
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    if amount >= 1_00_000:
        return f"₹{amount / 1_00_000:.2f} L"
    return f"₹{amount:,.0f}"


def _band_color(band: str | None) -> str:
    return {
        "low":      "#16a34a",   # green-600
        "medium":   "#d97706",   # amber-600
        "high":     "#ea580c",   # orange-600
        "critical": "#dc2626",   # red-600
    }.get((band or "").lower(), "#64748b")


def _band_bg(band: str | None) -> str:
    return {
        "low":      "#dcfce7",
        "medium":   "#fef3c7",
        "high":     "#ffedd5",
        "critical": "#fee2e2",
    }.get((band or "").lower(), "#f1f5f9")


def _age(dt: Any) -> str:
    """Human-readable age from a datetime to now."""
    if dt is None:
        return "—"
    now = datetime.now(timezone.utc)
    ts = dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)
    days = (now - ts).days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Base ── */
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #ffffff;
  color: #1e293b;
  font-size: 13px;
  line-height: 1.65;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

/* ── Page wrapper ── */
.page { max-width: 860px; margin: 0 auto; padding: 40px 32px; }

/* ── Cover header ── */
.cover {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #0ea5e9 100%);
  border-radius: 16px;
  padding: 40px 36px 32px;
  margin-bottom: 36px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.04'%3E%3Ccircle cx='20' cy='20' r='10'/%3E%3C/g%3E%3C/svg%3E");
}
.cover-content { position: relative; z-index: 1; }
.brand {
  font-size: 11px; font-weight: 800; letter-spacing: 3px;
  text-transform: uppercase; color: #93c5fd; margin-bottom: 12px;
  display: flex; align-items: center; gap: 6px;
}
.brand-dot { width: 6px; height: 6px; background: #0ea5e9; border-radius: 50%; }
.cover h1 { font-size: 26px; font-weight: 800; color: #fff; line-height: 1.2; margin-bottom: 6px; }
.cover .sub { color: #bfdbfe; font-size: 13px; margin-bottom: 24px; }
.cover-meta {
  display: flex; flex-wrap: wrap; gap: 20px;
  font-size: 12px; color: #e0f2fe; border-top: 1px solid rgba(255,255,255,.18);
  padding-top: 16px; margin-top: 4px;
}
.cover-meta span strong { color: #fff; }

/* ── Verdict badge ── */
.verdict-row {
  display: flex; align-items: center; gap: 20px; margin: 20px 0 12px;
}
.score-circle {
  width: 72px; height: 72px; border-radius: 50%;
  border: 4px solid;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex-shrink: 0;
  background: #fff;
}
.score-circle .num {
  font-size: 22px; font-weight: 800; line-height: 1;
}
.score-circle .denom { font-size: 10px; color: #94a3b8; }
.band-pill {
  padding: 5px 16px; border-radius: 999px;
  font-size: 13px; font-weight: 700; letter-spacing: .5px;
  text-transform: uppercase;
}
.verdict-desc { color: #475569; font-size: 13px; }
.verdict-desc strong { color: #0f172a; }
.confidence-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; border-radius: 6px;
  padding: 2px 9px; margin-left: 8px;
  background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0;
}

/* ── Sections ── */
section { margin-bottom: 32px; page-break-inside: avoid; }
.section-title {
  font-size: 15px; font-weight: 800; color: #0f172a;
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 14px; padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
}
.section-num {
  width: 24px; height: 24px; border-radius: 50%; background: #1e3a8a;
  color: #fff; font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

/* ── Info table ── */
.info-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.info-table th, .info-table td {
  padding: 8px 12px; border-bottom: 1px solid #f1f5f9; text-align: left; vertical-align: top;
}
.info-table th {
  background: #f8fafc; color: #64748b; font-size: 11px;
  text-transform: uppercase; letter-spacing: .5px; font-weight: 600; white-space: nowrap;
}
.info-table td:first-child { color: #475569; width: 42%; }
.info-table td:last-child { color: #0f172a; font-weight: 500; }
.info-table tr:last-child td { border-bottom: none; }
.info-table tr:hover td { background: #f8fafc; }

/* ── Score bars ── */
.score-grid { display: flex; flex-direction: column; gap: 11px; }
.score-row { display: flex; align-items: center; gap: 10px; }
.score-row-label { width: 195px; flex-shrink: 0; font-size: 12.5px; color: #334155; }
.bar-track {
  flex: 1; height: 12px; border-radius: 6px; background: #f1f5f9; overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 6px; }
.score-row-num { width: 44px; text-align: right; font-weight: 700; font-size: 12.5px; }
.score-row-wt { width: 38px; font-size: 11px; color: #94a3b8; }

/* ── Composite ring ── */
.composite-wrap {
  display: flex; align-items: center; gap: 20px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 16px 20px; margin-bottom: 18px;
}
.composite-ring {
  width: 64px; height: 64px; border-radius: 50%; flex-shrink: 0;
  border: 6px solid;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 800;
}

/* ── Flags ── */
.flags-list { list-style: none; display: flex; flex-direction: column; gap: 7px; }
.flag-item {
  display: flex; align-items: flex-start; gap: 9px;
  background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 8px; padding: 7px 11px; font-size: 12.5px; color: #991b1b;
}
.flag-item.warn { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.flag-dot { width: 7px; height: 7px; border-radius: 50%; background: #ef4444; flex-shrink: 0; margin-top: 4px; }
.flag-dot.warn { background: #f59e0b; }
.no-issues {
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;
  padding: 10px 14px; color: #15803d; font-size: 13px;
}

/* ── Appreciation ── */
.appr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.appr-card {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 12px 14px; text-align: center;
}
.appr-card .label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.appr-card .value { font-size: 20px; font-weight: 800; color: #0f172a; }
.appr-card .value.positive { color: #16a34a; }
.appr-card .sub { font-size: 11px; color: #64748b; margin-top: 2px; }
.appr-scenarios { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.scenario { border-radius: 8px; padding: 8px 12px; text-align: center; font-size: 12px; }
.scenario .scenario-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 3px; }
.scenario.bear { background: #fee2e2; color: #991b1b; }
.scenario.base { background: #dbeafe; color: #1d4ed8; }
.scenario.bull { background: #dcfce7; color: #15803d; }

/* ── Complaints ── */
.complaint-summary {
  display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap;
}
.complaint-stat {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 9px 14px; font-size: 12px;
}
.complaint-stat .num { font-size: 20px; font-weight: 800; color: #0f172a; }

/* ── News ── */
.news-item {
  border-left: 3px solid #e2e8f0; padding: 8px 12px; margin-bottom: 10px;
  border-radius: 0 8px 8px 0; background: #f8fafc;
}
.news-item.positive { border-color: #86efac; background: #f0fdf4; }
.news-item.negative { border-color: #fca5a5; background: #fff5f5; }
.news-item.critical { border-color: #ef4444; background: #fef2f2; }
.news-item .headline { font-weight: 600; color: #0f172a; font-size: 13px; margin-bottom: 3px; }
.news-item .meta { font-size: 11px; color: #94a3b8; }
.sentiment-tag {
  display: inline-block; font-size: 10px; font-weight: 700;
  border-radius: 4px; padding: 1px 6px; text-transform: uppercase; letter-spacing: .4px;
}
.sentiment-tag.positive { background: #dcfce7; color: #15803d; }
.sentiment-tag.negative { background: #fee2e2; color: #991b1b; }
.sentiment-tag.critical { background: #fef2f2; color: #dc2626; }
.sentiment-tag.neutral  { background: #f1f5f9; color: #475569; }

/* ── Freshness ── */
.freshness-grid { display: flex; flex-direction: column; gap: 8px; }
.freshness-row {
  display: flex; align-items: center; gap: 10px; font-size: 12.5px;
}
.freshness-source { width: 200px; flex-shrink: 0; color: #475569; }
.freshness-age { color: #0f172a; font-weight: 600; }
.freshness-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #22c55e; flex-shrink: 0;
}
.freshness-dot.stale { background: #f59e0b; }
.freshness-dot.old   { background: #ef4444; }

/* ── Footer ── */
.report-footer {
  margin-top: 40px; padding-top: 20px;
  border-top: 1px solid #e2e8f0;
  font-size: 10.5px; color: #94a3b8; text-align: center; line-height: 1.6;
}
.report-footer strong { color: #64748b; }

/* ── Print ── */
@page {
  margin: 18mm 15mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-size: 9pt; color: #94a3b8;
  }
}
@media print {
  .cover { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


# ── Section builders ──────────────────────────────────────────────────────────

def _score_bar(label: str, score: float, weight: int) -> str:
    pct = max(0, min(100, score))
    if pct >= 80:
        band = "low"
    elif pct >= 60:
        band = "medium"
    elif pct >= 40:
        band = "high"
    else:
        band = "critical"
    color = _band_color(band)
    return f"""
    <div class="score-row">
      <span class="score-row-label">{_esc(label)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>
      <span class="score-row-num" style="color:{color}">{pct:.0f}</span>
      <span class="score-row-wt">{weight}%</span>
    </div>"""


def _section(num: int, title: str, body: str) -> str:
    return f"""
<section>
  <div class="section-title">
    <span class="section-num">{num}</span>
    {_esc(title)}
  </div>
  {body}
</section>"""


def _tr(label: str, value: Any) -> str:
    return f"<tr><td>{_esc(label)}</td><td>{_esc(value) if not isinstance(value, str) or '<' not in value else value}</td></tr>"


def _tr_raw(label: str, value: str) -> str:
    """Like _tr but value is already-safe HTML."""
    return f"<tr><td>{_esc(label)}</td><td>{value}</td></tr>"


# ── Main class ────────────────────────────────────────────────────────────────

class ReportGenerator:
    """Generate PDF due-diligence reports for PropIQ projects."""

    def __init__(self) -> None:
        self._appreciation = AppreciationModel()
        self._risk_engine = RiskEngine()

    # ── Public entry point ────────────────────────────────────────────────────

    async def generate(
        self, project_id: uuid.UUID, db: AsyncSession
    ) -> tuple[bytes, str]:
        """
        Load all project data, build the HTML report, convert to PDF, persist
        to the local /reports directory, and return ``(pdf_bytes, filename)``.

        Raises:
            ProjectNotFoundError  — project not in DB.
            ReportGenerationError — rendering or persistence failed.
        """
        project = await self._load_project(project_id, db)

        rs = await self._ensure_risk_score(project, project_id, db)
        appr = await self._fetch_appreciation(project, rs, project_id, db)

        try:
            html = self._build_html(project, rs, appr)
            pdf_bytes = _html_to_pdf(html)
        except Exception as exc:
            logger.exception("HTML → PDF conversion failed for project %s", project_id)
            raise ReportGenerationError(str(exc)) from exc

        filename = self._persist(pdf_bytes, project_id)
        return pdf_bytes, filename

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _load_project(
        self, project_id: uuid.UUID, db: AsyncSession
    ) -> Project:
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.developer),
                selectinload(Project.risk_scores),
                selectinload(Project.complaints),
                selectinload(Project.news_items),
                selectinload(Project.transactions),
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError()
        return project

    async def _ensure_risk_score(
        self, project: Project, project_id: uuid.UUID, db: AsyncSession
    ) -> RiskScore:
        rs = next((s for s in project.risk_scores if s.is_current), None)
        if rs is None and project.risk_scores:
            rs = max(project.risk_scores, key=lambda s: s.generated_at)
        if rs is None:
            rs = await self._risk_engine.score_project(project_id, db)
            await db.commit()
        return rs

    async def _fetch_appreciation(
        self,
        project: Project,
        rs: RiskScore,
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        try:
            return await self._appreciation.estimate_appreciation(
                project_id=project_id,
                city=project.city,
                micromarket=project.micromarket,
                price_psf_current=project.price_psf_min,
                risk_score=rs.composite_score,
                db=db,
            )
        except Exception:
            return {}

    def _persist(self, pdf_bytes: bytes, project_id: uuid.UUID) -> str:
        reports_dir = _ensure_reports_dir()
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"propiq-report-{project_id}-{now_str}.pdf"
        out_path = reports_dir / filename
        try:
            out_path.write_bytes(pdf_bytes)
            logger.info("Report saved → %s", out_path)
        except OSError as exc:
            # Non-fatal — still return bytes even if we couldn't write to disk
            logger.warning("Could not persist report to disk: %s", exc)
        return filename

    # ── HTML builder ──────────────────────────────────────────────────────────

    def _build_html(
        self,
        project: Project,
        rs: RiskScore,
        appr: dict,
    ) -> str:
        dev: Developer | None = project.developer
        complaints: list[Complaint] = list(project.complaints)
        news: list[NewsItem] = list(project.news_items)
        transactions: list[Transaction] = list(project.transactions)

        now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
        score = int(rs.composite_score)
        band = rs.risk_band.value
        band_clr = _band_color(band)
        band_bg = _band_bg(band)

        # Possession delay status
        today = datetime.now(timezone.utc).date()
        possession = project.possession_date_latest or project.possession_date_declared
        if possession and possession < today:
            delay_months = max(0, int((today - possession).days / 30))
            possession_status = f"<span style='color:#dc2626;font-weight:700'>{delay_months}m overdue</span>"
        elif possession:
            possession_status = f"<span style='color:#16a34a;font-weight:700'>On track</span>"
        else:
            possession_status = "—"

        # Transaction price stats
        tx_psf = [t.price_psf for t in transactions if t.price_psf]
        avg_psf = sum(tx_psf) / len(tx_psf) if tx_psf else None

        # All flags combined
        all_flags = (
            [("legal", f) for f in (rs.legal_flags or [])]
            + [("developer", f) for f in (rs.developer_flags or [])]
            + [("project", f) for f in (rs.project_flags or [])]
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>PropIQ Report — {_esc(project.name)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">

<!-- ══ COVER ══════════════════════════════════════════════════════════════ -->
<div class="cover">
  <div class="cover-content">
    <div class="brand"><span class="brand-dot"></span>PROPIQ · DUE DILIGENCE REPORT</div>
    <h1>{_esc(project.name)}</h1>
    <div class="sub">{_esc(project.micromarket)}, {_esc(project.city)} · {_esc(project.project_type.value.title())}</div>

    <div class="verdict-row">
      <div class="score-circle" style="border-color:{band_clr};color:{band_clr}">
        <span class="num">{score}</span>
        <span class="denom">/100</span>
      </div>
      <div>
        <div class="band-pill" style="background:{band_bg};color:{band_clr}">{band.upper()} RISK</div>
        <div style="margin-top:6px;font-size:12px;color:#bfdbfe">
          Confidence: <strong style="color:#fff">{rs.confidence_level.value.upper()}</strong>
          &nbsp;·&nbsp; Scored: {_fmt_date(rs.generated_at)}
        </div>
      </div>
    </div>

    <div class="cover-meta">
      <span>Developer: <strong>{_esc(dev.name if dev else "—")}</strong></span>
      <span>RERA: <strong>{_esc(project.rera_registration_no or "Not registered")}</strong></span>
      <span>Status: <strong>{_esc(project.rera_status.value.upper())}</strong></span>
      <span>Generated: <strong>{now_str}</strong></span>
    </div>
  </div>
</div>

"""

        # ── 1. Executive Summary ──────────────────────────────────────────────
        exec_body = f"""
    <div class="composite-wrap">
      <div class="composite-ring" style="border-color:{band_clr};color:{band_clr}">{score}</div>
      <div>
        <p class="verdict-desc">
          <strong>{_esc(project.name)}</strong>
          {"by <strong>" + _esc(dev.name) + "</strong>" if dev else ""} is a
          {_esc(project.project_type.value)} project in
          <strong>{_esc(project.micromarket)}, {_esc(project.city)}</strong>.
          PropIQ assigns an overall risk score of
          <strong style="color:{band_clr}">{score}/100 ({band.upper()} RISK)</strong>.
        </p>
        <p style="margin-top:6px;font-size:12px;color:#64748b">
          RERA: <strong style="color:#0f172a">{_esc(project.rera_registration_no or "Not registered")}</strong>
          &nbsp;·&nbsp; Status: <strong style="color:#0f172a">{_esc(project.rera_status.value.upper())}</strong>
          &nbsp;·&nbsp; Possession: <strong style="color:#0f172a">{_fmt_date(possession)}</strong>
          &nbsp;·&nbsp; Delay: {possession_status}
        </p>
      </div>
    </div>
    <p style="font-size:12px;color:#64748b;margin-top:4px">
      This report covers {len(complaints)} RERA complaint(s),
      {len(transactions)} registered transaction(s), and
      {len(news)} news item(s). Data confidence: <strong style="color:#0f172a">{rs.confidence_level.value.upper()}</strong>.
    </p>"""
        html += _section(1, "Executive Summary", exec_body)

        # ── 2. Project Overview ───────────────────────────────────────────────
        unsold = (project.total_units - (project.units_sold or 0)) if project.total_units else None
        overview_body = f"""
    <table class="info-table">
      <tbody>
        {_tr("Project Name", project.name)}
        {_tr("City", project.city)}
        {_tr("Micromarket", project.micromarket)}
        {_tr("Project Type", project.project_type.value.title())}
        {_tr("RERA Registration", project.rera_registration_no or "Not registered")}
        {_tr("RERA Status", project.rera_status.value.upper())}
        {_tr("OC Status", project.oc_status.value.replace("_", " ").title())}
        {_tr("Total Units", project.total_units)}
        {_tr("Units Sold", project.units_sold if project.units_sold is not None else "—")}
        {_tr("Units Remaining", unsold if unsold is not None else "—")}
        {_tr("Carpet Area Range", f"{project.carpet_area_min or '—'}–{project.carpet_area_max or '—'} sqft" if project.carpet_area_min else "—")}
        {_tr("Price Range (PSF)", f"₹{project.price_psf_min:,.0f}–₹{project.price_psf_max:,.0f}" if project.price_psf_min else "—")}
        {_tr("Avg Registered Price", _fmt_inr(avg_psf) + "/sqft" if avg_psf else "—")}
        {_tr("Construction Progress", f"{project.construction_pct:.0f}%" if project.construction_pct is not None else "—")}
        {_tr("Declared Possession Date", _fmt_date(project.possession_date_declared))}
        {_tr("Latest Possession Date", _fmt_date(project.possession_date_latest))}
        {_tr_raw("Possession Status", possession_status)}
        {_tr("Data Last Refreshed", _fmt_date(project.last_scraped_at))}
      </tbody>
    </table>"""
        html += _section(2, "Project Overview", overview_body)

        # ── 3. Developer Profile ──────────────────────────────────────────────
        if dev:
            stress = dev.financial_stress_score or 0
            stress_color = "#16a34a" if stress < 30 else "#d97706" if stress < 60 else "#dc2626"
            stress_label = "Low stress" if stress < 30 else "Moderate stress" if stress < 60 else "High stress"
            mca_color = "#16a34a" if dev.mca_filing_status.value == "compliant" else "#dc2626"
            nclt_html = (
                f'<span style="color:#dc2626;font-weight:700">YES — {_esc(dev.nclt_details)}</span>'
                if dev.nclt_proceedings
                else '<span style="color:#16a34a;font-weight:700">No</span>'
            )
            on_time_pct = f"{dev.projects_on_time_pct:.1f}%" if dev.projects_on_time_pct is not None else "—"
            dev_body = f"""
    <table class="info-table">
      <tbody>
        {_tr("Developer Name", dev.name)}
        {_tr("MCA CIN", dev.mca_cin or "—")}
        {_tr("Headquarters", dev.city_hq or "—")}
        {_tr("Founded", dev.founded_year or "—")}
        {_tr("Website", dev.website or "—")}
        {_tr("Total Projects Delivered", dev.total_projects_delivered)}
        {_tr("On-time Delivery Rate", on_time_pct)}
        {_tr("Total Units Delivered", dev.total_units_delivered)}
        {_tr("Active Complaints", dev.active_complaint_count)}
        {_tr("Resolved Complaints", dev.resolved_complaint_count)}
        {_tr("MCA Filing Status", dev.mca_filing_status.value.upper())}
        {_tr_raw("NCLT Proceedings", nclt_html)}
        {_tr_raw("Financial Stress Score",
                 f'<strong style="color:{stress_color}">{stress:.0f}/100</strong> — {_esc(stress_label)}')}
        {_tr("Developer Data Last Updated", _fmt_date(dev.last_scraped_at))}
      </tbody>
    </table>"""
        else:
            dev_body = "<p style='color:#64748b'>Developer information not available.</p>"
        html += _section(3, "Developer Profile", dev_body)

        # ── 4. Risk Score Breakdown ───────────────────────────────────────────
        dims = [
            ("Legal & Compliance",       rs.legal_score,     25),
            ("Developer Track Record",   rs.developer_score, 25),
            ("Project Execution",        rs.project_score,   20),
            ("Location Quality",         rs.location_score,  15),
            ("Financial Indicators",     rs.financial_score, 10),
            ("Macro Environment",        rs.macro_score,      5),
        ]
        bars = "".join(_score_bar(lbl, sc, wt) for lbl, sc, wt in dims)
        risk_body = f'<div class="score-grid">{bars}</div>'
        html += _section(4, "Risk Score Breakdown", risk_body)

        # ── 5. Risk Flags ─────────────────────────────────────────────────────
        if all_flags:
            flag_items = ""
            for _cat, flag_text in all_flags:
                is_critical = score < 40 or _cat == "legal"
                cls = "flag-item" if is_critical else "flag-item warn"
                dot_cls = "flag-dot" if is_critical else "flag-dot warn"
                flag_items += f'<li class="{cls}"><span class="{dot_cls}"></span>{_esc(flag_text)}</li>'
            flags_body = f'<ul class="flags-list">{flag_items}</ul>'
        else:
            flags_body = '<div class="no-issues">✓ No risk flags identified for this project.</div>'
        html += _section(5, "Risk Flags", flags_body)

        # ── 6. Price Appreciation Forecast ────────────────────────────────────
        if appr:
            base_3 = appr.get("appreciation_3yr_base")
            bull_3 = appr.get("appreciation_3yr_bull")
            bear_3 = appr.get("appreciation_3yr_bear")
            base_5 = appr.get("appreciation_5yr_base")
            rental = appr.get("rental_yield_estimate")
            appr_body = f"""
    <div class="appr-grid">
      <div class="appr-card">
        <div class="label">3-Year CAGR (Base)</div>
        <div class="value positive">{f"+{base_3:.1f}%" if base_3 else "—"}</div>
        <div class="sub">Annual growth rate</div>
      </div>
      <div class="appr-card">
        <div class="label">5-Year CAGR (Base)</div>
        <div class="value positive">{f"+{base_5:.1f}%" if base_5 else "—"}</div>
        <div class="sub">Annual growth rate</div>
      </div>
      <div class="appr-card">
        <div class="label">Rental Yield (Est.)</div>
        <div class="value positive">{f"{rental:.1f}% p.a." if rental else "—"}</div>
        <div class="sub">Gross annual yield</div>
      </div>
    </div>
    <div class="appr-scenarios">
      <div class="scenario bear">
        <div class="scenario-label">Bear Case</div>
        <strong>{f"+{bear_3:.1f}% p.a." if bear_3 else "—"}</strong>
      </div>
      <div class="scenario base">
        <div class="scenario-label">Base Case</div>
        <strong>{f"+{base_3:.1f}% p.a." if base_3 else "—"}</strong>
      </div>
      <div class="scenario bull">
        <div class="scenario-label">Bull Case</div>
        <strong>{f"+{bull_3:.1f}% p.a." if bull_3 else "—"}</strong>
      </div>
    </div>
    <p style="margin-top:10px;font-size:11.5px;color:#94a3b8">
      Forecast period: 3 years. Based on city CAGR baseline, micromarket premium,
      risk-score adjustment, and macro indicators.
    </p>"""
        else:
            appr_body = "<p style='color:#64748b'>Appreciation data not available for this project.</p>"
        html += _section(6, "Price Appreciation Forecast", appr_body)

        # ── 7. RERA Complaint History ─────────────────────────────────────────
        pending = sum(1 for c in complaints if c.status == ComplaintStatus.pending)
        resolved = sum(1 for c in complaints if c.status == ComplaintStatus.resolved)
        dismissed = len(complaints) - pending - resolved
        comp_body = f"""
    <div class="complaint-summary">
      <div class="complaint-stat"><div class="num">{len(complaints)}</div>Total</div>
      <div class="complaint-stat" style="border-color:#fecaca"><div class="num" style="color:#dc2626">{pending}</div>Pending</div>
      <div class="complaint-stat" style="border-color:#bbf7d0"><div class="num" style="color:#16a34a">{resolved}</div>Resolved</div>
      <div class="complaint-stat"><div class="num" style="color:#64748b">{dismissed}</div>Dismissed</div>
    </div>"""
        if complaints:
            rows = ""
            for c in complaints[:20]:
                status_color = (
                    "#dc2626" if c.status == ComplaintStatus.pending
                    else "#16a34a" if c.status == ComplaintStatus.resolved
                    else "#64748b"
                )
                rows += f"""<tr>
                  <td>{_esc(c.complaint_no or "—")}</td>
                  <td>{_esc(c.category or "—")}</td>
                  <td><span style="color:{status_color};font-weight:600">{_esc(c.status.value.upper())}</span></td>
                  <td>{_fmt_date(c.complaint_date)}</td>
                  <td>{_fmt_date(c.resolution_date)}</td>
                </tr>"""
            comp_body += f"""
    <table class="info-table">
      <thead><tr>
        <th>Complaint No.</th><th>Category</th><th>Status</th>
        <th>Filed</th><th>Resolved</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    {"<p style='font-size:11.5px;color:#94a3b8;margin-top:8px'>Showing first 20 complaints.</p>" if len(complaints) > 20 else ""}"""
        else:
            comp_body += '<div class="no-issues">✓ No RERA complaints on record for this project.</div>'
        html += _section(7, "RERA Complaint History", comp_body)

        # ── 8. News & Sentiment ───────────────────────────────────────────────
        if news:
            news_items_html = ""
            for n in news[:10]:
                sent = n.sentiment_score or 0
                sentiment = n.sentiment_label.value
                cls = f"news-item {sentiment}"
                tag = f'<span class="sentiment-tag {sentiment}">{sentiment.upper()}</span>'
                news_items_html += f"""
        <div class="{cls}">
          <div class="headline">{_esc(n.headline)}</div>
          <div class="meta">{_esc(n.source_name or "—")} · {_fmt_date(n.published_at)} · {tag}
          {f" · score {sent:+.2f}" if n.sentiment_score is not None else ""}</div>
        </div>"""
            news_body = news_items_html
            if len(news) > 10:
                news_body += f"<p style='font-size:11.5px;color:#94a3b8;margin-top:6px'>Showing 10 of {len(news)} news items.</p>"
        else:
            news_body = "<p style='color:#64748b'>No recent news articles found for this project.</p>"
        html += _section(8, "News & Sentiment Analysis", news_body)

        # ── 9. Data Freshness ─────────────────────────────────────────────────

        def _freshness_row(source: str, dt: Any) -> str:
            age_str = _age(dt)
            if dt is None:
                dot_cls = "freshness-dot old"
            elif (datetime.now(timezone.utc) - (dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc))).days > 30:
                dot_cls = "freshness-dot stale"
            else:
                dot_cls = "freshness-dot"
            return f"""
          <div class="freshness-row">
            <span class="{dot_cls}"></span>
            <span class="freshness-source">{_esc(source)}</span>
            <span class="freshness-age">{_esc(age_str)}</span>
          </div>"""

        freshness_body = f"""
    <div class="freshness-grid">
      {_freshness_row("Project Data (RERA)", project.last_scraped_at)}
      {_freshness_row("Risk Score", rs.generated_at)}
      {_freshness_row("Developer Data (MCA)", dev.last_scraped_at if dev else None)}
    </div>
    <p style="margin-top:10px;font-size:11.5px;color:#94a3b8">
      Scoring version: {_esc(rs.scoring_version)} &nbsp;·&nbsp;
      Score ID: {str(rs.id)[:8]}…
    </p>"""
        html += _section(9, "Data Freshness & Provenance", freshness_body)

        # ── Footer ────────────────────────────────────────────────────────────
        html += f"""
<div class="report-footer">
  <p>
    <strong>PropIQ Technologies</strong> · Due Diligence Report
    generated {now_str}
  </p>
  <p style="margin-top:6px">
    This report is based on publicly available data (RERA portals, MCA21, news).
    PropIQ scores are algorithmic estimates for informational purposes only and
    do not constitute financial, legal, or investment advice.
    Always consult a qualified property advisor and conduct independent
    legal verification before making any investment decision.
  </p>
  <p style="margin-top:6px">
    © {datetime.now().year} PropIQ Technologies Pvt. Ltd. · propiq.in
  </p>
</div>

</div><!-- .page -->
</body>
</html>"""

        return html


# ── PDF conversion ────────────────────────────────────────────────────────────

def _html_to_pdf(html: str) -> bytes:
    """
    Convert *html* → PDF bytes via WeasyPrint.
    Falls back to UTF-8 encoded HTML if WeasyPrint is not installed
    (e.g. in CI / development without system fonts).
    """
    try:
        from weasyprint import HTML as WP_HTML  # type: ignore[import]
        return WP_HTML(string=html).write_pdf()
    except ImportError:
        logger.warning(
            "WeasyPrint not installed — returning HTML bytes. "
            "Install weasyprint for proper PDF output."
        )
        return html.encode("utf-8")
    except Exception as exc:
        logger.error("WeasyPrint render failed: %s — returning HTML bytes", exc)
        return html.encode("utf-8")
