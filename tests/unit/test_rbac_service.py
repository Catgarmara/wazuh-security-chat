"""
Test suite for Role-Based Access Control (RBAC) service.

This module tests user roles, permission mappings, permission checking,
and user management functions with proper authorization.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.rbac_service import RBACService, Permission, get_rbac_service
from models.database import User, UserRole
from models.schemas import UserCreate, UserUpdate


class TestRBACService:
    """Test cases for RBACService role-based access control."""
    
    @pytest.fixture
    def rbac_service(self):
        """Create RBACService instance for testing."""
        return RBACService()
    
    @pytest.fixture
    def admin_user(self):
        """Create a mock admin user."""
        return User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            role=UserRole.ADMIN,
            is_active=True
        )
    
    @pytest.fixture
    def analyst_user(self):
        """Create a mock analyst user."""
        return User(
            id=uuid4(),
            username="analyst",
            email="analyst@example.com",
            password_hash="hashed",
            role=UserRole.ANALYST,
            is_active=True
        )
    
    @pytest.fixture
    def viewer_user(self):
        """Create a mock viewer user."""
        return User(
            id=uuid4(),
            username="viewer",
            email="viewer@example.com",
            password_hash="hashed",
            role=UserRole.VIEWER,
            is_active=True
        )
    
    @pytest.fixture
    def inactive_user(self):
        """Create a mock inactive user."""
        return User(
            id=uuid4(),
            username="inactive",
            email="inactive@example.com",
            password_hash="hashed",
            role=UserRole.ANALYST,
            is_active=False
        )
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    def test_get_role_permissions_admin(self, rbac_service):
        """Test getting permissions for admin role."""
        permissions = rbac_service.get_role_permissions(UserRole.ADMIN)
        
        # Admin should have all permissions
        assert Permission.USER_CREATE in permissions
        assert Permission.USER_DELETE in permissions
        assert Permission.SYSTEM_CONFIG in permissions
        assert Permission.AI_VECTORSTORE in permissions
        assert len(permissions) > 10  # Admin has many permissions
    
    def test_get_role_permissions_analyst(self, rbac_service):
        """Test getting permissions for analyst role."""
        permissions = rbac_service.get_role_permissions(UserRole.ANALYST)
        
        # Analyst should have analysis permissions but not admin permissions
        assert Permission.AI_QUERY in permissions
        assert Permission.LOG_READ in permissions
        assert Permission.CHAT_CREATE in permissions
        assert Permission.ANALYTICS_READ in permissions
        
        # Analyst should not have admin permissions
        assert Permission.USER_CREATE not in permissions
        assert Permission.USER_DELETE not in permissions
        assert Permission.SYSTEM_CONFIG not in permissions
    
    def test_get_role_permissions_viewer(self, rbac_service):
        """Test getting permissions for viewer role."""
        permissions = rbac_service.get_role_permissions(UserRole.VIEWER)
        
        # Viewer should have read-only permissions
        assert Permission.AI_QUERY in permissions
        assert Permission.LOG_READ in permissions
        assert Permission.CHAT_READ in permissions
        assert Permission.ANALYTICS_READ in permissions
        
        # Viewer should not have write permissions
        assert Permission.CHAT_CREATE not in permissions
        assert Permission.LOG_RELOAD not in permissions
        assert Permission.USER_UPDATE not in permissions
    
    def test_has_permission_admin(self, rbac_service, admin_user):
        """Test permission checking for admin user."""
        # Admin should have all permissions
        assert rbac_service.has_permission(admin_user, Permission.USER_CREATE)
        assert rbac_service.has_permission(admin_user, Permission.SYSTEM_CONFIG)
        assert rbac_service.has_permission(admin_user, Permission.AI_VECTORSTORE)
    
    def test_has_permission_analyst(self, rbac_service, analyst_user):
        """Test permission checking for analyst user."""
        # Analyst should have analysis permissions
        assert rbac_service.has_permission(analyst_user, Permission.AI_QUERY)
        assert rbac_service.has_permission(analyst_user, Permission.LOG_READ)
        assert rbac_service.has_permission(analyst_user, Permission.CHAT_CREATE)
        
        # Analyst should not have admin permissions
        assert not rbac_service.has_permission(analyst_user, Permission.USER_CREATE)
        assert not rbac_service.has_permission(analyst_user, Permission.SYSTEM_CONFIG)
    
    def test_has_permission_viewer(self, rbac_service, viewer_user):
        """Test permission checking for viewer user."""
        # Viewer should have read permissions
        assert rbac_service.has_permission(viewer_user, Permission.AI_QUERY)
        assert rbac_service.has_permission(viewer_user, Permission.LOG_READ)
        assert rbac_service.has_permission(viewer_user, Permission.CHAT_READ)
        
        # Viewer should not have write permissions
        assert not rbac_service.has_permission(viewer_user, Permission.CHAT_CREATE)
        assert not rbac_service.has_permission(viewer_user, Permission.LOG_RELOAD)
    
    def test_has_permission_inactive_user(self, rbac_service, inactive_user):
        """Test permission checking for inactive user."""
        # Inactive user should have no permissions
        assert not rbac_service.has_permission(inactive_user, Permission.AI_QUERY)
        assert not rbac_service.has_permission(inactive_user, Permission.LOG_READ)
        assert not rbac_service.has_permission(inactive_user, Permission.USER_READ)
    
    def test_has_any_permission(self, rbac_service, analyst_user):
        """Test checking for any of multiple permissions."""
        # Analyst should have at least one of these permissions
        permissions = [Permission.AI_QUERY, Permission.USER_CREATE]
        assert rbac_service.has_any_permission(analyst_user, permissions)
        
        # Analyst should not have any of these admin permissions
        admin_permissions = [Permission.USER_CREATE, Permission.SYSTEM_CONFIG]
        assert not rbac_service.has_any_permission(analyst_user, admin_permissions)
    
    def test_has_all_permissions(self, rbac_service, admin_user, analyst_user):
        """Test checking for all of multiple permissions."""
        # Admin should have all these permissions
        permissions = [Permission.USER_CREATE, Permission.AI_QUERY, Permission.LOG_READ]
        assert rbac_service.has_all_permissions(admin_user, permissions)
        
        # Analyst should not have all these permissions
        assert not rbac_service.has_all_permissions(analyst_user, permissions)
    
    def test_require_permission_success(self, rbac_service, admin_user):
        """Test successful permission requirement."""
        # Should not raise exception for admin with user creation permission
        rbac_service.require_permission(admin_user, Permission.USER_CREATE)
    
    def test_require_permission_failure(self, rbac_service, viewer_user):
        """Test failed permission requirement."""
        # Should raise exception for viewer without user creation permission
        with pytest.raises(HTTPException) as exc_info:
            rbac_service.require_permission(viewer_user, Permission.USER_CREATE)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    def test_require_any_permission_success(self, rbac_service, analyst_user):
        """Test successful any permission requirement."""
        permissions = [Permission.AI_QUERY, Permission.USER_CREATE]
        # Should not raise exception as analyst has AI_QUERY permission
        rbac_service.require_any_permission(analyst_user, permissions)
    
    def test_require_any_permission_failure(self, rbac_service, viewer_user):
        """Test failed any permission requirement."""
        permissions = [Permission.USER_CREATE, Permission.SYSTEM_CONFIG]
        # Should raise exception as viewer has none of these permissions
        with pytest.raises(HTTPException) as exc_info:
            rbac_service.require_any_permission(viewer_user, permissions)
        
        assert exc_info.value.status_code == 403
        assert "Required one of" in exc_info.value.detail
    
    def test_can_access_user_data_self(self, rbac_service, analyst_user):
        """Test user can access their own data."""
        assert rbac_service.can_access_user_data(analyst_user, analyst_user.id)
    
    def test_can_access_user_data_admin(self, rbac_service, admin_user, analyst_user):
        """Test admin can access other user's data."""
        assert rbac_service.can_access_user_data(admin_user, analyst_user.id)
    
    def test_can_access_user_data_denied(self, rbac_service, analyst_user, viewer_user):
        """Test non-admin cannot access other user's data."""
        assert not rbac_service.can_access_user_data(analyst_user, viewer_user.id)
    
    def test_can_modify_user_admin(self, rbac_service, admin_user, analyst_user):
        """Test admin can modify other users."""
        assert rbac_service.can_modify_user(admin_user, analyst_user)
    
    def test_can_modify_user_self_admin(self, rbac_service, admin_user):
        """Test admin can modify themselves."""
        assert rbac_service.can_modify_user(admin_user, admin_user)
    
    def test_can_modify_user_admin_to_admin(self, rbac_service):
        """Test admin cannot modify other admins."""
        admin1 = User(id=uuid4(), role=UserRole.ADMIN, is_active=True)
        admin2 = User(id=uuid4(), role=UserRole.ADMIN, is_active=True)
        
        assert not rbac_service.can_modify_user(admin1, admin2)
    
    def test_can_modify_user_denied(self, rbac_service, analyst_user, viewer_user):
        """Test non-admin cannot modify users."""
        assert not rbac_service.can_modify_user(analyst_user, viewer_user)
    
    def test_can_delete_user_admin(self, rbac_service, admin_user, analyst_user):
        """Test admin can delete non-admin users."""
        assert rbac_service.can_delete_user(admin_user, analyst_user)
    
    def test_can_delete_user_self_denied(self, rbac_service, admin_user):
        """Test admin cannot delete themselves."""
        assert not rbac_service.can_delete_user(admin_user, admin_user)
    
    def test_can_delete_user_admin_denied(self, rbac_service):
        """Test admin cannot delete other admins."""
        admin1 = User(id=uuid4(), role=UserRole.ADMIN, is_active=True)
        admin2 = User(id=uuid4(), role=UserRole.ADMIN, is_active=True)
        
        assert not rbac_service.can_delete_user(admin1, admin2)
    
    def test_can_delete_user_non_admin_denied(self, rbac_service, analyst_user, viewer_user):
        """Test non-admin cannot delete users."""
        assert not rbac_service.can_delete_user(analyst_user, viewer_user)
    
    def test_filter_user_list_admin(self, rbac_service, admin_user, analyst_user, viewer_user):
        """Test admin can see all users in list."""
        users = [admin_user, analyst_user, viewer_user]
        filtered = rbac_service.filter_user_list(admin_user, users)
        
        assert len(filtered) == 3
        assert admin_user in filtered
        assert analyst_user in filtered
        assert viewer_user in filtered
    
    def test_filter_user_list_non_admin(self, rbac_service, admin_user, analyst_user, viewer_user):
        """Test non-admin can only see themselves in list."""
        users = [admin_user, analyst_user, viewer_user]
        filtered = rbac_service.filter_user_list(analyst_user, users)
        
        assert len(filtered) == 1
        assert analyst_user in filtered
        assert admin_user not in filtered
        assert viewer_user not in filtered
    
    def test_get_accessible_roles_admin(self, rbac_service, admin_user):
        """Test admin can assign analyst and viewer roles."""
        roles = rbac_service.get_accessible_roles(admin_user)
        
        assert UserRole.ANALYST in roles
        assert UserRole.VIEWER in roles
        assert UserRole.ADMIN not in roles  # Prevent privilege escalation
    
    def test_get_accessible_roles_non_admin(self, rbac_service, analyst_user):
        """Test non-admin cannot assign any roles."""
        roles = rbac_service.get_accessible_roles(analyst_user)
        
        assert len(roles) == 0
    
    def test_validate_role_assignment_success(self, rbac_service, admin_user):
        """Test successful role assignment validation."""
        # Should not raise exception for admin assigning analyst role
        rbac_service.validate_role_assignment(admin_user, UserRole.ANALYST)
    
    def test_validate_role_assignment_failure(self, rbac_service, admin_user):
        """Test failed role assignment validation."""
        # Should raise exception for admin trying to assign admin role
        with pytest.raises(HTTPException) as exc_info:
            rbac_service.validate_role_assignment(admin_user, UserRole.ADMIN)
        
        assert exc_info.value.status_code == 403
        assert "Cannot assign role" in exc_info.value.detail
    
    @patch('services.rbac_service.get_auth_service')
    def test_create_user_success(self, mock_get_auth_service, rbac_service, admin_user, mock_db):
        """Test successful user creation."""
        # Setup mocks
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        created_user = User(id=uuid4(), username="newuser", role=UserRole.ANALYST)
        mock_auth_service.create_user.return_value = created_user
        
        # Create user data
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123",
            role=UserRole.ANALYST
        )
        
        # Create user
        result = rbac_service.create_user(admin_user, user_data, mock_db)
        
        # Verify auth service was called
        mock_auth_service.create_user.assert_called_once_with(user_data, mock_db)
        assert result == created_user
    
    def test_create_user_permission_denied(self, rbac_service, analyst_user, mock_db):
        """Test user creation with insufficient permissions."""
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123",
            role=UserRole.ANALYST
        )
        
        # Should raise exception for non-admin trying to create user
        with pytest.raises(HTTPException) as exc_info:
            rbac_service.create_user(analyst_user, user_data, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    def test_update_user_success(self, rbac_service, admin_user, mock_db):
        """Test successful user update."""
        target_user = User(
            id=uuid4(),
            username="target",
            email="target@example.com",
            role=UserRole.VIEWER,
            is_active=True
        )
        
        # Setup mock database
        mock_db.query.return_value.filter.return_value.first.return_value = target_user
        
        # Update data
        update_data = UserUpdate(role=UserRole.ANALYST)
        
        # Update user
        result = rbac_service.update_user(admin_user, target_user.id, update_data, mock_db)
        
        # Verify update
        assert target_user.role == UserRole.ANALYST
        assert mock_db.commit.called
        assert mock_db.refresh.called
    
    def test_update_user_not_found(self, rbac_service, admin_user, mock_db):
        """Test user update with non-existent user."""
        # Setup mock database to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        update_data = UserUpdate(role=UserRole.ANALYST)
        
        # Should raise exception for non-existent user
        with pytest.raises(HTTPException) as exc_info:
            rbac_service.update_user(admin_user, uuid4(), update_data, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
    
    def test_delete_user_success(self, rbac_service, admin_user, mock_db):
        """Test successful user deletion (soft delete)."""
        target_user = User(
            id=uuid4(),
            username="target",
            role=UserRole.ANALYST,
            is_active=True
        )
        
        # Setup mock database
        mock_db.query.return_value.filter.return_value.first.return_value = target_user
        
        # Delete user
        rbac_service.delete_user(admin_user, target_user.id, mock_db)
        
        # Verify soft delete
        assert target_user.is_active is False
        assert mock_db.commit.called
    
    def test_list_users_admin(self, rbac_service, admin_user, mock_db):
        """Test user listing for admin."""
        users = [
            User(id=uuid4(), role=UserRole.ADMIN),
            User(id=uuid4(), role=UserRole.ANALYST),
            User(id=uuid4(), role=UserRole.VIEWER)
        ]
        
        # Setup mock database
        mock_db.query.return_value.all.return_value = users
        
        # List users
        result = rbac_service.list_users(admin_user, mock_db)
        
        # Admin should see all users
        assert len(result) == 3
    
    def test_list_users_non_admin(self, rbac_service, analyst_user, mock_db):
        """Test user listing for non-admin."""
        users = [
            User(id=uuid4(), role=UserRole.ADMIN),
            analyst_user,
            User(id=uuid4(), role=UserRole.VIEWER)
        ]
        
        # Setup mock database
        mock_db.query.return_value.all.return_value = users
        
        # List users
        result = rbac_service.list_users(analyst_user, mock_db)
        
        # Non-admin should only see themselves
        assert len(result) == 1
        assert result[0] == analyst_user
    
    def test_get_rbac_service(self):
        """Test RBAC service singleton function."""
        service1 = get_rbac_service()
        service2 = get_rbac_service()
        
        # Verify same instance is returned
        assert service1 is service2
        assert isinstance(service1, RBACService)


if __name__ == "__main__":
    pytest.main([__file__])