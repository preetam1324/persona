"""Generic async database connection manager."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class Database:
    """Async database connection manager.

    Usage:
        db = Database(url="postgresql+asyncpg://...")
        await db.init()

        async with db.session() as session:
            ...

        await db.close()
    """

    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init(self, metadata: DeclarativeBase | None = None) -> None:
        """Create all tables from the given metadata (or Base)."""
        target = metadata or Base
        async with self._engine.begin() as conn:
            await conn.run_sync(target.metadata.create_all)
        logger.info("Database tables initialized")

    async def close(self) -> None:
        """Dispose of the engine connection pool."""
        await self._engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide a transactional async session scope."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
