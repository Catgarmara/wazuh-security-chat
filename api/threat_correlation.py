"""
Threat Correlation API endpoints.

This module provides advanced threat correlation and analysis endpoints,
including attack pattern detection, threat hunting, and behavioral analysis.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from core.redis_client import get_redis_client
from services.siem_service import get_siem_service, SIEMServiceException
from models.database import User

# Request/Response models
class ThreatCorrelationRule(BaseModel):
    name: str
    description: str
    rule_type: str = "behavioral"  # behavioral, temporal, spatial, contextual, tactical
    conditions: Dict[str, Any]
    severity: str = "medium"
    confidence_threshold: float = 0.7
    time_window: int = 3600  # seconds
    enabled: bool = True

class ThreatHuntQuery(BaseModel):
    query: str
    time_range: str = "24h"
    data_sources: List[str] = ["alerts", "logs", "network"]
    hunt_type: str = "indicators"  # indicators, behaviors, anomalies
    confidence_threshold: float = 0.6

class AttackPathAnalysis(BaseModel):
    start_event_id: str
    max_depth: int = 10
    time_window: int = 7200  # 2 hours
    include_lateral_movement: bool = True
    include_privilege_escalation: bool = True

class BehavioralProfile(BaseModel):
    entity_type: str  # user, host, network, application
    entity_id: str
    profile_period: str = "7d"
    include_baselines: bool = True
    anomaly_detection: bool = True

# Create router
router = APIRouter(prefix="/threat-correlation", tags=["Threat Correlation"])


@router.get("/correlations", response_model=Dict[str, Any])
async def get_threat_correlations(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of correlations to return"),
    offset: int = Query(0, ge=0, description="Number of correlations to skip"),
    correlation_type: Optional[str] = Query(None, description="Filter by correlation type"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity"),
    confidence_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence score"),
    time_range: Optional[str] = Query("24h", description="Time range for correlations"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get active threat correlations with advanced filtering.
    
    Args:
        limit: Maximum number of correlations to return
        offset: Number of correlations to skip
        correlation_type: Filter by type (temporal, spatial, behavioral, contextual, tactical)
        severity_filter: Filter by severity (critical, high, medium, low)
        confidence_threshold: Minimum confidence score
        time_range: Time range filter (1h, 24h, 7d, 30d)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Active threat correlations with detailed analysis
    """
    try:
        siem_service = get_siem_service()
        redis_client = get_redis_client()
        
        # Calculate time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)
        
        # Get cached correlations
        cache_key = f"threat_correlations:{correlation_type or 'all'}:{severity_filter or 'all'}:{confidence_threshold}:{time_range}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            import json
            correlations_data = json.loads(cached_data)
        else:
            # Generate threat correlations (this would be replaced with actual correlation engine)
            correlations_data = await _generate_threat_correlations(
                start_time, now, correlation_type, severity_filter, confidence_threshold
            )
            
            # Cache results
            import json
            await redis_client.setex(cache_key, 300, json.dumps(correlations_data, default=str))
        
        # Apply pagination
        total_correlations = len(correlations_data.get("correlations", []))
        paginated_correlations = correlations_data.get("correlations", [])[offset:offset + limit]
        
        return {
            "correlations": paginated_correlations,
            "total": total_correlations,
            "limit": limit,
            "offset": offset,
            "stats": correlations_data.get("stats", {}),
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "time_range": time_range,
                "confidence_threshold": confidence_threshold,
                "correlation_types": correlations_data.get("types", [])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving threat correlations: {str(e)}"
        )


@router.post("/correlations/rules", response_model=Dict[str, Any])
async def create_correlation_rule(
    rule_data: ThreatCorrelationRule = Body(...),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create new threat correlation rule (Admin only).
    
    Args:
        rule_data: Correlation rule configuration
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Created correlation rule
    """
    try:
        rule_id = str(uuid4())
        
        correlation_rule = {
            "id": rule_id,
            "name": rule_data.name,
            "description": rule_data.description,
            "rule_type": rule_data.rule_type,
            "conditions": rule_data.conditions,
            "severity": rule_data.severity,
            "confidence_threshold": rule_data.confidence_threshold,
            "time_window": rule_data.time_window,
            "enabled": rule_data.enabled,
            "created_by": current_user.username,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_triggered": None,
            "trigger_count": 0,
            "false_positive_count": 0,
            "accuracy_score": 0.0
        }
        
        # Store correlation rule
        redis_client = get_redis_client()
        await redis_client.setex(f"correlation_rule:{rule_id}", 86400, 
                                json.dumps(correlation_rule, default=str))
        
        # Add to active rules list
        await redis_client.sadd("active_correlation_rules", rule_id)
        
        return correlation_rule
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating correlation rule: {str(e)}"
        )


@router.get("/correlations/rules", response_model=List[Dict[str, Any]])
async def get_correlation_rules(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all threat correlation rules.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of correlation rules
    """
    try:
        redis_client = get_redis_client()
        
        # Get active rule IDs
        rule_ids = await redis_client.smembers("active_correlation_rules")
        
        rules = []
        for rule_id in rule_ids:
            rule_data = await redis_client.get(f"correlation_rule:{rule_id}")
            if rule_data:
                import json
                rules.append(json.loads(rule_data))
        
        return rules
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving correlation rules: {str(e)}"
        )


