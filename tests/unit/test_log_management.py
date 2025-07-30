"""
Test script for LogService management functionality
"""

import sys
import os
import time
import tempfile
import shutil
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
LogReloadStatus = log_service_module.LogReloadStatus
LogHealthStatus = log_service_module.LogHealthStatus
LogFilter = log_service_module.LogFilter


def test_reload_status():
    """Test LogReloadStatus functionality."""
    print("🧪 Testing reload status...")
    
    start_time = datetime.now()
    status = LogReloadStatus(
        status="running",
        message="Processing logs...",
        progress=0.5,
        logs_processed=50,
        total_logs=100,
        start_time=start_time
    )
    
    assert status.status == "running"
    assert status.progress == 0.5
    assert status.logs_processed == 50
    assert status.total_logs == 100
    assert status.start_time == start_time
    
    # Test duration calculation
    time.sleep(0.1)  # Small delay
    status.end_time = datetime.now()
    duration = status.duration
    assert duration is not None
    assert duration.total_seconds() > 0
    
    print("✅ Reload status passed")


def test_health_status():
    """Test LogHealthStatus functionality."""
    print("\n🧪 Testing health status...")
    
    health = LogHealthStatus(
        status="healthy",
        last_reload=datetime.now(),
        total_logs_cached=1000,
        cache_size_mb=10.5,
        avg_processing_time=0.5,
        error_rate=0.01,
        disk_usage_mb=500.0,
        memory_usage_mb=128.0
    )
    
    assert health.status == "healthy"
    assert health.total_logs_cached == 1000
    assert health.cache_size_mb == 10.5
    assert health.error_rate == 0.01
    
    print("✅ Health status passed")


def test_date_range_reload():
    """Test log reload with date range."""
    print("\n🧪 Testing date range reload...")
    
    log_service = LogService()
    
    # Mock the load_logs_from_days method to return test data
    original_method = log_service.load_logs_from_days
    
    def mock_load_logs(days, ssh_creds=None):
        # Return logs spanning multiple days
        logs = []
        base_date = datetime.now() - timedelta(days=days)
        for i in range(days):
            log_date = base_date + timedelta(days=i)
            logs.append({
                "timestamp": log_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "full_log": f"Test log for day {i}",
                "level": "info",
                "location": "test"
            })
        return logs
    
    log_service.load_logs_from_days = mock_load_logs
    
    # Test date range reload
    start_date = datetime.now() - timedelta(days=3)
    end_date = datetime.now() - timedelta(days=1)
    
    progress_updates = []
    def progress_callback(status):
        progress_updates.append(status.message)
    
    status = log_service.reload_logs_with_date_range(
        start_date, end_date, progress_callback=progress_callback
    )
    
    assert status.status == "completed"
    assert len(progress_updates) > 0
    assert status.progress == 1.0
    
    # Restore original method
    log_service.load_logs_from_days = original_method
    
    print("✅ Date range reload passed")


def test_background_reload():
    """Test background log reload."""
    print("\n🧪 Testing background reload...")
    
    log_service = LogService()
    
    # Mock the load_logs_from_days method
    def mock_load_logs(days, ssh_creds=None):
        return [
            {
                "timestamp": "2024-01-15T10:30:00",
                "full_log": "Background test log",
                "level": "info",
                "location": "test"
            }
        ]
    
    log_service.load_logs_from_days = mock_load_logs
    
    progress_updates = []
    def progress_callback(status):
        progress_updates.append(status)
    
    # Start background reload
    thread = log_service.reload_logs_background(
        days=1, progress_callback=progress_callback
    )
    
    # Wait for completion
    thread.join(timeout=5.0)
    
    assert not thread.is_alive(), "Background thread should complete"
    assert len(progress_updates) > 0, "Should receive progress updates"
    
    # Check final status
    final_status = progress_updates[-1]
    assert final_status.status == "completed"
    
    print("✅ Background reload passed")


def test_health_status_calculation():
    """Test health status calculation."""
    print("\n🧪 Testing health status calculation...")
    
    log_service = LogService()
    
    # Create temporary log directory for testing
    temp_dir = tempfile.mkdtemp()
    original_path = log_service.log_base_path
    log_service.log_base_path = temp_dir
    
    try:
        # Create some test files
        test_file = os.path.join(temp_dir, "test.log")
        with open(test_file, 'w') as f:
            f.write("test log content" * 100)  # Create some content
        
        logs = [
            {"timestamp": "2024-01-15T10:30:00", "full_log": "Test log 1", "level": "info"},
            {"timestamp": "2024-01-15T11:30:00", "full_log": "Test log 2", "level": "warning"}
        ]
        
        health = log_service.get_health_status(logs)
        
        assert health.status in ["healthy", "warning", "critical"]
        assert health.total_logs_cached == 2
        assert health.cache_size_mb > 0
        assert health.disk_usage_mb >= 0
        
        print("✅ Health status calculation passed")
        
    finally:
        # Cleanup
        log_service.log_base_path = original_path
        shutil.rmtree(temp_dir)


