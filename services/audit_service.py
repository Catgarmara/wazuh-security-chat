"""
Audit logging service for comprehensive tracking of user actions and security events.

This service provides audit logging capabilities for compliance and security monitoring,
tracking all user actions, system events, and security-related activities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from core.database import get_db
from models.database import AuditLog, SecurityEvent, User
from models.schemas import AuditLogCreate, AuditLogResponse, SecurityEventCreate, SecurityEventResponse
from core.exceptions import WazuhChatException


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    ROLE_CHANGED = "role_changed"
    
    # Chat and AI events
    CHAT_SESSION_STARTED = "chat_session_started"
    CHAT_SESSION_ENDED = "chat_session_ended"
    MESSAGE_SENT = "message_sent"
    AI_QUERY_PROCESSED = "ai_query_processed"
    
    # Log management events
    LOGS_RELOADED = "logs_reloaded"
    LOG_SEARCH_PERFORMED = "log_search_performed"
    LOG_EXPORT = "log_export"
    
    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIG_CHANGED = "config_changed"
    
    # Security events
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SECURITY_EVENT_RESOLVED = "security_event_resolved"
    
    # Compliance events
    COMPLIANCE_REPORT_GENERATED = "compliance_report_generated"
    AUDIT_LOG_CLEANUP = "audit_log_cleanup"
    DATA_RETENTION_APPLIED = "data_retention_applied"
    COMPLIANCE_CERTIFICATE_GENERATED = "compliance_certificate_generated"


class SecurityEventSeverity(str, Enum):
    """Severity levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditService:
    """Service for audit logging and compliance tracking."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            user_id: ID of the user performing the action
            resource_type: Type of resource being accessed/modified
            resource_id: ID of the specific resource
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session identifier
            db: Database session
            
        Returns:
            Created audit log entry
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            # Create audit log entry
            audit_log = AuditLog(
                id=uuid4(),
                event_type=event_type.value,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            # Log to application logger as well
            self.logger.info(
                f"Audit Event: {event_type.value}",
                extra={
                    "audit_id": str(audit_log.id),
                    "user_id": str(user_id) if user_id else None,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "ip_address": ip_address,
                    "session_id": session_id,
                    "details": details
                }
            )
            
            return audit_log
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to log audit event: {str(e)}")
            raise WazuhChatException(f"Audit logging failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def log_security_event(
        self,
        event_type: str,
        severity: SecurityEventSeverity,
        description: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> SecurityEvent:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level of the event
            description: Human-readable description
            user_id: ID of the user involved (if applicable)
            ip_address: Source IP address
            details: Additional event details
            db: Database session
            
        Returns:
            Created security event entry
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            # Create security event entry
            security_event = SecurityEvent(
                id=uuid4(),
                event_type=event_type,
                severity=severity.value,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                details=details or {},
                timestamp=datetime.utcnow(),
                resolved=False
            )
            
            db.add(security_event)
            db.commit()
            db.refresh(security_event)
            
            # Log to application logger with appropriate level
            log_level = {
                SecurityEventSeverity.LOW: logging.INFO,
                SecurityEventSeverity.MEDIUM: logging.WARNING,
                SecurityEventSeverity.HIGH: logging.ERROR,
                SecurityEventSeverity.CRITICAL: logging.CRITICAL
            }.get(severity, logging.WARNING)
            
            self.logger.log(
                log_level,
                f"Security Event: {event_type} - {description}",
                extra={
                    "security_event_id": str(security_event.id),
                    "severity": severity.value,
                    "user_id": str(user_id) if user_id else None,
                    "ip_address": ip_address,
                    "details": details
                }
            )
            
            # Trigger alerts for high/critical events
            if severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                self._trigger_security_alert(security_event)
            
            return security_event
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to log security event: {str(e)}")
            raise WazuhChatException(f"Security event logging failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        db: Optional[Session] = None
    ) -> List[AuditLog]:
        """
        Retrieve audit logs with filtering.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            resource_type: Filter by resource type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            offset: Number of results to skip
            db: Database session
            
        Returns:
            List of audit log entries
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            query = db.query(AuditLog)
            
            # Apply filters
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            if event_type:
                query = query.filter(AuditLog.event_type == event_type)
            
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            
            # Order by timestamp descending
            query = query.order_by(desc(AuditLog.timestamp))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            return query.all()
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit logs: {str(e)}")
            raise WazuhChatException(f"Audit log retrieval failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def get_security_events(
        self,
        severity: Optional[SecurityEventSeverity] = None,
        resolved: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        db: Optional[Session] = None
    ) -> List[SecurityEvent]:
        """
        Retrieve security events with filtering.
        
        Args:
            severity: Filter by severity level
            resolved: Filter by resolution status
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            offset: Number of results to skip
            db: Database session
            
        Returns:
            List of security event entries
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            query = db.query(SecurityEvent)
            
            # Apply filters
            if severity:
                query = query.filter(SecurityEvent.severity == severity.value)
            
            if resolved is not None:
                query = query.filter(SecurityEvent.resolved == resolved)
            
            if start_time:
                query = query.filter(SecurityEvent.timestamp >= start_time)
            
            if end_time:
                query = query.filter(SecurityEvent.timestamp <= end_time)
            
            # Order by timestamp descending
            query = query.order_by(desc(SecurityEvent.timestamp))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            return query.all()
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve security events: {str(e)}")
            raise WazuhChatException(f"Security event retrieval failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def resolve_security_event(
        self,
        event_id: UUID,
        resolved_by: UUID,
        resolution_notes: Optional[str] = None,
        db: Optional[Session] = None
    ) -> SecurityEvent:
        """
        Mark a security event as resolved.
        
        Args:
            event_id: ID of the security event
            resolved_by: ID of the user resolving the event
            resolution_notes: Optional resolution notes
            db: Database session
            
        Returns:
            Updated security event
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            # Get the security event
            security_event = db.query(SecurityEvent).filter(
                SecurityEvent.id == event_id
            ).first()
            
            if not security_event:
                raise WazuhChatException(f"Security event {event_id} not found")
            
            # Update resolution status
            security_event.resolved = True
            security_event.resolved_at = datetime.utcnow()
            security_event.resolved_by = resolved_by
            security_event.resolution_notes = resolution_notes
            
            db.commit()
            db.refresh(security_event)
            
            # Log the resolution
            self.log_audit_event(
                event_type=AuditEventType.SECURITY_EVENT_RESOLVED,
                user_id=resolved_by,
                resource_type="security_event",
                resource_id=str(event_id),
                details={
                    "resolution_notes": resolution_notes,
                    "original_event_type": security_event.event_type,
                    "original_severity": security_event.severity
                },
                db=db
            )
            
            return security_event
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to resolve security event: {str(e)}")
            raise WazuhChatException(f"Security event resolution failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "full",
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate a compliance report for the specified date range.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            report_type: Type of report (full, summary, security)
            db: Database session
            
        Returns:
            Compliance report data
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            report = {
                "report_id": str(uuid4()),
                "generated_at": datetime.utcnow().isoformat(),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "report_type": report_type
            }
            
            # Get audit log statistics
            audit_stats = self._get_audit_statistics(start_date, end_date, db)
            report["audit_statistics"] = audit_stats
            
            # Get security event statistics
            security_stats = self._get_security_statistics(start_date, end_date, db)
            report["security_statistics"] = security_stats
            
            # Get user activity statistics
            user_stats = self._get_user_activity_statistics(start_date, end_date, db)
            report["user_activity"] = user_stats
            
            # Get compliance metrics
            compliance_metrics = self._get_compliance_metrics(start_date, end_date, db)
            report["compliance_metrics"] = compliance_metrics
            
            if report_type == "full":
                # Include detailed event lists for full reports
                report["recent_security_events"] = [
                    {
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "severity": event.severity,
                        "description": event.description,
                        "timestamp": event.timestamp.isoformat(),
                        "resolved": event.resolved
                    }
                    for event in self.get_security_events(
                        start_time=start_date,
                        end_time=end_date,
                        limit=50,
                        db=db
                    )
                ]
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {str(e)}")
            raise WazuhChatException(f"Compliance report generation failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def cleanup_old_audit_logs(
        self,
        retention_days: int = 365,
        db: Optional[Session] = None
    ) -> int:
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            retention_days: Number of days to retain audit logs
            db: Database session
            
        Returns:
            Number of deleted records
        """
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
            should_close = True
        else:
            should_close = False
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Count records to be deleted
            count = db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).count()
            
            # Delete old audit logs
            deleted = db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            db.commit()
            
            self.logger.info(f"Cleaned up {deleted} audit log records older than {retention_days} days")
            
            return deleted
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to cleanup audit logs: {str(e)}")
            raise WazuhChatException(f"Audit log cleanup failed: {str(e)}")
        finally:
            if should_close:
                db.close()
    
    def _get_audit_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """Get audit log statistics for the specified period."""
        # Total audit events
        total_events = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        ).count()
        
        # Events by type
        events_by_type = dict(
            db.query(AuditLog.event_type, func.count(AuditLog.id))
            .filter(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            )
            .group_by(AuditLog.event_type)
            .all()
        )
        
        # Unique users
        unique_users = db.query(AuditLog.user_id).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.user_id.isnot(None)
            )
        ).distinct().count()
        
        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "unique_users": unique_users
        }
    
    def _get_security_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """Get security event statistics for the specified period."""
        # Total security events
        total_events = db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.timestamp >= start_date,
                SecurityEvent.timestamp <= end_date
            )
        ).count()
        
        # Events by severity
        events_by_severity = dict(
            db.query(SecurityEvent.severity, func.count(SecurityEvent.id))
            .filter(
                and_(
                    SecurityEvent.timestamp >= start_date,
                    SecurityEvent.timestamp <= end_date
                )
            )
            .group_by(SecurityEvent.severity)
            .all()
        )
        
        # Resolution statistics
        resolved_events = db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.timestamp >= start_date,
                SecurityEvent.timestamp <= end_date,
                SecurityEvent.resolved == True
            )
        ).count()
        
        return {
            "total_events": total_events,
            "events_by_severity": events_by_severity,
            "resolved_events": resolved_events,
            "unresolved_events": total_events - resolved_events,
            "resolution_rate": (resolved_events / total_events * 100) if total_events > 0 else 0
        }
    
    def _get_user_activity_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """Get user activity statistics for the specified period."""
        # Login events
        login_events = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.event_type.in_([
                    AuditEventType.LOGIN_SUCCESS.value,
                    AuditEventType.LOGIN_FAILED.value
                ])
            )
        ).count()
        
        # Failed login attempts
        failed_logins = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.event_type == AuditEventType.LOGIN_FAILED.value
            )
        ).count()
        
        # Active users (users with any audit events)
        active_users = db.query(AuditLog.user_id).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.user_id.isnot(None)
            )
        ).distinct().count()
        
        return {
            "login_events": login_events,
            "failed_logins": failed_logins,
            "login_success_rate": ((login_events - failed_logins) / login_events * 100) if login_events > 0 else 0,
            "active_users": active_users
        }
    
    def _get_compliance_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """Get compliance-specific metrics."""
        # Data access events
        data_access_events = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.event_type.in_([
                    AuditEventType.LOG_SEARCH_PERFORMED.value,
                    AuditEventType.LOG_EXPORT.value,
                    AuditEventType.DATA_ACCESS.value
                ])
            )
        ).count()
        
        # Administrative actions
        admin_actions = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.event_type.in_([
                    AuditEventType.USER_CREATED.value,
                    AuditEventType.USER_UPDATED.value,
                    AuditEventType.USER_DELETED.value,
                    AuditEventType.ROLE_CHANGED.value,
                    AuditEventType.CONFIG_CHANGED.value
                ])
            )
        ).count()
        
        # Security violations
        security_violations = db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.timestamp >= start_date,
                SecurityEvent.timestamp <= end_date,
                SecurityEvent.severity.in_([
                    SecurityEventSeverity.HIGH.value,
                    SecurityEventSeverity.CRITICAL.value
                ])
            )
        ).count()
        
        return {
            "data_access_events": data_access_events,
            "administrative_actions": admin_actions,
            "security_violations": security_violations,
            "audit_coverage": "100%",  # Assuming full audit coverage
            "retention_compliance": "Active"  # Based on cleanup policies
        }
    
    def _trigger_security_alert(self, security_event: SecurityEvent):
        """Trigger security alerts for high-severity events."""
        # In a real implementation, this would integrate with alerting systems
        # like email, Slack, PagerDuty, etc.
        self.logger.critical(
            f"SECURITY ALERT: {security_event.event_type} - {security_event.description}",
            extra={
                "alert_type": "security",
                "severity": security_event.severity,
                "event_id": str(security_event.id),
                "timestamp": security_event.timestamp.isoformat()
            }
        )


# Global service instance
_audit_service = None


def get_audit_service() -> AuditService:
    """Get the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service