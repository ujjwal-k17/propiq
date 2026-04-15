"""
Redis cache manager
===================
Thin async wrapper around ``redis.asyncio`` with JSON serialisation,
structured cache-key generators, and a ``get_or_fetch`` pattern.

Obtain the singleton via ``get_cache(request)`` inside a route handler,
or construct ``CacheManager(redis_client)`` directly in services.

Usage::

    from app.core.cache import CacheManager, project_detail_key

    cache = CacheManager(request.app.state.redis)
    key   = project_detail_key(project_id)
    data  = await cache.get_or_fetch(key, lambda: fetch_from_db(), ttl=300)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import redis.asyncio as aioredis


class CacheManager:
    """
    Async Redis cache with transparent JSON serialisation.

    ``None`` is returned (not raised) for all cache misses and Redis errors
    so callers never have to guard against cache failures.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    # ── Primitive operations ──────────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        """Return the deserialised value for *key*, or ``None`` on miss."""
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Serialise *value* as JSON and store with *ttl* seconds expiry.
        Silently ignores Redis errors (cache is best-effort).
        """
        try:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        """Delete *key* from the cache. No-op if absent."""
        try:
            await self._redis.delete(key)
        except Exception:
            pass

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Coroutine[Any, Any, Any]],
        ttl: int = 3600,
    ) -> Any:
        """
        Return the cached value for *key* if present; otherwise call
        ``fetch_fn()`` (an async callable with no arguments), cache the
        result, and return it.

        Example::

            data = await cache.get_or_fetch(
                key  = project_detail_key(pid),
                fetch_fn = lambda: _load_project_from_db(pid, db),
                ttl  = 300,   # 5 minutes
            )
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        fresh = await fetch_fn()
        if fresh is not None:
            await self.set(key, fresh, ttl=ttl)
        return fresh

    async def invalidate_project(self, project_id: uuid.UUID) -> None:
        """Remove all cached data related to a project."""
        pid = str(project_id)
        for key in [
            project_score_key(project_id),
            project_detail_key(project_id),
        ]:
            await self.delete(key)


# ── Cache key generators ──────────────────────────────────────────────────────
# Keep keys in one place so they never drift between writers and readers.

def project_score_key(project_id: uuid.UUID | str) -> str:
    """Current risk score for a project."""
    return f"cache:project:{project_id}:score"


def project_detail_key(project_id: uuid.UUID | str) -> str:
    """Full project detail payload (assembled by GET /projects/{id})."""
    return f"cache:project:{project_id}:detail"


def search_key(query: str, filters: dict[str, Any] | None = None) -> str:
    """
    Stable key for a search query + filter combination.
    Uses an 8-character MD5 prefix so long queries don't blow up key sizes.
    """
    canonical = json.dumps(
        {"q": query.lower().strip(), "f": filters or {}},
        sort_keys=True,
    )
    digest = hashlib.md5(canonical.encode()).hexdigest()[:8]
    return f"cache:search:{digest}"


def curated_deals_key(
    city: str | None = None,
    risk_appetite: str | None = None,
) -> str:
    """Curated deals list (generic, not user-personalised)."""
    parts = [city or "all", risk_appetite or "any"]
    return f"cache:curated:{'_'.join(parts)}"


def developer_detail_key(developer_id: uuid.UUID | str) -> str:
    return f"cache:developer:{developer_id}:detail"


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_cache_from_request(request: Any) -> CacheManager | None:
    """
    Return a ``CacheManager`` wrapping ``request.app.state.redis``, or
    ``None`` if Redis is not initialised (e.g. in tests).
    """
    redis = getattr(getattr(request, "app", None), "state", None)
    if redis is None:
        return None
    redis_client = getattr(redis, "redis", None)
    if redis_client is None:
        return None
    return CacheManager(redis_client)