def test_log_cleanup():
    """Test log cleanup functionality."""
    print("\n🧪 Testing log cleanup...")
    
    log_service = LogService()
    
    # Create temporary directory structure
    temp_dir = tempfile.mkdtemp()
    original_path = log_service.log_base_path
    log_service.log_base_path = temp_dir
    
    try:
        # Create old log structure (simulate old logs)
        old_year = datetime.now().year - 1
        old_month = "Jan"
        old_dir = os.path.join(temp_dir, str(old_year), old_month)
        os.makedirs(old_dir, exist_ok=True)
        
        # Create old log file
        old_file = os.path.join(old_dir, "ossec-archive-01.json")
        with open(old_file, 'w') as f:
            f.write('{"timestamp": "2023-01-01T00:00:00", "full_log": "old log"}')
        
        # Create recent log structure
        recent_year = datetime.now().year
        recent_month = datetime.now().strftime("%b")
        recent_dir = os.path.join(temp_dir, str(recent_year), recent_month)
        os.makedirs(recent_dir, exist_ok=True)
        
        # Create recent log file
        recent_file = os.path.join(recent_dir, "ossec-archive-01.json")
        with open(recent_file, 'w') as f:
            f.write('{"timestamp": "2024-01-01T00:00:00", "full_log": "recent log"}')
        
        # Run cleanup (keep 30 days)
        results = log_service.cleanup_old_logs(days_to_keep=30)
        
        assert results["files_removed"] >= 0
        assert results["space_freed_mb"] >= 0
        assert isinstance(results["errors"], list)
        
        # Old file should be removed, recent file should remain
        assert not os.path.exists(old_file), "Old file should be removed"
        assert os.path.exists(recent_file), "Recent file should remain"
        
        print("✅ Log cleanup passed")
        
    finally:
        # Cleanup
        log_service.log_base_path = original_path
        shutil.rmtree(temp_dir)


def test_statistics_summary():
    """Test comprehensive statistics summary."""
    print("\n🧪 Testing statistics summary...")
    
    log_service = LogService()
    
    logs = [
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "SSH login successful",
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
            "full_log": "System error",
            "level": "error",
            "location": "server2",
            "agent": {"name": "db-server-01"},
            "rule": {"id": "2501", "level": 7},
            "decoder": {"name": "kernel"}
        }
    ]
    
    summary = log_service.get_log_statistics_summary(logs)
    
    # Check overview
    assert summary["overview"]["total_logs"] == 3
    assert summary["overview"]["total_agents"] == 2
    assert summary["overview"]["total_rules"] == 3
    
    # Check top items
    assert len(summary["top_items"]["agents"]) <= 5
    assert len(summary["top_items"]["rules"]) <= 5
    
    # Check distributions
    assert "levels" in summary["distributions"]
    assert "severity" in summary["distributions"]
    assert "hourly" in summary["distributions"]
    
    # Check health metrics
    assert "health" in summary
    assert "error_rate" in summary["health"]
    
    print("✅ Statistics summary passed")


def test_log_integrity_validation():
    """Test log integrity validation."""
    print("\n🧪 Testing log integrity validation...")
    
    log_service = LogService()
    
    logs = [
        # Valid log
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "Valid log entry",
            "level": "info"
        },
        # Invalid log (missing timestamp)
        {
            "full_log": "Invalid log entry",
            "level": "info"
        },
        # Invalid log (empty full_log)
        {
            "timestamp": "2024-01-15T10:30:00",
            "full_log": "",
            "level": "info"
        }
    ]
    
    validation = log_service.validate_log_integrity(logs)
    
    assert validation["total_logs"] == 3
    assert validation["valid_logs"] == 1
    assert validation["invalid_logs"] == 2
    assert len(validation["validation_errors"]) == 2
    assert len(validation["warnings"]) > 0  # Should warn about high error rate
    
    print("✅ Log integrity validation passed")


def test_error_handling():
    """Test error handling in management functions."""
    print("\n🧪 Testing error handling...")
    
    log_service = LogService()
    
    # Test invalid date range
    start_date = datetime.now()
    end_date = datetime.now() - timedelta(days=1)  # End before start
    
    status = log_service.reload_logs_with_date_range(start_date, end_date)
    assert status.status == "failed"
    assert "End date must be after start date" in status.message
    
    # Test invalid cleanup days
    try:
        log_service.cleanup_old_logs(days_to_keep=0)
        assert False, "Should raise ValidationError"
    except MockValidationError:
        pass
    
    print("✅ Error handling passed")


def main():
    """Run all management tests."""
    print("🚀 Starting LogService management tests...\n")
    
    try:
        test_reload_status()
        test_health_status()
        test_date_range_reload()
        test_background_reload()
        test_health_status_calculation()
        test_log_cleanup()
        test_statistics_summary()
        test_log_integrity_validation()
        test_error_handling()
        
        print("\n🎉 All management tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)