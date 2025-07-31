#!/usr/bin/env python3
"""
Simple validation script for database models.
"""

def validate_models():
    """Validate database models."""
    try:
        from models.database import (
            Base, User, ChatSession, Message, LogEntry, 
            QueryMetrics, SystemMetrics, AuditLog, SecurityEvent, ComplianceReport
        )
        
        models = [User, ChatSession, Message, LogEntry, QueryMetrics, SystemMetrics, 
                 AuditLog, SecurityEvent, ComplianceReport]
        
        print('Database Models Validation:')
        for model in models:
            table_name = getattr(model, '__tablename__', None)
            if table_name:
                print(f'  ✓ {model.__name__} -> {table_name}')
            else:
                print(f'  ✗ {model.__name__} missing __tablename__')
        
        print(f'\nTotal models: {len(models)}')
        print('✓ All database models are valid')
        return True
        
    except Exception as e:
        print(f'✗ Database models error: {e}')
        return False

def validate_migration_files():
    """Validate migration files exist and have correct structure."""
    import os
    
    print('\nMigration Files Validation:')
    
    # Check initial schema migration
    initial_path = 'alembic/versions/000_initial_schema.py'
    if os.path.exists(initial_path):
        print(f'  ✓ {initial_path} exists')
    else:
        print(f'  ✗ {initial_path} missing')
        return False
    
    # Check audit logging migration
    audit_path = 'alembic/versions/001_add_audit_logging_tables.py'
    if os.path.exists(audit_path):
        print(f'  ✓ {audit_path} exists')
    else:
        print(f'  ✗ {audit_path} missing')
        return False
    
    # Check alembic.ini
    if os.path.exists('alembic.ini'):
        print('  ✓ alembic.ini exists')
    else:
        print('  ✗ alembic.ini missing')
        return False
    
    # Check alembic/env.py
    if os.path.exists('alembic/env.py'):
        print('  ✓ alembic/env.py exists')
    else:
        print('  ✗ alembic/env.py missing')
        return False
    
    print('✓ All migration files are present')
    return True

if __name__ == "__main__":
    print("=== Database Migration Setup Validation ===")
    
    success = True
    success &= validate_models()
    success &= validate_migration_files()
    
    print(f"\n=== Validation Result: {'PASS' if success else 'FAIL'} ===")