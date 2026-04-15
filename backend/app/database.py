from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # Keep connections alive across idle periods (catches stale TCP connections)
    pool_pre_ping=True,
    # Tune pool to expected concurrency; override via env in production
    pool_size=10,
    max_overflow=20,
    # Wait up to 30s for a connection from the pool before raising
    pool_timeout=30,
)


# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Don't expire ORM objects after commit — avoids lazy-load errors in async
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Shared declarative base for all PropIQ ORM models.
    Import this in every model file; import all models in models/__init__.py
    so Alembic can discover them via Base.metadata.
    """


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession scoped to a single HTTP request.

    Commits on clean exit; rolls back on any exception; always closes.
    Use as a FastAPI dependency:

        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Startup helpers ───────────────────────────────────────────────────────────

async def create_all_tables() -> None:
    """
    Create every table defined in Base.metadata.

    Intended for development / CI only.
    In production, run:  alembic upgrade head
    """
    async with engine.begin() as conn:
        # Import all models so metadata is populated before we call create_all
        import app.models  # noqa: F401 — side-effect import
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables — destructive, for tests only."""
    async with engine.begin() as conn:
        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.drop_all)


async def get_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Yield a raw async connection (for bulk operations / COPY)."""
    async with engine.connect() as conn:
        yield conn
