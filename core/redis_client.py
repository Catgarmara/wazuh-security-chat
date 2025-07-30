"""
Redis client and session management for the Wazuh AI Companion.

This module provides Redis connection pooling, session management,
and caching utilities for performance optimization.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Callable
from uuid import UUID, uuid4
from functools import wraps

import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

from .config import get_settings

logger = logging.getLogger(__name__)

# Global Redis client and connection pool
redis_client: Optional[redis.Redis] = None
connection_pool: Optional[ConnectionPool] = None


def redis_retry(max_retries: int = 3, backoff_factor: float = 0.5):
    """
    Decorator for Redis operations with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Redis operation failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Redis operation failed after {max_retries + 1} attempts: {e}")
                except RedisError as e:
                    # Don't retry for other Redis errors
                    logger.error(f"Redis operation failed with non-retryable error: {e}")
                    raise
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


class RedisManager:
    """
    Redis manager class for connection management and operations.
    
    Provides high-level interface for Redis operations with proper
    error handling, connection pooling, and retry logic.
    """
    
    def __init__(self):
        self.client = redis_client
        self.pool = connection_pool
        self._last_health_check = None
        self._health_check_interval = 30  # seconds
    
    @redis_retry(max_retries=2, backoff_factor=0.1)
    def health_check(self, force: bool = False) -> dict:
        """
        Perform Redis health check with caching.
        
        Args:
            force: Force health check even if cached result is available
            
        Returns:
            dict: Health check results
        """
        if self.client is None:
            return {"status": "error", "message": "Redis not initialized"}
        
        # Return cached result if available and not forced
        now = time.time()
        if (not force and self._last_health_check and 
            now - self._last_health_check < self._health_check_interval):
            return getattr(self, '_cached_health_result', {"status": "cached"})
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            ping_result = self.client.ping()
            ping_time = time.time() - start_time
            
            # Get Redis info
            info = self.client.info()
            
            # Get connection pool status
            pool_info = {
                "created_connections": self.pool.created_connections,
                "available_connections": len(self.pool._available_connections),
                "in_use_connections": len(self.pool._in_use_connections),
                "max_connections": self.pool.max_connections,
            }
            
            # Calculate memory usage percentage if max memory is set
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            memory_usage_percent = (used_memory / max_memory * 100) if max_memory > 0 else 0
            
            result = {
                "status": "healthy",
                "ping": ping_result,
                "ping_time_ms": round(ping_time * 1000, 2),
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "used_memory_bytes": used_memory,
                "memory_usage_percent": round(memory_usage_percent, 2),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "pool_info": pool_info,
                "uptime_seconds": info.get("uptime_in_seconds"),
                "last_check": datetime.utcnow().isoformat(),
            }
            
            # Calculate hit ratio
            hits = result["keyspace_hits"]
            misses = result["keyspace_misses"]
            if hits + misses > 0:
                result["hit_ratio"] = round(hits / (hits + misses) * 100, 2)
            else:
                result["hit_ratio"] = 0
            
            # Cache the result
            self._last_health_check = now
            self._cached_health_result = result
            
            return result
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            error_result = {
                "status": "error", 
                "message": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
            self._cached_health_result = error_result
            return error_result
    
    def get_connection_info(self) -> dict:
        """
        Get detailed Redis connection information.
        
        Returns:
            dict: Connection information
        """
        if self.client is None or self.pool is None:
            return {"error": "Redis not initialized"}
        
        try:
            info = self.client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "blocked_clients": info.get("blocked_clients"),
                "used_memory": info.get("used_memory_human"),
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "pool_created_connections": self.pool.created_connections,
                "pool_available_connections": len(self.pool._available_connections),
                "pool_in_use_connections": len(self.pool._in_use_connections),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis connection info: {e}")
            return {"error": str(e)}
    
    def get_performance_metrics(self) -> dict:
        """
        Get Redis performance metrics.
        
        Returns:
            dict: Performance metrics
        """
        try:
            info = self.client.info()
            stats = self.client.info("stats")
            memory = self.client.info("memory")
            
            return {
                "operations_per_second": {
                    "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                },
                "memory": {
                    "used_memory": memory.get("used_memory", 0),
                    "used_memory_human": memory.get("used_memory_human", "0B"),
                    "used_memory_peak": memory.get("used_memory_peak", 0),
                    "used_memory_peak_human": memory.get("used_memory_peak_human", "0B"),
                    "memory_fragmentation_ratio": memory.get("mem_fragmentation_ratio", 0),
                },
                "keyspace": {
                    "keyspace_hits": stats.get("keyspace_hits", 0),
                    "keyspace_misses": stats.get("keyspace_misses", 0),
                    "expired_keys": stats.get("expired_keys", 0),
                    "evicted_keys": stats.get("evicted_keys", 0),
                },
                "connections": {
                    "connected_clients": info.get("connected_clients", 0),
                    "blocked_clients": info.get("blocked_clients", 0),
                    "total_connections_received": info.get("total_connections_received", 0),
                },
                "persistence": {
                    "rdb_last_save_time": info.get("rdb_last_save_time", 0),
                    "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save", 0),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get Redis performance metrics: {e}")
            return {"error": str(e)}
    
    def clear_cache_by_pattern(self, pattern: str) -> int:
        """
        Clear cache keys matching a pattern (with performance optimization).
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            int: Number of keys deleted
        """
        try:
            deleted_count = 0
            cursor = 0
            
            # Use SCAN instead of KEYS for better performance
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self.client.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {deleted_count} keys matching pattern: {pattern}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear cache pattern {pattern}: {e}")
            return 0


class SessionManager:
    """
    Session manager for user session storage and management.
    
    Handles user session data, authentication tokens, and temporary
    data storage with automatic expiration.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client
        self.session_prefix = "session:"
        self.token_prefix = "token:"
        self.user_prefix = "user:"
        
    @redis_retry(max_retries=3)
    def create_session(self, user_id: Union[str, UUID], session_data: Dict[str, Any], 
                      expire_seconds: int = 3600) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User identifier
            session_data: Session data to store
            expire_seconds: Session expiration time in seconds
            
        Returns:
            str: Session ID
        """
        session_id = str(uuid4())
        session_key = f"{self.session_prefix}{session_id}"
        
        # Add metadata to session data
        session_data.update({
            "user_id": str(user_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
        })
        
        try:
            # Store session data with expiration
            self.client.setex(
                session_key,
                expire_seconds,
                json.dumps(session_data, default=str)
            )
            
            # Add session to user's session list
            user_sessions_key = f"{self.user_prefix}{user_id}:sessions"
            self.client.sadd(user_sessions_key, session_id)
            self.client.expire(user_sessions_key, expire_seconds)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
        except RedisError as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    @redis_retry(max_retries=3)
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[Dict]: Session data or None if not found
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            session_data = self.client.get(session_key)
            if session_data is None:
                return None
            
            data = json.loads(session_data)
            
            # Update last accessed time
            data["last_accessed"] = datetime.utcnow().isoformat()
            self.client.setex(
                session_key,
                self.client.ttl(session_key),
                json.dumps(data, default=str)
            )
            
            return data
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    @redis_retry(max_retries=3)
    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session identifier
            session_data: Updated session data
            
        Returns:
            bool: True if successful, False otherwise
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            # Get current TTL
            ttl = self.client.ttl(session_key)
            if ttl <= 0:
                logger.warning(f"Session {session_id} expired or not found")
                return False
            
            # Update session data
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            self.client.setex(
                session_key,
                ttl,
                json.dumps(session_data, default=str)
            )
            
            return True
            
        except RedisError as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            # Get session data to find user_id
            session_data = self.get_session(session_id)
            if session_data:
                user_id = session_data.get("user_id")
                if user_id:
                    # Remove from user's session list
                    user_sessions_key = f"{self.user_prefix}{user_id}:sessions"
                    self.client.srem(user_sessions_key, session_id)
            
            # Delete session
            result = self.client.delete(session_key)
            
            if result:
                logger.info(f"Deleted session {session_id}")
            
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def get_user_sessions(self, user_id: Union[str, UUID]) -> list:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            list: List of session IDs
        """
        user_sessions_key = f"{self.user_prefix}{user_id}:sessions"
        
        try:
            session_ids = self.client.smembers(user_sessions_key)
            return [sid.decode() for sid in session_ids]
            
        except RedisError as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    def delete_user_sessions(self, user_id: Union[str, UUID]) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            int: Number of sessions deleted
        """
        session_ids = self.get_user_sessions(user_id)
        deleted_count = 0
        
        for session_id in session_ids:
            if self.delete_session(session_id):
                deleted_count += 1
        
        # Clean up user sessions set
        user_sessions_key = f"{self.user_prefix}{user_id}:sessions"
        self.client.delete(user_sessions_key)
        
        logger.info(f"Deleted {deleted_count} sessions for user {user_id}")
        return deleted_count
    
    @redis_retry(max_retries=3)
    def extend_session(self, session_id: str, extend_seconds: int = 3600) -> bool:
        """
        Extend session expiration time.
        
        Args:
            session_id: Session identifier
            extend_seconds: Additional seconds to extend
            
        Returns:
            bool: True if successful, False otherwise
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            current_ttl = self.client.ttl(session_key)
            if current_ttl <= 0:
                return False
            
            new_ttl = current_ttl + extend_seconds
            result = self.client.expire(session_key, new_ttl)
            
            if result:
                logger.debug(f"Extended session {session_id} by {extend_seconds} seconds")
            
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dict: Session statistics
        """
        try:
            # Count sessions by scanning keys
            session_count = 0
            active_users = set()
            cursor = 0
            
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor, 
                    match=f"{self.session_prefix}*", 
                    count=100
                )
                
                if keys:
                    session_count += len(keys)
                    
                    # Get user IDs from sessions (batch operation)
                    session_data_list = self.client.mget(keys)
                    for session_data in session_data_list:
                        if session_data:
                            try:
                                data = json.loads(session_data)
                                user_id = data.get("user_id")
                                if user_id:
                                    active_users.add(user_id)
                            except json.JSONDecodeError:
                                continue
                
                if cursor == 0:
                    break
            
            return {
                "total_sessions": session_count,
                "active_users": len(active_users),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except RedisError as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}
    
    @redis_retry(max_retries=3)
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (maintenance operation).
        
        Returns:
            int: Number of expired sessions cleaned up
        """
        try:
            cleaned_count = 0
            cursor = 0
            
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match=f"{self.session_prefix}*",
                    count=100
                )
                
                if keys:
                    # Check TTL for each key and remove expired ones
                    for key in keys:
                        ttl = self.client.ttl(key)
                        if ttl == -2:  # Key doesn't exist (expired)
                            cleaned_count += 1
                        elif ttl == -1:  # Key exists but has no expiration
                            # Set default expiration for sessions without TTL
                            self.client.expire(key, 3600)
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except RedisError as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0


class CacheManager:
    """
    Cache manager for application data caching.
    
    Provides high-level caching operations for frequently accessed
    data with automatic serialization and expiration.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client
        self.cache_prefix = "cache:"
    
    @redis_retry(max_retries=3)
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """
        Set a cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            expire_seconds: Optional expiration time
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = f"{self.cache_prefix}{key}"
        
        try:
            serialized_value = json.dumps(value, default=str)
            
            if expire_seconds:
                result = self.client.setex(cache_key, expire_seconds, serialized_value)
            else:
                result = self.client.set(cache_key, serialized_value)
            
            return bool(result)
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def get(self, key: str) -> Any:
        """
        Get a cache value.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found
        """
        cache_key = f"{self.cache_prefix}{key}"
        
        try:
            value = self.client.get(cache_key)
            if value is None:
                return None
            
            return json.loads(value)
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    @redis_retry(max_retries=3)
    def delete(self, key: str) -> bool:
        """
        Delete a cache value.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = f"{self.cache_prefix}{key}"
        
        try:
            result = self.client.delete(cache_key)
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def exists(self, key: str) -> bool:
        """
        Check if a cache key exists.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if exists, False otherwise
        """
        cache_key = f"{self.cache_prefix}{key}"
        
        try:
            return bool(self.client.exists(cache_key))
            
        except RedisError as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear cache keys matching a pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            
        Returns:
            int: Number of keys deleted
        """
        cache_pattern = f"{self.cache_prefix}{pattern}"
        
        try:
            keys = self.client.keys(cache_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
            
        except RedisError as e:
            logger.error(f"Failed to clear cache pattern {pattern}: {e}")
            return 0
    
    @redis_retry(max_retries=3)
    def mget(self, keys: list) -> Dict[str, Any]:
        """
        Get multiple cache values in a single operation.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict: Dictionary of key-value pairs
        """
        if not keys:
            return {}
        
        cache_keys = [f"{self.cache_prefix}{key}" for key in keys]
        
        try:
            values = self.client.mget(cache_keys)
            result = {}
            
            for i, value in enumerate(values):
                if value is not None:
                    try:
                        result[keys[i]] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached value for key: {keys[i]}")
                        result[keys[i]] = None
                else:
                    result[keys[i]] = None
            
            return result
            
        except RedisError as e:
            logger.error(f"Failed to get multiple cache keys: {e}")
            return {key: None for key in keys}
    
    @redis_retry(max_retries=3)
    def mset(self, data: Dict[str, Any], expire_seconds: Optional[int] = None) -> bool:
        """
        Set multiple cache values in a single operation.
        
        Args:
            data: Dictionary of key-value pairs to cache
            expire_seconds: Optional expiration time for all keys
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not data:
            return True
        
        try:
            # Prepare data for Redis
            redis_data = {}
            for key, value in data.items():
                cache_key = f"{self.cache_prefix}{key}"
                redis_data[cache_key] = json.dumps(value, default=str)
            
            # Set all values
            result = self.client.mset(redis_data)
            
            # Set expiration if specified
            if expire_seconds and result:
                pipe = self.client.pipeline()
                for cache_key in redis_data.keys():
                    pipe.expire(cache_key, expire_seconds)
                pipe.execute()
            
            return bool(result)
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to set multiple cache keys: {e}")
            return False
    
    @redis_retry(max_retries=3)
    def get_or_set(self, key: str, factory_func: Callable[[], Any], 
                   expire_seconds: Optional[int] = None) -> Any:
        """
        Get cached value or set it using factory function if not exists.
        
        Args:
            key: Cache key
            factory_func: Function to generate value if not cached
            expire_seconds: Optional expiration time
            
        Returns:
            Any: Cached or generated value
        """
        # Try to get existing value
        value = self.get(key)
        if value is not None:
            return value
        
        # Generate new value
        try:
            new_value = factory_func()
            self.set(key, new_value, expire_seconds)
            return new_value
        except Exception as e:
            logger.error(f"Failed to generate value for cache key {key}: {e}")
            return None
    
    @redis_retry(max_retries=3)
    def increment(self, key: str, amount: int = 1, expire_seconds: Optional[int] = None) -> int:
        """
        Increment a numeric cache value.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            expire_seconds: Optional expiration time
            
        Returns:
            int: New value after increment
        """
        cache_key = f"{self.cache_prefix}{key}"
        
        try:
            new_value = self.client.incrby(cache_key, amount)
            
            if expire_seconds:
                self.client.expire(cache_key, expire_seconds)
            
            return new_value
            
        except RedisError as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return 0
    
    @redis_retry(max_retries=3)
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict: Cache statistics
        """
        try:
            cache_count = 0
            total_memory = 0
            cursor = 0
            
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match=f"{self.cache_prefix}*",
                    count=100
                )
                
                if keys:
                    cache_count += len(keys)
                    
                    # Get memory usage for these keys
                    for key in keys:
                        try:
                            memory_usage = self.client.memory_usage(key)
                            if memory_usage:
                                total_memory += memory_usage
                        except:
                            # memory_usage might not be available in all Redis versions
                            pass
                
                if cursor == 0:
                    break
            
            return {
                "total_cache_keys": cache_count,
                "estimated_memory_bytes": total_memory,
                "estimated_memory_mb": round(total_memory / (1024 * 1024), 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except RedisError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


def init_redis() -> None:
    """
    Initialize Redis connection and connection pool with advanced configuration.
    
    This should be called once during application startup.
    """
    global redis_client, connection_pool
    
    settings = get_settings()
    
    logger.info("Initializing Redis connection...")
    
    try:
        # Create retry configuration
        retry_config = Retry(
            ExponentialBackoff(),
            retries=3
        )
        
        # Create connection pool with advanced settings
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
            socket_keepalive_options={},
            health_check_interval=30,
        )
        
        # Create Redis client with advanced configuration
        redis_client = redis.Redis(
            connection_pool=connection_pool,
            decode_responses=True,
            retry_on_timeout=True,
            retry_on_error=[ConnectionError, TimeoutError],
            retry=retry_config,
        )
        
        # Test connection with timeout
        start_time = time.time()
        ping_result = redis_client.ping()
        connection_time = time.time() - start_time
        
        # Get Redis info for validation
        info = redis_client.info()
        redis_version = info.get("redis_version", "unknown")
        
        logger.info(
            f"Redis connection initialized successfully - "
            f"Version: {redis_version}, "
            f"Connection time: {connection_time:.3f}s, "
            f"Pool max connections: {settings.redis.max_connections}"
        )
        
        # Update global manager instance
        redis_manager.client = redis_client
        redis_manager.pool = connection_pool
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        # Clean up on failure
        if connection_pool:
            try:
                connection_pool.disconnect()
            except:
                pass
        redis_client = None
        connection_pool = None
        raise


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        redis.Redis: Redis client
        
    Raises:
        RuntimeError: If Redis is not initialized
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    
    return redis_client


def get_session_manager() -> SessionManager:
    """
    Get session manager instance.
    
    Returns:
        SessionManager: Session manager
    """
    client = get_redis_client()
    return SessionManager(client)


def get_cache_manager() -> CacheManager:
    """
    Get cache manager instance.
    
    Returns:
        CacheManager: Cache manager
    """
    client = get_redis_client()
    return CacheManager(client)


def validate_redis_connection() -> bool:
    """
    Validate Redis connection and perform basic operations test.
    
    Returns:
        bool: True if connection is valid and operational
    """
    try:
        if redis_client is None:
            return False
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = {"timestamp": datetime.utcnow().isoformat()}
        
        # Test SET operation
        redis_client.setex(test_key, 10, json.dumps(test_value))
        
        # Test GET operation
        retrieved = redis_client.get(test_key)
        if not retrieved:
            return False
        
        # Test DELETE operation
        redis_client.delete(test_key)
        
        # Test connection pool status
        if connection_pool and connection_pool.created_connections == 0:
            logger.warning("No connections created in pool")
        
        return True
        
    except Exception as e:
        logger.error(f"Redis connection validation failed: {e}")
        return False


def shutdown_redis() -> None:
    """
    Shutdown Redis connections gracefully.
    
    This should be called during application shutdown.
    """
    global redis_client, connection_pool
    
    logger.info("Shutting down Redis connections...")
    
    try:
        # Close client connections gracefully
        if redis_client is not None:
            try:
                # Perform final operations if needed
                redis_client.connection_pool.disconnect()
            except Exception as e:
                logger.warning(f"Error during Redis client shutdown: {e}")
        
        # Disconnect connection pool
        if connection_pool is not None:
            try:
                connection_pool.disconnect()
            except Exception as e:
                logger.warning(f"Error during connection pool shutdown: {e}")
        
        # Clear global references
        redis_client = None
        connection_pool = None
        
        # Update manager instance
        redis_manager.client = None
        redis_manager.pool = None
        
        logger.info("Redis shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during Redis shutdown: {e}")
        # Force cleanup
        redis_client = None
        connection_pool = None


# Global manager instances
redis_manager = RedisManager()