"""
SIEM WebSocket endpoints for real-time event streaming.

This module provides WebSocket connections for real-time SIEM data streaming,
including security alerts, agent status updates, and threat intelligence feeds.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_user_from_token
from core.redis_client import get_redis_client
from services.siem_service import get_siem_service, SIEMServiceException
from models.database import User

logger = logging.getLogger(__name__)


class SIEMWebSocketManager:
    """
    WebSocket connection manager for SIEM real-time data streaming.
    
    Manages WebSocket connections and broadcasts SIEM events to connected clients
    based on their subscriptions and permissions.
    """
    
    def __init__(self):
        # Active connections by subscription type
        self.connections: Dict[str, Set[WebSocket]] = {
            "alerts": set(),
            "agents": set(), 
            "manager": set(),
            "threats": set(),
            "logs": set(),
            "correlations": set(),
            "all": set()
        }
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Redis client for pub/sub
        self.redis_client = get_redis_client()
        
        # SIEM service
        self.siem_service = get_siem_service()
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        
        logger.info("SIEM WebSocket Manager initialized")
    
    async def connect(self, websocket: WebSocket, user: User, subscriptions: List[str] = None):
        """
        Connect a WebSocket client with specified subscriptions.
        
        Args:
            websocket: WebSocket connection
            user: Authenticated user
            subscriptions: List of subscription types to subscribe to
        """
        await websocket.accept()
        
        # Default subscriptions
        if not subscriptions:
            subscriptions = ["alerts", "agents", "manager"]
        
        # Store connection info
        connection_id = str(uuid4())
        self.connection_info[websocket] = {
            "id": connection_id,
            "user_id": user.id,
            "user_role": user.role,
            "subscriptions": subscriptions,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        
        # Add to subscription groups
        for subscription in subscriptions:
            if subscription in self.connections:
                self.connections[subscription].add(websocket)
        
        # Add to all connections
        self.connections["all"].add(websocket)
        
        logger.info(f"WebSocket connected: user_id={user.id}, subscriptions={subscriptions}")
        
        # Send initial data
        await self._send_initial_data(websocket, subscriptions)
        
        # Start background monitoring for this connection
        task = asyncio.create_task(self._monitor_connection(websocket))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        # Remove from all subscription groups
        for subscription_set in self.connections.values():
            subscription_set.discard(websocket)
        
        # Remove connection info
        connection_info = self.connection_info.pop(websocket, {})
        
        logger.info(f"WebSocket disconnected: connection_id={connection_info.get('id', 'unknown')}")
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """
        Broadcast security alert to subscribed clients.
        
        Args:
            alert_data: Alert data to broadcast
        """
        message = {
            "type": "alert",
            "timestamp": datetime.utcnow().isoformat(),
            "data": alert_data
        }
        
        await self._broadcast_to_subscription("alerts", message)
        
        # Also broadcast critical alerts to all connections
        if alert_data.get("severity") == "critical":
            await self._broadcast_to_subscription("all", {
                **message,
                "type": "critical_alert"
            })
    
    async def broadcast_agent_update(self, agent_data: Dict[str, Any]):
        """
        Broadcast agent status update to subscribed clients.
        
        Args:
            agent_data: Agent data to broadcast
        """
        message = {
            "type": "agent_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": agent_data
        }
        
        await self._broadcast_to_subscription("agents", message)
    
    async def broadcast_manager_update(self, manager_data: Dict[str, Any]):
        """
        Broadcast manager status update to subscribed clients.
        
        Args:
            manager_data: Manager data to broadcast
        """
        message = {
            "type": "manager_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": manager_data
        }
        
        await self._broadcast_to_subscription("manager", message)
    
    async def broadcast_threat_intel(self, threat_data: Dict[str, Any]):
        """
        Broadcast threat intelligence update to subscribed clients.
        
        Args:
            threat_data: Threat intelligence data to broadcast
        """
        message = {
            "type": "threat_intel",
            "timestamp": datetime.utcnow().isoformat(),
            "data": threat_data
        }
        
        await self._broadcast_to_subscription("threats", message)
    
    async def broadcast_log_event(self, log_data: Dict[str, Any]):
        """
        Broadcast log event to subscribed clients.
        
        Args:
            log_data: Log event data to broadcast
        """
        message = {
            "type": "log_event",
            "timestamp": datetime.utcnow().isoformat(),
            "data": log_data
        }
        
        await self._broadcast_to_subscription("logs", message)
    
    async def broadcast_correlation(self, correlation_data: Dict[str, Any]):
        """
        Broadcast threat correlation to subscribed clients.
        
        Args:
            correlation_data: Correlation data to broadcast
        """
        message = {
            "type": "correlation",
            "timestamp": datetime.utcnow().isoformat(),
            "data": correlation_data
        }
        
        await self._broadcast_to_subscription("correlations", message)
    
    async def _broadcast_to_subscription(self, subscription: str, message: Dict[str, Any]):
        """
        Broadcast message to all clients subscribed to a specific type.
        
        Args:
            subscription: Subscription type
            message: Message to broadcast
        """
        if subscription not in self.connections:
            return
        
        # Create list of connections to avoid modification during iteration
        connections = list(self.connections[subscription])
        
        for websocket in connections:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    # Update last activity
                    if websocket in self.connection_info:
                        self.connection_info[websocket]["last_activity"] = datetime.utcnow()
                    
                    await websocket.send_json(message)
                else:
                    # Remove disconnected websocket
                    await self.disconnect(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                await self.disconnect(websocket)
    
    async def _send_initial_data(self, websocket: WebSocket, subscriptions: List[str]):
        """
        Send initial data to newly connected client.
        
        Args:
            websocket: WebSocket connection
            subscriptions: List of subscriptions
        """
        try:
            # Send welcome message
            await websocket.send_json({
                "type": "welcome",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "subscriptions": subscriptions,
                    "connection_id": self.connection_info[websocket]["id"]
                }
            })
            
            # Send initial data for each subscription
            if "manager" in subscriptions:
                manager_status = await self.siem_service.get_wazuh_manager_status(use_cache=True)
                await websocket.send_json({
                    "type": "manager_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": manager_status
                })
            
            if "agents" in subscriptions:
                agents_data = await self.siem_service.get_wazuh_agents(limit=10, use_cache=True)
                await websocket.send_json({
                    "type": "agent_summary",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "total": agents_data.get("total", 0),
                        "active": len([a for a in agents_data.get("agents", []) if a.get("status") == "active"])
                    }
                })
            
            if "alerts" in subscriptions:
                alerts_data = await self.siem_service.get_security_alerts(limit=5, time_range="24h")
                await websocket.send_json({
                    "type": "recent_alerts",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "total": alerts_data.get("total", 0),
                        "recent": alerts_data.get("alerts", [])[:3]
                    }
                })
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def _monitor_connection(self, websocket: WebSocket):
        """
        Monitor WebSocket connection and send periodic updates.
        
        Args:
            websocket: WebSocket connection to monitor
        """
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30)
                
                if websocket in self.connection_info:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "server_time": datetime.utcnow().isoformat(),
                            "connection_id": self.connection_info[websocket]["id"]
                        }
                    })
        except Exception as e:
            logger.error(f"Error in connection monitoring: {e}")
        finally:
            await self.disconnect(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection statistics.
        
        Returns:
            Connection statistics
        """
        return {
            "total_connections": len(self.connections["all"]),
            "connections_by_subscription": {
                sub: len(conns) for sub, conns in self.connections.items() if sub != "all"
            },
            "active_users": len(set(
                info["user_id"] for info in self.connection_info.values()
            ))
        }


