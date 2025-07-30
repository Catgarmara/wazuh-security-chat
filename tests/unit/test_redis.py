#!/usr/bin/env python3
"""
Test script to validate Redis connection and session management.
"""

import sys
import time
from datetime import datetime
from uuid import uuid4

def test_redis_imports():
    """Test that Redis modules can be imported."""
    try:
        from core.redis_client import (
            init_redis, get_redis_client, get_session_manager, 
            get_cache_manager, redis_manager, shutdown_redis,
            validate_redis_connection, redis_retry
        )
        print("✓ Redis imports successful")
        return True
    except ImportError as e:
        print(f"✗ Redis import error: {e}")
        return False

def test_session_manager_logic():
    """Test session manager logic without Redis connection."""
    try:
        from core.redis_client import SessionManager
        
        # Mock Redis client for testing logic
        class MockRedis:
            def __init__(self):
                self.data = {}
                self.sets = {}
                self.ttls = {}
            
            def setex(self, key, seconds, value):
                self.data[key] = value
                self.ttls[key] = seconds
                return True
            
            def get(self, key):
                return self.data.get(key)
            
            def ttl(self, key):
                return self.ttls.get(key, -1)
            
            def delete(self, key):
                if key in self.data:
                    del self.data[key]
                    return 1
                return 0
            
            def sadd(self, key, value):
                if key not in self.sets:
                    self.sets[key] = set()
                self.sets[key].add(value)
                return 1
            
            def srem(self, key, value):
                if key in self.sets:
                    self.sets[key].discard(value)
                    return 1
                return 0
            
            def smembers(self, key):
                return [v.encode() for v in self.sets.get(key, set())]
            
            def expire(self, key, seconds):
                self.ttls[key] = seconds
                return True
            
            def scan(self, cursor=0, match=None, count=100):
                keys = list(self.data.keys())
                if match:
                    pattern = match.replace('*', '')
                    keys = [k for k in keys if pattern in k]
                return (0, keys[:count])
            
            def mget(self, keys):
                return [self.data.get(key) for key in keys]
        
        # Test session manager with mock Redis
        mock_redis = MockRedis()
        session_manager = SessionManager(mock_redis)
        
        # Test session creation
        user_id = str(uuid4())
        session_data = {"username": "testuser", "role": "analyst"}
        session_id = session_manager.create_session(user_id, session_data)
        
        # Test session retrieval
        retrieved_data = session_manager.get_session(session_id)
        
        if retrieved_data and retrieved_data.get("username") == "testuser":
            print("✓ Session manager logic test passed")
            return True
        else:
            print("✗ Session manager logic test failed")
            return False
            
    except Exception as e:
        print(f"✗ Session manager logic test error: {e}")
        return False

def test_cache_manager_logic():
    """Test cache manager logic without Redis connection."""
    try:
        from core.redis_client import CacheManager
        
        # Mock Redis client for testing logic
        class MockRedis:
            def __init__(self):
                self.data = {}
                self.counters = {}
            
            def setex(self, key, seconds, value):
                self.data[key] = value
                return True
            
            def set(self, key, value):
                self.data[key] = value
                return True
            
            def get(self, key):
                return self.data.get(key)
            
            def mget(self, keys):
                return [self.data.get(key) for key in keys]
            
            def mset(self, data):
                self.data.update(data)
                return True
            
            def delete(self, key):
                if key in self.data:
                    del self.data[key]
                    return 1
                return 0
            
            def exists(self, key):
                return 1 if key in self.data else 0
            
            def keys(self, pattern):
                # Simple pattern matching for testing
                return [k for k in self.data.keys() if pattern.replace('*', '') in k]
            
            def incrby(self, key, amount):
                if key not in self.counters:
                    self.counters[key] = 0
                self.counters[key] += amount
                return self.counters[key]
            
            def expire(self, key, seconds):
                return True
            
            def pipeline(self):
                return MockPipeline(self)
            
            def scan(self, cursor=0, match=None, count=100):
                keys = list(self.data.keys())
                if match:
                    pattern = match.replace('*', '')
                    keys = [k for k in keys if pattern in k]
                return (0, keys)  # Return cursor 0 to end scan
        
        class MockPipeline:
            def __init__(self, redis_client):
                self.client = redis_client
                self.commands = []
            
            def expire(self, key, seconds):
                self.commands.append(('expire', key, seconds))
                return self
            
            def execute(self):
                return [True] * len(self.commands)
        
        # Test cache manager with mock Redis
        mock_redis = MockRedis()
        cache_manager = CacheManager(mock_redis)
        
        # Test basic cache operations
        test_data = {"key": "value", "number": 42}
        
        # Set cache
        result = cache_manager.set("test_key", test_data)
        if not result:
            print("✗ Cache set failed")
            return False
        
        # Get cache
        retrieved_data = cache_manager.get("test_key")
        if retrieved_data != test_data:
            print("✗ Cache get failed")
            return False
        
        # Test batch operations
        batch_data = {"key1": "value1", "key2": "value2"}
        if not cache_manager.mset(batch_data):
            print("✗ Cache mset failed")
            return False
        
        batch_result = cache_manager.mget(["key1", "key2"])
        if batch_result.get("key1") != "value1" or batch_result.get("key2") != "value2":
            print("✗ Cache mget failed")
            return False
        
        # Test increment
        counter_value = cache_manager.increment("counter", 5)
        if counter_value != 5:
            print("✗ Cache increment failed")
            return False
        
        # Check exists
        if not cache_manager.exists("test_key"):
            print("✗ Cache exists check failed")
            return False
        
        # Delete cache
        if not cache_manager.delete("test_key"):
            print("✗ Cache delete failed")
            return False
        
        print("✓ Cache manager logic test passed")
        return True
        
    except Exception as e:
        print(f"✗ Cache manager logic test error: {e}")
        return False

