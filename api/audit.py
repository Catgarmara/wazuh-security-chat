"""
Audit logging and compliance API endpoints.

This module provides REST API endpoints for audit logging, security event management,
and compliance reporting functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import require_permission
from models.database import User
from models.schemas import (
    AuditLogResponse, AuditLogSearch, SecurityEventResponse, SecurityEventSearch,
    SecurityEventResolve, ComplianceReportResponse, ComplianceReportCreate,
    ComplianceReportSearch, ComplianceReportData, AuditStatistics,
    SecurityStatistics, UserActivityStatistics, ComplianceMetrics,
    PaginatedResponse, ErrorResponse
)
from services.audit_service import get_audit_service, AuditEventType, SecurityEventSeverity
from services.auth_service import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])
audit_service = get_audit_service()


@router.get(
    "/logs",
    response_model=PaginatedResponse,
    summary="Get audit logs",
    description="Retrieve audit logs with optional filtering"
)
async def get_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering and pagination."""
    # Check permissions - only admins can view all audit logs
    if current_user.role != "admin" and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view audit logs"
        )
    
    try:
        # Get audit logs
        audit_logs = audit_service.get_audit_logs(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            db=db
        )
        
        # Convert to response format
        items = [AuditLogResponse.from_orm(log) for log in audit_logs]
        
        # Get total count for pagination
        total_count = len(audit_logs)  # Simplified - in production, use separate count query
        
        return PaginatedResponse(
            items=items,
            total=total_count,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total_count + limit - 1) // limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )


@router.get(
    "/security-events",
    response_model=PaginatedResponse,
    summary="Get security events",
    description="Retrieve security events with optional filtering"
)
async def get_security_events(
    severity: Optional[str] = Query(None, regex=r'^(low|medium|high|critical)$', description="Filter by severity"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(require_permission("view_security_events")),
    db: Session = Depends(get_db)
):
    """Get security events with filtering and pagination."""
    try:
        # Convert severity string to enum if provided
        severity_enum = None
        if severity:
            severity_enum = SecurityEventSeverity(severity)
        
        # Get security events
        security_events = audit_service.get_security_events(
            severity=severity_enum,
            resolved=resolved,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            db=db
        )
        
        # Convert to response format
        items = [SecurityEventResponse.from_orm(event) for event in security_events]
        
        # Get total count for pagination
        total_count = len(security_events)  # Simplified - in production, use separate count query
        
        return PaginatedResponse(
            items=items,
            total=total_count,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total_count + limit - 1) // limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security events: {str(e)}"
        )


@router.patch(
    "/security-events/{event_id}/resolve",
    response_model=SecurityEventResponse,
    summary="Resolve security event",
    description="Mark a security event as resolved"
)
async def resolve_security_event(
    event_id: UUID,
    resolution_data: SecurityEventResolve,
    current_user: User = Depends(require_permission("resolve_security_events")),
    db: Session = Depends(get_db)
):
    """Resolve a security event."""
    try:
        # Resolve the security event
        security_event = audit_service.resolve_security_event(
            event_id=event_id,
            resolved_by=current_user.id,
            resolution_notes=resolution_data.resolution_notes,
            db=db
        )
        
        return SecurityEventResponse.from_orm(security_event)
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Security event {event_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve security event: {str(e)}"
        )


