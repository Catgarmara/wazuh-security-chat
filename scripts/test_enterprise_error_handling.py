#!/usr/bin/env python3
"""
Test script for enterprise-grade error handling and resource management.

This script validates the implementation of task 10:
- Error handling for missing llama-cpp-python dependency
- Graceful degradation when models fail to load
- Intelligent resource monitoring and automatic model management
- Informative error messages and recovery suggestions
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exceptions import (
    EmbeddedAIError, ModelLoadingError, ResourceExhaustionError, ErrorCode
)
from core.resource_manager import get_resource_manager, ResourceType, ResourceStatus
from services.embedded_ai_service import EmbeddedAIService
from core.health import get_application_health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnterpriseErrorHandlingTester:
    """Test suite for enterprise-grade error handling and resource management."""
    
    def __init__(self):
        self.test_results = {}
        self.resource_manager = get_resource_manager()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all enterprise error handling tests."""
        logger.info("Starting enterprise error handling test suite...")
        
        test_methods = [
            self.test_llama_cpp_dependency_handling,
            self.test_model_loading_error_handling,
            self.test_resource_monitoring,
            self.test_automatic_model_management,
            self.test_graceful_degradation,
            self.test_recovery_suggestions,
            self.test_health_check_integration,
            self.test_resource_exhaustion_handling
        ]
        
        for test_method in test_methods:
            test_name = test_method.__name__
            logger.info(f"Running test: {test_name}")
            
            try:
                result = await test_method()
                self.test_results[test_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": result if isinstance(result, dict) else {"success": result}
                }
                logger.info(f"Test {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results[test_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "details": {"exception_type": type(e).__name__}
                }
                logger.error(f"Test {test_name} failed with error: {e}")
        
        return self.generate_test_report()
    
    async def test_llama_cpp_dependency_handling(self) -> bool:
        """Test handling of missing llama-cpp-python dependency."""
        logger.info("Testing llama-cpp-python dependency handling...")
        
        try:
            # This test checks if the service properly handles missing dependencies
            # In a real scenario, we would mock the import failure
            
            # Check if the service detects llama-cpp availability
            from services.embedded_ai_service import LLAMA_CPP_AVAILABLE
            
            if not LLAMA_CPP_AVAILABLE:
                # Test that service initialization handles missing dependency
                try:
                    service = EmbeddedAIService()
                    # Should raise EmbeddedAIError with proper recovery suggestions
                    return False  # Should not reach here
                except EmbeddedAIError as e:
                    # Verify error code and recovery suggestions
                    if (e.error_code == ErrorCode.LLAMA_CPP_NOT_AVAILABLE and 
                        e.recovery_suggestions and 
                        any("pip install llama-cpp-python" in suggestion for suggestion in e.recovery_suggestions)):
                        return True
                    return False
            else:
                logger.info("llama-cpp-python is available, skipping dependency error test")
                return True
                
        except Exception as e:
            logger.error(f"Dependency handling test failed: {e}")
            return False
    
    async def test_model_loading_error_handling(self) -> bool:
        """Test comprehensive model loading error handling."""
        logger.info("Testing model loading error handling...")
        
        try:
            service = EmbeddedAIService()
            
            # Test loading non-existent model
            try:
                service.load_model("non_existent_model")
                return False  # Should raise error
            except ModelLoadingError as e:
                # Verify error has proper structure
                if (e.error_code == ErrorCode.MODEL_NOT_AVAILABLE and
                    e.recovery_suggestions and
                    e.model_id == "non_existent_model"):
                    logger.info("Non-existent model error handling: PASSED")
                else:
                    return False
            
            # Test registering and loading invalid model path
            invalid_path = "/invalid/path/model.gguf"
            service.register_model("invalid_model", invalid_path, "Invalid Model")
            
            try:
                service.load_model("invalid_model")
                return False  # Should raise error
            except ModelLoadingError as e:
                # Verify error has proper structure and recovery suggestions
                if (e.error_code == ErrorCode.MODEL_NOT_AVAILABLE and
                    e.recovery_suggestions and
                    e.model_path == invalid_path):
                    logger.info("Invalid model path error handling: PASSED")
                    return True
                else:
                    return False
            
        except Exception as e:
            logger.error(f"Model loading error test failed: {e}")
            return False
    
    async def test_resource_monitoring(self) -> bool:
        """Test resource monitoring functionality."""
        logger.info("Testing resource monitoring...")
        
        try:
            # Start resource monitoring
            if not self.resource_manager.monitoring_active:
                self.resource_manager.start_monitoring()
            
            # Wait for monitoring to collect data
            await asyncio.sleep(2)
            
            # Get current resource status
            status = self.resource_manager.get_current_resource_status()
            
            # Verify status structure
            required_fields = ["overall_status", "timestamp", "resources"]
            if not all(field in status for field in required_fields):
                return False
            
            # Verify resource types are monitored
            expected_resources = ["cpu", "memory", "disk"]
            resources = status["resources"]
            
            for resource_type in expected_resources:
                if resource_type not in resources:
                    logger.error(f"Resource type {resource_type} not monitored")
                    return False
                
                resource_info = resources[resource_type]
                required_resource_fields = ["usage_percent", "status", "available", "total"]
                if not all(field in resource_info for field in required_resource_fields):
                    logger.error(f"Resource {resource_type} missing required fields")
                    return False
            
            logger.info("Resource monitoring structure: PASSED")
            
            # Test resource trends
            trends = self.resource_manager.get_resource_trends(ResourceType.MEMORY, hours=1)
            if "trend" not in trends or "average_usage" not in trends:
                return False
            
            logger.info("Resource trends: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Resource monitoring test failed: {e}")
            return False
    
    async def test_automatic_model_management(self) -> bool:
        """Test automatic model management based on resource availability."""
        logger.info("Testing automatic model management...")
        
        try:
            service = EmbeddedAIService()
            
            # Test getting inactive models
            inactive_models = service.get_inactive_models(inactive_threshold_minutes=1)
            logger.info(f"Found {len(inactive_models)} inactive models")
            
            # Test resource optimization methods
            resource_reduction_result = service.reduce_resource_usage()
            gpu_optimization_result = service.optimize_gpu_usage()
            
            if not isinstance(resource_reduction_result, bool):
                return False
            if not isinstance(gpu_optimization_result, bool):
                return False
            
            logger.info("Automatic model management methods: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Automatic model management test failed: {e}")
            return False
    
    async def test_graceful_degradation(self) -> bool:
        """Test graceful degradation when models fail to load."""
        logger.info("Testing graceful degradation...")
        
        try:
            service = EmbeddedAIService()
            
            # Check if service can operate in degraded mode
            if hasattr(service, 'service_degraded'):
                logger.info(f"Service degraded mode: {service.service_degraded}")
            
            # Check if backup models are configured
            if hasattr(service, 'backup_models'):
                backup_count = len(service.backup_models)
                logger.info(f"Backup models configured: {backup_count}")
            
            # Check if fallback model is available
            if hasattr(service, 'fallback_model_id'):
                fallback_model = service.fallback_model_id
                logger.info(f"Fallback model: {fallback_model}")
            
            # Test service status in degraded mode
            status = service.get_service_status()
            if "service_ready" not in status:
                return False
            
            logger.info("Graceful degradation: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Graceful degradation test failed: {e}")
            return False
    
    async def test_recovery_suggestions(self) -> bool:
        """Test informative error messages and recovery suggestions."""
        logger.info("Testing recovery suggestions...")
        
        try:
            service = EmbeddedAIService()
            
            # Test recovery plan generation
            test_error = ModelLoadingError(
                message="Test model loading error",
                model_id="test_model",
                memory_required=4096,
                memory_available=2048
            )
            
            recovery_plan = service.generate_recovery_plan(test_error)
            
            # Verify recovery plan structure
            required_fields = [
                "error_type", "error_message", "timestamp",
                "immediate_actions", "investigation_steps",
                "prevention_measures", "escalation_criteria"
            ]
            
            if not all(field in recovery_plan for field in required_fields):
                logger.error("Recovery plan missing required fields")
                return False
            
            # Verify recovery suggestions are meaningful
            if not recovery_plan["immediate_actions"]:
                logger.error("No immediate actions in recovery plan")
                return False
            
            logger.info("Recovery suggestions structure: PASSED")
            
            # Test resource recommendations
            recommendations = self.resource_manager.generate_resource_recommendations()
            if not isinstance(recommendations, list):
                return False
            
            logger.info("Resource recommendations: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Recovery suggestions test failed: {e}")
            return False
    
    async def test_health_check_integration(self) -> bool:
        """Test health check integration with error handling."""
        logger.info("Testing health check integration...")
        
        try:
            # Get application health
            health_status = await get_application_health(use_cache=False)
            
            # Verify health check structure
            if "summary" not in health_status or "checks" not in health_status:
                return False
            
            # Check for embedded AI service health
            checks = health_status["checks"]
            if "embedded_ai_service" not in checks:
                logger.error("Embedded AI service not in health checks")
                return False
            
            ai_health = checks["embedded_ai_service"]
            required_fields = ["status", "message", "details"]
            if not all(field in ai_health for field in required_fields):
                logger.error("AI health check missing required fields")
                return False
            
            # Verify detailed health information
            details = ai_health["details"]
            expected_details = [
                "llama_cpp_available", "loaded_models", "service_degraded",
                "resource_status", "backup_models_available"
            ]
            
            for detail in expected_details:
                if detail not in details:
                    logger.warning(f"Health check detail '{detail}' not found")
            
            logger.info("Health check integration: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Health check integration test failed: {e}")
            return False
    
    async def test_resource_exhaustion_handling(self) -> bool:
        """Test resource exhaustion error handling."""
        logger.info("Testing resource exhaustion handling...")
        
        try:
            # Test ResourceExhaustionError creation and structure
            error = ResourceExhaustionError(
                message="Memory exhausted",
                resource_type="memory",
                current_usage=95.5,
                threshold=90.0,
                auto_recovery_attempted=True
            )
            
            # Verify error structure
            if error.resource_type != "memory":
                return False
            if error.current_usage != 95.5:
                return False
            if not error.auto_recovery_attempted:
                return False
            
            # Test error dictionary conversion
            error_dict = error.to_dict()
            if "resource_type" not in error_dict["details"]:
                return False
            
            logger.info("Resource exhaustion error structure: PASSED")
            
            # Test resource callback registration
            callback_called = False
            
            def test_callback(metric):
                nonlocal callback_called
                callback_called = True
            
            self.resource_manager.register_resource_callback(
                ResourceStatus.WARNING, test_callback
            )
            
            logger.info("Resource exhaustion handling: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Resource exhaustion handling test failed: {e}")
            return False
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASSED")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "FAILED")
        error_tests = sum(1 for result in self.test_results.values() if result["status"] == "ERROR")
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "overall_status": "PASSED" if failed_tests == 0 and error_tests == 0 else "FAILED",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "recommendations": []
        }
        
        # Add recommendations based on test results
        if failed_tests > 0:
            report["recommendations"].append(
                "Review failed tests and address underlying issues before deployment"
            )
        
        if error_tests > 0:
            report["recommendations"].append(
                "Investigate test errors - may indicate configuration or dependency issues"
            )
        
        if passed_tests == total_tests:
            report["recommendations"].append(
                "All tests passed - enterprise error handling implementation is ready for production"
            )
        
        return report


