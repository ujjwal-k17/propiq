"""
Integration tests for the /auth/* API endpoints.
=================================================
Tests registration, login, profile access, and watchlist management.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_new_user(self, client: AsyncClient, seeded_db: dict):
        """POST /auth/register with valid data should create a new user."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "SecurePass1!",
                "full_name": "New User",
                "preferred_cities": ["Pune"],
                "risk_appetite": "moderate",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email_fails(self, client: AsyncClient, seeded_db: dict):
        """Registering with an existing email should return 400 or 409."""
        payload = {
            "email": "free@test.com",  # already seeded
            "password": "Password1!",
            "full_name": "Dupe User",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code in (400, 409, 422)

    async def test_register_missing_email_fails(self, client: AsyncClient, seeded_db: dict):
        """Missing required field should return 422."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"password": "Password1!"},
        )
        assert resp.status_code == 422

    async def test_register_returns_user_in_response(self, client: AsyncClient, seeded_db: dict):
        """Registration response should include user data."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "another@test.com", "password": "SecurePass1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Either inline user object or access_token
        assert "access_token" in data or "user" in data


class TestLogin:
    async def test_login_valid_credentials(self, client: AsyncClient, seeded_db: dict):
        """POST /auth/login with correct credentials should return a JWT."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "free@test.com", "password": "Password1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password(self, client: AsyncClient, seeded_db: dict):
        """Wrong password should return 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "free@test.com", "password": "WrongPassword!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient, seeded_db: dict):
        """Login with unknown email should return 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": "Password1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    async def test_login_returns_token_usable_for_auth(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Token received at login should authenticate subsequent requests."""
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "free@test.com", "password": "Password1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "free@test.com"


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, seeded_db: dict, auth_headers: dict):
        """GET /auth/me with valid token should return current user data."""
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "free@test.com"
        assert "subscription_tier" in data
        assert "watchlist_project_ids" in data

    async def test_get_me_unauthenticated_fails(self, client: AsyncClient, seeded_db: dict):
        """GET /auth/me without token should return 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token_fails(self, client: AsyncClient, seeded_db: dict):
        """GET /auth/me with a garbage token should return 401."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this_is_not_a_valid_jwt"},
        )
        assert resp.status_code == 401

    async def test_get_me_returns_correct_subscription_tier(
        self, client: AsyncClient, seeded_db: dict, pro_auth_headers: dict
    ):
        """Pro user should show pro subscription tier."""
        resp = await client.get("/api/v1/auth/me", headers=pro_auth_headers)
        assert resp.status_code == 200
        assert resp.json()["subscription_tier"] == "pro"


class TestUpdateMe:
    async def test_update_me_changes_name(
        self, client: AsyncClient, seeded_db: dict, auth_headers: dict
    ):
        """PUT /auth/me should update the user's profile."""
        resp = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated Name"

    async def test_update_me_changes_preferred_cities(
        self, client: AsyncClient, seeded_db: dict, auth_headers: dict
    ):
        """Preferred cities should be updateable."""
        resp = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"preferred_cities": ["Bengaluru", "Pune"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Bengaluru" in data.get("preferred_cities", [])

    async def test_update_me_unauthenticated_fails(self, client: AsyncClient, seeded_db: dict):
        """PUT /auth/me without auth should return 401."""
        resp = await client.put("/api/v1/auth/me", json={"full_name": "Hacker"})
        assert resp.status_code == 401


class TestWatchlist:
    async def test_watchlist_add_remove(
        self, client: AsyncClient, seeded_db: dict, auth_headers: dict
    ):
        """Add then remove a project from the watchlist; verify both operations."""
        proj_id = str(seeded_db["proj_low_risk"].id)

        # Add
        add_resp = await client.post(
            f"/api/v1/auth/watchlist/{proj_id}",
            headers=auth_headers,
        )
        assert add_resp.status_code in (200, 204)

        # Verify in /auth/me
        me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        me_data = me_resp.json()
        assert proj_id in me_data.get("watchlist_project_ids", [])

        # Remove
        del_resp = await client.delete(
            f"/api/v1/auth/watchlist/{proj_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code in (200, 204)

        # Verify removed
        me_resp2 = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert proj_id not in me_resp2.json().get("watchlist_project_ids", [])

    async def test_watchlist_add_unauthenticated_fails(
        self, client: AsyncClient, seeded_db: dict
    ):
        """Adding to watchlist without auth should return 401."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        resp = await client.post(f"/api/v1/auth/watchlist/{proj_id}")
        assert resp.status_code == 401

    async def test_watchlist_add_same_project_twice_is_idempotent(
        self, client: AsyncClient, seeded_db: dict, auth_headers: dict
    ):
        """Adding the same project twice should not duplicate it in the watchlist."""
        proj_id = str(seeded_db["proj_low_risk"].id)
        await client.post(f"/api/v1/auth/watchlist/{proj_id}", headers=auth_headers)
        await client.post(f"/api/v1/auth/watchlist/{proj_id}", headers=auth_headers)

        me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        watchlist = me_resp.json().get("watchlist_project_ids", [])
        assert watchlist.count(proj_id) == 1
