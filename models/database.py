"""
SQLAlchemy database models for the Wazuh AI Companion.

This module defines the database schema with proper relationships and constraints
for User, ChatSession, Message, LogEntry, and Analytics entities.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer, Float, 
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User role enumeration for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class MessageRole(str, Enum):
    """Message role enumeration for chat messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class LogLevel(str, Enum):
    """Log level enumeration for log entries."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    query_metrics = relationship("QueryMetrics", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index('idx_user_username_active', 'username', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
    )
    
    @validates('role')
    def validate_role(self, key, role):
        """Validate user role."""
        if role not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role: {role}")
        return role
    
    @validates('email')
    def validate_email(self, key, email):
        """Basic email validation."""
        if '@' not in email or '.' not in email:
            raise ValueError("Invalid email format")
        return email.lower()
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class ChatSession(Base):
    """Chat session model for managing user conversations."""
    
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)  # Optional session title
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class Message(Base):
    """Message model for storing chat conversation history."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store additional message metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        Index('idx_message_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_message_role', 'role'),
    )
    
    @validates('role')
    def validate_role(self, key, role):
        """Validate message role."""
        if role not in [r.value for r in MessageRole]:
            raise ValueError(f"Invalid message role: {role}")
        return role
    
    def __repr__(self):
        return f"<Message(id={self.id}, session_id={self.session_id}, role='{self.role}')>"


class LogEntry(Base):
    """Log entry model for storing and indexing Wazuh logs."""
    
    __tablename__ = "log_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(255), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    full_log = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # Structured log data
    embedding_id = Column(String(255), nullable=True, index=True)  # Vector embedding reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_log_timestamp_source', 'timestamp', 'source'),
        Index('idx_log_level_timestamp', 'level', 'timestamp'),
        Index('idx_log_embedding', 'embedding_id'),
    )
    
    @validates('level')
    def validate_level(self, key, level):
        """Validate log level."""
        if level not in [l.value for l in LogLevel]:
            raise ValueError(f"Invalid log level: {level}")
        return level
    
    def __repr__(self):
        return f"<LogEntry(id={self.id}, source='{self.source}', level='{self.level}')>"


class QueryMetrics(Base):
    """Query metrics model for analytics and monitoring."""
    
    __tablename__ = "query_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    response_time = Column(Float, nullable=False)  # Response time in seconds
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metrics
    tokens_used = Column(Integer, nullable=True)  # LLM tokens consumed
    logs_searched = Column(Integer, nullable=True)  # Number of logs searched
    
    # Relationships
    user = relationship("User", back_populates="query_metrics")
    
    # Constraints
    __table_args__ = (
        Index('idx_metrics_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_metrics_success_timestamp', 'success', 'timestamp'),
        Index('idx_metrics_response_time', 'response_time'),
    )
    
    def __repr__(self):
        return f"<QueryMetrics(id={self.id}, user_id={self.user_id}, success={self.success})>"


class SystemMetrics(Base):
    """System metrics model for monitoring application performance."""
    
    __tablename__ = "system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)  # e.g., 'seconds', 'bytes', 'count'
    tags = Column(JSON, nullable=True)  # Additional metric tags/labels
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_system_metrics_name_timestamp', 'metric_name', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<SystemMetrics(metric_name='{self.metric_name}', value={self.metric_value})>"


class AuditLog(Base):
    """Audit log model for tracking user actions and system events."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    details = Column(JSON, nullable=True)  # Additional event details
    ip_address = Column(String(45), nullable=True, index=True)  # IPv4/IPv6 address
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Constraints
    __table_args__ = (
        Index('idx_audit_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_resource_type_timestamp', 'resource_type', 'timestamp'),
        Index('idx_audit_ip_timestamp', 'ip_address', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', user_id={self.user_id})>"


class SecurityEvent(Base):
    """Security event model for tracking security-related incidents."""
    
    __tablename__ = "security_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    details = Column(JSON, nullable=True)  # Additional event details
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Resolution tracking
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    # Constraints
    __table_args__ = (
        Index('idx_security_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_security_severity_timestamp', 'severity', 'timestamp'),
        Index('idx_security_resolved_timestamp', 'resolved', 'timestamp'),
        Index('idx_security_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_security_ip_timestamp', 'ip_address', 'timestamp'),
    )
    
    @validates('severity')
    def validate_severity(self, key, severity):
        """Validate security event severity."""
        valid_severities = ['low', 'medium', 'high', 'critical']
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity: {severity}. Must be one of {valid_severities}")
        return severity
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, event_type='{self.event_type}', severity='{self.severity}')>"


class ComplianceReport(Base):
    """Compliance report model for storing generated compliance reports."""
    
    __tablename__ = "compliance_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_type = Column(String(50), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    report_data = Column(JSON, nullable=False)  # Full report data
    file_path = Column(String(500), nullable=True)  # Path to exported report file
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generator = relationship("User", foreign_keys=[generated_by])
    
    # Constraints
    __table_args__ = (
        Index('idx_compliance_type_period', 'report_type', 'period_start', 'period_end'),
        Index('idx_compliance_generated_by', 'generated_by'),
    )
    
    def __repr__(self):
        return f"<ComplianceReport(id={self.id}, type='{self.report_type}', period={self.period_start}-{self.period_end})>"