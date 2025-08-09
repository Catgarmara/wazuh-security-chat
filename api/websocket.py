"""
WebSocket API endpoints for real-time security analysis chat communication.

This module provides WebSocket endpoints for security-focused chat functionality,
including connection management, authentication, and real-time security analysis
using the embedded AI service for threat hunting and incident analysis.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.security import HTTPBearer

from services.chat_service import get_chat_service
from core.ai_factory import AIServiceFactory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Security scheme
security = HTTPBearer()


@router.websocket("/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time security analysis chat communication.
    
    This endpoint handles WebSocket connections for security-focused chat functionality,
    including user authentication, session management, and real-time security analysis
    using the embedded AI service for conversational threat hunting and incident analysis.
    
    Args:
        websocket: WebSocket connection
        token: JWT authentication token (required)
        
    Message Types:
        - join_session: Join a specific chat session
        - chat_message: Send a security analysis chat message
        - security_query: Send a specialized security query for threat hunting
        - ping: Heartbeat/keepalive message
        
    Response Types:
        - connection_established: Connection successful with AI service status
        - session_joined: Successfully joined session with security context
        - message: Chat message (user or security assistant)
        - security_analysis: Specialized security analysis response
        - typing: Typing indicator during AI processing
        - ai_status: Real-time AI service status updates
        - error: Error message
        - pong: Response to ping
    
    Security Features:
        - Real-time threat hunting assistance
        - Conversational incident analysis
        - SIEM query translation and optimization
        - Security context preservation across sessions
        - Embedded AI processing for data privacy
    
    Example Usage:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/ws/chat?token=your_jwt_token');
        
        // Join a session
        ws.send(JSON.stringify({
            type: 'join_session',
            session_id: 'session-uuid'
        }));
        
        // Send a security query
        ws.send(JSON.stringify({
            type: 'chat_message',
            message: 'Analyze suspicious login attempts from the last 24 hours'
        }));
        
        // Send specialized security query
        ws.send(JSON.stringify({
            type: 'security_query',
            query: 'Hunt for lateral movement indicators',
            context: 'incident_investigation'
        }));
        ```
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        return
    
    # Verify embedded AI service availability
    ai_service = AIServiceFactory.get_ai_service()
    if not ai_service:
        logger.warning("Embedded AI service not available for WebSocket connection")
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="AI service unavailable")
        return
    
    chat_service = get_chat_service()
    
    try:
        await chat_service.handle_websocket_connection(websocket, token)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
        except:
            pass


@router.get("/connections/info")
async def get_connection_info():
    """
    Get information about active WebSocket connections and AI service status.
    
    Returns connection statistics including total connections,
    unique users, active sessions, and embedded AI service status
    for real-time security analysis capabilities.
    
    Returns:
        Dictionary with connection statistics and AI service status
    """
    chat_service = get_chat_service()
    connection_manager = chat_service.get_connection_manager()
    connection_info = connection_manager.get_connection_info()
    
    # Add AI service status for security analysis capabilities
    ai_service = AIServiceFactory.get_ai_service()
    if ai_service:
        ai_status = ai_service.get_service_status()
        connection_info.update({
            "ai_service_ready": ai_status.get("service_ready", False),
            "loaded_models": ai_status.get("loaded_models", 0),
            "active_model": ai_status.get("active_model"),
            "conversation_sessions": ai_status.get("conversation_sessions", 0)
        })
    else:
        connection_info.update({
            "ai_service_ready": False,
            "loaded_models": 0,
            "active_model": None,
            "conversation_sessions": 0
        })
    
    return connection_info


@router.get("/ai/status")
async def get_ai_service_status():
    """
    Get detailed embedded AI service status for real-time security analysis.
    
    Returns comprehensive status information about the embedded AI service
    including model availability, system resources, and security analysis capabilities.
    
    Returns:
        Dictionary with detailed AI service status
    """
    ai_service = AIServiceFactory.get_ai_service()
    if not ai_service:
        return {
            "service_available": False,
            "error": "Embedded AI service not initialized"
        }
    
    try:
        status = ai_service.get_service_status()
        status["service_available"] = True
        return status
    except Exception as e:
        logger.error(f"Error getting AI service status: {e}")
        return {
            "service_available": False,
            "error": str(e)
        }