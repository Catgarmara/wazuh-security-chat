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
    logging.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.schema.messages import SystemMessage, HumanMessage, AIMessage
from core.exceptions import AIProcessingError, ServiceUnavailableError

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
        Initialize the Embedded AI service.
        
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
        
        # Conversation management
        self.conversation_sessions = {}
        self.active_model = None
        
        # System monitoring
        self.system_stats_cache = None
        self.stats_cache_time = None
        self.stats_cache_duration = 5  # seconds
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embedded_ai")
        
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize the service components"""
        try:
            # Create directories
            self.models_path.mkdir(parents=True, exist_ok=True)
            self.vectorstore_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize embedding model
            self.embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            
            # Load existing model configurations
            self._load_model_configurations()
            
            logger.info("Embedded AI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Embedded AI Service: {e}")
            raise AIProcessingError(f"Service initialization failed: {str(e)}")
    
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
        Load a model into memory for inference.
        
        Args:
            model_id: ID of the model to load
            force: Force loading even if at max capacity
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python not available")
            return False
        
        with self.model_lock:
            # Check if already loaded
            if model_id in self.loaded_models:
                logger.info(f"Model {model_id} already loaded")
                return True
            
            # Check if model is registered
            if model_id not in self.model_configs:
                logger.error(f"Model {model_id} not registered")
                return False
            
            # Check capacity
            if len(self.loaded_models) >= self.max_concurrent_models and not force:
                logger.warning(f"Cannot load model {model_id}: at max capacity ({self.max_concurrent_models})")
                return False
            
            config = self.model_configs[model_id]
            
            try:
                # Load the model
                logger.info(f"Loading model: {config.model_name}")
                
                llama_model = Llama(
                    model_path=config.model_path,
                    n_ctx=config.context_length,
                    n_gpu_layers=config.n_gpu_layers,
                    n_batch=config.n_batch,
                    use_mmap=config.use_mmap,
                    use_mlock=config.use_mlock,
                    verbose=config.verbose
                )
                
                # Store loaded model
                self.loaded_models[model_id] = (llama_model, config)
                
                # Initialize usage stats
                self.model_usage_stats[model_id] = {
                    'loaded_at': datetime.now().isoformat(),
                    'total_queries': 0,
                    'total_tokens_generated': 0,
                    'avg_response_time': 0,
                    'last_used': None
                }
                
                # Set as active model if none set
                if self.active_model is None:
                    self.active_model = model_id
                
                logger.info(f"Model {config.model_name} loaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model {model_id}: {e}")
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
        """Build a prompt including conversation history"""
        prompt_parts = []
        
        # Add system context
        system_context = """You are a security analyst performing threat hunting.
Your task is to analyze logs from Wazuh. You have access to the logs stored in the vector store.
The objective is to identify potential security threats or any other needs from the user.
All queries should be interpreted as asking about security events, patterns or other request from the user using the vectorized logs."""
        
        prompt_parts.append(f"System: {system_context}\n")
        
        # Add conversation history (last few turns)
        for message in history[-6:]:  # Last 3 exchanges
            if hasattr(message, 'content'):
                if isinstance(message, HumanMessage):
                    prompt_parts.append(f"Human: {message.content}\n")
                elif isinstance(message, AIMessage):
                    prompt_parts.append(f"Assistant: {message.content}\n")
        
        # Add current query
        prompt_parts.append(f"Human: {query}\nAssistant: ")
        
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
    def create_conversation_session(self, session_id: str) -> None:
        """Create a new conversation session."""
        self.conversation_sessions[session_id] = {
            "history": [SystemMessage(content="Security analysis assistant ready.")],
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
    
    def get_conversation_history(self, session_id: str) -> List:
        """Get conversation history for a session."""
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        return self.conversation_sessions[session_id]["history"]
    
    def add_to_conversation_history(self, session_id: str, message: Any) -> None:
        """Add a message to conversation history."""
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        session = self.conversation_sessions[session_id]
        session["history"].append(message)
        session["last_activity"] = datetime.now()
        
        # Limit history size
        if len(session["history"]) > self.conversation_memory_size * 2 + 1:
            system_msg = session["history"][0]
            recent_messages = session["history"][-(self.conversation_memory_size * 2):]
            session["history"] = [system_msg] + recent_messages
    
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
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        logger.info("Shutting down Embedded AI Service...")
        
        # Unload all models
        with self.model_lock:
            for model_id in list(self.loaded_models.keys()):
                self.unload_model(model_id)
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("Embedded AI Service shutdown complete")