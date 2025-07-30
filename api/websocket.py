"""
WebSocket API endpoints for real-time chat communication.

This module provides WebSocket endpoints for chat functionality,
including connection management, authentication, and message handling.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.security import HTTPBearer

from services.chat_service import get_chat_service

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
    WebSocket endpoint for real-time chat communication.
    
    This endpoint handles WebSocket connections for chat functionality,
    including user authentication, session management, and message processing.
    
    Args:
        websocket: WebSocket connection
        token: JWT authentication token (required)
        
    Message Types:
        - join_session: Join a specific chat session
        - chat_message: Send a chat message
        - ping: Heartbeat/keepalive message
        
    Response Types:
        - connection_established: Connection successful
        - session_joined: Successfully joined session
        - message: Chat message (user or assistant)
        - typing: Typing indicator
        - error: Error message
        - pong: Response to ping
    
    Example Usage:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/ws/chat?token=your_jwt_token');
        
        // Join a session
        ws.send(JSON.stringify({
            type: 'join_session',
            session_id: 'session-uuid'
        }));
        
        // Send a message
        ws.send(JSON.stringify({
            type: 'chat_message',
            message: 'Hello, AI assistant!'
        }));
        ```
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
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
    Get information about active WebSocket connections.
    
    Returns connection statistics including total connections,
    unique users, and active sessions.
    
    Returns:
        Dictionary with connection statistics
    """
    chat_service = get_chat_service()
    connection_manager = chat_service.get_connection_manager()
    return connection_manager.get_connection_info()