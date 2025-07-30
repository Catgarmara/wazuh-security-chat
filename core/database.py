"""
Database connection and session management for the Wazuh AI Companion.

This module provides database connection pooling, session management,
and utilities for database operations.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .config import get_settings
from models.database import Base

logger = logging.getLogger(__name__)

# Global database engine and session factory
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


def create_database_engine() -> Engine:
    """
    Create and configure the database engine with connection pooling.
    
    Returns:
        Engine: Configured SQLAlchemy engine
    """
    settings = get_settings()
    
    # Build database URL
    database_url = (
        f"postgresql://{settings.database.user}:{settings.database.password}"
        f"@{settings.database.host}:{settings.database.port}/{settings.database.name}"
    )
    
    # Engine configuration
    engine_config = {
        "poolclass": QueuePool,
        "pool_size": settings.database.pool_size,
        "max_overflow": settings.database.max_overflow,
        "pool_pre_ping": True,  # Validate connections before use
        "pool_recycle": 3600,   # Recycle connections every hour
        "echo": settings.debug,  # Log SQL queries in debug mode
    }
    
    # Create engine
    db_engine = create_engine(database_url, **engine_config)
    
    # Add connection event listeners
    @event.listens_for(db_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set database-specific connection parameters."""
        # This is for PostgreSQL, but we can add specific settings here
        pass
    
    @event.listens_for(db_engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkout for monitoring."""
        logger.debug("Connection checked out from pool")
    
    @event.listens_for(db_engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        """Log connection checkin for monitoring."""
        logger.debug("Connection checked in to pool")
    
    return db_engine


def init_database() -> None:
    """
    Initialize the database connection and session factory.
    
    This should be called once during application startup.
    """
    global engine, SessionLocal
    
    logger.info("Initializing database connection...")
    
    # Create engine
    engine = create_database_engine()
    
    # Create session factory
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    
    logger.info("Database connection initialized successfully")


def create_tables() -> None:
    """
    Create all database tables.
    
    This should be used for initial setup or testing.
    In production, use Alembic migrations instead.
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data! Use with caution.
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Provides automatic session management with proper cleanup
    and error handling.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        with get_db_session() as session:
            user = session.query(User).first()
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.
    
    This is used as a FastAPI dependency to inject database
    sessions into route handlers.
    
    Yields:
        Session: SQLAlchemy database session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class DatabaseManager:
    """
    Database manager class for advanced database operations.
    
    Provides utilities for database health checks, connection monitoring,
    and maintenance operations.
    """
    
    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal
    
    def health_check(self) -> dict:
        """
        Perform database health check.
        
        Returns:
            dict: Health check results
        """
        if self.engine is None:
            return {"status": "error", "message": "Database not initialized"}
        
        try:
            with get_db_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")
                
                # Get connection pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid(),
                }
                
                return {
                    "status": "healthy",
                    "pool_status": pool_status,
                    "engine_info": {
                        "url": str(self.engine.url).replace(self.engine.url.password, "***"),
                        "driver": self.engine.driver,
                        "dialect": str(self.engine.dialect),
                    }
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_connection_info(self) -> dict:
        """
        Get detailed connection information.
        
        Returns:
            dict: Connection information
        """
        if self.engine is None:
            return {"error": "Database not initialized"}
        
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in_connections": pool.checkedin(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalid(),
            "total_connections": pool.size() + pool.overflow(),
        }
    
    def close_all_connections(self) -> None:
        """
        Close all database connections.
        
        This should be called during application shutdown.
        """
        if self.engine is not None:
            logger.info("Closing all database connections...")
            self.engine.dispose()
            logger.info("All database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def shutdown_database() -> None:
    """
    Shutdown database connections.
    
    This should be called during application shutdown.
    """
    global engine, SessionLocal
    
    if engine is not None:
        logger.info("Shutting down database...")
        engine.dispose()
        engine = None
        SessionLocal = None
        logger.info("Database shutdown complete")


# Database initialization functions for testing
def init_test_database() -> None:
    """
    Initialize database for testing.
    
    Uses in-memory SQLite database for fast testing.
    """
    global engine, SessionLocal
    
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        pool_pre_ping=True
    )
    
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Test database initialized")


def cleanup_test_database() -> None:
    """
    Cleanup test database.
    """
    global engine, SessionLocal
    
    if engine is not None:
        engine.dispose()
        engine = None
        SessionLocal = None
    
    logger.info("Test database cleaned up")