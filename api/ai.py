"""
AI Service Management API endpoints.

This module provides REST API endpoints for AI service management,
vector store operations, and LLM configuration.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from services.ai_service import AIService
from services.log_service import LogService
from models.database import User
from models.schemas import DateRange

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ai", tags=["AI Service Management"])


def get_ai_service() -> AIService:
    """Get AI service instance."""
    return AIService()


def get_log_service() -> LogService:
    """Get log service instance."""
    return LogService()


@router.get("/health")
async def ai_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get AI service health status.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        AI service health status information
    """
    try:
        ai_service = get_ai_service()
        
        # Check LLM health
        llm_health = ai_service.check_llm_health()
        
        # Get vector store info
        vectorstore_info = ai_service.get_vectorstore_info()
        
        # Get service configuration
        config = ai_service.get_llm_config()
        
        return {
            "status": "healthy" if ai_service.is_ready() else "unhealthy",
            "service": "ai_management",
            "timestamp": datetime.now().isoformat(),
            "llm_health": llm_health,
            "vectorstore_info": vectorstore_info,
            "configuration": config,
            "ready": ai_service.is_ready()
        }
        
    except Exception as e:
        logger.error(f"Error checking AI service health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check AI service health"
        )


@router.get("/vectorstore/info")
async def get_vectorstore_info(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get information about the current vector store.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Vector store information
    """
    try:
        ai_service = get_ai_service()
        vectorstore_info = ai_service.get_vectorstore_info()
        
        return {
            "vectorstore_info": vectorstore_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving vector store info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vector store info: {str(e)}"
        )


@router.get("/vectorstore/list")
async def list_saved_vectorstores(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    List all saved vector stores.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of saved vector stores with metadata
    """
    try:
        ai_service = get_ai_service()
        vectorstores = ai_service.list_saved_vectorstores()
        
        return {
            "vectorstores": vectorstores,
            "total_count": len(vectorstores),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing vector stores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list vector stores: {str(e)}"
        )


@router.post("/vectorstore/save")
async def save_vectorstore(
    identifier: str = Query(..., description="Unique identifier for the vector store"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Save the current vector store to disk (Admin only).
    
    Args:
        identifier: Unique identifier for the vector store
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Save operation status
    """
    try:
        ai_service = get_ai_service()
        
        # Check if vector store exists
        vectorstore_info = ai_service.get_vectorstore_info()
        if vectorstore_info.get("status") != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No vector store available to save"
            )
        
        # Save vector store
        success = ai_service.save_vectorstore(identifier)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save vector store"
            )
        
        return {
            "message": f"Vector store saved successfully",
            "identifier": identifier,
            "saved_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
            "document_count": vectorstore_info.get("document_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving vector store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save vector store: {str(e)}"
        )


@router.post("/vectorstore/load")
async def load_vectorstore(
    identifier: str = Query(..., description="Unique identifier for the vector store"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Load a saved vector store from disk (Admin only).
    
    Args:
        identifier: Unique identifier for the vector store to load
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Load operation status
    """
    try:
        ai_service = get_ai_service()
        
        # Load vector store
        success = ai_service.load_vectorstore(identifier)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vector store '{identifier}' not found"
            )
        
        # Get updated info
        vectorstore_info = ai_service.get_vectorstore_info()
        
        return {
            "message": f"Vector store loaded successfully",
            "identifier": identifier,
            "loaded_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
            "vectorstore_info": vectorstore_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading vector store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load vector store: {str(e)}"
        )


@router.delete("/vectorstore/{identifier}")
async def delete_vectorstore(
    identifier: str,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Delete a saved vector store (Admin only).
    
    Args:
        identifier: Unique identifier for the vector store to delete
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Delete operation status
    """
    try:
        ai_service = get_ai_service()
        
        # Delete vector store
        success = ai_service.delete_vectorstore(identifier)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vector store '{identifier}' not found"
            )
        
        return {
            "message": f"Vector store deleted successfully",
            "identifier": identifier,
            "deleted_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting vector store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vector store: {str(e)}"
        )


@router.post("/vectorstore/rebuild")
async def rebuild_vectorstore(
    background_tasks: BackgroundTasks,
    days: int = Query(7, ge=1, le=365, description="Number of days of logs to use"),
    identifier: str = Query("default", description="Identifier for the vector store"),
    auto_save: bool = Query(True, description="Automatically save after rebuild"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Rebuild vector store from logs (Admin only).
    
    Args:
        background_tasks: FastAPI background tasks
        days: Number of days of logs to use for rebuilding
        identifier: Identifier for the vector store
        auto_save: Whether to automatically save after rebuild
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Rebuild operation status
    """
    try:
        ai_service = get_ai_service()
        log_service = get_log_service()
        
        # Start rebuild operation in background
        def rebuild_task():
            try:
                start_time = datetime.now()
                
                # Load logs
                logs = log_service.load_logs_from_days(days)
                logger.info(f"Loaded {len(logs)} logs for vector store rebuild")
                
                # Create new vector store
                ai_service.create_vectorstore(logs)
                logger.info("Vector store created successfully")
                
                # Auto-save if requested
                if auto_save:
                    ai_service.save_vectorstore(identifier)
                    logger.info(f"Vector store saved as '{identifier}'")
                
                end_time = datetime.now()
                logger.info(f"Vector store rebuild completed in {(end_time - start_time).total_seconds():.2f}s")
                
            except Exception as e:
                logger.error(f"Background vector store rebuild failed: {e}")
        
        background_tasks.add_task(rebuild_task)
        
        return {
            "message": f"Vector store rebuild started",
            "status": "started",
            "days": days,
            "identifier": identifier,
            "auto_save": auto_save,
            "initiated_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error initiating vector store rebuild: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate vector store rebuild: {str(e)}"
        )


@router.post("/vectorstore/update")
async def update_vectorstore(
    background_tasks: BackgroundTasks,
    days: int = Query(1, ge=1, le=30, description="Number of recent days to add"),
    identifier: str = Query("default", description="Identifier for the vector store"),
    auto_save: bool = Query(True, description="Automatically save after update"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Incrementally update vector store with new logs (Admin only).
    
    Args:
        background_tasks: FastAPI background tasks
        days: Number of recent days to add to vector store
        identifier: Identifier for the vector store
        auto_save: Whether to automatically save after update
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Update operation status
    """
    try:
        ai_service = get_ai_service()
        log_service = get_log_service()
        
        # Check if vector store exists
        vectorstore_info = ai_service.get_vectorstore_info()
        if vectorstore_info.get("status") != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No vector store available to update. Please rebuild first."
            )
        
        # Start update operation in background
        def update_task():
            try:
                start_time = datetime.now()
                
                # Load recent logs
                new_logs = log_service.load_logs_from_days(days)
                logger.info(f"Loaded {len(new_logs)} new logs for vector store update")
                
                # Update vector store incrementally
                ai_service.incremental_update_vectorstore(new_logs, identifier)
                logger.info("Vector store updated successfully")
                
                # Auto-save if requested
                if auto_save:
                    ai_service.save_vectorstore(identifier)
                    logger.info(f"Updated vector store saved as '{identifier}'")
                
                end_time = datetime.now()
                logger.info(f"Vector store update completed in {(end_time - start_time).total_seconds():.2f}s")
                
            except Exception as e:
                logger.error(f"Background vector store update failed: {e}")
        
        background_tasks.add_task(update_task)
        
        return {
            "message": f"Vector store update started",
            "status": "started",
            "days": days,
            "identifier": identifier,
            "auto_save": auto_save,
            "initiated_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating vector store update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate vector store update: {str(e)}"
        )


@router.get("/config")
async def get_ai_configuration(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current AI service configuration.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current AI service configuration
    """
    try:
        ai_service = get_ai_service()
        config = ai_service.get_llm_config()
        
        return {
            "configuration": config,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving AI configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AI configuration: {str(e)}"
        )


@router.post("/config")
async def update_ai_configuration(
    config_data: Dict[str, Any],
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Update AI service configuration (Admin only).
    
    Args:
        config_data: Configuration updates
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Updated configuration
    """
    try:
        ai_service = get_ai_service()
        
        # Update configuration
        ai_service.update_llm_config(**config_data)
        
        # Get updated configuration
        updated_config = ai_service.get_llm_config()
        
        return {
            "message": "AI configuration updated successfully",
            "updated_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
            "configuration": updated_config
        }
        
    except Exception as e:
        logger.error(f"Error updating AI configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI configuration: {str(e)}"
        )


@router.post("/similarity-search")
async def similarity_search(
    query: str = Query(..., description="Search query text"),
    k: int = Query(5, ge=1, le=20, description="Number of similar documents to return"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Perform similarity search in the vector store.
    
    Args:
        query: Search query text
        k: Number of similar documents to return
        current_user: Current authenticated user
        
    Returns:
        Similar documents from vector store
    """
    try:
        ai_service = get_ai_service()
        
        # Check if vector store is ready
        vectorstore_info = ai_service.get_vectorstore_info()
        if vectorstore_info.get("status") != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vector store not ready. Please rebuild or load a vector store first."
            )
        
        # Perform similarity search
        similar_docs = ai_service.similarity_search(query, k)
        
        # Format results
        results = []
        for i, doc in enumerate(similar_docs):
            results.append({
                "rank": i + 1,
                "content": doc.page_content,
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
            })
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "k": k,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing similarity search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform similarity search: {str(e)}"
        )