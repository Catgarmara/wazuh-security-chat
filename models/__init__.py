"""
Models package for the Wazuh AI Companion.

This package contains SQLAlchemy database models and Pydantic schemas
for data validation and serialization.
"""

from .database import (
    Base,
    User,
    ChatSession,
    Message,
    LogEntry,
    QueryMetrics,
    SystemMetrics,
    UserRole,
    MessageRole,
    LogLevel,
)

from .schemas import (
    # User schemas
    UserBase,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserResponse,
    UserProfile,
    
    # Authentication schemas
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    
    # Chat session schemas
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    
    # Message schemas
    MessageBase,
    MessageCreate,
    MessageResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    
    # Log entry schemas
    LogEntryBase,
    LogEntryCreate,
    LogEntryResponse,
    LogEntrySearch,
    LogStats,
    
    # Analytics schemas
    QueryMetricsBase,
    QueryMetricsCreate,
    QueryMetricsResponse,
    UsageMetrics,
    SystemMetricsBase,
    SystemMetricsCreate,
    SystemMetricsResponse,
    DashboardData,
    
    # Utility schemas
    PaginatedResponse,
    PaginationParams,
    ErrorDetail,
    ErrorResponse,
    HealthCheck,
    DateRange,
    TimestampMixin,
)

__all__ = [
    # Database models
    "Base",
    "User",
    "ChatSession", 
    "Message",
    "LogEntry",
    "QueryMetrics",
    "SystemMetrics",
    "UserRole",
    "MessageRole",
    "LogLevel",
    
    # Pydantic schemas
    "UserBase",
    "UserCreate",
    "UserUpdate", 
    "UserPasswordUpdate",
    "UserResponse",
    "UserProfile",
    "LoginRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "ChatSessionBase",
    "ChatSessionCreate",
    "ChatSessionUpdate",
    "ChatSessionResponse",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "LogEntryBase",
    "LogEntryCreate",
    "LogEntryResponse",
    "LogEntrySearch",
    "LogStats",
    "QueryMetricsBase",
    "QueryMetricsCreate",
    "QueryMetricsResponse",
    "UsageMetrics",
    "SystemMetricsBase",
    "SystemMetricsCreate",
    "SystemMetricsResponse",
    "DashboardData",
    "PaginatedResponse",
    "PaginationParams",
    "ErrorDetail",
    "ErrorResponse",
    "HealthCheck",
    "DateRange",
    "TimestampMixin",
]