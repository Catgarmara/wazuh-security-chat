#!/usr/bin/env python3
"""
Test script to validate the migration setup without requiring database connection.
"""

import os
import sys
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
from sqlalchemy import MetaData, create_engine
from sqlalchemy.pool import StaticPool

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_migration_files():
    """Test that migration files exist and are valid."""
    print("Testing migration files...")
    
    # Check if alembic.ini exists
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.exists():
        print("❌ alembic.ini not found")
        return False
    print("✅ alembic.ini found")
    
    # Check if versions directory exists
    versions_dir = project_root / "alembic" / "versions"
    if not versions_dir.exists():
        print("❌ alembic/versions directory not found")
        return False
    print("✅ alembic/versions directory found")
    
    # Check migration files
    migration_files = list(versions_dir.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith("__")]
    
    if not migration_files:
        print("❌ No migration files found")
        return False
    
    print(f"✅ Found {len(migration_files)} migration files:")
    for file in sorted(migration_files):
        print(f"   - {file.name}")
    
    return True

def test_alembic_config():
    """Test Alembic configuration."""
    print("\nTesting Alembic configuration...")
    
    try:
        # Create Alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Test script directory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        print("✅ Alembic script directory configured correctly")
        
        # Get revision history
        revisions = list(script_dir.walk_revisions())
        print(f"✅ Found {len(revisions)} revisions in history")
        
        for rev in revisions:
            print(f"   - {rev.revision}: {rev.doc}")
        
        return True
        
    except Exception as e:
        print(f"❌ Alembic configuration error: {e}")
        return False

def test_model_imports():
    """Test that database models can be imported."""
    print("\nTesting model imports...")
    
    try:
        from models.database import (
            Base, User, ChatSession, Message, LogEntry, 
            QueryMetrics, SystemMetrics, AuditLog, SecurityEvent, ComplianceReport
        )
        print("✅ All database models imported successfully")
        
        # Test that all models have proper table names
        models = [User, ChatSession, Message, LogEntry, QueryMetrics, SystemMetrics, 
                 AuditLog, SecurityEvent, ComplianceReport]
        
        for model in models:
            if hasattr(model, '__tablename__'):
                print(f"   - {model.__name__}: {model.__tablename__}")
            else:
                print(f"❌ {model.__name__} missing __tablename__")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Model import error: {e}")
        return False

def test_migration_content():
    """Test migration file content."""
    print("\nTesting migration content...")
    
    try:
        # Read migration files and check for required tables
        required_tables = {
            'users', 'chat_sessions', 'messages', 'log_entries', 
            'query_metrics', 'system_metrics', 'audit_logs', 
            'security_events', 'compliance_reports'
        }
        
        found_tables = set()
        
        versions_dir = project_root / "alembic" / "versions"
        for migration_file in versions_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue
                
            content = migration_file.read_text()
            
            # Check for table creation
            for table in required_tables:
                if f"'{table}'" in content or f'"{table}"' in content:
                    found_tables.add(table)
        
        missing_tables = required_tables - found_tables
        if missing_tables:
            print(f"❌ Missing tables in migrations: {missing_tables}")
            return False
        
        print("✅ All required tables found in migrations:")
        for table in sorted(found_tables):
            print(f"   - {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration content test error: {e}")
        return False

def test_migration_syntax():
    """Test migration file syntax by attempting to compile them."""
    print("\nTesting migration syntax...")
    
    try:
        versions_dir = project_root / "alembic" / "versions"
        for migration_file in versions_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue
                
            # Try to compile the migration file
            with open(migration_file, 'r') as f:
                code = f.read()
            
            try:
                compile(code, str(migration_file), 'exec')
                print(f"✅ {migration_file.name} syntax OK")
            except SyntaxError as e:
                print(f"❌ {migration_file.name} syntax error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Migration syntax test error: {e}")
        return False

def main():
    """Run all migration tests."""
    print("🔍 Testing Wazuh AI Companion Database Migration Setup")
    print("=" * 60)
    
    tests = [
        test_migration_files,
        test_alembic_config,
        test_model_imports,
        test_migration_content,
        test_migration_syntax,
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
        print("🎉 All migration tests passed! Database migration setup is complete.")
        return True
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)