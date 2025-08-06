# Business logic services

import threading
from typing import Optional

# Import services conditionally to handle missing dependencies
__all__ = [
    'get_ai_service',
    'initialize_ai_service',
    'is_ai_service_ready',
    'get_ai_service_status',
    'get_log_service', 
    'get_chat_service',
    'get_auth_service',
    'get_analytics_service',
    'reset_service_instances'
]

try:
    from .embedded_ai_service import EmbeddedAIService
    __all__.append('EmbeddedAIService')
except ImportError:
    EmbeddedAIService = None

try:
    from .auth_service import AuthService
    __all__.append('AuthService')
except ImportError:
    AuthService = None

try:
    from .rbac_service import RBACService
    __all__.append('RBACService')
except ImportError:
    RBACService = None

try:
    from .log_service import LogService
    __all__.append('LogService')
except ImportError:
    LogService = None

try:
    from .chat_service import ChatService
    __all__.append('ChatService')
except ImportError:
    ChatService = None

try:
    from .analytics_service import AnalyticsService
    __all__.append('AnalyticsService')
except ImportError:
    AnalyticsService = None

# Import AI service factory
try:
    from core.ai_factory import AIServiceFactory
except ImportError:
    AIServiceFactory = None

# Singleton instances for non-AI services
_log_service_instance: Optional[LogService] = None
_chat_service_instance: Optional[ChatService] = None
_auth_service_instance: Optional[AuthService] = None
_analytics_service_instance: Optional[AnalyticsService] = None

# Thread locks for singleton creation
_log_service_lock = threading.Lock()
_chat_service_lock = threading.Lock()
_auth_service_lock = threading.Lock()
_analytics_service_lock = threading.Lock()


def get_ai_service() -> Optional[EmbeddedAIService]:
    """
    Get Embedded AI service singleton instance using AIServiceFactory.
    
    Returns:
        EmbeddedAIService instance or None if not available
    """
    if AIServiceFactory is None:
        print("AIServiceFactory not available")
        return None
    
    try:
        return AIServiceFactory.get_ai_service()
    except Exception as e:
        print(f"Failed to get AI service from factory: {e}")
        return None


def get_log_service() -> Optional[LogService]:
    """
    Get Log service singleton instance.
    
    Returns:
        LogService instance or None if not available
    """
    global _log_service_instance
    
    if LogService is None:
        return None
    
    if _log_service_instance is None:
        with _log_service_lock:
            if _log_service_instance is None:
                try:
                    _log_service_instance = LogService()
                except Exception as e:
                    print(f"Failed to initialize Log service: {e}")
                    return None
    
    return _log_service_instance


def get_chat_service() -> Optional[ChatService]:
    """
    Get Chat service singleton instance.
    
    Returns:
        ChatService instance or None if not available
    """
    global _chat_service_instance
    
    if ChatService is None:
        return None
    
    if _chat_service_instance is None:
        with _chat_service_lock:
            if _chat_service_instance is None:
                try:
                    _chat_service_instance = ChatService()
                except Exception as e:
                    print(f"Failed to initialize Chat service: {e}")
                    return None
    
    return _chat_service_instance


def get_auth_service() -> Optional[AuthService]:
    """
    Get Auth service singleton instance.
    
    Returns:
        AuthService instance or None if not available
    """
    global _auth_service_instance
    
    if AuthService is None:
        return None
    
    if _auth_service_instance is None:
        with _auth_service_lock:
            if _auth_service_instance is None:
                try:
                    _auth_service_instance = AuthService()
                except Exception as e:
                    print(f"Failed to initialize Auth service: {e}")
                    return None
    
    return _auth_service_instance


def get_analytics_service() -> Optional[AnalyticsService]:
    """
    Get Analytics service singleton instance.
    
    Returns:
        AnalyticsService instance or None if not available
    """
    global _analytics_service_instance
    
    if AnalyticsService is None:
        return None
    
    if _analytics_service_instance is None:
        with _analytics_service_lock:
            if _analytics_service_instance is None:
                try:
                    _analytics_service_instance = AnalyticsService()
                except Exception as e:
                    print(f"Failed to initialize Analytics service: {e}")
                    return None
    
    return _analytics_service_instance


def initialize_ai_service(config=None):
    """
    Initialize the AI service with optional configuration.
    
    Args:
        config: Optional configuration dictionary for the AI service
        
    Returns:
        True if initialization successful, False otherwise
    """
    if AIServiceFactory is None:
        print("AIServiceFactory not available")
        return False
    
    try:
        return AIServiceFactory.initialize_ai_service(config)
    except Exception as e:
        print(f"Failed to initialize AI service: {e}")
        return False


def is_ai_service_ready():
    """
    Check if the AI service is ready to process requests.
    
    Returns:
        True if service is ready, False otherwise
    """
    if AIServiceFactory is None:
        return False
    
    try:
        return AIServiceFactory.is_service_ready()
    except Exception as e:
        print(f"Failed to check AI service readiness: {e}")
        return False


def get_ai_service_status():
    """
    Get comprehensive status information about the AI service.
    
    Returns:
        Dictionary containing service status information
    """
    if AIServiceFactory is None:
        return {'error': 'AIServiceFactory not available'}
    
    try:
        return AIServiceFactory.get_service_status()
    except Exception as e:
        print(f"Failed to get AI service status: {e}")
        return {'error': str(e)}


def reset_service_instances():
    """
    Reset all service instances (useful for testing).
    """
    global _log_service_instance, _chat_service_instance
    global _auth_service_instance, _analytics_service_instance
    
    # Reset AI service through factory
    if AIServiceFactory is not None:
        try:
            AIServiceFactory.reset_factory()
        except Exception as e:
            print(f"Failed to reset AI service factory: {e}")
    
    # Reset other service instances
    _log_service_instance = None
    _chat_service_instance = None
    _auth_service_instance = None
    _analytics_service_instance = None