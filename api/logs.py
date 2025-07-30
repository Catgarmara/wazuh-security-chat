"""
Log Management API endpoints.

This module provides REST API endpoints for log statistics, health checks,
log reload operations, and log search/filtering functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from services.log_service import LogService, LogFilter, SSHCredentials
from models.database import User
from models.schemas import (
    LogEntryResponse, LogEntrySearch, LogStats as LogStatsSchema,
    PaginatedResponse, DateRange
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/logs", tags=["Log Management"])


def get_log_service() -> LogService:
    """Get log service instance."""
    return LogService()


@router.get("/health")
async def log_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get log processing system health status.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Health status information
    """
    try:
        log_service = get_log_service()
        
        # Get basic health metrics
        health_status = {
            "status": "healthy",
            "service": "log_management",
            "timestamp": datetime.now().isoformat(),
            "last_reload": None,
            "total_logs_cached": 0,
            "avg_processing_time": 0.0,
            "disk_usage_mb": 0.0,
            "memory_usage_mb": 0.0
        }
        
        # Try to load a small sample to test functionality
        try:
            sample_logs = log_service.load_logs_from_days(1)
            health_status["total_logs_cached"] = len(sample_logs)
            health_status["status"] = "healthy"
        except Exception as e:
            logger.warning(f"Log loading test failed: {e}")
            health_status["status"] = "warning"
            health_status["error"] = str(e)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking log health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check log system health"
        )


