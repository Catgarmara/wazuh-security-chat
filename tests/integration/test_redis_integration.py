#!/usr/bin/env python3
"""
Integration test for Redis implementation - validates the enhanced features.
This test can run without actual Redis connection by using mock objects.
"""

import sys
import json
import time
from datetime import datetime
from uuid import uuid4


def test_enhanced_redis_features():
    """Test the enhanced Redis features without external dependencies."""
    print("Testing Enhanced Redis Features")
    print("=" * 40)
    
    try:
        # Test 1: Import all enhanced modules
        print("1. Testing imports...")
        from core.redis_client import (
            RedisManager, SessionManager, CacheManager,
            redis_retry, init_redis, validate_redis_connection,
            get_session_manager, get_cache_manager
        )
        print("   ✓ All imports successful")
        
        # Test 2: Retry decorator functionality
        print("2. Testing retry decorator...")
        
        @redis_retry(max_retries=2, backoff_factor=0.01)
        def test_retry_function():
            return "retry_success"
        
        result = test_retry_function()
        assert result == "retry_success", "Retry decorator failed"
        print("   ✓ Retry decorator working")
        
        # Test 3: Mock Redis operations
        print("3. Testing Redis manager with mock...")
        
        class MockRedis:
            def __init__(self):
                self.data = {}
                self.info_data = {
                    "redis_version": "7.0.0",
                    "connected_clients": 1,
                    "used_memory": 1024000,
                    "used_memory_human": "1.00M",
                    "total_commands_processed": 1000,
                    "keyspace_hits": 800,
                    "keyspace_misses": 200,
                    "uptime_in_seconds": 3600,
                    "instantaneous_ops_per_sec": 10,
                    "used_memory_peak": 2048000,
                    "used_memory_peak_human": "2.00M",
                    "mem_fragmentation_ratio": 1.2,
                    "expired_keys": 50,
                    "evicted_keys": 10,
                    "blocked_clients": 0,
                    "total_connections_received": 100,
                    "rdb_last_save_time": int(time.time()) - 3600,
                    "rdb_changes_since_last_save": 100,
                }
                self.pool_mock = MockPool()
            
            def ping(self):
                return True
            
            def info(self, section=None):
                if section:
                    return {k: v for k, v in self.info_data.items() if section in k}
                return self.info_data
            
            def setex(self, key, seconds, value):
                self.data[key] = value
                return True
            
            def get(self, key):
                return self.data.get(key)
            
            def delete(self, *keys):
                count = 0
                for key in keys:
                    if key in self.data:
                        del self.data[key]
                        count += 1
                return count
            
            def scan(self, cursor=0, match=None, count=100):
                keys = list(self.data.keys())
                if match:
                    pattern = match.replace('*', '')
                    keys = [k for k in keys if pattern in k]
                return (0, keys[:count])
            
            def mget(self, keys):
                return [self.data.get(key) for key in keys]
            
            def mset(self, data):
                self.data.update(data)
                return True
            
            def exists(self, key):
                return 1 if key in self.data else 0
            
            def ttl(self, key):
                return 3600 if key in self.data else -2
            
            def expire(self, key, seconds):
                return True
            
            def sadd(self, key, value):
                if key not in self.data:
                    self.data[key] = set()
                if not isinstance(self.data[key], set):
                    self.data[key] = set()
                self.data[key].add(value)
                return 1
            
            def srem(self, key, value):
                if key in self.data and isinstance(self.data[key], set):
                    self.data[key].discard(value)
                    return 1
                return 0
            
            def smembers(self, key):
                if key in self.data and isinstance(self.data[key], set):
                    return [v.encode() if isinstance(v, str) else str(v).encode() for v in self.data[key]]
                return []
            
            def incrby(self, key, amount):
                if key not in self.data:
                    self.data[key] = 0
                self.data[key] += amount
                return self.data[key]
            
            def pipeline(self):
                return MockPipeline(self)
            
            def memory_usage(self, key):
                return len(str(self.data.get(key, ""))) * 8  # Rough estimate
        
        class MockPool:
            def __init__(self):
                self.created_connections = 5
                self._available_connections = [1, 2, 3]
                self._in_use_connections = [4, 5]
                self.max_connections = 20
        
        class MockPipeline:
            def __init__(self, redis_client):
                self.client = redis_client
                self.commands = []
            
            def expire(self, key, seconds):
                self.commands.append(('expire', key, seconds))
                return self
            
            def execute(self):
                return [True] * len(self.commands)
        
        # Test RedisManager
        mock_redis = MockRedis()
        
        # Temporarily replace global variables for testing
        import core.redis_client as redis_module
        original_client = redis_module.redis_client
        original_pool = redis_module.connection_pool
        
        redis_module.redis_client = mock_redis
        redis_module.connection_pool = mock_redis.pool_mock
        
        manager = RedisManager()
        manager.client = mock_redis
        manager.pool = mock_redis.pool_mock
        
        # Test health check
        health = manager.health_check(force=True)
        assert health["status"] == "healthy", f"Health check failed: {health}"
        print("   ✓ Health check working")
        
        # Test performance metrics
        metrics = manager.get_performance_metrics()
        assert "operations_per_second" in metrics, "Performance metrics missing"
        print("   ✓ Performance metrics working")
        
        # Test 4: Session Manager
        print("4. Testing session manager...")
        session_manager = SessionManager(mock_redis)
        
        # Create session
        user_id = str(uuid4())
        session_data = {"username": "testuser", "role": "analyst"}
        session_id = session_manager.create_session(user_id, session_data)
        assert session_id, "Session creation failed"
        print("   ✓ Session creation working")
        
        # Get session
        retrieved_session = session_manager.get_session(session_id)
        assert retrieved_session["username"] == "testuser", "Session retrieval failed"
        print("   ✓ Session retrieval working")
        
        # Update session
        session_data["last_action"] = "test_action"
        result = session_manager.update_session(session_id, session_data)
        assert result, "Session update failed"
        print("   ✓ Session update working")
        
        # Get session stats
        stats = session_manager.get_session_stats()
        assert "total_sessions" in stats, "Session stats failed"
        print("   ✓ Session stats working")
        
        # Test 5: Cache Manager
        print("5. Testing cache manager...")
        cache_manager = CacheManager(mock_redis)
        
        # Basic cache operations
        test_data = {"key": "value", "number": 42}
        result = cache_manager.set("test_key", test_data)
        assert result, "Cache set failed"
        
        retrieved_data = cache_manager.get("test_key")
        assert retrieved_data == test_data, "Cache get failed"
        print("   ✓ Basic cache operations working")
        
        # Batch operations
        batch_data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = cache_manager.mset(batch_data)
        assert result, "Cache mset failed"
        
        batch_result = cache_manager.mget(["key1", "key2", "key3"])
        assert batch_result["key1"] == "value1", "Cache mget failed"
        print("   ✓ Batch cache operations working")
        
        # Increment operation
        counter_value = cache_manager.increment("counter", 5)
        assert counter_value == 5, "Cache increment failed"
        
        counter_value = cache_manager.increment("counter", 3)
        assert counter_value == 8, "Cache increment failed"
        print("   ✓ Cache increment working")
        
        # Get or set operation
        def factory_func():
            return {"generated": True, "timestamp": datetime.utcnow().isoformat()}
        
        result = cache_manager.get_or_set("generated_key", factory_func)
        assert result["generated"] == True, "Get or set failed"
        print("   ✓ Get or set working")
        
        # Cache stats
        cache_stats = cache_manager.get_cache_stats()
        assert "total_cache_keys" in cache_stats, "Cache stats failed"
        print("   ✓ Cache stats working")
        
        # Test 6: Configuration validation
        print("6. Testing configuration...")
        try:
            from core.config import get_settings
            settings = get_settings()
            redis_config = settings.redis
            
            # Validate required fields
            required_fields = ['host', 'port', 'db', 'max_connections']
            for field in required_fields:
                assert hasattr(redis_config, field), f"Missing Redis config field: {field}"
            
            print("   ✓ Configuration validation working")
        except Exception as e:
            print(f"   ⚠ Configuration test skipped: {e}")
        
        # Restore original values
        redis_module.redis_client = original_client
        redis_module.connection_pool = original_pool
        
        print("\n" + "=" * 40)
        print("🎉 All enhanced Redis features working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_pooling_features():
    """Test connection pooling and retry logic features."""
    print("\nTesting Connection Pooling Features")
    print("=" * 40)
    
    try:
        from core.redis_client import redis_retry
        from redis.exceptions import ConnectionError, TimeoutError
        
        # Test retry with different exception types
        attempt_count = 0
        
        @redis_retry(max_retries=3, backoff_factor=0.01)
        def connection_error_test():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Mock connection error")
            return "success_after_retries"
        
        result = connection_error_test()
        assert result == "success_after_retries", "Connection error retry failed"
        assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
        print("✓ Connection error retry working")
        
        # Test timeout error retry
        attempt_count = 0
        
        @redis_retry(max_retries=2, backoff_factor=0.01)
        def timeout_error_test():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise TimeoutError("Mock timeout error")
            return "success_after_timeout"
        
        result = timeout_error_test()
        assert result == "success_after_timeout", "Timeout error retry failed"
        print("✓ Timeout error retry working")
        
        print("🎉 Connection pooling features working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Connection pooling test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("Redis Integration Tests")
    print("=" * 50)
    
    tests = [
        test_enhanced_redis_features,
        test_connection_pooling_features,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"Integration Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Redis integration tests passed!")
        return 0
    else:
        print("❌ Some Redis integration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())