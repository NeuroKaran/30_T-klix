"""
Nova - Database Connection and Session Management
Async SQLite database using SQLAlchemy.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL - defaults to SQLite in Nova/backend directory
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'nova.db'}"
)


# =============================================================================
# Base Model
# =============================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# =============================================================================
# Engine and Session
# =============================================================================

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# Session Context Manager
# =============================================================================

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    Usage:
        async with get_session() as session:
            # Use session
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_session() as session:
        yield session


# =============================================================================
# Database Initialization
# =============================================================================

async def init_db() -> None:
    """
    Initialize the database - create all tables.
    Call this on application startup.
    """
    # Import models to register them with Base
    try:
        from . import db_models  # noqa: F401
    except ImportError:
        import db_models  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
