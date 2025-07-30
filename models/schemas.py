"""
Pydantic schemas for API request/response validation.

This module defines the data validation schemas used for API endpoints,
ensuring proper data serialization and validation for all database models.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum

from .database import UserRole, MessageRole, LogLevel


# Base schemas with common fields
class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None


# User schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(UserBase, TimestampMixin):
    """Schema for user API responses."""
    id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Schema for user profile information."""
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Authentication schemas
class LoginRequest(BaseModel):
    """Schema for login requests."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for authentication token responses."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh requests."""
    refresh_token: str


# Chat session schemas
class ChatSessionBase(BaseModel):
    """Base chat session schema."""
    title: Optional[str] = Field(None, max_length=255)


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a new chat session."""
    pass


class ChatSessionUpdate(BaseModel):
    """Schema for updating chat session."""
    title: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class ChatSessionResponse(ChatSessionBase, TimestampMixin):
    """Schema for chat session API responses."""
    id: UUID
    user_id: UUID
    is_active: bool
    ended_at: Optional[datetime] = None
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


# Message schemas
class MessageBase(BaseModel):
    """Base message schema."""
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=10000)
    message_metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    session_id: UUID


class MessageResponse(MessageBase):
    """Schema for message API responses."""
    id: UUID
    session_id: UUID
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    """Schema for chat message requests via WebSocket."""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[UUID] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message responses via WebSocket."""
    id: UUID
    role: MessageRole
    content: str
    timestamp: datetime
    session_id: UUID
    message_metadata: Optional[Dict[str, Any]] = None


# Log entry schemas
class LogEntryBase(BaseModel):
    """Base log entry schema."""
    timestamp: datetime
    source: str = Field(..., max_length=255)
    level: LogLevel
    full_log: str
    parsed_data: Optional[Dict[str, Any]] = None
    embedding_id: Optional[str] = Field(None, max_length=255)


class LogEntryCreate(LogEntryBase):
    """Schema for creating a new log entry."""
    pass


class LogEntryResponse(LogEntryBase):
    """Schema for log entry API responses."""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class LogEntrySearch(BaseModel):
    """Schema for log entry search requests."""
    query: Optional[str] = None
    source: Optional[str] = None
    level: Optional[LogLevel] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class LogStats(BaseModel):
    """Schema for log statistics."""
    total_logs: int
    date_range: Dict[str, datetime]
    sources: Dict[str, int]
    levels: Dict[str, int]
    processing_time: float


# Analytics schemas
class QueryMetricsBase(BaseModel):
    """Base query metrics schema."""
    query: str
    response_time: float = Field(..., ge=0)
    success: bool = True
    error_message: Optional[str] = None
    tokens_used: Optional[int] = Field(None, ge=0)
    logs_searched: Optional[int] = Field(None, ge=0)


class QueryMetricsCreate(QueryMetricsBase):
    """Schema for creating query metrics."""
    user_id: UUID


class QueryMetricsResponse(QueryMetricsBase):
    """Schema for query metrics API responses."""
    id: UUID
    user_id: UUID
    timestamp: datetime
    
    class Config:
        from_attributes = True


class UsageMetrics(BaseModel):
    """Schema for usage metrics aggregation."""
    total_queries: int
    unique_users: int
    avg_response_time: float
    error_rate: float
    peak_usage_time: Optional[datetime] = None
    date_range: Dict[str, datetime]


class SystemMetricsBase(BaseModel):
    """Base system metrics schema."""
    metric_name: str = Field(..., max_length=100)
    metric_value: float
    metric_unit: Optional[str] = Field(None, max_length=50)
    tags: Optional[Dict[str, Any]] = None


class SystemMetricsCreate(SystemMetricsBase):
    """Schema for creating system metrics."""
    pass


class SystemMetricsResponse(SystemMetricsBase):
    """Schema for system metrics API responses."""
    id: UUID
    timestamp: datetime
    
    class Config:
        from_attributes = True


class DashboardData(BaseModel):
    """Schema for dashboard data aggregation."""
    usage_metrics: UsageMetrics
    recent_queries: List[QueryMetricsResponse]
    system_health: Dict[str, Any]
    log_statistics: LogStats


# Pagination schemas
class PaginatedResponse(BaseModel):
    """Generic paginated response schema."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


# Error response schemas
class ErrorDetail(BaseModel):
    """Schema for error details."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Schema for API error responses."""
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    request_id: Optional[str] = None


# Health check schemas
class HealthCheck(BaseModel):
    """Schema for health check responses."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]  # service_name -> status


# Date range schema
class DateRange(BaseModel):
    """Schema for date range queries."""
    start_date: datetime
    end_date: datetime
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate that end_date is after start_date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v