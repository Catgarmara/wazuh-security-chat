#!/usr/bin/env python3
"""
Simple test to verify the project structure is correctly set up.
"""
import os
import sys
from pathlib import Path

def test_directory_structure():
    """Test that all required directories exist."""
    required_dirs = [
        "app",
        "core", 
        "models",
        "services",
        "api",
        "utils"
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print("✅ All required directories exist")
    return True

def test_core_files():
    """Test that core configuration files exist."""
    required_files = [
        "core/__init__.py",
        "core/config.py",
        "core/container.py", 
        "core/exceptions.py",
        "app/main.py",
        "main.py",
        "requirements.txt",
        ".env.example"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required core files exist")
    return True

def test_file_contents():
    """Test that key files have expected content."""
    tests = [
        ("core/config.py", "class AppSettings"),
        ("core/container.py", "class ServiceContainer"),
        ("core/exceptions.py", "class WazuhChatException"),
        ("app/main.py", "def create_app"),
        ("main.py", "def main")
    ]
    
    for file_path, expected_content in tests:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if expected_content not in content:
                    print(f"❌ {file_path} missing expected content: {expected_content}")
                    return False
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
    
    print("✅ All files contain expected content")
    return True

def main():
    """Run all tests."""
    print("🧪 Testing project structure...")
    
    tests = [
        test_directory_structure,
        test_core_files,
        test_file_contents
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        print("\n🎉 All structure tests passed!")
        print("✅ Project structure and core configuration setup complete")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())