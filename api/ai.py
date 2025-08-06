"""
AI Service Management API endpoints.

This module provides REST API endpoints for AI service management,
vector store operations, LLM configuration, model management, and inference.
Consolidates all AI functionality into a single API interface.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from services.embedded_ai_service import EmbeddedAIService
from services.log_service import LogService
from models.database import User
from models.schemas import DateRange

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class ModelConfigUpdate(BaseModel):
    context_length: Optional[int] = None
    n_gpu_layers: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None

class InferenceRequest(BaseModel):
    query: str
    model_id: Optional[str] = None
    session_id: str = "default"
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None

class ModelRegistration(BaseModel):
    model_id: str
    model_path: str
    model_name: str
    context_length: Optional[int] = 4096
    n_gpu_layers: Optional[int] = -1
    temperature: Optional[float] = 0.7

# Create router
router = APIRouter(prefix="/ai", tags=["AI Service Management"])


def get_ai_service() -> EmbeddedAIService:
    """Get Embedded AI service instance."""
    return EmbeddedAIService()


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
        
        # Get comprehensive service status
        status_data = ai_service.get_service_status()
        
        # Check LLM health
        llm_health = ai_service.check_llm_health()
        
        # Get vector store info
        vectorstore_info = ai_service.get_vectorstore_info()
        
        # Get service configuration
        config = ai_service.get_llm_config()
        
        return {
            "status": "healthy" if status_data["service_ready"] else "unhealthy",
            "service": "ai_management",
            "timestamp": datetime.now().isoformat(),
            "llm_health": llm_health,
            "vectorstore_info": vectorstore_info,
            "configuration": config,
            "ready": ai_service.is_ready(),
            **status_data
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


# ============================================================================
# Model Management Endpoints (formerly from embedded_ai.py)
# ============================================================================

@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get real-time system resource statistics."""
    try:
        ai_service = get_ai_service()
        system_stats = ai_service.get_system_stats()
        
        return {
            "cpu_percent": system_stats.cpu_percent,
            "memory": {
                "used_gb": round(system_stats.memory_used / (1024**3), 2),
                "total_gb": round(system_stats.memory_total / (1024**3), 2),
                "usage_percent": round((system_stats.memory_used / system_stats.memory_total) * 100, 1)
            },
            "gpu_stats": system_stats.gpu_stats,
            "disk_usage": system_stats.disk_usage,
            "timestamp": system_stats.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system statistics"
        )


@router.post("/models/register")
async def register_model(
    model_data: ModelRegistration,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """Register a new model with the service (Admin only)."""
    try:
        ai_service = get_ai_service()
        
        success = ai_service.register_model(
            model_id=model_data.model_id,
            model_path=model_data.model_path,
            model_name=model_data.model_name,
            context_length=model_data.context_length,
            n_gpu_layers=model_data.n_gpu_layers,
            temperature=model_data.temperature
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register model"
            )
        
        return {
            "message": "Model registered successfully",
            "model_id": model_data.model_id,
            "model_name": model_data.model_name,
            "registered_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register model: {str(e)}"
        )


@router.post("/models/{model_id}/load")
async def load_model(
    model_id: str,
    force: bool = Query(False, description="Force load even if at capacity"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """Load a model into memory (Admin only)."""
    try:
        ai_service = get_ai_service()
        
        success = ai_service.load_model(model_id, force=force)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load model {model_id}"
            )
        
        return {
            "message": f"Model loaded successfully",
            "model_id": model_id,
            "loaded_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load model: {str(e)}"
        )


@router.post("/models/{model_id}/unload")
async def unload_model(
    model_id: str,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """Unload a model from memory (Admin only)."""
    try:
        ai_service = get_ai_service()
        
        success = ai_service.unload_model(model_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to unload model {model_id}"
            )
        
        return {
            "message": f"Model unloaded successfully",
            "model_id": model_id,
            "unloaded_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unloading model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unload model: {str(e)}"
        )


@router.post("/models/hot-swap")
async def hot_swap_models(
    from_model_id: str = Query(..., description="Current model ID"),
    to_model_id: str = Query(..., description="Target model ID"),
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """Hot swap between models (Admin only)."""
    try:
        ai_service = get_ai_service()
        
        success = ai_service.hot_swap_model(from_model_id, to_model_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to hot swap from {from_model_id} to {to_model_id}"
            )
        
        return {
            "message": "Hot swap completed successfully",
            "from_model_id": from_model_id,
            "to_model_id": to_model_id,
            "swapped_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error hot swapping models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to hot swap models: {str(e)}"
        )


@router.get("/models/loaded")
async def get_loaded_models(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get currently loaded models."""
    try:
        ai_service = get_ai_service()
        loaded_models = ai_service.get_loaded_models()
        
        return {
            "loaded_models": loaded_models,
            "total_loaded": len(loaded_models),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting loaded models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get loaded models"
        )


@router.get("/models/available")
async def get_available_models(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get all available models."""
    try:
        ai_service = get_ai_service()
        available_models = ai_service.get_available_models()
        
        return {
            "available_models": available_models,
            "total_available": len(available_models),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available models"
        )


@router.put("/models/{model_id}/config")
async def update_model_config(
    model_id: str,
    config_update: ModelConfigUpdate,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """Update model configuration (Admin only)."""
    try:
        ai_service = get_ai_service()
        
        # Filter out None values
        config_dict = {k: v for k, v in config_update.dict().items() if v is not None}
        
        success = ai_service.update_model_config(model_id, **config_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        return {
            "message": "Model configuration updated successfully",
            "model_id": model_id,
            "updated_config": config_dict,
            "updated_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model configuration: {str(e)}"
        )


@router.post("/inference")
async def generate_inference(
    request: InferenceRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Generate AI inference response."""
    try:
        ai_service = get_ai_service()
        
        # Prepare generation parameters
        gen_kwargs = {}
        if request.max_tokens is not None:
            gen_kwargs['max_tokens'] = request.max_tokens
        if request.temperature is not None:
            gen_kwargs['temperature'] = request.temperature
        if request.top_p is not None:
            gen_kwargs['top_p'] = request.top_p
        
        # Generate response
        response = ai_service.generate_response(
            query=request.query,
            model_id=request.model_id,
            session_id=request.session_id,
            **gen_kwargs
        )
        
        return {
            "response": response,
            "model_id": request.model_id or ai_service.active_model,
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating inference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate inference: {str(e)}"
        )


@router.get("/conversations/{session_id}/history")
async def get_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get conversation history for a session."""
    try:
        ai_service = get_ai_service()
        history = ai_service.get_conversation_history(session_id)
        
        # Convert to serializable format
        history_data = []
        for message in history:
            if hasattr(message, 'content'):
                history_data.append({
                    'type': message.__class__.__name__,
                    'content': message.content,
                    'timestamp': datetime.now().isoformat()
                })
        
        return {
            "session_id": session_id,
            "history": history_data,
            "message_count": len(history_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation history"
        )


@router.delete("/conversations/{session_id}")
async def clear_conversation(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Clear conversation history for a session."""
    try:
        ai_service = get_ai_service()
        ai_service.clear_conversation_history(session_id)
        
        return {
            "message": "Conversation history cleared",
            "session_id": session_id,
            "cleared_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear conversation history"
        )