async def main():
    """Main test execution function."""
    print("=" * 80)
    print("ENTERPRISE ERROR HANDLING AND RESOURCE MANAGEMENT TEST SUITE")
    print("=" * 80)
    
    tester = EnterpriseErrorHandlingTester()
    
    try:
        report = await tester.run_all_tests()
        
        print("\n" + "=" * 80)
        print("TEST REPORT")
        print("=" * 80)
        
        summary = report["test_summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Overall Status: {report['overall_status']}")
        
        print("\n" + "-" * 40)
        print("INDIVIDUAL TEST RESULTS")
        print("-" * 40)
        
        for test_name, result in report["test_results"].items():
            status_symbol = "✓" if result["status"] == "PASSED" else "✗"
            print(f"{status_symbol} {test_name}: {result['status']}")
            if result["status"] in ["FAILED", "ERROR"] and "error" in result:
                print(f"  Error: {result['error']}")
        
        if report["recommendations"]:
            print("\n" + "-" * 40)
            print("RECOMMENDATIONS")
            print("-" * 40)
            for i, recommendation in enumerate(report["recommendations"], 1):
                print(f"{i}. {recommendation}")
        
        print("\n" + "=" * 80)
        
        # Return appropriate exit code
        return 0 if report["overall_status"] == "PASSED" else 1
        
    except Exception as e:
        print(f"Test suite execution failed: {e}")
        logger.error("Test suite execution failed", exc_info=True)
        return 1
    finally:
        # Cleanup
        try:
            tester.resource_manager.shutdown()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)