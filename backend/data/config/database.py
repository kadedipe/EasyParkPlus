"""
Database connection and session management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, AsyncIterator, Dict, Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.async_engine: Optional[AsyncEngine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.AsyncSessionLocal: Optional[async_sessionmaker] = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return
        
        # Create sync engine
        self.engine = create_engine(
            settings.database.url,
            poolclass=QueuePool,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
            echo=settings.database.echo,
            echo_pool=settings.debug,
            connect_args={
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        )
        
        # Create async engine
        self.async_engine = create_async_engine(
            settings.database.async_url,
            poolclass=QueuePool if not settings.is_test() else NullPool,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
            echo=settings.database.echo,
            echo_pool=settings.debug,
            connect_args={
                "timeout": 10,
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "parking-management",
                    "timezone": "UTC",
                },
            },
        )
        
        # Create session factories
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        
        self._setup_engine_events()
        self._initialized = True
        logger.info("Database manager initialized")
    
    def _setup_engine_events(self):
        """Set up SQLAlchemy engine events."""
        
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def checkin(dbapi_connection, connection_record):
            logger.debug("Database connection returned to pool")
        
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            conn.info.setdefault("query_start_time", []).append(asyncio.get_event_loop().time())
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            total = asyncio.get_event_loop().time() - conn.info["query_start_time"].pop()
            logger.debug("Query executed", extra={
                "query": statement[:100],
                "duration": total,
                "parameters": parameters,
            })
            
            # Log slow queries
            if total > 1.0:
                logger.warning(f"Slow query detected ({total:.2f}s): {statement[:200]}")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        if not self._initialized:
            self.initialize()
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        """Get an async database session."""
        if not self._initialized:
            self.initialize()
        
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Async database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def check_health(self) -> Dict[str, any]:
        """Check database health."""
        health_status = {"status": "healthy", "checks": {}}
        
        try:
            # Check sync connection
            with self.session() as session:
                result = session.execute(text("SELECT 1"))
                health_status["checks"]["sync"] = {
                    "status": "healthy",
                    "result": result.scalar() == 1,
                }
        except Exception as e:
            health_status["checks"]["sync"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        try:
            # Check async connection
            async with self.async_session() as session:
                result = await session.execute(text("SELECT 1"))
                health_status["checks"]["async"] = {
                    "status": "healthy",
                    "result": result.scalar() == 1,
                }
        except Exception as e:
            health_status["checks"]["async"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        # Get pool status
        if self.engine:
            pool = self.engine.pool
            health_status["pool"] = {
                "size": pool.size(),
                "checked_in_connections": pool.checkedin(),
                "overflow": pool.overflow(),
                "timeout": pool.timeout(),
            }
        
        return health_status
    
    async def close(self):
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            await self.async_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()