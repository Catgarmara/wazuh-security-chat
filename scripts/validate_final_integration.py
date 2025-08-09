#!/usr/bin/env python3
"""
Final Integration Validation - Static Analysis

This script performs static validation of the codebase to ensure
the embedded AI integration is complete and properly configured.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import importlib.util
import ast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StaticIntegrationValidator:
    """Static validation of embedded AI integration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.validation_results = {}
        self.errors = []
        
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all static validations"""
        logger.info("Starting static integration validation...")
        
        validations = [
            self.validate_service_factory_integration,
            self.validate_external_dependencies_removed,
            self.validate_configuration_cleanup,
            self.validate_docker_configuration,
            self.validate_api_consolidation,
            self.validate_service_imports,
            self.validate_embedded_ai_service,
            self.validate_requirements_file,
            self.validate_backup_scripts,
            self.validate_health_checks
        ]
        
        for validation in validations:
            validation_name = validation.__name__
            logger.info(f"Running validation: {validation_name}")
            
            try:
                result = validation()
                self.validation_results[validation_name] = {
                    'status': 'PASS' if result['success'] else 'FAIL',
                    'details': result
                }
                logger.info(f"Validation {validation_name}: {'PASS' if result['success'] else 'FAIL'}")
                
            except Exception as e:
                error_msg = f"Validation {validation_name} failed: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                self.validation_results[validation_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        return self.generate_report()
    
    def validate_service_factory_integration(self) -> Dict[str, Any]:
        """Validate AIServiceFactory integration - Requirement 1.6"""
        result = {
            'success': False,
            'factory_exists': False,
            'returns_embedded_service': False,
            'proper_imports': False
        }
        
        try:
            factory_path = self.project_root / 'core' / 'ai_factory.py'
            
            if factory_path.exists():
                result['factory_exists'] = True
                
                content = factory_path.read_text()
                
                # Check for EmbeddedAIService import
                if 'EmbeddedAIService' in content:
                    result['proper_imports'] = True
                
                # Check for get_ai_service method returning EmbeddedAIService
                if 'def get_ai_service' in content and 'EmbeddedAIService' in content:
                    result['returns_embedded_service'] = True
                
                result['success'] = all([
                    result['factory_exists'],
                    result['returns_embedded_service'],
                    result['proper_imports']
                ])
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_external_dependencies_removed(self) -> Dict[str, Any]:
        """Validate external AI dependencies are removed - Requirement 7.1-7.7"""
        result = {
            'success': False,
            'no_external_services': True,
            'no_external_imports': True,
            'clean_config': True,
            'external_services_found': [],
            'external_imports_found': []
        }
        
        try:
            # Check for external service files
            services_dir = self.project_root / 'services'
            external_services = ['ai_service.py', 'ollama_service.py', 'openai_service.py']
            
            for service_file in external_services:
                service_path = services_dir / service_file
                if service_path.exists():
                    result['external_services_found'].append(service_file)
                    result['no_external_services'] = False
            
            # Check for external imports in key files
            key_files = [
                'services/__init__.py',
                'core/config.py',
                'app/main.py'
            ]
            
            external_patterns = [
                'ollama',
                'openai',
                'anthropic',
                'ai_service',
                'AIService'
            ]
            
            for file_path in key_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    content = full_path.read_text().lower()
                    for pattern in external_patterns:
                        if pattern.lower() in content:
                            result['external_imports_found'].append(f"{file_path}: {pattern}")
                            result['no_external_imports'] = False
            
            # Check configuration
            config_path = self.project_root / 'core' / 'config.py'
            if config_path.exists():
                config_content = config_path.read_text()
                external_config_patterns = ['ollama', 'openai', 'anthropic']
                
                for pattern in external_config_patterns:
                    if pattern.lower() in config_content.lower():
                        result['clean_config'] = False
                        break
            
            result['success'] = all([
                result['no_external_services'],
                result['no_external_imports'],
                result['clean_config']
            ])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_configuration_cleanup(self) -> Dict[str, Any]:
        """Validate configuration cleanup - Requirement 4.7"""
        result = {
            'success': False,
            'embedded_ai_settings_present': False,
            'no_external_settings': True,
            'app_settings_updated': False
        }
        
        try:
            config_path = self.project_root / 'core' / 'config.py'
            
            if config_path.exists():
                content = config_path.read_text()
                
                # Check for EmbeddedAISettings
                if 'EmbeddedAISettings' in content:
                    result['embedded_ai_settings_present'] = True
                
                # Check AppSettings uses EmbeddedAISettings
                if 'embedded_ai' in content.lower() and 'EmbeddedAISettings' in content:
                    result['app_settings_updated'] = True
                
                # Check no external AI settings remain
                external_settings = ['ollama', 'openai', 'anthropic']
                for setting in external_settings:
                    if f'{setting}_' in content.lower() or f'{setting}settings' in content.lower():
                        result['no_external_settings'] = False
                        break
                
                result['success'] = all([
                    result['embedded_ai_settings_present'],
                    result['no_external_settings'],
                    result['app_settings_updated']
                ])
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_docker_configuration(self) -> Dict[str, Any]:
        """Validate Docker configuration - Requirements 4.1, 4.2, 4.6"""
        result = {
            'success': False,
            'dockerfile_has_llama_cpp': False,
            'compose_self_contained': True,
            'prod_compose_clean': True,
            'external_services_in_compose': []
        }
        
        try:
            # Check Dockerfile
            dockerfile_path = self.project_root / 'Dockerfile'
            if dockerfile_path.exists():
                dockerfile_content = dockerfile_path.read_text()
                if 'llama-cpp-python' in dockerfile_content:
                    result['dockerfile_has_llama_cpp'] = True
            
            # Check docker-compose.yml
            compose_path = self.project_root / 'docker-compose.yml'
            if compose_path.exists():
                compose_content = compose_path.read_text()
                external_services = ['ollama', 'external-ai']
                
                for service in external_services:
                    if service in compose_content.lower():
                        result['external_services_in_compose'].append(f"docker-compose.yml: {service}")
                        result['compose_self_contained'] = False
            
            # Check docker-compose.prod.yml
            prod_compose_path = self.project_root / 'docker-compose.prod.yml'
            if prod_compose_path.exists():
                prod_compose_content = prod_compose_path.read_text()
                external_services = ['ollama', 'external-ai']
                
                for service in external_services:
                    if service in prod_compose_content.lower():
                        result['external_services_in_compose'].append(f"docker-compose.prod.yml: {service}")
                        result['prod_compose_clean'] = False
            
            result['success'] = all([
                result['dockerfile_has_llama_cpp'],
                result['compose_self_contained'],
                result['prod_compose_clean']
            ])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_api_consolidation(self) -> Dict[str, Any]:
        """Validate API consolidation - Requirement 2.1"""
        result = {
            'success': False,
            'main_ai_api_exists': False,
            'no_separate_embedded_api': True,
            'consolidated_endpoints': False
        }
        
        try:
            # Check main AI API
            ai_api_path = self.project_root / 'api' / 'ai.py'
            if ai_api_path.exists():
                result['main_ai_api_exists'] = True
                
                content = ai_api_path.read_text()
                # Check for embedded AI endpoints
                if 'models' in content and 'query' in content:
                    result['consolidated_endpoints'] = True
            
            # Check no separate embedded AI API
            embedded_api_path = self.project_root / 'api' / 'embedded_ai.py'
            if embedded_api_path.exists():
                # Check if it's still being used
                main_app_path = self.project_root / 'app' / 'main.py'
                if main_app_path.exists():
                    main_content = main_app_path.read_text()
                    if 'embedded_ai' in main_content.lower():
                        result['no_separate_embedded_api'] = False
            
            result['success'] = all([
                result['main_ai_api_exists'],
                result['no_separate_embedded_api'],
                result['consolidated_endpoints']
            ])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_service_imports(self) -> Dict[str, Any]:
        """Validate service imports use EmbeddedAIService - Requirement 2.6"""
        result = {
            'success': False,
            'services_init_updated': False,
            'chat_service_updated': False,
            'websocket_updated': False
        }
        
        try:
            # Check services/__init__.py
            services_init_path = self.project_root / 'services' / '__init__.py'
            if services_init_path.exists():
                content = services_init_path.read_text()
                if 'EmbeddedAIService' in content and 'get_ai_service' in content:
                    result['services_init_updated'] = True
            
            # Check chat service
            chat_service_path = self.project_root / 'services' / 'chat_service.py'
            if chat_service_path.exists():
                content = chat_service_path.read_text()
                if 'EmbeddedAIService' in content or 'get_ai_service' in content:
                    result['chat_service_updated'] = True
            
            # Check WebSocket
            websocket_path = self.project_root / 'api' / 'websocket.py'
            if websocket_path.exists():
                content = websocket_path.read_text()
                if 'EmbeddedAIService' in content or 'get_ai_service' in content:
                    result['websocket_updated'] = True
            
            result['success'] = all([
                result['services_init_updated'],
                result['chat_service_updated'],
                result['websocket_updated']
            ])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_embedded_ai_service(self) -> Dict[str, Any]:
        """Validate EmbeddedAIService implementation"""
        result = {
            'success': False,
            'service_exists': False,
            'has_required_methods': False,
            'proper_imports': False,
            'missing_methods': []
        }
        
        try:
            service_path = self.project_root / 'services' / 'embedded_ai_service.py'
            
            if service_path.exists():
                result['service_exists'] = True
                
                content = service_path.read_text()
                
                # Check for required imports
                required_imports = ['llama_cpp', 'huggingface_hub']
                import_count = sum(1 for imp in required_imports if imp in content)
                result['proper_imports'] = import_count >= 1
                
                # Check for required methods
                required_methods = [
                    'generate_response',
                    'list_available_models',
                    'load_model',
                    'get_service_health',
                    'process_query'
                ]
                
                found_methods = []
                for method in required_methods:
                    if f'def {method}' in content or f'async def {method}' in content:
                        found_methods.append(method)
                    else:
                        result['missing_methods'].append(method)
                
                result['has_required_methods'] = len(found_methods) >= len(required_methods) * 0.8
                result['found_methods'] = found_methods
                
                result['success'] = all([
                    result['service_exists'],
                    result['has_required_methods'],
                    result['proper_imports']
                ])
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_requirements_file(self) -> Dict[str, Any]:
        """Validate requirements.txt has embedded AI dependencies"""
        result = {
            'success': False,
            'has_llama_cpp': False,
            'has_transformers': False,
            'no_external_ai_deps': True,
            'external_deps_found': []
        }
        
        try:
            requirements_path = self.project_root / 'requirements.txt'
            
            if requirements_path.exists():
                content = requirements_path.read_text().lower()
                
                # Check for required dependencies
                if 'llama-cpp-python' in content:
                    result['has_llama_cpp'] = True
                
                if 'transformers' in content or 'sentence-transformers' in content:
                    result['has_transformers'] = True
                
                # Check for external AI dependencies that should be removed
                external_deps = ['ollama', 'openai', 'anthropic']
                for dep in external_deps:
                    if dep in content:
                        result['external_deps_found'].append(dep)
                        result['no_external_ai_deps'] = False
                
                result['success'] = all([
                    result['has_llama_cpp'],
                    result['no_external_ai_deps']
                ])
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_backup_scripts(self) -> Dict[str, Any]:
        """Validate backup scripts reference only embedded AI - Requirement 7.5"""
        result = {
            'success': False,
            'backup_script_clean': True,
            'deploy_script_clean': True,
            'external_references': []
        }
        
        try:
            # Check backup script
            backup_path = self.project_root / 'scripts' / 'backup.py'
            if backup_path.exists():
                content = backup_path.read_text()
                external_refs = ['ollama', 'openai', 'anthropic']
                
                for ref in external_refs:
                    if ref.lower() in content.lower():
                        result['external_references'].append(f"backup.py: {ref}")
                        result['backup_script_clean'] = False
            
            # Check deploy script
            deploy_path = self.project_root / 'scripts' / 'deploy.py'
            if deploy_path.exists():
                content = deploy_path.read_text()
                external_refs = ['ollama', 'openai', 'anthropic']
                
                for ref in external_refs:
                    if ref.lower() in content.lower():
                        result['external_references'].append(f"deploy.py: {ref}")
                        result['deploy_script_clean'] = False
            
            result['success'] = all([
                result['backup_script_clean'],
                result['deploy_script_clean']
            ])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_health_checks(self) -> Dict[str, Any]:
        """Validate health checks monitor only embedded components"""
        result = {
            'success': False,
            'health_module_exists': False,
            'monitors_embedded_ai': False,
            'no_external_monitoring': True
        }
        
        try:
            health_path = self.project_root / 'core' / 'health.py'
            
            if health_path.exists():
                result['health_module_exists'] = True
                
                content = health_path.read_text()
                
                # Check for embedded AI monitoring
                if 'embedded' in content.lower() or 'EmbeddedAIService' in content:
                    result['monitors_embedded_ai'] = True
                
                # Check no external service monitoring
                external_services = ['ollama', 'openai', 'anthropic']
                for service in external_services:
                    if service.lower() in content.lower():
                        result['no_external_monitoring'] = False
                        break
                
                result['success'] = all([
                    result['health_module_exists'],
                    result['monitors_embedded_ai'],
                    result['no_external_monitoring']
                ])
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        
        # Calculate statistics
        total_validations = len(self.validation_results)
        passed = sum(1 for result in self.validation_results.values() 
                    if result['status'] == 'PASS')
        failed = sum(1 for result in self.validation_results.values() 
                    if result['status'] == 'FAIL')
        errors = sum(1 for result in self.validation_results.values() 
                    if result['status'] == 'ERROR')
        
        # Determine critical validations
        critical_validations = [
            'validate_service_factory_integration',
            'validate_external_dependencies_removed',
            'validate_embedded_ai_service',
            'validate_requirements_file'
        ]
        
        critical_passed = all(
            self.validation_results.get(validation, {}).get('status') == 'PASS'
            for validation in critical_validations
        )
        
        overall_status = 'PASS' if critical_passed and failed == 0 else 'FAIL'
        
        report = {
            'validation_summary': {
                'overall_status': overall_status,
                'total_validations': total_validations,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'success_rate': f"{(passed/total_validations)*100:.1f}%" if total_validations > 0 else "0%"
            },
            'critical_validations_status': {
                validation: self.validation_results.get(validation, {}).get('status', 'NOT_RUN')
                for validation in critical_validations
            },
            'detailed_results': self.validation_results,
            'errors': self.errors,
            'recommendations': self.generate_recommendations(),
            'next_steps': self.generate_next_steps(overall_status)
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check specific failures
        if self.validation_results.get('validate_external_dependencies_removed', {}).get('status') != 'PASS':
            recommendations.append("Remove all external AI service dependencies and references")
        
        if self.validation_results.get('validate_service_factory_integration', {}).get('status') != 'PASS':
            recommendations.append("Ensure AIServiceFactory properly returns EmbeddedAIService")
        
        if self.validation_results.get('validate_embedded_ai_service', {}).get('status') != 'PASS':
            recommendations.append("Complete EmbeddedAIService implementation with all required methods")
        
        if self.validation_results.get('validate_docker_configuration', {}).get('status') != 'PASS':
            recommendations.append("Update Docker configuration for self-contained deployment")
        
        if not recommendations:
            recommendations.append("Static validation passed - proceed with runtime testing")
        
        return recommendations
    
    def generate_next_steps(self, overall_status: str) -> List[str]:
        """Generate next steps based on validation results"""
        if overall_status == 'PASS':
            return [
                "Static validation completed successfully",
                "Run runtime integration tests with test_final_integration_validation.py",
                "Start application and verify all endpoints work",
                "Perform load testing if needed"
            ]
        else:
            return [
                "Fix failed validations before proceeding",
                "Review detailed results for specific issues",
                "Re-run static validation after fixes",
                "Then proceed with runtime testing"
            ]

def main():
    """Main execution function"""
    validator = StaticIntegrationValidator()
    
    try:
        # Run all static validations
        report = validator.run_all_validations()
        
        # Save report
        report_file = Path('STATIC_INTEGRATION_VALIDATION_REPORT.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*80)
        print("STATIC INTEGRATION VALIDATION REPORT")
        print("="*80)
        
        summary = report['validation_summary']
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Validations Run: {summary['total_validations']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']}")
        
        print("\nCritical Validations:")
        for validation, status in report['critical_validations_status'].items():
            print(f"  {validation}: {status}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        print("\nNext Steps:")
        for step in report['next_steps']:
            print(f"  - {step}")
        
        print(f"\nDetailed report saved to: {report_file}")
        print("="*80)
        
        # Exit with appropriate code
        sys.exit(0 if summary['overall_status'] == 'PASS' else 1)
        
    except Exception as e:
        logger.error(f"Static validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()