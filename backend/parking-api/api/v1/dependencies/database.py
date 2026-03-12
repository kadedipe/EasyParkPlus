"""
Database session and connection dependencies.
"""

from typing import AsyncGenerator, Callable, TypeVar, Optional
from contextlib import asynccontextmanager
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.session import AsyncSessionLocal, engine
from ....services.redis import redis_client, get_redis as get_redis_client
from ....utils.logger import logger

T = TypeVar('T')


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_session(request: Request) -> AsyncSession:
    """
    Get database session from request state.
    """
    if not hasattr(request.state, "db"):
        # Create new session if not in request state
        session = AsyncSessionLocal()
        request.state.db = session
    
    return request.state.db


async def get_redis():
    """
    Dependency for getting Redis client.
    """
    return redis_client


def transaction(func: Callable) -> Callable:
    """
    Decorator for wrapping functions in a database transaction.
    """
    async def wrapper(*args, **kwargs):
        # Extract db session from kwargs or args
        db = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                db = arg
                break
        
        if not db and 'db' in kwargs:
            db = kwargs['db']
        
        if not db:
            raise ValueError("No database session found")
        
        try:
            result = await func(*args, **kwargs)
            await db.commit()
            return result
        except Exception as e:
            await db.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise
    
    return wrapper


@asynccontextmanager
async def transaction_context(db: AsyncSession):
    """
    Context manager for database transactions.
    """
    try:
        yield
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise


async def get_read_only_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get read-only database session (for replicas).
    """
    # This could be configured to use a read replica
    async with AsyncSessionLocal() as session:
        # Set transaction to read-only
        await session.execute("SET TRANSACTION READ ONLY")
        try:
            yield session
        finally:
            await session.close()


class DatabaseHealthCheck:
    """
    Dependency for checking database health.
    """
    
    async def __call__(self, db: AsyncSession = Depends(get_db)) -> bool:
        try:
            await db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False


class RedisHealthCheck:
    """
    Dependency for checking Redis health.
    """
    
    async def __call__(self) -> bool:
        if not redis_client:
            return False
        try:
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False


async def ensure_db_connection(db: AsyncSession = Depends(get_db)):
    """
    Ensure database connection is alive.
    """
    try:
        await db.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Database connection lost: {str(e)}")
        # Try to reconnect
        await db.close()
        raise HTTPException(
            status_code=503,
            detail="Database connection lost"
        )


class ConnectionPool:
    """
    Manage database connection pool.
    """
    
    def __init__(self, min_size: int = 5, max_size: int = 20):
        self.min_size = min_size
        self.max_size = max_size
        self.current_size = 0
    
    async def acquire(self) -> AsyncSession:
        """
        Acquire a connection from pool.
        """
        if self.current_size >= self.max_size:
            # Wait for connection to be released
            await asyncio.sleep(0.1)
            return await self.acquire()
        
        self.current_size += 1
        return AsyncSessionLocal()
    
    async def release(self, session: AsyncSession):
        """
        Release connection back to pool.
        """
        await session.close()
        self.current_size -= 1


# Singleton instance
db_pool = ConnectionPool()


async def get_db_from_pool() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session from connection pool.
    """
    session = await db_pool.acquire()
    try:
        yield session
    finally:
        await db_pool.release(session)