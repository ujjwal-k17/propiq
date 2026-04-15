"""
Alembic environment configuration for PropIQ.

Supports:
- Async engine (asyncpg driver) via run_async_migrations()
- Autogenerate from SQLAlchemy metadata
- DATABASE_URL read from .env via pydantic-settings
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Load app config and models ────────────────────────────────────────────────
# These imports must happen before we reference Base.metadata
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — registers all ORM models on Base.metadata

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Set the database URL from our settings (overrides alembic.ini sqlalchemy.url)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ── Offline migrations ────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection — emits SQL to stdout.
    Useful for generating a migration script to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render Enum CREATE TYPE statements in PostgreSQL
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) migrations ─────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare server defaults so Alembic detects server_default changes
        compare_server_defaults=True,
        # Include schemas for cross-schema objects (future-proofing)
        include_schemas=False,
        # Render as batch for SQLite compat (not needed for PG, but harmless)
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations in a sync-compatible wrapper."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
