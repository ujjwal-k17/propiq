"""
Custom application exceptions
==============================
Each exception maps to a specific HTTP status code and carries a
machine-readable ``code`` field so frontend clients can handle them
consistently without parsing error message strings.

Register the handlers in main.py via ``register_exception_handlers(app)``.
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ── Base ──────────────────────────────────────────────────────────────────────

class PropIQError(Exception):
    """Base for all PropIQ domain exceptions."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)

    def to_dict(self, request_id: str | None = None) -> dict:
        return {
            "error": self.code,
            "detail": self.message,
            "request_id": request_id or str(uuid.uuid4()),
        }


# ── 4xx domain exceptions ─────────────────────────────────────────────────────

class ProjectNotFoundError(PropIQError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "project_not_found"
    message = "Project not found"


class DeveloperNotFoundError(PropIQError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "developer_not_found"
    message = "Developer not found"


class InvalidCredentialsError(PropIQError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_credentials"
    message = "Incorrect email or password"


class RateLimitExceededError(PropIQError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_exceeded"
    message = "Too many requests. Please try again later."

    def __init__(self, message: str | None = None, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self, request_id: str | None = None) -> dict:
        d = super().to_dict(request_id)
        if self.retry_after:
            d["retry_after_seconds"] = self.retry_after
        return d


class SubscriptionRequiredError(PropIQError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "subscription_required"
    message = "Upgrade to Pro to access this feature"


class InactiveAccountError(PropIQError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "account_inactive"
    message = "This account has been deactivated"


# ── 5xx domain exceptions ─────────────────────────────────────────────────────

class ScoreGenerationError(PropIQError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "score_generation_failed"
    message = "Failed to generate risk score for this project"


class ReportGenerationError(PropIQError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "report_generation_failed"
    message = "Failed to generate PDF report"


class ExternalServiceError(PropIQError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "external_service_error"
    message = "An upstream service returned an error"


# ── FastAPI exception handlers ────────────────────────────────────────────────

def _make_handler(exc_class: type[PropIQError]):
    async def handler(request: Request, exc: PropIQError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        headers: dict = {}
        if isinstance(exc, RateLimitExceededError) and exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers["WWW-Authenticate"] = "Bearer"
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(request_id),
            headers=headers or None,
        )
    return handler


def register_exception_handlers(app: FastAPI) -> None:
    """Register all PropIQ domain exception handlers on *app*."""
    domain_exceptions: list[type[PropIQError]] = [
        ProjectNotFoundError,
        DeveloperNotFoundError,
        InvalidCredentialsError,
        RateLimitExceededError,
        SubscriptionRequiredError,
        InactiveAccountError,
        ScoreGenerationError,
        ReportGenerationError,
        ExternalServiceError,
        PropIQError,  # catch-all for any unclassified domain error
    ]
    for exc_cls in domain_exceptions:
        app.add_exception_handler(exc_cls, _make_handler(exc_cls))

    # Generic unhandled exception → structured JSON (never expose traceback)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        import logging
        logging.getLogger("propiq").exception("Unhandled exception", exc_info=exc)
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An unexpected error occurred. Our team has been notified.",
                "request_id": request_id,
            },
        )

    app.add_exception_handler(Exception, _unhandled)
