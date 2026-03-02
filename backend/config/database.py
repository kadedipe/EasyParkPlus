"""Database configuration and connection management."""

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, NullPool
from contextlib import contextmanager
import logging

from . import config

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database connection configuration."""
    
    def __init__(self):
        self.engine = None
        self.Session = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup database engine with connection pooling."""
        pool_size = config.DB_POOL_SIZE
        max_overflow = config.DB_MAX_OVERFLOW
        
        # Use NullPool for testing
        if config.TESTING:
            poolclass = NullPool
        else:
            poolclass = QueuePool
        
        self.engine = create_engine(
            config.DATABASE_URL,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=config.DB_POOL_TIMEOUT,
            pool_recycle=config.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=poolclass,
            echo=config.DB_ECHO,
            connect_args={
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        )
        
        self.Session = scoped_session(
            sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        )
        
        logger.info(f"Database engine created with pool_size={pool_size}, max_overflow={max_overflow}")
    
    @contextmanager
    def session(self):
        """Get a database session."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def connection(self):
        """Get a raw connection."""
        conn = self.engine.raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_stats(self) -> dict:
        """Get connection pool statistics."""
        if hasattr(self.engine.pool, 'size'):
            return {
                'size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'total': self.engine.pool.total()
            }
        return {}
    
    def dispose(self):
        """Dispose of the connection pool."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("Database connection pool disposed")


# Global database instance
db = DatabaseConfig()