#!/usr/bin/env python3
"""
Task 3 Implementation Validation Script

Validates that the embedded AI service is established as the sole provider
according to the requirements and validation standards.
"""

import sys
import os
import logging
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Task3Validator:
    """Comprehensive validator for Task 3 implementation."""
    
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
    
    def log_result(self, test_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Log validation result."""
        result = {
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details or {}
        }
        self.validation_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name} - {message}")
        
        if not passed:
            self.errors.append(f"{test_name}: {message}")
    
    def log_warning(self, test_name: str, message: str):
        """Log validation warning."""
        self.warnings.append(f"{test_name}: {message}")
        logger.warning(f"⚠️  WARNING: {test_name} - {message}")
    
    def validate_ai_service_factory(self) -> bool:
        """Validate AIServiceFactory implementation."""
        try:
            from core.ai_factory import AIServiceFactory
            
            # Test 1: Factory class exists and is importable
            self.log_result(
                "AIServiceFactory Import",
                True,
                "AIServiceFactory successfully imported"
            )
            
            # Test 2: Factory has required methods
            required_methods = [
                'get_ai_service',
                'initialize_ai_service', 
                'shutdown_ai_service',
                'is_service_ready',
                'get_service_status'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(AIServiceFactory, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_result(
                    "AIServiceFactory Methods",
                    False,
                    f"Missing required methods: {missing_methods}"
                )
                return False
            else:
                self.log_result(
                    "AIServiceFactory Methods",
                    True,
                    "All required methods present"
                )
            
            # Test 3: Singleton pattern implementation
            factory1 = AIServiceFactory()
            factory2 = AIServiceFactory()
            
            if factory1 is factory2:
                self.log_result(
                    "AIServiceFactory Singleton",
                    True,
                    "Singleton pattern correctly implemented"
                )
            else:
                self.log_result(
                    "AIServiceFactory Singleton",
                    False,
                    "Singleton pattern not working - multiple instances created"
                )
                return False
            
            # Test 4: Thread safety (basic check)
            if hasattr(AIServiceFactory, '_lock') and hasattr(AIServiceFactory, '_ai_service_lock'):
                self.log_result(
                    "AIServiceFactory Thread Safety",
                    True,
                    "Thread safety locks present"
                )
            else:
                self.log_result(
                    "AIServiceFactory Thread Safety",
                    False,
                    "Thread safety locks missing"
                )
                return False
            
            return True
            
        except ImportError as e:
            self.log_result(
                "AIServiceFactory Import",
                False,
                f"Failed to import AIServiceFactory: {e}"
            )
            return False
        except Exception as e:
            self.log_result(
                "AIServiceFactory Validation",
                False,
                f"Unexpected error: {e}"
            )
            return False
    
    def validate_services_module(self) -> bool:
        """Validate services module integration."""
        try:
            from services import get_ai_service, initialize_ai_service, is_ai_service_ready, get_ai_service_status
            
            # Test 1: Required functions exist
            self.log_result(
                "Services Module Functions",
                True,
                "All required AI service functions available"
            )
            
            # Test 2: Functions use AIServiceFactory
            import inspect
            from services import __init__ as services_init
            
            source = inspect.getsource(services_init)
            if "AIServiceFactory" in source:
                self.log_result(
                    "Services Module Integration",
                    True,
                    "Services module uses AIServiceFactory"
                )
            else:
                self.log_result(
                    "Services Module Integration",
                    False,
                    "Services module does not use AIServiceFactory"
                )
                return False
            
            # Test 3: No direct EmbeddedAIService instantiation in get_ai_service
            get_ai_service_source = inspect.getsource(get_ai_service)
            if "EmbeddedAIService()" in get_ai_service_source:
                self.log_result(
                    "Services Module Direct Instantiation",
                    False,
                    "get_ai_service() directly instantiates EmbeddedAIService"
                )
                return False
            else:
                self.log_result(
                    "Services Module Direct Instantiation",
                    True,
                    "get_ai_service() uses factory pattern"
                )
            
            return True
            
        except ImportError as e:
            self.log_result(
                "Services Module Import",
                False,
                f"Failed to import services module: {e}"
            )
            return False
        except Exception as e:
            self.log_result(
                "Services Module Validation",
                False,
                f"Unexpected error: {e}"
            )
            return False
    
    def validate_api_integration(self) -> bool:
        """Validate API integration uses factory."""
        try:
            # Check api/ai.py
            api_ai_path = Path("api/ai.py")
            if not api_ai_path.exists():
                self.log_result(
                    "API AI Module",
                    False,
                    "api/ai.py file not found"
                )
                return False
            
            with open(api_ai_path, 'r') as f:
                api_content = f.read()
            
            # Test 1: Uses AIServiceFactory import
            if "from core.ai_factory import AIServiceFactory" in api_content:
                self.log_result(
                    "API AI Factory Import",
                    True,
                    "API module imports AIServiceFactory"
                )
            else:
                self.log_result(
                    "API AI Factory Import",
                    False,
                    "API module does not import AIServiceFactory"
                )
                return False
            
            # Test 2: get_ai_service function uses factory
            if "AIServiceFactory.get_ai_service()" in api_content:
                self.log_result(
                    "API AI Service Function",
                    True,
                    "API get_ai_service() uses factory"
                )
            else:
                self.log_result(
                    "API AI Service Function",
                    False,
                    "API get_ai_service() does not use factory"
                )
                return False
            
            # Test 3: No direct EmbeddedAIService instantiation
            if "EmbeddedAIService()" in api_content:
                self.log_result(
                    "API Direct Instantiation",
                    False,
                    "API module directly instantiates EmbeddedAIService"
                )
                return False
            else:
                self.log_result(
                    "API Direct Instantiation",
                    True,
                    "API module uses factory pattern"
                )
            
            return True
            
        except Exception as e:
            self.log_result(
                "API Integration Validation",
                False,
                f"Error validating API integration: {e}"
            )
            return False
    
    def validate_configuration(self) -> bool:
        """Validate configuration supports embedded AI."""
        try:
            from core.config import get_settings
            
            settings = get_settings()
            
            # Test 1: EmbeddedAISettings exists
            if hasattr(settings, 'embedded_ai'):
                self.log_result(
                    "Configuration Embedded AI",
                    True,
                    "EmbeddedAISettings configuration present"
                )
            else:
                self.log_result(
                    "Configuration Embedded AI",
                    False,
                    "EmbeddedAISettings configuration missing"
                )
                return False
            
            # Test 2: Required embedded AI settings
            required_settings = [
                'models_path',
                'vectorstore_path',
                'embedding_model_name',
                'max_concurrent_models',
                'conversation_memory_size'
            ]
            
            missing_settings = []
            for setting in required_settings:
                if not hasattr(settings.embedded_ai, setting):
                    missing_settings.append(setting)
            
            if missing_settings:
                self.log_result(
                    "Configuration Required Settings",
                    False,
                    f"Missing embedded AI settings: {missing_settings}"
                )
                return False
            else:
                self.log_result(
                    "Configuration Required Settings",
                    True,
                    "All required embedded AI settings present"
                )
            
            # Test 3: Validate appliance deployment settings
            try:
                settings.embedded_ai.validate_appliance_deployment()
                self.log_result(
                    "Configuration Appliance Validation",
                    True,
                    "Appliance deployment settings valid"
                )
            except ValueError as e:
                self.log_result(
                    "Configuration Appliance Validation",
                    False,
                    f"Appliance deployment validation failed: {e}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.log_result(
                "Configuration Validation",
                False,
                f"Error validating configuration: {e}"
            )
            return False
    
    def validate_no_external_ai_services(self) -> bool:
        """Validate no external AI service references remain."""
        try:
            # Check for old AI service imports/references
            files_to_check = [
                "core/ai_factory.py",
                "services/__init__.py",
                "api/ai.py"
            ]
            
            external_ai_patterns = [
                "OllamaService",
                "OpenAIService", 
                "from.*ollama",
                "import.*ollama",
                "from.*openai",
                "import.*openai"
            ]
            
            for file_path in files_to_check:
                if not Path(file_path).exists():
                    continue
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                found_external = []
                for pattern in external_ai_patterns:
                    if pattern.lower() in content.lower():
                        found_external.append(pattern)
                
                if found_external:
                    self.log_result(
                        f"External AI Services - {file_path}",
                        False,
                        f"Found external AI service references: {found_external}"
                    )
                    return False
            
            self.log_result(
                "External AI Services Check",
                True,
                "No external AI service references found"
            )
            return True
            
        except Exception as e:
            self.log_result(
                "External AI Services Validation",
                False,
                f"Error checking external AI services: {e}"
            )
            return False
    
    def validate_health_checks(self) -> bool:
        """Validate health check integration."""
        try:
            # Check if health.py uses factory
            health_path = Path("core/health.py")
            if not health_path.exists():
                self.log_warning(
                    "Health Check File",
                    "core/health.py not found - health checks may not be implemented"
                )
                return True
            
            with open(health_path, 'r') as f:
                health_content = f.read()
            
            # Check for factory usage
            if "AIServiceFactory" in health_content:
                self.log_result(
                    "Health Check Integration",
                    True,
                    "Health checks use AIServiceFactory"
                )
            else:
                self.log_warning(
                    "Health Check Integration",
                    "Health checks may not use AIServiceFactory"
                )
            
            return True
            
        except Exception as e:
            self.log_result(
                "Health Check Validation",
                False,
                f"Error validating health checks: {e}"
            )
            return False
    
    def validate_functional_integration(self) -> bool:
        """Validate functional integration works."""
        try:
            from core.ai_factory import AIServiceFactory
            from services import get_ai_service
            
            # Test 1: Factory method returns consistent results
            service1 = AIServiceFactory.get_ai_service()
            service2 = get_ai_service()
            
            # Both should return the same type (None or EmbeddedAIService)
            if type(service1) == type(service2):
                self.log_result(
                    "Functional Integration Consistency",
                    True,
                    f"Both methods return same type: {type(service1)}"
                )
            else:
                self.log_result(
                    "Functional Integration Consistency",
                    False,
                    f"Methods return different types: {type(service1)} vs {type(service2)}"
                )
                return False
            
            # Test 2: Status methods work
            try:
                status = AIServiceFactory.get_service_status()
                if isinstance(status, dict):
                    self.log_result(
                        "Functional Status Method",
                        True,
                        "Service status method returns dictionary"
                    )
                else:
                    self.log_result(
                        "Functional Status Method",
                        False,
                        f"Service status method returns {type(status)}, expected dict"
                    )
                    return False
            except Exception as e:
                self.log_result(
                    "Functional Status Method",
                    False,
                    f"Service status method failed: {e}"
                )
                return False
            
            # Test 3: Readiness check works
            try:
                ready = AIServiceFactory.is_service_ready()
                if isinstance(ready, bool):
                    self.log_result(
                        "Functional Readiness Check",
                        True,
                        f"Service readiness check returns boolean: {ready}"
                    )
                else:
                    self.log_result(
                        "Functional Readiness Check",
                        False,
                        f"Service readiness check returns {type(ready)}, expected bool"
                    )
                    return False
            except Exception as e:
                self.log_result(
                    "Functional Readiness Check",
                    False,
                    f"Service readiness check failed: {e}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.log_result(
                "Functional Integration Validation",
                False,
                f"Error validating functional integration: {e}"
            )
            return False
    
    def run_validation(self) -> bool:
        """Run complete validation suite."""
        logger.info("🚀 Starting Task 3 Implementation Validation")
        logger.info("=" * 60)
        
        validation_steps = [
            ("AI Service Factory", self.validate_ai_service_factory),
            ("Services Module", self.validate_services_module),
            ("API Integration", self.validate_api_integration),
            ("Configuration", self.validate_configuration),
            ("External AI Services", self.validate_no_external_ai_services),
            ("Health Checks", self.validate_health_checks),
            ("Functional Integration", self.validate_functional_integration)
        ]
        
        all_passed = True
        
        for step_name, validation_func in validation_steps:
            logger.info(f"\n📋 Validating: {step_name}")
            logger.info("-" * 40)
            
            try:
                result = validation_func()
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ Validation step '{step_name}' failed with exception: {e}")
                logger.error(traceback.format_exc())
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for r in self.validation_results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"⚠️  Warnings: {len(self.warnings)}")
        
        if failed_tests > 0:
            logger.info("\n🚨 FAILED TESTS:")
            for error in self.errors:
                logger.error(f"  • {error}")
        
        if self.warnings:
            logger.info("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  • {warning}")
        
        if failed_tests == 0:
            logger.info("\n🎉 ALL VALIDATIONS PASSED!")
            logger.info("✅ Task 3 implementation is valid and ready for deployment")
        else:
            logger.info(f"\n❌ {failed_tests} validation(s) failed")
            logger.info("🔧 Please address the failed tests before deployment")
        
        return failed_tests == 0


def main():
    """Main validation function."""
    try:
        validator = Task3Validator()
        success = validator.run_validation()
        validator.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Validation script failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()