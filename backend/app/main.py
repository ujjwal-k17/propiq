import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware
from app.database import create_all_tables
from app.api import auth, chat, developers, diligence, payments, projects, search
from app.api import ws as ws_router
from app.services.alert_manager import alert_subscriber_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Create DB tables (use Alembic migrations in production)
    await create_all_tables()

    # Verify Redis connection
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await redis.ping()
    app.state.redis = redis
    print("Redis connected.")

    # Start WebSocket alert subscriber (dedicated pub/sub connection)
    subscriber = asyncio.create_task(
        alert_subscriber_task(settings.REDIS_URL),
        name="alert_subscriber",
    )
    app.state.alert_subscriber = subscriber
    print("Alert subscriber started.")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    subscriber.cancel()
    try:
        await subscriber
    except asyncio.CancelledError:
        pass
    await app.state.redis.aclose()
    print("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered real estate due diligence for Indian property buyers and investors.",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware + exception handlers ──────────────────────────────────────────
# register_middleware adds CORS, error handling, and request logging layers.
# register_exception_handlers adds structured JSON responses for domain errors.
register_middleware(app)
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = settings.API_V1_PREFIX

app.include_router(auth.router,           prefix=PREFIX, tags=["Auth"])
app.include_router(projects.router,       prefix=PREFIX, tags=["Projects"])
app.include_router(developers.router,     prefix=PREFIX, tags=["Developers"])
app.include_router(search.router,         prefix=PREFIX, tags=["Search"])
app.include_router(diligence.router,      prefix=PREFIX, tags=["Diligence"])
app.include_router(chat.router,           prefix=PREFIX, tags=["AI Chat"])
app.include_router(payments.router,       prefix=PREFIX, tags=["Payments"])
# WebSocket router — note: no prefix wrapping needed; ws.py owns /ws/alerts
app.include_router(ws_router.router,      prefix=PREFIX, tags=["WebSocket"])


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(
        content={
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )
