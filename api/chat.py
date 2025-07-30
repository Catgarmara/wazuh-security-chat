"""
Chat API endpoints for session and message management.

This module provides REST API endpoints for chat session management,
message history retrieval, and conversation context handling.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user
from services.chat_service import get_chat_service
from models.database import User
from models.schemas import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    MessageResponse, PaginatedResponse, PaginationParams
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user)
) -> ChatSessionResponse:
    """
    Create a new chat session for the current user.
    
    Args:
        session_data: Session creation data
        current_user: Current authenticated user
        
    Returns:
        Created chat session
    """
    try:
        chat_service = get_chat_service()
        session = chat_service.create_chat_session(
            user_id=current_user.id,
            title=session_data.title
        )
        
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            message_count=0
        )
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    include_inactive: bool = Query(False, description="Include inactive sessions"),
    current_user: User = Depends(get_current_active_user)
) -> List[ChatSessionResponse]:
    """
    Get all chat sessions for the current user.
    
    Args:
        include_inactive: Whether to include inactive sessions
        current_user: Current authenticated user
        
    Returns:
        List of user's chat sessions
    """
    try:
        chat_service = get_chat_service()
        sessions = chat_service.get_user_sessions(
            user_id=current_user.id,
            include_inactive=include_inactive
        )
        
        # Convert to response format with message counts
        response_sessions = []
        for session in sessions:
            # Get message count for each session
            messages = chat_service.get_session_messages(
                session_id=session.id,
                user_id=current_user.id,
                limit=1000  # Get all messages to count
            )
            
            response_sessions.append(ChatSessionResponse(
                id=session.id,
                user_id=session.user_id,
                title=session.title,
                is_active=session.is_active,
                created_at=session.created_at,
                updated_at=session.updated_at,
                ended_at=session.ended_at,
                message_count=len(messages)
            ))
        
        return response_sessions
        
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user)
) -> ChatSessionResponse:
    """
    Get a specific chat session by ID.
    
    Args:
        session_id: Session ID to retrieve
        current_user: Current authenticated user
        
    Returns:
        Chat session details
    """
    try:
        chat_service = get_chat_service()
        session = chat_service.get_session_by_id(session_id, current_user.id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get message count
        messages = chat_service.get_session_messages(
            session_id=session.id,
            user_id=current_user.id,
            limit=1000
        )
        
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            message_count=len(messages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: UUID,
    session_data: ChatSessionUpdate,
    current_user: User = Depends(get_current_active_user)
) -> ChatSessionResponse:
    """
    Update a chat session.
    
    Args:
        session_id: Session ID to update
        session_data: Session update data
        current_user: Current authenticated user
        
    Returns:
        Updated chat session
    """
    try:
        chat_service = get_chat_service()
        session = chat_service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            title=session_data.title,
            is_active=session_data.is_active
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get message count
        messages = chat_service.get_session_messages(
            session_id=session.id,
            user_id=current_user.id,
            limit=1000
        )
        
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            message_count=len(messages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session"
        )


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    """
    End (deactivate) a chat session.
    
    Args:
        session_id: Session ID to end
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        chat_service = get_chat_service()
        success = chat_service.end_session(session_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {"message": "Session ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_active_user)
) -> List[MessageResponse]:
    """
    Get messages from a chat session.
    
    Args:
        session_id: Session ID to get messages from
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        current_user: Current authenticated user
        
    Returns:
        List of messages from the session
    """
    try:
        chat_service = get_chat_service()
        messages = chat_service.get_session_messages(
            session_id=session_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return [
            MessageResponse(
                id=message.id,
                session_id=message.session_id,
                role=message.role,
                content=message.content,
                message_metadata=message.message_metadata,
                timestamp=message.timestamp
            )
            for message in messages
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving messages from session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.get("/sessions/{session_id}/context")
async def get_conversation_context(
    session_id: UUID,
    max_messages: int = Query(10, ge=1, le=50, description="Maximum number of recent messages"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get conversation context for AI processing.
    
    Args:
        session_id: Session ID to get context from
        max_messages: Maximum number of recent messages to include
        current_user: Current authenticated user
        
    Returns:
        Conversation context data
    """
    try:
        chat_service = get_chat_service()
        context = chat_service.get_conversation_context(
            session_id=session_id,
            user_id=current_user.id,
            max_messages=max_messages
        )
        
        return {
            "session_id": str(session_id),
            "context": context,
            "message_count": len(context)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving context for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation context"
        )


@router.post("/sessions/cleanup")
async def cleanup_old_sessions(
    days_old: int = Query(30, ge=1, le=365, description="Age in days for session cleanup"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Clean up old inactive sessions (Admin only).
    
    Args:
        days_old: Number of days after which to clean up sessions
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Cleanup results
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        chat_service = get_chat_service()
        cleaned_count = chat_service.cleanup_old_sessions(days_old)
        
        return {
            "message": f"Cleaned up {cleaned_count} old sessions",
            "sessions_cleaned": cleaned_count,
            "days_old": days_old
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup old sessions"
        )