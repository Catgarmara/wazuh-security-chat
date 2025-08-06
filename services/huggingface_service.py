"""
HuggingFace Integration Service

Provides model discovery, browsing, and downloading capabilities from HuggingFace Hub.
Handles model metadata, search, filtering, and download management.
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
import requests
from urllib.parse import urlencode
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Information about a HuggingFace model"""
    id: str
    name: str
    display_name: str
    author: str
    description: str
    category: str
    size_estimate: str
    size_bytes: int
    downloads: int
    likes: int
    last_modified: str
    tags: List[str]
    license: str
    model_type: str
    library_name: str
    is_gated: bool
    quantizations: List[Dict[str, str]]

@dataclass 
class DownloadTask:
    """Download task information"""
    id: str
    model_id: str
    model_name: str
    author: str
    quantization: str
    file_url: str
    file_name: str
    total_size: int
    downloaded_size: int
    status: str  # 'queued', 'downloading', 'paused', 'completed', 'failed'
    progress: float
    speed: str
    eta: str
    start_time: Optional[datetime]
    completion_time: Optional[datetime]
    error_message: Optional[str]
    priority: str  # 'high', 'normal', 'low'

class HuggingFaceService:
    """Service for interacting with HuggingFace Hub"""
    
    HF_API_BASE = "https://huggingface.co/api"
    HF_HUB_BASE = "https://huggingface.co"
    
    def __init__(self, 
                 models_path: str = "./models",
                 cache_duration: int = 3600,  # 1 hour
                 max_concurrent_downloads: int = 3):
        """
        Initialize HuggingFace service.
        
        Args:
            models_path: Directory to store downloaded models
            cache_duration: Cache duration for API responses in seconds
            max_concurrent_downloads: Maximum concurrent downloads
        """
        self.models_path = Path(models_path)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        self.cache_duration = cache_duration
        self.max_concurrent_downloads = max_concurrent_downloads
        
        # Caching
        self.model_cache = {}
        self.cache_timestamps = {}
        
        # Download management
        self.download_tasks: Dict[str, DownloadTask] = {}
        self.active_downloads = 0
        self.download_queue = []
        self.download_lock = threading.RLock()
        self.download_threads = {}
        
        # Progress callbacks
        self.progress_callbacks: List[Callable] = []
        
        logger.info("HuggingFace service initialized")
    
    def add_progress_callback(self, callback: Callable) -> None:
        """Add a progress callback function"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """Notify all progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(task_id, progress_data)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        
        age = time.time() - self.cache_timestamps[cache_key]
        return age < self.cache_duration
    
    def search_models(self, 
                     query: Optional[str] = None,
                     category: Optional[str] = None,
                     author: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     sort: str = "downloads",
                     limit: int = 20,
                     use_cache: bool = True) -> List[ModelInfo]:
        """
        Search for models on HuggingFace Hub.
        
        Args:
            query: Search query string
            category: Model category filter
            author: Author filter
            tags: List of tags to filter by
            sort: Sort order (downloads, likes, lastModified)
            limit: Maximum number of results
            use_cache: Whether to use cached results
            
        Returns:
            List of ModelInfo objects
        """
        # Build cache key
        cache_key = hashlib.md5(
            f"{query}_{category}_{author}_{tags}_{sort}_{limit}".encode()
        ).hexdigest()
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            return self.model_cache[cache_key]
        
        try:
            # Build API parameters
            params = {
                'limit': limit,
                'sort': sort,
                'direction': -1,
                'full': True
            }
            
            if query:
                params['search'] = query
            if category:
                params['filter'] = f"task:{category}"
            if author:
                params['author'] = author
            if tags:
                params['tags'] = tags
            
            # Make API request
            url = f"{self.HF_API_BASE}/models?{urlencode(params, doseq=True)}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            models_data = response.json()
            models = []
            
            for model_data in models_data:
                try:
                    model_info = self._parse_model_data(model_data)
                    if model_info:
                        models.append(model_info)
                except Exception as e:
                    logger.warning(f"Failed to parse model data: {e}")
                    continue
            
            # Cache results
            self.model_cache[cache_key] = models
            self.cache_timestamps[cache_key] = time.time()
            
            return models
            
        except Exception as e:
            logger.error(f"Failed to search models: {e}")
            return []
    
    def _parse_model_data(self, model_data: Dict[str, Any]) -> Optional[ModelInfo]:
        """Parse model data from HuggingFace API response"""
        try:
            model_id = model_data.get('id', '')
            if not model_id:
                return None
            
            # Parse basic info
            author_name = model_id.split('/')[0] if '/' in model_id else 'unknown'
            model_name = model_id.split('/')[-1]
            
            # Estimate model category
            tags = model_data.get('tags', [])
            category = self._categorize_model(tags, model_name)
            
            # Estimate size (this is rough estimation based on model name)
            size_bytes, size_estimate = self._estimate_model_size(model_name, tags)
            
            # Generate quantization options
            quantizations = self._generate_quantization_options(size_bytes)
            
            return ModelInfo(
                id=model_id,
                name=model_name,
                display_name=model_data.get('displayName', model_name),
                author=author_name,
                description=model_data.get('description', 'No description available'),
                category=category,
                size_estimate=size_estimate,
                size_bytes=size_bytes,
                downloads=model_data.get('downloads', 0),
                likes=model_data.get('likes', 0),
                last_modified=model_data.get('lastModified', ''),
                tags=tags,
                license=model_data.get('license', 'unknown'),
                model_type=model_data.get('modelType', 'unknown'),
                library_name=model_data.get('library_name', ''),
                is_gated=model_data.get('gated', False),
                quantizations=quantizations
            )
            
        except Exception as e:
            logger.error(f"Failed to parse model data: {e}")
            return None
    
    def _categorize_model(self, tags: List[str], model_name: str) -> str:
        """Categorize model based on tags and name"""
        name_lower = model_name.lower()
        tags_lower = [tag.lower() for tag in tags]
        
        # Security models
        security_keywords = ['security', 'threat', 'malware', 'vulnerability', 'cybersecurity']
        if any(keyword in name_lower for keyword in security_keywords):
            return 'security'
        if any(keyword in ' '.join(tags_lower) for keyword in security_keywords):
            return 'security'
        
        # Code models
        code_keywords = ['code', 'programming', 'codellama', 'starcoder', 'copilot']
        if any(keyword in name_lower for keyword in code_keywords):
            return 'code'
        if 'code-generation' in tags_lower or 'coding' in tags_lower:
            return 'code'
        
        # Reasoning models
        reasoning_keywords = ['reasoning', 'logic', 'math', 'analysis']
        if any(keyword in name_lower for keyword in reasoning_keywords):
            return 'reasoning'
        if 'reasoning' in tags_lower or 'mathematics' in tags_lower:
            return 'reasoning'
        
        # Default to general
        return 'general'
    
    def _estimate_model_size(self, model_name: str, tags: List[str]) -> tuple[int, str]:
        """Estimate model size based on name and tags"""
        name_lower = model_name.lower()
        
        # Extract size from model name (e.g., "llama-7b", "13b-chat")
        size_mappings = {
            '1b': (1_000_000_000, '1.2 GB'),
            '3b': (3_000_000_000, '3.5 GB'),
            '7b': (7_000_000_000, '13.5 GB'),
            '8b': (8_000_000_000, '15 GB'),
            '13b': (13_000_000_000, '25 GB'),
            '20b': (20_000_000_000, '38 GB'),
            '30b': (30_000_000_000, '57 GB'),
            '70b': (70_000_000_000, '130 GB'),
        }
        
        for size_key, (bytes_est, size_str) in size_mappings.items():
            if size_key in name_lower:
                return bytes_est, size_str
        
        # Default small model
        return 1_000_000_000, '1.2 GB'
    
    def _generate_quantization_options(self, base_size: int) -> List[Dict[str, str]]:
        """Generate quantization options for a model"""
        quantizations = []
        
        # Q4_0 - Good quality, fast
        q4_size = int(base_size * 0.35)
        quantizations.append({
            'type': 'Q4_0',
            'size': self._format_bytes(q4_size),
            'description': 'Good quality, fast inference'
        })
        
        # Q5_0 - Better quality
        q5_size = int(base_size * 0.45)
        quantizations.append({
            'type': 'Q5_0', 
            'size': self._format_bytes(q5_size),
            'description': 'Better quality, moderate speed'
        })
        
        # Q8_0 - High quality
        q8_size = int(base_size * 0.65)
        quantizations.append({
            'type': 'Q8_0',
            'size': self._format_bytes(q8_size),
            'description': 'High quality, slower inference'
        })
        
        # FP16 - Original quality
        if base_size < 50_000_000_000:  # Only for models < 50B parameters
            quantizations.append({
                'type': 'FP16',
                'size': self._format_bytes(base_size),
                'description': 'Original quality, requires more resources'
            })
        
        return quantizations
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} PB"
    
    def get_model_details(self, model_id: str) -> Optional[ModelInfo]:
        """Get detailed information about a specific model"""
        try:
            url = f"{self.HF_API_BASE}/models/{model_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            model_data = response.json()
            return self._parse_model_data(model_data)
            
        except Exception as e:
            logger.error(f"Failed to get model details for {model_id}: {e}")
            return None
    
    def queue_download(self, 
                      model_id: str,
                      quantization: str = 'Q4_0',
                      priority: str = 'normal') -> str:
        """
        Queue a model for download.
        
        Args:
            model_id: HuggingFace model ID
            quantization: Quantization type
            priority: Download priority
            
        Returns:
            Download task ID
        """
        with self.download_lock:
            # Generate task ID
            task_id = f"dl_{int(time.time())}_{len(self.download_tasks)}"
            
            # Get model info
            model_info = self.get_model_details(model_id)
            if not model_info:
                logger.error(f"Could not get model info for {model_id}")
                return ""
            
            # Find quantization info
            quant_info = None
            for q in model_info.quantizations:
                if q['type'] == quantization:
                    quant_info = q
                    break
            
            if not quant_info:
                logger.error(f"Quantization {quantization} not available for {model_id}")
                return ""
            
            # Create download task
            task = DownloadTask(
                id=task_id,
                model_id=model_id,
                model_name=model_info.display_name,
                author=model_info.author,
                quantization=quantization,
                file_url=f"{self.HF_HUB_BASE}/{model_id}/resolve/main/model.gguf",  # Simplified
                file_name=f"{model_info.name}-{quantization.lower()}.gguf",
                total_size=int(quant_info['size'].split()[0].replace('GB', '')) * 1024**3,  # Rough
                downloaded_size=0,
                status='queued',
                progress=0.0,
                speed='0 MB/s',
                eta='Calculating...',
                start_time=None,
                completion_time=None,
                error_message=None,
                priority=priority
            )
            
            self.download_tasks[task_id] = task
            
            # Add to queue based on priority
            if priority == 'high':
                self.download_queue.insert(0, task_id)
            else:
                self.download_queue.append(task_id)
            
            # Start download if capacity available
            self._process_download_queue()
            
            logger.info(f"Queued download: {model_info.display_name} ({quantization})")
            return task_id
    
    def _process_download_queue(self) -> None:
        """Process the download queue"""
        while (self.active_downloads < self.max_concurrent_downloads and 
               self.download_queue):
            task_id = self.download_queue.pop(0)
            if task_id in self.download_tasks:
                self._start_download(task_id)
    
    def _start_download(self, task_id: str) -> None:
        """Start downloading a model"""
        task = self.download_tasks[task_id]
        
        # Update task status
        task.status = 'downloading'
        task.start_time = datetime.now()
        self.active_downloads += 1
        
        # Start download in separate thread
        thread = threading.Thread(
            target=self._download_worker,
            args=(task_id,),
            name=f"download_{task_id}"
        )
        self.download_threads[task_id] = thread
        thread.start()
        
        self._notify_progress(task_id, {'status': 'downloading', 'progress': 0})
    
    def _download_worker(self, task_id: str) -> None:
        """Download worker thread"""
        task = self.download_tasks[task_id]
        
        try:
            # Create target file path
            target_path = self.models_path / task.file_name
            
            # Simulate download (replace with actual download logic)
            self._simulate_download(task_id, target_path)
            
            # Mark as completed
            with self.download_lock:
                task.status = 'completed'
                task.completion_time = datetime.now()
                task.progress = 100.0
                task.speed = '0 MB/s'
                task.eta = 'Completed'
                self.active_downloads -= 1
                
                if task_id in self.download_threads:
                    del self.download_threads[task_id]
                
                # Process next in queue
                self._process_download_queue()
            
            self._notify_progress(task_id, {
                'status': 'completed', 
                'progress': 100,
                'file_path': str(target_path)
            })
            
            logger.info(f"Download completed: {task.model_name}")
            
        except Exception as e:
            # Mark as failed
            with self.download_lock:
                task.status = 'failed'
                task.error_message = str(e)
                task.progress = 0
                task.speed = '0 MB/s'
                task.eta = 'Failed'
                self.active_downloads -= 1
                
                if task_id in self.download_threads:
                    del self.download_threads[task_id]
                
                # Process next in queue
                self._process_download_queue()
            
            self._notify_progress(task_id, {
                'status': 'failed',
                'error': str(e)
            })
            
            logger.error(f"Download failed: {task.model_name} - {e}")
    
    def _simulate_download(self, task_id: str, target_path: Path) -> None:
        """Simulate model download (replace with actual implementation)"""
        task = self.download_tasks[task_id]
        
        # Simulate progress updates
        for i in range(101):
            if task.status != 'downloading':  # Check for cancellation
                return
            
            task.progress = float(i)
            task.downloaded_size = int(task.total_size * i / 100)
            
            if i < 100:
                remaining = task.total_size - task.downloaded_size
                speed = 45 * 1024 * 1024  # 45 MB/s
                eta_seconds = remaining / speed
                task.speed = f"{speed / (1024*1024):.1f} MB/s"
                task.eta = f"{int(eta_seconds // 60)}:{int(eta_seconds % 60):02d}"
            
            self._notify_progress(task_id, {
                'status': 'downloading',
                'progress': i,
                'speed': task.speed,
                'eta': task.eta
            })
            
            time.sleep(0.1)  # Simulate download time
        
        # Create mock model file
        target_path.write_text(f"Mock model file for {task.model_name}")
    
    def pause_download(self, task_id: str) -> bool:
        """Pause a download"""
        if task_id not in self.download_tasks:
            return False
        
        task = self.download_tasks[task_id]
        if task.status == 'downloading':
            task.status = 'paused'
            self._notify_progress(task_id, {'status': 'paused'})
            return True
        
        return False
    
    def resume_download(self, task_id: str) -> bool:
        """Resume a paused download"""
        if task_id not in self.download_tasks:
            return False
        
        task = self.download_tasks[task_id]
        if task.status == 'paused':
            task.status = 'downloading'
            self._notify_progress(task_id, {'status': 'downloading'})
            return True
        
        return False
    
    def cancel_download(self, task_id: str) -> bool:
        """Cancel a download"""
        if task_id not in self.download_tasks:
            return False
        
        with self.download_lock:
            task = self.download_tasks[task_id]
            
            if task.status in ['downloading', 'paused', 'queued']:
                task.status = 'cancelled'
                
                # Remove from queue if queued
                if task_id in self.download_queue:
                    self.download_queue.remove(task_id)
                
                # Clean up thread
                if task_id in self.download_threads:
                    del self.download_threads[task_id]
                
                if task.status == 'downloading':
                    self.active_downloads -= 1
                    self._process_download_queue()
                
                self._notify_progress(task_id, {'status': 'cancelled'})
                return True
        
        return False
    
    def get_download_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get download status"""
        if task_id not in self.download_tasks:
            return None
        
        task = self.download_tasks[task_id]
        return {
            'id': task.id,
            'model_id': task.model_id,
            'model_name': task.model_name,
            'author': task.author,
            'quantization': task.quantization,
            'status': task.status,
            'progress': task.progress,
            'speed': task.speed,
            'eta': task.eta,
            'downloaded_size': task.downloaded_size,
            'total_size': task.total_size,
            'start_time': task.start_time.isoformat() if task.start_time else None,
            'completion_time': task.completion_time.isoformat() if task.completion_time else None,
            'error_message': task.error_message,
            'priority': task.priority
        }
    
    def get_all_downloads(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all downloads grouped by status"""
        downloads = {
            'active': [],
            'completed': [],
            'failed': [],
            'queued': []
        }
        
        for task in self.download_tasks.values():
            status_data = self.get_download_status(task.id)
            if status_data:
                if task.status in ['downloading', 'paused']:
                    downloads['active'].append(status_data)
                elif task.status == 'completed':
                    downloads['completed'].append(status_data)
                elif task.status == 'failed':
                    downloads['failed'].append(status_data)
                elif task.status == 'queued':
                    downloads['queued'].append(status_data)
        
        return downloads
    
    def clear_completed_downloads(self) -> int:
        """Clear completed downloads and return count cleared"""
        cleared = 0
        to_remove = []
        
        for task_id, task in self.download_tasks.items():
            if task.status == 'completed':
                to_remove.append(task_id)
                cleared += 1
        
        for task_id in to_remove:
            del self.download_tasks[task_id]
        
        return cleared