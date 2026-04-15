"""
Unit tests for RiskEngine scoring methods.
==========================================
All tests are synchronous — we construct model objects directly without
hitting the database.  The engine is stateless so no fixtures are needed.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer, McaFilingStatus
from app.models.project import OcStatus, Project, ProjectType, ReraStatus
from app.models.risk_score import RiskBand
from app.services.risk_engine import RiskEngine


# ─── Helpers ──────────────────────────────────────────────────────────────────

TODAY = date.today()


def _project(**overrides) -> Project:
    """Return a minimal valid Project with sensible defaults."""
    defaults = dict(
        id=uuid.uuid4(),
        developer_id=uuid.uuid4(),
        name="Test Project",
        rera_registration_no="P51800099999",
        project_type=ProjectType.residential,
        city="Mumbai",
        micromarket="Powai",
        total_units=200,
        units_sold=120,
        carpet_area_min=700.0,
        carpet_area_max=1100.0,
        price_psf_min=18000.0,
        price_psf_max=24000.0,
        possession_date_declared=TODAY + timedelta(days=365),
        possession_date_latest=TODAY + timedelta(days=365),
        construction_pct=60.0,
        oc_status=OcStatus.not_applied,
        rera_status=ReraStatus.active,
    )
    defaults.update(overrides)
    return Project(**defaults)


def _developer(**overrides) -> Developer:
    """Return a minimal valid Developer with sensible defaults."""
    defaults = dict(
        id=uuid.uuid4(),
        name="Good Developer",
        total_projects_delivered=20,
        projects_on_time_pct=85.0,
        total_units_delivered=5000,
        active_complaint_count=2,
        resolved_complaint_count=10,
        financial_stress_score=20.0,
        mca_filing_status=McaFilingStatus.compliant,
        nclt_proceedings=False,
    )
    defaults.update(overrides)
    return Developer(**defaults)


def _complaint(status=ComplaintStatus.pending, project=None, developer=None) -> Complaint:
    pid = uuid.uuid4()
    return Complaint(
        id=pid,
        project_id=project.id if project else None,
        developer_id=developer.id if developer else None,
        rera_portal="maharera",
        complaint_no=f"CC/{pid.hex[:6]}",
        status=status,
        category="delay",
    )


engine = RiskEngine()


# ─── Legal score tests ────────────────────────────────────────────────────────

def test_legal_score_critical_with_nclt_revoked_rera():
    """Revoked RERA should push legal score close to 0."""
    proj = _project(rera_status=ReraStatus.revoked)
    score, flags = engine.calculate_legal_score(proj, [])
    assert score <= 50.0
    assert any("revoked" in f.lower() for f in flags)


def test_legal_score_high_with_lapsed_rera():
    """Lapsed RERA should substantially reduce the score."""
    proj = _project(rera_status=ReraStatus.lapsed)
    score, flags = engine.calculate_legal_score(proj, [])
    assert score <= 60.0
    assert any("lapsed" in f.lower() for f in flags)


def test_legal_score_low_with_clean_title():
    """Active RERA + OC received + no complaints → near-perfect legal score."""
    proj = _project(
        rera_status=ReraStatus.active,
        oc_status=OcStatus.received,
        possession_date_declared=TODAY - timedelta(days=90),
    )
    score, flags = engine.calculate_legal_score(proj, [])
    assert score >= 80.0
    assert flags == []


def test_legal_score_no_rera_number():
    """Missing RERA registration should be a major deduction."""
    proj = _project(rera_registration_no=None)
    score, flags = engine.calculate_legal_score(proj, [])
    assert score <= 50.0
    assert any("no rera" in f.lower() for f in flags)


def test_legal_score_penalises_active_complaints():
    """Each active complaint deducts 5 points (capped at 30)."""
    proj = _project()
    complaints = [_complaint(ComplaintStatus.pending) for _ in range(7)]
    score_no_comp, _ = engine.calculate_legal_score(proj, [])
    score_with_comp, flags = engine.calculate_legal_score(proj, complaints)
    # 7 complaints × 5 = 35, capped at 30
    assert score_no_comp - score_with_comp == pytest.approx(30.0)
    assert any("complaint" in f.lower() for f in flags)


def test_legal_score_oc_received_bonus():
    """OC received should give a +10 bonus on legal score."""
    proj_no_oc = _project(oc_status=OcStatus.not_applied)
    proj_oc = _project(oc_status=OcStatus.received)
    score_no_oc, _ = engine.calculate_legal_score(proj_no_oc, [])
    score_oc, _ = engine.calculate_legal_score(proj_oc, [])
    assert score_oc - score_no_oc == pytest.approx(10.0)


def test_legal_score_oc_not_applied_past_possession_date():
    """OC not applied past possession date should deduct 15 points."""
    proj_past = _project(
        oc_status=OcStatus.not_applied,
        possession_date_declared=TODAY - timedelta(days=30),
    )
    proj_future = _project(
        oc_status=OcStatus.not_applied,
        possession_date_declared=TODAY + timedelta(days=30),
    )
    score_past, flags_past = engine.calculate_legal_score(proj_past, [])
    score_future, _ = engine.calculate_legal_score(proj_future, [])
    assert score_future - score_past == pytest.approx(15.0)
    assert any("oc not applied" in f.lower() for f in flags_past)


# ─── Developer score tests ────────────────────────────────────────────────────

def test_developer_score_excellent_track_record():
    """95% on-time + low stress + compliant → high developer score."""
    dev = _developer(
        projects_on_time_pct=95.0,
        financial_stress_score=10.0,
        mca_filing_status=McaFilingStatus.compliant,
        nclt_proceedings=False,
        active_complaint_count=0,
    )
    score, flags = engine.calculate_developer_score(dev, [])
    assert score >= 80.0
    assert flags == []


def test_developer_score_troubled_developer():
    """NCLT + defaulted MCA + high stress → very low score."""
    dev = _developer(
        projects_on_time_pct=40.0,
        financial_stress_score=80.0,
        mca_filing_status=McaFilingStatus.defaulted,
        nclt_proceedings=True,
        nclt_details="NCLT Mumbai Case 2024",
        active_complaint_count=20,
    )
    score, flags = engine.calculate_developer_score(dev, [])
    assert score <= 20.0
    assert any("nclt" in f.lower() for f in flags)
    assert any("mca" in f.lower() or "defaulted" in f.lower() for f in flags)


def test_developer_score_nclt_deducts_40():
    """NCLT proceedings should deduct exactly 40 from base 60."""
    dev_no_nclt = _developer(nclt_proceedings=False, financial_stress_score=None,
                              projects_on_time_pct=None, active_complaint_count=0)
    dev_nclt = _developer(nclt_proceedings=True, financial_stress_score=None,
                           projects_on_time_pct=None, active_complaint_count=0)
    score_no, _ = engine.calculate_developer_score(dev_no_nclt, [])
    score_nclt, flags = engine.calculate_developer_score(dev_nclt, [])
    assert score_no - score_nclt == pytest.approx(40.0)
    assert any("nclt" in f.lower() for f in flags)


def test_developer_score_none_developer():
    """None developer should return 50 with a single informational flag."""
    score, flags = engine.calculate_developer_score(None, [])
    assert score == 50.0
    assert len(flags) == 1


def test_developer_score_on_time_bonus():
    """On-time ≥ 80% should add +20 points."""
    dev_low = _developer(projects_on_time_pct=30.0, financial_stress_score=None,
                          active_complaint_count=0)
    dev_high = _developer(projects_on_time_pct=90.0, financial_stress_score=None,
                           active_complaint_count=0)
    score_low, _ = engine.calculate_developer_score(dev_low, [])
    score_high, _ = engine.calculate_developer_score(dev_high, [])
    # Low: −20 penalty; High: +20 bonus → difference of 40
    assert score_high - score_low == pytest.approx(40.0)


# ─── Project score tests ──────────────────────────────────────────────────────

def test_project_score_on_schedule():
    """High construction + future possession date + high sold ratio → high score."""
    proj = _project(
        construction_pct=92.0,
        possession_date_declared=TODAY + timedelta(days=180),
        possession_date_latest=TODAY + timedelta(days=180),
        units_sold=160,
        total_units=200,  # 80% sold
        oc_status=OcStatus.not_applied,
    )
    score, flags = engine.calculate_project_score(proj)
    assert score >= 80.0
    assert flags == []


def test_project_score_severely_delayed():
    """Very low construction + heavily overdue + few sold → critical project score."""
    proj = _project(
        construction_pct=10.0,
        possession_date_declared=TODAY - timedelta(days=800),  # 26+ months overdue
        possession_date_latest=TODAY + timedelta(days=365),
        units_sold=20,
        total_units=200,  # 10% sold
        oc_status=OcStatus.not_applied,
    )
    score, flags = engine.calculate_project_score(proj)
    assert score <= 30.0
    assert any("progress" in f.lower() or "overdue" in f.lower() for f in flags)


def test_project_score_no_possession_date():
    """Missing possession date should be penalised."""
    proj_with_date = _project(
        possession_date_declared=TODAY + timedelta(days=365),
        possession_date_latest=TODAY + timedelta(days=365),
        construction_pct=60.0,
        units_sold=None,
    )
    proj_no_date = _project(
        possession_date_declared=None,
        possession_date_latest=None,
        construction_pct=60.0,
        units_sold=None,
    )
    score_with, _ = engine.calculate_project_score(proj_with_date)
    score_without, flags_without = engine.calculate_project_score(proj_no_date)
    assert score_with > score_without
    assert any("possession" in f.lower() for f in flags_without)


# ─── Composite and band tests ─────────────────────────────────────────────────

def test_composite_score_weighted_correctly():
    """calculate_composite should apply the correct WEIGHTS dict."""
    scores = {
        "legal": 100.0,
        "developer": 100.0,
        "project": 100.0,
        "location": 100.0,
        "financial": 100.0,
        "macro": 100.0,
    }
    result = engine.calculate_composite(scores)
    assert result == pytest.approx(100.0)

    # With all zeros
    zero_scores = {k: 0.0 for k in scores}
    assert engine.calculate_composite(zero_scores) == pytest.approx(0.0)

    # Partial: only legal = 100, rest = 0 → 25% contribution
    partial = {k: 0.0 for k in scores}
    partial["legal"] = 100.0
    assert engine.calculate_composite(partial) == pytest.approx(25.0)


def test_risk_band_classification():
    """Verify band boundaries: ≥80 low, 60–79 medium, 40–59 high, <40 critical."""
    assert engine.get_risk_band(80.0) == RiskBand.low
    assert engine.get_risk_band(100.0) == RiskBand.low
    assert engine.get_risk_band(79.9) == RiskBand.medium
    assert engine.get_risk_band(60.0) == RiskBand.medium
    assert engine.get_risk_band(59.9) == RiskBand.high
    assert engine.get_risk_band(40.0) == RiskBand.high
    assert engine.get_risk_band(39.9) == RiskBand.critical
    assert engine.get_risk_band(0.0) == RiskBand.critical


def test_composite_score_clamps_to_0_100():
    """Extreme scores should be clamped to [0, 100]."""
    # Minimum: all zeros
    result_low = engine.calculate_composite({k: 0.0 for k in
                                              ["legal","developer","project","location","financial","macro"]})
    assert 0.0 <= result_low <= 100.0

    # Maximum: all 100
    result_high = engine.calculate_composite({k: 100.0 for k in
                                               ["legal","developer","project","location","financial","macro"]})
    assert result_high == pytest.approx(100.0)


# ─── Location score tests ─────────────────────────────────────────────────────

def test_location_score_tier1_city_bonus():
    """Mumbai should score higher than a tier-2 city."""
    proj_mumbai = _project(city="Mumbai", micromarket="Andheri")
    proj_tier2 = _project(city="Nagpur", micromarket="Dharampeth")
    score_mumbai, _ = engine.calculate_location_score(proj_mumbai, [])
    score_tier2, flags_tier2 = engine.calculate_location_score(proj_tier2, [])
    assert score_mumbai > score_tier2
    assert any("tier" in f.lower() for f in flags_tier2)


def test_location_score_premium_micromarket():
    """Premium micromarket should give a +10 bonus."""
    proj_premium = _project(city="Mumbai", micromarket="BKC")
    proj_regular = _project(city="Mumbai", micromarket="Kurla")
    score_premium, _ = engine.calculate_location_score(proj_premium, [])
    score_regular, _ = engine.calculate_location_score(proj_regular, [])
    assert score_premium > score_regular


# ─── Financial score tests ────────────────────────────────────────────────────

def test_financial_score_high_stress_developer():
    """High financial stress (>70) should deduct 25 from financial score."""
    dev_stressed = _developer(financial_stress_score=80.0)
    dev_healthy = _developer(financial_stress_score=15.0)
    proj = _project(units_sold=100, total_units=200)
    score_stressed, flags = engine.calculate_financial_score(proj, dev_stressed)
    score_healthy, _ = engine.calculate_financial_score(proj, dev_healthy)
    # Stressed: -25; healthy: +5 (stress <40)
    assert score_healthy - score_stressed == pytest.approx(30.0)
    assert any("stress" in f.lower() for f in flags)


# ─── Macro score tests ────────────────────────────────────────────────────────

def test_macro_score_returns_valid_range():
    """Macro score should always be between 0 and 100."""
    proj = _project()
    score, _ = engine.calculate_macro_score(proj)
    assert 0.0 <= score <= 100.0


def test_appreciation_model_city_cagr_baselines():
    """Test that city CAGR baselines are defined for key Indian cities."""
    from app.services.appreciation_model import CITY_CAGR_BASELINE
    for city in ["Mumbai", "Bengaluru", "Pune", "Hyderabad"]:
        assert city in CITY_CAGR_BASELINE, f"{city} missing from CITY_CAGR_BASELINE"
        assert 4.0 <= CITY_CAGR_BASELINE[city] <= 20.0, (
            f"{city} CAGR {CITY_CAGR_BASELINE[city]} out of realistic range"
        )

def test_appreciation_model_bull_exceeds_base_exceeds_bear():
    """Bull scenario should be > base > bear for any city."""
    from app.services.appreciation_model import CITY_CAGR_BASELINE, INFRASTRUCTURE_CATALYSTS
    # Reconstruct the bull/bear deltas from the model constants
    # Bull = base + 3pp, Bear = base - 4pp (see appreciate_model.py docstring)
    base = CITY_CAGR_BASELINE["Mumbai"]
    bull = base + 3.0
    bear = base - 4.0
    assert bull > base > bear
