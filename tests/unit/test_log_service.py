"""
Unit tests for LogService
"""

import pytest
import json
import os
import tempfile
import gzip
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from services.log_service import LogService, SSHCredentials, LogStats
from core.exceptions import LogProcessingError, ValidationError, ServiceUnavailableError


class TestLogService:
    """Test cases for LogService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.log_service = LogService()
        self.sample_log = {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "Sample log entry for testing",
            "level": "info",
            "location": "test-server"
        }
    
    def test_validate_log_entry_valid(self):
        """Test validation of valid log entry."""
        assert self.log_service.validate_log_entry(self.sample_log) is True
    
    def test_validate_log_entry_missing_timestamp(self):
        """Test validation fails for missing timestamp."""
        invalid_log = self.sample_log.copy()
        del invalid_log["timestamp"]
        assert self.log_service.validate_log_entry(invalid_log) is False
    
    def test_validate_log_entry_missing_full_log(self):
        """Test validation fails for missing full_log."""
        invalid_log = self.sample_log.copy()
        del invalid_log["full_log"]
        assert self.log_service.validate_log_entry(invalid_log) is False
    
    def test_validate_log_entry_empty_full_log(self):
        """Test validation fails for empty full_log."""
        invalid_log = self.sample_log.copy()
        invalid_log["full_log"] = ""
        assert self.log_service.validate_log_entry(invalid_log) is False
    
    def test_validate_log_entry_invalid_timestamp(self):
        """Test validation fails for invalid timestamp."""
        invalid_log = self.sample_log.copy()
        invalid_log["timestamp"] = "invalid-timestamp"
        assert self.log_service.validate_log_entry(invalid_log) is False
    
    def test_validate_log_entry_not_dict(self):
        """Test validation fails for non-dictionary input."""
        assert self.log_service.validate_log_entry("not a dict") is False
        assert self.log_service.validate_log_entry(None) is False
    
    def test_clean_log_entry(self):
        """Test log entry cleaning."""
        dirty_log = {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "  Sample log with spaces  ",
            "empty_field": "",
            "null_field": None,
            "valid_field": "value"
        }
        
        cleaned = self.log_service.clean_log_entry(dirty_log)
        
        assert cleaned["full_log"] == "Sample log with spaces"
        assert "empty_field" not in cleaned
        assert "null_field" not in cleaned
        assert cleaned["valid_field"] == "value"
    
    def test_get_log_statistics(self):
        """Test log statistics generation."""
        logs = [
            {
                "timestamp": "2024-01-15T10:30:00",
                "full_log": "Log 1",
                "level": "info",
                "location": "server1"
            },
            {
                "timestamp": "2024-01-16T11:30:00",
                "full_log": "Log 2",
                "level": "warning",
                "location": "server1"
            },
            {
                "timestamp": "2024-01-17T12:30:00",
                "full_log": "Log 3",
                "level": "info",
                "location": "server2"
            }
        ]
        
        stats = self.log_service.get_log_statistics(logs)
        
        assert stats.total_logs == 3
        assert stats.sources["server1"] == 2
        assert stats.sources["server2"] == 1
        assert stats.levels["info"] == 2
        assert stats.levels["warning"] == 1
        assert "2024-01-15" in stats.date_range
        assert "2024-01-17" in stats.date_range
        assert stats.processing_time >= 0
    
    def test_load_logs_from_days_invalid_range(self):
        """Test validation of days parameter."""
        with pytest.raises(ValidationError):
            self.log_service.load_logs_from_days(0)
        
        with pytest.raises(ValidationError):
            self.log_service.load_logs_from_days(366)
    
    @patch('services.log_service.os.path.exists')
    @patch('services.log_service.os.path.getsize')
    @patch('builtins.open')
    def test_load_local_logs_success(self, mock_open, mock_getsize, mock_exists):
        """Test successful local log loading."""
        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        
        # Mock file content
        log_content = json.dumps(self.sample_log) + "\n"
        mock_file = MagicMock()
        mock_file.__enter__.return_value = [log_content]
        mock_open.return_value = mock_file
        
        logs = self.log_service.load_logs_from_days(1)
        
        assert len(logs) == 1
        assert logs[0]["timestamp"] == self.sample_log["timestamp"]
    
    @patch('services.log_service.paramiko.SSHClient')
    def test_load_remote_logs_success(self, mock_ssh_client):
        """Test successful remote log loading."""
        # Mock SSH connection
        mock_ssh = Mock()
        mock_sftp = Mock()
        mock_ssh_client.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock remote file
        mock_stat = Mock()
        mock_stat.st_size = 100
        mock_sftp.stat.return_value = mock_stat
        
        log_content = json.dumps(self.sample_log) + "\n"
        mock_file = Mock()
        mock_file.__iter__.return_value = iter([log_content])
        mock_sftp.open.return_value = mock_file
        
        ssh_creds = SSHCredentials("user", "pass", "host")
        logs = self.log_service.load_logs_from_days(1, ssh_creds)
        
        assert len(logs) == 1
        assert logs[0]["timestamp"] == self.sample_log["timestamp"]
    
    @patch('services.log_service.paramiko.SSHClient')
    def test_load_remote_logs_connection_failure(self, mock_ssh_client):
        """Test remote log loading with connection failure."""
        mock_ssh_client.side_effect = Exception("Connection failed")
        
        ssh_creds = SSHCredentials("user", "pass", "host")
        
        with pytest.raises(ServiceUnavailableError):
            self.log_service.load_logs_from_days(1, ssh_creds)
    
    def test_parse_log_file_with_temp_file(self):
        """Test log file parsing with actual temporary file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(json.dumps(self.sample_log) + "\n")
            f.write(json.dumps({
                "timestamp": "2024-01-16T10:30:00",
                "full_log": "Second log entry",
                "level": "warning"
            }) + "\n")
            f.write("invalid json line\n")  # This should be skipped
            temp_file_path = f.name
        
        try:
            logs = self.log_service._parse_log_file(temp_file_path, open)
            assert len(logs) == 2
            assert logs[0]["timestamp"] == self.sample_log["timestamp"]
            assert logs[1]["level"] == "warning"
        finally:
            os.unlink(temp_file_path)
    
    def test_parse_gzipped_log_file(self):
        """Test parsing of gzipped log file."""
        # Create temporary gzipped file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as f:
            temp_file_path = f.name
        
        try:
            with gzip.open(temp_file_path, 'wt', encoding='utf-8') as f:
                f.write(json.dumps(self.sample_log) + "\n")
            
            logs = self.log_service._parse_log_file(temp_file_path, gzip.open)
            assert len(logs) == 1
            assert logs[0]["timestamp"] == self.sample_log["timestamp"]
        finally:
            os.unlink(temp_file_path)
    
    def test_normalize_timestamp(self):
        """Test timestamp normalization."""
        # Test valid ISO timestamp
        iso_timestamp = "2024-01-15T10:30:00"
        normalized = self.log_service._normalize_timestamp(iso_timestamp)
        assert normalized == "2024-01-15T10:30:00"
        
        # Test invalid timestamp (should return original)
        invalid_timestamp = "invalid-timestamp"
        normalized = self.log_service._normalize_timestamp(invalid_timestamp)
        assert normalized == invalid_timestamp
    
    def test_ssh_credentials(self):
        """Test SSHCredentials class."""
        creds = SSHCredentials("user", "pass", "host", 2222)
        assert creds.username == "user"
        assert creds.password == "pass"
        assert creds.host == "host"
        assert creds.port == 2222
        
        # Test default port
        creds_default = SSHCredentials("user", "pass", "host")
        assert creds_default.port == 22
    
    def test_log_stats(self):
        """Test LogStats class."""
        sources = {"server1": 10, "server2": 5}
        levels = {"info": 12, "warning": 3}
        stats = LogStats(15, "2024-01-15 to 2024-01-17", sources, levels, 0.5)
        
        assert stats.total_logs == 15
        assert stats.date_range == "2024-01-15 to 2024-01-17"
        assert stats.sources == sources
        assert stats.levels == levels
        assert stats.processing_time == 0.5


if __name__ == "__main__":
    pytest.main([__file__])