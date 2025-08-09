"""
Embedded AI Service Module

This module replaces the Ollama-dependent AIService with a completely self-contained
LlamaCpp-based implementation. Provides model management, loading/unloading, and
inference capabilities without external dependencies.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import psutil

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logging.warning("GPUtil not installed. GPU monitoring will be disabled.")

try:
    from llama_cpp import Llama, LlamaGrammar
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.error("llama-cpp-python not installed. This is required for embedded AI functionality.")
    logging.info("Install with: pip install llama-cpp-python[server]")
    logging.info("For GPU support: CMAKE_ARGS='-DLLAMA_CUBLAS=on' pip install llama-cpp-python[server]")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.schema.messages import SystemMessage, HumanMessage, AIMessage
from core.exceptions import (
    AIProcessingError, ServiceUnavailableError, EmbeddedAIError, 
    ModelLoadingError, ResourceExhaustionError, ErrorCode
)
from core.resource_manager import get_resource_manager, ResourceType, ResourceStatus

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for a loaded model"""
    model_id: str
    model_path: str
    model_name: str
    context_length: int = 4096
    n_gpu_layers: int = -1
    n_batch: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_tokens: int = 1024
    use_mmap: bool = True
    use_mlock: bool = False
    verbose: bool = False

@dataclass
class SystemStats:
    """System resource statistics"""
    cpu_percent: float
    memory_used: float
    memory_total: float
    gpu_stats: List[Dict[str, Any]]
    disk_usage: Dict[str, float]
    timestamp: datetime

