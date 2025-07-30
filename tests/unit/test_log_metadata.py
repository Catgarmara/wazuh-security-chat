"""
Test script for LogService metadata extraction functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Mock the dependencies
class MockSettings:
    pass

class MockLogProcessingError(Exception):
    pass

class MockValidationError(Exception):
    pass

class MockServiceUnavailableError(Exception):
    pass

# Mock the core modules
def mock_get_settings():
    return MockSettings()

class MockConfigModule:
    def get_settings(self):
        return MockSettings()

class MockExceptionsModule:
    LogProcessingError = MockLogProcessingError
    ValidationError = MockValidationError
    ServiceUnavailableError = MockServiceUnavailableError

sys.modules['core.config'] = MockConfigModule()
sys.modules['core.exceptions'] = MockExceptionsModule()
sys.modules['paramiko'] = type('MockModule', (), {})()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the file
import importlib.util
spec = importlib.util.spec_from_file_location("log_service", "services/log_service.py")
log_service_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log_service_module)

LogService = log_service_module.LogService
LogMetadata = log_service_module.LogMetadata
LogFilter = log_service_module.LogFilter


def test_metadata_extraction():
    """Test log metadata extraction."""
    print("🧪 Testing metadata extraction...")
    
    log_service = LogService()
    
    # Sample Wazuh log entry
    sample_log = {
        "timestamp": "2024-01-15T10:30:00.123Z",
        "full_log": "Jan 15 10:30:00 server1 sshd[1234]: Failed password for user admin from 192.168.1.100 port 22 ssh2",
        "level": "warning",
        "location": "/var/log/auth.log",
        "rule": {
            "id": "5716",
            "level": 5,
            "description": "SSHD authentication failed",
            "groups": ["authentication_failed", "sshd"]
        },
        "agent": {
            "name": "server1",
            "ip": "192.168.1.10"
        },
        "decoder": {
            "name": "sshd"
        }
    }
    
    metadata = log_service.extract_log_metadata(sample_log)
    
    assert metadata.source == "/var/log/auth.log", "Source should match location"
    assert metadata.level == "warning", "Level should match"
    assert metadata.rule_id == "5716", "Rule ID should be extracted"
    assert metadata.agent_name == "server1", "Agent name should be extracted"
    assert metadata.agent_ip == "192.168.1.10", "Agent IP should be extracted"
    assert metadata.decoder_name == "sshd", "Decoder name should be extracted"
    assert metadata.severity == 5, "Severity should be extracted from rule level"
    assert "authentication_failed" in metadata.groups, "Rule groups should be included"
    assert "authentication" in metadata.tags, "Authentication tag should be detected"
    
    print("✅ Metadata extraction passed")


def test_enhanced_statistics():
    """Test enhanced statistics with metadata."""
    print("\n🧪 Testing enhanced statistics...")
    
    log_service = LogService()
    
    logs = [
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "SSH login attempt",
            "level": "info",
            "location": "server1",
            "agent": {"name": "web-server-01"},
            "rule": {"id": "5501", "level": 3},
            "decoder": {"name": "sshd"}
        },
        {
            "timestamp": "2024-01-15T14:30:00",
            "full_log": "Failed authentication",
            "level": "warning",
            "location": "server1",
            "agent": {"name": "web-server-01"},
            "rule": {"id": "5716", "level": 5},
            "decoder": {"name": "sshd"}
        },
        {
            "timestamp": "2024-01-16T09:15:00",
            "full_log": "File access denied",
            "level": "error",
            "location": "server2",
            "agent": {"name": "db-server-01"},
            "rule": {"id": "2501", "level": 7},
            "decoder": {"name": "kernel"}
        }
    ]
    
    stats = log_service.get_log_statistics(logs)
    
    assert stats.total_logs == 3, "Should count all logs"
    assert stats.agents["web-server-01"] == 2, "Should count agent logs"
    assert stats.agents["db-server-01"] == 1, "Should count agent logs"
    assert stats.rules["5716"] == 1, "Should count rule occurrences"
    assert stats.decoders["sshd"] == 2, "Should count decoder occurrences"
    assert stats.severity_distribution[5] == 1, "Should count severity levels"
    assert stats.hourly_distribution[10] == 1, "Should count hourly distribution"
    assert stats.hourly_distribution[14] == 1, "Should count hourly distribution"
    
    print("✅ Enhanced statistics passed")


def test_log_filtering():
    """Test log filtering functionality."""
    print("\n🧪 Testing log filtering...")
    
    log_service = LogService()
    
    logs = [
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "SSH login successful",
            "level": "info",
            "location": "server1",
            "agent": {"name": "web-server-01"},
            "rule": {"id": "5501", "level": 3}
        },
        {
            "timestamp": "2024-01-15T14:30:00",
            "full_log": "Failed authentication attempt",
            "level": "warning",
            "location": "server1",
            "agent": {"name": "web-server-01"},
            "rule": {"id": "5716", "level": 5}
        },
        {
            "timestamp": "2024-01-16T09:15:00",
            "full_log": "System error occurred",
            "level": "error",
            "location": "server2",
            "agent": {"name": "db-server-01"},
            "rule": {"id": "2501", "level": 7}
        }
    ]
    
    # Test level filtering
    level_filter = LogFilter(levels=["warning", "error"])
    filtered = log_service.filter_logs(logs, level_filter)
    assert len(filtered) == 2, "Should filter by level"
    
    # Test agent filtering
    agent_filter = LogFilter(agents=["web-server-01"])
    filtered = log_service.filter_logs(logs, agent_filter)
    assert len(filtered) == 2, "Should filter by agent"
    
    # Test severity filtering
    severity_filter = LogFilter(severity_min=5)
    filtered = log_service.filter_logs(logs, severity_filter)
    assert len(filtered) == 2, "Should filter by minimum severity"
    
    # Test text search filtering
    text_filter = LogFilter(search_text="authentication")
    filtered = log_service.filter_logs(logs, text_filter)
    assert len(filtered) == 1, "Should filter by text search"
    
    # Test date range filtering
    start_date = datetime(2024, 1, 16, 0, 0, 0)
    date_filter = LogFilter(start_date=start_date)
    filtered = log_service.filter_logs(logs, date_filter)
    assert len(filtered) == 1, "Should filter by date range"
    
    print("✅ Log filtering passed")


def test_log_search():
    """Test log search functionality."""
    print("\n🧪 Testing log search...")
    
    log_service = LogService()
    
    logs = [
        {
            "full_log": "SSH login successful for user admin",
            "level": "info",
            "location": "server1"
        },
        {
            "full_log": "Failed authentication attempt",
            "level": "warning",
            "location": "server1"
        },
        {
            "full_log": "System error in database connection",
            "level": "error",
            "location": "server2"
        }
    ]
    
    # Test basic search
    results = log_service.search_logs(logs, "authentication")
    assert len(results) == 1, "Should find authentication logs"
    
    # Test case-insensitive search
    results = log_service.search_logs(logs, "SSH")
    assert len(results) == 1, "Should find SSH logs (case insensitive)"
    
    # Test multi-field search
    results = log_service.search_logs(logs, "server1", ["location"])
    assert len(results) == 2, "Should find logs from server1"
    
    # Test empty query
    results = log_service.search_logs(logs, "")
    assert len(results) == 3, "Empty query should return all logs"
    
    print("✅ Log search passed")


def test_unique_values():
    """Test unique values extraction."""
    print("\n🧪 Testing unique values extraction...")
    
    log_service = LogService()
    
    logs = [
        {
            "level": "info",
            "agent": {"name": "web-server-01", "ip": "192.168.1.10"},
            "rule": {"id": "5501"}
        },
        {
            "level": "warning",
            "agent": {"name": "web-server-01", "ip": "192.168.1.10"},
            "rule": {"id": "5716"}
        },
        {
            "level": "error",
            "agent": {"name": "db-server-01", "ip": "192.168.1.20"},
            "rule": {"id": "2501"}
        }
    ]
    
    # Test simple field
    levels = log_service.get_unique_values(logs, "level")
    assert len(levels) == 3, "Should find 3 unique levels"
    assert "info" in levels and "warning" in levels and "error" in levels
    
    # Test nested field
    agent_names = log_service.get_unique_values(logs, "agent.name")
    assert len(agent_names) == 2, "Should find 2 unique agent names"
    assert "web-server-01" in agent_names and "db-server-01" in agent_names
    
    # Test non-existent field
    missing = log_service.get_unique_values(logs, "nonexistent.field")
    assert len(missing) == 0, "Should return empty set for non-existent field"
    
    print("✅ Unique values extraction passed")


def test_metadata_caching():
    """Test metadata caching functionality."""
    print("\n🧪 Testing metadata caching...")
    
    log_service = LogService()
    
    logs = [
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "Test log entry 1",
            "level": "info",
            "location": "server1",
            "rule": {"id": "5501", "level": 3}
        },
        {
            "timestamp": "2024-01-15T14:30:00",
            "full_log": "Test log entry 2",
            "level": "warning",
            "location": "server2",
            "rule": {"id": "5716", "level": 5}
        }
    ]
    
    metadata_cache = log_service.cache_log_metadata(logs)
    
    assert len(metadata_cache) == 2, "Should cache metadata for all logs"
    
    # Check that metadata objects are properly created
    for log_id, metadata in metadata_cache.items():
        assert isinstance(metadata, LogMetadata), "Should create LogMetadata objects"
        assert metadata.log_id == log_id, "Log ID should match cache key"
        assert metadata.timestamp is not None, "Timestamp should be parsed"
    
    print("✅ Metadata caching passed")


def test_tag_extraction():
    """Test tag extraction from log content."""
    print("\n🧪 Testing tag extraction...")
    
    log_service = LogService()
    
    # Test authentication-related log
    auth_log = {
        "full_log": "Failed password for user admin from 192.168.1.100",
        "rule": {"groups": ["authentication_failed", "sshd"]}
    }
    
    tags = log_service._extract_tags_from_log(auth_log)
    assert "authentication" in tags, "Should detect authentication tag"
    assert "authentication_failed" in tags, "Should include rule groups as tags"
    
    # Test network-related log
    network_log = {
        "full_log": "TCP connection established on port 80",
        "rule": {"groups": ["network"]}
    }
    
    tags = log_service._extract_tags_from_log(network_log)
    assert "network" in tags, "Should detect network tag from content and groups"
    
    # Test file system log
    file_log = {
        "full_log": "File /etc/passwd was modified by user root",
        "rule": {"groups": ["file_system"]}
    }
    
    tags = log_service._extract_tags_from_log(file_log)
    assert "file_system" in tags, "Should detect file system tag"
    
    print("✅ Tag extraction passed")


def main():
    """Run all metadata tests."""
    print("🚀 Starting LogService metadata tests...\n")
    
    try:
        test_metadata_extraction()
        test_enhanced_statistics()
        test_log_filtering()
        test_log_search()
        test_unique_values()
        test_metadata_caching()
        test_tag_extraction()
        
        print("\n🎉 All metadata tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)