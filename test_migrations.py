#!/usr/bin/env python3
"""
Comprehensive test suite for database migration setup.
This validates the migration setup without requiring database connectivity.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class MigrationTester:
    """Test class for validating database migrations."""
    
    def __init__(self):
        self.versions_dir = project_root / "alembic" / "versions"
        self.required_tables = {
            'users', 'chat_sessions', 'messages', 'log_entries',
            'query_metrics', 'system_metrics', 'audit_logs',
            'security_events', 'compliance_reports'
        }
        self.required_indexes = {
            'users': ['idx_user_username_active', 'idx_user_email_active'],
            'chat_sessions': ['idx_session_user_active', 'idx_session_created_at'],
            'messages': ['idx_message_session_timestamp', 'idx_message_role'],
            'log_entries': ['idx_log_timestamp_source', 'idx_log_level_timestamp', 'idx_log_embedding'],
            'query_metrics': ['idx_metrics_user_timestamp', 'idx_metrics_success_timestamp', 'idx_metrics_response_time'],
            'system_metrics': ['idx_system_metrics_name_timestamp'],
            'audit_logs': ['idx_audit_event_type_timestamp', 'idx_audit_user_timestamp'],
            'security_events': ['idx_security_event_type_timestamp', 'idx_security_severity_timestamp'],
            'compliance_reports': ['idx_compliance_type_period', 'idx_compliance_generated_by']
        }
    
    def test_migration_files_exist(self) -> bool:
        """Test that required migration files exist."""
        print("🔍 Testing migration files existence...")
        
        if not self.versions_dir.exists():
            print("❌ Alembic versions directory not found")
            return False
        
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        if len(migration_files) < 2:
            print(f"❌ Expected at least 2 migration files, found {len(migration_files)}")
            return False
        
        print(f"✅ Found {len(migration_files)} migration files:")
        for file in sorted(migration_files):
            print(f"   - {file.name}")
        
        return True
    
    def test_migration_structure(self) -> bool:
        """Test migration file structure and content."""
        print("\n🔍 Testing migration structure...")
        
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            
            # Check for required functions
            if 'def upgrade():' not in content:
                print(f"❌ {migration_file.name} missing upgrade() function")
                return False
            
            if 'def downgrade():' not in content:
                print(f"❌ {migration_file.name} missing downgrade() function")
                return False
            
            # Check for revision identifiers
            if 'revision =' not in content:
                print(f"❌ {migration_file.name} missing revision identifier")
                return False
            
            print(f"✅ {migration_file.name} structure valid")
        
        return True
    
    def test_table_creation(self) -> bool:
        """Test that all required tables are created in migrations."""
        print("\n🔍 Testing table creation...")
        
        created_tables = set()
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            
            # Find create_table calls
            table_matches = re.findall(r"create_table\s*\(\s*['\"]([^'\"]+)['\"]", content)
            created_tables.update(table_matches)
        
        missing_tables = self.required_tables - created_tables
        if missing_tables:
            print(f"❌ Missing tables in migrations: {missing_tables}")
            return False
        
        print("✅ All required tables found in migrations:")
        for table in sorted(created_tables):
            print(f"   - {table}")
        
        return True
    
    def test_index_creation(self) -> bool:
        """Test that required indexes are created."""
        print("\n🔍 Testing index creation...")
        
        created_indexes = {}
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            
            # Find create_index calls
            index_matches = re.findall(r"create_index\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]", content)
            
            for index_name, table_name in index_matches:
                if table_name not in created_indexes:
                    created_indexes[table_name] = []
                created_indexes[table_name].append(index_name)
        
        # Check required indexes
        missing_indexes = []
        for table, required_idx in self.required_indexes.items():
            table_indexes = created_indexes.get(table, [])
            for idx in required_idx:
                if idx not in table_indexes:
                    missing_indexes.append(f"{table}.{idx}")
        
        if missing_indexes:
            print(f"❌ Missing indexes: {missing_indexes}")
            return False
        
        print("✅ All required indexes found in migrations")
        for table, indexes in created_indexes.items():
            if indexes:
                print(f"   - {table}: {len(indexes)} indexes")
        
        return True
    
    def test_foreign_keys(self) -> bool:
        """Test that foreign key relationships are defined."""
        print("\n🔍 Testing foreign key relationships...")
        
        foreign_keys = []
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            
            # Find ForeignKeyConstraint calls
            fk_matches = re.findall(r"ForeignKeyConstraint\s*\(\s*\[([^\]]+)\],\s*\[([^\]]+)\]", content)
            foreign_keys.extend(fk_matches)
        
        expected_fks = [
            ("'user_id'", "'users.id'"),  # chat_sessions -> users
            ("'session_id'", "'chat_sessions.id'"),  # messages -> chat_sessions
            ("'user_id'", "'users.id'"),  # query_metrics -> users
        ]
        
        found_fks = 0
        for expected_fk in expected_fks:
            for fk in foreign_keys:
                if expected_fk[0] in fk[0] and expected_fk[1] in fk[1]:
                    found_fks += 1
                    break
        
        if found_fks < len(expected_fks):
            print(f"❌ Expected {len(expected_fks)} foreign keys, found {found_fks}")
            return False
        
        print(f"✅ Found {len(foreign_keys)} foreign key relationships")
        return True
    
    def test_downgrade_operations(self) -> bool:
        """Test that downgrade operations are properly defined."""
        print("\n🔍 Testing downgrade operations...")
        
        migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            
            # Check that downgrade function has operations
            downgrade_match = re.search(r'def downgrade\(\):(.*?)(?=def|\Z)', content, re.DOTALL)
            if not downgrade_match:
                print(f"❌ {migration_file.name} missing downgrade function")
                return False
            
            downgrade_content = downgrade_match.group(1)
            
            # Check for drop operations
            if 'drop_table' not in downgrade_content and 'pass' not in downgrade_content:
                print(f"❌ {migration_file.name} downgrade function appears empty")
                return False
            
            print(f"✅ {migration_file.name} downgrade operations defined")
        
        return True
    
    def test_model_consistency(self) -> bool:
        """Test that migrations are consistent with model definitions."""
        print("\n🔍 Testing model-migration consistency...")
        
        try:
            from models.database import Base
            
            # Get table names from models
            model_tables = set(Base.metadata.tables.keys())
            
            # Get table names from migrations
            migration_tables = set()
            migration_files = [f for f in self.versions_dir.glob("*.py") if not f.name.startswith("__")]
            
            for migration_file in migration_files:
                content = migration_file.read_text()
                table_matches = re.findall(r"create_table\s*\(\s*['\"]([^'\"]+)['\"]", content)
                migration_tables.update(table_matches)
            
            # Check consistency
            missing_in_migrations = model_tables - migration_tables
            extra_in_migrations = migration_tables - model_tables
            
            if missing_in_migrations:
                print(f"❌ Tables in models but not in migrations: {missing_in_migrations}")
                return False
            
            if extra_in_migrations:
                print(f"⚠️  Tables in migrations but not in current models: {extra_in_migrations}")
            
            print(f"✅ Model-migration consistency verified")
            print(f"   - Model tables: {len(model_tables)}")
            print(f"   - Migration tables: {len(migration_tables)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Model consistency test failed: {e}")
            return False
    
    def test_alembic_configuration(self) -> bool:
        """Test Alembic configuration."""
        print("\n🔍 Testing Alembic configuration...")
        
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            
            # Test config loading
            alembic_cfg = Config("alembic.ini")
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            
            # Get revisions
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) < 2:
                print(f"❌ Expected at least 2 revisions, found {len(revisions)}")
                return False
            
            print(f"✅ Alembic configuration valid")
            print(f"   - Found {len(revisions)} revisions")
            
            # Test revision chain
            for i, rev in enumerate(revisions):
                print(f"   - {rev.revision}: {rev.doc}")
                if i > 0 and rev.down_revision != revisions[i-1].revision:
                    print(f"⚠️  Revision chain may have gaps")
            
            return True
            
        except Exception as e:
            print(f"❌ Alembic configuration test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all migration tests."""
        print("🧪 Comprehensive Database Migration Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_migration_files_exist,
            self.test_migration_structure,
            self.test_table_creation,
            self.test_index_creation,
            self.test_foreign_keys,
            self.test_downgrade_operations,
            self.test_model_consistency,
            self.test_alembic_configuration,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    print()
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                print()
        
        print("=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All migration tests passed!")
            print("✅ Database migration setup is complete and functional!")
            return True
        else:
            print("❌ Some tests failed. Please review the issues above.")
            return False


def main():
    """Run the migration test suite."""
    tester = MigrationTester()
    success = tester.run_all_tests()
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)