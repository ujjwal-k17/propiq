"""
PropIQ Risk Engine
==================
Computes a composite risk score (0–100, higher = safer / lower risk) for a
RERA-registered real estate project across six weighted dimensions.

Scoring bands:
  Low      80–100  Safe to proceed with normal diligence
  Medium   60–79   Proceed with caution; verify flagged items
  High     40–59   Significant risk; deep legal/financial check required
  Critical  0–39   Avoid; multiple red flags present

Dimension weights:
  Legal       25%  — RERA status, OC, complaint filings
  Developer   25%  — track record, NCLT, MCA compliance, financial stress
  Project     20%  — construction progress, possession timeline, sales velocity
  Location    15%  — city tier, micromarket quality, price vs market
  Financial   10%  — developer health, sold ratio, pricing data completeness
  Macro        5%  — repo rate, GDP growth, inflation, demand index
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer, McaFilingStatus
from app.models.project import Project, OcStatus, ReraStatus
from app.models.risk_score import ConfidenceLevel, RiskBand, RiskScore
from app.models.transaction import Transaction

WEIGHTS: dict[str, float] = {
    "legal": 0.25,
    "developer": 0.25,
    "project": 0.20,
    "location": 0.15,
    "financial": 0.10,
    "macro": 0.05,
}

# Macro constants — update quarterly from RBI / MOSPI releases
_REPO_RATE = 6.5           # RBI repo rate %
_GDP_GROWTH = 6.8          # India GDP growth % (latest annual)
_INFLATION = 4.8           # CPI inflation %
_RE_DEMAND_INDEX = 72.0    # Proprietary demand index 0–100


class RiskEngine:
    """
    Stateless scoring engine.  Instantiate once and call ``score_project()``
    for each project that needs a fresh score.
    """

    SCORING_VERSION = "2.0"

    # ── Dimension: Legal ──────────────────────────────────────────────────────

    def calculate_legal_score(
        self,
        project: Project,
        complaints: list[Complaint],
    ) -> tuple[float, list[str]]:
        """
        Legal risk score (0–100).

        Deductions
        ----------
        - No RERA registration number            −50
        - RERA status lapsed                     −40
        - RERA status revoked                    −50
        - OC not applied past possession date    −15
        - Active / unresolved RERA complaints    −5 each  (cap −30)
        - Total complaint volume                 −3 each  (cap −20)

        Bonuses
        -------
        - OC already received                    +10
        """
        score = 100.0
        flags: list[str] = []

        if not project.rera_registration_no:
            score -= 50
            flags.append("No RERA registration number on record")
        else:
            if project.rera_status == ReraStatus.lapsed:
                score -= 40
                flags.append(
                    f"RERA registration lapsed: {project.rera_registration_no}"
                )
            elif project.rera_status == ReraStatus.revoked:
                score -= 50
                flags.append(
                    f"RERA registration revoked: {project.rera_registration_no}"
                )

        if project.oc_status == OcStatus.received:
            score += 10
        elif project.oc_status == OcStatus.not_applied and project.possession_date_declared:
            if project.possession_date_declared < date.today():
                score -= 15
                flags.append(
                    "OC not applied despite declared possession date having passed"
                )

        active_complaints = [
            c for c in complaints
            if c.status in (ComplaintStatus.pending, ComplaintStatus.unknown)
        ]
        active_penalty = min(len(active_complaints) * 5, 30)
        if active_penalty:
            score -= active_penalty
            flags.append(
                f"{len(active_complaints)} active/unresolved RERA complaint(s) on this project"
            )
        elif complaints:
            # All complaints resolved — smaller deduction for volume alone
            score -= min(len(complaints) * 3, 20)

        return max(0.0, min(100.0, score)), flags

    # ── Dimension: Developer ──────────────────────────────────────────────────

    def calculate_developer_score(
        self,
        developer: Developer | None,
        complaints: list[Complaint],
    ) -> tuple[float, list[str]]:
        """
        Developer quality score (0–100).

        Starts at 60 for a known developer; 50 when unknown.

        Deductions
        ----------
        - NCLT insolvency proceedings            −40
        - MCA filing defaulted                   −20
        - MCA filing delayed                     −10
        - Financial stress > 70 / 100            −20
        - Financial stress 40–70                 −10
        - On-time delivery < 40%                 −20
        - On-time delivery 40–60%                −5
        - Active developer complaints (−3 each, cap −20)

        Bonuses
        -------
        - Financial stress < 40 (healthy)        +5
        - On-time delivery ≥ 80%                 +20
        - On-time delivery 60–80%                +10
        """
        if developer is None:
            return 50.0, ["Developer profile not available — neutral score assigned"]

        score = 60.0
        flags: list[str] = []

        if developer.nclt_proceedings:
            score -= 40
            detail = f" ({developer.nclt_details})" if developer.nclt_details else ""
            flags.append(f"Developer under NCLT insolvency proceedings{detail}")

        if developer.mca_filing_status == McaFilingStatus.defaulted:
            score -= 20
            flags.append("Developer MCA filing status: DEFAULTED — severe compliance risk")
        elif developer.mca_filing_status == McaFilingStatus.delayed:
            score -= 10
            flags.append("Developer MCA filing status: DELAYED")

        if developer.financial_stress_score is not None:
            stress = developer.financial_stress_score
            if stress > 70:
                score -= 20
                flags.append(f"High financial stress score: {stress:.0f}/100")
            elif stress > 40:
                score -= 10
                flags.append(f"Moderate financial stress score: {stress:.0f}/100")
            else:
                score += 5

        if developer.projects_on_time_pct is not None:
            pct = developer.projects_on_time_pct
            if pct >= 80:
                score += 20
            elif pct >= 60:
                score += 10
            elif pct >= 40:
                score -= 5
            else:
                score -= 20
                flags.append(
                    f"Poor delivery track record: only {pct:.0f}% projects delivered on time"
                )

        dev_active = developer.active_complaint_count
        dev_penalty = min(dev_active * 3, 20)
        if dev_penalty:
            score -= dev_penalty
            flags.append(f"{dev_active} active complaint(s) against developer across all projects")

        return max(0.0, min(100.0, score)), flags

    # ── Dimension: Project Execution ──────────────────────────────────────────

    def calculate_project_score(
        self,
        project: Project,
    ) -> tuple[float, list[str]]:
        """
        Project execution / delivery score (0–100).

        Starts at 70 (neutral).

        Factors
        -------
        Construction progress:
          ≥ 90%   +20 | 70–89%  +10 | 50–69%   0 | 30–49%  −10 | < 30%  −20

        Possession date overdue (no OC):
          > 24 months   −30 | 13–24 months  −20 | 4–12 months  −10

        Revised possession date vs declared:
          > 24 months later  −30 | 13–24 months  −20 | 7–12 months  −10 | ≤ 6 months  −5

        Units sold ratio (demand proxy):
          ≥ 75%   +15 | 50–74%  +8 | < 25%  −10
        """
        score = 70.0
        flags: list[str] = []
        today = date.today()

        if project.construction_pct is not None:
            pct = project.construction_pct
            if pct >= 90:
                score += 20
            elif pct >= 70:
                score += 10
            elif pct >= 30:
                pass
            else:
                score -= 20
                flags.append(f"Very low construction progress: {pct:.0f}%")

        if project.possession_date_declared:
            # Check for date revision (delay signal)
            if (
                project.possession_date_latest
                and project.possession_date_latest > project.possession_date_declared
            ):
                delay_months = (
                    project.possession_date_latest - project.possession_date_declared
                ).days // 30
                if delay_months > 24:
                    score -= 30
                    flags.append(
                        f"Possession date revised back by {delay_months} months — severe delay"
                    )
                elif delay_months > 12:
                    score -= 20
                    flags.append(f"Possession date revised back by {delay_months} months")
                elif delay_months > 6:
                    score -= 10
                    flags.append(f"Possession date revised back by {delay_months} months")
                else:
                    score -= 5

            # Check if project is already overdue (no OC)
            if (
                project.possession_date_declared < today
                and project.oc_status != OcStatus.received
            ):
                overdue_months = (today - project.possession_date_declared).days // 30
                if overdue_months > 24:
                    score -= 30
                    flags.append(
                        f"Project overdue by {overdue_months} months — OC not yet received"
                    )
                elif overdue_months > 12:
                    score -= 20
                    flags.append(
                        f"Project overdue by {overdue_months} months — OC not yet received"
                    )
                elif overdue_months > 3:
                    score -= 10
                    flags.append(
                        f"Project overdue by {overdue_months} months — OC not yet received"
                    )
        else:
            score -= 10
            flags.append("No declared possession date on record")

        if project.units_sold is not None and project.total_units > 0:
            sold_ratio = project.units_sold / project.total_units
            if sold_ratio >= 0.75:
                score += 15
            elif sold_ratio >= 0.50:
                score += 8
            elif sold_ratio < 0.25:
                score -= 10
                flags.append(
                    f"Low sales velocity: {sold_ratio * 100:.0f}% units sold"
                )

        return max(0.0, min(100.0, score)), flags

    # ── Dimension: Location ───────────────────────────────────────────────────

    def calculate_location_score(
        self,
        project: Project,
        transactions: list[Transaction],
    ) -> tuple[float, list[str]]:
        """
        Location & market quality score (0–100).

        Starts at 60.

        Factors
        -------
        - Tier-1 city                                +15
        - Tier-2/3 city                              −5
        - Premium micromarket keyword match          +10
        - Project price > 30% above market avg       −15
        - Project price > 15% above market avg       −5
        - Project price ≥ 10% below market avg       +10 (value play)
        - No transaction data                        −5
        """
        _TIER_1 = {
            "Mumbai", "Bengaluru", "Hyderabad", "Pune", "Chennai",
            "Delhi", "NCR", "Gurgaon", "Noida", "Navi Mumbai",
        }
        _PREMIUM_KEYWORDS = {
            # Mumbai
            "bandra", "juhu", "worli", "powai", "lower parel", "bkc",
            "andheri west", "versova",
            # Bengaluru
            "whitefield", "koramangala", "indiranagar", "hebbal", "sarjapur",
            # Hyderabad
            "hitech city", "gachibowli", "banjara hills", "jubilee hills",
            "kondapur", "madhapur",
            # Pune
            "baner", "hinjewadi", "kothrud", "viman nagar", "kalyani nagar",
            # Chennai
            "adyar", "anna nagar", "velachery", "perungudi",
            # NCR
            "cyber city", "golf course", "sector 29", "dlf phase",
        }

        score = 60.0
        flags: list[str] = []

        city_norm = project.city.strip().title()
        if city_norm in _TIER_1:
            score += 15
        else:
            score -= 5
            flags.append(f"{project.city} is a Tier-2/3 city — lower market liquidity")

        micromarket_lower = project.micromarket.lower()
        if any(kw in micromarket_lower for kw in _PREMIUM_KEYWORDS):
            score += 10

        if transactions:
            market_prices = [t.price_psf for t in transactions if t.price_psf]
            if market_prices and project.price_psf_min and project.price_psf_max:
                avg_market = sum(market_prices) / len(market_prices)
                project_avg = (project.price_psf_min + project.price_psf_max) / 2
                premium_pct = (project_avg - avg_market) / avg_market * 100

                if premium_pct > 30:
                    score -= 15
                    flags.append(
                        f"Project priced {premium_pct:.0f}% above micromarket average "
                        f"(₹{project_avg:,.0f} vs ₹{avg_market:,.0f} psf)"
                    )
                elif premium_pct > 15:
                    score -= 5
                elif premium_pct < -10:
                    score += 10  # underpriced relative to market
        else:
            score -= 5
            flags.append(
                "No registered transaction data available for micromarket comparison"
            )

        return max(0.0, min(100.0, score)), flags

    # ── Dimension: Financial ──────────────────────────────────────────────────

    def calculate_financial_score(
        self,
        project: Project,
        developer: Developer | None,
    ) -> tuple[float, list[str]]:
        """
        Financial health signal score (0–100).

        Starts at 65.

        Factors
        -------
        - Missing price data                     −10
        - Unrealistic price range (max > 3× min) −10
        - Developer stress > 70                  −25
        - Developer stress 40–70                 −10
        - Units sold ≥ 60% (healthy cashflow)    +15
        - Units sold < 20% (cashflow risk)       −15
        """
        score = 65.0
        flags: list[str] = []

        if project.price_psf_min is None or project.price_psf_max is None:
            score -= 10
            flags.append(
                "Pricing information incomplete — unable to assess financial positioning"
            )
        elif project.price_psf_max > project.price_psf_min * 3:
            score -= 10
            flags.append("Unusually wide pricing range — possible data quality issue")

        if developer and developer.financial_stress_score is not None:
            stress = developer.financial_stress_score
            if stress > 70:
                score -= 25
                flags.append(
                    "Developer financial stress is high — project completion risk elevated"
                )
            elif stress > 40:
                score -= 10

        if project.units_sold is not None and project.total_units > 0:
            sold_ratio = project.units_sold / project.total_units
            if sold_ratio >= 0.60:
                score += 15
            elif sold_ratio < 0.20:
                score -= 15
                flags.append(
                    f"Only {sold_ratio * 100:.0f}% units sold — developer cash-flow risk"
                )

        return max(0.0, min(100.0, score)), flags

    # ── Dimension: Macro ──────────────────────────────────────────────────────

    def calculate_macro_score(
        self,
        project: Project,  # noqa: ARG002 — reserved for city-level overrides
    ) -> tuple[float, list[str]]:
        """
        Macro-economic environment score (0–100).

        Starts at 65.  Update the module-level constants quarterly.

        Factors: repo rate, GDP growth, CPI inflation, demand index.
        """
        score = 65.0
        flags: list[str] = []

        if _REPO_RATE <= 5.5:
            score += 15
        elif _REPO_RATE <= 6.5:
            score += 5
        elif _REPO_RATE >= 7.5:
            score -= 15
            flags.append(f"High repo rate ({_REPO_RATE}%) increases home-loan EMI burden")
        elif _REPO_RATE >= 7.0:
            score -= 5

        if _GDP_GROWTH >= 7.0:
            score += 10
        elif _GDP_GROWTH >= 5.0:
            score += 5
        elif _GDP_GROWTH < 4.0:
            score -= 15
            flags.append(f"Slow GDP growth ({_GDP_GROWTH}%) dampens real estate demand")

        if _INFLATION > 7.0:
            score -= 10
            flags.append(f"High inflation ({_INFLATION}%) erodes buyer purchasing power")
        elif _INFLATION < 4.0:
            score += 5

        if _RE_DEMAND_INDEX >= 70:
            score += 10
        elif _RE_DEMAND_INDEX < 40:
            score -= 10
            flags.append("Real estate demand index below neutral — soft market conditions")

        return max(0.0, min(100.0, score)), flags

    # ── Composite ─────────────────────────────────────────────────────────────

    def calculate_composite(self, scores: dict[str, float]) -> float:
        return round(
            scores["legal"] * WEIGHTS["legal"]
            + scores["developer"] * WEIGHTS["developer"]
            + scores["project"] * WEIGHTS["project"]
            + scores["location"] * WEIGHTS["location"]
            + scores["financial"] * WEIGHTS["financial"]
            + scores["macro"] * WEIGHTS["macro"],
            2,
        )

    def get_risk_band(self, composite: float) -> RiskBand:
        if composite >= 80:
            return RiskBand.low
        if composite >= 60:
            return RiskBand.medium
        if composite >= 40:
            return RiskBand.high
        return RiskBand.critical

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _confidence_level(
        self,
        project: Project,
        transactions: list[Transaction],
        developer: Developer | None,
    ) -> ConfidenceLevel:
        """
        Scores data completeness to set confidence in the output.
        High (≥ 8 pts), Medium (5–7 pts), Low (< 5 pts).
        """
        pts = 0
        if project.rera_registration_no:
            pts += 2
        if project.construction_pct is not None:
            pts += 1
        if project.possession_date_declared:
            pts += 1
        if project.price_psf_min and project.price_psf_max:
            pts += 1
        if developer is not None:
            pts += 2
        if developer and developer.projects_on_time_pct is not None:
            pts += 1
        if len(transactions) >= 5:
            pts += 2
        elif transactions:
            pts += 1

        if pts >= 8:
            return ConfidenceLevel.high
        if pts >= 5:
            return ConfidenceLevel.medium
        return ConfidenceLevel.low

    # ── Main entry point ──────────────────────────────────────────────────────

    async def score_project(
        self,
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> RiskScore:
        """
        Full scoring pipeline:
        1. Load project + developer eagerly; complaints + transactions separately.
        2. Run all six dimension scorers.
        3. Compute composite score and risk band.
        4. Mark all previous ``is_current=True`` scores for this project as False.
        5. Persist and return the new RiskScore (is_current=True).
        """
        # ── 1. Load data ──────────────────────────────────────────────────────
        proj_result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.developer))
        )
        project: Project | None = proj_result.scalar_one_or_none()
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        developer: Developer | None = project.developer

        complaints = list(
            (
                await db.execute(
                    select(Complaint).where(Complaint.project_id == project_id)
                )
            ).scalars()
        )
        transactions = list(
            (
                await db.execute(
                    select(Transaction).where(Transaction.project_id == project_id)
                )
            ).scalars()
        )

        # ── 2. Dimension scores ───────────────────────────────────────────────
        legal_score, legal_flags = self.calculate_legal_score(project, complaints)
        dev_score, dev_flags = self.calculate_developer_score(developer, complaints)
        proj_score, proj_flags = self.calculate_project_score(project)
        loc_score, _loc_flags = self.calculate_location_score(project, transactions)
        fin_score, _fin_flags = self.calculate_financial_score(project, developer)
        macro_score, _macro_flags = self.calculate_macro_score(project)

        # ── 3. Composite + band + confidence ─────────────────────────────────
        composite = self.calculate_composite(
            {
                "legal": legal_score,
                "developer": dev_score,
                "project": proj_score,
                "location": loc_score,
                "financial": fin_score,
                "macro": macro_score,
            }
        )
        band = self.get_risk_band(composite)
        confidence = self._confidence_level(project, transactions, developer)

        # ── 4. Retire previous current score ─────────────────────────────────
        await db.execute(
            update(RiskScore)
            .where(
                RiskScore.project_id == project_id,
                RiskScore.is_current.is_(True),
            )
            .values(is_current=False)
        )

        # ── 5. Data freshness provenance ──────────────────────────────────────
        now_iso = datetime.now(timezone.utc).isoformat()
        data_freshness = {
            "scored_at": now_iso,
            "project_scraped_at": (
                project.last_scraped_at.isoformat()
                if project.last_scraped_at
                else None
            ),
            "developer_scraped_at": (
                developer.last_scraped_at.isoformat()
                if developer and developer.last_scraped_at
                else None
            ),
            "transaction_count": len(transactions),
            "complaint_count": len(complaints),
        }

        # ── 6. Persist ────────────────────────────────────────────────────────
        risk_score = RiskScore(
            project_id=project_id,
            composite_score=composite,
            risk_band=band,
            legal_score=round(legal_score, 2),
            developer_score=round(dev_score, 2),
            project_score=round(proj_score, 2),
            location_score=round(loc_score, 2),
            financial_score=round(fin_score, 2),
            macro_score=round(macro_score, 2),
            legal_flags=legal_flags,
            developer_flags=dev_flags,
            project_flags=proj_flags,
            confidence_level=confidence,
            data_freshness=data_freshness,
            scoring_version=self.SCORING_VERSION,
            is_current=True,
        )
        db.add(risk_score)
        await db.flush()
        return risk_score