@router.post("/hunt", response_model=Dict[str, Any])
async def execute_threat_hunt(
    hunt_query: ThreatHuntQuery = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Execute threat hunting query across multiple data sources.
    
    Args:
        hunt_query: Threat hunting query configuration
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Threat hunting results with IOCs and behavioral patterns
    """
    try:
        hunt_id = str(uuid4())
        
        # Parse time range
        now = datetime.utcnow()
        if hunt_query.time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif hunt_query.time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif hunt_query.time_range == "7d":
            start_time = now - timedelta(days=7)
        elif hunt_query.time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)
        
        # Execute hunt across data sources
        hunt_results = await _execute_threat_hunt(
            hunt_query.query,
            hunt_query.data_sources,
            start_time,
            now,
            hunt_query.hunt_type,
            hunt_query.confidence_threshold
        )
        
        # Store hunt results
        hunt_session = {
            "id": hunt_id,
            "query": hunt_query.query,
            "hunt_type": hunt_query.hunt_type,
            "data_sources": hunt_query.data_sources,
            "time_range": hunt_query.time_range,
            "confidence_threshold": hunt_query.confidence_threshold,
            "started_at": start_time.isoformat(),
            "completed_at": now.isoformat(),
            "executed_by": current_user.username,
            "results": hunt_results,
            "status": "completed"
        }
        
        redis_client = get_redis_client()
        await redis_client.setex(f"hunt_session:{hunt_id}", 3600, 
                                json.dumps(hunt_session, default=str))
        
        return {
            "hunt_id": hunt_id,
            "status": "completed",
            "results": hunt_results,
            "metadata": {
                "execution_time": "2.3s",
                "data_sources_queried": len(hunt_query.data_sources),
                "total_events_analyzed": hunt_results.get("total_analyzed", 0),
                "indicators_found": len(hunt_results.get("indicators", [])),
                "behaviors_detected": len(hunt_results.get("behaviors", []))
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing threat hunt: {str(e)}"
        )


@router.post("/attack-path", response_model=Dict[str, Any])
async def analyze_attack_path(
    analysis_request: AttackPathAnalysis = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze attack paths and lateral movement patterns.
    
    Args:
        analysis_request: Attack path analysis configuration
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Attack path analysis with movement patterns and TTPs
    """
    try:
        analysis_id = str(uuid4())
        
        # Perform attack path analysis
        attack_path = await _analyze_attack_path(
            analysis_request.start_event_id,
            analysis_request.max_depth,
            analysis_request.time_window,
            analysis_request.include_lateral_movement,
            analysis_request.include_privilege_escalation
        )
        
        return {
            "analysis_id": analysis_id,
            "start_event_id": analysis_request.start_event_id,
            "attack_path": attack_path,
            "statistics": {
                "path_length": len(attack_path.get("events", [])),
                "unique_hosts": len(attack_path.get("affected_hosts", [])),
                "unique_users": len(attack_path.get("affected_users", [])),
                "privilege_escalations": len(attack_path.get("privilege_escalation_events", [])),
                "lateral_movements": len(attack_path.get("lateral_movement_events", [])),
                "attack_duration": attack_path.get("duration_minutes", 0),
                "mitre_techniques": attack_path.get("mitre_techniques", []),
                "risk_score": attack_path.get("risk_score", 0.0)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing attack path: {str(e)}"
        )


@router.post("/behavioral-profile", response_model=Dict[str, Any])
async def create_behavioral_profile(
    profile_request: BehavioralProfile = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create behavioral profile for entity (user, host, network, application).
    
    Args:
        profile_request: Behavioral profile configuration
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Behavioral profile with baselines and anomaly detection
    """
    try:
        profile_id = str(uuid4())
        
        # Generate behavioral profile
        behavioral_profile = await _generate_behavioral_profile(
            profile_request.entity_type,
            profile_request.entity_id,
            profile_request.profile_period,
            profile_request.include_baselines,
            profile_request.anomaly_detection
        )
        
        # Store profile
        profile_data = {
            "id": profile_id,
            "entity_type": profile_request.entity_type,
            "entity_id": profile_request.entity_id,
            "profile_period": profile_request.profile_period,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user.username,
            "profile": behavioral_profile
        }
        
        redis_client = get_redis_client()
        await redis_client.setex(f"behavioral_profile:{profile_id}", 86400, 
                                json.dumps(profile_data, default=str))
        
        return profile_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating behavioral profile: {str(e)}"
        )


@router.get("/mitre-mapping", response_model=Dict[str, Any])
async def get_mitre_attack_mapping(
    time_range: str = Query("7d", description="Time range for MITRE mapping"),
    include_subtechniques: bool = Query(True, description="Include sub-techniques"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get MITRE ATT&CK framework mapping for detected activities.
    
    Args:
        time_range: Time range for analysis (24h, 7d, 30d)
        include_subtechniques: Include sub-techniques in mapping
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        MITRE ATT&CK mapping with technique coverage and threat actor TTPs
    """
    try:
        # Get MITRE mapping from correlations and alerts
        mitre_mapping = await _generate_mitre_mapping(time_range, include_subtechniques)
        
        return {
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
            "mitre_version": "v12.1",
            "techniques": mitre_mapping.get("techniques", {}),
            "tactics": mitre_mapping.get("tactics", {}),
            "statistics": {
                "total_techniques_detected": len(mitre_mapping.get("techniques", {})),
                "total_tactics_covered": len(mitre_mapping.get("tactics", {})),
                "coverage_percentage": mitre_mapping.get("coverage_percentage", 0.0),
                "most_frequent_technique": mitre_mapping.get("most_frequent_technique", ""),
                "threat_actor_attribution": mitre_mapping.get("threat_actor_attribution", [])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating MITRE mapping: {str(e)}"
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_correlation_analytics(
    time_range: str = Query("7d", description="Time range for analytics"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get threat correlation analytics and insights.
    
    Args:
        time_range: Time range for analytics (24h, 7d, 30d)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Analytics dashboard with correlation insights and trends
    """
    try:
        analytics_data = await _generate_correlation_analytics(time_range)
        
        return {
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
            "correlation_metrics": analytics_data.get("correlation_metrics", {}),
            "detection_effectiveness": analytics_data.get("detection_effectiveness", {}),
            "false_positive_analysis": analytics_data.get("false_positive_analysis", {}),
            "trending_threats": analytics_data.get("trending_threats", []),
            "performance_metrics": analytics_data.get("performance_metrics", {}),
            "recommendations": analytics_data.get("recommendations", [])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating correlation analytics: {str(e)}"
        )


@router.get("/health")
async def threat_correlation_health_check() -> Dict[str, str]:
    """
    Health check endpoint for threat correlation service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "threat_correlation",
        "timestamp": str(int(time.time()))
    }


# Helper functions

async def _generate_threat_correlations(start_time, end_time, correlation_type, severity_filter, confidence_threshold):
    """Generate threat correlations based on filters."""
    # This would implement actual correlation logic
    # For now, return sample structure
    return {
        "correlations": [
            {
                "id": f"corr-{uuid4().hex[:8]}",
                "correlation_type": "behavioral",
                "severity": "high",
                "confidence": 0.85,
                "title": "Suspicious login patterns detected",
                "description": "Multiple failed login attempts followed by successful authentication",
                "events": [
                    {"id": "evt-001", "type": "authentication", "timestamp": start_time.isoformat()},
                    {"id": "evt-002", "type": "authentication", "timestamp": end_time.isoformat()}
                ],
                "mitre_techniques": ["T1110", "T1078"],
                "affected_entities": ["user-john", "host-workstation-01"],
                "risk_score": 8.5,
                "created_at": datetime.utcnow().isoformat()
            }
        ],
        "stats": {
            "total_correlations": 1,
            "active_correlations": 1,
            "high_confidence": 1,
            "critical_correlations": 0,
            "by_type": {
                "temporal": 0,
                "spatial": 0,
                "behavioral": 1,
                "contextual": 0,
                "tactical": 0
            },
            "avg_confidence": 0.85,
            "processing_time": 1.2
        },
        "types": ["behavioral"]
    }


async def _execute_threat_hunt(query, data_sources, start_time, end_time, hunt_type, confidence_threshold):
    """Execute threat hunting query."""
    # This would implement actual threat hunting logic
    return {
        "indicators": [],
        "behaviors": [],
        "anomalies": [],
        "total_analyzed": 0,
        "execution_time": 2.3,
        "confidence_scores": []
    }


async def _analyze_attack_path(start_event_id, max_depth, time_window, include_lateral_movement, include_privilege_escalation):
    """Analyze attack paths and lateral movement."""
    # This would implement actual attack path analysis
    return {
        "events": [],
        "affected_hosts": [],
        "affected_users": [],
        "privilege_escalation_events": [],
        "lateral_movement_events": [],
        "duration_minutes": 0,
        "mitre_techniques": [],
        "risk_score": 0.0
    }


async def _generate_behavioral_profile(entity_type, entity_id, profile_period, include_baselines, anomaly_detection):
    """Generate behavioral profile for entity."""
    # This would implement actual behavioral profiling
    return {
        "baseline_behavior": {},
        "current_behavior": {},
        "anomalies": [],
        "risk_indicators": [],
        "confidence_score": 0.0
    }


async def _generate_mitre_mapping(time_range, include_subtechniques):
    """Generate MITRE ATT&CK mapping."""
    # This would implement actual MITRE mapping
    return {
        "techniques": {},
        "tactics": {},
        "coverage_percentage": 0.0,
        "most_frequent_technique": "",
        "threat_actor_attribution": []
    }


async def _generate_correlation_analytics(time_range):
    """Generate correlation analytics."""
    # This would implement actual analytics generation
    return {
        "correlation_metrics": {},
        "detection_effectiveness": {},
        "false_positive_analysis": {},
        "trending_threats": [],
        "performance_metrics": {},
        "recommendations": []
    }