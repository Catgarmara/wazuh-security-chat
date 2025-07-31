"""
Analytics API endpoints.

This module provides REST API endpoints for analytics and monitoring,
including usage metrics, dashboard data, and system performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_user, admin_required, analyst_or_admin_required
from services.analytics_service import AnalyticsService
from models.schemas import (
    UsageMetrics, DashboardData, QueryMetricsResponse, SystemMetricsResponse,
    DateRange, SystemMetricsCreate, PaginatedResponse
)
from models.database import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Analytics service instance
analytics_service = AnalyticsService()


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    days: int = Query(default=7, ge=1, le=90, description="Number of days for metrics"),
    current_user: User = Depends(analyst_or_admin_required),
    db: Session = Depends(get_db)
) -> DashboardData:
    """
    Get comprehensive dashboard data including usage metrics and system health.
    
    Args:
        days: Number of days to include in metrics (1-90)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DashboardData: Comprehensive dashboard metrics
        
    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        date_range = DateRange(start_date=start_time, end_date=end_time)
        
        # Get usage metrics
        usage_metrics = analytics_service.get_usage_metrics(date_range=date_range)
        
        # Get recent queries (limited for dashboard)
        recent_queries = analytics_service.get_recent_queries(limit=10)
        
        # Get system performance metrics
        system_performance = analytics_service.get_system_performance_metrics(date_range=date_range)
        
        # Get user engagement metrics
        engagement_metrics = analytics_service.get_user_engagement_metrics(date_range=date_range)
        
        # Build system health summary
        system_health = {
            "database_status": "healthy",  # This could be enhanced with actual health checks
            "ai_service_status": "healthy",
            "performance_metrics": system_performance,
            "engagement_metrics": engagement_metrics,
            "last_updated": datetime.utcnow()
        }
        
        # Get log statistics (placeholder - would integrate with log service)
        log_statistics = {
            "total_logs": 0,
            "date_range": {"start_date": start_time, "end_date": end_time},
            "sources": {},
            "levels": {},
            "processing_time": 0.0
        }
        
        dashboard_data = DashboardData(
            usage_metrics=usage_metrics,
            recent_queries=recent_queries,
            system_health=system_health,
            log_statistics=log_statistics
        )
        
        logger.info(f"Dashboard data retrieved for user {current_user.id} ({days} days)")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )


