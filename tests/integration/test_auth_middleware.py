"""
Test suite for authentication middleware and dependencies.

This module tests FastAPI dependencies for token validation,
role-based route protection, and authentication middleware.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from core.middleware import (
    AuthenticationMiddleware, SecurityHeadersMiddleware,
    RequestLoggingMiddleware, RateLimitingMiddleware,
    setup_middleware, setup_exception_handlers
)
from core.permissions import (
    get_current_user, get_current_active_user,
    require_permission, require_any_permission,
    PermissionChecker, SelfOrPermissionChecker,
    admin_required
)
from services.rbac_service import Permission
from models.database import User, UserRole


class TestAuthenticationMiddleware:
    """Test cases for authentication middleware."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/api/v1/protected")
        async def protected_endpoint():
            return {"message": "protected"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with middleware."""
        app.add_middleware(AuthenticationMiddleware)
        return TestClient(app)
    
    def test_public_route_no_auth(self, client):
        """Test public route doesn't require authentication."""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}
    
    def test_protected_route_no_token(self, client):
        """Test protected route requires token."""
        response = client.get("/api/v1/protected")
        assert response.status_code == 401
        assert "Authorization token required" in response.json()["message"]
    
    def test_protected_route_invalid_token_format(self, client):
        """Test protected route with invalid token format."""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/v1/protected", headers=headers)
        assert response.status_code == 401
        assert "Authorization token required" in response.json()["message"]
    
    @patch('core.middleware.get_auth_service')
    @patch('core.middleware.get_db')
    def test_protected_route_valid_token(self, mock_get_db, mock_get_auth_service, client):
        """Test protected route with valid token."""
        # Setup mocks
        mock_user = User(id=uuid4(), username="test", role=UserRole.ANALYST, is_active=True)
        mock_auth_service = Mock()
        mock_auth_service.get_current_user.return_value = mock_user
        mock_get_auth_service.return_value = mock_auth_service
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        headers = {"Authorization": "Bearer valid_token"}
        response = client.get("/api/v1/protected", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "protected"}
    
    @patch('core.middleware.get_auth_service')
    @patch('core.middleware.get_db')
    def test_protected_route_invalid_token(self, mock_get_db, mock_get_auth_service, client):
        """Test protected route with invalid token."""
        # Setup mocks
        mock_auth_service = Mock()
        mock_auth_service.get_current_user.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/protected", headers=headers)
        assert response.status_code == 401
        assert "Invalid token" in response.json()["message"]


class TestSecurityHeadersMiddleware:
    """Test cases for security headers middleware."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with security headers middleware."""
        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app)
    
    def test_security_headers_added(self, client):
        """Test security headers are added to responses."""
        response = client.get("/test")
        
        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in response.headers


class TestRateLimitingMiddleware:
    """Test cases for rate limiting middleware."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with rate limiting middleware."""
        app.add_middleware(RateLimitingMiddleware, requests_per_minute=2)
        return TestClient(app)
    
    def test_rate_limiting_allows_requests(self, client):
        """Test rate limiting allows requests within limit."""
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    def test_rate_limiting_blocks_excess_requests(self, client):
        """Test rate limiting blocks requests over limit."""
        # Make requests up to limit
        for _ in range(2):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["message"]