@router.get("/stats")
async def get_log_statistics(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    include_metadata: bool = Query(True, description="Include detailed metadata"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get comprehensive log statistics.
    
    Args:
        days: Number of days to analyze (1-365)
        include_metadata: Whether to include detailed metadata
        current_user: Current authenticated user
        
    Returns:
        Log statistics and metadata
    """
    try:
        log_service = get_log_service()
        
        # Load logs for the specified period
        logs = log_service.load_logs_from_days(days)
        
        # Generate statistics
        stats = log_service.get_log_statistics(logs)
        
        # Convert to response format
        response = {
            "total_logs": stats.total_logs,
            "date_range": stats.date_range,
            "sources": stats.sources,
            "levels": stats.levels,
            "processing_time": stats.processing_time,
            "days_analyzed": days
        }
        
        # Add detailed metadata if requested
        if include_metadata:
            response.update({
                "agents": stats.agents,
                "rules": stats.rules,
                "decoders": stats.decoders,
                "severity_distribution": stats.severity_distribution,
                "hourly_distribution": stats.hourly_distribution
            })
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating log statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate log statistics: {str(e)}"
        )


@router.post("/reload")
async def reload_logs(
    background_tasks: BackgroundTasks,
    days: int = Query(7, ge=1, le=365, description="Number of days to reload"),
    force: bool = Query(False, description="Force reload even if recent"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Reload logs from the specified number of days (Admin only).
    
    Args:
        background_tasks: FastAPI background tasks
        days: Number of days to reload (1-365)
        force: Force reload even if recently done
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Reload operation status
    """
    try:
        log_service = get_log_service()
        
        # Start reload operation in background
        def reload_task():
            try:
                start_time = datetime.now()
                logs = log_service.load_logs_from_days(days)
                end_time = datetime.now()
                
                logger.info(f"Log reload completed: {len(logs)} logs loaded in {(end_time - start_time).total_seconds():.2f}s")
                
            except Exception as e:
                logger.error(f"Background log reload failed: {e}")
        
        background_tasks.add_task(reload_task)
        
        return {
            "message": f"Log reload started for {days} days",
            "status": "started",
            "days": days,
            "force": force,
            "initiated_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error initiating log reload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate log reload: {str(e)}"
        )


@router.post("/reload/date-range")
async def reload_logs_date_range(
    background_tasks: BackgroundTasks,
    date_range: DateRange,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Reload logs for a specific date range (Admin only).
    
    Args:
        background_tasks: FastAPI background tasks
        date_range: Start and end dates for reload
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Reload operation status
    """
    try:
        log_service = get_log_service()
        
        # Validate date range
        days_diff = (date_range.end_date - date_range.start_date).days + 1
        if days_diff > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 365 days"
            )
        
        # Start reload operation in background
        def reload_date_range_task():
            try:
                status = log_service.reload_logs_with_date_range(
                    start_date=date_range.start_date,
                    end_date=date_range.end_date
                )
                logger.info(f"Date range reload completed: {status.status}")
                
            except Exception as e:
                logger.error(f"Background date range reload failed: {e}")
        
        background_tasks.add_task(reload_date_range_task)
        
        return {
            "message": f"Log reload started for date range",
            "status": "started",
            "start_date": date_range.start_date.isoformat(),
            "end_date": date_range.end_date.isoformat(),
            "days": days_diff,
            "initiated_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating date range reload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate date range reload: {str(e)}"
        )


@router.get("/search")
async def search_logs(
    query: Optional[str] = Query(None, description="Search query text"),
    source: Optional[str] = Query(None, description="Filter by log source"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    agent: Optional[str] = Query(None, description="Filter by agent name"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    severity_min: Optional[int] = Query(None, ge=0, le=15, description="Minimum severity level"),
    severity_max: Optional[int] = Query(None, ge=0, le=15, description="Maximum severity level"),
    days: int = Query(7, ge=1, le=365, description="Number of days to search"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Search and filter logs based on various criteria.
    
    Args:
        query: Text search query
        source: Filter by log source
        level: Filter by log level
        agent: Filter by agent name
        rule_id: Filter by rule ID
        start_date: Start date for filtering
        end_date: End date for filtering
        severity_min: Minimum severity level
        severity_max: Maximum severity level
        days: Number of days to search in
        limit: Maximum number of results
        offset: Number of results to skip
        current_user: Current authenticated user
        
    Returns:
        Filtered and paginated log results
    """
    try:
        log_service = get_log_service()
        
        # Load logs for the specified period
        logs = log_service.load_logs_from_days(days)
        
        # Create filter object
        log_filter = LogFilter(
            start_date=start_date,
            end_date=end_date,
            levels=[level] if level else None,
            sources=[source] if source else None,
            agents=[agent] if agent else None,
            rule_ids=[rule_id] if rule_id else None,
            search_text=query,
            severity_min=severity_min,
            severity_max=severity_max
        )
        
        # Apply filters
        filtered_logs = log_service.filter_logs(logs, log_filter)
        
        # Apply text search if provided
        if query:
            filtered_logs = log_service.search_logs(filtered_logs, query)
        
        # Apply pagination
        total_results = len(filtered_logs)
        paginated_logs = filtered_logs[offset:offset + limit]
        
        # Convert to response format
        log_responses = []
        for log in paginated_logs:
            log_responses.append({
                "id": f"{log.get('timestamp', '')}-{hash(str(log))}",
                "timestamp": log.get('timestamp'),
                "source": log.get('location', 'unknown'),
                "level": log.get('level', 'unknown'),
                "full_log": log.get('full_log', ''),
                "agent_name": log.get('agent', {}).get('name') if isinstance(log.get('agent'), dict) else None,
                "rule_id": log.get('rule', {}).get('id') if isinstance(log.get('rule'), dict) else None,
                "rule_level": log.get('rule', {}).get('level') if isinstance(log.get('rule'), dict) else None,
                "decoder_name": log.get('decoder', {}).get('name') if isinstance(log.get('decoder'), dict) else None
            })
        
        return {
            "results": log_responses,
            "total": total_results,
            "limit": limit,
            "offset": offset,
            "pages": (total_results + limit - 1) // limit,
            "current_page": (offset // limit) + 1,
            "filters_applied": {
                "query": query,
                "source": source,
                "level": level,
                "agent": agent,
                "rule_id": rule_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "severity_min": severity_min,
                "severity_max": severity_max,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search logs: {str(e)}"
        )


@router.get("/sources")
async def get_log_sources(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get unique log sources from recent logs.
    
    Args:
        days: Number of days to analyze
        current_user: Current authenticated user
        
    Returns:
        List of unique log sources with counts
    """
    try:
        log_service = get_log_service()
        
        # Load logs and get statistics
        logs = log_service.load_logs_from_days(days)
        stats = log_service.get_log_statistics(logs)
        
        return {
            "sources": stats.sources,
            "total_sources": len(stats.sources),
            "days_analyzed": days,
            "total_logs": stats.total_logs
        }
        
    except Exception as e:
        logger.error(f"Error retrieving log sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve log sources: {str(e)}"
        )


@router.get("/agents")
async def get_log_agents(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get unique agents from recent logs.
    
    Args:
        days: Number of days to analyze
        current_user: Current authenticated user
        
    Returns:
        List of unique agents with counts
    """
    try:
        log_service = get_log_service()
        
        # Load logs and get statistics
        logs = log_service.load_logs_from_days(days)
        stats = log_service.get_log_statistics(logs)
        
        return {
            "agents": stats.agents,
            "total_agents": len(stats.agents),
            "days_analyzed": days,
            "total_logs": stats.total_logs
        }
        
    except Exception as e:
        logger.error(f"Error retrieving log agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve log agents: {str(e)}"
        )


@router.get("/rules")
async def get_log_rules(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(50, ge=1, le=500, description="Maximum rules to return"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get most common rules from recent logs.
    
    Args:
        days: Number of days to analyze
        limit: Maximum number of rules to return
        current_user: Current authenticated user
        
    Returns:
        List of rules with counts, sorted by frequency
    """
    try:
        log_service = get_log_service()
        
        # Load logs and get statistics
        logs = log_service.load_logs_from_days(days)
        stats = log_service.get_log_statistics(logs)
        
        # Sort rules by count and limit results
        sorted_rules = sorted(stats.rules.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            "rules": dict(sorted_rules),
            "total_unique_rules": len(stats.rules),
            "showing_top": len(sorted_rules),
            "days_analyzed": days,
            "total_logs": stats.total_logs
        }
        
    except Exception as e:
        logger.error(f"Error retrieving log rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve log rules: {str(e)}"
        )


@router.get("/config")
async def get_log_configuration(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current log processing configuration.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current log processing configuration
    """
    try:
        log_service = get_log_service()
        
        return {
            "log_base_path": log_service.log_base_path,
            "supported_formats": ["json", "json.gz"],
            "max_days_range": 365,
            "default_search_days": 7,
            "max_search_results": 1000,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving log configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve log configuration: {str(e)}"
        )


@router.post("/config")
async def update_log_configuration(
    config_data: Dict[str, Any],
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Update log processing configuration (Admin only).
    
    Args:
        config_data: Configuration updates
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Updated configuration
    """
    try:
        log_service = get_log_service()
        
        # Update allowed configuration parameters
        if "log_base_path" in config_data:
            log_service.log_base_path = config_data["log_base_path"]
        
        return {
            "message": "Configuration updated successfully",
            "updated_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
            "current_config": {
                "log_base_path": log_service.log_base_path
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating log configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update log configuration: {str(e)}"
        )