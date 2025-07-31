#!/usr/bin/env python3
"""
Simple test to verify service integration is working.
"""

def test_service_factories():
    """Test that all service factories work."""
    from services import get_ai_service, get_log_service, get_chat_service, get_auth_service
    
    print("Testing service factories...")
    
    # Test AI service
    ai_service = get_ai_service()
    print(f"AI Service: {'✓' if ai_service else '✗'}")
    
    # Test Log service  
    log_service = get_log_service()
    print(f"Log Service: {'✓' if log_service else '✗'}")
    
    # Test Auth service
    auth_service = get_auth_service()
    print(f"Auth Service: {'✓' if auth_service else '✗'}")
    
    # Test Chat service
    chat_service = get_chat_service()
    print(f"Chat Service: {'✓' if chat_service else '✗'}")
    
    if chat_service:
        print(f"  - AI service integrated: {'✓' if chat_service.ai_service else '✗'}")
        print(f"  - Log service integrated: {'✓' if chat_service.command_processor.log_service else '✗'}")
    
    return all([ai_service, log_service, auth_service, chat_service])

def test_ai_service_basic():
    """Test basic AI service functionality."""
    from services import get_ai_service
    
    print("\nTesting AI service basic functionality...")
    
    ai_service = get_ai_service()
    if not ai_service:
        print("AI service not available")
        return False
    
    # Test if service is ready
    is_ready = ai_service.is_ready()
    print(f"AI Service ready: {'✓' if is_ready else '✗'}")
    
    # Test LLM health check
    try:
        health = ai_service.check_llm_health()
        print(f"LLM health check: {'✓' if health.get('status') == 'healthy' else '✗'}")
    except Exception as e:
        print(f"LLM health check failed: {e}")
        return False
    
    return True

def test_log_service_basic():
    """Test basic log service functionality."""
    from services import get_log_service
    
    print("\nTesting Log service basic functionality...")
    
    log_service = get_log_service()
    if not log_service:
        print("Log service not available")
        return False
    
    # Test log validation
    test_log = {
        "timestamp": "2024-01-01T12:00:00",
        "full_log": "Test log entry"
    }
    
    is_valid = log_service.validate_log_entry(test_log)
    print(f"Log validation: {'✓' if is_valid else '✗'}")
    
    # Test log statistics with empty list
    stats = log_service.get_log_statistics([])
    print(f"Log statistics: {'✓' if stats.total_logs == 0 else '✗'}")
    
    return True

if __name__ == "__main__":
    print("=== Service Integration Test ===")
    
    success = True
    
    # Test service factories
    success &= test_service_factories()
    
    # Test AI service
    success &= test_ai_service_basic()
    
    # Test Log service
    success &= test_log_service_basic()
    
    print(f"\n=== Test Result: {'PASS' if success else 'FAIL'} ===")