"""
Permission checking decorators and middleware for RBAC.

This module provides decorators and middleware for enforcing role-based
access control throughout the application.
"""

from functools import wraps
from typing import List, Callable, Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from services.auth_service import get_auth_service
from services.rbac_service import get_rbac_service, Permission
from models.database import User


# HTTP Bearer token scheme for FastAPI
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_service = get_auth_service()
    token = credentials.credentials
    return auth_service.get_current_user(token, db)


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for a route.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (should be injected by FastAPI)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission
            rbac_service = get_rbac_service()
            rbac_service.require_permission(current_user, permission)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[Permission]):
    """
    Decorator to require any of the specified permissions for a route.
    
    Args:
        permissions: List of permissions (user needs at least one)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions
            rbac_service = get_rbac_service()
            rbac_service.require_any_permission(current_user, permissions)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(permissions: List[Permission]):
    """
    Decorator to require all of the specified permissions for a route.
    
    Args:
        permissions: List of permissions (user needs all)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions
            rbac_service = get_rbac_service()
            rbac_service.require_all_permissions(current_user, permissions)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_self_or_permission(permission: Permission):
    """
    Decorator to require either accessing own data or having a specific permission.
    
    Args:
        permission: Permission required for accessing other users' data
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user and target_user_id from kwargs
            current_user = kwargs.get('current_user')
            target_user_id = kwargs.get('user_id') or kwargs.get('target_user_id')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not target_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target user ID required"
                )
            
            # Check if user is accessing their own data or has permission
            rbac_service = get_rbac_service()
            if (current_user.id != target_user_id and 
                not rbac_service.has_permission(current_user, permission)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """FastAPI dependency class for checking permissions."""
    
    def __init__(self, permission: Permission):
        """
        Initialize permission checker.
        
        Args:
            permission: Required permission
        """
        self.permission = permission
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if current user has required permission.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if permission check passes
            
        Raises:
            HTTPException: If user doesn't have required permission
        """
        rbac_service = get_rbac_service()
        rbac_service.require_permission(current_user, self.permission)
        return current_user


class AnyPermissionChecker:
    """FastAPI dependency class for checking any of multiple permissions."""
    
    def __init__(self, permissions: List[Permission]):
        """
        Initialize permission checker.
        
        Args:
            permissions: List of permissions (user needs at least one)
        """
        self.permissions = permissions
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if current user has any of the required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if permission check passes
            
        Raises:
            HTTPException: If user doesn't have any required permission
        """
        rbac_service = get_rbac_service()
        rbac_service.require_any_permission(current_user, self.permissions)
        return current_user


class AllPermissionsChecker:
    """FastAPI dependency class for checking all of multiple permissions."""
    
    def __init__(self, permissions: List[Permission]):
        """
        Initialize permission checker.
        
        Args:
            permissions: List of permissions (user needs all)
        """
        self.permissions = permissions
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if current user has all of the required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if permission check passes
            
        Raises:
            HTTPException: If user doesn't have all required permissions
        """
        rbac_service = get_rbac_service()
        rbac_service.require_all_permissions(current_user, self.permissions)
        return current_user


class SelfOrPermissionChecker:
    """FastAPI dependency class for checking self-access or permission."""
    
    def __init__(self, permission: Permission):
        """
        Initialize permission checker.
        
        Args:
            permission: Permission required for accessing other users' data
        """
        self.permission = permission
    
    def __call__(
        self, 
        user_id: UUID,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Check if current user can access target user's data.
        
        Args:
            user_id: Target user ID
            current_user: Current authenticated user
            
        Returns:
            Current user if access check passes
            
        Raises:
            HTTPException: If user cannot access target data
        """
        rbac_service = get_rbac_service()
        if (current_user.id != user_id and 
            not rbac_service.has_permission(current_user, self.permission)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user


# Common permission dependency instances
RequireUserCreate = PermissionChecker(Permission.USER_CREATE)
RequireUserRead = PermissionChecker(Permission.USER_READ)
RequireUserUpdate = PermissionChecker(Permission.USER_UPDATE)
RequireUserDelete = PermissionChecker(Permission.USER_DELETE)
RequireUserList = PermissionChecker(Permission.USER_LIST)

RequireChatCreate = PermissionChecker(Permission.CHAT_CREATE)
RequireChatRead = PermissionChecker(Permission.CHAT_READ)
RequireChatDelete = PermissionChecker(Permission.CHAT_DELETE)
RequireChatList = PermissionChecker(Permission.CHAT_LIST)

RequireLogRead = PermissionChecker(Permission.LOG_READ)
RequireLogReload = PermissionChecker(Permission.LOG_RELOAD)
RequireLogStats = PermissionChecker(Permission.LOG_STATS)
RequireLogSearch = PermissionChecker(Permission.LOG_SEARCH)

RequireAnalyticsRead = PermissionChecker(Permission.ANALYTICS_READ)
RequireAnalyticsDashboard = PermissionChecker(Permission.ANALYTICS_DASHBOARD)
RequireAnalyticsReports = PermissionChecker(Permission.ANALYTICS_REPORTS)

RequireSystemConfig = PermissionChecker(Permission.SYSTEM_CONFIG)
RequireSystemHealth = PermissionChecker(Permission.SYSTEM_HEALTH)
RequireSystemMetrics = PermissionChecker(Permission.SYSTEM_METRICS)

RequireAIQuery = PermissionChecker(Permission.AI_QUERY)
RequireAIVectorstore = PermissionChecker(Permission.AI_VECTORSTORE)

# Self-access or permission checkers
SelfOrUserRead = SelfOrPermissionChecker(Permission.USER_READ)
SelfOrChatRead = SelfOrPermissionChecker(Permission.CHAT_READ)


def admin_required(current_user: User = Depends(get_current_active_user)) -> User:
    """
    FastAPI dependency to require admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin check passes
        
    Raises:
        HTTPException: If user is not an admin
    """
    from models.database import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def analyst_or_admin_required(current_user: User = Depends(get_current_active_user)) -> User:
    """
    FastAPI dependency to require analyst or admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if role check passes
        
    Raises:
        HTTPException: If user is not analyst or admin
    """
    from models.database import UserRole
    if current_user.role not in [UserRole.ANALYST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or Admin access required"
        )
    return current_user