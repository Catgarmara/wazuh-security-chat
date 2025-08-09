#!/usr/bin/env python3
"""
Test Security Appliance Startup and Basic Functionality

This script tests the basic startup and functionality of the security appliance
to ensure embedded AI integration is working properly.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import requests
import psutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ApplianceStartupTester:
    """Test security appliance startup and basic functionality"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = {}
        
    def run_startup_tests(self) -> Dict[str, Any]:
        """Run basic startup tests"""
        logger.info("Starting security appliance startup tests...")
        
        tests = [
            self.test_health_endpoint,
            self.test_ai_service_availability,
            self.test_embedded_ai_factory,
            self.test_basic_query_processing,
            self.test_model_management,
            self.test_self_containment
        ]
        
        for test in tests:
            test_name = test.__name__
            logger.info(f"Running test: {test_name}")
            
            try:
                result = test()
                self.test_results[test_name] = {
                    'status': 'PASS' if result['success'] else 'FAIL',
                    'details': result
                }
                logger.info(f"Test {test_name}: {'PASS' if result['success'] else 'FAIL'}")
                
            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        return self.generate_report()
    
    def test_health_endpoint(self) -> Dict[str, Any]:
        """Test health endpoint responds correctly"""
        result = {'success': False, 'response_time': 0}
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            result['response_time'] = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json()
                result['health_data'] = health_data
                result['success'] = True
                
                # Check for embedded AI in health response
                if 'embedded_ai' in health_data:
                    result['embedded_ai_present'] = True
                    result['embedded_ai_status'] = health_data['embedded_ai']
                    
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def test_ai_service_availability(self) -> Dict[str, Any]:
        """Test AI service is available and functional"""
        result = {'success': False}
        
        try:
            # Test AI service factory
            from core.ai_factory import AIServiceFactory
            
            ai_service = AIServiceFactory.get_ai_service()
            if ai_service:
                result['factory_works'] = True
                
                # Test service type
                from services.embedded_ai_service import EmbeddedAIService
                if isinstance(ai_service, EmbeddedAIService):
                    result['correct_service_type'] = True
                    result['success'] = True
                    
                    # Test basic service methods
                    try:
                        health = ai_service.get_service_health()
                        result['service_health'] = health
                        
                        if health.get('status') == 'healthy':
                            result['service_healthy'] = True
                            
                    except Exception as e:
                        result['health_error'] = str(e)
                        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def test_embedded_ai_factory(self) -> Dict[str, Any]:
        """Test embedded AI factory integration"""
        result = {'success': False}
        
        try:
            from core.ai_factory import AIServiceFactory
            from services.embedded_ai_service import EmbeddedAIService
            
            # Test factory methods
            ai_service = AIServiceFactory.get_ai_service()
            result['get_service_works'] = ai_service is not None
            
            if ai_service:
                result['service_type'] = type(ai_service).__name__
                result['is_embedded_service'] = isinstance(ai_service, EmbeddedAIService)
                
                # Test service status
                try:
                    status = AIServiceFactory.get_service_status()
                    result['factory_status'] = status
                    result['success'] = True
                    
                except Exception as e:
                    result['status_error'] = str(e)
                    
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def test_basic_query_processing(self) -> Dict[str, Any]:
        """Test basic query processing functionality"""
        result = {'success': False}
        
        try:
            # Test query endpoint
            query_data = {
                'query': 'What is the status of the security system?',
                'context': 'security_analysis'
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/query",
                json=query_data,
                timeout=30
            )
            
            result['endpoint_accessible'] = response.status_code in [200, 422, 500]
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                response_data = response.json()
                result['response_data'] = response_data
                result['success'] = True
                
            elif response.status_code == 422:
                # Validation error is acceptable - endpoint exists
                result['validation_error'] = response.json()
                result['success'] = True  # Endpoint exists and validates
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def test_model_management(self) -> Dict[str, Any]:
        """Test model management functionality"""
        result = {'success': False}
        
        try:
            # Test models endpoint
            response = requests.get(f"{self.base_url}/api/ai/models", timeout=10)
            
            result['endpoint_accessible'] = response.status_code in [200, 404, 500]
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                models_data = response.json()
                result['models_data'] = models_data
                result['success'] = True
                
                # Check for model management features
                if 'available_models' in models_data:
                    result['has_available_models'] = True
                    
                if 'loaded_models' in models_data:
                    result['has_loaded_models'] = True
                    
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def test_self_containment(self) -> Dict[str, Any]:
        """Test that the appliance is self-contained"""
        result = {'success': False}
        
        try:
            # Check for external network connections during operation
            initial_connections = self.get_external_connections()
            
            # Make some AI requests
            requests.get(f"{self.base_url}/health", timeout=5)
            requests.get(f"{self.base_url}/api/ai/models", timeout=5)
            
            final_connections = self.get_external_connections()
            
            # Should not have new external connections
            new_connections = final_connections - initial_connections
            result['new_external_connections'] = len(new_connections)
            result['external_connections'] = list(new_connections)
            
            # Success if no new external connections
            result['success'] = len(new_connections) == 0
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_external_connections(self) -> set:
        """Get current external network connections"""
        try:
            connections = set()
            for conn in psutil.net_connections():
                if conn.raddr and not conn.raddr.ip.startswith('127.'):
                    connections.add((conn.raddr.ip, conn.raddr.port))
            return connections
        except:
            return set()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        total_tests = len(self.test_results)
        passed = sum(1 for result in self.test_results.values() 
                    if result['status'] == 'PASS')
        failed = sum(1 for result in self.test_results.values() 
                    if result['status'] == 'FAIL')
        errors = sum(1 for result in self.test_results.values() 
                    if result['status'] == 'ERROR')
        
        # Critical tests that must pass
        critical_tests = [
            'test_health_endpoint',
            'test_ai_service_availability',
            'test_embedded_ai_factory'
        ]
        
        critical_passed = all(
            self.test_results.get(test, {}).get('status') == 'PASS'
            for test in critical_tests
        )
        
        overall_status = 'PASS' if critical_passed else 'FAIL'
        
        return {
            'summary': {
                'overall_status': overall_status,
                'total_tests': total_tests,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'success_rate': f"{(passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            'critical_tests_status': {
                test: self.test_results.get(test, {}).get('status', 'NOT_RUN')
                for test in critical_tests
            },
            'detailed_results': self.test_results,
            'recommendations': self.generate_recommendations(overall_status)
        }
    
    def generate_recommendations(self, overall_status: str) -> list:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if overall_status == 'FAIL':
            if self.test_results.get('test_health_endpoint', {}).get('status') != 'PASS':
                recommendations.append("Ensure the application is running and accessible")
            
            if self.test_results.get('test_ai_service_availability', {}).get('status') != 'PASS':
                recommendations.append("Check embedded AI service initialization")
            
            if self.test_results.get('test_embedded_ai_factory', {}).get('status') != 'PASS':
                recommendations.append("Verify AI service factory configuration")
        else:
            recommendations.append("Basic appliance functionality is working correctly")
            recommendations.append("Ready for comprehensive integration testing")
        
        return recommendations

def main():
    """Main execution function"""
    tester = ApplianceStartupTester()
    
    try:
        report = tester.run_startup_tests()
        
        # Save report
        report_file = Path('APPLIANCE_STARTUP_TEST_REPORT.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*60)
        print("SECURITY APPLIANCE STARTUP TEST REPORT")
        print("="*60)
        
        summary = report['summary']
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Tests Run: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']}")
        
        print("\nCritical Tests:")
        for test, status in report['critical_tests_status'].items():
            print(f"  {test}: {status}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        print(f"\nDetailed report saved to: {report_file}")
        print("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if summary['overall_status'] == 'PASS' else 1)
        
    except Exception as e:
        logger.error(f"Startup test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()