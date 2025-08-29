import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from .models import Base

# PUBLIC_INTERFACE
def build_postgres_dsn() -> str:
    """Build an async PostgreSQL DSN from environment variables.

    Requires:
    - DB_HOST
    - DB_PORT
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    """
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")

    missing = [k for k, v in [
        ("DB_HOST", host),
        ("DB_PORT", port),
        ("DB_NAME", name),
        ("DB_USER", user),
        ("DB_PASSWORD", pwd),
    ] if not v]
    if missing:
        raise RuntimeError(f"Missing required database env vars: {', '.join(missing)}")

    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{name}"


# Module-level engine and session factory
engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


# PUBLIC_INTERFACE
async def init_db() -> None:
    """Initialize the database connection and create tables if not present.

    This performs a minimal 'migration' by creating missing tables using SQLAlchemy's
    metadata. For production use, a proper migrations tool (e.g., Alembic) is recommended.
    """
    global engine, _session_factory
    if engine is None:
        dsn = build_postgres_dsn()
        engine = create_async_engine(dsn, echo=False, future=True)

    if _session_factory is None:
        _session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Simple initialization/migration: ensure schema is present and tables exist.
    async with engine.begin() as conn:
        # Sanity check connectivity
        await conn.execute(text("SELECT 1"))
        # Create tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)


# PUBLIC_INTERFACE
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields an AsyncSession.

    Usage:
        async with get_async_session() as session:
            ...
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() at startup.")
    session: AsyncSession = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
