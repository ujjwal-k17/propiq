"""
RERA Scraper — Maharashtra
==========================
Scrapes project registrations, quarterly updates and complaints from
MahaRERA (maharera.mahaonline.gov.in).

In development (ENVIRONMENT=development), all HTTP calls are replaced by
``MockDataProvider`` which returns 20 realistic synthetic projects covering
Mumbai and Bangalore.  This lets the rest of the pipeline run end-to-end
without hitting the live government portal.

In production (ENVIRONMENT=production), live HTTP scraping is performed.
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import date, timedelta
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.developer import Developer, McaFilingStatus
from app.models.project import OcStatus, Project, ProjectType, ReraStatus
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


# ── Mock data provider ────────────────────────────────────────────────────────

class MockDataProvider:
    """
    Returns 20 realistic synthetic RERA projects for local development.
    Profiles are deliberately varied: low-risk flagships, medium-risk
    mid-market, high-risk delayed projects, and critical NCLT/revoked cases.
    """

    _PROJECTS: list[dict] = [
        # ── Mumbai — Low risk ──────────────────────────────────────────────
        {
            "rera_no": "P51800045001",
            "name": "Lodha Altamount",
            "developer_name": "Lodha Developers Pvt Ltd",
            "developer_cin": "U45200MH1995PTC094767",
            "city": "Mumbai",
            "micromarket": "Altamount Road",
            "state": "Maharashtra",
            "registration_date": "2022-03-15",
            "possession_date_declared": "2025-06-30",
            "possession_date_latest": "2025-06-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 48,
            "units_sold": 42,
            "construction_pct": 88.0,
            "price_psf_min": 65000.0,
            "price_psf_max": 85000.0,
            "carpet_area_min": 1800.0,
            "complaint_count": 0,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 10.0,
            "projects_on_time_pct": 92.0,
        },
        {
            "rera_no": "P51800045002",
            "name": "Godrej BKC 9",
            "developer_name": "Godrej Properties Ltd",
            "developer_cin": "L74120MH1985PLC035308",
            "city": "Mumbai",
            "micromarket": "BKC",
            "state": "Maharashtra",
            "registration_date": "2021-08-20",
            "possession_date_declared": "2024-12-31",
            "possession_date_latest": "2025-03-31",
            "rera_status": "active",
            "oc_status": "applied",
            "units_total": 120,
            "units_sold": 108,
            "construction_pct": 97.0,
            "price_psf_min": 38000.0,
            "price_psf_max": 52000.0,
            "carpet_area_min": 650.0,
            "complaint_count": 2,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 15.0,
            "projects_on_time_pct": 85.0,
        },
        {
            "rera_no": "P51800045003",
            "name": "Oberoi Elysian Goregaon",
            "developer_name": "Oberoi Realty Ltd",
            "developer_cin": "L45200MH1998PLC114168",
            "city": "Mumbai",
            "micromarket": "Goregaon East",
            "state": "Maharashtra",
            "registration_date": "2022-11-10",
            "possession_date_declared": "2026-03-31",
            "possession_date_latest": "2026-03-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 240,
            "units_sold": 195,
            "construction_pct": 72.0,
            "price_psf_min": 22000.0,
            "price_psf_max": 28000.0,
            "carpet_area_min": 800.0,
            "complaint_count": 1,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 12.0,
            "projects_on_time_pct": 90.0,
        },
        # ── Mumbai — Medium risk ───────────────────────────────────────────
        {
            "rera_no": "P51800045004",
            "name": "Kalpataru Paramount Thane",
            "developer_name": "Kalpataru Ltd",
            "developer_cin": "U45200MH1969PLC014474",
            "city": "Thane",
            "micromarket": "Thane West",
            "state": "Maharashtra",
            "registration_date": "2021-04-05",
            "possession_date_declared": "2024-06-30",
            "possession_date_latest": "2025-09-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 380,
            "units_sold": 240,
            "construction_pct": 65.0,
            "price_psf_min": 11500.0,
            "price_psf_max": 14500.0,
            "carpet_area_min": 600.0,
            "complaint_count": 8,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 30.0,
            "projects_on_time_pct": 68.0,
        },
        {
            "rera_no": "P51800045005",
            "name": "Rustomjee Urbania Dahisar",
            "developer_name": "Rustomjee Developers Pvt Ltd",
            "developer_cin": "U45400MH2003PTC143682",
            "city": "Mumbai",
            "micromarket": "Dahisar",
            "state": "Maharashtra",
            "registration_date": "2020-09-12",
            "possession_date_declared": "2023-12-31",
            "possession_date_latest": "2025-06-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 450,
            "units_sold": 310,
            "construction_pct": 55.0,
            "price_psf_min": 9500.0,
            "price_psf_max": 12000.0,
            "carpet_area_min": 550.0,
            "complaint_count": 14,
            "nclt": False,
            "mca_filing_status": "delayed",
            "financial_stress_score": 42.0,
            "projects_on_time_pct": 60.0,
        },
        {
            "rera_no": "P51800045006",
            "name": "Piramal Vaikunth Thane",
            "developer_name": "Piramal Realty Pvt Ltd",
            "developer_cin": "U45400MH2012PTC228817",
            "city": "Thane",
            "micromarket": "Balkum",
            "state": "Maharashtra",
            "registration_date": "2021-07-20",
            "possession_date_declared": "2025-03-31",
            "possession_date_latest": "2025-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 600,
            "units_sold": 388,
            "construction_pct": 62.0,
            "price_psf_min": 10800.0,
            "price_psf_max": 13500.0,
            "carpet_area_min": 580.0,
            "complaint_count": 11,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 35.0,
            "projects_on_time_pct": 65.0,
        },
        # ── Mumbai — High risk ─────────────────────────────────────────────
        {
            "rera_no": "P51800045007",
            "name": "Omkar Alta Monte Malad",
            "developer_name": "Omkar Realtors & Developers Pvt Ltd",
            "developer_cin": "U45200MH2005PTC152890",
            "city": "Mumbai",
            "micromarket": "Malad East",
            "state": "Maharashtra",
            "registration_date": "2018-06-15",
            "possession_date_declared": "2021-12-31",
            "possession_date_latest": "2026-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 850,
            "units_sold": 620,
            "construction_pct": 35.0,
            "price_psf_min": 18000.0,
            "price_psf_max": 24000.0,
            "carpet_area_min": 700.0,
            "complaint_count": 38,
            "nclt": False,
            "mca_filing_status": "delayed",
            "financial_stress_score": 65.0,
            "projects_on_time_pct": 35.0,
        },
        {
            "rera_no": "P51800045008",
            "name": "HDIL Residency Park 2",
            "developer_name": "Housing Development & Infrastructure Ltd",
            "developer_cin": "L70100MH1996PLC101379",
            "city": "Mumbai",
            "micromarket": "Virar",
            "state": "Maharashtra",
            "registration_date": "2017-03-10",
            "possession_date_declared": "2020-06-30",
            "possession_date_latest": "2027-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 1200,
            "units_sold": 980,
            "construction_pct": 18.0,
            "price_psf_min": 6500.0,
            "price_psf_max": 8200.0,
            "carpet_area_min": 500.0,
            "complaint_count": 72,
            "nclt": True,
            "nclt_details": "NCLT Mumbai Bench — Insolvency Petition No. IB-1023/MB/2023",
            "mca_filing_status": "defaulted",
            "financial_stress_score": 88.0,
            "projects_on_time_pct": 15.0,
        },
        # ── Mumbai — Critical ──────────────────────────────────────────────
        {
            "rera_no": "P51800045009",
            "name": "DB Realty Sky Tower",
            "developer_name": "DB Realty Ltd",
            "developer_cin": "L45400MH1996PLC103939",
            "city": "Mumbai",
            "micromarket": "Mira Road",
            "state": "Maharashtra",
            "registration_date": "2016-11-20",
            "possession_date_declared": "2019-12-31",
            "possession_date_latest": "2028-06-30",
            "rera_status": "lapsed",
            "oc_status": "not_applied",
            "units_total": 780,
            "units_sold": 710,
            "construction_pct": 12.0,
            "price_psf_min": 8000.0,
            "price_psf_max": 10500.0,
            "carpet_area_min": 520.0,
            "complaint_count": 115,
            "nclt": True,
            "nclt_details": "NCLT Mumbai — Corporate Insolvency Resolution Process initiated",
            "mca_filing_status": "defaulted",
            "financial_stress_score": 95.0,
            "projects_on_time_pct": 8.0,
        },
        {
            "rera_no": "P51800045010",
            "name": "Radius Alchemy",
            "developer_name": "Radius Developers Pvt Ltd",
            "developer_cin": "U45200MH2007PTC173891",
            "city": "Mumbai",
            "micromarket": "Santacruz West",
            "state": "Maharashtra",
            "registration_date": "2017-08-14",
            "possession_date_declared": "2021-06-30",
            "possession_date_latest": None,
            "rera_status": "revoked",
            "oc_status": "not_applied",
            "units_total": 120,
            "units_sold": 102,
            "construction_pct": 22.0,
            "price_psf_min": 32000.0,
            "price_psf_max": 42000.0,
            "carpet_area_min": 1100.0,
            "complaint_count": 48,
            "nclt": True,
            "nclt_details": "NCLT Mumbai — Order dated 12-Jan-2024",
            "mca_filing_status": "defaulted",
            "financial_stress_score": 92.0,
            "projects_on_time_pct": 10.0,
        },
        # ── Bangalore — Low risk ───────────────────────────────────────────
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003001",
            "name": "Prestige Lakeside Habitat",
            "developer_name": "Prestige Estates Projects Ltd",
            "developer_cin": "L45200KA1997PLC022322",
            "city": "Bengaluru",
            "micromarket": "Whitefield",
            "state": "Karnataka",
            "registration_date": "2021-05-18",
            "possession_date_declared": "2025-09-30",
            "possession_date_latest": "2025-09-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 500,
            "units_sold": 462,
            "construction_pct": 85.0,
            "price_psf_min": 8500.0,
            "price_psf_max": 11000.0,
            "carpet_area_min": 720.0,
            "complaint_count": 1,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 8.0,
            "projects_on_time_pct": 88.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003002",
            "name": "Brigade Orchards",
            "developer_name": "Brigade Enterprises Ltd",
            "developer_cin": "L45200KA1995PLC018795",
            "city": "Bengaluru",
            "micromarket": "Devanahalli",
            "state": "Karnataka",
            "registration_date": "2020-10-22",
            "possession_date_declared": "2024-12-31",
            "possession_date_latest": "2025-06-30",
            "rera_status": "active",
            "oc_status": "applied",
            "units_total": 1200,
            "units_sold": 1050,
            "construction_pct": 94.0,
            "price_psf_min": 6200.0,
            "price_psf_max": 8500.0,
            "carpet_area_min": 800.0,
            "complaint_count": 3,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 11.0,
            "projects_on_time_pct": 82.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003003",
            "name": "Sobha Dream Acres",
            "developer_name": "Sobha Ltd",
            "developer_cin": "L45201KA1995PLC019899",
            "city": "Bengaluru",
            "micromarket": "Panathur",
            "state": "Karnataka",
            "registration_date": "2021-02-08",
            "possession_date_declared": "2025-12-31",
            "possession_date_latest": "2025-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 6000,
            "units_sold": 5400,
            "construction_pct": 78.0,
            "price_psf_min": 7200.0,
            "price_psf_max": 9800.0,
            "carpet_area_min": 680.0,
            "complaint_count": 4,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 14.0,
            "projects_on_time_pct": 91.0,
        },
        # ── Bangalore — Medium risk ────────────────────────────────────────
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003004",
            "name": "Manyata Tech Park Residences",
            "developer_name": "Manyata Promoters Pvt Ltd",
            "developer_cin": "U45200KA2007PTC043621",
            "city": "Bengaluru",
            "micromarket": "Hebbal",
            "state": "Karnataka",
            "registration_date": "2020-12-15",
            "possession_date_declared": "2024-03-31",
            "possession_date_latest": "2025-09-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 320,
            "units_sold": 198,
            "construction_pct": 58.0,
            "price_psf_min": 9200.0,
            "price_psf_max": 12500.0,
            "carpet_area_min": 760.0,
            "complaint_count": 9,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 38.0,
            "projects_on_time_pct": 62.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003005",
            "name": "Puravankara Purva Atmosphere",
            "developer_name": "Puravankara Ltd",
            "developer_cin": "L45201KA1986PLC007880",
            "city": "Bengaluru",
            "micromarket": "Thanisandra",
            "state": "Karnataka",
            "registration_date": "2021-09-05",
            "possession_date_declared": "2025-06-30",
            "possession_date_latest": "2026-03-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 480,
            "units_sold": 312,
            "construction_pct": 52.0,
            "price_psf_min": 8800.0,
            "price_psf_max": 11200.0,
            "carpet_area_min": 700.0,
            "complaint_count": 7,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 28.0,
            "projects_on_time_pct": 71.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003006",
            "name": "Assetz Canvas & Cove",
            "developer_name": "Assetz Property Group Pvt Ltd",
            "developer_cin": "U45200KA2006FTC040481",
            "city": "Bengaluru",
            "micromarket": "Bagalur Road",
            "state": "Karnataka",
            "registration_date": "2022-01-18",
            "possession_date_declared": "2026-06-30",
            "possession_date_latest": "2026-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 800,
            "units_sold": 420,
            "construction_pct": 40.0,
            "price_psf_min": 6800.0,
            "price_psf_max": 9000.0,
            "carpet_area_min": 720.0,
            "complaint_count": 5,
            "nclt": False,
            "mca_filing_status": "compliant",
            "financial_stress_score": 32.0,
            "projects_on_time_pct": 58.0,
        },
        # ── Bangalore — High risk ──────────────────────────────────────────
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003007",
            "name": "Value Designbuild Provident Adora",
            "developer_name": "Provident Housing Ltd",
            "developer_cin": "U45201KA2007PLC043814",
            "city": "Bengaluru",
            "micromarket": "Kanakapura Road",
            "state": "Karnataka",
            "registration_date": "2019-07-22",
            "possession_date_declared": "2022-12-31",
            "possession_date_latest": "2026-06-30",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 1500,
            "units_sold": 1380,
            "construction_pct": 28.0,
            "price_psf_min": 5500.0,
            "price_psf_max": 7200.0,
            "carpet_area_min": 650.0,
            "complaint_count": 42,
            "nclt": False,
            "mca_filing_status": "delayed",
            "financial_stress_score": 62.0,
            "projects_on_time_pct": 38.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003008",
            "name": "Mantri Serene",
            "developer_name": "Mantri Developers Pvt Ltd",
            "developer_cin": "U45201KA1999PTC025706",
            "city": "Bengaluru",
            "micromarket": "Koramangala",
            "state": "Karnataka",
            "registration_date": "2018-04-10",
            "possession_date_declared": "2021-06-30",
            "possession_date_latest": "2026-12-31",
            "rera_status": "active",
            "oc_status": "not_applied",
            "units_total": 240,
            "units_sold": 228,
            "construction_pct": 32.0,
            "price_psf_min": 14500.0,
            "price_psf_max": 19000.0,
            "carpet_area_min": 950.0,
            "complaint_count": 31,
            "nclt": False,
            "mca_filing_status": "delayed",
            "financial_stress_score": 70.0,
            "projects_on_time_pct": 30.0,
        },
        # ── Bangalore — Critical ───────────────────────────────────────────
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003009",
            "name": "Nitesh Logos",
            "developer_name": "Nitesh Estates Ltd",
            "developer_cin": "L45200KA2004PLC033134",
            "city": "Bengaluru",
            "micromarket": "Bellary Road",
            "state": "Karnataka",
            "registration_date": "2016-09-15",
            "possession_date_declared": "2019-12-31",
            "possession_date_latest": None,
            "rera_status": "lapsed",
            "oc_status": "not_applied",
            "units_total": 300,
            "units_sold": 278,
            "construction_pct": 15.0,
            "price_psf_min": 11000.0,
            "price_psf_max": 15000.0,
            "carpet_area_min": 900.0,
            "complaint_count": 68,
            "nclt": True,
            "nclt_details": "NCLT Bengaluru — IRP appointed, moratorium in effect",
            "mca_filing_status": "defaulted",
            "financial_stress_score": 90.0,
            "projects_on_time_pct": 12.0,
        },
        {
            "rera_no": "PRM/KA/RERA/1251/310/PR/170200/003010",
            "name": "SJR Palazza",
            "developer_name": "SJR Prime Corporation Pvt Ltd",
            "developer_cin": "U45201KA2004PTC035612",
            "city": "Bengaluru",
            "micromarket": "Electronic City",
            "state": "Karnataka",
            "registration_date": "2017-11-30",
            "possession_date_declared": "2020-06-30",
            "possession_date_latest": None,
            "rera_status": "revoked",
            "oc_status": "not_applied",
            "units_total": 420,
            "units_sold": 395,
            "construction_pct": 10.0,
            "price_psf_min": 4800.0,
            "price_psf_max": 6200.0,
            "carpet_area_min": 600.0,
            "complaint_count": 89,
            "nclt": True,
            "nclt_details": "NCLT Bengaluru — liquidation order passed",
            "mca_filing_status": "defaulted",
            "financial_stress_score": 98.0,
            "projects_on_time_pct": 5.0,
        },
    ]

    def get_projects_by_city(self, city: str, max_pages: int = 5) -> list[dict]:
        city_lower = city.lower()
        # Normalise city aliases
        aliases = {
            "bangalore": "bengaluru",
            "bombay": "mumbai",
        }
        city_lower = aliases.get(city_lower, city_lower)
        return [
            p for p in self._PROJECTS
            if p["city"].lower() == city_lower or p["state"].lower() == city_lower
        ]

    def get_project_detail(self, rera_no: str) -> dict | None:
        for p in self._PROJECTS:
            if p["rera_no"] == rera_no:
                return p
        return None

    def all_projects(self) -> list[dict]:
        return list(self._PROJECTS)


_MOCK = MockDataProvider()


# ── Live scraper ──────────────────────────────────────────────────────────────

class RERAScraperMaharashtra(BaseScraper):
    """
    Scraper for MahaRERA (Maharashtra).
    In development mode delegates to ``MockDataProvider``.
    """

    BASE_URL = "https://maharera.mahaonline.gov.in"
    SOURCE_NAME = "maharera"

    _IS_DEV = settings.ENVIRONMENT.lower() == "development"

    async def scrape(self, *args: Any, **kwargs: Any) -> list[dict]:
        return await self.search_projects(**kwargs)

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_projects(
        self, query: str = "", city: str = "Mumbai", page: int = 1
    ) -> list[dict]:
        """
        Search RERA project registrations.
        Returns list of dicts with: rera_no, name, developer_name, city,
        micromarket, registration_date, possession_date_declared, status,
        units_total.
        """
        if self._IS_DEV:
            self.log(f"[mock] search_projects city={city} page={page}")
            results = _MOCK.get_projects_by_city(city)
            # Paginate mock results (10 per page)
            start = (page - 1) * 10
            return results[start : start + 10]

        # ── Live: POST to MahaRERA search API ─────────────────────────────
        endpoint = f"{self.BASE_URL}/Authenticated/Registration/Search"
        payload = {
            "SearchKeyword": query,
            "City": city,
            "PageNo": page,
            "PageSize": 10,
        }
        html = await self.fetch_page(endpoint, method="POST", data=payload)
        return self._parse_search_results(html)

    async def get_project_details(self, rera_no: str) -> dict:
        """
        Fetch full project detail.
        Returns all fields including construction_pct, units_sold,
        complaint_count, and approvals.
        """
        if self._IS_DEV:
            self.log(f"[mock] get_project_details rera_no={rera_no}")
            detail = _MOCK.get_project_detail(rera_no)
            if detail:
                return detail
            return {"rera_no": rera_no, "error": "not_found"}

        url = f"{self.BASE_URL}/Authenticated/Registration/ProjectDetail/{rera_no}"
        html = await self.fetch_page(url)
        return self._parse_project_detail(html, rera_no)

    async def get_developer_projects(self, developer_name: str) -> list[dict]:
        """Return all projects by a given developer name."""
        if self._IS_DEV:
            self.log(f"[mock] get_developer_projects developer={developer_name}")
            name_lower = developer_name.lower()
            return [
                p for p in _MOCK.all_projects()
                if name_lower in p["developer_name"].lower()
            ]

        return await self.search_projects(query=developer_name)

    async def scrape_and_store(
        self,
        db: AsyncSession,
        city: str = "Mumbai",
        max_pages: int = 5,
    ) -> dict:
        """
        Full ETL for a city:
        1. Fetch all pages of search results.
        2. For each project: upsert Project + Developer records.
        3. Trigger RiskEngine scoring for new/updated projects.

        Returns a summary dict with counts.
        """
        from app.services.risk_engine import RiskEngine

        engine = RiskEngine()
        summary = {"created": 0, "updated": 0, "scored": 0, "errors": 0}

        for page in range(1, max_pages + 1):
            projects = await self.search_projects(city=city, page=page)
            if not projects:
                break

            for raw in projects:
                try:
                    project, created = await self._upsert_project(raw, db)
                    if created:
                        summary["created"] += 1
                    else:
                        summary["updated"] += 1

                    await engine.score_project(project.id, db)
                    summary["scored"] += 1

                except Exception as exc:
                    self.log(
                        f"Error processing {raw.get('rera_no')}: {exc}",
                        level="error",
                    )
                    summary["errors"] += 1

            await db.commit()
            self.log(
                f"Page {page}/{max_pages} done — "
                f"created={summary['created']} updated={summary['updated']}"
            )

        return summary

    async def save(self, records: list[dict], db: Any) -> int:
        count = 0
        for raw in records:
            try:
                _, created = await self._upsert_project(raw, db)
                count += 1
            except Exception as exc:
                self.log(f"save error for {raw.get('rera_no')}: {exc}", level="error")
        await db.commit()
        return count

    # ── DB upsert helpers ─────────────────────────────────────────────────────

    async def _upsert_project(
        self, raw: dict, db: AsyncSession
    ) -> tuple[Project, bool]:
        """
        Upsert a Project (and its Developer) from a raw scrape dict.
        Returns (project, was_created).
        """
        developer = await self._upsert_developer(raw, db)

        # Check if project already exists by RERA number
        result = await db.execute(
            select(Project).where(
                Project.rera_registration_no == raw["rera_no"]
            )
        )
        existing: Project | None = result.scalar_one_or_none()

        # Parse dates
        def _parse_date(val: str | None) -> date | None:
            if not val:
                return None
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None

        rera_status_map = {
            "active": ReraStatus.active,
            "lapsed": ReraStatus.lapsed,
            "revoked": ReraStatus.revoked,
            "completed": ReraStatus.completed,
        }
        oc_status_map = {
            "not_applied": OcStatus.not_applied,
            "applied": OcStatus.applied,
            "received": OcStatus.received,
        }

        fields = {
            "name": raw["name"],
            "city": raw["city"],
            "micromarket": raw["micromarket"],
            "total_units": raw.get("units_total", 0),
            "units_sold": raw.get("units_sold"),
            "carpet_area_min": raw.get("carpet_area_min"),
            "price_psf_min": raw.get("price_psf_min"),
            "price_psf_max": raw.get("price_psf_max"),
            "possession_date_declared": _parse_date(raw.get("possession_date_declared")),
            "possession_date_latest": _parse_date(raw.get("possession_date_latest")),
            "construction_pct": raw.get("construction_pct"),
            "rera_status": rera_status_map.get(raw.get("rera_status", "active"), ReraStatus.active),
            "oc_status": oc_status_map.get(raw.get("oc_status", "not_applied"), OcStatus.not_applied),
        }

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            await db.flush()
            return existing, False
        else:
            project = Project(
                id=uuid.uuid4(),
                developer_id=developer.id,
                rera_registration_no=raw["rera_no"],
                project_type=ProjectType.residential,
                **fields,
            )
            db.add(project)
            await db.flush()
            return project, True

    async def _upsert_developer(self, raw: dict, db: AsyncSession) -> Developer:
        cin = raw.get("developer_cin")
        name = raw["developer_name"]

        # Look up by CIN first, then by name
        if cin:
            result = await db.execute(
                select(Developer).where(Developer.mca_cin == cin)
            )
            dev = result.scalar_one_or_none()
        else:
            result = await db.execute(
                select(Developer).where(Developer.name == name)
            )
            dev = result.scalar_one_or_none()

        mca_status_map = {
            "compliant": McaFilingStatus.compliant,
            "delayed": McaFilingStatus.delayed,
            "defaulted": McaFilingStatus.defaulted,
        }

        if dev:
            dev.nclt_proceedings = raw.get("nclt", False)
            dev.nclt_details = raw.get("nclt_details")
            dev.financial_stress_score = raw.get("financial_stress_score")
            dev.projects_on_time_pct = raw.get("projects_on_time_pct")
            dev.active_complaint_count = raw.get("complaint_count", 0)
            dev.mca_filing_status = mca_status_map.get(
                raw.get("mca_filing_status", "unknown"), McaFilingStatus.unknown
            )
            await db.flush()
            return dev

        dev = Developer(
            id=uuid.uuid4(),
            name=name,
            mca_cin=cin,
            nclt_proceedings=raw.get("nclt", False),
            nclt_details=raw.get("nclt_details"),
            financial_stress_score=raw.get("financial_stress_score"),
            projects_on_time_pct=raw.get("projects_on_time_pct"),
            active_complaint_count=raw.get("complaint_count", 0),
            mca_filing_status=mca_status_map.get(
                raw.get("mca_filing_status", "unknown"), McaFilingStatus.unknown
            ),
        )
        db.add(dev)
        await db.flush()
        return dev

    # ── Live HTML parsers (used in production) ────────────────────────────────

    def _parse_search_results(self, html: str) -> list[dict]:
        soup = self.parse_html(html)
        projects = []
        for row in soup.select("table.project-list tr[data-rera]"):
            projects.append({
                "rera_no": row.get("data-rera", ""),
                "name": self.extract_text(row.select_one(".project-name")),
                "developer_name": self.extract_text(row.select_one(".developer-name")),
                "city": self.extract_text(row.select_one(".city")),
                "micromarket": self.extract_text(row.select_one(".locality")),
                "registration_date": self.extract_text(row.select_one(".reg-date")),
                "possession_date_declared": self.extract_text(row.select_one(".possession-date")),
                "rera_status": "active",
                "units_total": int(self.extract_text(row.select_one(".total-units")) or 0),
            })
        return projects

    def _parse_project_detail(self, html: str, rera_no: str) -> dict:
        soup = self.parse_html(html)

        def _field(selector: str) -> str:
            el = soup.select_one(selector)
            return self.extract_text(el)

        return {
            "rera_no": rera_no,
            "name": _field(".project-title h1"),
            "developer_name": _field(".developer-info .name"),
            "city": _field(".location .city"),
            "micromarket": _field(".location .locality"),
            "registration_date": _field(".reg-details .reg-date"),
            "possession_date_declared": _field(".timeline .declared-date"),
            "possession_date_latest": _field(".timeline .revised-date"),
            "rera_status": _field(".status-badge").lower() or "active",
            "oc_status": "not_applied",
            "units_total": int(_field(".units .total") or 0),
            "units_sold": int(_field(".units .sold") or 0),
            "construction_pct": float(_field(".construction .progress") or 0),
            "complaint_count": int(_field(".complaints .count") or 0),
        }
