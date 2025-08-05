"""
Input Sanitization and Validation Middleware

This module provides comprehensive input sanitization and validation
for all API endpoints to prevent injection attacks and malformed requests.
"""

import re
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.exceptions import ValidationError, ErrorCode

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Input sanitization utilities."""
    
    # Dangerous patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>"
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]\\]",
        r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ping|wget|curl|nc|telnet|ssh|ftp)\b",
        r"(\.\.\/|\.\.\\)",
        r"(/etc/passwd|/etc/shadow|/proc/|/sys/)",
        r"(\$\{|\$\()"
    ]
    
    LDAP_INJECTION_PATTERNS = [
        r"[()&|!*]",
        r"\\[0-9a-fA-F]{2}",
        r"\x00"
    ]
    
    def __init__(self):
        self.sql_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS]
        self.xss_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.XSS_PATTERNS]
        self.cmd_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.COMMAND_INJECTION_PATTERNS]
        self.ldap_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.LDAP_INJECTION_PATTERNS]
    
    def sanitize_string(self, value: str, strict: bool = False) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: String to sanitize
            strict: Whether to apply strict sanitization
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # HTML encode dangerous characters
        sanitized = html.escape(value)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove control characters except common whitespace
        sanitized = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        if strict:
            # Remove all HTML tags
            sanitized = re.sub(r'<[^>]*>', '', sanitized)
            
            # Remove JavaScript protocols
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
            
            # Limit length
            if len(sanitized) > 10000:
                sanitized = sanitized[:10000]
        
        return sanitized
    
    def detect_sql_injection(self, value: str) -> bool:
        """Detect potential SQL injection attempts."""
        if not isinstance(value, str):
            return False
        
        for regex in self.sql_regex:
            if regex.search(value):
                return True
        return False
    
    def detect_xss(self, value: str) -> bool:
        """Detect potential XSS attempts."""
        if not isinstance(value, str):
            return False
        
        for regex in self.xss_regex:
            if regex.search(value):
                return True
        return False
    
    def detect_command_injection(self, value: str) -> bool:
        """Detect potential command injection attempts."""
        if not isinstance(value, str):
            return False
        
        for regex in self.cmd_regex:
            if regex.search(value):
                return True
        return False
    
    def detect_ldap_injection(self, value: str) -> bool:
        """Detect potential LDAP injection attempts."""
        if not isinstance(value, str):
            return False
        
        for regex in self.ldap_regex:
            if regex.search(value):
                return True
        return False
    
    def validate_and_sanitize(self, value: Any, field_name: str = "unknown", 
                            strict: bool = False) -> Any:
        """
        Validate and sanitize input value.
        
        Args:
            value: Value to validate and sanitize
            field_name: Name of the field for error reporting
            strict: Whether to apply strict sanitization
            
        Returns:
            Sanitized value
            
        Raises:
            ValidationError: If dangerous patterns are detected
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            # Check for dangerous patterns
            if self.detect_sql_injection(value):
                raise ValidationError(
                    f"Potential SQL injection detected in field '{field_name}'",
                    ErrorCode.INVALID_INPUT,
                    details={"field": field_name, "attack_type": "sql_injection"}
                )
            
            if self.detect_xss(value):
                raise ValidationError(
                    f"Potential XSS attack detected in field '{field_name}'",
                    ErrorCode.INVALID_INPUT,
                    details={"field": field_name, "attack_type": "xss"}
                )
            
            if self.detect_command_injection(value):
                raise ValidationError(
                    f"Potential command injection detected in field '{field_name}'",
                    ErrorCode.INVALID_INPUT,
                    details={"field": field_name, "attack_type": "command_injection"}
                )
            
            if self.detect_ldap_injection(value):
                raise ValidationError(
                    f"Potential LDAP injection detected in field '{field_name}'",
                    ErrorCode.INVALID_INPUT,
                    details={"field": field_name, "attack_type": "ldap_injection"}
                )
            
            return self.sanitize_string(value, strict)
        
        elif isinstance(value, dict):
            return {k: self.validate_and_sanitize(v, f"{field_name}.{k}", strict) 
                   for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self.validate_and_sanitize(item, f"{field_name}[{i}]", strict) 
                   for i, item in enumerate(value)]
        
        else:
            return value


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for input sanitization and validation."""
    
    def __init__(self, app: ASGIApp, strict_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.sanitizer = InputSanitizer()
        self.strict_paths = strict_paths or ["/api/v1/auth/", "/api/v1/admin/"]
        
        # Paths to skip sanitization (e.g., file uploads, raw data endpoints)
        self.skip_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply input sanitization to requests."""
        try:
            # Skip sanitization for certain paths
            if any(request.url.path.startswith(skip_path) for skip_path in self.skip_paths):
                return await call_next(request)
            
            # Determine if strict sanitization should be applied
            strict = any(request.url.path.startswith(strict_path) for strict_path in self.strict_paths)
            
            # Sanitize query parameters
            if request.query_params:
                sanitized_params = {}
                for key, value in request.query_params.items():
                    try:
                        sanitized_params[key] = self.sanitizer.validate_and_sanitize(
                            value, f"query.{key}", strict
                        )
                    except ValidationError as e:
                        logger.warning(f"Input validation failed for query param '{key}': {e}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error_code": e.error_code.value,
                                "message": str(e),
                                "details": e.details,
                                "timestamp": e.timestamp.isoformat()
                            }
                        )
            
            # Sanitize request body for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Read the request body
                    body = await request.body()
                    if body:
                        # Try to parse as JSON
                        try:
                            json_data = json.loads(body.decode('utf-8'))
                            sanitized_data = self.sanitizer.validate_and_sanitize(
                                json_data, "body", strict
                            )
                            
                            # Replace the request body with sanitized data
                            sanitized_body = json.dumps(sanitized_data).encode('utf-8')
                            
                            # Create a new request with sanitized body
                            async def receive():
                                return {
                                    "type": "http.request",
                                    "body": sanitized_body,
                                    "more_body": False
                                }
                            
                            request._receive = receive
                            
                        except json.JSONDecodeError:
                            # Not JSON data, apply basic string sanitization
                            body_str = body.decode('utf-8', errors='ignore')
                            sanitized_body_str = self.sanitizer.validate_and_sanitize(
                                body_str, "body", strict
                            )
                            
                            async def receive():
                                return {
                                    "type": "http.request", 
                                    "body": sanitized_body_str.encode('utf-8'),
                                    "more_body": False
                                }
                            
                            request._receive = receive
                            
                except ValidationError as e:
                    logger.warning(f"Input validation failed for request body: {e}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error_code": e.error_code.value,
                            "message": str(e),
                            "details": e.details,
                            "timestamp": e.timestamp.isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error during input sanitization: {e}")
                    # Continue with original request if sanitization fails
            
            # Process the request
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Input sanitization middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_code": "SANITIZATION_ERROR",
                    "message": "Input sanitization failed",
                    "timestamp": str(e)
                }
            )


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """Validate username format."""
    # Allow alphanumeric, underscore, hyphen, 3-50 characters
    pattern = r'^[a-zA-Z0-9_-]{3,50}$'
    return re.match(pattern, username) is not None


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Returns:
        Dictionary with validation results
    """
    result = {
        "valid": True,
        "score": 0,
        "issues": []
    }
    
    if len(password) < 8:
        result["valid"] = False
        result["issues"].append("Password must be at least 8 characters long")
    else:
        result["score"] += 1
    
    if not re.search(r'[a-z]', password):
        result["valid"] = False
        result["issues"].append("Password must contain at least one lowercase letter")
    else:
        result["score"] += 1
    
    if not re.search(r'[A-Z]', password):
        result["valid"] = False
        result["issues"].append("Password must contain at least one uppercase letter")
    else:
        result["score"] += 1
    
    if not re.search(r'\d', password):
        result["valid"] = False
        result["issues"].append("Password must contain at least one digit")
    else:
        result["score"] += 1
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        result["issues"].append("Password should contain at least one special character")
    else:
        result["score"] += 1
    
    # Check for common weak passwords
    weak_passwords = [
        "password", "123456", "password123", "admin", "qwerty",
        "letmein", "welcome", "monkey", "dragon", "master"
    ]
    
    if password.lower() in weak_passwords:
        result["valid"] = False
        result["issues"].append("Password is too common")
    
    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    # Remove directory traversal attempts
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate JSON data against required fields.
    
    Args:
        data: JSON data to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If validation fails
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            ErrorCode.MISSING_REQUIRED_FIELD,
            details={"missing_fields": missing_fields}
        )