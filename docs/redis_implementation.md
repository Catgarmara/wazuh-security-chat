# Redis Connection and Session Management Implementation

## Overview

This document describes the enhanced Redis implementation for the Wazuh AI Companion, providing robust connection pooling, session management, and caching utilities with retry logic and performance optimizations.

## Features Implemented

### 1. Connection Pooling with Retry Logic

- **Advanced Connection Pool**: Configured with health checks, keepalive, and automatic reconnection
- **Exponential Backoff Retry**: Automatic retry for connection and timeout errors
- **Connection Monitoring**: Real-time monitoring of pool status and connection health

```python
# Connection pool configuration
connection_pool = ConnectionPool(
    host=settings.redis.host,
    port=settings.redis.port,
    db=settings.redis.db,
    password=settings.redis.password,
    max_connections=settings.redis.max_connections,
    retry_on_timeout=True,
    retry_on_error=[ConnectionError, TimeoutError],
    retry=retry_config,
    socket_timeout=10,
    socket_connect_timeout=10,
    socket_keepalive=True,
    health_check_interval=30,
)
```

### 2. Session Management

The `SessionManager` class provides comprehensive user session handling:

#### Key Features:
- **Session Creation**: Create sessions with automatic expiration
- **Session Retrieval**: Get session data with automatic last-accessed updates
- **Session Updates**: Update session data while preserving TTL
- **User Session Tracking**: Track all sessions per user
- **Batch Operations**: Efficient session statistics and cleanup
- **Automatic Cleanup**: Remove expired sessions

#### Usage Examples:

```python
# Create session manager
session_manager = get_session_manager()

# Create a new session
session_id = session_manager.create_session(
    user_id="user123",
    session_data={"username": "analyst", "role": "security_analyst"},
    expire_seconds=3600
)

# Retrieve session
session_data = session_manager.get_session(session_id)

# Update session
session_data["last_action"] = "query_logs"
session_manager.update_session(session_id, session_data)

# Get session statistics
stats = session_manager.get_session_stats()
print(f"Active sessions: {stats['total_sessions']}")
print(f"Active users: {stats['active_users']}")
```

### 3. Cache Management

The `CacheManager` class provides high-performance caching with advanced features:

#### Key Features:
- **Basic Operations**: Set, get, delete, exists operations with retry logic
- **Batch Operations**: Multi-get and multi-set for improved performance
- **Atomic Operations**: Increment/decrement with optional expiration
- **Pattern Matching**: Clear cache by patterns using SCAN for performance
- **Get-or-Set**: Atomic get-or-generate pattern
- **Cache Statistics**: Memory usage and key count monitoring

#### Usage Examples:

```python
# Create cache manager
cache_manager = get_cache_manager()

# Basic caching
cache_manager.set("user:123:profile", user_data, expire_seconds=3600)
profile = cache_manager.get("user:123:profile")

# Batch operations
batch_data = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3"
}
cache_manager.mset(batch_data, expire_seconds=1800)
results = cache_manager.mget(["key1", "key2", "key3"])

# Get-or-set pattern
def expensive_computation():
    return {"result": "computed_value", "timestamp": datetime.utcnow()}

result = cache_manager.get_or_set("expensive_key", expensive_computation, 3600)

# Increment counters
cache_manager.increment("api_calls:user:123", 1, expire_seconds=86400)
```

### 4. Performance Monitoring

The `RedisManager` class provides comprehensive monitoring:

#### Health Checks:
- Connection status and response time
- Memory usage and fragmentation
- Hit/miss ratios
- Connection pool status

#### Performance Metrics:
- Operations per second
- Memory usage statistics
- Keyspace statistics
- Connection statistics

