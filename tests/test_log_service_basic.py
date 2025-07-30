"""
Basic test script for LogService functionality without external dependencies
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Mock the dependencies that aren't available
class MockSettings:
    pass

class MockLogProcessingError(Exception):
    pass

class MockValidationError(Exception):
    pass

class MockServiceUnavailableError(Exception):
    pass

# Mock the core modules
sys.modules['core.config'] = type('MockModule', (), {'get_settings': lambda: MockSettings()})()
sys.modules['core.exceptions'] = type('MockModule', (), {
    'LogProcessingError': MockLogProcessingError,
    'ValidationError': MockValidationError,
    'ServiceUnavailableError': MockServiceUnavailableError
})()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import our service
from services.log_service import LogService, SSHCredentials, LogStats


def test_basic_functionality():
    """Test basic LogService functionality."""
    print("🧪 Testing basic LogService functionality...")
    
    log_service = LogService()
    
    # Test log validation
    valid_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    assert log_service.validate_log_entry(valid_log), "Valid log should pass validation"
    print("✅ Log validation works")
    
    # Test invalid log
    invalid_log = {"full_log": "Missing timestamp"}
    assert not log_service.validate_log_entry(invalid_log), "Invalid log should fail"
    print("✅ Invalid log detection works")
    
    # Test log cleaning
    dirty_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "  Spaces  ",
        "empty": "",
        "null": None,
        "valid": "value"
    }
    
    cleaned = log_service.clean_log_entry(dirty_log)
    assert cleaned["full_log"] == "Spaces", "Should strip spaces"
    assert "empty" not in cleaned, "Should remove empty fields"
    assert "null" not in cleaned, "Should remove null fields"
    assert cleaned["valid"] == "value", "Should keep valid fields"
    print("✅ Log cleaning works")
    
    # Test statistics
    logs = [
        {"timestamp": "2024-01-15T10:30:00", "full_log": "Log 1", "level": "info", "location": "server1"},
        {"timestamp": "2024-01-16T11:30:00", "full_log": "Log 2", "level": "warning", "location": "server1"},
        {"timestamp": "2024-01-17T12:30:00", "full_log": "Log 3", "level": "info", "location": "server2"}
    ]
    
    stats = log_service.get_log_statistics(logs)
    assert stats.total_logs == 3, "Should count all logs"
    assert stats.sources["server1"] == 2, "Should count server1 logs"
    assert stats.levels["info"] == 2, "Should count info logs"
    print("✅ Statistics generation works")
    
    # Test SSH credentials
    creds = SSHCredentials("user", "pass", "host", 2222)
    assert creds.username == "user"
    assert creds.port == 2222
    print("✅ SSH credentials work")
    
    # Test days validation
    try:
        log_service.load_logs_from_days(0)
        assert False, "Should raise error for 0 days"
    except MockValidationError:
        print("✅ Days validation works")
    
    print("\n🎉 All basic tests passed!")


def test_file_parsing():
    """Test file parsing functionality."""
    print("\n🧪 Testing file parsing...")
    
    log_service = LogService()
    
    sample_log = {
        "timestamp": "2024-01-15T10:30:00",
        "full_log": "Sample log entry",
        "level": "info"
    }
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(json.dumps(sample_log) + "\n")
        f.write("invalid json\n")  # Should be skipped
        f.write(json.dumps({"timestamp": "2024-01-16T10:30:00", "full_log": "Log 2"}) + "\n")
        temp_file = f.name
    
    try:
        logs = log_service._parse_log_file(temp_file, open)
        assert len(logs) == 2, f"Expected 2 logs, got {len(logs)}"
        assert logs[0]["level"] == "info", "First log should have info level"
        print("✅ File parsing works")
    finally:
        os.unlink(temp_file)


def main():
    """Run all tests."""
    print("🚀 Starting basic LogService tests...\n")
    
    try:
        test_basic_functionality()
        test_file_parsing()
        print("\n✅ All tests completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)