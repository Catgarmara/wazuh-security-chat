"""
Alert Management API endpoints.

This module provides comprehensive alert lifecycle management endpoints,
including workflow creation, status updates, and automated response actions.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from core.redis_client import get_redis_client
from services.siem_service import get_siem_service, SIEMServiceException
from models.database import User

# Request/Response models
class AlertStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    assigned_to: Optional[str] = None

class WorkflowStepUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    assigned_to: Optional[str] = None

class WorkflowCreate(BaseModel):
    name: str
    description: str
    alert_id: str
    workflow_type: str = "generic"
    priority: int = 3
    assigned_to: Optional[str] = None
    auto_start: bool = False

class AlertComment(BaseModel):
    message: str
    alert_id: str

class BulkAlertUpdate(BaseModel):
    alert_ids: List[str]
    status: str
    notes: Optional[str] = None

class AlertRule(BaseModel):
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    severity: str = "medium"


# Create router
router = APIRouter(prefix="/alerts", tags=["Alert Management"])


@router.get("/{alert_id}", response_model=Dict[str, Any])
async def get_alert_details(
    alert_id: str = Path(..., description="Alert ID to retrieve"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific alert.
    
    Args:
        alert_id: Alert ID to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Detailed alert information including history and workflows
    """
    try:
        siem_service = get_siem_service()
        redis_client = get_redis_client()
        
        # Get alert from cache or SIEM service
        cached_alert = await redis_client.get(f"alert:{alert_id}")
        if cached_alert:
            import json
            alert_data = json.loads(cached_alert)
        else:
            # This would fetch from actual alert storage
            alert_data = {
                "id": alert_id,
                "rule_id": 5712,
                "rule_description": "Example security alert",
                "severity": "high",
                "status": "open",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_name": "example-agent",
                "category": "Security"
            }
        
        # Get alert history
        history = await _get_alert_history(alert_id)
        
        # Get associated workflows
        workflows = await _get_alert_workflows(alert_id)
        
        # Get comments
        comments = await _get_alert_comments(alert_id)
        
        return {
            "alert": alert_data,
            "history": history,
            "workflows": workflows,
            "comments": comments
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert: {str(e)}"
        )


