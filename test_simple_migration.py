#!/usr/bin/env python3
"""
Simple test to check if we can run migrations with SQLite.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_simple_migration():
    """Test basic migration functionality."""
    print("Testing simple migration with SQLite...")
    
    # Create temporary SQLite database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        from sqlalchemy import create_engine
        from alembic.config import Config
        from alembic import command
        
        # Create engine
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Create Alembic config
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f'sqlite:///{db_path}')
        
        print(f"Database: {db_path}")
        
        # Try to run migrations
        try:
            command.upgrade(alembic_cfg, "head")
            print("✅ Migrations ran successfully")
            
            # Check tables
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"✅ Created {len(tables)} tables: {tables}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

if __name__ == "__main__":
    success = test_simple_migration()
    sys.exit(0 if success else 1)