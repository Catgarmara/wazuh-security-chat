#!/usr/bin/env python3
"""
Run Final Integration Validation

This script runs comprehensive validation of the security appliance
to ensure all requirements are met for task 16.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalValidationRunner:
    """Run comprehensive final validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.validation_results = {}
        
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation phases"""
        logger.info("Starting comprehensive final validation...")
        
        # Phase 1: Static validation
        logger.info("Phase 1: Running static validation...")
        static_result = self.run_static_validation()
        self.validation_results['static_validation'] = static_result
        
        # Phase 2: Application startup test (if static passes)
        if static_result.get('overall_status') == 'PASS':
            logger.info("Phase 2: Testing application startup...")
            startup_result = self.run_startup_test()
            self.validation_results['startup_test'] = startup_result
        else:
            logger.warning("Skipping startup test due to static validation failures")
            self.validation_results['startup_test'] = {'status': 'SKIPPED', 'reason': 'Static validation failed'}
        
        # Phase 3: Integration test (if startup passes)
        if (self.validation_results.get('startup_test', {}).get('summary', {}).get('overall_status') == 'PASS'):
            logger.info("Phase 3: Running integration tests...")
            integration_result = self.run_integration_test()
            self.validation_results['integration_test'] = integration_result
        else:
            logger.warning("Skipping integration test due to startup failures")
            self.validation_results['integration_test'] = {'status': 'SKIPPED', 'reason': 'Startup test failed'}
        
        return self.generate_final_report()
    
    def run_static_validation(self) -> Dict[str, Any]:
        """Run static code validation"""
        try:
            result = subprocess.run([
                sys.executable, 'scripts/validate_final_integration.py'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Try to load the JSON report
            report_file = self.project_root / 'STATIC_INTEGRATION_VALIDATION_REPORT.json'
            if report_file.exists():
                with open(report_file, 'r') as f:
                    static_data = json.load(f)
                return static_data
            else:
                return {
                    'overall_status': 'FAIL',
                    'error': 'Static validation report not generated',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except Exception as e:
            return {
                'overall_status': 'ERROR',
                'error': str(e)
            }
    
    def run_startup_test(self) -> Dict[str, Any]:
        """Run application startup test"""
        try:
            result = subprocess.run([
                sys.executable, 'scripts/test_appliance_startup.py'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Try to load the JSON report
            report_file = self.project_root / 'APPLIANCE_STARTUP_TEST_REPORT.json'
            if report_file.exists():
                with open(report_file, 'r') as f:
                    startup_data = json.load(f)
                return startup_data
            else:
                return {
                    'summary': {'overall_status': 'FAIL'},
                    'error': 'Startup test report not generated',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except Exception as e:
            return {
                'summary': {'overall_status': 'ERROR'},
                'error': str(e)
            }
    
    def run_integration_test(self) -> Dict[str, Any]:
        """Run comprehensive integration test"""
        try:
            result = subprocess.run([
                sys.executable, 'scripts/test_final_integration_validation.py'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Try to load the JSON report
            report_file = self.project_root / 'FINAL_INTEGRATION_VALIDATION_REPORT.json'
            if report_file.exists():
                with open(report_file, 'r') as f:
                    integration_data = json.load(f)
                return integration_data
            else:
                return {
                    'validation_summary': {'overall_status': 'FAIL'},
                    'error': 'Integration test report not generated',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except Exception as e:
            return {
                'validation_summary': {'overall_status': 'ERROR'},
                'error': str(e)
            }
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        
        # Extract status from each phase
        static_status = self.validation_results.get('static_validation', {}).get('validation_summary', {}).get('overall_status', 'NOT_RUN')
        startup_status = self.validation_results.get('startup_test', {}).get('summary', {}).get('overall_status', 'NOT_RUN')
        integration_status = self.validation_results.get('integration_test', {}).get('validation_summary', {}).get('overall_status', 'NOT_RUN')
        
        # Determine overall validation status
        if static_status == 'PASS' and startup_status == 'PASS' and integration_status == 'PASS':
            overall_status = 'PASS'
        elif static_status == 'PASS' and startup_status == 'PASS':
            overall_status = 'PARTIAL_PASS'
        else:
            overall_status = 'FAIL'
        
        # Generate requirements compliance report
        requirements_compliance = self.assess_requirements_compliance()
        
        report = {
            'final_validation_summary': {
                'overall_status': overall_status,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'validation_phases': {
                    'static_validation': static_status,
                    'startup_test': startup_status,
                    'integration_test': integration_status
                }
            },
            'requirements_compliance': requirements_compliance,
            'detailed_phase_results': self.validation_results,
            'final_recommendations': self.generate_final_recommendations(overall_status),
            'deployment_readiness': self.assess_deployment_readiness(overall_status)
        }
        
        return report
    
    def assess_requirements_compliance(self) -> Dict[str, Any]:
        """Assess compliance with task 16 requirements"""
        
        requirements = {
            '1.1_appliance_startup': 'NOT_ASSESSED',
            '1.4_embedded_ai_sole_provider': 'NOT_ASSESSED',
            '2.1_natural_language_queries': 'NOT_ASSESSED',
            '2.2_websocket_integration': 'NOT_ASSESSED',
            '2.3_security_log_analysis': 'NOT_ASSESSED',
            '5.1_siem_query_translation': 'NOT_ASSESSED',
            '5.2_threat_hunting': 'NOT_ASSESSED',
            '5.3_security_analysis': 'NOT_ASSESSED',
            '5.4_mitre_attack_mapping': 'NOT_ASSESSED',
            '5.5_executive_summaries': 'NOT_ASSESSED',
            '5.6_compliance_reporting': 'NOT_ASSESSED',
            '7.6_self_containment': 'NOT_ASSESSED'
        }
        
        # Assess based on validation results
        static_results = self.validation_results.get('static_validation', {}).get('detailed_results', {})
        startup_results = self.validation_results.get('startup_test', {}).get('detailed_results', {})
        integration_results = self.validation_results.get('integration_test', {}).get('detailed_results', {})
        
        # Map validation results to requirements
        if static_results.get('validate_service_factory_integration', {}).get('status') == 'PASS':
            requirements['1.4_embedded_ai_sole_provider'] = 'COMPLIANT'
        
        if static_results.get('validate_external_dependencies_removed', {}).get('status') == 'PASS':
            requirements['7.6_self_containment'] = 'COMPLIANT'
        
        if startup_results.get('test_health_endpoint', {}).get('status') == 'PASS':
            requirements['1.1_appliance_startup'] = 'COMPLIANT'
        
        if integration_results.get('test_natural_language_query_processing', {}).get('status') == 'PASS':
            requirements['2.1_natural_language_queries'] = 'COMPLIANT'
        
        if integration_results.get('test_websocket_integration', {}).get('status') == 'PASS':
            requirements['2.2_websocket_integration'] = 'COMPLIANT'
        
        if integration_results.get('test_siem_query_translation', {}).get('status') == 'PASS':
            requirements['5.1_siem_query_translation'] = 'COMPLIANT'
        
        if integration_results.get('test_threat_hunting_capabilities', {}).get('status') == 'PASS':
            requirements['5.2_threat_hunting'] = 'COMPLIANT'
        
        if integration_results.get('test_security_analysis_features', {}).get('status') == 'PASS':
            requirements['5.3_security_analysis'] = 'COMPLIANT'
        
        # Calculate compliance percentage
        total_requirements = len(requirements)
        compliant_requirements = sum(1 for status in requirements.values() if status == 'COMPLIANT')
        compliance_percentage = (compliant_requirements / total_requirements) * 100
        
        return {
            'individual_requirements': requirements,
            'compliance_summary': {
                'total_requirements': total_requirements,
                'compliant': compliant_requirements,
                'compliance_percentage': f"{compliance_percentage:.1f}%"
            }
        }
    
    def generate_final_recommendations(self, overall_status: str) -> list:
        """Generate final recommendations"""
        recommendations = []
        
        if overall_status == 'PASS':
            recommendations.extend([
                "✅ All validation phases completed successfully",
                "✅ Security appliance is ready for production deployment",
                "✅ Embedded AI integration is fully functional",
                "✅ All critical requirements are met",
                "📋 Consider running load testing for production readiness",
                "📋 Update deployment documentation with final configuration"
            ])
        elif overall_status == 'PARTIAL_PASS':
            recommendations.extend([
                "⚠️ Basic functionality validated but integration tests incomplete",
                "🔧 Address any remaining integration issues",
                "🔧 Complete comprehensive testing before production deployment",
                "📋 Review integration test results for specific issues"
            ])
        else:
            recommendations.extend([
                "❌ Critical validation failures detected",
                "🔧 Address static validation issues first",
                "🔧 Ensure application starts correctly",
                "🔧 Fix embedded AI service integration",
                "📋 Re-run validation after fixes"
            ])
        
        return recommendations
    
    def assess_deployment_readiness(self, overall_status: str) -> Dict[str, Any]:
        """Assess deployment readiness"""
        
        readiness_criteria = {
            'static_validation_passed': self.validation_results.get('static_validation', {}).get('validation_summary', {}).get('overall_status') == 'PASS',
            'application_starts': self.validation_results.get('startup_test', {}).get('summary', {}).get('overall_status') == 'PASS',
            'embedded_ai_functional': False,
            'self_contained': False,
            'basic_queries_work': False
        }
        
        # Check embedded AI functionality
        startup_results = self.validation_results.get('startup_test', {}).get('detailed_results', {})
        if startup_results.get('test_ai_service_availability', {}).get('status') == 'PASS':
            readiness_criteria['embedded_ai_functional'] = True
        
        # Check self-containment
        static_results = self.validation_results.get('static_validation', {}).get('detailed_results', {})
        if static_results.get('validate_external_dependencies_removed', {}).get('status') == 'PASS':
            readiness_criteria['self_contained'] = True
        
        # Check basic query functionality
        if startup_results.get('test_basic_query_processing', {}).get('status') == 'PASS':
            readiness_criteria['basic_queries_work'] = True
        
        # Calculate readiness score
        total_criteria = len(readiness_criteria)
        met_criteria = sum(1 for met in readiness_criteria.values() if met)
        readiness_score = (met_criteria / total_criteria) * 100
        
        # Determine readiness level
        if readiness_score >= 90:
            readiness_level = 'PRODUCTION_READY'
        elif readiness_score >= 70:
            readiness_level = 'STAGING_READY'
        elif readiness_score >= 50:
            readiness_level = 'DEVELOPMENT_READY'
        else:
            readiness_level = 'NOT_READY'
        
        return {
            'readiness_level': readiness_level,
            'readiness_score': f"{readiness_score:.1f}%",
            'criteria_met': readiness_criteria,
            'critical_blockers': self.identify_critical_blockers(readiness_criteria)
        }
    
    def identify_critical_blockers(self, criteria: Dict[str, bool]) -> list:
        """Identify critical blockers for deployment"""
        blockers = []
        
        if not criteria['static_validation_passed']:
            blockers.append("Static validation failures must be resolved")
        
        if not criteria['application_starts']:
            blockers.append("Application startup issues must be fixed")
        
        if not criteria['embedded_ai_functional']:
            blockers.append("Embedded AI service must be functional")
        
        if not criteria['self_contained']:
            blockers.append("External dependencies must be removed for self-containment")
        
        return blockers

def main():
    """Main execution function"""
    runner = FinalValidationRunner()
    
    try:
        # Run comprehensive validation
        report = runner.run_all_validations()
        
        # Save final report
        report_file = Path('FINAL_VALIDATION_REPORT.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print comprehensive summary
        print("\n" + "="*80)
        print("FINAL SECURITY APPLIANCE INTEGRATION VALIDATION")
        print("="*80)
        
        summary = report['final_validation_summary']
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Validation Timestamp: {summary['timestamp']}")
        
        print("\nValidation Phases:")
        for phase, status in summary['validation_phases'].items():
            print(f"  {phase}: {status}")
        
        print("\nRequirements Compliance:")
        compliance = report['requirements_compliance']['compliance_summary']
        print(f"  Compliance Rate: {compliance['compliance_percentage']}")
        print(f"  Compliant Requirements: {compliance['compliant']}/{compliance['total_requirements']}")
        
        print("\nDeployment Readiness:")
        readiness = report['deployment_readiness']
        print(f"  Readiness Level: {readiness['readiness_level']}")
        print(f"  Readiness Score: {readiness['readiness_score']}")
        
        if readiness['critical_blockers']:
            print("\nCritical Blockers:")
            for blocker in readiness['critical_blockers']:
                print(f"  ❌ {blocker}")
        
        print("\nFinal Recommendations:")
        for rec in report['final_recommendations']:
            print(f"  {rec}")
        
        print(f"\nComprehensive report saved to: {report_file}")
        print("="*80)
        
        # Exit with appropriate code
        exit_code = 0 if summary['overall_status'] in ['PASS', 'PARTIAL_PASS'] else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Final validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()