@router.put("/{alert_id}/status", response_model=Dict[str, str])
async def update_alert_status(
    alert_id: str = Path(..., description="Alert ID to update"),
    status_update: AlertStatusUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Update alert status and add to history.
    
    Args:
        alert_id: Alert ID to update
        status_update: New status information
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Update confirmation
    """
    try:
        # Validate status
        valid_statuses = ["open", "acknowledged", "resolved", "false_positive", "in_progress"]
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update alert status in cache/database
        await _update_alert_status(
            alert_id, 
            status_update.status, 
            current_user.username,
            status_update.notes,
            status_update.assigned_to
        )
        
        # Add to history
        await _add_alert_history(
            alert_id,
            "status_change",
            f"Status changed to {status_update.status}",
            current_user.username,
            {
                "old_status": "open",  # This would be fetched from current alert
                "new_status": status_update.status,
                "notes": status_update.notes,
                "assigned_to": status_update.assigned_to
            }
        )
        
        # Trigger automated actions if configured
        await _trigger_alert_actions(alert_id, status_update.status, current_user)
        
        return {
            "message": f"Alert {alert_id} status updated to {status_update.status}",
            "alert_id": alert_id,
            "status": status_update.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating alert status: {str(e)}"
        )


@router.post("/{alert_id}/comments", response_model=Dict[str, str])
async def add_alert_comment(
    alert_id: str = Path(..., description="Alert ID to comment on"),
    comment: AlertComment = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Add comment to an alert.
    
    Args:
        alert_id: Alert ID to comment on
        comment: Comment data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Comment creation confirmation
    """
    try:
        comment_id = str(uuid4())
        
        await _add_alert_comment(
            alert_id,
            comment_id,
            comment.message,
            current_user.username
        )
        
        # Add to history
        await _add_alert_history(
            alert_id,
            "comment_added",
            f"Comment added by {current_user.username}",
            current_user.username,
            {"comment_id": comment_id, "comment": comment.message}
        )
        
        return {
            "message": "Comment added successfully",
            "comment_id": comment_id,
            "alert_id": alert_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding comment: {str(e)}"
        )


@router.post("/{alert_id}/workflows", response_model=Dict[str, Any])
async def create_alert_workflow(
    alert_id: str = Path(..., description="Alert ID to create workflow for"),
    workflow_data: WorkflowCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new workflow for an alert.
    
    Args:
        alert_id: Alert ID to create workflow for
        workflow_data: Workflow creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created workflow information
    """
    try:
        siem_service = get_siem_service()
        
        # Create workflow using SIEM service
        workflow = await siem_service.create_alert_workflow(
            alert_id=alert_id,
            workflow_type=workflow_data.workflow_type
        )
        
        # Update with user-provided data
        workflow.update({
            "name": workflow_data.name,
            "description": workflow_data.description,
            "priority": workflow_data.priority,
            "assigned_to": workflow_data.assigned_to or current_user.username,
            "created_by": current_user.username
        })
        
        # Store workflow
        await _store_workflow(workflow)
        
        # Add to alert history
        await _add_alert_history(
            alert_id,
            "workflow_created",
            f"Workflow '{workflow_data.name}' created",
            current_user.username,
            {"workflow_id": workflow["id"], "workflow_type": workflow_data.workflow_type}
        )
        
        # Auto-start if requested
        if workflow_data.auto_start:
            await _start_workflow(workflow["id"], current_user.username)
        
        return workflow
        
    except SIEMServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SIEM service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating workflow: {str(e)}"
        )


@router.get("/{alert_id}/workflows", response_model=List[Dict[str, Any]])
async def get_alert_workflows(
    alert_id: str = Path(..., description="Alert ID to get workflows for"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all workflows associated with an alert.
    
    Args:
        alert_id: Alert ID to get workflows for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of workflows for the alert
    """
    try:
        workflows = await _get_alert_workflows(alert_id)
        return workflows
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving workflows: {str(e)}"
        )


@router.put("/workflows/{workflow_id}/steps/{step_id}", response_model=Dict[str, str])
async def update_workflow_step(
    workflow_id: str = Path(..., description="Workflow ID"),
    step_id: str = Path(..., description="Step ID to update"),
    step_update: WorkflowStepUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Update a workflow step status.
    
    Args:
        workflow_id: Workflow ID
        step_id: Step ID to update
        step_update: Step update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Update confirmation
    """
    try:
        # Validate step status
        valid_statuses = ["pending", "in_progress", "completed", "skipped", "failed"]
        if step_update.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update workflow step
        await _update_workflow_step(
            workflow_id,
            step_id,
            step_update.status,
            current_user.username,
            step_update.notes,
            step_update.assigned_to
        )
        
        return {
            "message": f"Workflow step {step_id} updated to {step_update.status}",
            "workflow_id": workflow_id,
            "step_id": step_id,
            "status": step_update.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating workflow step: {str(e)}"
        )


@router.post("/bulk-update", response_model=Dict[str, Any])
async def bulk_update_alerts(
    bulk_update: BulkAlertUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Bulk update multiple alerts.
    
    Args:
        bulk_update: Bulk update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Bulk update results
    """
    try:
        results = {
            "successful": [],
            "failed": [],
            "total": len(bulk_update.alert_ids)
        }
        
        for alert_id in bulk_update.alert_ids:
            try:
                await _update_alert_status(
                    alert_id,
                    bulk_update.status,
                    current_user.username,
                    bulk_update.notes
                )
                
                await _add_alert_history(
                    alert_id,
                    "bulk_status_change",
                    f"Bulk status change to {bulk_update.status}",
                    current_user.username,
                    {"new_status": bulk_update.status, "notes": bulk_update.notes}
                )
                
                results["successful"].append(alert_id)
                
            except Exception as e:
                results["failed"].append({
                    "alert_id": alert_id,
                    "error": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk update: {str(e)}"
        )


@router.get("/rules", response_model=List[Dict[str, Any]])
async def get_alert_rules(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get alert automation rules.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of alert rules
    """
    try:
        # This would fetch from actual rule storage
        rules = await _get_alert_rules()
        return rules
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert rules: {str(e)}"
        )


@router.post("/rules", response_model=Dict[str, Any])
async def create_alert_rule(
    rule: AlertRule = Body(...),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create new alert automation rule (Admin only).
    
    Args:
        rule: Alert rule data
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Created rule information
    """
    try:
        rule_id = str(uuid4())
        
        rule_data = {
            "id": rule_id,
            "name": rule.name,
            "description": rule.description,
            "conditions": rule.conditions,
            "actions": rule.actions,
            "enabled": rule.enabled,
            "severity": rule.severity,
            "created_by": current_user.username,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await _store_alert_rule(rule_data)
        
        return rule_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating alert rule: {str(e)}"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_alert_statistics(
    time_range: str = Query("24h", description="Time range for statistics"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get alert management statistics.
    
    Args:
        time_range: Time range for statistics (24h, 7d, 30d)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Alert statistics
    """
    try:
        # Calculate time range
        now = datetime.utcnow()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)
        
        # This would calculate from actual data
        stats = {
            "total_alerts": 156,
            "by_status": {
                "open": 45,
                "acknowledged": 23,
                "resolved": 78,
                "false_positive": 10
            },
            "by_severity": {
                "critical": 12,
                "high": 34,
                "medium": 67,
                "low": 43
            },
            "response_times": {
                "avg_acknowledgment_time": "15m",
                "avg_resolution_time": "2h 30m",
                "fastest_resolution": "5m",
                "slowest_resolution": "12h 45m"
            },
            "workflows": {
                "total_workflows": 89,
                "completed_workflows": 67,
                "avg_completion_time": "1h 45m"
            },
            "trends": {
                "alerts_per_hour": 6.5,
                "resolution_rate": 78.5,
                "false_positive_rate": 6.4
            }
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating statistics: {str(e)}"
        )


@router.get("/health")
async def alert_management_health_check() -> Dict[str, str]:
    """
    Health check endpoint for alert management service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "alert_management",
        "timestamp": str(int(time.time()))
    }


# Helper functions

async def _update_alert_status(alert_id: str, status: str, user: str, notes: str = None, assigned_to: str = None):
    """Update alert status in storage."""
    redis_client = get_redis_client()
    
    # Update alert data
    alert_key = f"alert:{alert_id}"
    update_data = {
        "status": status,
        "updated_by": user,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if notes:
        update_data["notes"] = notes
    if assigned_to:
        update_data["assigned_to"] = assigned_to
    
    # This would update in actual storage
    await redis_client.hset(alert_key, mapping=update_data)


async def _add_alert_history(alert_id: str, action: str, description: str, user: str, metadata: Dict = None):
    """Add entry to alert history."""
    redis_client = get_redis_client()
    
    history_entry = {
        "id": str(uuid4()),
        "alert_id": alert_id,
        "action": action,
        "description": description,
        "user": user,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    
    # Store in alert history list
    history_key = f"alert_history:{alert_id}"
    import json
    await redis_client.lpush(history_key, json.dumps(history_entry))
    
    # Keep only last 100 entries
    await redis_client.ltrim(history_key, 0, 99)


async def _get_alert_history(alert_id: str) -> List[Dict[str, Any]]:
    """Get alert history."""
    redis_client = get_redis_client()
    
    history_key = f"alert_history:{alert_id}"
    history_data = await redis_client.lrange(history_key, 0, -1)
    
    import json
    return [json.loads(entry) for entry in history_data]


async def _add_alert_comment(alert_id: str, comment_id: str, message: str, user: str):
    """Add comment to alert."""
    redis_client = get_redis_client()
    
    comment = {
        "id": comment_id,
        "alert_id": alert_id,
        "message": message,
        "user": user,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    comments_key = f"alert_comments:{alert_id}"
    import json
    await redis_client.lpush(comments_key, json.dumps(comment))


async def _get_alert_comments(alert_id: str) -> List[Dict[str, Any]]:
    """Get alert comments."""
    redis_client = get_redis_client()
    
    comments_key = f"alert_comments:{alert_id}"
    comments_data = await redis_client.lrange(comments_key, 0, -1)
    
    import json
    return [json.loads(comment) for comment in comments_data]


async def _get_alert_workflows(alert_id: str) -> List[Dict[str, Any]]:
    """Get workflows for alert."""
    # This would fetch from actual workflow storage
    return []


async def _store_workflow(workflow: Dict[str, Any]):
    """Store workflow data."""
    redis_client = get_redis_client()
    
    workflow_key = f"workflow:{workflow['id']}"
    import json
    await redis_client.setex(workflow_key, 3600, json.dumps(workflow))


async def _start_workflow(workflow_id: str, user: str):
    """Start workflow execution."""
    # This would implement workflow execution logic
    pass


async def _update_workflow_step(workflow_id: str, step_id: str, status: str, user: str, notes: str = None, assigned_to: str = None):
    """Update workflow step."""
    # This would update workflow step in storage
    pass


async def _trigger_alert_actions(alert_id: str, status: str, user: User):
    """Trigger automated actions based on alert status change."""
    # This would implement automated action triggering
    pass


async def _get_alert_rules() -> List[Dict[str, Any]]:
    """Get alert automation rules."""
    # This would fetch from actual rule storage
    return []


async def _store_alert_rule(rule: Dict[str, Any]):
    """Store alert rule."""
    redis_client = get_redis_client()
    
    rule_key = f"alert_rule:{rule['id']}"
    import json
    await redis_client.setex(rule_key, 86400, json.dumps(rule))