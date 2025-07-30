"""
Authentication API endpoints.

This module provides REST API endpoints for user authentication,
including login, logout, token refresh, and user profile management.
"""

import time
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import (
    get_current_user, get_current_active_user,
    RequireUserCreate, RequireUserUpdate, RequireUserDelete, RequireUserList,
    SelfOrUserRead, admin_required
)
from services.auth_service import get_auth_service
from services.rbac_service import get_rbac_service
from models.schemas import (
    LoginRequest, TokenResponse, TokenRefreshRequest,
    UserCreate, UserUpdate, UserResponse, UserProfile,
    PaginatedResponse, PaginationParams
)
from models.database import User


# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return access token.
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        Token response with access token and user profile
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_service = get_auth_service()
    return auth_service.login(login_data, db)


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token request
        db: Database session
        
    Returns:
        New access token data
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    auth_service = get_auth_service()
    return auth_service.refresh_access_token(refresh_data.refresh_token, db)


@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout user by blacklisting tokens.
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    auth_service = get_auth_service()
    access_token = credentials.credentials
    
    # Get refresh token from request body if provided
    refresh_token = None
    if hasattr(request, 'json'):
        try:
            body = await request.json()
            refresh_token = body.get('refresh_token')
        except:
            pass
    
    # Blacklist tokens
    auth_service.logout(access_token, refresh_token)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserProfile:
    """
    Get current user's profile information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile data
    """
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserProfile:
    """
    Update current user's profile information.
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user profile
    """
    rbac_service = get_rbac_service()
    
    # Users can only update their own email, not role or active status
    limited_update = UserUpdate(email=user_update.email)
    
    updated_user = rbac_service.update_user(
        current_user, current_user.id, limited_update, db
    )
    
    return UserProfile(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login
    )


# Admin-only user management endpoints

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(RequireUserCreate),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Create a new user (Admin only).
    
    Args:
        user_data: User creation data
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Created user data
        
    Raises:
        HTTPException: If user creation fails or insufficient permissions
    """
    rbac_service = get_rbac_service()
    created_user = rbac_service.create_user(current_user, user_data, db)
    
    return UserResponse(
        id=created_user.id,
        username=created_user.username,
        email=created_user.email,
        role=created_user.role,
        is_active=created_user.is_active,
        created_at=created_user.created_at,
        updated_at=created_user.updated_at,
        last_login=created_user.last_login
    )


@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(RequireUserList),
    db: Session = Depends(get_db)
) -> PaginatedResponse:
    """
    List all users (Admin only).
    
    Args:
        pagination: Pagination parameters
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Paginated list of users
    """
    rbac_service = get_rbac_service()
    users = rbac_service.list_users(current_user, db)
    
    # Apply pagination
    start = (pagination.page - 1) * pagination.size
    end = start + pagination.size
    paginated_users = users[start:end]
    
    # Convert to response format
    user_responses = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login
        )
        for user in paginated_users
    ]
    
    return PaginatedResponse(
        items=user_responses,
        total=len(users),
        page=pagination.page,
        size=pagination.size,
        pages=(len(users) + pagination.size - 1) // pagination.size
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(SelfOrUserRead),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get user by ID (Self or Admin only).
    
    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User data
        
    Raises:
        HTTPException: If user not found or insufficient permissions
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(RequireUserUpdate),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Update user by ID (Admin only).
    
    Args:
        user_id: User ID to update
        user_update: User update data
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Updated user data
        
    Raises:
        HTTPException: If user not found or insufficient permissions
    """
    rbac_service = get_rbac_service()
    updated_user = rbac_service.update_user(current_user, user_id, user_update, db)
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        last_login=updated_user.last_login
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(RequireUserDelete),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete user by ID (Admin only).
    
    Args:
        user_id: User ID to delete
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If user not found or insufficient permissions
    """
    rbac_service = get_rbac_service()
    rbac_service.delete_user(current_user, user_id, db)
    
    return {"message": "User successfully deleted"}


@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current user's permissions.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User permissions and role information
    """
    rbac_service = get_rbac_service()
    permissions = rbac_service.get_role_permissions(current_user.role)
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "permissions": [perm.value for perm in permissions],
        "accessible_roles": [role.value for role in rbac_service.get_accessible_roles(current_user)]
    }


@router.get("/health")
async def auth_health_check() -> Dict[str, str]:
    """
    Health check endpoint for authentication service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": str(int(time.time()))
    }