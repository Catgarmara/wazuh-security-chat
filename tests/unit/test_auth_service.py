"""
Test suite for authentication service JWT token management.

This module tests JWT token generation, validation, refresh functionality,
password hashing, and token blacklisting mechanisms.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.auth_service import AuthService, get_auth_service
from models.database import User, UserRole
from models.schemas import LoginRequest, UserCreate


class TestAuthService:
    """Test cases for AuthService JWT token management."""
    
    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing."""
        return AuthService()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            role=UserRole.ANALYST,
            is_active=True,
            created_at=datetime.utcnow(),
            last_login=None
        )
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    def test_hash_password(self, auth_service):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)
        
        # Verify hash is different from original password
        assert hashed != password
        # Verify hash starts with bcrypt identifier
        assert hashed.startswith("$2b$")
        # Verify hash length is reasonable
        assert len(hashed) >= 50
    
    def test_verify_password_success(self, auth_service):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)
        
        # Verify correct password
        assert auth_service.verify_password(password, hashed) is True
    
    def test_verify_password_failure(self, auth_service):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_service.hash_password(password)
        
        # Verify incorrect password
        assert auth_service.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self, auth_service):
        """Test password verification with invalid hash."""
        password = "testpassword123"
        invalid_hash = "invalid_hash"
        
        # Verify invalid hash returns False
        assert auth_service.verify_password(password, invalid_hash) is False
    
    @patch('services.auth_service.get_redis_client')
    def test_create_access_token(self, mock_redis, auth_service, mock_user):
        """Test access token creation."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        token_data = auth_service.create_access_token(mock_user)
        
        # Verify token structure
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data
        assert "expires_at" in token_data
        
        # Verify token type
        assert token_data["token_type"] == "bearer"
        
        # Verify expiration time
        assert token_data["expires_in"] == auth_service._access_token_expire_minutes * 60
        
        # Verify token is a string
        assert isinstance(token_data["access_token"], str)
        assert len(token_data["access_token"]) > 0
    
    @patch('services.auth_service.get_redis_client')
    def test_create_refresh_token(self, mock_redis, auth_service, mock_user):
        """Test refresh token creation."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        auth_service.redis_client = mock_redis_client
        
        token_data = auth_service.create_refresh_token(mock_user)
        
        # Verify token structure
        assert "refresh_token" in token_data
        assert "token_id" in token_data
        assert "expires_in" in token_data
        assert "expires_at" in token_data
        
        # Verify expiration time
        expected_expires_in = auth_service._refresh_token_expire_days * 24 * 60 * 60
        assert token_data["expires_in"] == expected_expires_in
        
        # Verify Redis storage was called
        mock_redis_client.setex.assert_called_once()
        
        # Verify token is a string
        assert isinstance(token_data["refresh_token"], str)
        assert len(token_data["refresh_token"]) > 0
    
    @patch('services.auth_service.get_redis_client')
    def test_verify_access_token_success(self, mock_redis, auth_service, mock_user):
        """Test successful access token verification."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.exists.return_value = False  # Token not blacklisted
        
        # Create token
        token_data = auth_service.create_access_token(mock_user)
        token = token_data["access_token"]
        
        # Verify token
        payload = auth_service.verify_token(token, "access")
        
        # Verify payload contents
        assert payload["sub"] == str(mock_user.id)
        assert payload["username"] == mock_user.username
        assert payload["email"] == mock_user.email
        assert payload["role"] == mock_user.role
        assert payload["type"] == "access"
    
    @patch('services.auth_service.get_redis_client')
    def test_verify_refresh_token_success(self, mock_redis, auth_service, mock_user):
        """Test successful refresh token verification."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.exists.return_value = True  # Token exists in Redis
        auth_service.redis_client = mock_redis_client
        
        # Create token
        token_data = auth_service.create_refresh_token(mock_user)
        token = token_data["refresh_token"]
        
        # Verify token
        payload = auth_service.verify_token(token, "refresh")
        
        # Verify payload contents
        assert payload["sub"] == str(mock_user.id)
        assert payload["username"] == mock_user.username
        assert payload["type"] == "refresh"
        assert "jti" in payload
    
    @patch('services.auth_service.get_redis_client')
    def test_verify_token_blacklisted(self, mock_redis, auth_service, mock_user):
        """Test verification of blacklisted access token."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.exists.return_value = True  # Token is blacklisted
        
        # Create token
        token_data = auth_service.create_access_token(mock_user)
        token = token_data["access_token"]
        
        # Verify token raises exception
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(token, "access")
        
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail
    
    @patch('services.auth_service.get_redis_client')
    def test_verify_token_wrong_type(self, mock_redis, auth_service, mock_user):
        """Test verification with wrong token type."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Create access token
        token_data = auth_service.create_access_token(mock_user)
        token = token_data["access_token"]
        
        # Try to verify as refresh token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(token, "refresh")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail
    
    def test_verify_token_invalid(self, auth_service):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(invalid_token, "access")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    @patch('services.auth_service.get_redis_client')
    def test_blacklist_access_token(self, mock_redis, auth_service, mock_user):
        """Test access token blacklisting."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        auth_service.redis_client = mock_redis_client
        
        # Create token
        token_data = auth_service.create_access_token(mock_user)
        token = token_data["access_token"]
        
        # Blacklist token
        auth_service.blacklist_token(token, "access")
        
        # Verify Redis setex was called
        mock_redis_client.setex.assert_called()
    
    @patch('services.auth_service.get_redis_client')
    def test_blacklist_refresh_token(self, mock_redis, auth_service, mock_user):
        """Test refresh token blacklisting."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        auth_service.redis_client = mock_redis_client
        
        # Create token
        token_data = auth_service.create_refresh_token(mock_user)
        token = token_data["refresh_token"]
        
        # Blacklist token
        auth_service.blacklist_token(token, "refresh")
        
        # Verify Redis delete was called
        mock_redis_client.delete.assert_called()
    
    def test_authenticate_user_success(self, auth_service, mock_db):
        """Test successful user authentication."""
        # Setup mock user with hashed password
        password = "testpassword123"
        hashed_password = auth_service.hash_password(password)
        
        mock_user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash=hashed_password,
            role=UserRole.ANALYST,
            is_active=True
        )
        
        # Setup mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Create login request
        login_data = LoginRequest(username="testuser", password=password)
        
        # Authenticate user
        result = auth_service.authenticate_user(login_data, mock_db)
        
        # Verify result
        assert result == mock_user
        assert mock_db.commit.called
    
    def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test authentication with non-existent user."""
        # Setup mock database query to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Create login request
        login_data = LoginRequest(username="nonexistent", password="password")
        
        # Verify authentication raises exception
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_user(login_data, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail
    
    def test_authenticate_user_wrong_password(self, auth_service, mock_db):
        """Test authentication with wrong password."""
        # Setup mock user with different password
        correct_password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed_password = auth_service.hash_password(correct_password)
        
        mock_user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash=hashed_password,
            role=UserRole.ANALYST,
            is_active=True
        )
        
        # Setup mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Create login request with wrong password
        login_data = LoginRequest(username="testuser", password=wrong_password)
        
        # Verify authentication raises exception
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_user(login_data, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail
    
    def test_create_user_success(self, auth_service, mock_db):
        """Test successful user creation."""
        # Setup mock database query to return None (no existing user)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Create user data
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="newpassword123",
            role=UserRole.ANALYST
        )
        
        # Create user
        result = auth_service.create_user(user_data, mock_db)
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
    
    def test_create_user_duplicate_username(self, auth_service, mock_db):
        """Test user creation with duplicate username."""
        # Setup existing user
        existing_user = User(
            id=uuid4(),
            username="existinguser",
            email="different@example.com",
            password_hash="hash",
            role=UserRole.ANALYST,
            is_active=True
        )
        
        # Setup mock database query to return existing user
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        # Create user data with same username
        user_data = UserCreate(
            username="existinguser",
            email="new@example.com",
            password="newpassword123",
            role=UserRole.ANALYST
        )
        
        # Verify user creation raises exception
        with pytest.raises(HTTPException) as exc_info:
            auth_service.create_user(user_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Username already exists" in exc_info.value.detail
    
    def test_get_auth_service(self):
        """Test auth service singleton function."""
        service1 = get_auth_service()
        service2 = get_auth_service()
        
        # Verify same instance is returned
        assert service1 is service2
        assert isinstance(service1, AuthService)


if __name__ == "__main__":
    pytest.main([__file__])