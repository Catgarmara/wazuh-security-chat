"""
Enterprise-grade resource management system for embedded AI security appliance.

This module provides intelligent resource monitoring, automatic model management,
and proactive resource optimization to ensure stable 24/7 security operations.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import psutil

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False

from core.exceptions import ResourceExhaustionError, ErrorCode
from core.config import get_settings

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of system resources to monitor."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    GPU = "gpu"
    NETWORK = "network"


class ResourceStatus(str, Enum):
    """Resource utilization status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


@dataclass
class ResourceThresholds:
    """Resource utilization thresholds for different alert levels."""
    warning: float = 75.0
    critical: float = 85.0
    exhausted: float = 95.0


@dataclass
class ResourceMetrics:
    """Current resource utilization metrics."""
    resource_type: ResourceType
    current_usage: float
    available: float
    total: float
    status: ResourceStatus
    timestamp: datetime
    details: Dict[str, Any]


class ResourceManager:
    """
    Enterprise-grade resource management system for embedded AI operations.
    
    Provides:
    - Real-time resource monitoring
    - Automatic model management based on resource availability
    - Proactive resource optimization
    - Intelligent fallback mechanisms
    - Recovery suggestions for operations teams
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_settings = self.settings.embedded_ai
        
        # Resource thresholds
        self.thresholds = {
            ResourceType.CPU: ResourceThresholds(70.0, 85.0, 95.0),
            ResourceType.MEMORY: ResourceThresholds(75.0, 85.0, 95.0),
            ResourceType.DISK: ResourceThresholds(80.0, 90.0, 95.0),
            ResourceType.GPU: ResourceThresholds(75.0, 85.0, 95.0)
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = self.ai_settings.resource_monitoring_interval
        
        # Resource history for trend analysis
        self.resource_history: Dict[ResourceType, List[ResourceMetrics]] = {
            resource_type: [] for resource_type in ResourceType
        }
        self.history_retention_hours = 24
        
        # Callbacks for resource events
        self.resource_callbacks: Dict[ResourceStatus, List[Callable]] = {
            status: [] for status in ResourceStatus
        }
        
        # Auto-recovery state
        self.recovery_attempts: Dict[str, int] = {}
        self.max_recovery_attempts = 3
        self.recovery_cooldown_minutes = 15
        self.last_recovery_attempt: Dict[str, datetime] = {}
        
        # Model management integration
        self.model_manager = None
        self.auto_model_management = self.ai_settings.auto_unload_inactive_models
        
        logger.info("Resource Manager initialized with enterprise-grade monitoring")
    
    def set_model_manager(self, model_manager) -> None:
        """Set the model manager for automatic model lifecycle management."""
        self.model_manager = model_manager
        logger.info("Model manager integration enabled for resource management")
    
    def register_resource_callback(self, status: ResourceStatus, callback: Callable) -> None:
        """Register a callback for resource status changes."""
        self.resource_callbacks[status].append(callback)
        logger.debug(f"Registered callback for {status.value} resource status")
    
    def start_monitoring(self) -> None:
        """Start continuous resource monitoring."""
        if self.monitoring_active:
            logger.warning("Resource monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ResourceMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        logger.info("Resource monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Collect current resource metrics
                metrics = self._collect_resource_metrics()
                
                # Update resource history
                self._update_resource_history(metrics)
                
                # Check for resource issues and trigger callbacks
                self._check_resource_thresholds(metrics)
                
                # Perform automatic resource management
                if self.auto_model_management:
                    self._perform_automatic_model_management(metrics)
                
                # Clean up old history data
                self._cleanup_resource_history()
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
            
            # Wait for next monitoring cycle
            time.sleep(self.monitoring_interval)
        
        logger.info("Resource monitoring loop stopped")
    
    def _collect_resource_metrics(self) -> Dict[ResourceType, ResourceMetrics]:
        """Collect current resource utilization metrics."""
        metrics = {}
        current_time = datetime.now()
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_status = self._determine_resource_status(ResourceType.CPU, cpu_percent)
            
            metrics[ResourceType.CPU] = ResourceMetrics(
                resource_type=ResourceType.CPU,
                current_usage=cpu_percent,
                available=100.0 - cpu_percent,
                total=100.0,
                status=cpu_status,
                timestamp=current_time,
                details={
                    "cpu_count": psutil.cpu_count(),
                    "cpu_count_logical": psutil.cpu_count(logical=True),
                    "load_avg": getattr(psutil, 'getloadavg', lambda: [0, 0, 0])()[:3]
                }
            )
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = self._determine_resource_status(ResourceType.MEMORY, memory_percent)
            
            metrics[ResourceType.MEMORY] = ResourceMetrics(
                resource_type=ResourceType.MEMORY,
                current_usage=memory_percent,
                available=memory.available / (1024**3),  # GB
                total=memory.total / (1024**3),  # GB
                status=memory_status,
                timestamp=current_time,
                details={
                    "used_gb": memory.used / (1024**3),
                    "cached_gb": getattr(memory, 'cached', 0) / (1024**3),
                    "buffers_gb": getattr(memory, 'buffers', 0) / (1024**3),
                    "swap_percent": psutil.swap_memory().percent
                }
            )
            
            # Disk metrics
            disk = psutil.disk_usage(self.ai_settings.models_path)
            disk_percent = (disk.used / disk.total) * 100
            disk_status = self._determine_resource_status(ResourceType.DISK, disk_percent)
            
            metrics[ResourceType.DISK] = ResourceMetrics(
                resource_type=ResourceType.DISK,
                current_usage=disk_percent,
                available=disk.free / (1024**3),  # GB
                total=disk.total / (1024**3),  # GB
                status=disk_status,
                timestamp=current_time,
                details={
                    "used_gb": disk.used / (1024**3),
                    "models_path": str(self.ai_settings.models_path),
                    "io_stats": dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else {}
                }
            )
            
            # GPU metrics (if available)
            if GPUTIL_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        # Use first GPU for primary metrics
                        gpu = gpus[0]
                        gpu_percent = gpu.load * 100
                        gpu_status = self._determine_resource_status(ResourceType.GPU, gpu_percent)
                        
                        metrics[ResourceType.GPU] = ResourceMetrics(
                            resource_type=ResourceType.GPU,
                            current_usage=gpu_percent,
                            available=(gpu.memoryTotal - gpu.memoryUsed) / 1024,  # GB
                            total=gpu.memoryTotal / 1024,  # GB
                            status=gpu_status,
                            timestamp=current_time,
                            details={
                                "gpu_count": len(gpus),
                                "gpu_name": gpu.name,
                                "memory_used_gb": gpu.memoryUsed / 1024,
                                "temperature": gpu.temperature,
                                "all_gpus": [
                                    {
                                        "id": g.id,
                                        "name": g.name,
                                        "load": g.load * 100,
                                        "memory_used_gb": g.memoryUsed / 1024,
                                        "memory_total_gb": g.memoryTotal / 1024,
                                        "temperature": g.temperature
                                    }
                                    for g in gpus
                                ]
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to collect GPU metrics: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")
        
        return metrics
    
    def _determine_resource_status(self, resource_type: ResourceType, usage_percent: float) -> ResourceStatus:
        """Determine resource status based on usage and thresholds."""
        thresholds = self.thresholds.get(resource_type, ResourceThresholds())
        
        if usage_percent >= thresholds.exhausted:
            return ResourceStatus.EXHAUSTED
        elif usage_percent >= thresholds.critical:
            return ResourceStatus.CRITICAL
        elif usage_percent >= thresholds.warning:
            return ResourceStatus.WARNING
        else:
            return ResourceStatus.NORMAL
    
    def _update_resource_history(self, metrics: Dict[ResourceType, ResourceMetrics]) -> None:
        """Update resource history for trend analysis."""
        for resource_type, metric in metrics.items():
            history = self.resource_history[resource_type]
            history.append(metric)
            
            # Limit history size
            if len(history) > 1000:  # Keep last 1000 measurements
                history.pop(0)
    
    def _cleanup_resource_history(self) -> None:
        """Remove old resource history data."""
        cutoff_time = datetime.now() - timedelta(hours=self.history_retention_hours)
        
        for resource_type in ResourceType:
            history = self.resource_history[resource_type]
            self.resource_history[resource_type] = [
                metric for metric in history if metric.timestamp > cutoff_time
            ]
    
    def _check_resource_thresholds(self, metrics: Dict[ResourceType, ResourceMetrics]) -> None:
        """Check resource thresholds and trigger appropriate callbacks."""
        for resource_type, metric in metrics.items():
            # Trigger callbacks for current status
            callbacks = self.resource_callbacks.get(metric.status, [])
            for callback in callbacks:
                try:
                    callback(metric)
                except Exception as e:
                    logger.error(f"Error in resource callback for {resource_type.value}: {e}")
            
            # Log resource issues
            if metric.status in [ResourceStatus.CRITICAL, ResourceStatus.EXHAUSTED]:
                logger.warning(
                    f"{resource_type.value.upper()} resource {metric.status.value}: "
                    f"{metric.current_usage:.1f}% usage"
                )
            
            # Attempt automatic recovery for critical resources
            if metric.status == ResourceStatus.EXHAUSTED:
                self._attempt_automatic_recovery(metric)
    
    def _attempt_automatic_recovery(self, metric: ResourceMetrics) -> None:
        """Attempt automatic recovery for exhausted resources."""
        recovery_key = f"{metric.resource_type.value}_recovery"
        current_time = datetime.now()
        
        # Check recovery cooldown
        last_attempt = self.last_recovery_attempt.get(recovery_key)
        if last_attempt:
            time_since_last = (current_time - last_attempt).total_seconds() / 60
            if time_since_last < self.recovery_cooldown_minutes:
                return
        
        # Check max recovery attempts
        attempts = self.recovery_attempts.get(recovery_key, 0)
        if attempts >= self.max_recovery_attempts:
            logger.error(
                f"Maximum recovery attempts ({self.max_recovery_attempts}) reached for "
                f"{metric.resource_type.value} resource exhaustion"
            )
            return
        
        # Attempt recovery based on resource type
        recovery_success = False
        
        try:
            if metric.resource_type == ResourceType.MEMORY:
                recovery_success = self._recover_memory_resources()
            elif metric.resource_type == ResourceType.DISK:
                recovery_success = self._recover_disk_resources()
            elif metric.resource_type == ResourceType.CPU:
                recovery_success = self._recover_cpu_resources()
            elif metric.resource_type == ResourceType.GPU:
                recovery_success = self._recover_gpu_resources()
            
            # Update recovery tracking
            self.recovery_attempts[recovery_key] = attempts + 1
            self.last_recovery_attempt[recovery_key] = current_time
            
            if recovery_success:
                logger.info(f"Automatic recovery successful for {metric.resource_type.value} exhaustion")
                # Reset recovery attempts on success
                self.recovery_attempts[recovery_key] = 0
            else:
                logger.warning(f"Automatic recovery failed for {metric.resource_type.value} exhaustion")
                
        except Exception as e:
            logger.error(f"Error during automatic recovery for {metric.resource_type.value}: {e}")
    
    def _recover_memory_resources(self) -> bool:
        """Attempt to recover memory resources by unloading inactive models."""
        if not self.model_manager:
            return False
        
        try:
            # Get inactive models
            inactive_models = self.model_manager.get_inactive_models(
                inactive_threshold_minutes=self.ai_settings.ai_model_inactivity_timeout_minutes // 2
            )
            
            if not inactive_models:
                return False
            
            # Unload least recently used models
            unloaded_count = 0
            for model_id in inactive_models[:2]:  # Unload up to 2 models
                if self.model_manager.unload_model(model_id):
                    unloaded_count += 1
                    logger.info(f"Unloaded inactive model {model_id} to free memory")
            
            return unloaded_count > 0
            
        except Exception as e:
            logger.error(f"Failed to recover memory resources: {e}")
            return False
    
    def _recover_disk_resources(self) -> bool:
        """Attempt to recover disk resources by cleaning up temporary files."""
        try:
            # Clean up model cache if enabled
            if hasattr(self.model_manager, 'cleanup_model_cache'):
                return self.model_manager.cleanup_model_cache()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to recover disk resources: {e}")
            return False
    
    def _recover_cpu_resources(self) -> bool:
        """Attempt to recover CPU resources by reducing concurrent operations."""
        try:
            # Reduce batch sizes or concurrent operations if possible
            if self.model_manager:
                return self.model_manager.reduce_resource_usage()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to recover CPU resources: {e}")
            return False
    
    def _recover_gpu_resources(self) -> bool:
        """Attempt to recover GPU resources by optimizing GPU usage."""
        try:
            # Reduce GPU layers or switch to CPU-only mode temporarily
            if self.model_manager:
                return self.model_manager.optimize_gpu_usage()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to recover GPU resources: {e}")
            return False
    
    def _perform_automatic_model_management(self, metrics: Dict[ResourceType, ResourceMetrics]) -> None:
        """Perform automatic model management based on resource availability."""
        if not self.model_manager:
            return
        
        try:
            memory_metric = metrics.get(ResourceType.MEMORY)
            if not memory_metric:
                return
            
            # Unload inactive models if memory usage is high
            if memory_metric.status in [ResourceStatus.WARNING, ResourceStatus.CRITICAL]:
                inactive_models = self.model_manager.get_inactive_models(
                    inactive_threshold_minutes=self.ai_settings.ai_model_inactivity_timeout_minutes
                )
                
                for model_id in inactive_models:
                    if self.model_manager.unload_model(model_id):
                        logger.info(f"Auto-unloaded inactive model {model_id} due to high memory usage")
                        break  # Unload one at a time
            
        except Exception as e:
            logger.error(f"Error in automatic model management: {e}")
    
    def get_current_resource_status(self) -> Dict[str, Any]:
        """Get current resource status summary."""
        metrics = self._collect_resource_metrics()
        
        status_summary = {
            "overall_status": "normal",
            "timestamp": datetime.now().isoformat(),
            "resources": {}
        }
        
        # Determine overall status
        critical_resources = []
        warning_resources = []
        
        for resource_type, metric in metrics.items():
            resource_info = {
                "usage_percent": round(metric.current_usage, 2),
                "available": round(metric.available, 2),
                "total": round(metric.total, 2),
                "status": metric.status.value,
                "details": metric.details
            }
            
            status_summary["resources"][resource_type.value] = resource_info
            
            if metric.status in [ResourceStatus.CRITICAL, ResourceStatus.EXHAUSTED]:
                critical_resources.append(resource_type.value)
            elif metric.status == ResourceStatus.WARNING:
                warning_resources.append(resource_type.value)
        
        # Set overall status
        if critical_resources:
            status_summary["overall_status"] = "critical"
            status_summary["critical_resources"] = critical_resources
        elif warning_resources:
            status_summary["overall_status"] = "warning"
            status_summary["warning_resources"] = warning_resources
        
        return status_summary
    
    def get_resource_trends(self, resource_type: ResourceType, hours: int = 1) -> Dict[str, Any]:
        """Get resource usage trends for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = self.resource_history.get(resource_type, [])
        
        # Filter history for the requested time period
        recent_history = [
            metric for metric in history if metric.timestamp > cutoff_time
        ]
        
        if not recent_history:
            return {
                "resource_type": resource_type.value,
                "period_hours": hours,
                "data_points": 0,
                "trend": "no_data"
            }
        
        # Calculate trend statistics
        usage_values = [metric.current_usage for metric in recent_history]
        avg_usage = sum(usage_values) / len(usage_values)
        min_usage = min(usage_values)
        max_usage = max(usage_values)
        
        # Determine trend direction
        if len(usage_values) >= 2:
            recent_avg = sum(usage_values[-10:]) / min(10, len(usage_values))
            older_avg = sum(usage_values[:10]) / min(10, len(usage_values))
            
            if recent_avg > older_avg * 1.1:
                trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "resource_type": resource_type.value,
            "period_hours": hours,
            "data_points": len(recent_history),
            "average_usage": round(avg_usage, 2),
            "min_usage": round(min_usage, 2),
            "max_usage": round(max_usage, 2),
            "trend": trend,
            "current_usage": round(recent_history[-1].current_usage, 2) if recent_history else 0
        }
    
    def generate_resource_recommendations(self) -> List[Dict[str, Any]]:
        """Generate resource optimization recommendations for operations teams."""
        recommendations = []
        current_status = self.get_current_resource_status()
        
        for resource_name, resource_info in current_status["resources"].items():
            usage = resource_info["usage_percent"]
            status = resource_info["status"]
            
            if status in ["critical", "exhausted"]:
                if resource_name == "memory":
                    recommendations.append({
                        "priority": "high",
                        "resource": resource_name,
                        "issue": f"Memory usage at {usage}%",
                        "recommendations": [
                            "Reduce max_concurrent_models in configuration",
                            "Enable automatic model unloading",
                            "Use smaller quantized model variants",
                            "Increase system RAM if possible"
                        ],
                        "immediate_actions": [
                            "Unload inactive AI models",
                            "Clear model cache",
                            "Restart embedded AI service"
                        ]
                    })
                elif resource_name == "disk":
                    recommendations.append({
                        "priority": "high",
                        "resource": resource_name,
                        "issue": f"Disk usage at {usage}%",
                        "recommendations": [
                            "Clean up old model files",
                            "Reduce model cache size",
                            "Move models to larger storage volume",
                            "Enable automatic cache cleanup"
                        ],
                        "immediate_actions": [
                            "Delete unused model files",
                            "Clear temporary files",
                            "Compress old log files"
                        ]
                    })
                elif resource_name == "cpu":
                    recommendations.append({
                        "priority": "high",
                        "resource": resource_name,
                        "issue": f"CPU usage at {usage}%",
                        "recommendations": [
                            "Reduce concurrent AI inference requests",
                            "Lower model batch sizes",
                            "Use GPU acceleration if available",
                            "Scale horizontally with additional instances"
                        ],
                        "immediate_actions": [
                            "Reduce active model count",
                            "Lower inference batch sizes",
                            "Enable request queuing"
                        ]
                    })
            
            elif status == "warning":
                recommendations.append({
                    "priority": "medium",
                    "resource": resource_name,
                    "issue": f"{resource_name.title()} usage at {usage}%",
                    "recommendations": [
                        f"Monitor {resource_name} usage trends",
                        f"Consider optimizing {resource_name} usage",
                        "Plan for resource scaling if trend continues"
                    ],
                    "immediate_actions": [
                        f"Review {resource_name} usage patterns",
                        "Enable proactive monitoring alerts"
                    ]
                })
        
        return recommendations
    
    def shutdown(self) -> None:
        """Gracefully shutdown the resource manager."""
        logger.info("Shutting down Resource Manager...")
        self.stop_monitoring()
        logger.info("Resource Manager shutdown complete")


# Global resource manager instance
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    return resource_manager