class EmbeddedAIService:
    """
    Self-contained AI service using LlamaCpp for model inference.
    Provides complete model lifecycle management without external dependencies.
    """
    
    def __init__(self, 
                 models_path: str = "./models",
                 vectorstore_path: str = "./data/vectorstore", 
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 max_concurrent_models: int = 3,
                 conversation_memory_size: int = 10):
        """
        Initialize the Embedded AI service with enterprise-grade error handling.
        
        Args:
            models_path: Directory to store downloaded models
            vectorstore_path: Path to store vector store data
            embedding_model_name: HuggingFace embedding model name
            max_concurrent_models: Maximum number of models to keep loaded
            conversation_memory_size: Number of conversation turns to remember
        """
        self.models_path = Path(models_path)
        self.vectorstore_path = Path(vectorstore_path)
        self.embedding_model_name = embedding_model_name
        self.max_concurrent_models = max_concurrent_models
        self.conversation_memory_size = conversation_memory_size
        
        # Core components
        self.embedding_model = None
        self.vectorstore = None
        self.vectorstore_metadata = {}
        
        # Model management
        self.loaded_models: Dict[str, Tuple[Llama, ModelConfig]] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_usage_stats: Dict[str, Dict[str, Any]] = {}
        self.model_lock = threading.RLock()
        
        # Backup model configuration for fallback
        self.backup_models: List[str] = []
        self.fallback_model_id = None
        
        # Conversation management
        self.conversation_sessions = {}
        self.active_model = None
        
        # System monitoring
        self.system_stats_cache = None
        self.stats_cache_time = None
        self.stats_cache_duration = 5  # seconds
        
        # Resource management integration
        self.resource_manager = get_resource_manager()
        self.resource_manager.set_model_manager(self)
        
        # Error tracking and recovery
        self.initialization_errors = []
        self.service_degraded = False
        self.last_health_check = None
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embedded_ai")
        
        # Initialize service with comprehensive error handling
        self._initialize_service_with_fallbacks()
    
    def _initialize_service_with_fallbacks(self) -> None:
        """Initialize the service components with comprehensive error handling and fallbacks."""
        initialization_success = False
        
        try:
            # Check llama-cpp-python availability first
            if not LLAMA_CPP_AVAILABLE:
                error_msg = (
                    "llama-cpp-python is not available. This is required for embedded AI functionality. "
                    "Install with: pip install llama-cpp-python[server]"
                )
                self.initialization_errors.append(error_msg)
                raise EmbeddedAIError(
                    message=error_msg,
                    error_code=ErrorCode.LLAMA_CPP_NOT_AVAILABLE,
                    recovery_suggestions=[
                        "Install llama-cpp-python: pip install llama-cpp-python[server]",
                        "For GPU support: CMAKE_ARGS='-DLLAMA_CUBLAS=on' pip install llama-cpp-python[server]",
                        "Verify Python environment has required dependencies",
                        "Check system compatibility with llama-cpp-python",
                        "Restart the application after installation"
                    ]
                )
            
            # Create directories with proper error handling
            try:
                self.models_path.mkdir(parents=True, exist_ok=True)
                self.vectorstore_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directories: models={self.models_path}, vectorstore={self.vectorstore_path}")
            except PermissionError as e:
                error_msg = f"Permission denied creating directories: {e}"
                self.initialization_errors.append(error_msg)
                raise EmbeddedAIError(
                    message=error_msg,
                    error_code=ErrorCode.CONFIGURATION_ERROR,
                    recovery_suggestions=[
                        "Check directory permissions for models and vectorstore paths",
                        "Run application with appropriate user permissions",
                        "Verify disk space availability",
                        "Consider changing models_path and vectorstore_path in configuration"
                    ]
                )
            
            # Initialize embedding model with fallback options
            self._initialize_embedding_model_with_fallbacks()
            
            # Load existing model configurations
            self._load_model_configurations()
            
            # Set up backup models for fallback
            self._setup_backup_models()
            
            # Start resource monitoring
            if not self.resource_manager.monitoring_active:
                self.resource_manager.start_monitoring()
            
            # Register resource callbacks
            self._register_resource_callbacks()
            
            initialization_success = True
            logger.info("Embedded AI Service initialized successfully with enterprise-grade error handling")
            
        except EmbeddedAIError:
            # Re-raise embedded AI errors as-is
            raise
        except Exception as e:
            error_msg = f"Unexpected error during service initialization: {str(e)}"
            self.initialization_errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            
            # Try to initialize in degraded mode
            try:
                self._initialize_degraded_mode()
                logger.warning("Embedded AI Service initialized in degraded mode")
            except Exception as degraded_error:
                logger.error(f"Failed to initialize even in degraded mode: {degraded_error}")
                raise EmbeddedAIError(
                    message=f"Complete service initialization failure: {error_msg}",
                    error_code=ErrorCode.AI_PROCESSING_ERROR,
                    details={"initialization_errors": self.initialization_errors},
                    cause=e,
                    recovery_suggestions=[
                        "Check system requirements and dependencies",
                        "Verify configuration settings",
                        "Review system logs for detailed error information",
                        "Try restarting the service",
                        "Contact system administrator if issues persist"
                    ]
                )
    
    def _initialize_embedding_model_with_fallbacks(self) -> None:
        """Initialize embedding model with fallback options."""
        embedding_models_to_try = [
            self.embedding_model_name,
            "all-MiniLM-L6-v2",  # Fallback 1
            "sentence-transformers/all-MiniLM-L6-v2",  # Fallback 2
        ]
        
        for model_name in embedding_models_to_try:
            try:
                logger.info(f"Attempting to initialize embedding model: {model_name}")
                self.embedding_model = HuggingFaceEmbeddings(model_name=model_name)
                self.embedding_model_name = model_name
                logger.info(f"Successfully initialized embedding model: {model_name}")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize embedding model {model_name}: {e}")
                continue
        
        # If all embedding models fail, raise error
        error_msg = f"Failed to initialize any embedding model from: {embedding_models_to_try}"
        self.initialization_errors.append(error_msg)
        raise EmbeddedAIError(
            message=error_msg,
            error_code=ErrorCode.EMBEDDING_GENERATION_FAILED,
            recovery_suggestions=[
                "Check internet connection for model downloads",
                "Verify HuggingFace transformers library is installed",
                "Try using a different embedding model",
                "Clear HuggingFace cache and retry",
                "Check available disk space for model downloads"
            ]
        )
    
    def _setup_backup_models(self) -> None:
        """Set up backup models for fallback scenarios."""
        # Define backup models in order of preference
        backup_model_names = [
            "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            "phi-2.Q4_K_M.gguf",
            "mistral-7b-instruct-v0.1.Q4_K_M.gguf"
        ]
        
        for model_name in backup_model_names:
            model_path = self.models_path / model_name
            if model_path.exists():
                model_id = f"backup_{model_name.replace('.gguf', '')}"
                if self.register_model(model_id, str(model_path), f"Backup {model_name}"):
                    self.backup_models.append(model_id)
                    if not self.fallback_model_id:
                        self.fallback_model_id = model_id
        
        if self.backup_models:
            logger.info(f"Configured {len(self.backup_models)} backup models for fallback")
        else:
            logger.warning("No backup models available for fallback scenarios")
    
    def _initialize_degraded_mode(self) -> None:
        """Initialize service in degraded mode with minimal functionality."""
        self.service_degraded = True
        logger.warning("Initializing Embedded AI Service in degraded mode")
        
        # Try to at least initialize basic components
        try:
            if not self.embedding_model:
                # Try the most basic embedding model
                self.embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to initialize even basic embedding model: {e}")
        
        # Load any existing model configurations
        try:
            self._load_model_configurations()
        except Exception as e:
            logger.error(f"Failed to load model configurations in degraded mode: {e}")
    
    def _register_resource_callbacks(self) -> None:
        """Register callbacks for resource status changes."""
        self.resource_manager.register_resource_callback(
            ResourceStatus.WARNING, self._handle_resource_warning
        )
        self.resource_manager.register_resource_callback(
            ResourceStatus.CRITICAL, self._handle_resource_critical
        )
        self.resource_manager.register_resource_callback(
            ResourceStatus.EXHAUSTED, self._handle_resource_exhausted
        )
    
    def _handle_resource_warning(self, metric) -> None:
        """Handle resource warning status."""
        logger.warning(
            f"Resource warning: {metric.resource_type.value} at {metric.current_usage:.1f}%"
        )
        
        # Proactive model management
        if metric.resource_type == ResourceType.MEMORY and metric.current_usage > 80:
            self._proactive_model_cleanup()
    
    def _handle_resource_critical(self, metric) -> None:
        """Handle resource critical status."""
        logger.error(
            f"Resource critical: {metric.resource_type.value} at {metric.current_usage:.1f}%"
        )
        
        # Aggressive resource management
        if metric.resource_type == ResourceType.MEMORY:
            self._emergency_memory_cleanup()
    
    def _handle_resource_exhausted(self, metric) -> None:
        """Handle resource exhausted status."""
        logger.critical(
            f"Resource exhausted: {metric.resource_type.value} at {metric.current_usage:.1f}%"
        )
        
        # Emergency resource management
        if metric.resource_type == ResourceType.MEMORY:
            self._emergency_memory_cleanup()
            # Consider switching to fallback model
            if self.fallback_model_id and self.active_model != self.fallback_model_id:
                self._switch_to_fallback_model()
    
    def _proactive_model_cleanup(self) -> None:
        """Proactively clean up resources before they become critical."""
        try:
            inactive_models = self.get_inactive_models(inactive_threshold_minutes=15)
            if inactive_models:
                model_to_unload = inactive_models[0]
                if self.unload_model(model_to_unload):
                    logger.info(f"Proactively unloaded inactive model: {model_to_unload}")
        except Exception as e:
            logger.error(f"Error in proactive model cleanup: {e}")
    
    def _emergency_memory_cleanup(self) -> None:
        """Emergency memory cleanup when resources are critical."""
        try:
            # Unload all models except active one
            models_to_unload = [
                model_id for model_id in self.loaded_models.keys() 
                if model_id != self.active_model
            ]
            
            for model_id in models_to_unload:
                if self.unload_model(model_id):
                    logger.warning(f"Emergency unloaded model: {model_id}")
            
            # Clear conversation history to free memory
            self._clear_old_conversations()
            
        except Exception as e:
            logger.error(f"Error in emergency memory cleanup: {e}")
    
    def _switch_to_fallback_model(self) -> None:
        """Switch to fallback model in emergency situations."""
        if not self.fallback_model_id:
            logger.error("No fallback model available for emergency switch")
            return
        
        try:
            logger.warning(f"Switching to fallback model: {self.fallback_model_id}")
            
            # Load fallback model if not already loaded
            if self.fallback_model_id not in self.loaded_models:
                if not self.load_model(self.fallback_model_id, force=True):
                    logger.error("Failed to load fallback model")
                    return
            
            # Switch active model
            self.active_model = self.fallback_model_id
            logger.info(f"Successfully switched to fallback model: {self.fallback_model_id}")
            
        except Exception as e:
            logger.error(f"Failed to switch to fallback model: {e}")
    
    def _clear_old_conversations(self) -> None:
        """Clear old conversation sessions to free memory."""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=1)  # Keep only last hour
            
            sessions_to_remove = []
            for session_id, session_data in self.conversation_sessions.items():
                if session_data.get("last_activity", current_time) < cutoff_time:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.conversation_sessions[session_id]
            
            if sessions_to_remove:
                logger.info(f"Cleared {len(sessions_to_remove)} old conversation sessions")
                
        except Exception as e:
            logger.error(f"Error clearing old conversations: {e}")
    
    def _load_model_configurations(self) -> None:
        """Load model configurations from disk"""
        config_file = self.models_path / "model_configs.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    configs = json.load(f)
                
                for model_id, config_data in configs.items():
                    self.model_configs[model_id] = ModelConfig(**config_data)
                    
            except Exception as e:
                logger.warning(f"Failed to load model configurations: {e}")
    
    def _save_model_configurations(self) -> None:
        """Save model configurations to disk"""
        config_file = self.models_path / "model_configs.json"
        try:
            configs = {}
            for model_id, config in self.model_configs.items():
                configs[model_id] = {
                    'model_id': config.model_id,
                    'model_path': config.model_path,
                    'model_name': config.model_name,
                    'context_length': config.context_length,
                    'n_gpu_layers': config.n_gpu_layers,
                    'n_batch': config.n_batch,
                    'temperature': config.temperature,
                    'top_p': config.top_p,
                    'top_k': config.top_k,
                    'repeat_penalty': config.repeat_penalty,
                    'max_tokens': config.max_tokens,
                    'use_mmap': config.use_mmap,
                    'use_mlock': config.use_mlock,
                    'verbose': config.verbose
                }
            
            with open(config_file, 'w') as f:
                json.dump(configs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save model configurations: {e}")
    
    def get_system_stats(self) -> SystemStats:
        """Get current system resource statistics"""
        current_time = datetime.now()
        
        # Use cached stats if available and recent
        if (self.system_stats_cache and self.stats_cache_time and 
            (current_time - self.stats_cache_time).total_seconds() < self.stats_cache_duration):
            return self.system_stats_cache
        
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # GPU stats (if available)
            gpu_stats = []
            if GPUTIL_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    for gpu in gpus:
                        gpu_stats.append({
                            'id': gpu.id,
                            'name': gpu.name,
                            'usage': gpu.load * 100,
                            'memory_used': gpu.memoryUsed,
                            'memory_total': gpu.memoryTotal,
                            'temperature': gpu.temperature
                        })
                except Exception:
                    # GPU monitoring not available
                    pass
            
            # Disk usage
            disk_usage = {}
            try:
                models_usage = psutil.disk_usage(self.models_path)
                disk_usage['models'] = {
                    'used': models_usage.used,
                    'total': models_usage.total,
                    'free': models_usage.free
                }
            except Exception:
                disk_usage['models'] = {'used': 0, 'total': 0, 'free': 0}
            
            stats = SystemStats(
                cpu_percent=cpu_percent,
                memory_used=memory.used,
                memory_total=memory.total,
                gpu_stats=gpu_stats,
                disk_usage=disk_usage,
                timestamp=current_time
            )
            
            # Cache the stats
            self.system_stats_cache = stats
            self.stats_cache_time = current_time
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return SystemStats(0, 0, 0, [], {}, current_time)
    
    def register_model(self, model_id: str, model_path: str, model_name: str, **config_kwargs) -> bool:
        """
        Register a model for use with the service.
        
        Args:
            model_id: Unique identifier for the model
            model_path: Path to the GGUF model file
            model_name: Human-readable model name
            **config_kwargs: Additional model configuration parameters
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            model_path_obj = Path(model_path)
            if not model_path_obj.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Create model configuration
            config = ModelConfig(
                model_id=model_id,
                model_path=str(model_path_obj.absolute()),
                model_name=model_name,
                **config_kwargs
            )
            
            self.model_configs[model_id] = config
            self._save_model_configurations()
            
            logger.info(f"Model registered: {model_name} ({model_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register model {model_id}: {e}")
            return False
    
    def load_model(self, model_id: str, force: bool = False) -> bool:
        """
        Load a model into memory for inference with comprehensive error handling.
        
        Args:
            model_id: ID of the model to load
            force: Force loading even if at max capacity
            
        Returns:
            True if model loaded successfully, False otherwise
            
        Raises:
            ModelLoadingError: If model loading fails with detailed diagnostics
        """
        if not LLAMA_CPP_AVAILABLE:
            error_msg = "llama-cpp-python not available for model loading"
            logger.error(error_msg)
            raise ModelLoadingError(
                message=error_msg,
                error_code=ErrorCode.LLAMA_CPP_NOT_AVAILABLE,
                model_id=model_id,
                recovery_suggestions=[
                    "Install llama-cpp-python: pip install llama-cpp-python[server]",
                    "Verify installation: python -c 'import llama_cpp'",
                    "Restart the application after installation"
                ]
            )
        
        with self.model_lock:
            # Check if already loaded
            if model_id in self.loaded_models:
                logger.info(f"Model {model_id} already loaded")
                return True
            
            # Check if model is registered
            if model_id not in self.model_configs:
                error_msg = f"Model {model_id} not registered"
                logger.error(error_msg)
                raise ModelLoadingError(
                    message=error_msg,
                    error_code=ErrorCode.MODEL_NOT_AVAILABLE,
                    model_id=model_id,
                    recovery_suggestions=[
                        f"Register model {model_id} before loading",
                        "Check available models with get_available_models()",
                        "Verify model file exists and is accessible"
                    ]
                )
            
            config = self.model_configs[model_id]
            
            # Check if model file exists
            if not Path(config.model_path).exists():
                error_msg = f"Model file not found: {config.model_path}"
                logger.error(error_msg)
                raise ModelLoadingError(
                    message=error_msg,
                    error_code=ErrorCode.MODEL_NOT_AVAILABLE,
                    model_id=model_id,
                    model_path=config.model_path,
                    recovery_suggestions=[
                        "Verify model file exists at specified path",
                        "Re-download the model if it was deleted or corrupted",
                        "Check file permissions",
                        "Update model path in configuration if file was moved"
                    ]
                )
            
            # Check system resources before loading
            try:
                resource_status = self.resource_manager.get_current_resource_status()
                memory_info = resource_status["resources"].get("memory", {})
                memory_usage = memory_info.get("usage_percent", 0)
                memory_available_gb = memory_info.get("available", 0)
                
                # Estimate memory requirement (rough estimate based on model size)
                model_size_gb = self._estimate_model_memory_requirement(config.model_path)
                
                if memory_available_gb < model_size_gb and not force:
                    error_msg = f"Insufficient memory to load model {model_id}"
                    logger.error(f"{error_msg}: requires ~{model_size_gb}GB, available {memory_available_gb}GB")
                    raise ModelLoadingError(
                        message=error_msg,
                        error_code=ErrorCode.INSUFFICIENT_MEMORY,
                        model_id=model_id,
                        model_path=config.model_path,
                        memory_required=int(model_size_gb * 1024),  # MB
                        memory_available=int(memory_available_gb * 1024),  # MB
                        recovery_suggestions=[
                            "Free up system memory by closing other applications",
                            "Unload inactive models to free memory",
                            "Use a smaller quantized model variant",
                            "Increase system RAM",
                            "Enable model auto-unloading for inactive models"
                        ]
                    )
                
            except Exception as e:
                logger.warning(f"Could not check system resources before model loading: {e}")
            
            # Check capacity
            if len(self.loaded_models) >= self.max_concurrent_models and not force:
                error_msg = f"Cannot load model {model_id}: at max capacity ({self.max_concurrent_models})"
                logger.warning(error_msg)
                
                # Try to unload an inactive model to make space
                inactive_models = self.get_inactive_models(inactive_threshold_minutes=5)
                if inactive_models:
                    oldest_inactive = inactive_models[0]
                    logger.info(f"Auto-unloading inactive model {oldest_inactive} to make space")
                    self.unload_model(oldest_inactive)
                else:
                    raise ModelLoadingError(
                        message=error_msg,
                        error_code=ErrorCode.RESOURCE_EXHAUSTION,
                        model_id=model_id,
                        details={"max_concurrent_models": self.max_concurrent_models},
                        recovery_suggestions=[
                            "Increase max_concurrent_models in configuration",
                            "Unload unused models manually",
                            "Enable automatic model unloading",
                            "Use force=True to override capacity limits"
                        ]
                    )
            
            # Attempt to load the model with timeout and error handling
            try:
                logger.info(f"Loading model: {config.model_name} from {config.model_path}")
                start_time = time.time()
                
                # Load with timeout to prevent hanging
                load_timeout = getattr(self.resource_manager.ai_settings, 'ai_model_load_timeout_seconds', 300)
                
                def load_model_with_timeout():
                    return Llama(
                        model_path=config.model_path,
                        n_ctx=config.context_length,
                        n_gpu_layers=config.n_gpu_layers if self._gpu_available() else 0,
                        n_batch=config.n_batch,
                        use_mmap=config.use_mmap,
                        use_mlock=config.use_mlock,
                        verbose=config.verbose
                    )
                
                # Use thread pool to implement timeout
                future = self.executor.submit(load_model_with_timeout)
                try:
                    llama_model = future.result(timeout=load_timeout)
                except TimeoutError:
                    future.cancel()
                    error_msg = f"Model loading timed out after {load_timeout} seconds"
                    logger.error(error_msg)
                    raise ModelLoadingError(
                        message=error_msg,
                        error_code=ErrorCode.MODEL_INFERENCE_TIMEOUT,
                        model_id=model_id,
                        model_path=config.model_path,
                        recovery_suggestions=[
                            "Increase model_load_timeout_seconds in configuration",
                            "Use a smaller model that loads faster",
                            "Check system performance and available resources",
                            "Verify model file is not corrupted"
                        ]
                    )
                
                load_time = time.time() - start_time
                
                # Store loaded model
                self.loaded_models[model_id] = (llama_model, config)
                
                # Initialize usage stats
                self.model_usage_stats[model_id] = {
                    'loaded_at': datetime.now().isoformat(),
                    'load_time_seconds': round(load_time, 2),
                    'total_queries': 0,
                    'total_tokens_generated': 0,
                    'avg_response_time': 0,
                    'last_used': None,
                    'memory_usage_mb': self._estimate_model_memory_usage(model_id)
                }
                
                # Set as active model if none set
                if self.active_model is None:
                    self.active_model = model_id
                
                logger.info(
                    f"Model {config.model_name} loaded successfully in {load_time:.2f}s "
                    f"(estimated memory: {self._estimate_model_memory_usage(model_id)}MB)"
                )
                return True
                
            except ModelLoadingError:
                # Re-raise model loading errors as-is
                raise
            except Exception as e:
                error_msg = f"Failed to load model {model_id}"
                logger.error(f"{error_msg}: {e}", exc_info=True)
                
                # Determine specific error type and provide targeted recovery suggestions
                if "out of memory" in str(e).lower() or "memory" in str(e).lower():
                    error_code = ErrorCode.INSUFFICIENT_MEMORY
                    suggestions = [
                        "Free up system memory",
                        "Use a smaller quantized model",
                        "Reduce context length (n_ctx)",
                        "Reduce GPU layers if using GPU acceleration"
                    ]
                elif "file" in str(e).lower() or "path" in str(e).lower():
                    error_code = ErrorCode.MODEL_NOT_AVAILABLE
                    suggestions = [
                        "Verify model file exists and is readable",
                        "Check file permissions",
                        "Re-download the model file"
                    ]
                elif "gpu" in str(e).lower() or "cuda" in str(e).lower():
                    error_code = ErrorCode.GPU_ACCELERATION_FAILED
                    suggestions = [
                        "Disable GPU acceleration (set n_gpu_layers=0)",
                        "Check CUDA installation and drivers",
                        "Verify GPU memory availability"
                    ]
                else:
                    error_code = ErrorCode.MODEL_LOADING_FAILED
                    suggestions = [
                        "Check model file integrity",
                        "Verify system compatibility",
                        "Try loading a different model",
                        "Check system logs for detailed error information"
                    ]
                
                raise ModelLoadingError(
                    message=f"{error_msg}: {str(e)}",
                    error_code=error_code,
                    model_id=model_id,
                    model_path=config.model_path,
                    cause=e,
                    recovery_suggestions=suggestions
                )
    
    def _estimate_model_memory_requirement(self, model_path: str) -> float:
        """Estimate memory requirement for a model in GB."""
        try:
            file_size_gb = Path(model_path).stat().st_size / (1024**3)
            # Rough estimate: model needs 1.2-1.5x its file size in memory
            return file_size_gb * 1.3
        except Exception:
            # Default estimate for unknown models
            return 2.0
    
    def _estimate_model_memory_usage(self, model_id: str) -> int:
        """Estimate current memory usage of a loaded model in MB."""
        try:
            if model_id in self.model_configs:
                config = self.model_configs[model_id]
                file_size_mb = Path(config.model_path).stat().st_size / (1024**2)
                return int(file_size_mb * 1.3)  # Rough estimate
        except Exception:
            pass
        return 1024  # Default estimate
    
    def _gpu_available(self) -> bool:
        """Check if GPU acceleration is available and enabled."""
        try:
            if not GPUTIL_AVAILABLE:
                return False
            
            gpus = GPUtil.getGPUs()
            return len(gpus) > 0 and getattr(self.resource_manager.ai_settings, 'enable_gpu_acceleration', True)
        except Exception:
            return False
    
    def unload_model(self, model_id: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            True if model unloaded successfully, False otherwise
        """
        with self.model_lock:
            if model_id not in self.loaded_models:
                logger.warning(f"Model {model_id} not loaded")
                return False
            
            try:
                # Remove from loaded models
                llama_model, config = self.loaded_models.pop(model_id)
                
                # Clean up resources (llama-cpp handles this automatically)
                del llama_model
                
                # Update active model if needed
                if self.active_model == model_id:
                    self.active_model = next(iter(self.loaded_models), None)
                
                logger.info(f"Model {config.model_name} unloaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unload model {model_id}: {e}")
                return False
    
    def hot_swap_model(self, from_model_id: str, to_model_id: str) -> bool:
        """
        Hot swap between two models.
        
        Args:
            from_model_id: Currently active model ID
            to_model_id: Model ID to switch to
            
        Returns:
            True if swap successful, False otherwise
        """
        try:
            # Load target model if not already loaded
            if to_model_id not in self.loaded_models:
                if not self.load_model(to_model_id):
                    return False
            
            # Switch active model
            with self.model_lock:
                self.active_model = to_model_id
                logger.info(f"Hot swapped from {from_model_id} to {to_model_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to hot swap models: {e}")
            return False
    
    def generate_response(self, query: str, model_id: Optional[str] = None, 
                         session_id: str = "default", **generation_kwargs) -> str:
        """
        Generate a response using the specified or active model.
        
        Args:
            query: Input query text
            model_id: Specific model to use (uses active if None)
            session_id: Conversation session ID
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ServiceUnavailableError("llama-cpp-python not available")
        
        # Determine model to use
        target_model = model_id or self.active_model
        if not target_model or target_model not in self.loaded_models:
            raise ServiceUnavailableError("No model available for inference")
        
        llama_model, config = self.loaded_models[target_model]
        
        try:
            start_time = time.time()
            
            # Get conversation context
            conversation_history = self.get_conversation_history(session_id)
            
            # Build prompt with conversation history
            prompt = self._build_prompt_with_history(query, conversation_history)
            
            # Set generation parameters
            gen_params = {
                'max_tokens': generation_kwargs.get('max_tokens', config.max_tokens),
                'temperature': generation_kwargs.get('temperature', config.temperature),
                'top_p': generation_kwargs.get('top_p', config.top_p),
                'top_k': generation_kwargs.get('top_k', config.top_k),
                'repeat_penalty': generation_kwargs.get('repeat_penalty', config.repeat_penalty),
                'stop': generation_kwargs.get('stop', [])
            }
            
            # Generate response
            response = llama_model(prompt, **gen_params)
            
            # Extract generated text
            generated_text = response['choices'][0]['text'].strip()
            
            # Update conversation history
            self.add_to_conversation_history(session_id, HumanMessage(content=query))
            self.add_to_conversation_history(session_id, AIMessage(content=generated_text))
            
            # Update usage statistics
            end_time = time.time()
            response_time = end_time - start_time
            tokens_generated = response['usage']['completion_tokens']
            
            self._update_model_stats(target_model, response_time, tokens_generated)
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise AIProcessingError(f"Response generation failed: {str(e)}")
    
    def _build_prompt_with_history(self, query: str, history: List) -> str:
        """Build a prompt including conversation history with enhanced security context"""
        prompt_parts = []
        
        # Enhanced security-focused system context
        system_context = """You are an expert cybersecurity analyst and threat hunter with deep expertise in:

🔍 **Threat Hunting & Detection:**
- Advanced persistent threat (APT) analysis using MITRE ATT&CK framework
- Behavioral analysis and anomaly detection techniques
- Threat intelligence correlation and IOC development
- Network traffic analysis and endpoint telemetry interpretation

🚨 **Incident Response & Investigation:**
- Security incident containment, eradication, and recovery procedures
- Digital forensics and malware analysis techniques
- Timeline reconstruction and attack pattern recognition
- Impact assessment and damage evaluation methodologies

🛡️ **Security Analysis & Operations:**
- SIEM platform expertise (Wazuh, Splunk, Elastic Stack)
- Log analysis and correlation across multiple data sources
- Risk assessment and vulnerability management
- Compliance frameworks (SOX, PCI-DSS, HIPAA, NIST)

**Your Mission:** Provide comprehensive, actionable security analysis that helps analysts identify threats, investigate incidents, and strengthen security posture. Always include specific SIEM queries, investigation steps, and risk assessments in your responses.

**Response Format:** Use security icons (🔍, 🛡️, ⚠️, 🚨, ✅) and structured sections for clarity."""
        
        prompt_parts.append(f"System: {system_context}\n")
        
        # Add conversation history with security context preservation
        for message in history[-8:]:  # Increased to 4 exchanges for better context
            if hasattr(message, 'content'):
                if isinstance(message, HumanMessage):
                    prompt_parts.append(f"Security Analyst: {message.content}\n")
                elif isinstance(message, AIMessage):
                    prompt_parts.append(f"Cybersecurity AI: {message.content}\n")
        
        # Add current query with security focus
        prompt_parts.append(f"Security Analyst: {query}\nCybersecurity AI: ")
        
        return "".join(prompt_parts)
    
    def _update_model_stats(self, model_id: str, response_time: float, tokens_generated: int) -> None:
        """Update usage statistics for a model"""
        if model_id in self.model_usage_stats:
            stats = self.model_usage_stats[model_id]
            stats['total_queries'] += 1
            stats['total_tokens_generated'] += tokens_generated
            stats['last_used'] = datetime.now().isoformat()
            
            # Update average response time
            total_queries = stats['total_queries']
            current_avg = stats['avg_response_time']
            stats['avg_response_time'] = (current_avg * (total_queries - 1) + response_time) / total_queries
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get information about currently loaded models"""
        models = []
        
        with self.model_lock:
            for model_id, (llama_model, config) in self.loaded_models.items():
                stats = self.model_usage_stats.get(model_id, {})
                
                models.append({
                    'id': model_id,
                    'name': config.model_name,
                    'is_active': model_id == self.active_model,
                    'config': {
                        'context_length': config.context_length,
                        'n_gpu_layers': config.n_gpu_layers,
                        'temperature': config.temperature,
                        'max_tokens': config.max_tokens
                    },
                    'stats': stats
                })
        
        return models
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get information about all registered models"""
        models = []
        
        for model_id, config in self.model_configs.items():
            is_loaded = model_id in self.loaded_models
            stats = self.model_usage_stats.get(model_id, {}) if is_loaded else {}
            
            models.append({
                'id': model_id,
                'name': config.model_name,
                'path': config.model_path,
                'is_loaded': is_loaded,
                'is_active': model_id == self.active_model,
                'config': {
                    'context_length': config.context_length,
                    'n_gpu_layers': config.n_gpu_layers,
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens
                },
                'stats': stats
            })
        
        return models
    
    def update_model_config(self, model_id: str, **config_updates) -> bool:
        """Update configuration for a model"""
        if model_id not in self.model_configs:
            return False
        
        try:
            config = self.model_configs[model_id]
            
            # Update configuration
            for key, value in config_updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # If model is loaded, need to reload for some config changes
            needs_reload = any(key in ['context_length', 'n_gpu_layers', 'n_batch'] 
                             for key in config_updates.keys())
            
            if needs_reload and model_id in self.loaded_models:
                self.unload_model(model_id)
                self.load_model(model_id)
            
            self._save_model_configurations()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update model config {model_id}: {e}")
            return False
    
    # Vector store methods (inherited from original AIService)
    def create_vectorstore(self, logs: List[Dict[str, Any]]) -> FAISS:
        """Create a FAISS vector store from log data."""
        if not logs:
            raise AIProcessingError("Cannot create vector store: no logs provided")
        
        if not self.embedding_model:
            raise AIProcessingError("Embedding model not initialized")
        
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, 
                chunk_overlap=50
            )
            documents = []
            
            for log in logs:
                full_log = log.get('full_log', '')
                if full_log:
                    splits = text_splitter.split_text(full_log)
                    for chunk in splits:
                        documents.append(Document(page_content=chunk))
            
            if not documents:
                raise AIProcessingError("No valid documents found in logs")
            
            self.vectorstore = FAISS.from_documents(documents, self.embedding_model)
            return self.vectorstore
            
        except Exception as e:
            raise AIProcessingError(f"Failed to create vector store: {str(e)}")
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform similarity search in the vector store."""
        if not self.vectorstore:
            raise AIProcessingError("Vector store not initialized")
        
        try:
            similar_docs = self.vectorstore.similarity_search(query, k=k)
            return similar_docs
        except Exception as e:
            raise AIProcessingError(f"Similarity search failed: {str(e)}")
    
    # Conversation management methods
    def create_conversation_session(self, session_id: str, security_context: str = "general") -> None:
        """Create a new conversation session with security context."""
        # Enhanced security-focused system message based on context
        security_contexts = {
            "threat_hunting": "🔍 **Threat Hunting Assistant Ready** - I'm specialized in proactive threat detection, APT analysis, and behavioral anomaly identification using MITRE ATT&CK framework. I can help you hunt for advanced threats, develop IOCs, and analyze attack patterns.",
            
            "incident_investigation": "🚨 **Incident Response Assistant Ready** - I'm specialized in security incident investigation, digital forensics, and containment procedures. I can help you investigate breaches, analyze malware, reconstruct attack timelines, and develop response strategies.",
            
            "vulnerability_analysis": "⚠️ **Vulnerability Assessment Assistant Ready** - I'm specialized in security weakness identification, risk assessment, and remediation planning. I can help you prioritize vulnerabilities, assess exploit likelihood, and develop mitigation strategies.",
            
            "general": "🛡️ **Cybersecurity Assistant Ready** - I'm your comprehensive security analysis partner with expertise across threat hunting, incident response, vulnerability management, and compliance. I can help with any security-related analysis or investigation."
        }
        
        system_message_content = security_contexts.get(security_context, security_contexts["general"])
        
        self.conversation_sessions[session_id] = {
            "history": [SystemMessage(content=system_message_content)],
            "security_context": security_context,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "query_count": 0,
            "threat_indicators_discussed": [],
            "investigation_topics": []
        }
    
    def get_conversation_history(self, session_id: str) -> List:
        """Get conversation history for a session."""
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        return self.conversation_sessions[session_id]["history"]
    
    def get_security_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get security-focused conversation context for enhanced analysis."""
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        session = self.conversation_sessions[session_id]
        
        return {
            "security_context": session.get("security_context", "general"),
            "query_count": session.get("query_count", 0),
            "threat_indicators_discussed": session.get("threat_indicators_discussed", []),
            "investigation_topics": session.get("investigation_topics", []),
            "session_duration": (datetime.now() - session["created_at"]).total_seconds(),
            "last_activity": session["last_activity"].isoformat(),
            "message_count": len(session["history"])
        }
    
    def add_to_conversation_history(self, session_id: str, message: Any) -> None:
        """Add a message to conversation history with security context preservation."""
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        session = self.conversation_sessions[session_id]
        session["history"].append(message)
        session["last_activity"] = datetime.now()
        session["query_count"] = session.get("query_count", 0) + 1
        
        # Extract and track security indicators from messages
        if isinstance(message, HumanMessage):
            content_lower = message.content.lower()
            
            # Track threat indicators mentioned
            threat_keywords = ['malware', 'apt', 'breach', 'compromise', 'attack', 'threat', 'suspicious']
            for keyword in threat_keywords:
                if keyword in content_lower and keyword not in session.get("threat_indicators_discussed", []):
                    session.setdefault("threat_indicators_discussed", []).append(keyword)
            
            # Track investigation topics
            investigation_keywords = ['investigate', 'analyze', 'hunt', 'forensic', 'incident']
            for keyword in investigation_keywords:
                if keyword in content_lower and keyword not in session.get("investigation_topics", []):
                    session.setdefault("investigation_topics", []).append(keyword)
        
        # Enhanced history management with security context preservation
        max_history = self.conversation_memory_size * 2 + 1
        if len(session["history"]) > max_history:
            system_msg = session["history"][0]  # Always preserve system message
            
            # Keep more recent messages but ensure we preserve important security context
            recent_messages = session["history"][-(self.conversation_memory_size * 2):]
            
            # Try to preserve messages with high security relevance
            security_relevant_messages = []
            for msg in session["history"][1:-len(recent_messages)]:  # Messages between system and recent
                if hasattr(msg, 'content'):
                    content_lower = msg.content.lower()
                    if any(keyword in content_lower for keyword in ['critical', 'urgent', 'breach', 'compromise', 'malware', 'apt']):
                        security_relevant_messages.append(msg)
            
            # Combine system message, important security messages, and recent messages
            preserved_messages = [system_msg]
            if security_relevant_messages:
                preserved_messages.extend(security_relevant_messages[-2:])  # Keep last 2 critical messages
            preserved_messages.extend(recent_messages)
            
            session["history"] = preserved_messages
    
    def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self.conversation_sessions:
            self.conversation_sessions[session_id]["history"] = [
                SystemMessage(content="Security analysis assistant ready.")
            ]
            self.conversation_sessions[session_id]["last_activity"] = datetime.now()
    
    def is_ready(self) -> bool:
        """Check if the service is ready to process requests."""
        return (
            self.embedding_model is not None and
            len(self.loaded_models) > 0 and
            self.active_model is not None
        )
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        system_stats = self.get_system_stats()
        
        return {
            'service_ready': self.is_ready(),
            'llama_cpp_available': LLAMA_CPP_AVAILABLE,
            'loaded_models': len(self.loaded_models),
            'active_model': self.active_model,
            'total_registered_models': len(self.model_configs),
            'max_concurrent_models': self.max_concurrent_models,
            'conversation_sessions': len(self.conversation_sessions),
            'system_stats': {
                'cpu_percent': system_stats.cpu_percent,
                'memory_used_gb': round(system_stats.memory_used / (1024**3), 2),
                'memory_total_gb': round(system_stats.memory_total / (1024**3), 2),
                'memory_percent': round((system_stats.memory_used / system_stats.memory_total) * 100, 1),
                'gpu_count': len(system_stats.gpu_stats),
                'gpu_stats': system_stats.gpu_stats
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_inactive_models(self, inactive_threshold_minutes: int = 30) -> List[str]:
        """Get list of inactive models that can be unloaded to free resources."""
        inactive_models = []
        current_time = datetime.now()
        threshold = timedelta(minutes=inactive_threshold_minutes)
        
        with self.model_lock:
            for model_id, stats in self.model_usage_stats.items():
                if model_id not in self.loaded_models:
                    continue
                
                # Skip active model
                if model_id == self.active_model:
                    continue
                
                # Check last used time
                last_used_str = stats.get('last_used')
                if last_used_str:
                    try:
                        last_used = datetime.fromisoformat(last_used_str)
                        if current_time - last_used > threshold:
                            inactive_models.append(model_id)
                    except Exception:
                        # If we can't parse the date, consider it inactive
                        inactive_models.append(model_id)
                else:
                    # Never used, consider inactive
                    inactive_models.append(model_id)
        
        # Sort by last used time (oldest first)
        def get_last_used_time(model_id):
            stats = self.model_usage_stats.get(model_id, {})
            last_used_str = stats.get('last_used')
            if last_used_str:
                try:
                    return datetime.fromisoformat(last_used_str)
                except Exception:
                    pass
            return datetime.min
        
        inactive_models.sort(key=get_last_used_time)
        return inactive_models
    
    def reduce_resource_usage(self) -> bool:
        """Reduce resource usage by optimizing model configurations."""
        try:
            # Reduce batch sizes for all loaded models
            with self.model_lock:
                for model_id, (llama_model, config) in self.loaded_models.items():
                    if config.n_batch > 256:
                        config.n_batch = max(256, config.n_batch // 2)
                        logger.info(f"Reduced batch size for model {model_id} to {config.n_batch}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to reduce resource usage: {e}")
            return False
    
    def optimize_gpu_usage(self) -> bool:
        """Optimize GPU usage by reducing GPU layers or switching to CPU."""
        try:
            with self.model_lock:
                for model_id, (llama_model, config) in self.loaded_models.items():
                    if config.n_gpu_layers > 0:
                        # Reduce GPU layers by half
                        config.n_gpu_layers = max(0, config.n_gpu_layers // 2)
                        logger.info(f"Reduced GPU layers for model {model_id} to {config.n_gpu_layers}")
                        
                        # Note: This would require reloading the model to take effect
                        # For now, just update the config for future loads
            
            return True
        except Exception as e:
            logger.error(f"Failed to optimize GPU usage: {e}")
            return False
    
    def cleanup_model_cache(self) -> bool:
        """Clean up model cache to free disk space."""
        try:
            # This would implement cache cleanup logic
            # For now, just log the action
            logger.info("Model cache cleanup requested")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup model cache: {e}")
            return False
    
    def get_service_health_detailed(self) -> Dict[str, Any]:
        """Get detailed service health information for operations teams."""
        try:
            basic_status = self.get_service_status()
            resource_status = self.resource_manager.get_current_resource_status()
            
            # Add detailed diagnostics
            detailed_status = {
                **basic_status,
                "resource_status": resource_status,
                "initialization_errors": self.initialization_errors,
                "service_degraded": self.service_degraded,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "backup_models_available": len(self.backup_models),
                "fallback_model_id": self.fallback_model_id,
                "model_details": []
            }
            
            # Add detailed model information
            with self.model_lock:
                for model_id, (llama_model, config) in self.loaded_models.items():
                    stats = self.model_usage_stats.get(model_id, {})
                    model_detail = {
                        "model_id": model_id,
                        "model_name": config.model_name,
                        "model_path": config.model_path,
                        "is_active": model_id == self.active_model,
                        "memory_usage_mb": stats.get('memory_usage_mb', 0),
                        "load_time_seconds": stats.get('load_time_seconds', 0),
                        "total_queries": stats.get('total_queries', 0),
                        "avg_response_time": stats.get('avg_response_time', 0),
                        "last_used": stats.get('last_used'),
                        "config": {
                            "context_length": config.context_length,
                            "n_gpu_layers": config.n_gpu_layers,
                            "n_batch": config.n_batch,
                            "temperature": config.temperature
                        }
                    }
                    detailed_status["model_details"].append(model_detail)
            
            # Add resource recommendations
            detailed_status["resource_recommendations"] = self.resource_manager.generate_resource_recommendations()
            
            # Update last health check time
            self.last_health_check = datetime.now()
            
            return detailed_status
            
        except Exception as e:
            logger.error(f"Failed to get detailed service health: {e}")
            return {
                "error": f"Health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def generate_recovery_plan(self, error: Exception) -> Dict[str, Any]:
        """Generate a recovery plan for operations teams based on the error."""
        recovery_plan = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "immediate_actions": [],
            "investigation_steps": [],
            "prevention_measures": [],
            "escalation_criteria": []
        }
        
        if isinstance(error, ModelLoadingError):
            recovery_plan.update({
                "immediate_actions": [
                    "Check system memory and disk space availability",
                    "Verify model file exists and is accessible",
                    "Try loading a smaller backup model",
                    "Restart embedded AI service if needed"
                ],
                "investigation_steps": [
                    "Review system resource usage trends",
                    "Check model file integrity",
                    "Verify configuration settings",
                    "Examine system logs for detailed error information"
                ],
                "prevention_measures": [
                    "Enable automatic resource monitoring",
                    "Configure backup models for fallback",
                    "Set up proactive memory management",
                    "Implement model usage analytics"
                ],
                "escalation_criteria": [
                    "Multiple model loading failures within 1 hour",
                    "System resources consistently above 90%",
                    "No backup models available",
                    "Service unavailable for more than 15 minutes"
                ]
            })
        elif isinstance(error, ResourceExhaustionError):
            recovery_plan.update({
                "immediate_actions": [
                    "Free up system resources immediately",
                    "Unload inactive AI models",
                    "Clear temporary files and caches",
                    "Switch to fallback model if available"
                ],
                "investigation_steps": [
                    "Identify resource consumption patterns",
                    "Review recent system changes",
                    "Check for memory leaks or runaway processes",
                    "Analyze resource usage trends"
                ],
                "prevention_measures": [
                    "Implement automatic resource management",
                    "Set up resource usage alerts",
                    "Configure model auto-unloading",
                    "Plan for horizontal scaling"
                ],
                "escalation_criteria": [
                    "Resource exhaustion persists after cleanup",
                    "System becomes unresponsive",
                    "Multiple services affected",
                    "Business operations impacted"
                ]
            })
        else:
            recovery_plan.update({
                "immediate_actions": [
                    "Check service status and logs",
                    "Restart affected services",
                    "Verify system connectivity",
                    "Switch to backup systems if available"
                ],
                "investigation_steps": [
                    "Review error logs and stack traces",
                    "Check system dependencies",
                    "Verify configuration settings",
                    "Test individual components"
                ],
                "prevention_measures": [
                    "Implement comprehensive monitoring",
                    "Set up automated health checks",
                    "Create backup and recovery procedures",
                    "Document troubleshooting procedures"
                ],
                "escalation_criteria": [
                    "Error persists after initial recovery attempts",
                    "Multiple systems affected",
                    "Data integrity concerns",
                    "Extended service outage"
                ]
            })
        
        return recovery_plan
    
    def shutdown(self):
        """Gracefully shutdown the service with comprehensive cleanup."""
        logger.info("Shutting down Embedded AI Service...")
        
        try:
            # Stop resource monitoring
            if self.resource_manager.monitoring_active:
                self.resource_manager.stop_monitoring()
            
            # Unload all models
            with self.model_lock:
                for model_id in list(self.loaded_models.keys()):
                    try:
                        self.unload_model(model_id)
                    except Exception as e:
                        logger.error(f"Error unloading model {model_id} during shutdown: {e}")
            
            # Clear conversation sessions
            self.conversation_sessions.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Embedded AI Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
            raise