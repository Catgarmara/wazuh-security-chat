#!/usr/bin/env python3
"""
Database management utility script.

Provides commands for database operations like migrations, seeding,
backup, and maintenance tasks.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import (
    init_database, create_tables, drop_tables, 
    get_db_session, db_manager, shutdown_database
)
from core.config import get_settings
from models.database import User, ChatSession, Message, LogEntry, QueryMetrics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def health_check():
    """Perform database health check."""
    logger.info("Performing database health check...")
    
    try:
        init_database()
        health_info = db_manager.health_check()
        
        print("\n=== Database Health Check ===")
        print(f"Status: {health_info['status']}")
        
        if health_info['status'] == 'healthy':
            print("\nConnection Pool Status:")
            pool_status = health_info['pool_status']
            for key, value in pool_status.items():
                print(f"  {key}: {value}")
            
            print("\nEngine Information:")
            engine_info = health_info['engine_info']
            for key, value in engine_info.items():
                print(f"  {key}: {value}")
        else:
            print(f"Error: {health_info.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)
    finally:
        shutdown_database()


def create_migration(message: str):
    """Create a new Alembic migration."""
    import subprocess
    
    logger.info(f"Creating migration: {message}")
    
    try:
        cmd = ["alembic", "revision", "--autogenerate", "-m", message]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Migration created successfully")
            print(result.stdout)
        else:
            logger.error("Migration creation failed")
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("Alembic not found. Make sure it's installed and in PATH")
        sys.exit(1)


def run_migrations():
    """Run pending Alembic migrations."""
    import subprocess
    
    logger.info("Running database migrations...")
    
    try:
        cmd = ["alembic", "upgrade", "head"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Migrations completed successfully")
            print(result.stdout)
        else:
            logger.error("Migration failed")
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("Alembic not found. Make sure it's installed and in PATH")
        sys.exit(1)


def rollback_migration(revision: str = "-1"):
    """Rollback to a specific migration."""
    import subprocess
    
    logger.info(f"Rolling back to revision: {revision}")
    
    try:
        cmd = ["alembic", "downgrade", revision]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Rollback completed successfully")
            print(result.stdout)
        else:
            logger.error("Rollback failed")
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("Alembic not found. Make sure it's installed and in PATH")
        sys.exit(1)


def show_migration_history():
    """Show migration history."""
    import subprocess
    
    try:
        cmd = ["alembic", "history", "--verbose"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Migration History:")
            print(result.stdout)
        else:
            logger.error("Failed to get migration history")
            print(result.stderr)
            
    except FileNotFoundError:
        logger.error("Alembic not found. Make sure it's installed and in PATH")


def reset_database():
    """Reset database (drop and recreate all tables)."""
    logger.warning("This will DELETE ALL DATA in the database!")
    
    confirm = input("Are you sure you want to continue? (yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("Database reset cancelled")
        return
    
    try:
        init_database()
        
        logger.info("Dropping all tables...")
        drop_tables()
        
        logger.info("Creating all tables...")
        create_tables()
        
        logger.info("Database reset completed successfully")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        sys.exit(1)
    finally:
        shutdown_database()


def show_stats():
    """Show database statistics."""
    logger.info("Gathering database statistics...")
    
    try:
        init_database()
        
        with get_db_session() as session:
            # Count records in each table
            user_count = session.query(User).count()
            session_count = session.query(ChatSession).count()
            message_count = session.query(Message).count()
            log_count = session.query(LogEntry).count()
            metrics_count = session.query(QueryMetrics).count()
            
            print("\n=== Database Statistics ===")
            print(f"Users: {user_count}")
            print(f"Chat Sessions: {session_count}")
            print(f"Messages: {message_count}")
            print(f"Log Entries: {log_count}")
            print(f"Query Metrics: {metrics_count}")
            
            # Connection pool info
            conn_info = db_manager.get_connection_info()
            print("\n=== Connection Pool ===")
            for key, value in conn_info.items():
                print(f"{key}: {value}")
                
    except Exception as e:
        logger.error(f"Failed to gather statistics: {e}")
        sys.exit(1)
    finally:
        shutdown_database()


def cleanup_old_data(days: int = 30):
    """Clean up old data (sessions, messages, metrics)."""
    from datetime import datetime, timedelta
    
    logger.info(f"Cleaning up data older than {days} days...")
    
    try:
        init_database()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with get_db_session() as session:
            # Clean up old inactive sessions
            old_sessions = session.query(ChatSession).filter(
                ChatSession.is_active == False,
                ChatSession.ended_at < cutoff_date
            )
            session_count = old_sessions.count()
            old_sessions.delete()
            
            # Clean up old query metrics
            old_metrics = session.query(QueryMetrics).filter(
                QueryMetrics.timestamp < cutoff_date
            )
            metrics_count = old_metrics.count()
            old_metrics.delete()
            
            session.commit()
            
            logger.info(f"Cleaned up {session_count} old sessions and {metrics_count} old metrics")
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)
    finally:
        shutdown_database()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Database management utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health check command
    subparsers.add_parser("health", help="Perform database health check")
    
    # Migration commands
    migration_parser = subparsers.add_parser("migrate", help="Run database migrations")
    
    create_migration_parser = subparsers.add_parser("create-migration", help="Create new migration")
    create_migration_parser.add_argument("message", help="Migration message")
    
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("--revision", default="-1", help="Revision to rollback to")
    
    subparsers.add_parser("history", help="Show migration history")
    
    # Database management commands
    subparsers.add_parser("reset", help="Reset database (WARNING: deletes all data)")
    subparsers.add_parser("stats", help="Show database statistics")
    
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Days to keep (default: 30)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    if args.command == "health":
        health_check()
    elif args.command == "migrate":
        run_migrations()
    elif args.command == "create-migration":
        create_migration(args.message)
    elif args.command == "rollback":
        rollback_migration(args.revision)
    elif args.command == "history":
        show_migration_history()
    elif args.command == "reset":
        reset_database()
    elif args.command == "stats":
        show_stats()
    elif args.command == "cleanup":
        cleanup_old_data(args.days)


if __name__ == "__main__":
    main()