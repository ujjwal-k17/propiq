"""
ASGI middleware
===============
Register via ``register_middleware(app)`` in main.py.

Middleware stack (outermost → innermost):
  1. CORSMiddleware        — allow frontend origins from env
  2. ErrorHandlingMiddleware — catch unhandled exceptions → structured JSON
  3. RequestLoggingMiddleware — log method / path / status / duration + request_id
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger("propiq.http")


# ── Request logging middleware ────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Attaches a ``request_id`` (UUID4) to every request, logs the outcome
    at INFO level, and makes the ID available as ``request.state.request_id``
    for use in error responses.

    Log format::

        [req_id] METHOD /path → STATUS in 42ms
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[%s] %s %s → %d in %.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Expose request_id in response headers for tracing
        response.headers["X-Request-ID"] = request_id
        return response


# ── Error handling middleware ─────────────────────────────────────────────────

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Catches any exception that escapes route handlers and returns a
    structured JSON error response instead of a raw 500 traceback.

    Domain exceptions (subclasses of PropIQError) are handled by FastAPI's
    exception handlers registered in exceptions.py.  This middleware is the
    *final safety net* for truly unexpected exceptions.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            logger.exception(
                "[%s] Unhandled exception on %s %s",
                request_id,
                request.method,
                request.url.path,
                exc_info=exc,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "detail": (
                        "An unexpected error occurred. Our team has been notified."
                    ),
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )


# ── Registration helper ───────────────────────────────────────────────────────

def register_middleware(app: FastAPI) -> None:
    """
    Add all middleware to *app* in the correct order.

    Call this **before** including routers so the stack is complete when
    the first request arrives.
    """
    # CORS — innermost added last in Starlette's LIFO middleware stack,
    # so declare it first here.
    origins = getattr(settings, "CORS_ORIGINS", ["http://localhost:3000"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Error handler wraps the CORS middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Logging middleware is outermost so it captures total wall time
    app.add_middleware(RequestLoggingMiddleware)
