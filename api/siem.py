"""
SIEM API endpoints.

This module provides REST API endpoints for SIEM operations,
including Wazuh integration, security alerts, and threat monitoring.
"""

import time
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from services.siem_service import get_siem_service, SIEMServiceException
from models.database import User
from models.schemas import (
    WazuhManagerStatus, WazuhAgentResponse, SecurityAlertResponse,
    ThreatIntelligenceResponse, LogEventResponse, AlertWorkflowResponse,
    ThreatCorrelationResponse, PaginatedResponse
)


# Create router
router = APIRouter(prefix="/siem", tags=["SIEM"])


@router.get("/manager/status", response_model=Dict[str, Any])
async def get_wazuh_manager_status(
    use_cache: bool = Query(True, description="Use cached data if available"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Wazuh manager status and performance metrics.
    
    Args:
        use_cache: Whether to use cached data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Manager status data including performance metrics and module status
        
    Raises:
        HTTPException: If user lacks permissions or service error occurs
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_wazuh_manager_status(use_cache=use_cache)
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/agents", response_model=Dict[str, Any])
async def get_wazuh_agents(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to skip"),
    search: Optional[str] = Query(None, description="Search query for agent names/IPs"),
    status_filter: Optional[str] = Query(None, description="Filter by agent status"),
    use_cache: bool = Query(True, description="Use cached data if available"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Wazuh agents with filtering and pagination.
    
    Args:
        limit: Maximum number of agents to return
        offset: Number of agents to skip
        search: Search query for agent names/IPs
        status_filter: Filter by agent status (active, disconnected, pending, never_connected)
        use_cache: Whether to use cached data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Paginated list of agents with status information
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_wazuh_agents(
            limit=limit,
            offset=offset,
            search=search,
            status_filter=status_filter,
            use_cache=use_cache
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/alerts", response_model=Dict[str, Any])
async def get_security_alerts(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    severity_filter: Optional[str] = Query(None, description="Filter by alert severity"),
    status_filter: Optional[str] = Query(None, description="Filter by alert status"),
    time_range: Optional[str] = Query(None, description="Time range filter (24h, 7d, 30d)"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get security alerts with filtering and pagination.
    
    Args:
        limit: Maximum number of alerts to return
        offset: Number of alerts to skip
        severity_filter: Filter by severity (critical, high, medium, low)
        status_filter: Filter by status (open, acknowledged, resolved, false_positive)
        time_range: Time range filter (24h, 7d, 30d)
        search: Search query
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Paginated list of security alerts
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_security_alerts(
            limit=limit,
            offset=offset,
            severity_filter=severity_filter,
            status_filter=status_filter,
            time_range=time_range,
            search=search
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/threat-intelligence", response_model=Dict[str, Any])
async def get_threat_intelligence(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of indicators to return"),
    offset: int = Query(0, ge=0, description="Number of indicators to skip"),
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get threat intelligence indicators.
    
    Args:
        limit: Maximum number of indicators to return
        offset: Number of indicators to skip
        threat_type: Filter by threat type (malware, phishing, c2, botnet, vulnerability, apt, exploit)
        severity_filter: Filter by severity (critical, high, medium, low)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Threat intelligence indicators and feed status
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_threat_intelligence(
            limit=limit,
            offset=offset,
            threat_type=threat_type,
            severity_filter=severity_filter
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/logs", response_model=Dict[str, Any])
async def get_log_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    level_filter: Optional[str] = Query(None, description="Filter by log level"),
    source_filter: Optional[str] = Query(None, description="Filter by log source"),
    time_range: Optional[str] = Query(None, description="Time range filter (1h, 24h, 7d, 30d)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get log events with filtering.
    
    Args:
        limit: Maximum number of events to return
        offset: Number of events to skip
        level_filter: Filter by log level (error, warning, info, debug, trace)
        source_filter: Filter by source (wazuh, system, application, security, network, database)
        time_range: Time range filter (1h, 24h, 7d, 30d)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Log events with statistics
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_log_events(
            limit=limit,
            offset=offset,
            level_filter=level_filter,
            source_filter=source_filter,
            time_range=time_range
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/alerts/{alert_id}/workflow", response_model=Dict[str, Any])
async def create_alert_workflow(
    alert_id: str = Path(..., description="Alert ID to create workflow for"),
    workflow_type: str = Query("critical_malware", description="Type of workflow to create"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create an alert management workflow.
    
    Args:
        alert_id: Alert ID to create workflow for
        workflow_type: Type of workflow to create
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created workflow data
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.create_alert_workflow(
            alert_id=alert_id,
            workflow_type=workflow_type
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/correlations", response_model=Dict[str, Any])
async def get_threat_correlations(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of correlations to return"),
    offset: int = Query(0, ge=0, description="Number of correlations to skip"),
    correlation_type: Optional[str] = Query(None, description="Filter by correlation type"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get threat correlations and attack patterns.
    
    Args:
        limit: Maximum number of correlations to return
        offset: Number of correlations to skip
        correlation_type: Filter by type (temporal, spatial, behavioral, contextual, tactical)
        severity_filter: Filter by severity (critical, high, medium, low)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Threat correlations with statistics
    """
    try:
        siem_service = get_siem_service()
        return await siem_service.get_threat_correlations(
            limit=limit,
            offset=offset,
            correlation_type=correlation_type,
            severity_filter=severity_filter
        )
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_siem_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get SIEM dashboard overview data.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Overview statistics for SIEM dashboard
    """
    try:
        siem_service = get_siem_service()
        
        # Get data from multiple sources
        manager_status = await siem_service.get_wazuh_manager_status(use_cache=True)
        agents_data = await siem_service.get_wazuh_agents(limit=1, use_cache=True)
        alerts_data = await siem_service.get_security_alerts(limit=1, time_range="24h")
        threat_intel = await siem_service.get_threat_intelligence(limit=1)
        logs_data = await siem_service.get_log_events(limit=1, time_range="24h")
        
        # Calculate overview statistics
        overview_stats = {
            "manager_status": manager_status.get("status", "offline"),
            "total_agents": agents_data.get("total", 0),
            "active_agents": len([a for a in agents_data.get("agents", []) if a.get("status") == "active"]),
            "total_alerts": alerts_data.get("total", 0),
            "critical_alerts": len([a for a in alerts_data.get("alerts", []) if a.get("severity") == "critical"]),
            "threat_indicators": threat_intel.get("total", 0),
            "active_threats": len([i for i in threat_intel.get("indicators", []) if i.get("status") == "active"]),
            "log_events_24h": logs_data.get("total", 0),
            "security_score": 87  # This would be calculated based on various factors
        }
        
        return overview_stats
        
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def siem_health_check() -> Dict[str, str]:
    """
    Health check endpoint for SIEM service.
    
    Returns:
        Health status of SIEM components
    """
    try:
        siem_service = get_siem_service()
        
        # Test Wazuh connectivity
        manager_status = await siem_service.get_wazuh_manager_status(use_cache=False)
        wazuh_healthy = manager_status.get("status") != "offline"
        
        return {
            "status": "healthy" if wazuh_healthy else "degraded",
            "service": "siem",
            "wazuh_manager": "connected" if wazuh_healthy else "disconnected",
            "timestamp": str(int(time.time()))
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "siem",
            "error": str(e),
            "timestamp": str(int(time.time()))
        }


# Admin-only endpoints for SIEM management

@router.post("/manager/restart")
async def restart_wazuh_manager(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Restart Wazuh manager (Admin only).
    
    Args:
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Operation status
    """
    # This would implement actual restart logic
    return {
        "message": "Wazuh manager restart initiated",
        "status": "pending"
    }


@router.post("/agents/{agent_id}/restart")
async def restart_wazuh_agent(
    agent_id: str = Path(..., description="Agent ID to restart"),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Restart specific Wazuh agent (Admin only).
    
    Args:
        agent_id: Agent ID to restart
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Operation status
    """
    # This would implement actual agent restart logic
    return {
        "message": f"Agent {agent_id} restart initiated",
        "status": "pending"
    }


@router.put("/alerts/{alert_id}/status")
async def update_alert_status(
    alert_id: str = Path(..., description="Alert ID to update"),
    new_status: str = Query(..., description="New alert status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Update alert status.
    
    Args:
        alert_id: Alert ID to update
        new_status: New status (open, acknowledged, resolved, false_positive)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Update status
    """
    # This would implement actual alert status update logic
    return {
        "message": f"Alert {alert_id} status updated to {new_status}",
        "alert_id": alert_id,
        "status": new_status
    }