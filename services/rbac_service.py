"""
Role-Based Access Control (RBAC) service for managing user permissions.

This module defines user roles (Admin, Analyst, Viewer) with permission mappings,
implements permission checking decorators and middleware, and provides user
management functions for CRUD operations.
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.database import User, UserRole
from models.schemas import UserCreate, UserUpdate, UserResponse


class Permission(str, Enum):
    """System permissions for role-based access control."""
    
    # User management permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Chat permissions
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"
    CHAT_DELETE = "chat:delete"
    CHAT_LIST = "chat:list"
    
    # Log management permissions
    LOG_READ = "log:read"
    LOG_RELOAD = "log:reload"
    LOG_STATS = "log:stats"
    LOG_SEARCH = "log:search"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_DASHBOARD = "analytics:dashboard"
    ANALYTICS_REPORTS = "analytics:reports"
    
    # System administration permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_HEALTH = "system:health"
    SYSTEM_METRICS = "system:metrics"
    
    # AI service permissions
    AI_QUERY = "ai:query"
    AI_VECTORSTORE = "ai:vectorstore"


class RBACService:
    """Role-Based Access Control service for managing permissions."""
    
    def __init__(self):
        """Initialize RBAC service with role-permission mappings."""
        self._role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, Set[Permission]]:
        """
        Initialize role-permission mappings.
        
        Returns:
            Dictionary mapping roles to their permissions
        """
        return {
            UserRole.ADMIN: {
                # Admin has all permissions
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.USER_LIST,
                Permission.CHAT_CREATE,
                Permission.CHAT_READ,
                Permission.CHAT_DELETE,
                Permission.CHAT_LIST,
                Permission.LOG_READ,
                Permission.LOG_RELOAD,
                Permission.LOG_STATS,
                Permission.LOG_SEARCH,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_DASHBOARD,
                Permission.ANALYTICS_REPORTS,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_HEALTH,
                Permission.SYSTEM_METRICS,
                Permission.AI_QUERY,
                Permission.AI_VECTORSTORE,
            },
            UserRole.ANALYST: {
                # Analyst can perform security analysis tasks
                Permission.USER_READ,  # Can view own profile
                Permission.CHAT_CREATE,
                Permission.CHAT_READ,
                Permission.CHAT_DELETE,  # Can delete own chats
                Permission.CHAT_LIST,  # Can list own chats
                Permission.LOG_READ,
                Permission.LOG_STATS,
                Permission.LOG_SEARCH,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_DASHBOARD,
                Permission.SYSTEM_HEALTH,  # Can check system status
                Permission.AI_QUERY,
            },
            UserRole.VIEWER: {
                # Viewer has read-only access
                Permission.USER_READ,  # Can view own profile
                Permission.CHAT_READ,  # Can view own chats
                Permission.CHAT_LIST,  # Can list own chats
                Permission.LOG_READ,
                Permission.LOG_STATS,
                Permission.ANALYTICS_READ,
                Permission.SYSTEM_HEALTH,  # Can check system status
                Permission.AI_QUERY,  # Can query AI but with limitations
            }
        }
    
    def get_role_permissions(self, role: UserRole) -> Set[Permission]:
        """
        Get permissions for a specific role.
        
        Args:
            role: User role to get permissions for
            
        Returns:
            Set of permissions for the role
        """
        return self._role_permissions.get(role, set())
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user: User to check permissions for
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user.is_active:
            return False
        
        user_role = UserRole(user.role)
        role_permissions = self.get_role_permissions(user_role)
        return permission in role_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if a user has any of the specified permissions.
        
        Args:
            user: User to check permissions for
            permissions: List of permissions to check
            
        Returns:
            True if user has any of the permissions, False otherwise
        """
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if a user has all of the specified permissions.
        
        Args:
            user: User to check permissions for
            permissions: List of permissions to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        return all(self.has_permission(user, perm) for perm in permissions)
    
    def require_permission(self, user: User, permission: Permission) -> None:
        """
        Require a user to have a specific permission.
        
        Args:
            user: User to check permissions for
            permission: Required permission
            
        Raises:
            HTTPException: If user doesn't have the required permission
        """
        if not self.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
    
    def require_any_permission(self, user: User, permissions: List[Permission]) -> None:
        """
        Require a user to have any of the specified permissions.
        
        Args:
            user: User to check permissions for
            permissions: List of permissions (user needs at least one)
            
        Raises:
            HTTPException: If user doesn't have any of the required permissions
        """
        if not self.has_any_permission(user, permissions):
            permission_names = [perm.value for perm in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(permission_names)}"
            )
    
    def require_all_permissions(self, user: User, permissions: List[Permission]) -> None:
        """
        Require a user to have all of the specified permissions.
        
        Args:
            user: User to check permissions for
            permissions: List of permissions (user needs all)
            
        Raises:
            HTTPException: If user doesn't have all required permissions
        """
        if not self.has_all_permissions(user, permissions):
            permission_names = [perm.value for perm in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(permission_names)}"
            )
    
    def can_access_user_data(self, current_user: User, target_user_id: UUID) -> bool:
        """
        Check if a user can access another user's data.
        
        Args:
            current_user: User requesting access
            target_user_id: ID of user whose data is being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Users can always access their own data
        if current_user.id == target_user_id:
            return True
        
        # Admins can access any user's data
        if self.has_permission(current_user, Permission.USER_READ):
            return True
        
        return False
    
    def can_modify_user(self, current_user: User, target_user: User) -> bool:
        """
        Check if a user can modify another user's account.
        
        Args:
            current_user: User requesting modification
            target_user: User to be modified
            
        Returns:
            True if modification is allowed, False otherwise
        """
        # Only admins can modify other users
        if not self.has_permission(current_user, Permission.USER_UPDATE):
            return False
        
        # Prevent admins from modifying other admins (unless it's themselves)
        if (target_user.role == UserRole.ADMIN and 
            current_user.id != target_user.id):
            return False
        
        return True
    
    def can_delete_user(self, current_user: User, target_user: User) -> bool:
        """
        Check if a user can delete another user's account.
        
        Args:
            current_user: User requesting deletion
            target_user: User to be deleted
            
        Returns:
            True if deletion is allowed, False otherwise
        """
        # Only admins can delete users
        if not self.has_permission(current_user, Permission.USER_DELETE):
            return False
        
        # Prevent self-deletion
        if current_user.id == target_user.id:
            return False
        
        # Prevent deletion of other admins
        if target_user.role == UserRole.ADMIN:
            return False
        
        return True
    
    def filter_user_list(self, current_user: User, users: List[User]) -> List[User]:
        """
        Filter user list based on current user's permissions.
        
        Args:
            current_user: User requesting the list
            users: List of users to filter
            
        Returns:
            Filtered list of users
        """
        # Admins can see all users
        if self.has_permission(current_user, Permission.USER_LIST):
            return users
        
        # Other users can only see themselves
        return [user for user in users if user.id == current_user.id]
    
    def get_accessible_roles(self, current_user: User) -> List[UserRole]:
        """
        Get list of roles that a user can assign to others.
        
        Args:
            current_user: User requesting role assignment
            
        Returns:
            List of assignable roles
        """
        if not self.has_permission(current_user, Permission.USER_CREATE):
            return []
        
        # Admins can assign any role except admin (to prevent privilege escalation)
        if current_user.role == UserRole.ADMIN:
            return [UserRole.ANALYST, UserRole.VIEWER]
        
        return []
    
    def validate_role_assignment(self, current_user: User, target_role: UserRole) -> None:
        """
        Validate if a user can assign a specific role.
        
        Args:
            current_user: User attempting role assignment
            target_role: Role to be assigned
            
        Raises:
            HTTPException: If role assignment is not allowed
        """
        accessible_roles = self.get_accessible_roles(current_user)
        
        if target_role not in accessible_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot assign role: {target_role.value}"
            )
    
    def create_user(self, current_user: User, user_data: UserCreate, db: Session) -> User:
        """
        Create a new user with permission validation.
        
        Args:
            current_user: User creating the new user
            user_data: User creation data
            db: Database session
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: If user creation is not allowed
        """
        # Check permission to create users
        self.require_permission(current_user, Permission.USER_CREATE)
        
        # Validate role assignment
        self.validate_role_assignment(current_user, user_data.role)
        
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
        
        # Create user (password hashing should be done by auth service)
        from services.auth_service import get_auth_service
        auth_service = get_auth_service()
        
        return auth_service.create_user(user_data, db)
    
    def update_user(self, current_user: User, target_user_id: UUID, 
                   user_data: UserUpdate, db: Session) -> User:
        """
        Update a user with permission validation.
        
        Args:
            current_user: User performing the update
            target_user_id: ID of user to update
            user_data: User update data
            db: Database session
            
        Returns:
            Updated user object
            
        Raises:
            HTTPException: If user update is not allowed
        """
        # Get target user
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check permission to modify user
        if not self.can_modify_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify this user"
            )
        
        # Validate role change if provided
        if user_data.role is not None and user_data.role != target_user.role:
            self.validate_role_assignment(current_user, user_data.role)
        
        # Update user fields
        if user_data.email is not None:
            # Check if email is already taken by another user
            existing_user = db.query(User).filter(
                User.email == user_data.email,
                User.id != target_user_id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            target_user.email = user_data.email
        
        if user_data.role is not None:
            target_user.role = user_data.role
        
        if user_data.is_active is not None:
            target_user.is_active = user_data.is_active
        
        db.commit()
        db.refresh(target_user)
        
        return target_user
    
    def delete_user(self, current_user: User, target_user_id: UUID, db: Session) -> None:
        """
        Delete a user with permission validation.
        
        Args:
            current_user: User performing the deletion
            target_user_id: ID of user to delete
            db: Database session
            
        Raises:
            HTTPException: If user deletion is not allowed
        """
        # Get target user
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check permission to delete user
        if not self.can_delete_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete this user"
            )
        
        # Soft delete by deactivating user
        target_user.is_active = False
        db.commit()
    
    def list_users(self, current_user: User, db: Session) -> List[User]:
        """
        List users with permission filtering.
        
        Args:
            current_user: User requesting the list
            db: Database session
            
        Returns:
            List of users accessible to current user
        """
        # Get all users
        all_users = db.query(User).all()
        
        # Filter based on permissions
        return self.filter_user_list(current_user, all_users)


# Global RBAC service instance
rbac_service = RBACService()


def get_rbac_service() -> RBACService:
    """Get RBAC service instance."""
    return rbac_service