```python
# Get health status
health = redis_manager.health_check()
print(f"Status: {health['status']}")
print(f"Response time: {health['ping_time_ms']}ms")
print(f"Hit ratio: {health['hit_ratio']}%")

# Get detailed performance metrics
metrics = redis_manager.get_performance_metrics()
print(f"Ops/sec: {metrics['operations_per_second']['instantaneous_ops_per_sec']}")
print(f"Memory usage: {metrics['memory']['used_memory_human']}")
```

### 5. Retry Logic and Error Handling

The `@redis_retry` decorator provides automatic retry for transient failures:

```python
@redis_retry(max_retries=3, backoff_factor=0.5)
def redis_operation():
    # This operation will be retried up to 3 times
    # with exponential backoff on ConnectionError or TimeoutError
    return redis_client.get("some_key")
```

## Configuration

### Redis Environment Variables

Redis configuration is managed through the application settings:

```bash
# Redis Connection Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password
REDIS_MAX_CONNECTIONS=20
```

**Configuration Details:**
- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0, range: 0-15)
- `REDIS_PASSWORD`: Redis authentication password (optional)
- `REDIS_MAX_CONNECTIONS`: Maximum connections in pool (default: 20)

### Integration with Core Config

All Redis settings are defined in `core/config.py` using Pydantic validation:
- Port validation (1-65535)
- Database number validation (0-15)
- Connection URL generation
- Environment variable binding

## Initialization and Shutdown

```python
# Application startup
from core.redis_client import init_redis

# Initialize Redis connection
init_redis()

# Validate connection
from core.redis_client import validate_redis_connection
if not validate_redis_connection():
    raise RuntimeError("Redis connection validation failed")

# Application shutdown
from core.redis_client import shutdown_redis
shutdown_redis()
```

## Performance Optimizations

### 1. Connection Pooling
- Reuse connections across requests
- Automatic connection health checks
- Configurable pool size based on load

### 2. Batch Operations
- Use `mget`/`mset` for multiple keys
- Reduce network round trips
- Pipeline operations when possible

### 3. Efficient Key Scanning
- Use `SCAN` instead of `KEYS` for pattern matching
- Paginated results to avoid blocking
- Cursor-based iteration

### 4. Memory Management
- Automatic expiration for all cached data
- Memory usage monitoring
- Pattern-based cache clearing

## Error Handling

The implementation handles various error scenarios:

1. **Connection Errors**: Automatic retry with exponential backoff
2. **Timeout Errors**: Configurable timeout with retry logic
3. **Memory Errors**: Graceful degradation and monitoring
4. **Serialization Errors**: JSON encoding/decoding error handling

## Testing

The implementation includes comprehensive tests:

1. **Unit Tests**: Test individual components with mocks
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Validate optimization features
4. **Error Handling Tests**: Test retry and error scenarios

Run tests:
```bash
python test_redis.py
python test_redis_integration.py
```

## Security Considerations

1. **Password Protection**: Redis password authentication
2. **Connection Encryption**: TLS support for production
3. **Access Control**: Database-level isolation
4. **Session Security**: Secure session data serialization

## Monitoring and Observability

The implementation provides extensive monitoring capabilities:

1. **Health Checks**: Regular connection and performance validation
2. **Metrics Collection**: Detailed performance and usage metrics
3. **Error Tracking**: Comprehensive error logging and tracking
4. **Cache Statistics**: Memory usage and hit ratio monitoring

## Requirements Satisfied

This implementation satisfies the following task requirements:

✅ **Set up Redis client with connection pooling and retry logic**
- Advanced connection pool with health checks
- Exponential backoff retry mechanism
- Connection monitoring and validation

✅ **Create session storage and retrieval functions**
- Comprehensive SessionManager class
- Session CRUD operations with TTL management
- User session tracking and cleanup
- Session statistics and monitoring

✅ **Implement cache management utilities for performance optimization**
- High-performance CacheManager class
- Batch operations for improved performance
- Pattern-based cache management
- Memory usage monitoring and optimization

The implementation follows Redis best practices and provides a robust foundation for the production-ready Wazuh AI Companion system.