"""
PropIQ Seed Data
================
Populates the development database with realistic test data:
  - 5 developers with varied risk profiles
  - 25 projects across Mumbai, Bengaluru, Pune
  - Risk scores via the RiskEngine (not hardcoded)
  - 50+ transactions spread across micromarkets
  - 30+ complaints across projects/developers
  - 20+ news items with varied sentiment
  - 2 test users (free and pro tier)

Usage:
    python -m app.seed_data
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.database import AsyncSessionLocal, create_all_tables
from app.models.complaint import Complaint, ComplaintStatus
from app.models.developer import Developer, McaFilingStatus
from app.models.news_item import NewsCategory, NewsItem, SentimentLabel
from app.models.project import OcStatus, Project, ProjectType, ReraStatus
from app.models.risk_score import ConfidenceLevel, RiskBand, RiskScore
from app.models.transaction import Transaction
from app.models.user import RiskAppetite, SubscriptionTier, User
from app.services.risk_engine import RiskEngine


# ─── Helper ───────────────────────────────────────────────────────────────────

def _date(s: str) -> date:
    return date.fromisoformat(s)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


TODAY = date.today()


# ─── Developer definitions ────────────────────────────────────────────────────

DEVELOPER_DATA = [
    {
        "name": "Lodha Group",
        "mca_cin": "U45200MH1995PLC089830",
        "city_hq": "Mumbai",
        "founded_year": 1980,
        "website": "https://www.lodhagroup.com",
        "total_projects_delivered": 42,
        "projects_on_time_pct": 95.0,
        "total_units_delivered": 28500,
        "active_complaint_count": 3,
        "resolved_complaint_count": 18,
        "financial_stress_score": 12.0,
        "mca_filing_status": McaFilingStatus.compliant,
        "nclt_proceedings": False,
        "rera_registration_ids": [
            {"state": "Maharashtra", "id": "A51800001234"},
            {"state": "Karnataka", "id": "PRM/KA/RERA/1251/001"},
        ],
    },
    {
        "name": "Prestige Estates",
        "mca_cin": "U45201KA2010PLC054123",
        "city_hq": "Bengaluru",
        "founded_year": 1986,
        "website": "https://www.prestigeconstructions.com",
        "total_projects_delivered": 30,
        "projects_on_time_pct": 85.0,
        "total_units_delivered": 19200,
        "active_complaint_count": 9,
        "resolved_complaint_count": 22,
        "financial_stress_score": 25.0,
        "mca_filing_status": McaFilingStatus.compliant,
        "nclt_proceedings": False,
        "rera_registration_ids": [
            {"state": "Karnataka", "id": "PRM/KA/RERA/1251/002"},
            {"state": "Maharashtra", "id": "A51800002345"},
        ],
    },
    {
        "name": "BuildRight Properties",
        "mca_cin": "U45200MH2005PLC123456",
        "city_hq": "Pune",
        "founded_year": 2005,
        "website": None,
        "total_projects_delivered": 8,
        "projects_on_time_pct": 50.0,
        "total_units_delivered": 2100,
        "active_complaint_count": 24,
        "resolved_complaint_count": 6,
        "financial_stress_score": 72.0,
        "mca_filing_status": McaFilingStatus.delayed,
        "nclt_proceedings": True,
        "nclt_details": "NCLT Mumbai Bench Case No. CP(IBC)/1456/2024 — admitted March 2024",
        "rera_registration_ids": [
            {"state": "Maharashtra", "id": "P52100001122"},
        ],
    },
    {
        "name": "GreenArch Developers",
        "mca_cin": "U45200KA2019PLC987654",
        "city_hq": "Bengaluru",
        "founded_year": 2019,
        "website": "https://www.greenarch.in",
        "total_projects_delivered": 1,
        "projects_on_time_pct": None,
        "total_units_delivered": 180,
        "active_complaint_count": 2,
        "resolved_complaint_count": 1,
        "financial_stress_score": 45.0,
        "mca_filing_status": McaFilingStatus.unknown,
        "nclt_proceedings": False,
        "rera_registration_ids": [
            {"state": "Karnataka", "id": "PRM/KA/RERA/1251/308"},
        ],
    },
    {
        "name": "Skyline Real Estate",
        "mca_cin": "U45200MH2012PLC234567",
        "city_hq": "Mumbai",
        "founded_year": 2012,
        "website": None,
        "total_projects_delivered": 5,
        "projects_on_time_pct": 40.0,
        "total_units_delivered": 780,
        "active_complaint_count": 38,
        "resolved_complaint_count": 4,
        "financial_stress_score": 88.0,
        "mca_filing_status": McaFilingStatus.defaulted,
        "nclt_proceedings": True,
        "nclt_details": "NCLT Mumbai Bench Case No. CP(IBC)/0234/2023 — pending resolution",
        "rera_registration_ids": [],
    },
]

# ─── Project definitions ──────────────────────────────────────────────────────
# Format: (developer_index, name, city, micromarket, rera_no, project_type,
#          total_units, units_sold, carpet_min, carpet_max, psf_min, psf_max,
#          possession_declared, possession_latest, construction_pct,
#          oc_status, rera_status)

PROJECT_DATA = [
    # ── Lodha Group (index 0) — Low risk ──────────────────────────────────────
    (0, "Lodha World Towers", "Mumbai", "Lower Parel",
     "P51800012001", ProjectType.residential,
     240, 215, 850.0, 1400.0, 28000.0, 42000.0,
     _date("2025-06-30"), _date("2025-06-30"), 92.0,
     OcStatus.applied, ReraStatus.active),

    (0, "Lodha Palava City Phase 3", "Mumbai", "Dombivli",
     "P51800012002", ProjectType.residential,
     1200, 980, 600.0, 950.0, 7800.0, 11200.0,
     _date("2026-03-31"), _date("2026-03-31"), 78.0,
     OcStatus.not_applied, ReraStatus.active),

    (0, "Lodha Bellissimo", "Mumbai", "Mahalaxmi",
     "P51800012003", ProjectType.residential,
     180, 172, 1800.0, 2800.0, 45000.0, 68000.0,
     _date("2024-12-31"), _date("2024-12-31"), 98.0,
     OcStatus.received, ReraStatus.completed),

    (0, "Lodha Belmondo", "Pune", "Hinjewadi",
     "P52100012004", ProjectType.residential,
     600, 540, 720.0, 1100.0, 9500.0, 13500.0,
     _date("2026-09-30"), _date("2026-09-30"), 62.0,
     OcStatus.not_applied, ReraStatus.active),

    (0, "Lodha NXT", "Mumbai", "Thane West",
     "P51800012005", ProjectType.commercial,
     320, 210, 500.0, 900.0, 14000.0, 19500.0,
     _date("2027-06-30"), _date("2027-06-30"), 35.0,
     OcStatus.not_applied, ReraStatus.active),

    # ── Prestige Estates (index 1) — Low/Medium risk ──────────────────────────
    (1, "Prestige Lakeside Habitat", "Bengaluru", "Whitefield",
     "PRM/KA/RERA/1251/308/AA/180601/000301", ProjectType.residential,
     3426, 2900, 1050.0, 1800.0, 7500.0, 11500.0,
     _date("2025-09-30"), _date("2025-09-30"), 88.0,
     OcStatus.applied, ReraStatus.active),

    (1, "Prestige Song of the South", "Bengaluru", "Begur",
     "PRM/KA/RERA/1251/308/AA/180601/000302", ProjectType.residential,
     2352, 2100, 930.0, 1550.0, 6800.0, 9800.0,
     _date("2025-12-31"), _date("2025-12-31"), 82.0,
     OcStatus.not_applied, ReraStatus.active),

    (1, "Prestige Kew Gardens", "Bengaluru", "Koramangala",
     "PRM/KA/RERA/1251/308/AA/190601/000303", ProjectType.residential,
     304, 290, 1400.0, 2200.0, 15500.0, 22000.0,
     _date("2024-06-30"), _date("2024-06-30"), 100.0,
     OcStatus.received, ReraStatus.completed),

    (1, "Prestige Tech Vista", "Bengaluru", "Sarjapur Road",
     "PRM/KA/RERA/1251/308/AA/210601/000304", ProjectType.commercial,
     420, 180, 800.0, 1400.0, 9000.0, 13000.0,
     _date("2026-06-30"), _date("2026-12-31"), 45.0,
     OcStatus.not_applied, ReraStatus.active),

    (1, "Prestige Meridian Park", "Pune", "Kharadi",
     "P52100009901", ProjectType.residential,
     480, 320, 850.0, 1400.0, 8500.0, 12500.0,
     _date("2026-03-31"), _date("2026-09-30"), 55.0,
     OcStatus.not_applied, ReraStatus.active),

    # ── BuildRight Properties (index 2) — High/Critical risk ─────────────────
    (2, "BuildRight Andheri Heights", "Mumbai", "Andheri East",
     "P51800035001", ProjectType.residential,
     180, 95, 550.0, 850.0, 18000.0, 24000.0,
     _date("2022-12-31"), _date("2024-12-31"), 32.0,
     OcStatus.not_applied, ReraStatus.active),

    (2, "BuildRight Powai Greens", "Mumbai", "Powai",
     "P51800035002", ProjectType.residential,
     240, 85, 680.0, 1100.0, 22000.0, 30000.0,
     _date("2021-06-30"), _date("2025-06-30"), 18.0,
     OcStatus.not_applied, ReraStatus.lapsed),

    (2, "BuildRight Hinjewadi IT Park", "Pune", "Hinjewadi",
     "P52100035003", ProjectType.commercial,
     280, 42, 600.0, 1000.0, 7200.0, 10500.0,
     _date("2022-03-31"), _date("2025-12-31"), 24.0,
     OcStatus.not_applied, ReraStatus.lapsed),

    (2, "BuildRight Baner Residency", "Pune", "Baner",
     "P52100035004", ProjectType.residential,
     120, 30, 720.0, 1100.0, 9000.0, 12500.0,
     _date("2023-06-30"), _date("2026-06-30"), 15.0,
     OcStatus.not_applied, ReraStatus.active),

    (2, "BuildRight Kurla Complex", "Mumbai", "Kurla West",
     "P51800035005", ProjectType.residential,
     320, 210, 420.0, 680.0, 14500.0, 19000.0,
     _date("2024-03-31"), _date("2025-12-31"), 48.0,
     OcStatus.not_applied, ReraStatus.active),

    # ── GreenArch Developers (index 3) — Medium risk ──────────────────────────
    (3, "GreenArch EcoHomes Whitefield", "Bengaluru", "Whitefield",
     "PRM/KA/RERA/1251/308/AA/220601/000401", ProjectType.residential,
     220, 130, 900.0, 1400.0, 6500.0, 9200.0,
     _date("2026-12-31"), _date("2026-12-31"), 42.0,
     OcStatus.not_applied, ReraStatus.active),

    (3, "GreenArch HSR Terraces", "Bengaluru", "HSR Layout",
     "PRM/KA/RERA/1251/308/AA/220601/000402", ProjectType.residential,
     88, 62, 1100.0, 1700.0, 10500.0, 15000.0,
     _date("2026-03-31"), _date("2026-09-30"), 55.0,
     OcStatus.not_applied, ReraStatus.active),

    (3, "GreenArch BKC Offices", "Mumbai", "BKC",
     "P51800078001", ProjectType.commercial,
     150, 45, 900.0, 1600.0, 32000.0, 48000.0,
     _date("2027-03-31"), _date("2027-03-31"), 28.0,
     OcStatus.not_applied, ReraStatus.active),

    # ── Skyline Real Estate (index 4) — Critical risk ─────────────────────────
    (4, "Skyline Majestic Towers", "Mumbai", "Andheri West",
     None, ProjectType.residential,
     380, 290, 750.0, 1250.0, 20000.0, 28000.0,
     _date("2021-12-31"), _date("2024-12-31"), 12.0,
     OcStatus.not_applied, ReraStatus.revoked),

    (4, "Skyline BKC Residences", "Mumbai", "BKC",
     "P51800099001", ProjectType.residential,
     160, 148, 1500.0, 2500.0, 40000.0, 58000.0,
     _date("2020-06-30"), _date("2023-12-31"), 8.0,
     OcStatus.not_applied, ReraStatus.lapsed),

    (4, "Skyline Powai Luxe", "Mumbai", "Powai",
     "P51800099002", ProjectType.residential,
     200, 175, 900.0, 1500.0, 24000.0, 34000.0,
     _date("2022-03-31"), _date("2025-06-30"), 22.0,
     OcStatus.not_applied, ReraStatus.lapsed),

    (4, "Skyline Navi Mumbai Township", "Mumbai", "Kharghar",
     None, ProjectType.residential,
     840, 620, 500.0, 800.0, 9500.0, 14000.0,
     _date("2021-06-30"), None, 5.0,
     OcStatus.not_applied, ReraStatus.revoked),

    # ── Additional medium-risk projects ───────────────────────────────────────
    (1, "Prestige Finsbury Park", "Bengaluru", "ORR Bellandur",
     "PRM/KA/RERA/1251/308/AA/230601/000305", ProjectType.residential,
     540, 280, 1200.0, 2000.0, 12000.0, 17500.0,
     _date("2027-06-30"), _date("2027-06-30"), 22.0,
     OcStatus.not_applied, ReraStatus.active),

    (0, "Lodha Altamount", "Mumbai", "Altamount Road",
     "P51800012006", ProjectType.residential,
     48, 42, 4000.0, 8000.0, 75000.0, 120000.0,
     _date("2025-03-31"), _date("2025-09-30"), 85.0,
     OcStatus.applied, ReraStatus.active),

    (3, "GreenArch Kharadi Square", "Pune", "Kharadi",
     "P52100078002", ProjectType.commercial,
     200, 88, 750.0, 1200.0, 8000.0, 11500.0,
     _date("2026-09-30"), _date("2026-09-30"), 38.0,
     OcStatus.not_applied, ReraStatus.active),
]


# ─── Complaint definitions ────────────────────────────────────────────────────

# (developer_index, project_index_or_None, portal, complaint_no, complaint_date,
#  status, category, resolution_date_or_None)
COMPLAINT_DATA = [
    # BuildRight — many complaints (high risk)
    (2, 10, "maharera", "CC006/2024/001", _date("2024-01-15"), ComplaintStatus.pending, "delay", None),
    (2, 10, "maharera", "CC006/2024/002", _date("2024-02-20"), ComplaintStatus.pending, "delay", None),
    (2, 10, "maharera", "CC006/2024/003", _date("2024-03-10"), ComplaintStatus.pending, "quality", None),
    (2, 11, "maharera", "CC006/2024/004", _date("2023-08-05"), ComplaintStatus.pending, "possession", None),
    (2, 11, "maharera", "CC006/2024/005", _date("2023-09-12"), ComplaintStatus.pending, "refund", None),
    (2, 11, "maharera", "CC006/2024/006", _date("2023-10-01"), ComplaintStatus.pending, "delay", None),
    (2, 12, "maharera", "CC006/2023/007", _date("2023-11-22"), ComplaintStatus.pending, "delay", None),
    (2, 12, "maharera", "CC006/2023/008", _date("2023-12-14"), ComplaintStatus.unknown, "quality", None),
    (2, 13, "maharera", "CC006/2024/009", _date("2024-04-05"), ComplaintStatus.pending, "possession", None),
    (2, 14, "maharera", "CC006/2024/010", _date("2024-05-18"), ComplaintStatus.pending, "delay", None),
    (2, None, "maharera", "CC006/2022/011", _date("2022-06-01"), ComplaintStatus.resolved, "delay", _date("2023-01-15")),
    (2, None, "maharera", "CC006/2022/012", _date("2022-08-20"), ComplaintStatus.resolved, "refund", _date("2023-03-10")),

    # Skyline — critical risk
    (4, 18, "maharera", "CC009/2023/001", _date("2022-09-10"), ComplaintStatus.pending, "fraud", None),
    (4, 18, "maharera", "CC009/2023/002", _date("2022-10-25"), ComplaintStatus.pending, "possession", None),
    (4, 18, "maharera", "CC009/2023/003", _date("2023-01-15"), ComplaintStatus.pending, "refund", None),
    (4, 19, "maharera", "CC009/2023/004", _date("2022-11-20"), ComplaintStatus.pending, "delay", None),
    (4, 19, "maharera", "CC009/2024/005", _date("2023-03-08"), ComplaintStatus.pending, "fraud", None),
    (4, 20, "maharera", "CC009/2024/006", _date("2023-05-14"), ComplaintStatus.pending, "possession", None),
    (4, 21, "maharera", "CC009/2024/007", _date("2023-07-22"), ComplaintStatus.pending, "delay", None),
    (4, None, "maharera", "CC009/2022/008", _date("2022-04-01"), ComplaintStatus.resolved, "quality", _date("2023-06-15")),

    # Prestige — moderate complaints (some resolved)
    (1, 5, "krera", "KR/C/2024/00156", _date("2024-01-10"), ComplaintStatus.pending, "delay", None),
    (1, 5, "krera", "KR/C/2024/00157", _date("2024-02-28"), ComplaintStatus.resolved, "quality", _date("2024-06-10")),
    (1, 6, "krera", "KR/C/2023/00289", _date("2023-11-05"), ComplaintStatus.resolved, "possession", _date("2024-04-01")),
    (1, 7, "krera", "KR/C/2024/00312", _date("2024-03-20"), ComplaintStatus.pending, "delay", None),
    (1, None, "maharera", "CC005/2024/013", _date("2024-01-25"), ComplaintStatus.pending, "quality", None),

    # Lodha — very few (low risk)
    (0, 0, "maharera", "CC001/2024/001", _date("2024-06-01"), ComplaintStatus.resolved, "quality", _date("2024-09-15")),
    (0, 1, "maharera", "CC001/2024/002", _date("2024-03-10"), ComplaintStatus.resolved, "delay", _date("2024-07-20")),
    (0, 3, "maharera", "CC001/2023/003", _date("2023-12-05"), ComplaintStatus.resolved, "other", _date("2024-04-01")),

    # GreenArch — new developer, few complaints
    (3, 15, "krera", "KR/C/2024/00401", _date("2024-02-14"), ComplaintStatus.pending, "quality", None),
    (3, 16, "krera", "KR/C/2024/00402", _date("2024-04-01"), ComplaintStatus.resolved, "delay", _date("2024-08-10")),
]


# ─── News item definitions ────────────────────────────────────────────────────

# (developer_index, project_index_or_None, headline, summary, sentiment_score,
#  sentiment_label, category, source_name, published_dt)
NEWS_DATA = [
    # Lodha — positive
    (0, None,
     "Lodha Group reports record quarterly sales of ₹3,800 crore",
     "Lodha Group announced its strongest quarterly results, driven by demand in Mumbai's luxury and mid-income segments. The developer delivered 1,200 units ahead of schedule.",
     0.82, SentimentLabel.positive, NewsCategory.positive, "Economic Times",
     _dt("2024-10-15T10:00:00")),

    (0, 0,
     "Lodha World Towers receives occupancy certificate for 3 towers",
     "Maharashtra RERA acknowledges receipt and Lodha Group completes OC formalities for three towers at its premium Lower Parel project.",
     0.75, SentimentLabel.positive, NewsCategory.positive, "Times of India",
     _dt("2024-11-20T09:30:00")),

    # Prestige — mostly positive, one delay flag
    (1, None,
     "Prestige Estates Q2 FY25: Revenue up 28%, launches in 4 new cities",
     "Prestige Estates delivered strong Q2 numbers backed by robust demand in Bengaluru. The developer also announced expansion into Hyderabad and Chennai.",
     0.68, SentimentLabel.positive, NewsCategory.positive, "Moneycontrol",
     _dt("2024-10-28T11:15:00")),

    (1, 7,
     "Prestige Tech Vista commercial tower faces 6-month possession delay",
     "Buyers at Prestige Tech Vista's commercial project on Sarjapur Road have been notified of a revised possession timeline following civil work delays.",
     -0.42, SentimentLabel.negative, NewsCategory.delay, "Deccan Herald",
     _dt("2024-09-05T14:00:00")),

    (1, 5,
     "Prestige Lakeside Habitat wins CREDAI Best Township Award",
     "The 100-acre Prestige Lakeside Habitat in Whitefield has been recognised for sustainable design and timely construction.",
     0.79, SentimentLabel.positive, NewsCategory.positive, "Property Times",
     _dt("2024-08-22T10:00:00")),

    # BuildRight — negative / critical
    (2, None,
     "BuildRight Properties dragged to NCLT by creditor banks over ₹480 crore default",
     "A consortium of three lenders has filed insolvency proceedings against BuildRight Properties at the Mumbai NCLT Bench, citing non-repayment of project loans.",
     -0.91, SentimentLabel.critical, NewsCategory.nclt, "Business Standard",
     _dt("2024-03-12T08:00:00")),

    (2, 11,
     "MahaRERA cancels registration of BuildRight Powai Greens over 4-year delay",
     "Maharashtra RERA has lapsed the registration of BuildRight Powai Greens after the project failed to meet milestones for the fourth consecutive year.",
     -0.88, SentimentLabel.critical, NewsCategory.delay, "Times of India",
     _dt("2024-01-18T09:00:00")),

    (2, 10,
     "Homebuyers at BuildRight Andheri Heights demand refund after 2-year delay",
     "Over 85 flat owners have served legal notices to BuildRight Properties demanding full refund with interest after possession was delayed by more than 24 months.",
     -0.76, SentimentLabel.critical, NewsCategory.fraud, "Housing News",
     _dt("2024-04-05T12:00:00")),

    (2, None,
     "BuildRight MCA filings found delayed; serious corporate governance concerns",
     "Ministry of Corporate Affairs has flagged BuildRight Properties for consistent delays in annual filing, raising red flags for prospective buyers.",
     -0.65, SentimentLabel.negative, NewsCategory.financial_stress, "Economic Times",
     _dt("2024-02-20T10:30:00")),

    # GreenArch — mixed/neutral
    (3, None,
     "GreenArch Developers receives IGBC green certification for Whitefield project",
     "The startup developer GreenArch has received IGBC Gold rating for its EcoHomes project in Whitefield, bolstering its sustainability positioning.",
     0.62, SentimentLabel.positive, NewsCategory.positive, "Hindu Business Line",
     _dt("2024-07-10T11:00:00")),

    (3, 15,
     "GreenArch EcoHomes Whitefield: delayed by 6 months due to monsoon disruption",
     "Construction timelines at GreenArch's debut project have slipped by two quarters due to heavy monsoon and material cost escalations.",
     -0.38, SentimentLabel.negative, NewsCategory.delay, "Bangalore Mirror",
     _dt("2024-08-14T14:00:00")),

    # Skyline — critical
    (4, None,
     "Skyline Real Estate chairman arrested in multi-crore homebuyer fraud case",
     "Mumbai Police Economic Offences Wing arrested Skyline Real Estate's chairman for alleged diversion of buyer funds worth ₹320 crore from three stalled projects.",
     -0.98, SentimentLabel.critical, NewsCategory.fraud, "Times of India",
     _dt("2024-05-08T07:30:00")),

    (4, 18,
     "Skyline Majestic Towers declared abandoned; RERA recommends criminal probe",
     "Maharashtra RERA has classified Skyline Majestic Towers as an abandoned project and recommended a criminal investigation into fund diversion.",
     -0.95, SentimentLabel.critical, NewsCategory.nclt, "Economic Times",
     _dt("2024-06-15T09:00:00")),

    (4, 19,
     "Courts freeze Skyline BKC Residences escrow accounts on buyer petition",
     "Bombay High Court granted interim relief to over 140 buyers at Skyline BKC Residences, freezing all construction escrow accounts pending inquiry.",
     -0.87, SentimentLabel.critical, NewsCategory.fraud, "Business Standard",
     _dt("2024-07-01T10:00:00")),

    # Market & macro positive news
    (None, None,
     "India real estate market hits record ₹3.47 lakh crore in FY24 sales",
     "Residential and commercial real estate sales reached an all-time high in FY24, driven by end-user demand and NRI investment in Mumbai, Pune, and Bengaluru.",
     0.72, SentimentLabel.positive, NewsCategory.positive, "Moneycontrol",
     _dt("2024-04-22T10:00:00")),

    (None, None,
     "RBI keeps repo rate unchanged at 6.5%; positive signal for housing demand",
     "The Monetary Policy Committee held the repo rate steady, providing stability to home loan EMIs and sustaining demand momentum in the real estate sector.",
     0.55, SentimentLabel.positive, NewsCategory.positive, "Economic Times",
     _dt("2024-08-08T11:00:00")),

    (None, None,
     "Bengaluru residential sales up 18% YoY driven by IT sector hiring",
     "Record hiring in Bengaluru's tech corridor has pushed residential demand to a 10-year high, with Whitefield and Sarjapur Road emerging as hotspots.",
     0.65, SentimentLabel.positive, NewsCategory.positive, "Property Times",
     _dt("2024-09-12T09:00:00")),

    # Project-specific positive
    (0, 2,
     "Lodha Bellissimo receives final OC; possession ceremonies begin",
     "Lodha Group has received the occupancy certificate for all towers at Bellissimo, Mahalaxmi, and begun handing over keys to 172 apartment owners.",
     0.88, SentimentLabel.positive, NewsCategory.positive, "Times of India",
     _dt("2024-10-05T12:00:00")),

    (1, 7,
     "Prestige Kew Gardens 100% sold out; secondary market prices up 22%",
     "The premium project in Koramangala has been fully sold and resale prices have appreciated 22% since launch.",
     0.84, SentimentLabel.positive, NewsCategory.positive, "Deccan Herald",
     _dt("2024-09-25T14:00:00")),

    (2, 12,
     "RERA orders BuildRight to refund buyers of Hinjewadi IT Park with 10.85% interest",
     "Maharashtra RERA has ordered BuildRight Properties to refund all buyers of its commercial Hinjewadi project with statutory interest after lapse of RERA registration.",
     -0.70, SentimentLabel.negative, NewsCategory.delay, "Housing News",
     _dt("2024-11-01T10:00:00")),
]


# ─── Transaction definitions ──────────────────────────────────────────────────

# (project_index, micromarket, city, price_psf, carpet_sqft, tx_date, unit_type, floor_no)
TRANSACTION_DATA = [
    # Mumbai — Powai
    (None, "Powai", "Mumbai", 22000.0, 850.0, _date("2024-03-15"), "2BHK", 8),
    (None, "Powai", "Mumbai", 23500.0, 1100.0, _date("2024-05-10"), "3BHK", 14),
    (None, "Powai", "Mumbai", 21800.0, 750.0, _date("2024-01-22"), "2BHK", 5),
    (None, "Powai", "Mumbai", 24200.0, 1200.0, _date("2023-11-08"), "3BHK", 20),
    (None, "Powai", "Mumbai", 20500.0, 680.0, _date("2023-09-14"), "1BHK", 3),

    # Mumbai — BKC
    (None, "BKC", "Mumbai", 38000.0, 900.0, _date("2024-06-05"), "2BHK", 12),
    (None, "BKC", "Mumbai", 41000.0, 1500.0, _date("2024-04-18"), "3BHK", 18),
    (None, "BKC", "Mumbai", 36500.0, 1100.0, _date("2024-02-28"), "2BHK", 9),
    (None, "BKC", "Mumbai", 44000.0, 2000.0, _date("2023-12-15"), "office", 22),

    # Mumbai — Andheri East
    (None, "Andheri East", "Mumbai", 18500.0, 650.0, _date("2024-07-10"), "2BHK", 6),
    (None, "Andheri East", "Mumbai", 19200.0, 900.0, _date("2024-05-25"), "2BHK", 11),
    (None, "Andheri East", "Mumbai", 17800.0, 550.0, _date("2024-03-20"), "1BHK", 4),

    # Mumbai — Lower Parel
    (0, "Lower Parel", "Mumbai", 29000.0, 1050.0, _date("2024-08-12"), "2BHK", 16),
    (0, "Lower Parel", "Mumbai", 32000.0, 1400.0, _date("2024-06-30"), "3BHK", 24),
    (0, "Lower Parel", "Mumbai", 27500.0, 900.0, _date("2024-04-14"), "2BHK", 10),

    # Mumbai — Thane West
    (None, "Thane West", "Mumbai", 13500.0, 750.0, _date("2024-09-01"), "2BHK", 7),
    (None, "Thane West", "Mumbai", 14200.0, 1000.0, _date("2024-07-15"), "3BHK", 12),

    # Bengaluru — Whitefield
    (5, "Whitefield", "Bengaluru", 8000.0, 1050.0, _date("2024-08-20"), "2BHK", 5),
    (5, "Whitefield", "Bengaluru", 8800.0, 1500.0, _date("2024-07-05"), "3BHK", 9),
    (5, "Whitefield", "Bengaluru", 7600.0, 950.0, _date("2024-05-18"), "2BHK", 3),
    (None, "Whitefield", "Bengaluru", 7200.0, 850.0, _date("2024-03-22"), "2BHK", 6),
    (None, "Whitefield", "Bengaluru", 9200.0, 1800.0, _date("2024-01-15"), "4BHK", 14),

    # Bengaluru — Koramangala
    (7, "Koramangala", "Bengaluru", 16000.0, 1500.0, _date("2024-09-10"), "3BHK", 8),
    (7, "Koramangala", "Bengaluru", 18000.0, 2000.0, _date("2024-07-22"), "4BHK", 15),
    (None, "Koramangala", "Bengaluru", 15500.0, 1200.0, _date("2024-06-05"), "3BHK", 5),

    # Bengaluru — HSR Layout
    (None, "HSR Layout", "Bengaluru", 11500.0, 1100.0, _date("2024-10-01"), "3BHK", 7),
    (None, "HSR Layout", "Bengaluru", 12000.0, 1400.0, _date("2024-08-15"), "3BHK", 10),
    (16, "HSR Layout", "Bengaluru", 11000.0, 1150.0, _date("2024-07-08"), "3BHK", 4),

    # Bengaluru — Sarjapur Road
    (None, "Sarjapur Road", "Bengaluru", 10500.0, 1200.0, _date("2024-09-20"), "3BHK", 6),
    (None, "Sarjapur Road", "Bengaluru", 9800.0, 950.0, _date("2024-06-25"), "2BHK", 3),

    # Pune — Hinjewadi
    (3, "Hinjewadi", "Pune", 10000.0, 850.0, _date("2024-08-05"), "2BHK", 6),
    (3, "Hinjewadi", "Pune", 11200.0, 1100.0, _date("2024-05-20"), "3BHK", 12),
    (None, "Hinjewadi", "Pune", 9500.0, 750.0, _date("2024-03-10"), "2BHK", 4),
    (None, "Hinjewadi", "Pune", 12000.0, 1400.0, _date("2024-01-28"), "3BHK", 8),

    # Pune — Baner
    (None, "Baner", "Pune", 9200.0, 900.0, _date("2024-10-12"), "2BHK", 5),
    (None, "Baner", "Pune", 10100.0, 1200.0, _date("2024-08-30"), "3BHK", 9),
    (13, "Baner", "Pune", 8800.0, 780.0, _date("2024-07-10"), "2BHK", 3),

    # Pune — Kharadi
    (9, "Kharadi", "Pune", 8800.0, 950.0, _date("2024-11-01"), "2BHK", 7),
    (9, "Kharadi", "Pune", 9500.0, 1300.0, _date("2024-09-15"), "3BHK", 11),
    (None, "Kharadi", "Pune", 8200.0, 800.0, _date("2024-07-25"), "2BHK", 4),

    # Historical transactions (2022-2023) for price trend data
    (None, "Whitefield", "Bengaluru", 6800.0, 1050.0, _date("2022-06-15"), "2BHK", 5),
    (None, "Whitefield", "Bengaluru", 7100.0, 1050.0, _date("2023-01-10"), "2BHK", 5),
    (None, "Powai", "Mumbai", 19000.0, 850.0, _date("2022-04-20"), "2BHK", 8),
    (None, "Powai", "Mumbai", 20500.0, 850.0, _date("2023-02-14"), "2BHK", 8),
    (None, "Hinjewadi", "Pune", 8200.0, 900.0, _date("2022-05-08"), "2BHK", 5),
    (None, "Hinjewadi", "Pune", 9000.0, 900.0, _date("2023-03-22"), "2BHK", 5),
    (None, "Koramangala", "Bengaluru", 13500.0, 1400.0, _date("2022-08-12"), "3BHK", 8),
    (None, "Koramangala", "Bengaluru", 14800.0, 1400.0, _date("2023-05-30"), "3BHK", 8),
    (None, "BKC", "Mumbai", 32000.0, 900.0, _date("2022-10-05"), "2BHK", 12),
    (None, "BKC", "Mumbai", 35000.0, 900.0, _date("2023-07-18"), "2BHK", 12),
]


# ─── Seed function ────────────────────────────────────────────────────────────

async def clear_database(db: AsyncSession) -> None:
    """Truncate all tables in dependency order."""
    for table in [
        "news_items", "complaints", "transactions", "risk_scores",
        "projects", "developers", "users",
    ]:
        await db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    await db.commit()
    print("Cleared existing data.")


async def seed_database(db: AsyncSession) -> None:
    """Populate the database with realistic test data."""
    print("Seeding PropIQ database...")

    # ── 1. Users ──────────────────────────────────────────────────────────────
    users = [
        User(
            email="free@propiq.test",
            hashed_password=get_password_hash("Test1234!"),
            full_name="Free User",
            subscription_tier=SubscriptionTier.free,
            preferred_cities=["Mumbai"],
            risk_appetite=RiskAppetite.moderate,
            watchlist_project_ids=[],
            is_active=True,
        ),
        User(
            email="pro@propiq.test",
            hashed_password=get_password_hash("Test1234!"),
            full_name="Pro Investor",
            subscription_tier=SubscriptionTier.pro,
            preferred_cities=["Mumbai", "Bengaluru"],
            risk_appetite=RiskAppetite.aggressive,
            watchlist_project_ids=[],
            is_active=True,
            is_nri=True,
            budget_min=5_000_000.0,
            budget_max=30_000_000.0,
        ),
    ]
    db.add_all(users)
    await db.flush()
    print(f"  Created {len(users)} users.")

    # ── 2. Developers ─────────────────────────────────────────────────────────
    devs: list[Developer] = []
    for d in DEVELOPER_DATA:
        dev = Developer(
            name=d["name"],
            mca_cin=d["mca_cin"],
            city_hq=d["city_hq"],
            founded_year=d["founded_year"],
            website=d.get("website"),
            total_projects_delivered=d["total_projects_delivered"],
            projects_on_time_pct=d["projects_on_time_pct"],
            total_units_delivered=d["total_units_delivered"],
            active_complaint_count=d["active_complaint_count"],
            resolved_complaint_count=d["resolved_complaint_count"],
            financial_stress_score=d["financial_stress_score"],
            mca_filing_status=d["mca_filing_status"],
            nclt_proceedings=d["nclt_proceedings"],
            nclt_details=d.get("nclt_details"),
            rera_registration_ids=d.get("rera_registration_ids"),
            last_scraped_at=datetime.now(timezone.utc),
        )
        devs.append(dev)
    db.add_all(devs)
    await db.flush()
    print(f"  Created {len(devs)} developers.")

    # ── 3. Projects ───────────────────────────────────────────────────────────
    projects: list[Project] = []
    for row in PROJECT_DATA:
        (dev_idx, name, city, micromarket, rera_no, ptype,
         total_units, units_sold, cmin, cmax, pmin, pmax,
         poss_declared, poss_latest, cpct, oc_status, rera_status) = row

        proj = Project(
            developer_id=devs[dev_idx].id,
            name=name,
            rera_registration_no=rera_no,
            project_type=ptype,
            city=city,
            micromarket=micromarket,
            total_units=total_units,
            units_sold=units_sold,
            carpet_area_min=cmin,
            carpet_area_max=cmax,
            price_psf_min=pmin,
            price_psf_max=pmax,
            possession_date_declared=poss_declared,
            possession_date_latest=poss_latest,
            construction_pct=cpct,
            oc_status=oc_status,
            rera_status=rera_status,
            last_scraped_at=datetime.now(timezone.utc),
            amenities={"gym": True, "swimming_pool": True, "parking": True},
        )
        projects.append(proj)
    db.add_all(projects)
    await db.flush()
    print(f"  Created {len(projects)} projects.")

    # ── 4. Complaints ─────────────────────────────────────────────────────────
    complaints: list[Complaint] = []
    for row in COMPLAINT_DATA:
        (dev_idx, proj_idx, portal, complaint_no, complaint_date,
         status, category, resolution_date) = row

        c = Complaint(
            developer_id=devs[dev_idx].id,
            project_id=projects[proj_idx].id if proj_idx is not None else None,
            rera_portal=portal,
            complaint_no=complaint_no,
            complaint_date=complaint_date,
            status=status,
            category=category,
            resolution_date=resolution_date,
        )
        complaints.append(c)
    db.add_all(complaints)
    await db.flush()
    print(f"  Created {len(complaints)} complaints.")

    # ── 5. News items ─────────────────────────────────────────────────────────
    news_items: list[NewsItem] = []
    for row in NEWS_DATA:
        (dev_idx, proj_idx, headline, summary, sentiment_score,
         sentiment_label, category, source_name, published_at) = row

        n = NewsItem(
            developer_id=devs[dev_idx].id if dev_idx is not None else None,
            project_id=projects[proj_idx].id if proj_idx is not None else None,
            headline=headline,
            summary=summary,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            category=category,
            source_name=source_name,
            published_at=published_at,
        )
        news_items.append(n)
    db.add_all(news_items)
    await db.flush()
    print(f"  Created {len(news_items)} news items.")

    # ── 6. Transactions ───────────────────────────────────────────────────────
    transactions: list[Transaction] = []
    for row in TRANSACTION_DATA:
        (proj_idx, micromarket, city, price_psf, carpet_sqft, tx_date,
         unit_type, floor_no) = row

        source_map = {"Mumbai": "igr_maharashtra", "Bengaluru": "kaveri_karnataka",
                      "Pune": "igr_maharashtra"}

        t = Transaction(
            project_id=projects[proj_idx].id if proj_idx is not None else None,
            micromarket=micromarket,
            city=city,
            price_psf=price_psf,
            carpet_area_sqft=carpet_sqft,
            total_price=price_psf * carpet_sqft,
            transaction_date=tx_date,
            registration_no=f"REG/{city[:3].upper()}/{tx_date.year}/{uuid.uuid4().hex[:8].upper()}",
            unit_type=unit_type,
            floor_no=floor_no,
            source=source_map.get(city, "igr_maharashtra"),
        )
        transactions.append(t)
    db.add_all(transactions)
    await db.flush()
    print(f"  Created {len(transactions)} transactions.")

    # ── 7. Risk scores (via RiskEngine) ──────────────────────────────────────
    engine = RiskEngine()
    scored = 0
    for proj in projects:
        # Load related complaints for this project
        proj_complaints = [
            c for c in complaints if c.project_id == proj.id
        ]
        dev = next(d for d in devs if d.id == proj.developer_id)

        legal_score, legal_flags = engine.calculate_legal_score(proj, proj_complaints)
        dev_score, dev_flags = engine.calculate_developer_score(dev, proj_complaints)
        proj_score, proj_flags = engine.calculate_project_score(proj)
        location_score, _ = engine.calculate_location_score(proj, [])
        financial_score, _ = engine.calculate_financial_score(proj, dev)
        macro_score, _ = engine.calculate_macro_score(proj)

        composite = (
            legal_score    * 0.25
            + dev_score    * 0.25
            + proj_score   * 0.20
            + location_score * 0.15
            + financial_score * 0.10
            + macro_score  * 0.05
        )
        composite = max(0.0, min(100.0, composite))

        band: RiskBand
        if composite >= 80:
            band = RiskBand.low
        elif composite >= 60:
            band = RiskBand.medium
        elif composite >= 40:
            band = RiskBand.high
        else:
            band = RiskBand.critical

        # Determine confidence based on data completeness
        fields_present = sum([
            proj.rera_registration_no is not None,
            proj.construction_pct is not None,
            proj.possession_date_declared is not None,
            proj.units_sold is not None,
        ])
        if fields_present >= 4:
            confidence = ConfidenceLevel.high
        elif fields_present >= 2:
            confidence = ConfidenceLevel.medium
        else:
            confidence = ConfidenceLevel.low

        # Simple appreciation estimate
        city_cagr = {"Mumbai": 8.5, "Bengaluru": 11.0, "Pune": 10.0}.get(proj.city, 9.0)
        risk_adj = max(city_cagr - (100 - composite) * 0.05, 2.0)

        rs = RiskScore(
            project_id=proj.id,
            composite_score=composite,
            risk_band=band,
            legal_score=legal_score,
            developer_score=dev_score,
            project_score=proj_score,
            location_score=location_score,
            financial_score=financial_score,
            macro_score=macro_score,
            legal_flags=legal_flags,
            developer_flags=dev_flags,
            project_flags=proj_flags,
            confidence_level=confidence,
            appreciation_3yr_base=round(risk_adj, 1),
            appreciation_3yr_bull=round(risk_adj + 3.0, 1),
            appreciation_3yr_bear=round(max(risk_adj - 4.0, 1.0), 1),
            appreciation_5yr_base=round(risk_adj + 0.5, 1),
            rental_yield_estimate=round(
                {"Mumbai": 2.8, "Bengaluru": 3.5, "Pune": 3.2}.get(proj.city, 3.0), 1
            ),
            is_current=True,
            scoring_version=engine.SCORING_VERSION,
            data_freshness={
                "rera": datetime.now(timezone.utc).isoformat(),
                "mca": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(rs)
        scored += 1

    await db.flush()
    print(f"  Generated {scored} risk scores.")

    await db.commit()
    print(
        f"\nSeed complete: {len(users)} users, {len(devs)} developers, "
        f"{len(projects)} projects, {len(complaints)} complaints, "
        f"{len(news_items)} news items, {len(transactions)} transactions, "
        f"{scored} risk scores."
    )


# ─── CLI entry point ──────────────────────────────────────────────────────────

async def main() -> None:
    await create_all_tables()
    async with AsyncSessionLocal() as db:
        await clear_database(db)
        await seed_database(db)


if __name__ == "__main__":
    asyncio.run(main())
