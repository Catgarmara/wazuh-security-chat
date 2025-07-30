"""
Base exception classes and error handling framework.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class ErrorCode(str, Enum):
    """Standard error codes."""
    
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "AUTH_001"
    INVALID_TOKEN = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"
    USER_NOT_FOUND = "AUTH_005"
    USER_ALREADY_EXISTS = "AUTH_006"
    
    # Validation
    VALIDATION_ERROR = "VAL_001"
    INVALID_INPUT = "VAL_002"
    MISSING_REQUIRED_FIELD = "VAL_003"
    INVALID_FORMAT = "VAL_004"
    
    # Service Errors
    SERVICE_UNAVAILABLE = "SVC_001"
    EXTERNAL_SERVICE_ERROR = "SVC_002"
    TIMEOUT_ERROR = "SVC_003"
    RATE_LIMIT_EXCEEDED = "SVC_004"
    
    # AI/ML Errors
    AI_PROCESSING_ERROR = "AI_001"
    MODEL_NOT_AVAILABLE = "AI_002"
    EMBEDDING_GENERATION_FAILED = "AI_003"
    VECTOR_STORE_ERROR = "AI_004"
    LLM_RESPONSE_ERROR = "AI_005"
    
    # Log Processing
    LOG_FILE_NOT_FOUND = "LOG_001"
    LOG_PARSING_ERROR = "LOG_002"
    LOG_ACCESS_DENIED = "LOG_003"
    REMOTE_CONNECTION_FAILED = "LOG_004"
    
    # Database
    DATABASE_CONNECTION_ERROR = "DB_001"
    DATABASE_QUERY_ERROR = "DB_002"
    RECORD_NOT_FOUND = "DB_003"
    DUPLICATE_RECORD = "DB_004"
    
    # WebSocket
    WEBSOCKET_CONNECTION_ERROR = "WS_001"
    WEBSOCKET_MESSAGE_ERROR = "WS_002"
    
    # General
    INTERNAL_SERVER_ERROR = "GEN_001"
    NOT_IMPLEMENTED = "GEN_002"
    CONFIGURATION_ERROR = "GEN_003"


class WazuhChatException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
        self.request_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class AuthenticationError(WazuhChatException):
    """Authentication and authorization errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class ValidationError(WazuhChatException):
    """Input validation errors."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class ServiceUnavailableError(WazuhChatException):
    """Service dependency errors."""
    
    def __init__(
        self,
        message: str = "Service unavailable",
        error_code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class AIProcessingError(WazuhChatException):
    """AI/ML processing errors."""
    
    def __init__(
        self,
        message: str = "AI processing failed",
        error_code: ErrorCode = ErrorCode.AI_PROCESSING_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class LogProcessingError(WazuhChatException):
    """Log processing errors."""
    
    def __init__(
        self,
        message: str = "Log processing failed",
        error_code: ErrorCode = ErrorCode.LOG_PARSING_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class DatabaseError(WazuhChatException):
    """Database operation errors."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: ErrorCode = ErrorCode.DATABASE_QUERY_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class WebSocketError(WazuhChatException):
    """WebSocket communication errors."""
    
    def __init__(
        self,
        message: str = "WebSocket error",
        error_code: ErrorCode = ErrorCode.WEBSOCKET_CONNECTION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class ConfigurationError(WazuhChatException):
    """Configuration errors."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        error_code: ErrorCode = ErrorCode.CONFIGURATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAP = {
    AuthenticationError: 401,
    ValidationError: 400,
    ServiceUnavailableError: 503,
    AIProcessingError: 500,
    LogProcessingError: 500,
    DatabaseError: 500,
    WebSocketError: 500,
    ConfigurationError: 500,
    WazuhChatException: 500
}