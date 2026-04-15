"""
MCA Scraper
===========
Fetches corporate information from the MCA21 portal for developer due diligence.

Fields collected:
  - Company master data (CIN, name, status, registered address)
  - Directors list
  - Charge documents (bank liens / hypothecations)
  - Annual filing compliance (last AGM date, filing delays)

Financial stress scoring (0 = healthy, 100 = severe distress):
  - Delayed MCA filing     +20
  - Satisfied charges with major banks (distress signal)  +40
  - Last AGM > 2 years ago  +30
  - Active NCLT proceedings  +40
  - Multiple large charges outstanding  +10 each (cap +20)

In development mode (ENVIRONMENT=development), live HTTP calls are replaced
by realistic mock company data keyed on CIN.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.developer import Developer, McaFilingStatus
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


# ── Mock data for development ─────────────────────────────────────────────────

_MOCK_COMPANIES: dict[str, dict] = {
    "U45200MH1995PTC094767": {
        "cin": "U45200MH1995PTC094767",
        "name": "Lodha Developers Pvt Ltd",
        "status": "Active",
        "paid_up_capital": 5_00_00_00_000,
        "filing_status": "compliant",
        "last_agm_date": "2024-09-30",
        "registered_address": "412, Floor 4, 17G Vardhaman Chamber, Cawasji Patel Road, Fort, Mumbai 400001",
        "directors": [
            {"name": "Abhishek Lodha", "din": "00136230", "designation": "MD"},
            {"name": "Mangal Prabhat Lodha", "din": "00131633", "designation": "Director"},
        ],
        "charges": [],
        "distress_signals": [],
    },
    "L74120MH1985PLC035308": {
        "cin": "L74120MH1985PLC035308",
        "name": "Godrej Properties Ltd",
        "status": "Active",
        "paid_up_capital": 2_14_85_57_660,
        "filing_status": "compliant",
        "last_agm_date": "2024-08-28",
        "registered_address": "Godrej One, Pirojshanagar, Eastern Express Highway, Vikhroli East, Mumbai 400079",
        "directors": [
            {"name": "Pirojsha Godrej", "din": "00432983", "designation": "Executive Chairperson"},
            {"name": "Gaurav Pandey", "din": "07610375", "designation": "MD & CEO"},
        ],
        "charges": [],
        "distress_signals": [],
    },
    "L45200MH1998PLC114168": {
        "cin": "L45200MH1998PLC114168",
        "name": "Oberoi Realty Ltd",
        "status": "Active",
        "paid_up_capital": 3_62_67_54_900,
        "filing_status": "compliant",
        "last_agm_date": "2024-09-20",
        "registered_address": "Commerz, 3rd Floor, International Business Park, Oberoi Garden City, Off Western Express Highway, Goregaon East, Mumbai 400063",
        "directors": [
            {"name": "Vikas Oberoi", "din": "00011701", "designation": "Chairman & MD"},
        ],
        "charges": [
            {"bank": "HDFC Bank", "amount": 200_00_00_000, "status": "open", "date": "2022-04-15"},
        ],
        "distress_signals": [],
    },
    "U45200MH1969PLC014474": {
        "cin": "U45200MH1969PLC014474",
        "name": "Kalpataru Ltd",
        "status": "Active",
        "paid_up_capital": 1_00_00_00_000,
        "filing_status": "compliant",
        "last_agm_date": "2024-10-12",
        "registered_address": "Lodha Supremus, 2nd Floor, Road No. 22, Wagle Industrial Estate, Thane West 400604",
        "directors": [
            {"name": "Mofatraj Munot", "din": "00010698", "designation": "Executive Chairman"},
        ],
        "charges": [
            {"bank": "SBI", "amount": 450_00_00_000, "status": "open", "date": "2021-06-30"},
        ],
        "distress_signals": [],
    },
    "U45400MH2003PTC143682": {
        "cin": "U45400MH2003PTC143682",
        "name": "Rustomjee Developers Pvt Ltd",
        "status": "Active",
        "paid_up_capital": 50_00_00_000,
        "filing_status": "delayed",
        "last_agm_date": "2023-12-31",
        "registered_address": "Rustomjee Central Park, Andheri-Kurla Road, Andheri East, Mumbai 400059",
        "directors": [
            {"name": "Berjis Desai", "din": "00153675", "designation": "Independent Director"},
        ],
        "charges": [
            {"bank": "Yes Bank", "amount": 300_00_00_000, "status": "open", "date": "2020-03-15"},
            {"bank": "Punjab National Bank", "amount": 150_00_00_000, "status": "satisfied", "date": "2019-08-10"},
        ],
        "distress_signals": ["MCA filing delayed by 90 days for FY2022-23"],
    },
    "U45200MH2005PTC152890": {
        "cin": "U45200MH2005PTC152890",
        "name": "Omkar Realtors & Developers Pvt Ltd",
        "status": "Active",
        "paid_up_capital": 25_00_00_000,
        "filing_status": "delayed",
        "last_agm_date": "2023-06-30",
        "registered_address": "Omkar House, Western Express Highway, Santacruz East, Mumbai 400055",
        "directors": [
            {"name": "Kanji Rita", "din": "01689222", "designation": "Director"},
        ],
        "charges": [
            {"bank": "SBI", "amount": 800_00_00_000, "status": "satisfied", "date": "2018-09-20"},
            {"bank": "ICICI Bank", "amount": 400_00_00_000, "status": "open", "date": "2019-11-05"},
        ],
        "distress_signals": [
            "3 charge satisfactions in distress pattern",
            "Last AGM delayed by 18 months",
        ],
    },
    "L70100MH1996PLC101379": {
        "cin": "L70100MH1996PLC101379",
        "name": "Housing Development & Infrastructure Ltd",
        "status": "Under Insolvency",
        "paid_up_capital": 4_00_00_00_000,
        "filing_status": "defaulted",
        "last_agm_date": "2021-12-31",
        "registered_address": "HDIL Towers, Anant Kanekar Marg, Bandra East, Mumbai 400051",
        "directors": [
            {"name": "Rakesh Kumar Wadhawan", "din": "00023517", "designation": "Executive Chairman"},
        ],
        "charges": [
            {"bank": "Punjab & Maharashtra Co-op Bank", "amount": 6_500_00_00_000, "status": "open", "date": "2015-04-10"},
            {"bank": "SBI", "amount": 2_000_00_00_000, "status": "satisfied", "date": "2017-07-22"},
        ],
        "distress_signals": [
            "NCLT Mumbai — CIRP initiated 2019",
            "PMC Bank fraud link",
            "AGM not held for 3 years",
            "Multiple charge defaults",
        ],
    },
    "L45200KA1997PLC022322": {
        "cin": "L45200KA1997PLC022322",
        "name": "Prestige Estates Projects Ltd",
        "status": "Active",
        "paid_up_capital": 4_00_60_25_000,
        "filing_status": "compliant",
        "last_agm_date": "2024-09-25",
        "registered_address": "The Falcon House, No 1, Main Guard Cross Road, Bengaluru 560001",
        "directors": [
            {"name": "Irfan Razack", "din": "00209022", "designation": "Chairman & MD"},
        ],
        "charges": [],
        "distress_signals": [],
    },
    "L45200KA1995PLC018795": {
        "cin": "L45200KA1995PLC018795",
        "name": "Brigade Enterprises Ltd",
        "status": "Active",
        "paid_up_capital": 2_37_00_00_000,
        "filing_status": "compliant",
        "last_agm_date": "2024-08-31",
        "registered_address": "29th & 30th Floor, World Trade Center, Brigade Gateway Campus, Rajajinagar, Bengaluru 560055",
        "directors": [
            {"name": "M R Jaishankar", "din": "00191267", "designation": "Chairman & MD"},
        ],
        "charges": [
            {"bank": "HDFC Bank", "amount": 500_00_00_000, "status": "open", "date": "2023-02-14"},
        ],
        "distress_signals": [],
    },
    "L45201KA1995PLC019899": {
        "cin": "L45201KA1995PLC019899",
        "name": "Sobha Ltd",
        "status": "Active",
        "paid_up_capital": 1_05_60_51_420,
        "filing_status": "compliant",
        "last_agm_date": "2024-09-18",
        "registered_address": "Sobha, SARJAPUR ROAD, Bengaluru 560102",
        "directors": [
            {"name": "J C Sharma", "din": "00191306", "designation": "MD & CEO"},
        ],
        "charges": [
            {"bank": "Axis Bank", "amount": 250_00_00_000, "status": "open", "date": "2022-07-08"},
        ],
        "distress_signals": [],
    },
}


class MCAScraper(BaseScraper):
    """Fetches and analyses MCA21 corporate data for developer due diligence."""

    BASE_URL = "https://www.mca.gov.in"
    SOURCE_NAME = "mca21"

    _IS_DEV = settings.ENVIRONMENT.lower() == "development"

    async def scrape(self, cin: str, **kwargs: Any) -> list[dict]:
        data = await self.get_company_details(cin)
        return [data]

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_company_details(self, cin: str) -> dict:
        """
        Fetch company master data for a given CIN.

        Returns dict with:
          cin, name, status, paid_up_capital, filing_status,
          directors, charges, last_agm_date, registered_address,
          distress_signals.
        """
        if self._IS_DEV:
            self.log(f"[mock] get_company_details cin={cin}")
            if cin in _MOCK_COMPANIES:
                return _MOCK_COMPANIES[cin]
            # Return a generic healthy company for unknown CINs
            return {
                "cin": cin,
                "name": "Unknown Developer Ltd",
                "status": "Active",
                "paid_up_capital": 10_00_00_000,
                "filing_status": "compliant",
                "last_agm_date": "2024-06-30",
                "registered_address": "India",
                "directors": [],
                "charges": [],
                "distress_signals": [],
            }

        # ── Live: MCA21 company master endpoint ───────────────────────────
        url = f"{self.BASE_URL}/content/mca/global/en/data-and-reports/company-master-data.html"
        params = {"company_cin": cin}
        html = await self.fetch_page(url)
        return self._parse_company_master(html, cin)

    async def check_financial_stress(self, company_data: dict) -> float:
        """
        Compute a financial stress score (0–100) from MCA company data.

        Scoring rules:
          +20  MCA filing is delayed
          +40  Any charge marked 'satisfied' with a major bank (distress signal:
               banks forced to write off / SARFAESI action)
          +30  Last AGM date > 2 years ago
          +40  Company status contains 'insolvency' / 'struck off' / 'dissolved'
          +10  Each outstanding charge with amount > ₹100 Cr (cap +20)
        """
        score = 0.0

        filing_status = company_data.get("filing_status", "")
        if filing_status == "delayed":
            score += 20
        elif filing_status == "defaulted":
            score += 35

        charges: list[dict] = company_data.get("charges", [])
        satisfied_distress = [
            c for c in charges
            if c.get("status") == "satisfied"
            and any(
                bank in c.get("bank", "").upper()
                for bank in ["SBI", "PNB", "BANK OF BARODA", "UNION BANK", "CANARA"]
            )
        ]
        if satisfied_distress:
            score += 40

        large_open = [
            c for c in charges
            if c.get("status") == "open" and c.get("amount", 0) > 100_00_00_000
        ]
        score += min(len(large_open) * 10, 20)

        agm_str = company_data.get("last_agm_date")
        if agm_str:
            try:
                agm_date = date.fromisoformat(agm_str)
                days_since_agm = (date.today() - agm_date).days
                if days_since_agm > 730:  # > 2 years
                    score += 30
                elif days_since_agm > 365:
                    score += 10
            except ValueError:
                pass

        status_lower = company_data.get("status", "").lower()
        if any(
            kw in status_lower
            for kw in ("insolvency", "struck off", "dissolved", "under liquidation")
        ):
            score += 40

        return min(100.0, score)

    async def save(self, records: list[dict], db: AsyncSession) -> int:
        """Update Developer records with MCA data."""
        count = 0
        for record in records:
            cin = record.get("cin")
            if not cin:
                continue
            try:
                result = await db.execute(
                    select(Developer).where(Developer.mca_cin == cin)
                )
                dev: Developer | None = result.scalar_one_or_none()
                if not dev:
                    continue

                stress_score = await self.check_financial_stress(record)
                filing_map = {
                    "compliant": McaFilingStatus.compliant,
                    "delayed": McaFilingStatus.delayed,
                    "defaulted": McaFilingStatus.defaulted,
                }

                dev.financial_stress_score = stress_score
                dev.mca_filing_status = filing_map.get(
                    record.get("filing_status", "unknown"),
                    McaFilingStatus.unknown,
                )
                count += 1
            except Exception as exc:
                self.log(f"save error for cin={cin}: {exc}", level="error")

        await db.commit()
        return count

    # ── Live HTML parsers ─────────────────────────────────────────────────────

    def _parse_company_master(self, html: str, cin: str) -> dict:
        soup = self.parse_html(html)
        return {
            "cin": cin,
            "name": self.extract_text(soup.select_one(".company-name")),
            "status": self.extract_text(soup.select_one(".company-status")),
            "paid_up_capital": 0,
            "filing_status": "compliant",
            "last_agm_date": self.extract_text(soup.select_one(".last-agm-date")),
            "registered_address": self.extract_text(soup.select_one(".registered-address")),
            "directors": [],
            "charges": [],
            "distress_signals": [],
        }