def test_config_integration():
    """Test Redis configuration integration."""
    try:
        from core.config import get_settings
        
        settings = get_settings()
        
        # Check Redis settings
        redis_config = settings.redis
        
        if hasattr(redis_config, 'host') and hasattr(redis_config, 'port'):
            print(f"✓ Redis config loaded: {redis_config.host}:{redis_config.port}")
            return True
        else:
            print("✗ Redis config missing required fields")
            return False
            
    except Exception as e:
        print(f"✗ Config integration test error: {e}")
        return False

def test_retry_decorator():
    """Test Redis retry decorator functionality."""
    try:
        from core.redis_client import redis_retry
        
        # Test successful operation
        @redis_retry(max_retries=2)
        def successful_operation():
            return "success"
        
        result = successful_operation()
        if result != "success":
            print("✗ Retry decorator success test failed")
            return False
        
        # Test operation that fails then succeeds
        call_count = 0
        
        @redis_retry(max_retries=2, backoff_factor=0.01)  # Fast backoff for testing
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                from redis.exceptions import ConnectionError
                raise ConnectionError("Connection failed")
            return "success_after_retry"
        
        result = flaky_operation()
        if result != "success_after_retry" or call_count != 2:
            print("✗ Retry decorator retry test failed")
            return False
        
        print("✓ Retry decorator test passed")
        return True
        
    except Exception as e:
        print(f"✗ Retry decorator test error: {e}")
        return False

def test_performance_optimizations():
    """Test performance optimization features."""
    try:
        from core.redis_client import SessionManager, CacheManager
        
        # Mock Redis for performance testing
        class MockRedis:
            def __init__(self):
                self.data = {}
                self.operation_count = 0
            
            def scan(self, cursor=0, match=None, count=100):
                self.operation_count += 1
                keys = []
                if match:
                    pattern = match.replace('*', '')
                    keys = [k for k in self.data.keys() if pattern in k]
                return (0, keys[:count])  # Simulate pagination
            
            def mget(self, keys):
                self.operation_count += 1
                return [self.data.get(key) for key in keys]
            
            def mset(self, data):
                self.operation_count += 1
                self.data.update(data)
                return True
            
            def setex(self, key, seconds, value):
                self.operation_count += 1
                self.data[key] = value
                return True
            
            def get(self, key):
                self.operation_count += 1
                return self.data.get(key)
            
            def delete(self, *keys):
                self.operation_count += 1
                count = 0
                for key in keys:
                    if key in self.data:
                        del self.data[key]
                        count += 1
                return count
            
            def pipeline(self):
                return MockPipeline(self)
        
        class MockPipeline:
            def __init__(self, redis_client):
                self.client = redis_client
                self.commands = []
            
            def expire(self, key, seconds):
                self.commands.append(('expire', key, seconds))
                return self
            
            def execute(self):
                return [True] * len(self.commands)
        
        mock_redis = MockRedis()
        cache_manager = CacheManager(mock_redis)
        
        # Test batch operations efficiency
        initial_ops = mock_redis.operation_count
        
        # Single operations (less efficient)
        for i in range(5):
            cache_manager.set(f"key_{i}", f"value_{i}")
        
        single_ops = mock_redis.operation_count - initial_ops
        
        # Reset and test batch operations
        mock_redis.data.clear()
        mock_redis.operation_count = 0
        
        # Batch operations (more efficient)
        batch_data = {f"key_{i}": f"value_{i}" for i in range(5)}
        cache_manager.mset(batch_data)
        
        batch_ops = mock_redis.operation_count
        
        # Batch should be more efficient (fewer operations)
        if batch_ops >= single_ops:
            print(f"✗ Batch operations not more efficient: {batch_ops} vs {single_ops}")
            return False
        
        print("✓ Performance optimization test passed")
        return True
        
    except Exception as e:
        print(f"✗ Performance optimization test error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Redis connection and session management...")
    print("=" * 50)
    
    tests = [
        test_redis_imports,
        test_session_manager_logic,
        test_cache_manager_logic,
        test_config_integration,
        test_retry_decorator,
        test_performance_optimizations,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Redis tests passed!")
        return 0
    else:
        print("❌ Some Redis tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())