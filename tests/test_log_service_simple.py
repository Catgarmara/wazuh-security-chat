"""
Simple test script for LogService functionality
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from services.log_service import LogService, SSHCredentials, LogStats
    from core.exceptions import ValidationError
    print("✅ Successfully imported LogService")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_log_validation():
    """Test log entry validation."""
    print("\n🧪 Testing log validation...")
    
    log_service = LogService()
    
    # Valid log
    valid_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    assert log_service.validate_log_entry(valid_log), "Valid log should pass validation"
    print("✅ Valid log validation passed")
    
    # Invalid log - missing timestamp
    invalid_log = {
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    assert not log_service.validate_log_entry(invalid_log), "Invalid log should fail validation"
    print("✅ Invalid log validation passed")
    
    # Invalid log - empty full_log
    empty_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "",
        "level": "info"
    }
    
    assert not log_service.validate_log_entry(empty_log), "Empty full_log should fail validation"
    print("✅ Empty full_log validation passed")


def test_log_cleaning():
    """Test log entry cleaning."""
    print("\n🧪 Testing log cleaning...")
    
    log_service = LogService()
    
    dirty_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "  Sample log with spaces  ",
        "empty_field": "",
        "null_field": None,
        "valid_field": "value"
    }
    
    cleaned = log_service.clean_log_entry(dirty_log)
    
    assert cleaned["full_log"] == "Sample log with spaces", "Spaces should be stripped"
    assert "empty_field" not in cleaned, "Empty fields should be removed"
    assert "null_field" not in cleaned, "Null fields should be removed"
    assert cleaned["valid_field"] == "value", "Valid fields should be preserved"
    
    print("✅ Log cleaning passed")


def test_log_statistics():
    """Test log statistics generation."""
    print("\n🧪 Testing log statistics...")
    
    log_service = LogService()
    
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
    
    stats = log_service.get_log_statistics(logs)
    
    assert stats.total_logs == 3, f"Expected 3 logs, got {stats.total_logs}"
    assert stats.sources["server1"] == 2, f"Expected 2 logs from server1, got {stats.sources.get('server1', 0)}"
    assert stats.sources["server2"] == 1, f"Expected 1 log from server2, got {stats.sources.get('server2', 0)}"
    assert stats.levels["info"] == 2, f"Expected 2 info logs, got {stats.levels.get('info', 0)}"
    assert stats.levels["warning"] == 1, f"Expected 1 warning log, got {stats.levels.get('warning', 0)}"
    assert "2024-01-15" in stats.date_range, "Date range should include start date"
    assert "2024-01-17" in stats.date_range, "Date range should include end date"
    assert stats.processing_time >= 0, "Processing time should be non-negative"
    
    print("✅ Log statistics passed")


def test_days_validation():
    """Test days parameter validation."""
    print("\n🧪 Testing days validation...")
    
    log_service = LogService()
    
    try:
        log_service.load_logs_from_days(0)
        assert False, "Should raise ValidationError for 0 days"
    except ValidationError:
        print("✅ Zero days validation passed")
    
    try:
        log_service.load_logs_from_days(366)
        assert False, "Should raise ValidationError for 366 days"
    except ValidationError:
        print("✅ Max days validation passed")


def test_ssh_credentials():
    """Test SSH credentials class."""
    print("\n🧪 Testing SSH credentials...")
    
    creds = SSHCredentials("user", "pass", "host", 2222)
    assert creds.username == "user", "Username should match"
    assert creds.password == "pass", "Password should match"
    assert creds.host == "host", "Host should match"
    assert creds.port == 2222, "Port should match"
    
    # Test default port
    creds_default = SSHCredentials("user", "pass", "host")
    assert creds_default.port == 22, "Default port should be 22"
    
    print("✅ SSH credentials passed")


def test_file_parsing():
    """Test log file parsing with temporary file."""
    print("\n🧪 Testing file parsing...")
    
    log_service = LogService()
    
    sample_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry for testing",
        "level": "info",
        "location": "test-server"
    }
    
    # Create temporary file with test data
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(json.dumps(sample_log) + "\n")
        f.write(json.dumps({
            "timestamp": "2024-01-16T10:30:00",
            "full_log": "Second log entry",
            "level": "warning"
        }) + "\n")
        f.write("invalid json line\n")  # This should be skipped
        temp_file_path = f.name
    
    try:
        logs = log_service._parse_log_file(temp_file_path, open)
        assert len(logs) == 2, f"Expected 2 valid logs, got {len(logs)}"
        assert logs[0]["timestamp"] == sample_log["timestamp"], "First log timestamp should match"
        assert logs[1]["level"] == "warning", "Second log level should be warning"
        print("✅ File parsing passed")
    finally:
        os.unlink(temp_file_path)


def main():
    """Run all tests."""
    print("🚀 Starting LogService tests...")
    
    try:
        test_log_validation()
        test_log_cleaning()
        test_log_statistics()
        test_days_validation()
        test_ssh_credentials()
        test_file_parsing()
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)