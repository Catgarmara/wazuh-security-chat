"""
Base exception classes and error handling framework.
"""
import os
from typing import Optional, Dict, Any, List
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
    
    # Embedded AI Specific Errors
    LLAMA_CPP_NOT_AVAILABLE = "AI_006"
    MODEL_LOADING_FAILED = "AI_007"
    MODEL_MEMORY_EXCEEDED = "AI_008"
    MODEL_INFERENCE_TIMEOUT = "AI_009"
    MODEL_CORRUPTION_DETECTED = "AI_010"
    RESOURCE_EXHAUSTION = "AI_011"
    GPU_ACCELERATION_FAILED = "AI_012"
    MODEL_QUANTIZATION_FAILED = "AI_013"
    BACKUP_MODEL_UNAVAILABLE = "AI_014"
    MODEL_SWAP_FAILED = "AI_015"
    
    # Resource Management Errors
    INSUFFICIENT_MEMORY = "RES_001"
    INSUFFICIENT_DISK_SPACE = "RES_002"
    CPU_OVERLOAD = "RES_003"
    GPU_UNAVAILABLE = "RES_004"
    RESOURCE_MONITORING_FAILED = "RES_005"
    AUTOMATIC_RECOVERY_FAILED = "RES_006"
    
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


class EmbeddedAIError(WazuhChatException):
    """Embedded AI service specific errors with recovery suggestions."""
    
    def __init__(
        self,
        message: str = "Embedded AI error",
        error_code: ErrorCode = ErrorCode.AI_PROCESSING_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        super().__init__(message, error_code, details, cause)
        self.recovery_suggestions = recovery_suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary with recovery suggestions."""
        result = super().to_dict()
        if self.recovery_suggestions:
            result["recovery_suggestions"] = self.recovery_suggestions
        return result


class ModelLoadingError(EmbeddedAIError):
    """Model loading specific errors with detailed diagnostics."""
    
    def __init__(
        self,
        message: str = "Model loading failed",
        error_code: ErrorCode = ErrorCode.MODEL_LOADING_FAILED,
        model_id: Optional[str] = None,
        model_path: Optional[str] = None,
        memory_required: Optional[int] = None,
        memory_available: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        # Build detailed error message
        if model_id:
            message = f"Failed to load model '{model_id}': {message}"
        
        # Add model-specific details
        model_details = details or {}
        if model_path:
            model_details["model_path"] = model_path
        if memory_required:
            model_details["memory_required_mb"] = memory_required
        if memory_available:
            model_details["memory_available_mb"] = memory_available
        
        # Generate recovery suggestions if not provided
        if not recovery_suggestions:
            recovery_suggestions = self._generate_recovery_suggestions(
                memory_required, memory_available, model_path
            )
        
        super().__init__(message, error_code, model_details, cause, recovery_suggestions)
        self.model_id = model_id
        self.model_path = model_path
    
    def _generate_recovery_suggestions(
        self, 
        memory_required: Optional[int], 
        memory_available: Optional[int],
        model_path: Optional[str]
    ) -> List[str]:
        """Generate context-aware recovery suggestions."""
        suggestions = []
        
        if memory_required and memory_available and memory_required > memory_available:
            suggestions.extend([
                "Free up system memory by closing other applications",
                "Reduce max_concurrent_models in configuration",
                "Use a smaller quantized model variant (Q4_K_M instead of Q8_0)",
                "Enable model auto-unloading for inactive models"
            ])
        
        if model_path and not os.path.exists(model_path):
            suggestions.extend([
                "Verify the model file exists at the specified path",
                "Re-download the model if it was corrupted",
                "Check file permissions for the models directory"
            ])
        
        suggestions.extend([
            "Try loading a backup model if available",
            "Check system logs for detailed error information",
            "Restart the embedded AI service if the issue persists"
        ])
        
        return suggestions


class ResourceExhaustionError(WazuhChatException):
    """Resource exhaustion errors with automatic recovery options."""
    
    def __init__(
        self,
        message: str = "System resources exhausted",
        error_code: ErrorCode = ErrorCode.RESOURCE_EXHAUSTION,
        resource_type: str = "memory",
        current_usage: Optional[float] = None,
        threshold: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        auto_recovery_attempted: bool = False
    ):
        # Build detailed error message
        if current_usage and threshold:
            message = f"{message}: {resource_type} usage {current_usage:.1f}% exceeds threshold {threshold:.1f}%"
        
        # Add resource-specific details
        resource_details = details or {}
        resource_details.update({
            "resource_type": resource_type,
            "current_usage_percent": current_usage,
            "threshold_percent": threshold,
            "auto_recovery_attempted": auto_recovery_attempted
        })
        
        super().__init__(message, error_code, resource_details, cause)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold
        self.auto_recovery_attempted = auto_recovery_attempted


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAP = {
    AuthenticationError: 401,
    ValidationError: 400,
    ServiceUnavailableError: 503,
    AIProcessingError: 500,
    EmbeddedAIError: 500,
    ModelLoadingError: 503,
    ResourceExhaustionError: 503,
    LogProcessingError: 500,
    DatabaseError: 500,
    WebSocketError: 500,
    ConfigurationError: 500,
    WazuhChatException: 500
}