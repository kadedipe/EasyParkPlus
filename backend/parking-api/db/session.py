"""
Database session management.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from ..core.config import settings


class DatabaseSessionManager:
    """
    Manages database sessions and engines.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
    
    def init(self, host: str, pool_enabled: bool = True):
        """
        Initialize database engine and sessionmaker.
        
        Args:
            host: Database connection string
            pool_enabled: Whether to enable connection pooling
        """
        # Engine configuration
        engine_kwargs = {
            "echo": settings.DB_ECHO,
            "future": True,
        }
        
        # Connection pooling configuration
        if pool_enabled:
            engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
            engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
            engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
            engine_kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING
            engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
        else:
            engine_kwargs["poolclass"] = NullPool
        
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    async def close(self):
        """
        Close database connection.
        """
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None
    
    @property
    def engine(self) -> AsyncEngine:
        """
        Get database engine.
        
        Returns:
            AsyncEngine: Database engine
        """
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        return self._engine
    
    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """
        Get sessionmaker.
        
        Returns:
            async_sessionmaker: Sessionmaker instance
        """
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")
        return self._sessionmaker
    
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a new database session.
        
        Yields:
            AsyncSession: Database session
        """
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as context manager.
        
        Yields:
            AsyncSession: Database session
        """
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_connection(self):
        """
        Get raw database connection.
        
        Returns:
            Connection: Raw database connection
        """
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        
        async with self._engine.connect() as conn:
            yield conn


# Create global session manager instance
sessionmanager = DatabaseSessionManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with sessionmanager.get_session() as session:
        yield session


async def initialize_database():
    """
    Initialize database connection.
    """
    from ..core.config import settings
    
    # Construct database URL
    db_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    
    # Initialize session manager
    sessionmanager.init(db_url, pool_enabled=settings.DB_POOL_ENABLED)


async def close_database_connection():
    """
    Close database connection.
    """
    await sessionmanager.close()