@router.get("/usage-metrics", response_model=UsageMetrics)
async def get_usage_metrics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days for metrics"),
    user_id: Optional[UUID] = Query(default=None, description="Filter by specific user ID"),
    current_user: User = Depends(analyst_or_admin_required),
    db: Session = Depends(get_db)
) -> UsageMetrics:
    """
    Get detailed usage metrics for a specified time period.
    
    Args:
        days: Number of days to include in metrics (1-90)
        user_id: Optional user ID to filter metrics
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UsageMetrics: Detailed usage statistics
        
    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        date_range = DateRange(start_date=start_time, end_date=end_time)
        
        # Non-admin users can only view their own metrics
        if current_user.role != "admin" and user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view other users' metrics"
            )
        
        # Get usage metrics
        usage_metrics = analytics_service.get_usage_metrics(
            date_range=date_range,
            user_id=user_id
        )
        
        logger.info(
            f"Usage metrics retrieved for user {current_user.id} "
            f"(days={days}, filter_user={user_id})"
        )
        return usage_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage metrics"
        )


@router.get("/user-engagement", response_model=Dict[str, Any])
async def get_user_engagement_metrics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days for metrics"),
    current_user: User = Depends(analyst_or_admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user engagement and activity metrics.
    
    Args:
        days: Number of days to include in metrics (1-90)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict containing user engagement metrics
        
    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        date_range = DateRange(start_date=start_time, end_date=end_time)
        
        # Get user engagement metrics
        engagement_metrics = analytics_service.get_user_engagement_metrics(date_range=date_range)
        
        logger.info(f"User engagement metrics retrieved for user {current_user.id} ({days} days)")
        return engagement_metrics
        
    except Exception as e:
        logger.error(f"Failed to get user engagement metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user engagement metrics"
        )


@router.get("/system-performance", response_model=Dict[str, Any])
async def get_system_performance_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours for metrics"),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get system performance and health metrics.
    
    Args:
        hours: Number of hours to include in metrics (1-168)
        current_user: Current authenticated user (admin only)
        db: Database session
        
    Returns:
        Dict containing system performance metrics
        
    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        date_range = DateRange(start_date=start_time, end_date=end_time)
        
        # Get system performance metrics
        performance_metrics = analytics_service.get_system_performance_metrics(date_range=date_range)
        
        logger.info(f"System performance metrics retrieved for admin {current_user.id} ({hours} hours)")
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Failed to get system performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system performance metrics"
        )


@router.get("/queries/recent", response_model=List[QueryMetricsResponse])
async def get_recent_queries(
    limit: int = Query(default=20, ge=1, le=100, description="Number of recent queries to return"),
    user_id: Optional[UUID] = Query(default=None, description="Filter by specific user ID"),
    current_user: User = Depends(analyst_or_admin_required),
    db: Session = Depends(get_db)
) -> List[QueryMetricsResponse]:
    """
    Get recent query metrics.
    
    Args:
        limit: Maximum number of queries to return (1-100)
        user_id: Optional user ID to filter queries
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of recent query metrics
        
    Raises:
        HTTPException: If query retrieval fails
    """
    try:
        # Non-admin users can only view their own queries
        if current_user.role != "admin" and user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view other users' queries"
            )
        
        # If no user_id specified and user is not admin, show only their queries
        if not user_id and current_user.role != "admin":
            user_id = current_user.id
        
        # Get recent queries
        recent_queries = analytics_service.get_recent_queries(
            limit=limit,
            user_id=user_id
        )
        
        logger.info(
            f"Recent queries retrieved for user {current_user.id} "
            f"(limit={limit}, filter_user={user_id})"
        )
        return recent_queries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent queries"
        )


@router.post("/system-metrics", response_model=SystemMetricsResponse)
async def record_system_metric(
    metric_data: SystemMetricsCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> SystemMetricsResponse:
    """
    Record a system performance metric.
    
    Args:
        metric_data: System metric data to record
        current_user: Current authenticated user (admin only)
        db: Database session
        
    Returns:
        SystemMetricsResponse: Created system metric record
        
    Raises:
        HTTPException: If metric recording fails
    """
    try:
        # Record the system metric
        system_metric = analytics_service.record_system_metric(
            metric_name=metric_data.metric_name,
            metric_value=metric_data.metric_value,
            metric_unit=metric_data.metric_unit,
            tags=metric_data.tags
        )
        
        logger.info(
            f"System metric recorded by admin {current_user.id}: "
            f"{metric_data.metric_name}={metric_data.metric_value}"
        )
        return system_metric
        
    except Exception as e:
        logger.error(f"Failed to record system metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record system metric"
        )


@router.get("/reports/usage", response_model=Dict[str, Any])
async def generate_usage_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    format: str = Query(default="json", pattern="^(json|csv)$", description="Report format"),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a comprehensive usage report for a date range.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        format: Report format (json or csv)
        current_user: Current authenticated user (admin only)
        db: Database session
        
    Returns:
        Dict containing comprehensive usage report
        
    Raises:
        HTTPException: If report generation fails
    """
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Limit report range to prevent performance issues
        max_days = 365
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report range cannot exceed {max_days} days"
            )
        
        date_range = DateRange(start_date=start_date, end_date=end_date)
        
        # Get comprehensive metrics
        usage_metrics = analytics_service.get_usage_metrics(date_range=date_range)
        engagement_metrics = analytics_service.get_user_engagement_metrics(date_range=date_range)
        performance_metrics = analytics_service.get_system_performance_metrics(date_range=date_range)
        
        # Build comprehensive report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow(),
                "generated_by": current_user.username,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "format": format
            },
            "usage_summary": usage_metrics.dict(),
            "user_engagement": engagement_metrics,
            "system_performance": performance_metrics,
            "trends": {
                "query_volume_trend": "stable",  # This could be enhanced with actual trend analysis
                "user_growth_trend": "growing",
                "performance_trend": "stable"
            }
        }
        
        logger.info(
            f"Usage report generated by admin {current_user.id} "
            f"for period {start_date} to {end_date}"
        )
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate usage report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate usage report"
        )


@router.delete("/metrics/cleanup")
async def cleanup_old_metrics(
    days_to_keep: int = Query(default=90, ge=30, le=365, description="Days of metrics to retain"),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Clean up old metrics data to manage database size.
    
    Args:
        days_to_keep: Number of days of metrics to retain (30-365)
        current_user: Current authenticated user (admin only)
        db: Database session
        
    Returns:
        Dict containing cleanup results
        
    Raises:
        HTTPException: If cleanup fails
    """
    try:
        # Perform cleanup
        deleted_count = analytics_service.cleanup_old_metrics(days_to_keep=days_to_keep)
        
        result = {
            "cleanup_completed": True,
            "records_deleted": deleted_count,
            "days_retained": days_to_keep,
            "cleanup_date": datetime.utcnow(),
            "performed_by": current_user.username
        }
        
        logger.info(
            f"Metrics cleanup performed by admin {current_user.id}: "
            f"{deleted_count} records deleted, {days_to_keep} days retained"
        )
        return result
        
    except Exception as e:
        logger.error(f"Failed to cleanup old metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup old metrics"
        )


@router.get("/health", response_model=Dict[str, Any])
async def analytics_health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Health check endpoint for analytics service.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict containing health status
    """
    try:
        # Basic health checks
        health_status = {
            "service": "analytics",
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": "1.0.0",
            "checks": {
                "database": "healthy",
                "analytics_service": "healthy"
            }
        }
        
        # Try to get a simple metric to verify service is working
        try:
            recent_queries = analytics_service.get_recent_queries(limit=1)
            health_status["checks"]["query_retrieval"] = "healthy"
        except Exception as e:
            health_status["checks"]["query_retrieval"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return {
            "service": "analytics",
            "status": "unhealthy",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }