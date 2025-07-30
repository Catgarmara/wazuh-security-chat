"""
Log Service Module

This module provides log processing functionality for the Wazuh AI Companion.
It handles loading, parsing, and validation of Wazuh log files from both local
and remote sources.
"""

import json
import os
import gzip
import re
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
import paramiko
from core.exceptions import LogProcessingError, ValidationError, ServiceUnavailableError
from core.config import get_settings
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class SSHCredentials:
    """SSH connection credentials for remote log access."""
    
    def __init__(self, username: str, password: str, host: str, port: int = 22):
        self.username = username
        self.password = password
        self.host = host
        self.port = port


class LogMetadata:
    """Container for extracted log metadata."""
    
    def __init__(self, log_id: str, timestamp: datetime, source: str, level: str,
                 rule_id: Optional[str] = None, agent_name: Optional[str] = None,
                 agent_ip: Optional[str] = None, decoder_name: Optional[str] = None,
                 location: Optional[str] = None, groups: Optional[List[str]] = None,
                 tags: Optional[List[str]] = None, severity: Optional[int] = None):
        self.log_id = log_id
        self.timestamp = timestamp
        self.source = source
        self.level = level
        self.rule_id = rule_id
        self.agent_name = agent_name
        self.agent_ip = agent_ip
        self.decoder_name = decoder_name
        self.location = location
        self.groups = groups or []
        self.tags = tags or []
        self.severity = severity


class LogStats:
    """Enhanced log statistics container."""
    
    def __init__(self, total_logs: int, date_range: str, sources: Dict[str, int], 
                 levels: Dict[str, int], processing_time: float,
                 agents: Optional[Dict[str, int]] = None,
                 rules: Optional[Dict[str, int]] = None,
                 decoders: Optional[Dict[str, int]] = None,
                 severity_distribution: Optional[Dict[int, int]] = None,
                 hourly_distribution: Optional[Dict[int, int]] = None):
        self.total_logs = total_logs
        self.date_range = date_range
        self.sources = sources
        self.levels = levels
        self.processing_time = processing_time
        self.agents = agents or {}
        self.rules = rules or {}
        self.decoders = decoders or {}
        self.severity_distribution = severity_distribution or {}
        self.hourly_distribution = hourly_distribution or {}


class LogFilter:
    """Log filtering criteria."""
    
    def __init__(self, start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 levels: Optional[List[str]] = None,
                 sources: Optional[List[str]] = None,
                 agents: Optional[List[str]] = None,
                 rule_ids: Optional[List[str]] = None,
                 search_text: Optional[str] = None,
                 severity_min: Optional[int] = None,
                 severity_max: Optional[int] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.levels = levels or []
        self.sources = sources or []
        self.agents = agents or []
        self.rule_ids = rule_ids or []
        self.search_text = search_text
        self.severity_min = severity_min
        self.severity_max = severity_max


class LogReloadStatus:
    """Status information for log reload operations."""
    
    def __init__(self, status: str, message: str, progress: float = 0.0,
                 logs_processed: int = 0, total_logs: int = 0,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 error: Optional[str] = None):
        self.status = status  # 'pending', 'running', 'completed', 'failed'
        self.message = message
        self.progress = progress  # 0.0 to 1.0
        self.logs_processed = logs_processed
        self.total_logs = total_logs
        self.start_time = start_time or datetime.now()
        self.end_time = end_time
        self.error = error
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get operation duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class LogHealthStatus:
    """Health status information for log processing system."""
    
    def __init__(self, status: str, last_reload: Optional[datetime] = None,
                 total_logs_cached: int = 0, cache_size_mb: float = 0.0,
                 avg_processing_time: float = 0.0, error_rate: float = 0.0,
                 disk_usage_mb: float = 0.0, memory_usage_mb: float = 0.0):
        self.status = status  # 'healthy', 'warning', 'critical'
        self.last_reload = last_reload
        self.total_logs_cached = total_logs_cached
        self.cache_size_mb = cache_size_mb
        self.avg_processing_time = avg_processing_time
        self.error_rate = error_rate
        self.disk_usage_mb = disk_usage_mb
        self.memory_usage_mb = memory_usage_mb


class LogService:
    """
    Service for handling Wazuh log processing operations.
    
    This service provides functionality to:
    - Load logs from local and remote sources
    - Parse and validate log entries
    - Extract metadata and statistics
    - Handle SSH connections for remote log access
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.log_base_path = "/var/ossec/logs/archives"
        
    def load_logs_from_days(self, past_days: int = 7, 
                           ssh_credentials: Optional[SSHCredentials] = None) -> List[Dict[str, Any]]:
        """
        Load logs from the specified number of past days.
        
        Args:
            past_days: Number of days to load logs from (1-365)
            ssh_credentials: Optional SSH credentials for remote log access
            
        Returns:
            List of parsed log entries
            
        Raises:
            LogProcessingError: If log loading fails
            ValidationError: If parameters are invalid
        """
        if not 1 <= past_days <= 365:
            raise ValidationError("past_days must be between 1 and 365")
            
        try:
            if ssh_credentials:
                return self._load_remote_logs(ssh_credentials, past_days)
            else:
                return self._load_local_logs(past_days)
        except Exception as e:
            logger.error(f"Failed to load logs from {past_days} days: {e}")
            raise LogProcessingError(f"Log loading failed: {str(e)}")
    
    def _load_local_logs(self, past_days: int) -> List[Dict[str, Any]]:
        """Load logs from local filesystem."""
        logs = []
        today = datetime.now()
        
        for i in range(past_days):
            day = today - timedelta(days=i)
            file_paths = self._get_log_file_paths(day)
            
            for file_path, open_func in file_paths:
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    logger.warning(f"Log file missing or empty: {file_path}")
                    continue
                    
                try:
                    parsed_logs = self._parse_log_file(file_path, open_func)
                    logs.extend(parsed_logs)
                    logger.info(f"Loaded {len(parsed_logs)} logs from {file_path}")
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    continue
                    
        return logs
    
    def _load_remote_logs(self, ssh_credentials: SSHCredentials, 
                         past_days: int) -> List[Dict[str, Any]]:
        """Load logs from remote server via SSH."""
        logs = []
        today = datetime.now()
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                ssh_credentials.host,
                username=ssh_credentials.username,
                password=ssh_credentials.password,
                port=ssh_credentials.port,
                timeout=10
            )
            sftp = ssh.open_sftp()
            
            for i in range(past_days):
                day = today - timedelta(days=i)
                remote_logs = self._load_remote_day_logs(sftp, day)
                logs.extend(remote_logs)
                
            sftp.close()
            ssh.close()
            
        except Exception as e:
            logger.error(f"Remote connection failed: {e}")
            raise ServiceUnavailableError(f"Remote log access failed: {str(e)}")
            
        return logs
    
    def _load_remote_day_logs(self, sftp, day: datetime) -> List[Dict[str, Any]]:
        """Load logs for a specific day from remote server."""
        logs = []
        year = day.year
        month_name = day.strftime("%b")
        day_num = day.strftime("%d")
        
        base_path = f"{self.log_base_path}/{year}/{month_name}"
        json_path = f"{base_path}/ossec-archive-{day_num}.json"
        gz_path = f"{base_path}/ossec-archive-{day_num}.json.gz"
        
        remote_file = None
        try:
            # Try JSON file first
            if sftp.stat(json_path).st_size > 0:
                remote_file = sftp.open(json_path, 'r')
                logs = self._parse_remote_file(remote_file, is_gzipped=False)
            elif sftp.stat(gz_path).st_size > 0:
                remote_file = gzip.GzipFile(fileobj=sftp.open(gz_path, 'rb'))
                logs = self._parse_remote_file(remote_file, is_gzipped=True)
        except IOError:
            logger.warning(f"Remote log not found: {json_path} / {gz_path}")
        except Exception as e:
            logger.error(f"Error reading remote file: {e}")
        finally:
            if remote_file:
                remote_file.close()
                
        return logs
    
    def _parse_remote_file(self, remote_file, is_gzipped: bool) -> List[Dict[str, Any]]:
        """Parse a remote log file."""
        logs = []
        try:
            for line in remote_file:
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='ignore')
                if line.strip():
                    try:
                        log = json.loads(line.strip())
                        if self.validate_log_entry(log):
                            logs.append(log)
                    except json.JSONDecodeError:
                        logger.warning("Skipping invalid JSON line from remote file")
        except Exception as e:
            logger.error(f"Error parsing remote file: {e}")
            
        return logs
    
    def _get_log_file_paths(self, day: datetime) -> List[Tuple[str, callable]]:
        """Get possible log file paths for a given day."""
        year = day.year
        month_name = day.strftime("%b")
        day_num = day.strftime("%d")
        
        json_path = f"{self.log_base_path}/{year}/{month_name}/ossec-archive-{day_num}.json"
        gz_path = f"{self.log_base_path}/{year}/{month_name}/ossec-archive-{day_num}.json.gz"
        
        return [
            (json_path, open),
            (gz_path, gzip.open)
        ]
    
    def _parse_log_file(self, file_path: str, open_func: callable) -> List[Dict[str, Any]]:
        """Parse a single log file."""
        logs = []
        
        try:
            with open_func(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            log = json.loads(line.strip())
                            if self.validate_log_entry(log):
                                logs.append(log)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON at line {line_num} in {file_path}")
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise LogProcessingError(f"Failed to parse log file: {str(e)}")
            
        return logs
    
    def validate_log_entry(self, log: Dict[str, Any]) -> bool:
        """
        Validate a log entry for required fields and data integrity.
        
        Args:
            log: Log entry dictionary
            
        Returns:
            True if log entry is valid, False otherwise
        """
        if not isinstance(log, dict):
            return False
            
        # Check for required fields
        required_fields = ['timestamp', 'full_log']
        for field in required_fields:
            if field not in log:
                logger.debug(f"Log entry missing required field: {field}")
                return False
                
        # Validate timestamp format
        timestamp = log.get('timestamp', '')
        if not self._validate_timestamp(timestamp):
            logger.debug(f"Invalid timestamp format: {timestamp}")
            return False
            
        # Validate full_log is not empty
        if not log.get('full_log', '').strip():
            logger.debug("Log entry has empty full_log field")
            return False
            
        return True
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        """Validate timestamp format."""
        if not timestamp:
            return False
            
        try:
            # Try to parse common timestamp formats
            datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
            return True
        except ValueError:
            try:
                datetime.strptime(timestamp[:10], "%Y-%m-%d")
                return True
            except ValueError:
                return False
    
    def clean_log_entry(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize a log entry.
        
        Args:
            log: Raw log entry
            
        Returns:
            Cleaned log entry
        """
        cleaned_log = log.copy()
        
        # Normalize timestamp
        if 'timestamp' in cleaned_log:
            cleaned_log['timestamp'] = self._normalize_timestamp(cleaned_log['timestamp'])
            
        # Clean full_log field
        if 'full_log' in cleaned_log:
            cleaned_log['full_log'] = cleaned_log['full_log'].strip()
            
        # Remove null or empty fields
        cleaned_log = {k: v for k, v in cleaned_log.items() 
                      if v is not None and str(v).strip()}
        
        return cleaned_log
    
    def _normalize_timestamp(self, timestamp: str) -> str:
        """Normalize timestamp to ISO format."""
        try:
            # Parse and reformat to ISO format
            dt = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
            return dt.isoformat()
        except ValueError:
            # Return original if parsing fails
            return timestamp
    
    def get_log_statistics(self, logs: List[Dict[str, Any]]) -> LogStats:
        """
        Generate statistics for a collection of logs.
        
        Args:
            logs: List of log entries
            
        Returns:
            LogStats object with statistics
        """
        start_time = datetime.now()
        
        total_logs = len(logs)
        sources = {}
        levels = {}
        dates = []
        
        for log in logs:
            # Count sources
            source = log.get('location', 'unknown')
            sources[source] = sources.get(source, 0) + 1
            
            # Count levels
            level = log.get('level', 'unknown')
            levels[level] = levels.get(level, 0) + 1
            
            # Collect dates
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    date = datetime.strptime(timestamp[:10], "%Y-%m-%d")
                    dates.append(date)
                except ValueError:
                    pass
        
        # Calculate date range
        date_range = ""
        if dates:
            earliest = min(dates).strftime("%Y-%m-%d")
            latest = max(dates).strftime("%Y-%m-%d")
            date_range = f"from {earliest} to {latest}"
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Enhanced statistics with metadata
        agents = {}
        rules = {}
        decoders = {}
        severity_distribution = {}
        hourly_distribution = defaultdict(int)
        
        for log in logs:
            # Count agents
            agent_name = log.get('agent', {}).get('name', 'unknown') if isinstance(log.get('agent'), dict) else 'unknown'
            agents[agent_name] = agents.get(agent_name, 0) + 1
            
            # Count rules
            rule_id = log.get('rule', {}).get('id', 'unknown') if isinstance(log.get('rule'), dict) else 'unknown'
            rules[rule_id] = rules.get(rule_id, 0) + 1
            
            # Count decoders
            decoder_name = log.get('decoder', {}).get('name', 'unknown') if isinstance(log.get('decoder'), dict) else 'unknown'
            decoders[decoder_name] = decoders.get(decoder_name, 0) + 1
            
            # Count severity levels
            rule_level = log.get('rule', {}).get('level', 0) if isinstance(log.get('rule'), dict) else 0
            if isinstance(rule_level, int):
                severity_distribution[rule_level] = severity_distribution.get(rule_level, 0) + 1
            
            # Count hourly distribution
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
                    hourly_distribution[dt.hour] += 1
                except ValueError:
                    pass
        
        return LogStats(
            total_logs=total_logs,
            date_range=date_range,
            sources=sources,
            levels=levels,
            processing_time=processing_time,
            agents=agents,
            rules=rules,
            decoders=decoders,
            severity_distribution=severity_distribution,
            hourly_distribution=dict(hourly_distribution)
        )
    
    def extract_log_metadata(self, log: Dict[str, Any]) -> LogMetadata:
        """
        Extract metadata from a log entry.
        
        Args:
            log: Raw log entry dictionary
            
        Returns:
            LogMetadata object with extracted information
        """
        # Generate log ID (could be improved with actual UUID)
        log_id = f"{log.get('timestamp', '')}-{hash(str(log))}"
        
        # Parse timestamp
        timestamp_str = log.get('timestamp', '')
        try:
            timestamp = datetime.strptime(timestamp_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            timestamp = datetime.now()
        
        # Extract basic fields
        source = log.get('location', 'unknown')
        level = log.get('level', 'unknown')
        
        # Extract rule information
        rule_info = log.get('rule', {})
        rule_id = rule_info.get('id') if isinstance(rule_info, dict) else None
        severity = rule_info.get('level') if isinstance(rule_info, dict) else None
        groups = rule_info.get('groups', []) if isinstance(rule_info, dict) else []
        
        # Extract agent information
        agent_info = log.get('agent', {})
        agent_name = agent_info.get('name') if isinstance(agent_info, dict) else None
        agent_ip = agent_info.get('ip') if isinstance(agent_info, dict) else None
        
        # Extract decoder information
        decoder_info = log.get('decoder', {})
        decoder_name = decoder_info.get('name') if isinstance(decoder_info, dict) else None
        
        # Extract location
        location = log.get('location', source)
        
        # Extract or generate tags
        tags = self._extract_tags_from_log(log)
        
        return LogMetadata(
            log_id=log_id,
            timestamp=timestamp,
            source=source,
            level=level,
            rule_id=rule_id,
            agent_name=agent_name,
            agent_ip=agent_ip,
            decoder_name=decoder_name,
            location=location,
            groups=groups,
            tags=tags,
            severity=severity
        )
    
    def _extract_tags_from_log(self, log: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from log content."""
        tags = set()
        
        # Add rule groups as tags
        rule_groups = log.get('rule', {}).get('groups', [])
        if isinstance(rule_groups, list):
            tags.update(rule_groups)
        
        # Extract tags from full_log content using patterns
        full_log = log.get('full_log', '')
        if full_log:
            # Common security-related patterns
            patterns = {
                'authentication': r'(?i)(login|auth|password|credential)',
                'network': r'(?i)(connection|network|tcp|udp|port)',
                'file_system': r'(?i)(file|directory|path|write|read)',
                'process': r'(?i)(process|pid|exec|command)',
                'error': r'(?i)(error|fail|exception|denied)',
                'warning': r'(?i)(warning|warn|alert)',
                'security': r'(?i)(security|threat|attack|malware|virus)',
                'system': r'(?i)(system|kernel|service|daemon)'
            }
            
            for tag, pattern in patterns.items():
                if re.search(pattern, full_log):
                    tags.add(tag)
        
        return list(tags)
    
    def filter_logs(self, logs: List[Dict[str, Any]], 
                   log_filter: LogFilter) -> List[Dict[str, Any]]:
        """
        Filter logs based on specified criteria.
        
        Args:
            logs: List of log entries to filter
            log_filter: Filter criteria
            
        Returns:
            Filtered list of log entries
        """
        filtered_logs = []
        
        for log in logs:
            if not self._matches_filter(log, log_filter):
                continue
            filtered_logs.append(log)
        
        return filtered_logs
    
    def _matches_filter(self, log: Dict[str, Any], log_filter: LogFilter) -> bool:
        """Check if a log entry matches the filter criteria."""
        
        # Date range filter
        if log_filter.start_date or log_filter.end_date:
            timestamp_str = log.get('timestamp', '')
            try:
                log_timestamp = datetime.strptime(timestamp_str[:19], "%Y-%m-%dT%H:%M:%S")
                if log_filter.start_date and log_timestamp < log_filter.start_date:
                    return False
                if log_filter.end_date and log_timestamp > log_filter.end_date:
                    return False
            except ValueError:
                return False
        
        # Level filter
        if log_filter.levels:
            log_level = log.get('level', '')
            if log_level not in log_filter.levels:
                return False
        
        # Source filter
        if log_filter.sources:
            log_source = log.get('location', '')
            if log_source not in log_filter.sources:
                return False
        
        # Agent filter
        if log_filter.agents:
            agent_name = log.get('agent', {}).get('name', '') if isinstance(log.get('agent'), dict) else ''
            if agent_name not in log_filter.agents:
                return False
        
        # Rule ID filter
        if log_filter.rule_ids:
            rule_id = log.get('rule', {}).get('id', '') if isinstance(log.get('rule'), dict) else ''
            if rule_id not in log_filter.rule_ids:
                return False
        
        # Severity filter
        if log_filter.severity_min is not None or log_filter.severity_max is not None:
            rule_level = log.get('rule', {}).get('level', 0) if isinstance(log.get('rule'), dict) else 0
            if isinstance(rule_level, int):
                if log_filter.severity_min is not None and rule_level < log_filter.severity_min:
                    return False
                if log_filter.severity_max is not None and rule_level > log_filter.severity_max:
                    return False
        
        # Text search filter
        if log_filter.search_text:
            full_log = log.get('full_log', '').lower()
            search_text = log_filter.search_text.lower()
            if search_text not in full_log:
                return False
        
        return True
    
    def search_logs(self, logs: List[Dict[str, Any]], 
                   query: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search logs using text query across specified fields.
        
        Args:
            logs: List of log entries to search
            query: Search query string
            fields: List of fields to search in (default: ['full_log'])
            
        Returns:
            List of matching log entries
        """
        if not query.strip():
            return logs
        
        if fields is None:
            fields = ['full_log']
        
        query_lower = query.lower()
        matching_logs = []
        
        for log in logs:
            match_found = False
            for field in fields:
                field_value = str(log.get(field, '')).lower()
                if query_lower in field_value:
                    match_found = True
                    break
            
            if match_found:
                matching_logs.append(log)
        
        return matching_logs
    
    def get_unique_values(self, logs: List[Dict[str, Any]], 
                         field_path: str) -> Set[str]:
        """
        Get unique values for a specific field path in logs.
        
        Args:
            logs: List of log entries
            field_path: Dot-separated field path (e.g., 'agent.name', 'rule.id')
            
        Returns:
            Set of unique values
        """
        unique_values = set()
        
        for log in logs:
            value = self._get_nested_field(log, field_path)
            if value is not None:
                unique_values.add(str(value))
        
        return unique_values
    
    def _get_nested_field(self, log: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested field path."""
        fields = field_path.split('.')
        current = log
        
        for field in fields:
            if isinstance(current, dict) and field in current:
                current = current[field]
            else:
                return None
        
        return current
    
    def cache_log_metadata(self, logs: List[Dict[str, Any]]) -> Dict[str, LogMetadata]:
        """
        Extract and cache metadata for a list of logs.
        
        Args:
            logs: List of log entries
            
        Returns:
            Dictionary mapping log IDs to metadata
        """
        metadata_cache = {}
        
        for log in logs:
            try:
                metadata = self.extract_log_metadata(log)
                metadata_cache[metadata.log_id] = metadata
            except Exception as e:
                logger.warning(f"Failed to extract metadata from log: {e}")
                continue
        
        logger.info(f"Cached metadata for {len(metadata_cache)} logs")
        return metadata_cache
    
    def reload_logs_with_date_range(self, start_date: datetime, end_date: datetime,
                                   ssh_credentials: Optional[SSHCredentials] = None,
                                   progress_callback: Optional[Callable[[LogReloadStatus], None]] = None) -> LogReloadStatus:
        """
        Reload logs within a specific date range.
        
        Args:
            start_date: Start date for log loading
            end_date: End date for log loading
            ssh_credentials: Optional SSH credentials for remote access
            progress_callback: Optional callback for progress updates
            
        Returns:
            LogReloadStatus with operation results
        """
        status = LogReloadStatus("running", "Starting log reload...")
        
        if progress_callback:
            progress_callback(status)
        
        try:
            # Calculate days between dates
            days_diff = (end_date - start_date).days + 1
            if days_diff <= 0:
                raise ValidationError("End date must be after start date")
            if days_diff > 365:
                raise ValidationError("Date range cannot exceed 365 days")
            
            status.message = f"Loading logs for {days_diff} days..."
            status.progress = 0.1
            if progress_callback:
                progress_callback(status)
            
            # Load logs
            logs = self.load_logs_from_days(days_diff, ssh_credentials)
            
            status.message = "Filtering logs by date range..."
            status.progress = 0.5
            if progress_callback:
                progress_callback(status)
            
            # Filter logs by exact date range
            date_filter = LogFilter(start_date=start_date, end_date=end_date)
            filtered_logs = self.filter_logs(logs, date_filter)
            
            status.message = "Processing log metadata..."
            status.progress = 0.8
            if progress_callback:
                progress_callback(status)
            
            # Cache metadata
            metadata_cache = self.cache_log_metadata(filtered_logs)
            
            # Complete status
            status.status = "completed"
            status.message = f"Successfully loaded {len(filtered_logs)} logs"
            status.progress = 1.0
            status.logs_processed = len(filtered_logs)
            status.total_logs = len(logs)
            status.end_time = datetime.now()
            
            if progress_callback:
                progress_callback(status)
            
            return status
            
        except Exception as e:
            status.status = "failed"
            status.message = f"Log reload failed: {str(e)}"
            status.error = str(e)
            status.end_time = datetime.now()
            
            if progress_callback:
                progress_callback(status)
            
            logger.error(f"Log reload failed: {e}")
            return status
    
    def reload_logs_background(self, days: int = 7,
                              ssh_credentials: Optional[SSHCredentials] = None,
                              progress_callback: Optional[Callable[[LogReloadStatus], None]] = None) -> threading.Thread:
        """
        Start background log reload operation.
        
        Args:
            days: Number of days to load
            ssh_credentials: Optional SSH credentials
            progress_callback: Optional progress callback
            
        Returns:
            Thread object for the background operation
        """
        def reload_worker():
            status = LogReloadStatus("running", f"Background reload started for {days} days...")
            
            if progress_callback:
                progress_callback(status)
            
            try:
                logs = self.load_logs_from_days(days, ssh_credentials)
                
                status.message = "Processing logs in background..."
                status.progress = 0.5
                if progress_callback:
                    progress_callback(status)
                
                metadata_cache = self.cache_log_metadata(logs)
                
                status.status = "completed"
                status.message = f"Background reload completed: {len(logs)} logs processed"
                status.progress = 1.0
                status.logs_processed = len(logs)
                status.end_time = datetime.now()
                
                if progress_callback:
                    progress_callback(status)
                
            except Exception as e:
                status.status = "failed"
                status.message = f"Background reload failed: {str(e)}"
                status.error = str(e)
                status.end_time = datetime.now()
                
                if progress_callback:
                    progress_callback(status)
                
                logger.error(f"Background reload failed: {e}")
        
        thread = threading.Thread(target=reload_worker, daemon=True)
        thread.start()
        return thread
    
    def get_health_status(self, logs: Optional[List[Dict[str, Any]]] = None) -> LogHealthStatus:
        """
        Get health status of the log processing system.
        
        Args:
            logs: Optional current logs for analysis
            
        Returns:
            LogHealthStatus with system health information
        """
        try:
            # Basic health metrics
            total_logs = len(logs) if logs else 0
            
            # Estimate cache size (rough calculation)
            cache_size_mb = total_logs * 0.001  # Rough estimate: 1KB per log
            
            # Check disk usage for log directory
            disk_usage_mb = self._get_disk_usage_mb()
            
            # Get memory usage (simplified)
            memory_usage_mb = self._get_memory_usage_mb()
            
            # Determine overall health status
            status = "healthy"
            if disk_usage_mb > 1000:  # > 1GB
                status = "warning"
            if disk_usage_mb > 5000:  # > 5GB
                status = "critical"
            
            return LogHealthStatus(
                status=status,
                last_reload=datetime.now(),  # Would be tracked in real implementation
                total_logs_cached=total_logs,
                cache_size_mb=cache_size_mb,
                avg_processing_time=0.5,  # Would be calculated from metrics
                error_rate=0.0,  # Would be calculated from error tracking
                disk_usage_mb=disk_usage_mb,
                memory_usage_mb=memory_usage_mb
            )
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return LogHealthStatus(
                status="critical",
                error_rate=1.0
            )
    
    def _get_disk_usage_mb(self) -> float:
        """Get disk usage for log directory in MB."""
        try:
            if os.path.exists(self.log_base_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.log_base_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except OSError:
                            continue
                return total_size / (1024 * 1024)  # Convert to MB
            return 0.0
        except Exception:
            return 0.0
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB (simplified)."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # psutil not available, return estimate
            return 50.0  # Rough estimate
        except Exception:
            return 0.0
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """
        Clean up old log files to free disk space.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            Dictionary with cleanup results
        """
        if days_to_keep < 1:
            raise ValidationError("days_to_keep must be at least 1")
        
        cleanup_results = {
            "files_removed": 0,
            "space_freed_mb": 0.0,
            "errors": []
        }
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            if not os.path.exists(self.log_base_path):
                return cleanup_results
            
            for year_dir in os.listdir(self.log_base_path):
                year_path = os.path.join(self.log_base_path, year_dir)
                if not os.path.isdir(year_path):
                    continue
                
                try:
                    year = int(year_dir)
                except ValueError:
                    continue
                
                for month_dir in os.listdir(year_path):
                    month_path = os.path.join(year_path, month_dir)
                    if not os.path.isdir(month_path):
                        continue
                    
                    # Check if this month/year is before cutoff
                    try:
                        month_date = datetime.strptime(f"{year}-{month_dir}-01", "%Y-%b-%d")
                        if month_date >= cutoff_date:
                            continue
                    except ValueError:
                        continue
                    
                    # Remove old files in this month
                    for filename in os.listdir(month_path):
                        file_path = os.path.join(month_path, filename)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleanup_results["files_removed"] += 1
                            cleanup_results["space_freed_mb"] += file_size / (1024 * 1024)
                        except Exception as e:
                            cleanup_results["errors"].append(f"Failed to remove {file_path}: {str(e)}")
            
            logger.info(f"Cleanup completed: {cleanup_results['files_removed']} files removed, "
                       f"{cleanup_results['space_freed_mb']:.2f} MB freed")
            
        except Exception as e:
            cleanup_results["errors"].append(f"Cleanup failed: {str(e)}")
            logger.error(f"Log cleanup failed: {e}")
        
        return cleanup_results
    
    def get_log_statistics_summary(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get a comprehensive summary of log statistics for management endpoints.
        
        Args:
            logs: List of log entries
            
        Returns:
            Dictionary with comprehensive statistics
        """
        stats = self.get_log_statistics(logs)
        
        # Calculate additional metrics
        total_agents = len(stats.agents)
        total_rules = len(stats.rules)
        total_decoders = len(stats.decoders)
        
        # Find top items
        top_agents = sorted(stats.agents.items(), key=lambda x: x[1], reverse=True)[:5]
        top_rules = sorted(stats.rules.items(), key=lambda x: x[1], reverse=True)[:5]
        top_sources = sorted(stats.sources.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate severity distribution percentages
        severity_percentages = {}
        if stats.total_logs > 0:
            for severity, count in stats.severity_distribution.items():
                severity_percentages[severity] = (count / stats.total_logs) * 100
        
        return {
            "overview": {
                "total_logs": stats.total_logs,
                "date_range": stats.date_range,
                "processing_time": stats.processing_time,
                "total_agents": total_agents,
                "total_rules": total_rules,
                "total_decoders": total_decoders
            },
            "top_items": {
                "agents": top_agents,
                "rules": top_rules,
                "sources": top_sources
            },
            "distributions": {
                "levels": stats.levels,
                "severity": stats.severity_distribution,
                "severity_percentages": severity_percentages,
                "hourly": stats.hourly_distribution
            },
            "health": {
                "error_rate": 0.0,  # Would be calculated from actual error tracking
                "avg_processing_time": stats.processing_time,
                "cache_hit_rate": 0.95  # Would be calculated from cache metrics
            }
        }
    
    def validate_log_integrity(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate the integrity of loaded logs.
        
        Args:
            logs: List of log entries to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "total_logs": len(logs),
            "valid_logs": 0,
            "invalid_logs": 0,
            "validation_errors": [],
            "warnings": []
        }
        
        for i, log in enumerate(logs):
            try:
                if self.validate_log_entry(log):
                    validation_results["valid_logs"] += 1
                else:
                    validation_results["invalid_logs"] += 1
                    validation_results["validation_errors"].append(f"Log {i}: Invalid log entry")
            except Exception as e:
                validation_results["invalid_logs"] += 1
                validation_results["validation_errors"].append(f"Log {i}: {str(e)}")
        
        # Add warnings for common issues
        if validation_results["invalid_logs"] > 0:
            error_rate = validation_results["invalid_logs"] / validation_results["total_logs"]
            if error_rate > 0.1:  # More than 10% invalid
                validation_results["warnings"].append(f"High error rate: {error_rate:.1%} of logs are invalid")
        
        if validation_results["total_logs"] == 0:
            validation_results["warnings"].append("No logs found - check log sources and date range")
        
        return validation_results