class TestPermissionDependencies:
    """Test cases for permission checking dependencies."""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            role=UserRole.ANALYST,
            is_active=True
        )
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user for testing."""
        return User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True
        )
    
    @pytest.fixture
    def mock_inactive_user(self):
        """Create mock inactive user for testing."""
        return User(
            id=uuid4(),
            username="inactive",
            email="inactive@example.com",
            role=UserRole.ANALYST,
            is_active=False
        )
    
    @patch('core.permissions.get_auth_service')
    def test_get_current_user_success(self, mock_get_auth_service, mock_user):
        """Test successful current user retrieval."""
        # Setup mocks
        mock_auth_service = Mock()
        mock_auth_service.get_current_user.return_value = mock_user
        mock_get_auth_service.return_value = mock_auth_service
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        mock_db = Mock()
        
        # Test dependency
        result = get_current_user(mock_credentials, mock_db)
        
        assert result == mock_user
        mock_auth_service.get_current_user.assert_called_once_with("valid_token", mock_db)
    
    def test_get_current_active_user_success(self, mock_user):
        """Test successful active user check."""
        result = get_current_active_user(mock_user)
        assert result == mock_user
    
    def test_get_current_active_user_inactive(self, mock_inactive_user):
        """Test active user check with inactive user."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(mock_inactive_user)
        
        assert exc_info.value.status_code == 403
        assert "Inactive user account" in exc_info.value.detail
    
    @patch('core.permissions.get_rbac_service')
    def test_permission_checker_success(self, mock_get_rbac_service, mock_user):
        """Test successful permission checking."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.require_permission.return_value = None
        mock_get_rbac_service.return_value = mock_rbac_service
        
        # Test permission checker
        checker = PermissionChecker(Permission.AI_QUERY)
        result = checker(mock_user)
        
        assert result == mock_user
        mock_rbac_service.require_permission.assert_called_once_with(mock_user, Permission.AI_QUERY)
    
    @patch('core.permissions.get_rbac_service')
    def test_permission_checker_failure(self, mock_get_rbac_service, mock_user):
        """Test failed permission checking."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.require_permission.side_effect = HTTPException(
            status_code=403, detail="Insufficient permissions"
        )
        mock_get_rbac_service.return_value = mock_rbac_service
        
        # Test permission checker
        checker = PermissionChecker(Permission.USER_CREATE)
        
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    @patch('core.permissions.get_rbac_service')
    def test_self_or_permission_checker_self_access(self, mock_get_rbac_service, mock_user):
        """Test self access in SelfOrPermissionChecker."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_get_rbac_service.return_value = mock_rbac_service
        
        # Test self access
        checker = SelfOrPermissionChecker(Permission.USER_READ)
        result = checker(mock_user.id, mock_user)
        
        assert result == mock_user
        # Should not check permission for self access
        mock_rbac_service.has_permission.assert_not_called()
    
    @patch('core.permissions.get_rbac_service')
    def test_self_or_permission_checker_permission_access(self, mock_get_rbac_service, mock_admin_user):
        """Test permission access in SelfOrPermissionChecker."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.has_permission.return_value = True
        mock_get_rbac_service.return_value = mock_rbac_service
        
        other_user_id = uuid4()
        
        # Test permission access
        checker = SelfOrPermissionChecker(Permission.USER_READ)
        result = checker(other_user_id, mock_admin_user)
        
        assert result == mock_admin_user
        mock_rbac_service.has_permission.assert_called_once_with(mock_admin_user, Permission.USER_READ)
    
    @patch('core.permissions.get_rbac_service')
    def test_self_or_permission_checker_denied(self, mock_get_rbac_service, mock_user):
        """Test denied access in SelfOrPermissionChecker."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.has_permission.return_value = False
        mock_get_rbac_service.return_value = mock_rbac_service
        
        other_user_id = uuid4()
        
        # Test denied access
        checker = SelfOrPermissionChecker(Permission.USER_READ)
        
        with pytest.raises(HTTPException) as exc_info:
            checker(other_user_id, mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    def test_admin_required_success(self, mock_admin_user):
        """Test successful admin requirement."""
        result = admin_required(mock_admin_user)
        assert result == mock_admin_user
    
    def test_admin_required_failure(self, mock_user):
        """Test failed admin requirement."""
        with pytest.raises(HTTPException) as exc_info:
            admin_required(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail


class TestPermissionDecorators:
    """Test cases for permission decorators."""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            role=UserRole.ANALYST,
            is_active=True
        )
    
    @patch('core.permissions.get_rbac_service')
    async def test_require_permission_decorator_success(self, mock_get_rbac_service, mock_user):
        """Test successful permission decorator."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.require_permission.return_value = None
        mock_get_rbac_service.return_value = mock_rbac_service
        
        # Create decorated function
        @require_permission(Permission.AI_QUERY)
        async def test_function(current_user=None):
            return {"message": "success"}
        
        # Test function call
        result = await test_function(current_user=mock_user)
        
        assert result == {"message": "success"}
        mock_rbac_service.require_permission.assert_called_once_with(mock_user, Permission.AI_QUERY)
    
    @patch('core.permissions.get_rbac_service')
    async def test_require_permission_decorator_failure(self, mock_get_rbac_service, mock_user):
        """Test failed permission decorator."""
        # Setup mocks
        mock_rbac_service = Mock()
        mock_rbac_service.require_permission.side_effect = HTTPException(
            status_code=403, detail="Insufficient permissions"
        )
        mock_get_rbac_service.return_value = mock_rbac_service
        
        # Create decorated function
        @require_permission(Permission.USER_CREATE)
        async def test_function(current_user=None):
            return {"message": "success"}
        
        # Test function call
        with pytest.raises(HTTPException) as exc_info:
            await test_function(current_user=mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    async def test_require_permission_decorator_no_user(self):
        """Test permission decorator without user."""
        # Create decorated function
        @require_permission(Permission.AI_QUERY)
        async def test_function(current_user=None):
            return {"message": "success"}
        
        # Test function call without user
        with pytest.raises(HTTPException) as exc_info:
            await test_function()
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


class TestMiddlewareSetup:
    """Test cases for middleware setup functions."""
    
    def test_setup_middleware(self):
        """Test middleware setup function."""
        app = FastAPI()
        
        # Setup middleware
        setup_middleware(app)
        
        # Verify middleware was added (check by counting middleware)
        assert len(app.user_middleware) > 0
    
    def test_setup_exception_handlers(self):
        """Test exception handlers setup function."""
        app = FastAPI()
        
        # Setup exception handlers
        setup_exception_handlers(app)
        
        # Verify exception handlers were added
        assert len(app.exception_handlers) > 0


if __name__ == "__main__":
    pytest.main([__file__])