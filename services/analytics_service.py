"""
Analytics service for usage metrics collection and monitoring.

This service handles query tracking, performance metrics collection,
user engagement monitoring, and system performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from core.database import get_db_session
from models.database import QueryMetrics, SystemMetrics, User, ChatSession, Message, LogEntry
from models.schemas import (
    QueryMetricsCreate, QueryMetricsResponse, SystemMetricsCreate, 
    SystemMetricsResponse, UsageMetrics, DashboardData, DateRange
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for analytics and monitoring functionality.
    
    Handles usage metrics collection, performance monitoring,
    and dashboard data aggregation.
    """
    
    def __init__(self):
        """Initialize the analytics service."""
        self.logger = logger
    
    def track_user_query(
        self, 
        user_id: UUID, 
        query: str, 
        response_time: float,
        success: bool = True,
        error_message: Optional[str] = None,
        tokens_used: Optional[int] = None,
        logs_searched: Optional[int] = None
    ) -> QueryMetricsResponse:
        """
        Track a user query for analytics.
        
        Args:
            user_id: ID of the user making the query
            query: The query text
            response_time: Response time in seconds
            success: Whether the query was successful
            error_message: Error message if query failed
            tokens_used: Number of LLM tokens used
            logs_searched: Number of logs searched
            
        Returns:
            QueryMetricsResponse: Created query metrics record
        """
        try:
            with get_db_session() as session:
                # Create query metrics record
                metrics_data = QueryMetricsCreate(
                    user_id=user_id,
                    query=query,
                    response_time=response_time,
                    success=success,
                    error_message=error_message,
                    tokens_used=tokens_used,
                    logs_searched=logs_searched
                )
                
                query_metrics = QueryMetrics(
                    user_id=metrics_data.user_id,
                    query=metrics_data.query,
                    response_time=metrics_data.response_time,
                    success=metrics_data.success,
                    error_message=metrics_data.error_message,
                    tokens_used=metrics_data.tokens_used,
                    logs_searched=metrics_data.logs_searched
                )
                
                session.add(query_metrics)
                session.flush()
                
                self.logger.info(
                    f"Tracked query metrics for user {user_id}: "
                    f"response_time={response_time}s, success={success}"
                )
                
                return QueryMetricsResponse.from_orm(query_metrics)
                
        except Exception as e:
            self.logger.error(f"Failed to track user query: {e}")
            raise
    
    def record_system_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> SystemMetricsResponse:
        """
        Record a system performance metric.
        
        Args:
            metric_name: Name of the metric (e.g., 'cpu_usage', 'memory_usage')
            metric_value: Numeric value of the metric
            metric_unit: Unit of measurement (e.g., 'percent', 'bytes')
            tags: Additional tags/labels for the metric
            
        Returns:
            SystemMetricsResponse: Created system metrics record
        """
        try:
            with get_db_session() as session:
                metrics_data = SystemMetricsCreate(
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_unit=metric_unit,
                    tags=tags
                )
                
                system_metrics = SystemMetrics(
                    metric_name=metrics_data.metric_name,
                    metric_value=metrics_data.metric_value,
                    metric_unit=metrics_data.metric_unit,
                    tags=metrics_data.tags
                )
                
                session.add(system_metrics)
                session.flush()
                
                self.logger.debug(
                    f"Recorded system metric: {metric_name}={metric_value} {metric_unit or ''}"
                )
                
                return SystemMetricsResponse.from_orm(system_metrics)
                
        except Exception as e:
            self.logger.error(f"Failed to record system metric: {e}")
            raise
    
    def get_usage_metrics(
        self, 
        date_range: Optional[DateRange] = None,
        user_id: Optional[UUID] = None
    ) -> UsageMetrics:
        """
        Get usage metrics for a specified date range.
        
        Args:
            date_range: Date range for metrics (defaults to last 24 hours)
            user_id: Optional user ID to filter metrics
            
        Returns:
            UsageMetrics: Aggregated usage metrics
        """
        try:
            with get_db_session() as session:
                # Default to last 24 hours if no date range provided
                if date_range is None:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=24)
                else:
                    start_time = date_range.start_date
                    end_time = date_range.end_date
                
                # Build base query
                query = session.query(QueryMetrics).filter(
                    and_(
                        QueryMetrics.timestamp >= start_time,
                        QueryMetrics.timestamp <= end_time
                    )
                )
                
                # Filter by user if specified
                if user_id:
                    query = query.filter(QueryMetrics.user_id == user_id)
                
                # Get all metrics for the period
                metrics = query.all()
                
                if not metrics:
                    return UsageMetrics(
                        total_queries=0,
                        unique_users=0,
                        avg_response_time=0.0,
                        error_rate=0.0,
                        peak_usage_time=None,
                        date_range={"start_date": start_time, "end_date": end_time}
                    )
                
                # Calculate aggregated metrics
                total_queries = len(metrics)
                unique_users = len(set(m.user_id for m in metrics))
                avg_response_time = sum(m.response_time for m in metrics) / total_queries
                error_count = sum(1 for m in metrics if not m.success)
                error_rate = error_count / total_queries if total_queries > 0 else 0.0
                
                # Find peak usage time (hour with most queries)
                peak_usage_time = self._find_peak_usage_time(session, start_time, end_time, user_id)
                
                return UsageMetrics(
                    total_queries=total_queries,
                    unique_users=unique_users,
                    avg_response_time=avg_response_time,
                    error_rate=error_rate,
                    peak_usage_time=peak_usage_time,
                    date_range={"start_date": start_time, "end_date": end_time}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get usage metrics: {e}")
            raise
    
    def get_user_engagement_metrics(
        self, 
        date_range: Optional[DateRange] = None
    ) -> Dict[str, Any]:
        """
        Get user engagement and activity metrics.
        
        Args:
            date_range: Date range for metrics (defaults to last 7 days)
            
        Returns:
            Dict containing user engagement metrics
        """
        try:
            with get_db_session() as session:
                # Default to last 7 days if no date range provided
                if date_range is None:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=7)
                else:
                    start_time = date_range.start_date
                    end_time = date_range.end_date
                
                # Active users in period
                active_users = session.query(func.count(func.distinct(QueryMetrics.user_id))).filter(
                    and_(
                        QueryMetrics.timestamp >= start_time,
                        QueryMetrics.timestamp <= end_time
                    )
                ).scalar() or 0
                
                # Total chat sessions in period
                total_sessions = session.query(func.count(ChatSession.id)).filter(
                    and_(
                        ChatSession.created_at >= start_time,
                        ChatSession.created_at <= end_time
                    )
                ).scalar() or 0
                
                # Total messages in period
                total_messages = session.query(func.count(Message.id)).join(ChatSession).filter(
                    and_(
                        Message.timestamp >= start_time,
                        Message.timestamp <= end_time
                    )
                ).scalar() or 0
                
                # Average session duration (for completed sessions)
                avg_session_duration = session.query(
                    func.avg(
                        func.extract('epoch', ChatSession.ended_at - ChatSession.created_at)
                    )
                ).filter(
                    and_(
                        ChatSession.created_at >= start_time,
                        ChatSession.created_at <= end_time,
                        ChatSession.ended_at.isnot(None)
                    )
                ).scalar() or 0.0
                
                # User activity by role
                user_activity_by_role = session.query(
                    User.role,
                    func.count(func.distinct(QueryMetrics.user_id))
                ).join(QueryMetrics).filter(
                    and_(
                        QueryMetrics.timestamp >= start_time,
                        QueryMetrics.timestamp <= end_time
                    )
                ).group_by(User.role).all()
                
                role_activity = {role: count for role, count in user_activity_by_role}
                
                return {
                    "active_users": active_users,
                    "total_sessions": total_sessions,
                    "total_messages": total_messages,
                    "avg_session_duration_seconds": float(avg_session_duration),
                    "user_activity_by_role": role_activity,
                    "date_range": {"start_date": start_time, "end_date": end_time}
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get user engagement metrics: {e}")
            raise
    
    def get_system_performance_metrics(
        self, 
        date_range: Optional[DateRange] = None
    ) -> Dict[str, Any]:
        """
        Get system performance and health metrics.
        
        Args:
            date_range: Date range for metrics (defaults to last hour)
            
        Returns:
            Dict containing system performance metrics
        """
        try:
            with get_db_session() as session:
                # Default to last hour if no date range provided
                if date_range is None:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)
                else:
                    start_time = date_range.start_date
                    end_time = date_range.end_date
                
                # Get latest system metrics by metric name
                latest_metrics = {}
                metric_names = session.query(func.distinct(SystemMetrics.metric_name)).filter(
                    and_(
                        SystemMetrics.timestamp >= start_time,
                        SystemMetrics.timestamp <= end_time
                    )
                ).all()
                
                for (metric_name,) in metric_names:
                    latest_metric = session.query(SystemMetrics).filter(
                        and_(
                            SystemMetrics.metric_name == metric_name,
                            SystemMetrics.timestamp >= start_time,
                            SystemMetrics.timestamp <= end_time
                        )
                    ).order_by(desc(SystemMetrics.timestamp)).first()
                    
                    if latest_metric:
                        latest_metrics[metric_name] = {
                            "value": latest_metric.metric_value,
                            "unit": latest_metric.metric_unit,
                            "timestamp": latest_metric.timestamp,
                            "tags": latest_metric.tags
                        }
                
                # Calculate query performance metrics
                query_performance = session.query(
                    func.avg(QueryMetrics.response_time).label('avg_response_time'),
                    func.min(QueryMetrics.response_time).label('min_response_time'),
                    func.max(QueryMetrics.response_time).label('max_response_time'),
                    func.count(QueryMetrics.id).label('total_queries')
                ).filter(
                    and_(
                        QueryMetrics.timestamp >= start_time,
                        QueryMetrics.timestamp <= end_time
                    )
                ).first()
                
                performance_stats = {
                    "avg_response_time": float(query_performance.avg_response_time or 0),
                    "min_response_time": float(query_performance.min_response_time or 0),
                    "max_response_time": float(query_performance.max_response_time or 0),
                    "total_queries": query_performance.total_queries or 0
                }
                
                return {
                    "system_metrics": latest_metrics,
                    "query_performance": performance_stats,
                    "date_range": {"start_date": start_time, "end_date": end_time}
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get system performance metrics: {e}")
            raise
    
    def get_recent_queries(
        self, 
        limit: int = 10,
        user_id: Optional[UUID] = None
    ) -> List[QueryMetricsResponse]:
        """
        Get recent query metrics.
        
        Args:
            limit: Maximum number of queries to return
            user_id: Optional user ID to filter queries
            
        Returns:
            List of recent query metrics
        """
        try:
            with get_db_session() as session:
                query = session.query(QueryMetrics)
                
                if user_id:
                    query = query.filter(QueryMetrics.user_id == user_id)
                
                recent_queries = query.order_by(
                    desc(QueryMetrics.timestamp)
                ).limit(limit).all()
                
                return [QueryMetricsResponse.from_orm(q) for q in recent_queries]
                
        except Exception as e:
            self.logger.error(f"Failed to get recent queries: {e}")
            raise
    
    def _find_peak_usage_time(
        self, 
        session: Session, 
        start_time: datetime, 
        end_time: datetime,
        user_id: Optional[UUID] = None
    ) -> Optional[datetime]:
        """
        Find the hour with the highest query volume.
        
        Args:
            session: Database session
            start_time: Start of date range
            end_time: End of date range
            user_id: Optional user ID filter
            
        Returns:
            Datetime of peak usage hour, or None if no data
        """
        try:
            # Group queries by hour and count
            query = session.query(
                func.date_trunc('hour', QueryMetrics.timestamp).label('hour'),
                func.count(QueryMetrics.id).label('query_count')
            ).filter(
                and_(
                    QueryMetrics.timestamp >= start_time,
                    QueryMetrics.timestamp <= end_time
                )
            )
            
            if user_id:
                query = query.filter(QueryMetrics.user_id == user_id)
            
            peak_hour = query.group_by(
                func.date_trunc('hour', QueryMetrics.timestamp)
            ).order_by(
                desc('query_count')
            ).first()
            
            return peak_hour.hour if peak_hour else None
            
        except Exception as e:
            self.logger.error(f"Failed to find peak usage time: {e}")
            return None
    
    def cleanup_old_metrics(self, days_to_keep: int = 90) -> int:
        """
        Clean up old metrics data to manage database size.
        
        Args:
            days_to_keep: Number of days of metrics to retain
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            with get_db_session() as session:
                # Delete old query metrics
                query_deleted = session.query(QueryMetrics).filter(
                    QueryMetrics.timestamp < cutoff_date
                ).delete()
                
                # Delete old system metrics
                system_deleted = session.query(SystemMetrics).filter(
                    SystemMetrics.timestamp < cutoff_date
                ).delete()
                
                total_deleted = query_deleted + system_deleted
                
                self.logger.info(
                    f"Cleaned up {total_deleted} old metrics records "
                    f"(query: {query_deleted}, system: {system_deleted})"
                )
                
                return total_deleted
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old metrics: {e}")
            raise