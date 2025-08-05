"""
Health check system for Wazuh AI Companion services.

This module provides comprehensive health checks for all application services,
including database connectivity, external service availability, and system resources.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

import psutil
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db, engine
from core.redis_client import get_redis_client
from core.config import get_settings
from core.metrics import metrics

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result."""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time: Optional[float] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check to dictionary."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        
        if self.response_time is not None:
            result["response_time_ms"] = round(self.response_time * 1000, 2)
        
        if self.details:
            result["details"] = self.details
        
        return result


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.settings = get_settings()
        self._last_check_time = None
        self._cached_results = {}
        self._cache_duration = 30  # seconds
    
    async def check_database_health(self) -> HealthCheck:
        """Check PostgreSQL database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            db = next(get_db())
            
            # Test query execution
            result = db.execute(text("SELECT 1 as test")).fetchone()
            if result and result.test == 1:
                # Get connection pool stats
                pool = engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                # Check for slow queries or high connection usage
                connection_usage = (pool.checkedout() / pool.size()) * 100
                
                if connection_usage > 80:
                    status = HealthStatus.DEGRADED
                    message = f"High database connection usage: {connection_usage:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database connectivity normal"
                
                response_time = time.time() - start_time
                
                return HealthCheck(
                    name="database",
                    status=status,
                    message=message,
                    details=pool_status,
                    response_time=response_time
                )
            else:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database query test failed",
                    response_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time=time.time() - start_time
            )
        finally:
            if 'db' in locals():
                db.close()
    
    async def check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            redis_client = get_redis_client()
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Get Redis info
            info = await redis_client.info()
            memory_usage = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            connected_clients = info.get('connected_clients', 0)
            
            # Calculate memory usage percentage
            if max_memory > 0:
                memory_percentage = (memory_usage / max_memory) * 100
            else:
                memory_percentage = 0
            
            # Determine health status
            if memory_percentage > 90:
                status = HealthStatus.DEGRADED
                message = f"High Redis memory usage: {memory_percentage:.1f}%"
            elif connected_clients > 100:
                status = HealthStatus.DEGRADED
                message = f"High Redis client connections: {connected_clients}"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis connectivity normal"
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="redis",
                status=status,
                message=message,
                details={
                    "memory_usage_bytes": memory_usage,
                    "memory_usage_percentage": round(memory_percentage, 2),
                    "connected_clients": connected_clients,
                    "redis_version": info.get('redis_version', 'unknown')
                },
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_ai_service_health(self) -> HealthCheck:
        """Check AI service health including LLM and vector store."""
        start_time = time.time()
        
        try:
            from services import get_ai_service
            ai_service = get_ai_service()
            
            # Test vector store availability
            if hasattr(ai_service, 'vectorstore') and ai_service.vectorstore:
                # Test vector store with a simple query
                try:
                    test_results = ai_service.vectorstore.similarity_search("test", k=1)
                    vector_store_status = "available"
                    vector_store_docs = len(test_results) if test_results else 0
                except Exception as e:
                    vector_store_status = f"error: {str(e)}"
                    vector_store_docs = 0
            else:
                vector_store_status = "not_initialized"
                vector_store_docs = 0
            
            # Test LLM connectivity (if available)
            llm_status = "unknown"
            try:
                if hasattr(ai_service, 'llm') and ai_service.llm:
                    # Simple test query to LLM
                    test_response = await asyncio.wait_for(
                        asyncio.create_task(ai_service._test_llm_connection()),
                        timeout=10.0
                    )
                    llm_status = "available" if test_response else "unavailable"
                else:
                    llm_status = "not_configured"
            except asyncio.TimeoutError:
                llm_status = "timeout"
            except Exception as e:
                llm_status = f"error: {str(e)}"
            
            # Determine overall AI service health
            if vector_store_status == "available" and llm_status == "available":
                status = HealthStatus.HEALTHY
                message = "AI service fully operational"
            elif vector_store_status == "available" or llm_status == "available":
                status = HealthStatus.DEGRADED
                message = "AI service partially operational"
            else:
                status = HealthStatus.UNHEALTHY
                message = "AI service unavailable"
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="ai_service",
                status=status,
                message=message,
                details={
                    "vector_store_status": vector_store_status,
                    "vector_store_documents": vector_store_docs,
                    "llm_status": llm_status
                },
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return HealthCheck(
                name="ai_service",
                status=HealthStatus.UNHEALTHY,
                message=f"AI service check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_log_service_health(self) -> HealthCheck:
        """Check log service health and log processing capabilities."""
        start_time = time.time()
        
        try:
            from services import get_log_service
            log_service = get_log_service()
            
            # Check if log service can access log directories
            log_stats = {
                "total_logs": 0,
                "last_processed": None,
                "processing_errors": 0
            }
            
            # Test log service functionality
            try:
                # This would typically check log file access, processing status, etc.
                if hasattr(log_service, 'get_log_statistics'):
                    stats = log_service.get_log_statistics()
                    log_stats.update(stats)
                
                status = HealthStatus.HEALTHY
                message = "Log service operational"
                
            except Exception as e:
                status = HealthStatus.DEGRADED
                message = f"Log service partially operational: {str(e)}"
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="log_service",
                status=status,
                message=message,
                details=log_stats,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Log service health check failed: {e}")
            return HealthCheck(
                name="log_service",
                status=HealthStatus.UNHEALTHY,
                message=f"Log service unavailable: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_system_resources(self) -> HealthCheck:
        """Check system resource utilization."""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                load_1min = load_avg[0]
            except (AttributeError, OSError):
                load_1min = None
            
            # Determine health status based on resource usage
            critical_resources = []
            warning_resources = []
            
            if cpu_percent > 90:
                critical_resources.append(f"CPU: {cpu_percent:.1f}%")
            elif cpu_percent > 75:
                warning_resources.append(f"CPU: {cpu_percent:.1f}%")
            
            if memory_percent > 90:
                critical_resources.append(f"Memory: {memory_percent:.1f}%")
            elif memory_percent > 75:
                warning_resources.append(f"Memory: {memory_percent:.1f}%")
            
            if disk_percent > 90:
                critical_resources.append(f"Disk: {disk_percent:.1f}%")
            elif disk_percent > 80:
                warning_resources.append(f"Disk: {disk_percent:.1f}%")
            
            # Determine overall status
            if critical_resources:
                status = HealthStatus.UNHEALTHY
                message = f"Critical resource usage: {', '.join(critical_resources)}"
            elif warning_resources:
                status = HealthStatus.DEGRADED
                message = f"High resource usage: {', '.join(warning_resources)}"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            response_time = time.time() - start_time
            
            details = {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk_percent, 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
            
            if load_1min is not None:
                details["load_average_1min"] = round(load_1min, 2)
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"System resources health check failed: {e}")
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resources check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_websocket_health(self) -> HealthCheck:
        """Check WebSocket service health."""
        start_time = time.time()
        
        try:
            from services import get_chat_service
            chat_service = get_chat_service()
            
            # Get WebSocket connection statistics
            active_connections = 0
            if hasattr(chat_service, 'active_connections'):
                active_connections = len(chat_service.active_connections)
            
            # Check for any connection issues
            connection_errors = 0
            if hasattr(chat_service, 'connection_errors'):
                connection_errors = chat_service.connection_errors
            
            # Determine health status
            if connection_errors > 10:
                status = HealthStatus.DEGRADED
                message = f"WebSocket service has {connection_errors} recent errors"
            else:
                status = HealthStatus.HEALTHY
                message = "WebSocket service operational"
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="websocket_service",
                status=status,
                message=message,
                details={
                    "active_connections": active_connections,
                    "connection_errors": connection_errors
                },
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}")
            return HealthCheck(
                name="websocket_service",
                status=HealthStatus.UNHEALTHY,
                message=f"WebSocket service check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def run_all_health_checks(self, use_cache: bool = True) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        current_time = time.time()
        
        # Check if we can use cached results
        if (use_cache and self._last_check_time and 
            current_time - self._last_check_time < self._cache_duration):
            return self._cached_results
        
        start_time = time.time()
        
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_ai_service_health(),
            self.check_log_service_health(),
            self.check_system_resources(),
            self.check_websocket_health(),
            return_exceptions=True
        )
        
        # Process results
        results = {}
        overall_status = HealthStatus.HEALTHY
        unhealthy_services = []
        degraded_services = []
        
        for check in health_checks:
            if isinstance(check, Exception):
                # Handle exceptions from health checks
                logger.error(f"Health check exception: {check}")
                continue
            
            results[check.name] = check.to_dict()
            
            # Update overall status
            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                unhealthy_services.append(check.name)
            elif check.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED
                degraded_services.append(check.name)
        
        # Build summary
        total_checks = len(results)
        healthy_checks = sum(1 for r in results.values() if r["status"] == "healthy")
        
        summary = {
            "overall_status": overall_status.value,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "degraded_checks": len(degraded_services),
            "unhealthy_checks": len(unhealthy_services),
            "check_duration_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if unhealthy_services:
            summary["unhealthy_services"] = unhealthy_services
        if degraded_services:
            summary["degraded_services"] = degraded_services
        
        # Build final result
        health_result = {
            "summary": summary,
            "checks": results,
            "application": {
                "name": self.settings.app_name,
                "version": self.settings.version,
                "environment": self.settings.environment
            }
        }
        
        # Cache results
        self._cached_results = health_result
        self._last_check_time = current_time
        
        # Record health check metrics
        for check in health_checks:
            if not isinstance(check, Exception):
                metrics.record_health_check(
                    service=check.name,
                    status=check.status.value,
                    duration=check.response_time or 0.0
                )
        
        # Record system error if overall status is unhealthy
        if overall_status == HealthStatus.UNHEALTHY:
            metrics.record_system_error("health_check", "system")
        
        return health_result
    
    async def get_service_health(self, service_name: str) -> Optional[HealthCheck]:
        """Get health status for a specific service."""
        health_check_methods = {
            "database": self.check_database_health,
            "redis": self.check_redis_health,
            "ai_service": self.check_ai_service_health,
            "log_service": self.check_log_service_health,
            "system_resources": self.check_system_resources,
            "websocket_service": self.check_websocket_health
        }
        
        if service_name not in health_check_methods:
            return None
        
        try:
            return await health_check_methods[service_name]()
        except Exception as e:
            logger.error(f"Failed to check health for {service_name}: {e}")
            return HealthCheck(
                name=service_name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}"
            )


# Global health checker instance
health_checker = HealthChecker()


async def get_application_health(use_cache: bool = True) -> Dict[str, Any]:
    """Get comprehensive application health status."""
    return await health_checker.run_all_health_checks(use_cache=use_cache)


async def get_service_health(service_name: str) -> Optional[Dict[str, Any]]:
    """Get health status for a specific service."""
    health_check = await health_checker.get_service_health(service_name)
    return health_check.to_dict() if health_check else None