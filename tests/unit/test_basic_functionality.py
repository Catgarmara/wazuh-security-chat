#!/usr/bin/env python3
"""
Basic functionality test for authentication system.
"""

from services.auth_service import AuthService
from services.rbac_service import RBACService, Permission
from models.database import User, UserRole
from uuid import uuid4
from datetime import datetime


def test_auth_service():
    """Test basic AuthService functionality."""
    print("Testing AuthService...")
    
    auth = AuthService()
    
    # Test password hashing
    password = "testpassword123"
    hashed = auth.hash_password(password)
    assert hashed.startswith("$2b$"), "Hash should start with bcrypt identifier"
    assert auth.verify_password(password, hashed), "Password verification should work"
    assert not auth.verify_password("wrong", hashed), "Wrong password should fail"
    print("✓ Password hashing and verification works")
    
    # Test token creation
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    token_data = auth.create_access_token(user)
    assert "access_token" in token_data, "Should have access_token"
    assert "token_type" in token_data, "Should have token_type"
    assert token_data["token_type"] == "bearer", "Token type should be bearer"
    print("✓ Access token creation works")
    
    # Test token verification
    token = token_data["access_token"]
    payload = auth.verify_token(token, "access")
    assert payload["username"] == user.username, "Username should match"
    assert payload["role"] == user.role, "Role should match"
    assert payload["type"] == "access", "Token type should match"
    print("✓ Token verification works")


def test_rbac_service():
    """Test basic RBACService functionality."""
    print("\nTesting RBACService...")
    
    rbac = RBACService()
    
    # Test role permissions
    admin_perms = rbac.get_role_permissions(UserRole.ADMIN)
    analyst_perms = rbac.get_role_permissions(UserRole.ANALYST)
    viewer_perms = rbac.get_role_permissions(UserRole.VIEWER)
    
    assert Permission.USER_CREATE in admin_perms, "Admin should have USER_CREATE"
    assert Permission.USER_CREATE not in analyst_perms, "Analyst should not have USER_CREATE"
    assert Permission.USER_CREATE not in viewer_perms, "Viewer should not have USER_CREATE"
    
    assert Permission.AI_QUERY in admin_perms, "Admin should have AI_QUERY"
    assert Permission.AI_QUERY in analyst_perms, "Analyst should have AI_QUERY"
    assert Permission.AI_QUERY in viewer_perms, "Viewer should have AI_QUERY"
    
    print(f"✓ Admin has {len(admin_perms)} permissions")
    print(f"✓ Analyst has {len(analyst_perms)} permissions")
    print(f"✓ Viewer has {len(viewer_perms)} permissions")
    
    # Test permission checking
    admin_user = User(id=uuid4(), role=UserRole.ADMIN, is_active=True)
    analyst_user = User(id=uuid4(), role=UserRole.ANALYST, is_active=True)
    viewer_user = User(id=uuid4(), role=UserRole.VIEWER, is_active=True)
    
    assert rbac.has_permission(admin_user, Permission.USER_CREATE), "Admin should have USER_CREATE"
    assert not rbac.has_permission(analyst_user, Permission.USER_CREATE), "Analyst should not have USER_CREATE"
    assert not rbac.has_permission(viewer_user, Permission.USER_CREATE), "Viewer should not have USER_CREATE"
    
    print("✓ Permission checking works")


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting imports...")
    
    try:
        import services.auth_service
        print("✓ auth_service imports successfully")
    except Exception as e:
        print(f"✗ auth_service import failed: {e}")
        return False
    
    try:
        import services.rbac_service
        print("✓ rbac_service imports successfully")
    except Exception as e:
        print(f"✗ rbac_service import failed: {e}")
        return False
    
    try:
        import core.permissions
        print("✓ permissions imports successfully")
    except Exception as e:
        print(f"✗ permissions import failed: {e}")
        return False
    
    try:
        import core.middleware
        print("✓ middleware imports successfully")
    except Exception as e:
        print(f"✗ middleware import failed: {e}")
        return False
    
    try:
        import api.auth
        print("✓ auth API imports successfully")
    except Exception as e:
        print(f"✗ auth API import failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("Running basic functionality tests for authentication system...\n")
    
    try:
        if not test_imports():
            print("\n✗ Import tests failed")
            exit(1)
        
        test_auth_service()
        test_rbac_service()
        
        print("\n🎉 All basic functionality tests passed!")
        print("\nAuthentication system is working correctly:")
        print("- JWT token generation and validation ✓")
        print("- Password hashing with bcrypt ✓")
        print("- Role-based access control ✓")
        print("- Permission checking ✓")
        print("- All modules import successfully ✓")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)