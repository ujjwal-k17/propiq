"""
Test configuration and fixtures
================================
Uses an in-memory SQLite database for speed.  Each test module gets a fresh
database with pre-populated seed rows via the ``seeded_db`` fixture.

Usage in test files:
    async def test_foo(client: AsyncClient, auth_headers: dict): ...
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.database import Base, get_db
from app.main import app
from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer, McaFilingStatus
from app.models.news_item import NewsCategory, NewsItem, SentimentLabel
from app.models.project import OcStatus, Project, ProjectType, ReraStatus
from app.models.risk_score import ConfidenceLevel, RiskBand, RiskScore
from app.models.transaction import Transaction
from app.models.user import RiskAppetite, SubscriptionTier, User

# ─── SQLite in-memory engine ──────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── pytest-asyncio config ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Database lifecycle ───────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create all tables, yield a session, drop all tables after each test.
    This gives each test function a clean, isolated database.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─── Pre-populated database fixture ──────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def seeded_db(db: AsyncSession) -> dict:
    """
    Populate the test database with a minimal but representative dataset.
    Returns a dict of created objects so tests can reference them by key.
    """
    today = date.today()

    # ── Users ─────────────────────────────────────────────────────────────────
    free_user = User(
        email="free@test.com",
        hashed_password=get_password_hash("Password1!"),
        full_name="Free User",
        subscription_tier=SubscriptionTier.free,
        preferred_cities=["Mumbai"],
        risk_appetite=RiskAppetite.moderate,
        watchlist_project_ids=[],
        is_active=True,
    )
    pro_user = User(
        email="pro@test.com",
        hashed_password=get_password_hash("Password1!"),
        full_name="Pro User",
        subscription_tier=SubscriptionTier.pro,
        preferred_cities=["Mumbai", "Bengaluru"],
        risk_appetite=RiskAppetite.aggressive,
        watchlist_project_ids=[],
        is_active=True,
    )
    db.add_all([free_user, pro_user])
    await db.flush()

    # ── Developer: excellent track record ─────────────────────────────────────
    dev_excellent = Developer(
        name="Lodha Group",
        mca_cin="U45200MH1995PLC089830",
        city_hq="Mumbai",
        founded_year=1980,
        total_projects_delivered=42,
        projects_on_time_pct=95.0,
        total_units_delivered=28500,
        active_complaint_count=3,
        resolved_complaint_count=18,
        financial_stress_score=12.0,
        mca_filing_status=McaFilingStatus.compliant,
        nclt_proceedings=False,
    )
    # ── Developer: troubled ──────────────────────────────────────────────────
    dev_troubled = Developer(
        name="BuildRight Properties",
        mca_cin="U45200MH2005PLC123456",
        city_hq="Pune",
        founded_year=2005,
        total_projects_delivered=8,
        projects_on_time_pct=50.0,
        total_units_delivered=2100,
        active_complaint_count=24,
        resolved_complaint_count=6,
        financial_stress_score=72.0,
        mca_filing_status=McaFilingStatus.delayed,
        nclt_proceedings=True,
        nclt_details="NCLT Mumbai Bench Case CP(IBC)/1456/2024",
    )
    db.add_all([dev_excellent, dev_troubled])
    await db.flush()

    # ── Projects ──────────────────────────────────────────────────────────────
    proj_low_risk = Project(
        developer_id=dev_excellent.id,
        name="Lodha World Towers",
        rera_registration_no="P51800012001",
        project_type=ProjectType.residential,
        city="Mumbai",
        micromarket="Lower Parel",
        total_units=240,
        units_sold=215,
        carpet_area_min=850.0,
        carpet_area_max=1400.0,
        price_psf_min=28000.0,
        price_psf_max=42000.0,
        possession_date_declared=date(today.year + 1, 6, 30),
        possession_date_latest=date(today.year + 1, 6, 30),
        construction_pct=92.0,
        oc_status=OcStatus.applied,
        rera_status=ReraStatus.active,
    )
    proj_lapsed_rera = Project(
        developer_id=dev_troubled.id,
        name="BuildRight Powai Greens",
        rera_registration_no="P51800035002",
        project_type=ProjectType.residential,
        city="Mumbai",
        micromarket="Powai",
        total_units=240,
        units_sold=85,
        carpet_area_min=680.0,
        carpet_area_max=1100.0,
        price_psf_min=22000.0,
        price_psf_max=30000.0,
        possession_date_declared=date(today.year - 3, 6, 30),
        possession_date_latest=date(today.year + 1, 6, 30),
        construction_pct=18.0,
        oc_status=OcStatus.not_applied,
        rera_status=ReraStatus.lapsed,
    )
    proj_on_schedule = Project(
        developer_id=dev_excellent.id,
        name="Lodha Palava City",
        rera_registration_no="P51800012002",
        project_type=ProjectType.residential,
        city="Mumbai",
        micromarket="Dombivli",
        total_units=1200,
        units_sold=980,
        carpet_area_min=600.0,
        carpet_area_max=950.0,
        price_psf_min=7800.0,
        price_psf_max=11200.0,
        possession_date_declared=date(today.year + 2, 3, 31),
        possession_date_latest=date(today.year + 2, 3, 31),
        construction_pct=78.0,
        oc_status=OcStatus.not_applied,
        rera_status=ReraStatus.active,
    )
    proj_nclt = Project(
        developer_id=dev_troubled.id,
        name="BuildRight Andheri Heights",
        rera_registration_no="P51800035001",
        project_type=ProjectType.residential,
        city="Mumbai",
        micromarket="Andheri East",
        total_units=180,
        units_sold=95,
        carpet_area_min=550.0,
        carpet_area_max=850.0,
        price_psf_min=18000.0,
        price_psf_max=24000.0,
        possession_date_declared=date(today.year - 2, 12, 31),
        possession_date_latest=date(today.year, 12, 31),
        construction_pct=32.0,
        oc_status=OcStatus.not_applied,
        rera_status=ReraStatus.active,
    )
    proj_blr = Project(
        developer_id=dev_excellent.id,
        name="Lodha Bengaluru Tech Park",
        rera_registration_no="PRM/KA/RERA/1251/308/AA/240601/000001",
        project_type=ProjectType.commercial,
        city="Bengaluru",
        micromarket="Whitefield",
        total_units=320,
        units_sold=180,
        carpet_area_min=500.0,
        carpet_area_max=1200.0,
        price_psf_min=9000.0,
        price_psf_max=13000.0,
        possession_date_declared=date(today.year + 2, 12, 31),
        possession_date_latest=date(today.year + 2, 12, 31),
        construction_pct=55.0,
        oc_status=OcStatus.not_applied,
        rera_status=ReraStatus.active,
    )
    db.add_all([proj_low_risk, proj_lapsed_rera, proj_on_schedule, proj_nclt, proj_blr])
    await db.flush()

    # ── Complaints ────────────────────────────────────────────────────────────
    complaint_active = Complaint(
        developer_id=dev_troubled.id,
        project_id=proj_nclt.id,
        rera_portal="maharera",
        complaint_no="CC006/2024/001",
        complaint_date=date(today.year, 1, 15),
        status=ComplaintStatus.pending,
        category="delay",
    )
    complaint_resolved = Complaint(
        developer_id=dev_excellent.id,
        project_id=proj_low_risk.id,
        rera_portal="maharera",
        complaint_no="CC001/2024/001",
        complaint_date=date(today.year, 3, 10),
        status=ComplaintStatus.resolved,
        category="quality",
        resolution_date=date(today.year, 6, 15),
    )
    db.add_all([complaint_active, complaint_resolved])
    await db.flush()

    # ── Risk scores ───────────────────────────────────────────────────────────
    rs_low = RiskScore(
        project_id=proj_low_risk.id,
        composite_score=84.0,
        risk_band=RiskBand.low,
        legal_score=90.0,
        developer_score=85.0,
        project_score=88.0,
        location_score=82.0,
        financial_score=78.0,
        macro_score=72.0,
        legal_flags=[],
        developer_flags=[],
        project_flags=[],
        confidence_level=ConfidenceLevel.high,
        appreciation_3yr_base=8.5,
        appreciation_3yr_bull=11.5,
        appreciation_3yr_bear=4.5,
        appreciation_5yr_base=9.0,
        rental_yield_estimate=2.8,
        is_current=True,
        scoring_version="2.0",
    )
    rs_lapsed = RiskScore(
        project_id=proj_lapsed_rera.id,
        composite_score=28.0,
        risk_band=RiskBand.critical,
        legal_score=20.0,
        developer_score=15.0,
        project_score=25.0,
        location_score=65.0,
        financial_score=40.0,
        macro_score=72.0,
        legal_flags=["RERA registration lapsed: P51800035002",
                     "OC not applied despite declared possession date having passed"],
        developer_flags=["Developer under NCLT insolvency proceedings",
                         "Poor delivery track record: only 50% projects delivered on time"],
        project_flags=["Very low construction progress: 18%",
                       "Possession date revised back by 48 months — severe delay"],
        confidence_level=ConfidenceLevel.high,
        appreciation_3yr_base=2.0,
        appreciation_3yr_bull=5.0,
        appreciation_3yr_bear=0.5,
        appreciation_5yr_base=2.5,
        rental_yield_estimate=2.8,
        is_current=True,
        scoring_version="2.0",
    )
    rs_medium = RiskScore(
        project_id=proj_on_schedule.id,
        composite_score=72.0,
        risk_band=RiskBand.medium,
        legal_score=80.0,
        developer_score=85.0,
        project_score=70.0,
        location_score=68.0,
        financial_score=65.0,
        macro_score=72.0,
        legal_flags=[],
        developer_flags=[],
        project_flags=[],
        confidence_level=ConfidenceLevel.high,
        appreciation_3yr_base=9.0,
        appreciation_3yr_bull=12.0,
        appreciation_3yr_bear=5.0,
        appreciation_5yr_base=9.5,
        rental_yield_estimate=2.8,
        is_current=True,
        scoring_version="2.0",
    )
    rs_blr = RiskScore(
        project_id=proj_blr.id,
        composite_score=75.0,
        risk_band=RiskBand.medium,
        legal_score=88.0,
        developer_score=85.0,
        project_score=72.0,
        location_score=80.0,
        financial_score=68.0,
        macro_score=72.0,
        legal_flags=[],
        developer_flags=[],
        project_flags=[],
        confidence_level=ConfidenceLevel.high,
        appreciation_3yr_base=11.0,
        appreciation_3yr_bull=14.0,
        appreciation_3yr_bear=7.0,
        appreciation_5yr_base=11.5,
        rental_yield_estimate=3.5,
        is_current=True,
        scoring_version="2.0",
    )
    db.add_all([rs_low, rs_lapsed, rs_medium, rs_blr])
    await db.flush()

    # ── Transactions ──────────────────────────────────────────────────────────
    txns = [
        Transaction(
            project_id=proj_low_risk.id,
            micromarket="Lower Parel",
            city="Mumbai",
            price_psf=29000.0,
            carpet_area_sqft=1050.0,
            total_price=30450000.0,
            transaction_date=date(today.year, 3, 15),
            registration_no="REG/MUM/001",
            unit_type="2BHK",
            floor_no=16,
            source="igr_maharashtra",
        ),
        Transaction(
            project_id=None,
            micromarket="Bengaluru",
            city="Bengaluru",
            price_psf=8000.0,
            carpet_area_sqft=1050.0,
            total_price=8400000.0,
            transaction_date=date(today.year, 4, 10),
            registration_no="REG/BLR/001",
            unit_type="2BHK",
            floor_no=5,
            source="kaveri_karnataka",
        ),
    ]
    db.add_all(txns)
    await db.commit()

    return {
        "free_user": free_user,
        "pro_user": pro_user,
        "dev_excellent": dev_excellent,
        "dev_troubled": dev_troubled,
        "proj_low_risk": proj_low_risk,
        "proj_lapsed_rera": proj_lapsed_rera,
        "proj_on_schedule": proj_on_schedule,
        "proj_nclt": proj_nclt,
        "proj_blr": proj_blr,
        "rs_low": rs_low,
        "rs_lapsed": rs_lapsed,
        "rs_medium": rs_medium,
        "complaint_active": complaint_active,
        "complaint_resolved": complaint_resolved,
    }


# ─── Auth token helpers ───────────────────────────────────────────────────────

def _make_token(user: User) -> str:
    return create_access_token({"sub": str(user.id)})


@pytest.fixture
def free_token(seeded_db: dict) -> str:
    return _make_token(seeded_db["free_user"])


@pytest.fixture
def pro_token(seeded_db: dict) -> str:
    return _make_token(seeded_db["pro_user"])


@pytest.fixture
def auth_headers(free_token: str) -> dict:
    """Authorization headers for the free-tier test user."""
    return {"Authorization": f"Bearer {free_token}"}


@pytest.fixture
def pro_auth_headers(pro_token: str) -> dict:
    """Authorization headers for the pro-tier test user."""
    return {"Authorization": f"Bearer {pro_token}"}


# ─── HTTP client ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession, seeded_db: dict) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the FastAPI app with the test database injected.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
