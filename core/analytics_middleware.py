"""
Analytics middleware for automatic metrics collection.

This middleware automatically tracks query metrics, performance data,
and system metrics for all API requests.
"""

import time
import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from services.analytics_service import AnalyticsService
from models.database import User

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic analytics collection.
    
    Tracks request metrics, response times, and user activity
    for analytics and monitoring purposes.
    """
    
    def __init__(self, app, analytics_service: Optional[AnalyticsService] = None):
        """
        Initialize analytics middleware.
        
        Args:
            app: FastAPI application instance
            analytics_service: Analytics service instance (optional)
        """
        super().__init__(app)
        self.analytics_service = analytics_service or AnalyticsService()
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect analytics data.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        # Record start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")
        
        # Get user information if available
        user_id = None
        try:
            # Try to extract user from request state (set by auth middleware)
            user = getattr(request.state, 'user', None)
            if user and hasattr(user, 'id'):
                user_id = user.id
        except Exception:
            # User extraction failed, continue without user tracking
            pass
        
        # Process request
        response = None
        error_message = None
        success = True
        
        try:
            response = await call_next(request)
        except Exception as e:
            success = False
            error_message = str(e)
            self.logger.error(f"Request failed: {method} {path} - {error_message}")
            raise
        finally:
            # Calculate response time
            response_time = time.time() - start_time
            
            # Track metrics asynchronously (don't block response)
            try:
                await self._track_request_metrics(
                    method=method,
                    path=path,
                    user_id=user_id,
                    response_time=response_time,
                    success=success,
                    error_message=error_message,
                    user_agent=user_agent,
                    status_code=response.status_code if response else 500
                )
            except Exception as e:
                # Don't let analytics failures affect the main request
                self.logger.error(f"Failed to track request metrics: {e}")
        
        return response
    
    async def _track_request_metrics(
        self,
        method: str,
        path: str,
        user_id: Optional[UUID],
        response_time: float,
        success: bool,
        error_message: Optional[str],
        user_agent: str,
        status_code: int
    ) -> None:
        """
        Track request metrics asynchronously.
        
        Args:
            method: HTTP method
            path: Request path
            user_id: User ID if authenticated
            response_time: Response time in seconds
            success: Whether request was successful
            error_message: Error message if request failed
            user_agent: User agent string
            status_code: HTTP status code
        """
        try:
            # Only track certain endpoints to avoid noise
            if self._should_track_endpoint(path):
                # For chat/query endpoints, track as query metrics
                if self._is_query_endpoint(path) and user_id:
                    # Extract query from request if possible
                    query_text = f"{method} {path}"  # Simplified for now
                    
                    await self._track_query_metric(
                        user_id=user_id,
                        query=query_text,
                        response_time=response_time,
                        success=success,
                        error_message=error_message
                    )
                
                # Track system performance metrics
                await self._track_system_metrics(
                    endpoint=path,
                    method=method,
                    response_time=response_time,
                    status_code=status_code,
                    user_agent=user_agent
                )
                
        except Exception as e:
            self.logger.error(f"Failed to track detailed metrics: {e}")
    
    async def _track_query_metric(
        self,
        user_id: UUID,
        query: str,
        response_time: float,
        success: bool,
        error_message: Optional[str]
    ) -> None:
        """
        Track query-specific metrics.
        
        Args:
            user_id: User ID
            query: Query text
            response_time: Response time in seconds
            success: Whether query was successful
            error_message: Error message if query failed
        """
        try:
            self.analytics_service.track_user_query(
                user_id=user_id,
                query=query,
                response_time=response_time,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            self.logger.error(f"Failed to track query metric: {e}")
    
    async def _track_system_metrics(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_agent: str
    ) -> None:
        """
        Track system performance metrics.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            response_time: Response time in seconds
            status_code: HTTP status code
            user_agent: User agent string
        """
        try:
            # Track response time metric
            self.analytics_service.record_system_metric(
                metric_name="api_response_time",
                metric_value=response_time,
                metric_unit="seconds",
                tags={
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code
                }
            )
            
            # Track request count metric
            self.analytics_service.record_system_metric(
                metric_name="api_request_count",
                metric_value=1,
                metric_unit="count",
                tags={
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to track system metrics: {e}")
    
    def _should_track_endpoint(self, path: str) -> bool:
        """
        Determine if an endpoint should be tracked.
        
        Args:
            path: Request path
            
        Returns:
            True if endpoint should be tracked
        """
        # Skip health checks and static files
        skip_patterns = [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/"
        ]
        
        for pattern in skip_patterns:
            if pattern in path:
                return False
        
        return True
    
    def _is_query_endpoint(self, path: str) -> bool:
        """
        Determine if an endpoint is a query/chat endpoint.
        
        Args:
            path: Request path
            
        Returns:
            True if endpoint is query-related
        """
        query_patterns = [
            "/api/v1/chat",
            "/ws/chat",
            "/api/v1/ai",
            "/api/v1/logs/search"
        ]
        
        for pattern in query_patterns:
            if pattern in path:
                return True
        
        return False


class MetricsCollector:
    """
    Utility class for collecting various system metrics.
    
    Provides methods to collect CPU, memory, and other system metrics
    for monitoring and analytics.
    """
    
    def __init__(self, analytics_service: Optional[AnalyticsService] = None):
        """
        Initialize metrics collector.
        
        Args:
            analytics_service: Analytics service instance
        """
        self.analytics_service = analytics_service or AnalyticsService()
        self.logger = logger
    
    async def collect_system_metrics(self) -> None:
        """
        Collect and record system performance metrics.
        
        This method should be called periodically to collect
        system-level performance metrics.
        """
        try:
            # Collect CPU usage (placeholder - would use psutil in production)
            await self._collect_cpu_metrics()
            
            # Collect memory usage
            await self._collect_memory_metrics()
            
            # Collect database metrics
            await self._collect_database_metrics()
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    async def _collect_cpu_metrics(self) -> None:
        """Collect CPU usage metrics."""
        try:
            # Placeholder implementation
            # In production, would use psutil.cpu_percent()
            cpu_usage = 0.0  # psutil.cpu_percent(interval=1)
            
            self.analytics_service.record_system_metric(
                metric_name="cpu_usage",
                metric_value=cpu_usage,
                metric_unit="percent",
                tags={"component": "system"}
            )
        except Exception as e:
            self.logger.error(f"Failed to collect CPU metrics: {e}")
    
    async def _collect_memory_metrics(self) -> None:
        """Collect memory usage metrics."""
        try:
            # Placeholder implementation
            # In production, would use psutil.virtual_memory()
            memory_usage = 0.0  # psutil.virtual_memory().percent
            memory_used_mb = 0.0  # psutil.virtual_memory().used / 1024 / 1024
            
            self.analytics_service.record_system_metric(
                metric_name="memory_usage",
                metric_value=memory_usage,
                metric_unit="percent",
                tags={"component": "system"}
            )
            
            self.analytics_service.record_system_metric(
                metric_name="memory_used",
                metric_value=memory_used_mb,
                metric_unit="MB",
                tags={"component": "system"}
            )
        except Exception as e:
            self.logger.error(f"Failed to collect memory metrics: {e}")
    
    async def _collect_database_metrics(self) -> None:
        """Collect database performance metrics."""
        try:
            # Placeholder implementation
            # In production, would query database connection pool stats
            from core.database import db_manager
            
            connection_info = db_manager.get_connection_info()
            
            self.analytics_service.record_system_metric(
                metric_name="db_connections_active",
                metric_value=float(connection_info.get("checked_out_connections", 0)),
                metric_unit="count",
                tags={"component": "database"}
            )
            
            self.analytics_service.record_system_metric(
                metric_name="db_connections_idle",
                metric_value=float(connection_info.get("checked_in_connections", 0)),
                metric_unit="count",
                tags={"component": "database"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")


# Utility function to create analytics middleware
def create_analytics_middleware(analytics_service: Optional[AnalyticsService] = None) -> AnalyticsMiddleware:
    """
    Create analytics middleware instance.
    
    Args:
        analytics_service: Optional analytics service instance
        
    Returns:
        Configured analytics middleware
    """
    return AnalyticsMiddleware(app=None, analytics_service=analytics_service)


# Background task for periodic metrics collection
async def periodic_metrics_collection(
    collector: Optional[MetricsCollector] = None,
    interval_seconds: int = 60
) -> None:
    """
    Background task for periodic system metrics collection.
    
    Args:
        collector: Metrics collector instance
        interval_seconds: Collection interval in seconds
    """
    import asyncio
    
    if collector is None:
        collector = MetricsCollector()
    
    while True:
        try:
            await collector.collect_system_metrics()
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Periodic metrics collection failed: {e}")
            await asyncio.sleep(interval_seconds)  # Continue despite errors