# Global WebSocket manager instance
siem_ws_manager = SIEMWebSocketManager()


# Create router
router = APIRouter(prefix="/ws/siem", tags=["SIEM WebSocket"])


@router.websocket("/stream")
async def siem_websocket_endpoint(
    websocket: WebSocket,
    token: str = None,
    subscriptions: str = "alerts,agents,manager"
):
    """
    WebSocket endpoint for real-time SIEM data streaming.
    
    Args:
        websocket: WebSocket connection
        token: Authentication token
        subscriptions: Comma-separated list of subscription types
    """
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user = await get_current_user_from_token(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        # Parse subscriptions
        subscription_list = [s.strip() for s in subscriptions.split(",") if s.strip()]
        valid_subscriptions = ["alerts", "agents", "manager", "threats", "logs", "correlations"]
        subscription_list = [s for s in subscription_list if s in valid_subscriptions]
        
        if not subscription_list:
            subscription_list = ["alerts", "agents", "manager"]
        
        # Connect to WebSocket manager
        await siem_ws_manager.connect(websocket, user, subscription_list)
        
        # Handle incoming messages
        while True:
            try:
                # Wait for messages from client
                message = await websocket.receive_json()
                
                # Handle client messages
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "subscribe":
                    # Handle subscription changes
                    new_subs = message.get("subscriptions", [])
                    # Update subscriptions (implementation would go here)
                    pass
                elif message.get("type") == "unsubscribe":
                    # Handle unsubscription
                    remove_subs = message.get("subscriptions", [])
                    # Remove subscriptions (implementation would go here)
                    pass
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass
    finally:
        await siem_ws_manager.disconnect(websocket)


@router.websocket("/alerts")
async def alerts_websocket_endpoint(
    websocket: WebSocket,
    token: str = None
):
    """
    WebSocket endpoint specifically for security alerts.
    
    Args:
        websocket: WebSocket connection
        token: Authentication token
    """
    try:
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user = await get_current_user_from_token(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        await siem_ws_manager.connect(websocket, user, ["alerts"])
        
        while True:
            try:
                message = await websocket.receive_json()
                
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in alerts WebSocket: {e}")
                break
    
    except Exception as e:
        logger.error(f"Alerts WebSocket connection error: {e}")
    finally:
        await siem_ws_manager.disconnect(websocket)


@router.get("/connections/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    Get WebSocket connection statistics (Admin only).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        WebSocket connection statistics
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return siem_ws_manager.get_connection_stats()


# Background task for simulating real-time events (for development/testing)
async def simulate_siem_events():
    """
    Simulate SIEM events for testing WebSocket functionality.
    This would be replaced with actual event listeners in production.
    """
    while True:
        try:
            await asyncio.sleep(10)  # Wait 10 seconds between simulated events
            
            # Simulate different types of events
            import random
            
            event_type = random.choice(["alert", "agent_update", "manager_update"])
            
            if event_type == "alert":
                # Simulate alert
                alert_data = {
                    "id": f"alert-{uuid4().hex[:8]}",
                    "title": "Simulated Security Alert",
                    "severity": random.choice(["critical", "high", "medium", "low"]),
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_name": f"agent-{random.randint(1, 10)}"
                }
                await siem_ws_manager.broadcast_alert(alert_data)
            
            elif event_type == "agent_update":
                # Simulate agent status change
                agent_data = {
                    "id": f"agent-{random.randint(1, 10)}",
                    "name": f"agent-{random.randint(1, 10)}",
                    "status": random.choice(["active", "disconnected"]),
                    "last_seen": datetime.utcnow().isoformat()
                }
                await siem_ws_manager.broadcast_agent_update(agent_data)
            
            elif event_type == "manager_update":
                # Simulate manager status update
                manager_data = {
                    "status": "online",
                    "cpu_usage": random.randint(20, 80),
                    "memory_usage": random.randint(30, 90),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await siem_ws_manager.broadcast_manager_update(manager_data)
                
        except Exception as e:
            logger.error(f"Error in SIEM event simulation: {e}")
            await asyncio.sleep(5)  # Wait before retrying


# Start background simulation task (for development)
# In production, this would be replaced with actual event listeners
# asyncio.create_task(simulate_siem_events())