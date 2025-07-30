"""
Direct test for LogService without going through __init__.py
"""

import sys
import os
import json
import tempfile
from datetime import datetime

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

# Create a proper mock module
class MockConfigModule:
    def get_settings(self):
        return MockSettings()

class MockExceptionsModule:
    LogProcessingError = MockLogProcessingError
    ValidationError = MockValidationError
    ServiceUnavailableError = MockServiceUnavailableError

sys.modules['core.config'] = MockConfigModule()
sys.modules['core.exceptions'] = MockExceptionsModule()

# Mock paramiko
sys.modules['paramiko'] = type('MockModule', (), {})()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the file
import importlib.util
spec = importlib.util.spec_from_file_location("log_service", "services/log_service.py")
log_service_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log_service_module)

LogService = log_service_module.LogService
SSHCredentials = log_service_module.SSHCredentials
LogStats = log_service_module.LogStats


def test_log_service():
    """Test LogService functionality."""
    print("🧪 Testing LogService...")
    
    log_service = LogService()
    
    # Test 1: Valid log validation
    valid_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    result = log_service.validate_log_entry(valid_log)
    assert result is True, "Valid log should pass validation"
    print("✅ Valid log validation passed")
    
    # Test 2: Invalid log validation (missing timestamp)
    invalid_log = {
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    result = log_service.validate_log_entry(invalid_log)
    assert result is False, "Invalid log should fail validation"
    print("✅ Invalid log validation passed")
    
    # Test 3: Log cleaning
    dirty_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "  Sample log with spaces  ",
        "empty_field": "",
        "null_field": None,
        "valid_field": "value"
    }
    
    cleaned = log_service.clean_log_entry(dirty_log)
    assert cleaned["full_log"] == "Sample log with spaces", "Should strip spaces"
    assert "empty_field" not in cleaned, "Should remove empty fields"
    assert "null_field" not in cleaned, "Should remove null fields"
    assert cleaned["valid_field"] == "value", "Should preserve valid fields"
    print("✅ Log cleaning passed")
    
    # Test 4: Statistics generation
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
    assert stats.sources["server1"] == 2, f"Expected 2 logs from server1"
    assert stats.sources["server2"] == 1, f"Expected 1 log from server2"
    assert stats.levels["info"] == 2, f"Expected 2 info logs"
    assert stats.levels["warning"] == 1, f"Expected 1 warning log"
    print("✅ Statistics generation passed")
    
    # Test 5: SSH Credentials
    creds = SSHCredentials("testuser", "testpass", "testhost", 2222)
    assert creds.username == "testuser"
    assert creds.password == "testpass"
    assert creds.host == "testhost"
    assert creds.port == 2222
    print("✅ SSH credentials passed")
    
    # Test 6: Days validation
    try:
        log_service.load_logs_from_days(0)
        assert False, "Should raise ValidationError for 0 days"
    except MockValidationError:
        print("✅ Days validation passed")
    
    # Test 7: File parsing
    sample_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(json.dumps(sample_log) + "\n")
        f.write("invalid json line\n")  # Should be skipped
        f.write(json.dumps({
            "timestamp": "2024-01-16T10:30:00",
            "full_log": "Second log entry",
            "level": "warning"
        }) + "\n")
        temp_file_path = f.name
    
    try:
        logs = log_service._parse_log_file(temp_file_path, open)
        assert len(logs) == 2, f"Expected 2 valid logs, got {len(logs)}"
        assert logs[0]["timestamp"] == sample_log["timestamp"]
        assert logs[1]["level"] == "warning"
        print("✅ File parsing passed")
    finally:
        os.unlink(temp_file_path)
    
    print("\n🎉 All LogService tests passed!")


if __name__ == "__main__":
    try:
        test_log_service()
        print("✅ LogService implementation is working correctly!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)