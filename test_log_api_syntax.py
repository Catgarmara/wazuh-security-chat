#!/usr/bin/env python3
"""
Simple syntax check for log management API.
"""

import sys
import ast
from pathlib import Path

def check_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the AST to check syntax
        ast.parse(source)
        print(f"✅ {file_path}: Syntax is valid")
        return True
        
    except SyntaxError as e:
        print(f"❌ {file_path}: Syntax error at line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ {file_path}: Error checking syntax: {e}")
        return False

def main():
    """Check syntax of log API files."""
    files_to_check = [
        "api/logs.py",
        "app/main.py"
    ]
    
    all_valid = True
    
    for file_path in files_to_check:
        if not check_syntax(file_path):
            all_valid = False
    
    if all_valid:
        print("\n🎉 All files have valid syntax!")
        
        # Check if the log API endpoints are properly defined
        try:
            with open("api/logs.py", 'r') as f:
                content = f.read()
                
            endpoints = [
                "/health",
                "/stats", 
                "/reload",
                "/reload/date-range",
                "/search",
                "/sources",
                "/agents", 
                "/rules",
                "/config"
            ]
            
            print("\n📋 Checking endpoint definitions:")
            for endpoint in endpoints:
                if f'"{endpoint}"' in content or f"'{endpoint}'" in content:
                    print(f"✅ {endpoint} endpoint defined")
                else:
                    print(f"❌ {endpoint} endpoint missing")
                    all_valid = False
            
            # Check HTTP methods
            methods = ["@router.get", "@router.post", "@router.put"]
            print("\n🔧 Checking HTTP methods:")
            for method in methods:
                if method in content:
                    count = content.count(method)
                    print(f"✅ {method} used {count} times")
                    
        except Exception as e:
            print(f"❌ Error checking endpoints: {e}")
            all_valid = False
    
    if all_valid:
        print("\n✅ Log Management API implementation looks good!")
        return True
    else:
        print("\n❌ Issues found in Log Management API implementation!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)