@router.post(
    "/compliance-reports",
    response_model=ComplianceReportData,
    summary="Generate compliance report",
    description="Generate a compliance report for the specified period"
)
async def generate_compliance_report(
    report_request: ComplianceReportCreate,
    current_user: User = Depends(require_permission("generate_compliance_reports")),
    db: Session = Depends(get_db)
):
    """Generate a compliance report."""
    try:
        # Generate the compliance report
        report_data = audit_service.generate_compliance_report(
            start_date=report_request.period_start,
            end_date=report_request.period_end,
            report_type=report_request.report_type,
            db=db
        )
        
        # Log the report generation
        audit_service.log_audit_event(
            event_type=AuditEventType.COMPLIANCE_REPORT_GENERATED,
            user_id=current_user.id,
            resource_type="compliance_report",
            details={
                "report_type": report_request.report_type,
                "period_start": report_request.period_start.isoformat(),
                "period_end": report_request.period_end.isoformat()
            },
            db=db
        )
        
        return ComplianceReportData(**report_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.get(
    "/statistics/audit",
    response_model=AuditStatistics,
    summary="Get audit statistics",
    description="Get audit log statistics for the specified period"
)
async def get_audit_statistics(
    start_date: datetime = Query(..., description="Start date for statistics"),
    end_date: datetime = Query(..., description="End date for statistics"),
    current_user: User = Depends(require_permission("view_audit_statistics")),
    db: Session = Depends(get_db)
):
    """Get audit statistics for the specified period."""
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Generate statistics
        stats = audit_service._get_audit_statistics(start_date, end_date, db)
        stats["date_range"] = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        return AuditStatistics(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit statistics: {str(e)}"
        )


@router.get(
    "/statistics/security",
    response_model=SecurityStatistics,
    summary="Get security statistics",
    description="Get security event statistics for the specified period"
)
async def get_security_statistics(
    start_date: datetime = Query(..., description="Start date for statistics"),
    end_date: datetime = Query(..., description="End date for statistics"),
    current_user: User = Depends(require_permission("view_security_statistics")),
    db: Session = Depends(get_db)
):
    """Get security statistics for the specified period."""
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Generate statistics
        stats = audit_service._get_security_statistics(start_date, end_date, db)
        
        return SecurityStatistics(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security statistics: {str(e)}"
        )


@router.get(
    "/statistics/user-activity",
    response_model=UserActivityStatistics,
    summary="Get user activity statistics",
    description="Get user activity statistics for the specified period"
)
async def get_user_activity_statistics(
    start_date: datetime = Query(..., description="Start date for statistics"),
    end_date: datetime = Query(..., description="End date for statistics"),
    current_user: User = Depends(require_permission("view_user_activity_statistics")),
    db: Session = Depends(get_db)
):
    """Get user activity statistics for the specified period."""
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Generate statistics
        stats = audit_service._get_user_activity_statistics(start_date, end_date, db)
        
        return UserActivityStatistics(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user activity statistics: {str(e)}"
        )


@router.get(
    "/statistics/compliance",
    response_model=ComplianceMetrics,
    summary="Get compliance metrics",
    description="Get compliance metrics for the specified period"
)
async def get_compliance_metrics(
    start_date: datetime = Query(..., description="Start date for metrics"),
    end_date: datetime = Query(..., description="End date for metrics"),
    current_user: User = Depends(require_permission("view_compliance_metrics")),
    db: Session = Depends(get_db)
):
    """Get compliance metrics for the specified period."""
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Generate metrics
        metrics = audit_service._get_compliance_metrics(start_date, end_date, db)
        
        return ComplianceMetrics(**metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve compliance metrics: {str(e)}"
        )


@router.delete(
    "/logs/cleanup",
    summary="Cleanup old audit logs",
    description="Clean up audit logs older than the specified retention period"
)
async def cleanup_audit_logs(
    retention_days: int = Query(365, ge=1, le=3650, description="Number of days to retain audit logs"),
    current_user: User = Depends(require_permission("manage_audit_logs")),
    db: Session = Depends(get_db)
):
    """Clean up old audit logs based on retention policy."""
    try:
        # Perform cleanup
        deleted_count = audit_service.cleanup_old_audit_logs(
            retention_days=retention_days,
            db=db
        )
        
        # Log the cleanup operation
        audit_service.log_audit_event(
            event_type=AuditEventType.AUDIT_LOG_CLEANUP,
            user_id=current_user.id,
            resource_type="audit_logs",
            details={
                "retention_days": retention_days,
                "deleted_count": deleted_count
            },
            db=db
        )
        
        return {
            "message": f"Successfully cleaned up {deleted_count} audit log records",
            "deleted_count": deleted_count,
            "retention_days": retention_days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup audit logs: {str(e)}"
        )


# Health check endpoint for audit service
@router.get(
    "/health",
    summary="Audit service health check",
    description="Check the health of the audit logging service"
)
async def audit_health_check(
    db: Session = Depends(get_db)
):
    """Check the health of the audit logging service."""
    try:
        # Test database connectivity by counting recent audit logs
        from sqlalchemy import func
        from models.database import AuditLog
        
        recent_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "recent_audit_logs": recent_count,
            "database_connection": "ok"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "database_connection": "failed"
        }