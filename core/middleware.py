"""
Authentication middleware for FastAPI application.

This module provides middleware for handling authentication, CORS,
security headers, and request/response processing.
"""

import time
import uuid
from typing import Callable, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from core.config import get_settings
from core.exceptions import WazuhChatException, AuthenticationError
from services.auth_service import get_auth_service


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP header
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response information."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        if self.settings.debug:
            print(f"[{request_id}] {request.method} {request.url}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add request ID and processing time to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            if self.settings.debug:
                print(f"[{request_id}] {response.status_code} - {process_time:.3f}s")
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            print(f"[{request_id}] ERROR - {process_time:.3f}s: {str(e)}")
            
            # Re-raise the exception
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication for protected routes."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.auth_service = get_auth_service()
        self.settings = get_settings()
        
        # Routes that don't require authentication
        self.public_routes = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            f"{self.settings.api_prefix}/auth/login",
            f"{self.settings.api_prefix}/auth/refresh",
        }
        
        # Routes that require authentication
        self.protected_prefixes = [
            f"{self.settings.api_prefix}/",
            "/ws/"
        ]
    
    def _is_public_route(self, path: str) -> bool:
        """Check if a route is public (doesn't require authentication)."""
        # Check exact matches
        if path in self.public_routes:
            return True
        
        # Check if path starts with any protected prefix
        for prefix in self.protected_prefixes:
            if path.startswith(prefix):
                return False
        
        # Default to public for other routes
        return True
    
    def _extract_token_from_header(self, authorization: str) -> Optional[str]:
        """Extract token from Authorization header."""
        if not authorization:
            return None
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle authentication for protected routes."""
        path = request.url.path
        
        # Skip authentication for public routes
        if self._is_public_route(path):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        token = self._extract_token_from_header(authorization)
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error_code": "MISSING_TOKEN",
                    "message": "Authorization token required",
                    "timestamp": time.time(),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
        
        try:
            # Verify token and get user
            from core.database import get_db
            from sqlalchemy.orm import Session
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                # Get current user
                user = self.auth_service.get_current_user(token, db)
                
                # Add user to request state
                request.state.current_user = user
                request.state.access_token = token
                
                # Process request
                response = await call_next(request)
                return response
                
            finally:
                # Close database session
                db.close()
                
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error_code": "AUTHENTICATION_FAILED",
                    "message": e.detail,
                    "timestamp": time.time(),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Authentication service error",
                    "timestamp": time.time(),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting."""
    
    def __init__(self, app: FastAPI, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
        self.window_size = 60  # 1 minute window
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                timestamp for timestamp in self.request_counts[client_ip]
                if timestamp > window_start
            ]
        else:
            self.request_counts[client_ip] = []
        
        # Check if rate limit exceeded
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            return True
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc"]:
            return await call_next(request)
        
        # Check rate limit
        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                    "timestamp": time.time(),
                    "request_id": getattr(request.state, "request_id", None)
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60)
                }
            )
        
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the FastAPI application."""
    settings = get_settings()
    
    # Trusted host middleware (should be first)
    if settings.environment.value != "development":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure based on your deployment
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # Session middleware (for WebSocket sessions)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.security.secret_key,
        max_age=settings.security.access_token_expire_minutes * 60
    )
    
    # Rate limiting middleware
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=100  # Adjust based on your needs
    )
    
    # Input sanitization middleware
    from core.input_sanitization import InputSanitizationMiddleware
    app.add_middleware(
        InputSanitizationMiddleware,
        strict_paths=["/api/v1/auth/", "/api/v1/admin/"]
    )
    
    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Authentication middleware (should be last)
    app.add_middleware(AuthenticationMiddleware)


# Exception handlers
async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Handle authentication exceptions."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error_code": "AUTHENTICATION_ERROR",
            "message": str(exc),
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def wazuh_chat_exception_handler(request: Request, exc: WazuhChatException) -> JSONResponse:
    """Handle application-specific exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "APPLICATION_ERROR",
            "message": str(exc),
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Set up exception handlers for the FastAPI application."""
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(WazuhChatException, wazuh_chat_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)