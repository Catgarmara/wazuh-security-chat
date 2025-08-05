"""
SIEM Service Layer

Provides centralized data management and business logic for SIEM operations,
including Wazuh integration, alert management, and threat correlation.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

import aiohttp
import redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from core.config import get_settings
from core.redis_client import get_redis_client
from core.exceptions import WazuhChatException
from models.database import User
from models.schemas import (
    SIEMAlert, SIEMAlertCreate, SIEMAlertUpdate,
    WazuhManager, WazuhAgent, WazuhRule,
    ThreatIntelligence, LogEvent, AlertWorkflow,
    CorrelationRule, ThreatCorrelation
)

logger = logging.getLogger(__name__)


class SIEMServiceException(WazuhChatException):
    """Exception raised by SIEM service operations."""
    pass


class SIEMService:
    """
    SIEM Service for managing security information and event management operations.
    
    Provides comprehensive SIEM functionality including:
    - Wazuh manager and agent monitoring
    - Security alert management
    - Threat intelligence integration
    - Log analysis and correlation
    - Real-time event streaming
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis_client()
        self.logger = logger
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        self.manager_cache_key = "siem:manager:status"
        self.agents_cache_key = "siem:agents:list"
        self.alerts_cache_key = "siem:alerts:active"
        
        # Wazuh API settings
        self.wazuh_api_url = self.settings.wazuh_api_url or "https://localhost:55000"
        self.wazuh_api_user = self.settings.wazuh_api_user or "wazuh"
        self.wazuh_api_password = self.settings.wazuh_api_password or "wazuh"
        
    async def get_wazuh_manager_status(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get Wazuh manager status and performance metrics.
        
        Args:
            use_cache: Whether to use cached data
            
        Returns:
            Manager status data
        """
        if use_cache:
            cached_data = await self._get_cached_data(self.manager_cache_key)
            if cached_data:
                return cached_data
        
        try:
            # Get manager status from Wazuh API
            async with aiohttp.ClientSession() as session:
                # Authenticate with Wazuh API
                auth_token = await self._authenticate_wazuh_api(session)
                
                # Get manager information
                manager_info = await self._call_wazuh_api(
                    session, "/manager/info", auth_token
                )
                
                # Get manager status
                manager_status = await self._call_wazuh_api(
                    session, "/manager/status", auth_token
                )
                
                # Get manager stats
                manager_stats = await self._call_wazuh_api(
                    session, "/manager/stats", auth_token
                )
                
                # Get cluster info if available
                cluster_info = await self._call_wazuh_api(
                    session, "/cluster/status", auth_token, ignore_errors=True
                )
                
                # Combine data
                status_data = {
                    "status": "online" if manager_status.get("status") == "running" else "offline",
                    "version": manager_info.get("version", "unknown"),
                    "uptime": self._calculate_uptime(manager_stats.get("start_time")),
                    "last_restart": manager_stats.get("start_time"),
                    "cluster_mode": cluster_info is not None and cluster_info.get("enabled", False),
                    "cluster_nodes": cluster_info.get("node_count", 0) if cluster_info else 0,
                    "configuration": {
                        "rules_loaded": manager_stats.get("total_rules", 0),
                        "decoders_loaded": manager_stats.get("total_decoders", 0),
                        "cdb_lists": manager_stats.get("total_cdb_lists", 0),
                        "log_level": manager_info.get("log_level", "info")
                    },
                    "performance": {
                        "events_received": manager_stats.get("events_received", 0),
                        "events_processed": manager_stats.get("events_processed", 0),
                        "events_dropped": manager_stats.get("events_dropped", 0),
                        "average_processing_time": manager_stats.get("avg_processing_time", 0.0),
                        "queue_usage": manager_stats.get("queue_usage_percentage", 0)
                    },
                    "modules": {
                        "vulnerability_detection": manager_info.get("modules", {}).get("vulnerability_detection", False),
                        "osquery": manager_info.get("modules", {}).get("osquery", False),
                        "syscollector": manager_info.get("modules", {}).get("syscollector", False),
                        "sca": manager_info.get("modules", {}).get("sca", False),
                        "rootcheck": manager_info.get("modules", {}).get("rootcheck", False),
                        "file_integrity": manager_info.get("modules", {}).get("fim", False),
                        "log_analysis": manager_info.get("modules", {}).get("logcollector", False),
                        "active_response": manager_info.get("modules", {}).get("active_response", False)
                    }
                }
                
                # Cache the result
                await self._cache_data(self.manager_cache_key, status_data)
                
                return status_data
                
        except Exception as e:
            self.logger.error(f"Error getting Wazuh manager status: {e}")
            # Return fallback data
            return {
                "status": "offline",
                "version": "unknown",
                "uptime": "0 days, 0 hours, 0 minutes",
                "last_restart": datetime.utcnow().isoformat(),
                "cluster_mode": False,
                "cluster_nodes": 0,
                "configuration": {
                    "rules_loaded": 0,
                    "decoders_loaded": 0,
                    "cdb_lists": 0,
                    "log_level": "unknown"
                },
                "performance": {
                    "events_received": 0,
                    "events_processed": 0,
                    "events_dropped": 0,
                    "average_processing_time": 0.0,
                    "queue_usage": 0
                },
                "modules": {}
            }
    
    async def get_wazuh_agents(self, 
                              limit: int = 500, 
                              offset: int = 0,
                              search: Optional[str] = None,
                              status_filter: Optional[str] = None,
                              use_cache: bool = True) -> Dict[str, Any]:
        """
        Get Wazuh agents with filtering and pagination.
        
        Args:
            limit: Maximum number of agents to return
            offset: Number of agents to skip
            search: Search query for agent names/IPs
            status_filter: Filter by agent status
            use_cache: Whether to use cached data
            
        Returns:
            Agents data with pagination info
        """
        cache_key = f"{self.agents_cache_key}:{limit}:{offset}:{search or ''}:{status_filter or ''}"
        
        if use_cache:
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
        
        try:
            async with aiohttp.ClientSession() as session:
                auth_token = await self._authenticate_wazuh_api(session)
                
                # Build query parameters
                params = {
                    "limit": limit,
                    "offset": offset
                }
                
                if search:
                    params["search"] = search
                if status_filter:
                    params["status"] = status_filter
                
                # Get agents from Wazuh API
                agents_response = await self._call_wazuh_api(
                    session, "/agents", auth_token, params=params
                )
                
                agents_data = agents_response.get("data", {})
                agents = agents_data.get("affected_items", [])
                
                # Transform agent data
                transformed_agents = []
                for agent in agents:
                    transformed_agents.append({
                        "id": agent.get("id"),
                        "name": agent.get("name"),
                        "ip_address": agent.get("ip"),
                        "os": agent.get("os", {}).get("name", "unknown"),
                        "os_platform": agent.get("os", {}).get("platform", "unknown"),
                        "os_version": agent.get("os", {}).get("version", "unknown"),
                        "version": agent.get("version", "unknown"),
                        "status": self._map_agent_status(agent.get("status")),
                        "last_keep_alive": agent.get("last_keep_alive"),
                        "registration_date": agent.get("date_add"),
                        "groups": agent.get("group", []),
                        "node_name": agent.get("node_name", "unknown"),
                        "manager_host": agent.get("manager"),
                        "config_sum": agent.get("config_sum", ""),
                        "merged_sum": agent.get("merged_sum", ""),
                        "sync_status": "synced" if agent.get("sync_status") == "synced" else "not_synced"
                    })
                
                result = {
                    "agents": transformed_agents,
                    "total": agents_data.get("total_affected_items", 0),
                    "limit": limit,
                    "offset": offset
                }
                
                # Cache the result
                await self._cache_data(cache_key, result, ttl=60)  # Short cache for agents
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error getting Wazuh agents: {e}")
            return {
                "agents": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
    
    async def get_security_alerts(self,
                                 limit: int = 100,
                                 offset: int = 0,
                                 severity_filter: Optional[str] = None,
                                 status_filter: Optional[str] = None,
                                 time_range: Optional[str] = None,
                                 search: Optional[str] = None) -> Dict[str, Any]:
        """
        Get security alerts with filtering and pagination.
        
        Args:
            limit: Maximum number of alerts to return
            offset: Number of alerts to skip
            severity_filter: Filter by alert severity
            status_filter: Filter by alert status
            time_range: Time range filter (24h, 7d, 30d)
            search: Search query
            
        Returns:
            Alerts data with pagination info
        """
        try:
            async with aiohttp.ClientSession() as session:
                auth_token = await self._authenticate_wazuh_api(session)
                
                # Calculate time range
                time_from = None
                if time_range:
                    if time_range == "24h":
                        time_from = datetime.utcnow() - timedelta(hours=24)
                    elif time_range == "7d":
                        time_from = datetime.utcnow() - timedelta(days=7)
                    elif time_range == "30d":
                        time_from = datetime.utcnow() - timedelta(days=30)
                
                # Build query parameters
                params = {
                    "limit": limit,
                    "offset": offset,
                    "sort": "-timestamp"
                }
                
                if time_from:
                    params["timestamp"] = f">{time_from.isoformat()}Z"
                if search:
                    params["search"] = search
                
                # Get alerts from Wazuh API
                alerts_response = await self._call_wazuh_api(
                    session, "/security_events", auth_token, params=params
                )
                
                alerts_data = alerts_response.get("data", {})
                alerts = alerts_data.get("affected_items", [])
                
                # Transform alert data
                transformed_alerts = []
                for alert in alerts:
                    rule = alert.get("rule", {})
                    agent = alert.get("agent", {})
                    
                    transformed_alert = {
                        "id": f"alert-{alert.get('id', uuid4().hex[:8])}",
                        "rule_id": rule.get("id"),
                        "rule_description": rule.get("description", "Unknown rule"),
                        "severity": self._map_alert_severity(rule.get("level", 0)),
                        "status": "open",  # Default status
                        "timestamp": alert.get("timestamp"),
                        "agent_id": agent.get("id"),
                        "agent_name": agent.get("name"),
                        "source_ip": alert.get("data", {}).get("srcip"),
                        "destination_ip": alert.get("data", {}).get("dstip"),
                        "user": alert.get("data", {}).get("srcuser"),
                        "process": alert.get("data", {}).get("process"),
                        "file_path": alert.get("data", {}).get("path"),
                        "command": alert.get("data", {}).get("command"),
                        "category": rule.get("groups", [None])[0] if rule.get("groups") else "Unknown",
                        "mitre_technique": rule.get("mitre", {}).get("technique", [None])[0] if rule.get("mitre") else None,
                        "mitre_tactic": rule.get("mitre", {}).get("tactic", [None])[0] if rule.get("mitre") else None,
                        "event_count": 1,
                        "raw_log": alert.get("full_log", "")
                    }
                    
                    # Apply filters
                    if severity_filter and transformed_alert["severity"] != severity_filter:
                        continue
                    if status_filter and transformed_alert["status"] != status_filter:
                        continue
                    
                    transformed_alerts.append(transformed_alert)
                
                return {
                    "alerts": transformed_alerts,
                    "total": len(transformed_alerts),
                    "limit": limit,
                    "offset": offset
                }
                
        except Exception as e:
            self.logger.error(f"Error getting security alerts: {e}")
            return {
                "alerts": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
    
    async def get_threat_intelligence(self,
                                    limit: int = 100,
                                    offset: int = 0,
                                    threat_type: Optional[str] = None,
                                    severity_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get threat intelligence indicators.
        
        Args:
            limit: Maximum number of indicators to return
            offset: Number of indicators to skip
            threat_type: Filter by threat type
            severity_filter: Filter by severity
            
        Returns:
            Threat intelligence data
        """
        # This would integrate with external threat intelligence feeds
        # For now, return mock data structure
        return {
            "indicators": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "feeds": [
                {
                    "name": "AlienVault OTX",
                    "status": "online",
                    "last_update": datetime.utcnow().isoformat(),
                    "indicators_count": 0
                }
            ]
        }
    
    async def get_log_events(self,
                           limit: int = 100,
                           offset: int = 0,
                           level_filter: Optional[str] = None,
                           source_filter: Optional[str] = None,
                           time_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Get log events with filtering.
        
        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            level_filter: Filter by log level
            source_filter: Filter by log source
            time_range: Time range filter
            
        Returns:
            Log events data
        """
        try:
            async with aiohttp.ClientSession() as session:
                auth_token = await self._authenticate_wazuh_api(session)
                
                # Get logs from Wazuh API
                params = {
                    "limit": limit,
                    "offset": offset,
                    "sort": "-timestamp"
                }
                
                logs_response = await self._call_wazuh_api(
                    session, "/manager/logs", auth_token, params=params
                )
                
                logs_data = logs_response.get("data", {})
                logs = logs_data.get("affected_items", [])
                
                # Transform log data
                transformed_logs = []
                for log in logs:
                    transformed_logs.append({
                        "id": f"log-{uuid4().hex[:8]}",
                        "timestamp": log.get("timestamp"),
                        "level": log.get("level", "info").lower(),
                        "source": "wazuh",
                        "message": log.get("description", ""),
                        "raw_log": log.get("message", ""),
                        "parsed_fields": {},
                        "classification": "System Information",
                        "tags": ["wazuh", "manager"],
                        "event_count": 1
                    })
                
                return {
                    "logs": transformed_logs,
                    "total": len(transformed_logs),
                    "limit": limit,
                    "offset": offset,
                    "stats": {
                        "by_level": {"info": len(transformed_logs), "error": 0, "warning": 0},
                        "by_source": {"wazuh": len(transformed_logs)},
                        "trends": {"last_hour": len(transformed_logs)}
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting log events: {e}")
            return {
                "logs": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "stats": {"by_level": {}, "by_source": {}, "trends": {}}
            }
    
    async def create_alert_workflow(self, alert_id: str, workflow_type: str) -> Dict[str, Any]:
        """
        Create an alert management workflow.
        
        Args:
            alert_id: Alert ID to create workflow for
            workflow_type: Type of workflow to create
            
        Returns:
            Created workflow data
        """
        workflow_id = f"workflow-{uuid4().hex[:8]}"
        
        # Define workflow templates
        workflows = {
            "critical_malware": {
                "name": "Critical Malware Investigation",
                "description": "Comprehensive investigation workflow for critical malware alerts",
                "steps": [
                    {
                        "name": "Initial Alert Triage",
                        "description": "Review alert details and assess severity",
                        "action": "investigate",
                        "automated": False,
                        "required": True,
                        "estimated_time": 15
                    },
                    {
                        "name": "Isolate Affected System",
                        "description": "Isolate the affected system from network",
                        "action": "contain",
                        "automated": True,
                        "required": True,
                        "estimated_time": 5
                    }
                ]
            }
        }
        
        template = workflows.get(workflow_type, workflows["critical_malware"])
        
        workflow_data = {
            "id": workflow_id,
            "name": template["name"],
            "description": template["description"],
            "alert_id": alert_id,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "steps": template["steps"]
        }
        
        # Cache workflow data
        await self._cache_data(f"workflow:{workflow_id}", workflow_data, ttl=3600)
        
        return workflow_data
    
    async def get_threat_correlations(self,
                                    limit: int = 50,
                                    offset: int = 0,
                                    correlation_type: Optional[str] = None,
                                    severity_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get threat correlations and attack patterns.
        
        Args:
            limit: Maximum number of correlations to return
            offset: Number of correlations to skip
            correlation_type: Filter by correlation type
            severity_filter: Filter by severity
            
        Returns:
            Threat correlations data
        """
        # This would implement advanced correlation logic
        # For now, return structure for frontend integration
        return {
            "correlations": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "stats": {
                "total_correlations": 0,
                "active_correlations": 0,
                "high_confidence": 0,
                "critical_correlations": 0,
                "by_type": {
                    "temporal": 0,
                    "spatial": 0,
                    "behavioral": 0,
                    "contextual": 0,
                    "tactical": 0
                },
                "avg_confidence": 0.0,
                "processing_time": 0.0
            }
        }
    
    # Private helper methods
    
    async def _authenticate_wazuh_api(self, session: aiohttp.ClientSession) -> str:
        """Authenticate with Wazuh API and return token."""
        auth_url = f"{self.wazuh_api_url}/security/user/authenticate"
        
        async with session.post(
            auth_url,
            auth=aiohttp.BasicAuth(self.wazuh_api_user, self.wazuh_api_password),
            ssl=False  # For development - use proper SSL in production
        ) as response:
            if response.status != 200:
                raise SIEMServiceException("Failed to authenticate with Wazuh API")
            
            data = await response.json()
            return data.get("data", {}).get("token", "")
    
    async def _call_wazuh_api(self, 
                            session: aiohttp.ClientSession, 
                            endpoint: str, 
                            token: str,
                            params: Optional[Dict] = None,
                            ignore_errors: bool = False) -> Dict[str, Any]:
        """Make authenticated call to Wazuh API."""
        url = f"{self.wazuh_api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with session.get(url, headers=headers, params=params, ssl=False) as response:
                if response.status != 200:
                    if ignore_errors:
                        return {}
                    raise SIEMServiceException(f"Wazuh API call failed: {response.status}")
                
                return await response.json()
        except Exception as e:
            if ignore_errors:
                return {}
            raise SIEMServiceException(f"Wazuh API call error: {e}")
    
    async def _cache_data(self, key: str, data: Any, ttl: int = None) -> None:
        """Cache data in Redis."""
        try:
            await self.redis_client.setex(
                key, 
                ttl or self.cache_ttl, 
                json.dumps(data, default=str)
            )
        except Exception as e:
            self.logger.warning(f"Failed to cache data: {e}")
    
    async def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data from Redis."""
        try:
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            self.logger.warning(f"Failed to get cached data: {e}")
        return None
    
    def _calculate_uptime(self, start_time: Optional[str]) -> str:
        """Calculate uptime from start time."""
        if not start_time:
            return "Unknown"
        
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            delta = datetime.utcnow() - start.replace(tzinfo=None)
            
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            return f"{days} days, {hours} hours, {minutes} minutes"
        except:
            return "Unknown"
    
    def _map_agent_status(self, status: str) -> str:
        """Map Wazuh agent status to standard format."""
        status_map = {
            "active": "active",
            "disconnected": "disconnected",
            "never_connected": "never_connected",
            "pending": "pending"
        }
        return status_map.get(status, "disconnected")
    
    def _map_alert_severity(self, level: int) -> str:
        """Map Wazuh rule level to severity."""
        if level >= 12:
            return "critical"
        elif level >= 7:
            return "high"
        elif level >= 4:
            return "medium"
        else:
            return "low"


# Singleton instance
_siem_service = None

def get_siem_service() -> SIEMService:
    """Get SIEM service instance."""
    global _siem_service
    if _siem_service is None:
        _siem_service = SIEMService()
    return _siem_service