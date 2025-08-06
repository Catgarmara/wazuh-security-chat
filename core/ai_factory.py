"""
AI Service Factory Module

Provides a centralized factory for creating and managing AI service instances.
This factory ensures that only EmbeddedAIService is used throughout the application,
replacing the previous Ollama-dependent architecture.
"""

import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AIServiceFactory:
    """
    Factory class for managing AI service instances.
    
    This factory provides a single point of access to the EmbeddedAIService,
    ensuring consistent service initialization and management across the application.
    """
    
    _instance: Optional['AIServiceFactory'] = None
    _lock = threading.Lock()
    _ai_service_instance = None
    _ai_service_lock = threading.Lock()
    
    def __new__(cls) -> 'AIServiceFactory':
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the factory"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._service_config = {}
            self._initialization_time = None
            logger.info("AI Service Factory initialized")
    
    @staticmethod
    def get_ai_service() -> Optional['EmbeddedAIService']:
        """
        Get the EmbeddedAIService singleton instance.
        
        Returns:
            EmbeddedAIService instance or None if initialization fails
        """
        factory = AIServiceFactory()
        return factory._get_service_instance()
    
    def _get_service_instance(self) -> Optional['EmbeddedAIService']:
        """
        Internal method to get or create the AI service instance.
        
        Returns:
            EmbeddedAIService instance or None if not available
        """
        if self._ai_service_instance is None:
            with self._ai_service_lock:
                if self._ai_service_instance is None:
                    self._ai_service_instance = self._create_ai_service()
        
        return self._ai_service_instance
    
    def _create_ai_service(self) -> Optional['EmbeddedAIService']:
        """
        Create a new EmbeddedAIService instance.
        
        Returns:
            EmbeddedAIService instance or None if creation fails
        """
        try:
            # Import here to avoid circular imports
            from services.embedded_ai_service import EmbeddedAIService
            
            logger.info("Creating new EmbeddedAIService instance")
            
            # Create service with default or configured parameters
            service = EmbeddedAIService(
                models_path=self._service_config.get('models_path', './models'),
                vectorstore_path=self._service_config.get('vectorstore_path', './data/vectorstore'),
                embedding_model_name=self._service_config.get('embedding_model_name', 'all-MiniLM-L6-v2'),
                max_concurrent_models=self._service_config.get('max_concurrent_models', 3),
                conversation_memory_size=self._service_config.get('conversation_memory_size', 10)
            )
            
            self._initialization_time = datetime.now()
            logger.info("EmbeddedAIService instance created successfully")
            
            return service
            
        except ImportError as e:
            logger.error(f"Failed to import EmbeddedAIService: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create EmbeddedAIService instance: {e}")
            return None
    
    @staticmethod
    def initialize_ai_service(config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the AI service with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the AI service
            
        Returns:
            True if initialization successful, False otherwise
        """
        factory = AIServiceFactory()
        return factory._initialize_service(config)
    
    def _initialize_service(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Internal method to initialize the AI service.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if config:
                self._service_config.update(config)
                logger.info(f"AI service configuration updated: {list(config.keys())}")
            
            # Force recreation of service instance with new config
            with self._ai_service_lock:
                if self._ai_service_instance is not None:
                    logger.info("Shutting down existing AI service instance")
                    try:
                        self._ai_service_instance.shutdown()
                    except Exception as e:
                        logger.warning(f"Error during service shutdown: {e}")
                
                self._ai_service_instance = None
            
            # Create new instance
            service = self._get_service_instance()
            
            if service is None:
                logger.error("Failed to initialize AI service")
                return False
            
            logger.info("AI service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            return False
    
    @staticmethod
    def shutdown_ai_service() -> None:
        """
        Shutdown the AI service and clean up resources.
        """
        factory = AIServiceFactory()
        factory._shutdown_service()
    
    def _shutdown_service(self) -> None:
        """
        Internal method to shutdown the AI service.
        """
        try:
            with self._ai_service_lock:
                if self._ai_service_instance is not None:
                    logger.info("Shutting down AI service")
                    self._ai_service_instance.shutdown()
                    self._ai_service_instance = None
                    logger.info("AI service shutdown complete")
                else:
                    logger.info("AI service was not running")
        except Exception as e:
            logger.error(f"Error during AI service shutdown: {e}")
    
    @staticmethod
    def is_service_ready() -> bool:
        """
        Check if the AI service is ready to process requests.
        
        Returns:
            True if service is ready, False otherwise
        """
        factory = AIServiceFactory()
        return factory._is_service_ready()
    
    def _is_service_ready(self) -> bool:
        """
        Internal method to check service readiness.
        
        Returns:
            True if service is ready, False otherwise
        """
        try:
            service = self._get_service_instance()
            if service is None:
                return False
            
            return service.is_ready()
            
        except Exception as e:
            logger.error(f"Error checking service readiness: {e}")
            return False
    
    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """
        Get comprehensive status information about the AI service.
        
        Returns:
            Dictionary containing service status information
        """
        factory = AIServiceFactory()
        return factory._get_service_status()
    
    def _get_service_status(self) -> Dict[str, Any]:
        """
        Internal method to get service status.
        
        Returns:
            Dictionary containing service status information
        """
        try:
            service = self._get_service_instance()
            
            base_status = {
                'factory_initialized': self._initialized,
                'service_instance_created': service is not None,
                'initialization_time': self._initialization_time.isoformat() if self._initialization_time else None,
                'service_config': self._service_config.copy()
            }
            
            if service is not None:
                service_status = service.get_service_status()
                base_status.update(service_status)
            else:
                base_status.update({
                    'service_ready': False,
                    'error': 'Service instance not available'
                })
            
            return base_status
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                'factory_initialized': getattr(self, '_initialized', False),
                'service_instance_created': False,
                'service_ready': False,
                'error': str(e)
            }
    
    @staticmethod
    def reset_factory() -> None:
        """
        Reset the factory instance (useful for testing).
        """
        with AIServiceFactory._lock:
            if AIServiceFactory._instance is not None:
                AIServiceFactory._instance._shutdown_service()
                AIServiceFactory._instance = None
        logger.info("AI Service Factory reset")


# Convenience functions for backward compatibility and ease of use
def get_ai_service():
    """Convenience function to get AI service instance"""
    return AIServiceFactory.get_ai_service()

def initialize_ai_service(config: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience function to initialize AI service"""
    return AIServiceFactory.initialize_ai_service(config)

def shutdown_ai_service() -> None:
    """Convenience function to shutdown AI service"""
    AIServiceFactory.shutdown_ai_service()

def is_ai_service_ready() -> bool:
    """Convenience function to check AI service readiness"""
    return AIServiceFactory.is_service_ready()

def get_ai_service_status() -> Dict[str, Any]:
    """Convenience function to get AI service status"""
    return AIServiceFactory.get_service_status()