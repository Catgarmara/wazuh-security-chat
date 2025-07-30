"""
Audit logging middleware for automatic tracking of user actions and security events.

This middleware automatically logs audit events for all API requests and responses,
providing comprehensive audit trails for compliance and security monitoring.
"""

import json
import time
from typing import Callable, Optional, Dict, Any
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from services.audit_service import get_audit_service, AuditEventType, SecurityEventSeverity
from core.database import get_db


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log audit events for API requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_service = get_audit_service()
        
        # Define which endpoints should be audited
        self.audit_endpoints = {
            # Authentication endpoints
            "POST /api/v1/auth/login": AuditEventType.LOGIN_SUCCESS,
            "POST /api/v1/auth/logout": AuditEventType.LOGOUT,
            "POST /api/v1/auth/refresh": AuditEventType.TOKEN_REFRESH,
            "PUT /api/v1/auth/password": AuditEventType.PASSWORD_CHANGE,
            
            # User management endpoints
            "POST /api/v1/auth/users": AuditEventType.USER_CREATED,
            "PUT /api/v1/auth/users": AuditEventType.USER_UPDATED,
            "DELETE /api/v1/auth/users": AuditEventType.USER_DELETED,
            "PATCH /api/v1/auth/users": AuditEventType.USER_UPDATED,
            
            # Chat endpoints
            "POST /api/v1/chat/sessions": AuditEventType.CHAT_SESSION_STARTED,
            "DELETE /api/v1/chat/sessions": AuditEventType.CHAT_SESSION_ENDED,
            
            # Log management endpoints
            "POST /api/v1/logs/reload": AuditEventType.LOGS_RELOADED,
            "GET /api/v1/logs/search": AuditEventType.LOG_SEARCH_PERFORMED,
            "POST /api/v1/logs/export": AuditEventType.LOG_EXPORT,
            
            # System configuration
            "PUT /api/v1/config": AuditEventType.CONFIG_CHANGED,
            "PATCH /api/v1/config": AuditEventType.CONFIG_CHANGED,
        }
        
        # Define security-sensitive endpoints that should trigger security events
        self.security_endpoints = {
            "POST /api/v1/auth/login",
            "PUT /api/v1/auth/password",
            "POST /api/v1/auth/users",
            "DELETE /api/v1/auth/users",
            "POST /api/v1/logs/export",
        }
        
        # Define endpoints that should not be audited (to avoid noise)
        self.excluded_endpoints = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/api/v1/health",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit events."""
        # Skip audit logging for excluded endpoints
        if self._should_exclude_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract request information
        start_time = time.time()
        method = request.method
        path = request.url.path
        endpoint_key = f"{method} {path}"
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        session_id = getattr(request.state, "request_id", None)
        
        # Get current user if available
        current_user = getattr(request.state, "current_user", None)
        user_id = current_user.id if current_user else None
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log audit event if this is an auditable endpoint
        await self._log_audit_event(
            request=request,
            response=response,
            method=method,
            path=path,
            endpoint_key=endpoint_key,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent,
            session_id=session_id,
            processing_time=processing_time
        )
        
        # Log security events for sensitive operations
        await self._log_security_events(
            request=request,
            response=response,
            method=method,
            path=path,
            endpoint_key=endpoint_key,
            user_id=user_id,
            client_ip=client_ip,
            processing_time=processing_time
        )
        
        return response
    
    def _should_exclude_endpoint(self, path: str) -> bool:
        """Check if an endpoint should be excluded from audit logging."""
        # Check exact matches
        if path in self.excluded_endpoints:
            return True
        
        # Check if path starts with any excluded prefix
        for excluded in self.excluded_endpoints:
            if path.startswith(excluded):
                return True
        
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def _log_audit_event(
        self,
        request: Request,
        response: Response,
        method: str,
        path: str,
        endpoint_key: str,
        user_id: Optional[str],
        client_ip: str,
        user_agent: Optional[str],
        session_id: Optional[str],
        processing_time: float
    ):
        """Log audit event for the request."""
        try:
            # Determine event type
            event_type = self.audit_endpoints.get(endpoint_key)
            if not event_type:
                # For non-specific endpoints, use generic event types
                if method == "GET":
                    event_type = AuditEventType.DATA_ACCESS
                elif method in ["POST", "PUT", "PATCH", "DELETE"]:
                    event_type = AuditEventType.DATA_MODIFICATION
                else:
                    return  # Skip logging for other methods
            
            # Extract resource information from path
            resource_type, resource_id = self._extract_resource_info(path)
            
            # Prepare audit details
            details = {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "processing_time": processing_time,
                "content_type": response.headers.get("Content-Type"),
                "content_length": response.headers.get("Content-Length")
            }
            
            # Add request body size if available
            if hasattr(request, "body"):
                try:
                    body = await request.body()
                    if body:
                        details["request_size"] = len(body)
                except:
                    pass  # Ignore errors reading request body
            
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # Log the audit event
                self.audit_service.log_audit_event(
                    event_type=event_type,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    session_id=session_id,
                    db=db
                )
            finally:
                db.close()
                
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to log audit event: {str(e)}")
    
    async def _log_security_events(
        self,
        request: Request,
        response: Response,
        method: str,
        path: str,
        endpoint_key: str,
        user_id: Optional[str],
        client_ip: str,
        processing_time: float
    ):
        """Log security events for sensitive operations."""
        try:
            # Check if this is a security-sensitive endpoint
            if endpoint_key not in self.security_endpoints:
                return
            
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # Log different types of security events based on response status
                if response.status_code == 401:
                    # Unauthorized access attempt
                    self.audit_service.log_security_event(
                        event_type="unauthorized_access_attempt",
                        severity=SecurityEventSeverity.MEDIUM,
                        description=f"Unauthorized access attempt to {method} {path}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
                elif response.status_code == 403:
                    # Forbidden access (insufficient permissions)
                    self.audit_service.log_security_event(
                        event_type="insufficient_permissions",
                        severity=SecurityEventSeverity.MEDIUM,
                        description=f"Access denied due to insufficient permissions for {method} {path}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
                elif response.status_code >= 500:
                    # Server error on sensitive endpoint
                    self.audit_service.log_security_event(
                        event_type="system_error_on_sensitive_endpoint",
                        severity=SecurityEventSeverity.HIGH,
                        description=f"Server error on sensitive endpoint {method} {path}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
                elif response.status_code == 200 and endpoint_key == "POST /api/v1/auth/login":
                    # Successful login - log as low severity security event for monitoring
                    self.audit_service.log_security_event(
                        event_type="successful_authentication",
                        severity=SecurityEventSeverity.LOW,
                        description=f"Successful authentication from {client_ip}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
                elif response.status_code == 200 and "users" in path and method in ["POST", "DELETE"]:
                    # User management operations
                    severity = SecurityEventSeverity.MEDIUM if method == "DELETE" else SecurityEventSeverity.LOW
                    self.audit_service.log_security_event(
                        event_type="user_management_operation",
                        severity=severity,
                        description=f"User management operation: {method} {path}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
                elif response.status_code == 200 and "export" in path:
                    # Data export operations
                    self.audit_service.log_security_event(
                        event_type="data_export_operation",
                        severity=SecurityEventSeverity.MEDIUM,
                        description=f"Data export operation: {method} {path}",
                        user_id=user_id,
                        ip_address=client_ip,
                        details={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "processing_time": processing_time
                        },
                        db=db
                    )
                
            finally:
                db.close()
                
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to log security event: {str(e)}")
    
    def _extract_resource_info(self, path: str) -> tuple[Optional[str], Optional[str]]:
        """Extract resource type and ID from the request path."""
        path_parts = path.strip("/").split("/")
        
        # Skip API version prefix
        if len(path_parts) > 2 and path_parts[0] == "api" and path_parts[1].startswith("v"):
            path_parts = path_parts[2:]
        
        if not path_parts:
            return None, None
        
        resource_type = path_parts[0]
        resource_id = None
        
        # Try to extract resource ID (usually the second part or after specific keywords)
        if len(path_parts) > 1:
            # Check for UUID pattern in path parts
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            
            for part in path_parts[1:]:
                if re.match(uuid_pattern, part, re.IGNORECASE):
                    resource_id = part
                    break
        
        return resource_type, resource_id


class SecurityEventMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and log security events based on request patterns."""
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_service = get_audit_service()
        
        # Track request patterns for anomaly detection
        self.request_patterns = {}
        
        # Define suspicious patterns
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(\bor\b|\band\b)\s+\d+\s*=\s*\d+",
            r"(?i)'\s*(or|and)\s*'",
            
            # XSS patterns
            r"(?i)<script[^>]*>",
            r"(?i)javascript:",
            r"(?i)on\w+\s*=",
            
            # Path traversal patterns
            r"\.\./",
            r"\.\.\\",
            
            # Command injection patterns
            r"(?i)(;|\||\&)\s*(cat|ls|dir|type|echo|ping|wget|curl)",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and detect security events."""
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Check for suspicious patterns in request
        await self._check_suspicious_patterns(request, client_ip, user_agent)
        
        # Check for rate limiting violations
        await self._check_rate_limiting(request, client_ip)
        
        # Process the request
        response = await call_next(request)
        
        # Check response for security indicators
        await self._check_response_security(request, response, client_ip)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_suspicious_patterns(self, request: Request, client_ip: str, user_agent: str):
        """Check request for suspicious patterns."""
        try:
            import re
            
            # Check URL path
            path = str(request.url.path)
            query = str(request.url.query) if request.url.query else ""
            
            # Check for suspicious patterns
            for pattern in self.suspicious_patterns:
                if re.search(pattern, path) or re.search(pattern, query):
                    # Get database session
                    db_gen = get_db()
                    db = next(db_gen)
                    
                    try:
                        self.audit_service.log_security_event(
                            event_type="suspicious_request_pattern",
                            severity=SecurityEventSeverity.HIGH,
                            description=f"Suspicious pattern detected in request: {pattern}",
                            ip_address=client_ip,
                            details={
                                "pattern": pattern,
                                "path": path,
                                "query": query,
                                "user_agent": user_agent,
                                "method": request.method
                            },
                            db=db
                        )
                    finally:
                        db.close()
                    
                    break  # Only log once per request
                    
        except Exception as e:
            print(f"Failed to check suspicious patterns: {str(e)}")
    
    async def _check_rate_limiting(self, request: Request, client_ip: str):
        """Check for potential rate limiting violations."""
        try:
            current_time = time.time()
            
            # Track requests per IP
            if client_ip not in self.request_patterns:
                self.request_patterns[client_ip] = []
            
            # Clean old entries (older than 1 minute)
            self.request_patterns[client_ip] = [
                timestamp for timestamp in self.request_patterns[client_ip]
                if current_time - timestamp < 60
            ]
            
            # Add current request
            self.request_patterns[client_ip].append(current_time)
            
            # Check if rate limit is exceeded (more than 100 requests per minute)
            if len(self.request_patterns[client_ip]) > 100:
                # Get database session
                db_gen = get_db()
                db = next(db_gen)
                
                try:
                    self.audit_service.log_security_event(
                        event_type="rate_limit_violation",
                        severity=SecurityEventSeverity.MEDIUM,
                        description=f"Rate limit exceeded: {len(self.request_patterns[client_ip])} requests in 1 minute",
                        ip_address=client_ip,
                        details={
                            "requests_per_minute": len(self.request_patterns[client_ip]),
                            "path": str(request.url.path),
                            "method": request.method,
                            "user_agent": request.headers.get("User-Agent", "")
                        },
                        db=db
                    )
                finally:
                    db.close()
                    
        except Exception as e:
            print(f"Failed to check rate limiting: {str(e)}")
    
    async def _check_response_security(self, request: Request, response: Response, client_ip: str):
        """Check response for security indicators."""
        try:
            # Check for multiple failed authentication attempts
            if (response.status_code == 401 and 
                "auth" in str(request.url.path).lower()):
                
                # Get database session
                db_gen = get_db()
                db = next(db_gen)
                
                try:
                    self.audit_service.log_security_event(
                        event_type="authentication_failure",
                        severity=SecurityEventSeverity.MEDIUM,
                        description=f"Authentication failure from {client_ip}",
                        ip_address=client_ip,
                        details={
                            "path": str(request.url.path),
                            "method": request.method,
                            "status_code": response.status_code,
                            "user_agent": request.headers.get("User-Agent", "")
                        },
                        db=db
                    )
                finally:
                    db.close()
                    
        except Exception as e:
            print(f"Failed to check response security: {str(e)}")


def setup_audit_middleware(app):
    """Set up audit logging middleware."""
    # Add security event detection middleware first
    app.add_middleware(SecurityEventMiddleware)
    
    # Add audit logging middleware
    app.add_middleware(AuditLoggingMiddleware)