#!/usr/bin/env python3
"""
Test script to validate migration up and down operations using SQLite for testing.
"""

import os
import sys
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, MetaData, inspect
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_migration_operations():
    """Test migration up and down operations using SQLite."""
    print("🔍 Testing Migration Operations (Up/Down)")
    print("=" * 50)
    
    # Create temporary SQLite database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Create SQLite engine
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Create Alembic config with SQLite URL
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f'sqlite:///{db_path}')
        
        print(f"📁 Using temporary database: {db_path}")
        
        # Test migration up
        print("\n🔼 Testing migration UP operations...")
        
        try:
            # Run all migrations up
            command.upgrade(alembic_cfg, "head")
            print("✅ All migrations applied successfully")
            
            # Check that all tables were created
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            expected_tables = {
                'users', 'chat_sessions', 'messages', 'log_entries',
                'query_metrics', 'system_metrics', 'audit_logs',
                'security_events', 'compliance_reports', 'alembic_version'
            }
            
            found_tables = set(tables)
            missing_tables = expected_tables - found_tables
            
            if missing_tables:
                print(f"❌ Missing tables after migration: {missing_tables}")
                return False
            
            print("✅ All expected tables created:")
            for table in sorted(found_tables):
                if table != 'alembic_version':
                    print(f"   - {table}")
            
            # Test table structure for key tables
            print("\n🔍 Validating table structures...")
            
            # Test users table
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            expected_user_columns = {'id', 'username', 'email', 'password_hash', 'role', 'is_active', 'created_at', 'updated_at', 'last_login'}
            if not expected_user_columns.issubset(set(user_columns)):
                print(f"❌ Users table missing columns: {expected_user_columns - set(user_columns)}")
                return False
            print("✅ Users table structure correct")
            
            # Test indexes
            user_indexes = inspector.get_indexes('users')
            print(f"✅ Users table has {len(user_indexes)} indexes")
            
            # Test foreign keys
            session_fks = inspector.get_foreign_keys('chat_sessions')
            if not any(fk['referred_table'] == 'users' for fk in session_fks):
                print("❌ Chat sessions missing foreign key to users")
                return False
            print("✅ Foreign key relationships correct")
            
        except Exception as e:
            print(f"❌ Migration UP failed: {e}")
            return False
        
        # Test migration down
        print("\n🔽 Testing migration DOWN operations...")
        
        try:
            # Get current revision
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) < 2:
                print("⚠️  Not enough revisions to test downgrade")
                return True
            
            # Downgrade to previous revision
            prev_revision = revisions[1].revision
            command.downgrade(alembic_cfg, prev_revision)
            print(f"✅ Downgraded to revision {prev_revision}")
            
            # Check that some tables were removed
            inspector = inspect(engine)
            tables_after_downgrade = set(inspector.get_table_names())
            
            # Should have fewer tables after downgrade
            if len(tables_after_downgrade) >= len(found_tables):
                print("⚠️  Expected fewer tables after downgrade")
            else:
                print("✅ Tables removed during downgrade")
            
            # Upgrade back to head
            command.upgrade(alembic_cfg, "head")
            print("✅ Upgraded back to head")
            
            # Verify all tables are back
            inspector = inspect(engine)
            final_tables = set(inspector.get_table_names())
            
            if final_tables != found_tables:
                print("❌ Tables not restored correctly after re-upgrade")
                return False
            
            print("✅ All tables restored after re-upgrade")
            
        except Exception as e:
            print(f"❌ Migration DOWN/UP cycle failed: {e}")
            return False
        
        print("\n🎉 All migration operations completed successfully!")
        return True
        
    finally:
        # Clean up temporary database
        try:
            os.unlink(db_path)
        except:
            pass

def test_migration_consistency():
    """Test that migrations are consistent with model definitions."""
    print("\n🔍 Testing Migration-Model Consistency")
    print("=" * 40)
    
    try:
        # Import models to get metadata
        from models.database import Base
        
        # Get all table names from models
        model_tables = set(Base.metadata.tables.keys())
        
        # Get table names from migrations
        migration_tables = set()
        versions_dir = project_root / "alembic" / "versions"
        
        for migration_file in versions_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue
                
            content = migration_file.read_text()
            
            # Look for create_table calls
            import re
            table_matches = re.findall(r"create_table\s*\(\s*['\"]([^'\"]+)['\"]", content)
            migration_tables.update(table_matches)
        
        # Compare
        missing_in_migrations = model_tables - migration_tables
        extra_in_migrations = migration_tables - model_tables
        
        if missing_in_migrations:
            print(f"❌ Tables in models but not in migrations: {missing_in_migrations}")
            return False
        
        if extra_in_migrations:
            print(f"⚠️  Tables in migrations but not in models: {extra_in_migrations}")
        
        print("✅ Migration-model consistency check passed")
        print(f"   - Model tables: {len(model_tables)}")
        print(f"   - Migration tables: {len(migration_tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Consistency check failed: {e}")
        return False

def main():
    """Run all migration operation tests."""
    print("🧪 Testing Database Migration Operations")
    print("=" * 60)
    
    tests = [
        test_migration_operations,
        test_migration_consistency,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All migration operation tests passed!")
        print("✅ Database migration setup is fully functional!")
        return True
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)