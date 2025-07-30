"""
Authentication service for JWT token management and user authentication.

This module provides JWT token generation, validation, refresh functionality,
secure password hashing using bcrypt, and token blacklisting for logout.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import get_settings
from core.redis_client import get_redis_client
from core.metrics import metrics
from models.database import User, UserRole
from models.schemas import UserCreate, LoginRequest, TokenResponse, UserProfile


class AuthService:
    """Authentication service for managing JWT tokens and user authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        try:
            self.redis_client = get_redis_client()
        except RuntimeError:
            # For testing purposes, use a mock Redis client
            self.redis_client = None
        self._secret_key = self.settings.security.secret_key
        self._algorithm = self.settings.security.jwt_algorithm
        self._access_token_expire_minutes = self.settings.security.access_token_expire_minutes
        self._refresh_token_expire_days = self.settings.security.refresh_token_expire_days
        self._bcrypt_rounds = self.settings.security.bcrypt_rounds
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with salt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    def create_access_token(self, user: User) -> Dict[str, Any]:
        """
        Create a JWT access token for a user.
        
        Args:
            user: User object to create token for
            
        Returns:
            Dictionary containing token data
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self._access_token_expire_minutes)
        
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "iat": now,
            "exp": expire,
            "type": "access"
        }
        
        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        
        # Record token issuance
        metrics.record_token_issued()
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self._access_token_expire_minutes * 60,
            "expires_at": expire
        }
    
    def create_refresh_token(self, user: User) -> Dict[str, Any]:
        """
        Create a JWT refresh token for a user.
        
        Args:
            user: User object to create token for
            
        Returns:
            Dictionary containing refresh token data
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self._refresh_token_expire_days)
        
        # Generate a unique token ID for blacklisting
        token_id = secrets.token_urlsafe(32)
        
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "jti": token_id,  # JWT ID for blacklisting
            "iat": now,
            "exp": expire,
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        
        # Store token ID in Redis for blacklisting capability
        if self.redis_client:
            redis_key = f"refresh_token:{token_id}"
            self.redis_client.setex(
                redis_key,
                timedelta(days=self._refresh_token_expire_days),
                str(user.id)
            )
        
        return {
            "refresh_token": token,
            "token_id": token_id,
            "expires_in": self._refresh_token_expire_days * 24 * 60 * 60,
            "expires_at": expire
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Type of token ("access" or "refresh")
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            # Check if refresh token is blacklisted
            if token_type == "refresh":
                token_id = payload.get("jti")
                if not token_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid refresh token format"
                    )
                
                if self.redis_client:
                    redis_key = f"refresh_token:{token_id}"
                    if not self.redis_client.exists(redis_key):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token has been revoked"
                        )
            
            # Check if access token is blacklisted
            elif token_type == "access":
                if self.redis_client:
                    blacklist_key = f"blacklisted_token:{token}"
                    if self.redis_client.exists(blacklist_key):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has been revoked"
                        )
            
            # Record successful token validation
            metrics.record_token_validation("success")
            return payload
            
        except jwt.ExpiredSignatureError:
            metrics.record_token_validation("expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            metrics.record_token_validation("invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_access_token(self, refresh_token: str, db: Session) -> Dict[str, Any]:
        """
        Create a new access token using a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            db: Database session
            
        Returns:
            New access token data
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )
        
        # Get user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        return self.create_access_token(user)
    
    def blacklist_token(self, token: str, token_type: str = "access") -> None:
        """
        Blacklist a token to prevent its use.
        
        Args:
            token: Token to blacklist
            token_type: Type of token ("access" or "refresh")
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"verify_exp": False}  # Don't verify expiration for blacklisting
            )
            
            if token_type == "access":
                # Blacklist access token until its natural expiration
                exp = payload.get("exp")
                if exp:
                    expire_time = datetime.fromtimestamp(exp)
                    ttl = expire_time - datetime.utcnow()
                    if ttl.total_seconds() > 0 and self.redis_client:
                        blacklist_key = f"blacklisted_token:{token}"
                        self.redis_client.setex(blacklist_key, ttl, "blacklisted")
            
            elif token_type == "refresh":
                # Remove refresh token from Redis
                token_id = payload.get("jti")
                if token_id and self.redis_client:
                    redis_key = f"refresh_token:{token_id}"
                    self.redis_client.delete(redis_key)
                    
        except jwt.InvalidTokenError:
            # Token is already invalid, no need to blacklist
            pass
    
    def authenticate_user(self, login_data: LoginRequest, db: Session) -> User:
        """
        Authenticate a user with username/email and password.
        
        Args:
            login_data: Login credentials
            db: Database session
            
        Returns:
            Authenticated user object
            
        Raises:
            HTTPException: If authentication fails
        """
        # Try to find user by username or email
        user = db.query(User).filter(
            (User.username == login_data.username) | (User.email == login_data.username),
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not self.verify_password(login_data.password, user.password_hash):
            metrics.record_auth_attempt("failed", "password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Record successful authentication
        metrics.record_auth_attempt("success", "password")
        
        return user
    
    def create_user(self, user_data: UserCreate, db: Session) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            user_data: User creation data
            db: Database session
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: If user creation fails
        """
        # Check if username already exists
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
        
        # Hash password
        hashed_password = self.hash_password(user_data.password)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            role=user_data.role
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def login(self, login_data: LoginRequest, db: Session) -> TokenResponse:
        """
        Complete login process with token generation.
        
        Args:
            login_data: Login credentials
            db: Database session
            
        Returns:
            Token response with access and refresh tokens
        """
        # Authenticate user
        user = self.authenticate_user(login_data, db)
        
        # Create tokens
        access_token_data = self.create_access_token(user)
        refresh_token_data = self.create_refresh_token(user)
        
        # Create user profile
        user_profile = UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
        return TokenResponse(
            access_token=access_token_data["access_token"],
            token_type=access_token_data["token_type"],
            expires_in=access_token_data["expires_in"],
            user=user_profile
        )
    
    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """
        Logout user by blacklisting tokens.
        
        Args:
            access_token: Access token to blacklist
            refresh_token: Optional refresh token to blacklist
        """
        # Blacklist access token
        self.blacklist_token(access_token, "access")
        
        # Blacklist refresh token if provided
        if refresh_token:
            self.blacklist_token(refresh_token, "refresh")
    
    def get_current_user(self, token: str, db: Session) -> User:
        """
        Get current user from access token.
        
        Args:
            token: Access token
            db: Database session
            
        Returns:
            Current user object
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        # Verify token
        payload = self.verify_token(token, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user


# Global auth service instance
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    return auth_service