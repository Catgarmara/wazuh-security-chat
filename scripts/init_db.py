#!/usr/bin/env python3
"""
Database initialization script for the Wazuh AI Companion.

This script initializes the database, runs migrations, and optionally
seeds initial data for development or production environments.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import init_database, create_tables, get_db_session
from core.config import get_settings
from models.database import User, UserRole
from passlib.context import CryptContext

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin_user():
    """Create default admin user if it doesn't exist."""
    settings = get_settings()
    
    with get_db_session() as session:
        # Check if admin user already exists
        admin_user = session.query(User).filter(
            User.username == "admin"
        ).first()
        
        if admin_user:
            logger.info("Admin user already exists")
            return
        
        # Create admin user
        hashed_password = pwd_context.hash("admin123")  # Change this in production!
        
        admin_user = User(
            username="admin",
            email="admin@wazuh-companion.local",
            password_hash=hashed_password,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        session.add(admin_user)
        session.commit()
        
        logger.info("Admin user created successfully")
        logger.warning("Default admin password is 'admin123' - CHANGE THIS IN PRODUCTION!")


def create_sample_users():
    """Create sample users for development."""
    settings = get_settings()
    
    if settings.environment.value != "development":
        logger.info("Skipping sample user creation (not in development mode)")
        return
    
    sample_users = [
        {
            "username": "analyst1",
            "email": "analyst1@wazuh-companion.local",
            "password": "analyst123",
            "role": UserRole.ANALYST
        },
        {
            "username": "viewer1", 
            "email": "viewer1@wazuh-companion.local",
            "password": "viewer123",
            "role": UserRole.VIEWER
        }
    ]
    
    with get_db_session() as session:
        for user_data in sample_users:
            # Check if user already exists
            existing_user = session.query(User).filter(
                User.username == user_data["username"]
            ).first()
            
            if existing_user:
                logger.info(f"User {user_data['username']} already exists")
                continue
            
            # Create user
            hashed_password = pwd_context.hash(user_data["password"])
            
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hashed_password,
                role=user_data["role"],
                is_active=True
            )
            
            session.add(user)
            logger.info(f"Created sample user: {user_data['username']}")
        
        session.commit()
        logger.info("Sample users created successfully")


def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")
    
    try:
        # Initialize database connection
        init_database()
        logger.info("Database connection initialized")
        
        # Create tables (for development - use Alembic in production)
        settings = get_settings()
        if settings.environment.value == "development":
            create_tables()
            logger.info("Database tables created")
        
        # Create admin user
        create_admin_user()
        
        # Create sample users for development
        create_sample_users()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()