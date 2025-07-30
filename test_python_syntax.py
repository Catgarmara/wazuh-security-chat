#!/usr/bin/env python3
"""
Python syntax validation script - checks that all Python files have valid syntax.
"""

import ast
import sys
from pathlib import Path


def validate_python_syntax(file_path):
    """Validate Python syntax for a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        return True, None
        
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def main():
    """Validate syntax for all Python files in the project."""
    print("Python Syntax Validation")
    print("=" * 40)
    
    # List of Python files to check
    python_files = [
        "core/redis_client.py",
        "core/config.py",
        "core/database.py",
        "core/exceptions.py",
        "core/container.py",
        "test_redis.py",
        "test_redis_integration.py",
        "validate_redis_implementation.py",
        "main.py",
        "app/main.py",
        "models/database.py",
        "models/schemas.py",
        "services/auth_service.py",
        "services/rbac_service.py",
        "api/auth.py",
        "core/middleware.py",
        "core/permissions.py",
        "scripts/db_manager.py",
        "scripts/init_db.py",
    ]
    
    passed = 0
    total = 0
    
    for file_path in python_files:
        path = Path(file_path)
        if path.exists():
            total += 1
            is_valid, error = validate_python_syntax(path)
            
            if is_valid:
                print(f"✓ {file_path}")
                passed += 1
            else:
                print(f"❌ {file_path}: {error}")
        else:
            print(f"⚠ {file_path}: File not found")
    
    print("\n" + "=" * 40)
    print(f"Syntax validation: {passed}/{total} files passed")
    
    if passed == total and total > 0:
        print("🎉 All Python files have valid syntax!")
        return 0
    else:
        print("❌ Some files have syntax errors!")
        return 1


if __name__ == "__main__":
    sys.exit(main())