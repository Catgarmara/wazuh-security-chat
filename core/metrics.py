"""
Prometheus metrics collection for Wazuh AI Companion.
"""
import time
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry, 
    generate_latest, CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse

# Create custom registry for application metrics
REGISTRY = CollectorRegistry()

# Application info
app_info = Info(
    'wazuh_app_info', 
    'Application information',
    registry=REGISTRY
)

# HTTP request metrics
http_requests_total = Counter(
    'wazuh_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    'wazuh_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# WebSocket metrics
websocket_connections_total = Counter(
    'wazuh_websocket_connections_total',
    'Total WebSocket connections',
    ['status'],
    registry=REGISTRY
)

websocket_connections_active = Gauge(
    'wazuh_websocket_connections_active',
    'Active WebSocket connections',
    registry=REGISTRY
)

websocket_messages_total = Counter(
    'wazuh_websocket_messages_total',
    'Total WebSocket messages',
    ['direction', 'message_type'],
    registry=REGISTRY
)

# AI service metrics
ai_queries_total = Counter(
    'wazuh_ai_queries_total',
    'Total AI queries processed',
    ['status'],
    registry=REGISTRY
)

ai_query_duration_seconds = Histogram(
    'wazuh_ai_query_duration_seconds',
    'AI query processing duration in seconds',
    registry=REGISTRY
)

ai_vector_search_duration_seconds = Histogram(
    'wazuh_ai_vector_search_duration_seconds',
    'Vector similarity search duration in seconds',
    registry=REGISTRY
)

ai_llm_request_duration_seconds = Histogram(
    'wazuh_ai_llm_request_duration_seconds',
    'LLM request duration in seconds',
    registry=REGISTRY
)

# Database metrics
database_connections_active = Gauge(
    'wazuh_database_connections_active',
    'Active database connections',
    registry=REGISTRY
)

database_queries_total = Counter(
    'wazuh_database_queries_total',
    'Total database queries',
    ['operation', 'table'],
    registry=REGISTRY
)

database_query_duration_seconds = Histogram(
    'wazuh_database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    registry=REGISTRY
)

# Redis metrics
redis_operations_total = Counter(
    'wazuh_redis_operations_total',
    'Total Redis operations',
    ['operation', 'status'],
    registry=REGISTRY
)

redis_operation_duration_seconds = Histogram(
    'wazuh_redis_operation_duration_seconds',
    'Redis operation duration in seconds',
    ['operation'],
    registry=REGISTRY
)

# Log processing metrics
log_entries_processed_total = Counter(
    'wazuh_log_entries_processed_total',
    'Total log entries processed',
    ['source', 'status'],
    registry=REGISTRY
)

log_processing_duration_seconds = Histogram(
    'wazuh_log_processing_duration_seconds',
    'Log processing duration in seconds',
    ['operation'],
    registry=REGISTRY
)

log_files_loaded_total = Counter(
    'wazuh_log_files_loaded_total',
    'Total log files loaded',
    ['source', 'status'],
    registry=REGISTRY
)

# Authentication metrics
auth_attempts_total = Counter(
    'wazuh_auth_attempts_total',
    'Total authentication attempts',
    ['status', 'method'],
    registry=REGISTRY
)

auth_tokens_issued_total = Counter(
    'wazuh_auth_tokens_issued_total',
    'Total authentication tokens issued',
    registry=REGISTRY
)

auth_tokens_validated_total = Counter(
    'wazuh_auth_tokens_validated_total',
    'Total token validation attempts',
    ['status'],
    registry=REGISTRY
)

# Chat service metrics
chat_sessions_total = Counter(
    'wazuh_chat_sessions_total',
    'Total chat sessions created',
    registry=REGISTRY
)

chat_sessions_active = Gauge(
    'wazuh_chat_sessions_active',
    'Active chat sessions',
    registry=REGISTRY
)

chat_messages_total = Counter(
    'wazuh_chat_messages_total',
    'Total chat messages processed',
    ['role'],
    registry=REGISTRY
)

# System metrics
system_errors_total = Counter(
    'wazuh_system_errors_total',
    'Total system errors',
    ['error_type', 'service'],
    registry=REGISTRY
)

# Business metrics
user_queries_per_session = Histogram(
    'wazuh_user_queries_per_session',
    'Number of queries per user session',
    registry=REGISTRY
)

session_duration_seconds = Histogram(
    'wazuh_session_duration_seconds',
    'User session duration in seconds',
    registry=REGISTRY
)


class MetricsCollector:
    """Centralized metrics collection class."""
    
    def __init__(self):
        self.start_time = time.time()
        
    def set_app_info(self, name: str, version: str, environment: str):
        """Set application information."""
        app_info.info({
            'name': name,
            'version': version,
            'environment': environment,
            'start_time': str(int(self.start_time))
        })
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_websocket_connection(self, status: str):
        """Record WebSocket connection event."""
        websocket_connections_total.labels(status=status).inc()
        
        if status == 'connected':
            websocket_connections_active.inc()
        elif status == 'disconnected':
            websocket_connections_active.dec()
    
    def record_websocket_message(self, direction: str, message_type: str = 'chat'):
        """Record WebSocket message."""
        websocket_messages_total.labels(
            direction=direction,
            message_type=message_type
        ).inc()
    
    def record_ai_query(self, status: str, duration: float):
        """Record AI query metrics."""
        ai_queries_total.labels(status=status).inc()
        ai_query_duration_seconds.observe(duration)
    
    def record_vector_search(self, duration: float):
        """Record vector search duration."""
        ai_vector_search_duration_seconds.observe(duration)
    
    def record_llm_request(self, duration: float):
        """Record LLM request duration."""
        ai_llm_request_duration_seconds.observe(duration)
    
    def record_database_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        database_queries_total.labels(
            operation=operation,
            table=table
        ).inc()
        
        database_query_duration_seconds.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def set_database_connections(self, count: int):
        """Set active database connections count."""
        database_connections_active.set(count)
    
    def record_redis_operation(self, operation: str, status: str, duration: float):
        """Record Redis operation metrics."""
        redis_operations_total.labels(
            operation=operation,
            status=status
        ).inc()
        
        redis_operation_duration_seconds.labels(
            operation=operation
        ).observe(duration)
    
    def record_log_processing(self, source: str, status: str, count: int = 1):
        """Record log processing metrics."""
        log_entries_processed_total.labels(
            source=source,
            status=status
        ).inc(count)
    
    def record_log_file_loaded(self, source: str, status: str):
        """Record log file loading."""
        log_files_loaded_total.labels(
            source=source,
            status=status
        ).inc()
    
    def record_auth_attempt(self, status: str, method: str = 'password'):
        """Record authentication attempt."""
        auth_attempts_total.labels(
            status=status,
            method=method
        ).inc()
    
    def record_token_issued(self):
        """Record token issuance."""
        auth_tokens_issued_total.inc()
    
    def record_token_validation(self, status: str):
        """Record token validation."""
        auth_tokens_validated_total.labels(status=status).inc()
    
    def record_chat_session(self, action: str):
        """Record chat session events."""
        if action == 'created':
            chat_sessions_total.inc()
            chat_sessions_active.inc()
        elif action == 'ended':
            chat_sessions_active.dec()
    
    def record_chat_message(self, role: str):
        """Record chat message."""
        chat_messages_total.labels(role=role).inc()
    
    def record_system_error(self, error_type: str, service: str):
        """Record system error."""
        system_errors_total.labels(
            error_type=error_type,
            service=service
        ).inc()
    
    def record_session_metrics(self, query_count: int, duration: float):
        """Record session-level business metrics."""
        user_queries_per_session.observe(query_count)
        session_duration_seconds.observe(duration)


# Global metrics collector instance
metrics = MetricsCollector()


def timed_metric(metric_histogram):
    """Decorator to time function execution and record to histogram."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric_histogram.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric_histogram.observe(duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    data = generate_latest(REGISTRY)
    return PlainTextResponse(
        content=data,
        media_type=CONTENT_TYPE_LATEST
    )


def setup_metrics_middleware(app):
    """Set up metrics collection middleware."""
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        metrics.record_http_request(method, endpoint, status_code, duration)
        
        return response