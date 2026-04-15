"""
PropIQ Appreciation Model
=========================
Estimates property price appreciation potential and rental yield for a project.

Methodology
-----------
1. Start with city-level CAGR baseline (NHB HPI + industry consensus data).
2. Add micromarket boosts for infrastructure catalysts present in the locality.
3. If ≥ 3 registered transactions exist, blend observed historical CAGR
   (70% weight) with city baseline (30% weight) for a data-driven estimate.
4. Compute bull (+3 pp) and bear (−4 pp) scenario CAGRs.
5. Return a 5-year estimate that mean-reverts slightly toward the city baseline
   (guards against extrapolating short-term micro-market spikes).
6. Report a risk-adjusted CAGR = base × (risk_score / 100) to account for the
   probability that risk factors suppress realised appreciation.

All CAGR values are annual percentages (e.g. 8.5 means 8.5% p.a.).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction

# ── City-level CAGR baseline (%) ─────────────────────────────────────────────
# Source: NHB Residex, Knight Frank India Research, Anarock Q1 2025 estimates.
CITY_CAGR_BASELINE: dict[str, float] = {
    "Mumbai": 8.5,
    "Navi Mumbai": 9.5,
    "Thane": 9.5,
    "Bengaluru": 11.0,
    "Hyderabad": 12.0,
    "Pune": 9.5,
    "Chennai": 8.0,
    "Delhi": 7.5,
    "NCR": 8.5,
    "Gurgaon": 9.0,
    "Noida": 8.0,
    "Ahmedabad": 10.0,
    "Kolkata": 6.5,
    "Surat": 8.0,
    "Coimbatore": 7.5,
    "Kochi": 7.0,
}

_DEFAULT_CAGR = 8.0  # fallback for unlisted cities

# ── Infrastructure catalysts → CAGR boost (pp) ───────────────────────────────
INFRASTRUCTURE_CATALYSTS: dict[str, float] = {
    # Generic infrastructure
    "metro": 1.5,
    "airport": 1.0,
    "it park": 1.5,
    "expressway": 1.0,
    "ring road": 0.8,
    "highway": 0.5,
    # Mumbai
    "bkc": 2.0,
    "worli": 1.0,
    "sea link": 0.5,
    "trans harbour": 1.0,
    # Bengaluru
    "whitefield": 1.5,
    "koramangala": 1.0,
    "sarjapur": 1.5,
    "hebbal": 1.0,
    "electronic city": 1.5,
    # Hyderabad
    "hitech city": 1.5,
    "gachibowli": 1.5,
    "financial district": 1.5,
    "kondapur": 1.0,
    # Pune
    "hinjewadi": 2.0,
    "baner": 1.0,
    "wakad": 1.0,
    "kharadi": 1.5,
    # NCR
    "cyber city": 1.5,
    "golf course": 1.0,
    "dwarka expressway": 1.5,
    "yamuna expressway": 1.0,
}

# ── Rental yield by city (gross %) ───────────────────────────────────────────
CITY_RENTAL_YIELD: dict[str, float] = {
    "Mumbai": 2.8,
    "Navi Mumbai": 3.2,
    "Thane": 3.0,
    "Bengaluru": 3.5,
    "Hyderabad": 3.2,
    "Pune": 3.0,
    "Chennai": 3.2,
    "Delhi": 2.5,
    "NCR": 2.8,
    "Gurgaon": 3.0,
    "Noida": 2.8,
    "Ahmedabad": 3.0,
    "Kolkata": 2.5,
    "Kochi": 3.0,
}

_DEFAULT_RENTAL_YIELD = 2.8


class AppreciationModel:
    """
    Stateless appreciation estimator.  Call ``estimate_appreciation()`` for
    each project after computing its composite risk score.
    """

    async def estimate_appreciation(
        self,
        project_id: uuid.UUID,
        city: str,
        micromarket: str,
        price_psf_current: float | None,
        risk_score: float,
        db: AsyncSession,
    ) -> dict:
        """
        Estimate price appreciation for a project.

        Parameters
        ----------
        project_id       : UUID of the project (used to fetch transactions).
        city             : City name (e.g. "Bengaluru").
        micromarket      : Locality/micromarket name (e.g. "Whitefield").
        price_psf_current: Current listed price per sq ft (optional).
        risk_score       : Composite risk score 0–100 from RiskEngine.
        db               : Active async SQLAlchemy session.

        Returns
        -------
        dict with keys:
          appreciation_3yr_base   — base-case 3-year CAGR %
          appreciation_3yr_bull   — bull-case 3-year CAGR %
          appreciation_3yr_bear   — bear-case 3-year CAGR %
          appreciation_5yr_base   — base-case 5-year CAGR %
          rental_yield_estimate   — gross rental yield %
          risk_adjusted_3yr_cagr  — base_3yr × (risk_score / 100)
          data_points_used        — number of transactions used for calibration
        """
        # ── Step 1: City baseline ─────────────────────────────────────────────
        city_key = city.strip().title()
        city_baseline = CITY_CAGR_BASELINE.get(city_key, _DEFAULT_CAGR)
        base_cagr = city_baseline

        # ── Step 2: Micromarket catalyst boost ───────────────────────────────
        micromarket_lower = micromarket.lower()
        catalyst_boost = sum(
            boost
            for keyword, boost in INFRASTRUCTURE_CATALYSTS.items()
            if keyword in micromarket_lower
        )
        base_cagr += catalyst_boost

        # ── Step 3: Calibrate from transaction data ───────────────────────────
        txns = list(
            (
                await db.execute(
                    select(Transaction)
                    .where(Transaction.project_id == project_id)
                    .order_by(Transaction.transaction_date)
                )
            ).scalars()
        )
        data_points = len(txns)

        if data_points >= 3:
            mid = data_points // 2
            early_prices = [t.price_psf for t in txns[:mid] if t.price_psf]
            late_prices = [t.price_psf for t in txns[mid:] if t.price_psf]

            if early_prices and late_prices:
                early_avg = sum(early_prices) / len(early_prices)
                late_avg = sum(late_prices) / len(late_prices)

                span_days = (
                    txns[-1].transaction_date - txns[0].transaction_date
                ).days
                span_years = max(span_days / 365.25, 0.5)

                if early_avg > 0:
                    observed_cagr = (
                        (late_avg / early_avg) ** (1.0 / span_years) - 1.0
                    ) * 100.0
                    # Blend observed with city baseline; cap at realistic range
                    blended = 0.70 * observed_cagr + 0.30 * city_baseline
                    base_cagr = max(3.0, min(20.0, blended))

        # ── Step 4: Scenario CAGRs ────────────────────────────────────────────
        base_3yr = round(base_cagr, 2)
        bull_3yr = round(base_cagr + 3.0, 2)
        bear_3yr = round(max(0.0, base_cagr - 4.0), 2)

        # 5-year: mean-revert 20% toward city baseline to avoid over-extrapolation
        base_5yr = round(base_cagr * 0.80 + city_baseline * 0.20, 2)

        # ── Step 5: Risk-adjusted CAGR ────────────────────────────────────────
        risk_adj_3yr = round(base_3yr * (risk_score / 100.0), 2)

        # ── Step 6: Rental yield ──────────────────────────────────────────────
        rental_yield = round(CITY_RENTAL_YIELD.get(city_key, _DEFAULT_RENTAL_YIELD), 2)

        return {
            "appreciation_3yr_base": base_3yr,
            "appreciation_3yr_bull": bull_3yr,
            "appreciation_3yr_bear": bear_3yr,
            "appreciation_5yr_base": base_5yr,
            "rental_yield_estimate": rental_yield,
            "risk_adjusted_3yr_cagr": risk_adj_3yr,
            "data_points_used": data_points,
        }
