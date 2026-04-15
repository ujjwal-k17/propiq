"""
Integration tests for the /projects/* API endpoints.
=====================================================
Uses the shared ``client`` and ``seeded_db`` fixtures from conftest.py.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestSearchProjects:
    async def test_search_projects_by_city(self, client: AsyncClient, seeded_db: dict):
        """GET /projects/?city=Mumbai should return only Mumbai projects."""
        resp = await client.get("/api/v1/projects/", params={"city": "Mumbai"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        for item in data["items"]:
            assert item["city"] == "Mumbai"

    async def test_search_projects_by_city_bengaluru(self, client: AsyncClient, seeded_db: dict):
        """Bengaluru filter should return the Bengaluru project."""
        resp = await client.get("/api/v1/projects/", params={"city": "Bengaluru"})
        assert resp.status_code == 200
        data = resp.json()
        blr_names = [i["name"] for i in data["items"]]
        # proj_blr is in Bengaluru
        assert any("Bengaluru" in n or "Tech" in n for n in blr_names)

    async def test_search_projects_no_filter_returns_all(self, client: AsyncClient, seeded_db: dict):
        """GET /projects/ without filters should return all projects."""
        resp = await client.get("/api/v1/projects/")
        assert resp.status_code == 200
        data = resp.json()
        # We seeded 5 projects
        assert data["total"] >= 5

    async def test_search_projects_with_risk_filter_low(self, client: AsyncClient, seeded_db: dict):
        """Filtering by risk_band=low should return only low-risk projects."""
        resp = await client.get("/api/v1/projects/", params={"risk_band": "low"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            rs = item.get("risk_score") or {}
            if rs.get("risk_band"):
                assert rs["risk_band"] == "low"

    async def test_search_projects_with_risk_filter_critical(self, client: AsyncClient, seeded_db: dict):
        """Filtering by risk_band=critical should return lapsed/troubled projects."""
        resp = await client.get("/api/v1/projects/", params={"risk_band": "critical"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            rs = item.get("risk_score") or {}
            if rs.get("risk_band"):
                assert rs["risk_band"] == "critical"

    async def test_search_projects_pagination(self, client: AsyncClient, seeded_db: dict):
        """Pagination params should be respected."""
        resp = await client.get("/api/v1/projects/", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2

    async def test_search_projects_sort_by_score_desc(self, client: AsyncClient, seeded_db: dict):
        """sort_by=score should return highest-score projects first."""
        resp = await client.get(
            "/api/v1/projects/",
            params={"sort_by": "score", "sort_dir": "desc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        scores = [
            (i.get("risk_score") or {}).get("composite_score") or
            (i.get("risk_score") or {}).get("overall_score") or 0
            for i in items
        ]
        for i in range(len(scores) - 1):
            if scores[i] is not None and scores[i + 1] is not None:
                assert scores[i] >= scores[i + 1]


class TestProjectDetail:
    async def test_get_project_detail_returns_all_sections(
        self, client: AsyncClient, seeded_db: dict
    ):
        """GET /projects/{id} should include developer, risk score, appreciation."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.get(f"/api/v1/projects/{proj_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Core project fields
        assert data["id"] == proj_id
        assert data["name"] == "Lodha World Towers"
        assert data["city"] == "Mumbai"
        # Related sections
        assert "developer" in data
        assert data["developer"]["name"] == "Lodha Group"
        assert "current_risk_score" in data
        assert "appreciation" in data
        assert "complaint_summary" in data

    async def test_get_project_detail_not_found(self, client: AsyncClient, seeded_db: dict):
        """Unknown UUID should return 404."""
        import uuid
        resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_project_detail_includes_risk_score(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Risk score section should contain composite_score and risk_band."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.get(f"/api/v1/projects/{proj_id}")
        assert resp.status_code == 200
        data = resp.json()
        rs = data.get("current_risk_score") or {}
        assert "composite_score" in rs or "overall_score" in rs
        assert "risk_band" in rs

    async def test_get_project_detail_critical_project_has_flags(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Critical project (lapsed RERA) should have non-empty flags."""
        proj_id = str(seeded_db["proj_lapsed_rera"].id)
        resp = await client.get(f"/api/v1/projects/{proj_id}")
        assert resp.status_code == 200
        data = resp.json()
        rs = data.get("current_risk_score") or {}
        all_flags = (
            (rs.get("legal_flags") or [])
            + (rs.get("developer_flags") or [])
            + (rs.get("project_flags") or [])
        )
        assert len(all_flags) > 0


class TestProjectRiskScore:
    async def test_get_project_risk_score(self, client: AsyncClient, seeded_db: dict):
        """GET /projects/{id}/risk-score should return a valid RiskScore object."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.get(f"/api/v1/projects/{proj_id}/risk-score")
        assert resp.status_code == 200
        data = resp.json()
        assert "composite_score" in data or "overall_score" in data
        assert "risk_band" in data
        assert "legal_score" in data
        assert "developer_score" in data
        assert "project_score" in data

    async def test_get_risk_score_for_critical_project(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Lapsed RERA project should return critical or high risk_band."""
        proj_id = str(seeded_db["proj_lapsed_rera"].id)
        resp = await client.get(f"/api/v1/projects/{proj_id}/risk-score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_band"] in ("critical", "high")


class TestProjectRefresh:
    async def test_refresh_project_unauthenticated_fails(
        self, client: AsyncClient, seeded_db: dict
    ):
        """POST /projects/{id}/refresh without auth should return 401 or 422."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.post(f"/api/v1/projects/{proj_id}/refresh")
        assert resp.status_code in (401, 422)

    async def test_refresh_project_authenticated_succeeds(
        self, client: AsyncClient, seeded_db: dict, auth_headers: dict
    ):
        """Authenticated refresh should return 200 with a status message."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.post(
            f"/api/v1/projects/{proj_id}/refresh",
            headers=auth_headers,
        )
        # May return 200 (success) or 429 (rate limit in test env)
        assert resp.status_code in (200, 429)


class TestCuratedDeals:
    async def test_curated_deals_returns_results(self, client: AsyncClient, seeded_db: dict):
        """GET /diligence/curated should return a list."""
        resp = await client.get("/api/v1/diligence/curated")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_curated_deals_returns_low_medium_only(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Curated deals should only include low and medium risk projects."""
        resp = await client.get("/api/v1/diligence/curated")
        assert resp.status_code == 200
        data = resp.json()
        for deal in data:
            rs = deal.get("risk_score") or {}
            band = rs.get("risk_band")
            if band:
                assert band in ("low", "medium"), (
                    f"Curated deal contains {band} risk project"
                )

    async def test_curated_deals_city_filter(self, client: AsyncClient, seeded_db: dict):
        """city param should filter curated deals by city."""
        resp = await client.get("/api/v1/diligence/curated", params={"city": "Mumbai"})
        assert resp.status_code == 200
        data = resp.json()
        for deal in data:
            project = deal.get("project") or deal
            assert project.get("city") == "Mumbai"
