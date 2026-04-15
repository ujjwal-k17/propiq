"""
FastAPI dependencies
====================
Import these in route handlers instead of re-implementing auth logic.

    from app.core.dependencies import (
        get_current_user,
        get_current_active_user,
        require_pro_subscription,
        get_optional_user,
        RateLimiter,
    )
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InactiveAccountError,
    InvalidCredentialsError,
    RateLimitExceededError,
    SubscriptionRequiredError,
)
from app.core.security import oauth2_optional, oauth2_scheme, verify_token
from app.database import get_db
from app.models.user import SubscriptionTier, User


# ── User resolution ───────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the Bearer JWT and return the matching active User.
    Raises ``InvalidCredentialsError`` (401) if the token is missing,
    expired, or refers to a non-existent user.
    """
    payload = verify_token(token)
    if payload is None:
        raise InvalidCredentialsError()

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise InvalidCredentialsError()

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidCredentialsError()

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError()
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Extends ``get_current_user`` by additionally checking ``is_active``.
    Raises ``InactiveAccountError`` (403) for deactivated accounts.
    """
    if not user.is_active:
        raise InactiveAccountError()
    return user


async def require_pro_subscription(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Gate an endpoint behind a Pro or Enterprise subscription.
    Raises ``SubscriptionRequiredError`` (403) for Free / Basic users.
    """
    if user.subscription_tier not in (
        SubscriptionTier.pro,
        SubscriptionTier.enterprise,
    ):
        raise SubscriptionRequiredError(
            f"This feature requires a Pro subscription. "
            f"Your current plan: {user.subscription_tier.value}."
        )
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Return the authenticated User when a valid Bearer token is present,
    or ``None`` for unauthenticated requests.  Never raises.

    Use this on endpoints that are public but personalise their response
    when a logged-in user is detected.
    """
    if not token:
        return None
    payload = verify_token(token)
    if payload is None:
        return None
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    return user if (user and user.is_active) else None


# ── Rate limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Redis-backed sliding-window rate limiter.

    Usage in a route::

        limiter = RateLimiter()

        @router.post("/")
        async def endpoint(request: Request, user: User = Depends(...)):
            key = f"rl:chat:{user.id}:{date.today()}"
            await limiter.check_rate_limit(request, key, limit=20, window_seconds=86400)
            ...

    ``check_rate_limit`` increments a Redis counter and raises
    ``RateLimitExceededError`` (429) when the limit is breached.
    It is a no-op when Redis is not available on ``request.app.state``.
    """

    async def check_rate_limit(
        self,
        request: Request,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """
        Increment *key* and raise if the count exceeds *limit*.

        Returns the current counter value (useful for returning remaining
        quota in response headers).

        Parameters
        ----------
        request        : FastAPI Request (used to reach app.state.redis).
        key            : Redis key, e.g. ``"rl:chat:{user_id}:{date}"``.
        limit          : Maximum allowed calls within the window.
        window_seconds : TTL for the key (the sliding window duration).
        """
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return 0  # Redis unavailable — skip rate limiting gracefully

        count: int = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)

        if count > limit:
            raise RateLimitExceededError(
                message=(
                    f"Rate limit of {limit} requests per "
                    f"{window_seconds // 3600}h window exceeded."
                ),
                retry_after=window_seconds,
            )
        return count

    # ── Pre-built limiters for common use cases ───────────────────────────────

    async def chat_limit(self, request: Request, user: User) -> int:
        """20 messages / day for Free tier; unlimited for Pro+."""
        if user.subscription_tier in (SubscriptionTier.pro, SubscriptionTier.enterprise):
            return 0
        key = f"rl:chat:{user.id}:{date.today().isoformat()}"
        return await self.check_rate_limit(request, key, limit=20, window_seconds=86400)

    async def report_limit(self, request: Request, user: User) -> int:
        """5 report generations / day for Free tier."""
        if user.subscription_tier in (SubscriptionTier.pro, SubscriptionTier.enterprise):
            return 0
        key = f"rl:report:{user.id}:{date.today().isoformat()}"
        return await self.check_rate_limit(request, key, limit=5, window_seconds=86400)

    async def refresh_limit(self, request: Request, project_id: str) -> int:
        """1 refresh per project per 6 hours (applies to all users)."""
        key = f"rl:refresh:project:{project_id}"
        return await self.check_rate_limit(
            request, key, limit=1, window_seconds=6 * 3600
        )


# Singleton — import and reuse rather than constructing per-request
rate_limiter = RateLimiter()
