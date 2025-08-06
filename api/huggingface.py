"""
HuggingFace API endpoints.

REST API for HuggingFace model browsing, searching, and downloading.
Provides integration with HuggingFace Hub for model discovery and management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.permissions import get_current_active_user, admin_required
from services.huggingface_service import HuggingFaceService
from models.database import User

logger = logging.getLogger(__name__)

# Pydantic models
class ModelSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    sort: str = "downloads"
    limit: int = 20

class DownloadRequest(BaseModel):
    model_id: str
    quantization: str = "Q4_0"
    priority: str = "normal"

# Create router
router = APIRouter(prefix="/huggingface", tags=["HuggingFace Integration"])

# Service instance
_hf_service: Optional[HuggingFaceService] = None

def get_hf_service() -> HuggingFaceService:
    """Get HuggingFace service instance."""
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFaceService()
    return _hf_service

@router.get("/search")
async def search_models(
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Model category filter"),
    author: Optional[str] = Query(None, description="Author filter"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    sort: str = Query("downloads", description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Search for models on HuggingFace Hub.
    """
    try:
        hf_service = get_hf_service()
        
        # Parse tags if provided
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
        
        # Search models
        models = hf_service.search_models(
            query=query,
            category=category,
            author=author,
            tags=tag_list,
            sort=sort,
            limit=limit
        )
        
        # Convert to serializable format
        model_data = []
        for model in models:
            model_data.append({
                'id': model.id,
                'name': model.name,
                'display_name': model.display_name,
                'author': model.author,
                'description': model.description,
                'category': model.category,
                'size_estimate': model.size_estimate,
                'size_bytes': model.size_bytes,
                'downloads': model.downloads,
                'likes': model.likes,
                'last_modified': model.last_modified,
                'tags': model.tags,
                'license': model.license,
                'model_type': model.model_type,
                'library_name': model.library_name,
                'is_gated': model.is_gated,
                'quantizations': model.quantizations
            })
        
        return {
            "models": model_data,
            "total_results": len(model_data),
            "search_params": {
                "query": query,
                "category": category,
                "author": author,
                "tags": tag_list,
                "sort": sort,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search models: {str(e)}"
        )

@router.get("/models/{model_id}")
async def get_model_details(
    model_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific model.
    """
    try:
        hf_service = get_hf_service()
        
        # Replace URL encoding
        model_id = model_id.replace("%2F", "/")
        
        model = hf_service.get_model_details(model_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        return {
            "model": {
                'id': model.id,
                'name': model.name,
                'display_name': model.display_name,
                'author': model.author,
                'description': model.description,
                'category': model.category,
                'size_estimate': model.size_estimate,
                'size_bytes': model.size_bytes,
                'downloads': model.downloads,
                'likes': model.likes,
                'last_modified': model.last_modified,
                'tags': model.tags,
                'license': model.license,
                'model_type': model.model_type,
                'library_name': model.library_name,
                'is_gated': model.is_gated,
                'quantizations': model.quantizations
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model details: {str(e)}"
        )

@router.post("/download")
async def queue_download(
    download_request: DownloadRequest,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Queue a model for download (Admin only).
    """
    try:
        hf_service = get_hf_service()
        
        task_id = hf_service.queue_download(
            model_id=download_request.model_id,
            quantization=download_request.quantization,
            priority=download_request.priority
        )
        
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to queue download"
            )
        
        return {
            "message": "Download queued successfully",
            "task_id": task_id,
            "model_id": download_request.model_id,
            "quantization": download_request.quantization,
            "priority": download_request.priority,
            "queued_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue download: {str(e)}"
        )

@router.get("/downloads")
async def get_downloads(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get all downloads grouped by status.
    """
    try:
        hf_service = get_hf_service()
        downloads = hf_service.get_all_downloads()
        
        # Calculate totals
        total_downloads = sum(len(downloads[key]) for key in downloads.keys())
        
        return {
            "downloads": downloads,
            "totals": {
                "active": len(downloads['active']),
                "completed": len(downloads['completed']),
                "failed": len(downloads['failed']),
                "queued": len(downloads['queued']),
                "total": total_downloads
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting downloads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get downloads"
        )

@router.get("/downloads/{task_id}")
async def get_download_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get status of a specific download task.
    """
    try:
        hf_service = get_hf_service()
        status_data = hf_service.get_download_status(task_id)
        
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download task {task_id} not found"
            )
        
        return {
            "download": status_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get download status"
        )

@router.post("/downloads/{task_id}/pause")
async def pause_download(
    task_id: str,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Pause a download (Admin only).
    """
    try:
        hf_service = get_hf_service()
        success = hf_service.pause_download(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to pause download {task_id}"
            )
        
        return {
            "message": "Download paused successfully",
            "task_id": task_id,
            "paused_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause download: {str(e)}"
        )

@router.post("/downloads/{task_id}/resume")
async def resume_download(
    task_id: str,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Resume a paused download (Admin only).
    """
    try:
        hf_service = get_hf_service()
        success = hf_service.resume_download(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to resume download {task_id}"
            )
        
        return {
            "message": "Download resumed successfully",
            "task_id": task_id,
            "resumed_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume download: {str(e)}"
        )

@router.delete("/downloads/{task_id}")
async def cancel_download(
    task_id: str,
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Cancel a download (Admin only).
    """
    try:
        hf_service = get_hf_service()
        success = hf_service.cancel_download(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel download {task_id}"
            )
        
        return {
            "message": "Download cancelled successfully",
            "task_id": task_id,
            "cancelled_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel download: {str(e)}"
        )

@router.delete("/downloads/completed")
async def clear_completed_downloads(
    current_user: User = Depends(admin_required)
) -> Dict[str, Any]:
    """
    Clear all completed downloads (Admin only).
    """
    try:
        hf_service = get_hf_service()
        cleared_count = hf_service.clear_completed_downloads()
        
        return {
            "message": f"Cleared {cleared_count} completed downloads",
            "cleared_count": cleared_count,
            "cleared_by": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing completed downloads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear completed downloads"
        )

@router.get("/categories")
async def get_categories(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get available model categories.
    """
    try:
        categories = [
            {
                "id": "security",
                "name": "Security",
                "description": "Models specialized for cybersecurity analysis and threat detection"
            },
            {
                "id": "general",
                "name": "General",
                "description": "General-purpose conversational models"
            },
            {
                "id": "code",
                "name": "Code",
                "description": "Models specialized for code generation and analysis"
            },
            {
                "id": "reasoning",
                "name": "Reasoning",
                "description": "Models optimized for logical reasoning and problem solving"
            }
        ]
        
        return {
            "categories": categories,
            "total_categories": len(categories),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories"
        )