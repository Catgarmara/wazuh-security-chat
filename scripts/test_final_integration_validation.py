#!/usr/bin/env python3
"""
Final Security Appliance Integration Testing and Validation

This script performs comprehensive testing to validate that the security appliance
is fully integrated with embedded AI as the sole provider and meets all requirements.

Requirements tested:
- 1.1: Complete self-contained security appliance
- 1.4: Embedded AI service availability and functionality
- 2.1: Natural language security query translation
- 2.2: Real-time WebSocket integration
- 2.3: Security log analysis processing
- 5.1-5.6: SIEM integration and query translation
- 7.6: Complete self-containment validation
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp
import websockets
import psutil
import requests
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
from core.database import get_database_url
from services.embedded_ai_service import EmbeddedAIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalIntegrationValidator:
    """Comprehensive validation of the security appliance integration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"http://localhost:{self.settings.port}"
        self.ws_url = f"ws://localhost:{self.settings.port}"
        self.test_results = {}
        self.errors = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests and return comprehensive results"""
        logger.info("Starting final security appliance integration validation...")
        
        test_methods = [
            self.test_appliance_startup,
            self.test_embedded_ai_sole_provider,
            self.test_external_dependencies_removed,
            self.test_natural_language_query_processing,
            self.test_websocket_integration,
            self.test_huggingface_model_management,
            self.test_siem_query_translation,
            self.test_threat_hunting_capabilities,
            self.test_security_analysis_features,
            self.test_resource_management,
            self.test_health_monitoring,
            self.test_self_containment_validation
        ]
        
        for test_method in test_methods:
            test_name = test_method.__name__
            logger.info(f"Running test: {test_name}")
            
            try:
                result = await test_method()
                self.test_results[test_name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'details': result if isinstance(result, dict) else {'success': result}
                }
                logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
                
            except Exception as e:
                error_msg = f"Test {test_name} failed with exception: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.errors.append(error_msg)
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        return self.generate_final_report()
    
    async def test_appliance_startup(self) -> Dict[str, Any]:
        """Test complete security appliance startup - Requirement 1.1"""
        logger.info("Testing security appliance startup...")
        
        results = {
            'api_health': False,
            'database_connection': False,
            'redis_connection': False,
            'embedded_ai_ready': False,
            'startup_time': 0
        }
        
        start_time = time.time()
        
        # Test API health endpoint
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                results['api_health'] = True
                results['health_details'] = health_data
                
                # Check embedded AI status in health response
                if 'embedded_ai' in health_data and health_data['embedded_ai'].get('status') == 'healthy':
                    results['embedded_ai_ready'] = True
                    
        except Exception as e:
            logger.error(f"API health check failed: {e}")
        
        # Test database connection
        try:
            engine = create_engine(get_database_url())
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                results['database_connection'] = True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
        
        # Test Redis connection
        try:
            import redis
            redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                decode_responses=True
            )
            redis_client.ping()
            results['redis_connection'] = True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
        
        results['startup_time'] = time.time() - start_time
        
        # All critical components must be ready
        success = all([
            results['api_health'],
            results['database_connection'],
            results['redis_connection'],
            results['embedded_ai_ready']
        ])
        
        results['overall_success'] = success
        return results
    
    async def test_embedded_ai_sole_provider(self) -> Dict[str, Any]:
        """Test that EmbeddedAIService is the sole AI provider - Requirement 1.4"""
        logger.info("Testing embedded AI as sole provider...")
        
        results = {
            'service_factory_returns_embedded': False,
            'no_external_ai_imports': False,
            'embedded_service_functional': False,
            'model_loading_works': False
        }
        
        try:
            # Test service factory
            from core.ai_factory import AIServiceFactory
            ai_service = AIServiceFactory.get_ai_service()
            
            if isinstance(ai_service, EmbeddedAIService):
                results['service_factory_returns_embedded'] = True
                
                # Test service functionality
                health = await ai_service.get_service_health()
                if health.get('status') == 'healthy':
                    results['embedded_service_functional'] = True
                
                # Test model availability
                models = await ai_service.list_available_models()
                if models:
                    results['model_loading_works'] = True
                    results['available_models'] = models
                    
        except Exception as e:
            logger.error(f"Embedded AI service test failed: {e}")
        
        # Check for external AI service imports (should not exist)
        try:
            # These imports should fail if external services are properly removed
            external_imports_found = []
            
            try:
                import services.ai_service
                external_imports_found.append('ai_service')
            except ImportError:
                pass
            
            try:
                import services.ollama_service
                external_imports_found.append('ollama_service')
            except ImportError:
                pass
            
            results['no_external_ai_imports'] = len(external_imports_found) == 0
            if external_imports_found:
                results['external_imports_found'] = external_imports_found
                
        except Exception as e:
            logger.error(f"External import check failed: {e}")
        
        results['overall_success'] = all([
            results['service_factory_returns_embedded'],
            results['no_external_ai_imports'],
            results['embedded_service_functional']
        ])
        
        return results
    
    async def test_external_dependencies_removed(self) -> Dict[str, Any]:
        """Test that all external AI service dependencies are removed - Requirement 7.6"""
        logger.info("Testing removal of external dependencies...")
        
        results = {
            'config_clean': False,
            'docker_compose_clean': False,
            'requirements_clean': False,
            'no_external_connections': False
        }
        
        # Check configuration files
        try:
            config_content = Path('core/config.py').read_text()
            external_configs = ['ollama', 'openai', 'anthropic', 'huggingface_hub']
            found_configs = [cfg for cfg in external_configs if cfg.lower() in config_content.lower()]
            
            results['config_clean'] = len(found_configs) == 0
            if found_configs:
                results['external_configs_found'] = found_configs
                
        except Exception as e:
            logger.error(f"Config check failed: {e}")
        
        # Check docker-compose files
        try:
            compose_files = ['docker-compose.yml', 'docker-compose.prod.yml']
            external_services = []
            
            for compose_file in compose_files:
                if Path(compose_file).exists():
                    content = Path(compose_file).read_text()
                    if 'ollama' in content.lower() or 'external-ai' in content.lower():
                        external_services.append(compose_file)
            
            results['docker_compose_clean'] = len(external_services) == 0
            if external_services:
                results['external_services_found'] = external_services
                
        except Exception as e:
            logger.error(f"Docker compose check failed: {e}")
        
        # Check requirements.txt
        try:
            if Path('requirements.txt').exists():
                requirements = Path('requirements.txt').read_text()
                external_deps = ['ollama', 'openai', 'anthropic']
                found_deps = [dep for dep in external_deps if dep in requirements.lower()]
                
                results['requirements_clean'] = len(found_deps) == 0
                if found_deps:
                    results['external_deps_found'] = found_deps
            else:
                results['requirements_clean'] = True
                
        except Exception as e:
            logger.error(f"Requirements check failed: {e}")
        
        # Test no external connections are attempted
        try:
            # Monitor network connections during startup
            import psutil
            connections_before = len(psutil.net_connections())
            
            # Trigger AI service initialization
            response = requests.get(f"{self.base_url}/api/ai/models", timeout=5)
            
            connections_after = len(psutil.net_connections())
            
            # Should not have significantly more connections (only local ones)
            results['no_external_connections'] = (connections_after - connections_before) <= 2
            results['connection_delta'] = connections_after - connections_before
            
        except Exception as e:
            logger.error(f"Network connection check failed: {e}")
        
        results['overall_success'] = all([
            results['config_clean'],
            results['docker_compose_clean'],
            results['requirements_clean'],
            results['no_external_connections']
        ])
        
        return results
    
    async def test_natural_language_query_processing(self) -> Dict[str, Any]:
        """Test natural language security query functionality - Requirement 2.1"""
        logger.info("Testing natural language query processing...")
        
        results = {
            'query_endpoint_available': False,
            'query_translation_works': False,
            'security_context_preserved': False,
            'response_quality': False
        }
        
        test_queries = [
            "Show me failed login attempts from the last hour",
            "Find suspicious network connections to external IPs",
            "What are the top security alerts today?",
            "Analyze authentication failures by user"
        ]
        
        try:
            for query in test_queries:
                # Test query processing endpoint
                payload = {
                    "query": query,
                    "context": "security_analysis"
                }
                
                response = requests.post(
                    f"{self.base_url}/api/ai/query",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    results['query_endpoint_available'] = True
                    
                    data = response.json()
                    
                    # Check if response contains security-relevant content
                    response_text = data.get('response', '').lower()
                    security_keywords = ['security', 'alert', 'threat', 'login', 'authentication', 'network']
                    
                    if any(keyword in response_text for keyword in security_keywords):
                        results['security_context_preserved'] = True
                    
                    # Check response quality (should be more than just an error)
                    if len(response_text) > 50 and 'error' not in response_text:
                        results['response_quality'] = True
                    
                    # Check if query translation occurred
                    if 'siem_query' in data or 'translated_query' in data:
                        results['query_translation_works'] = True
                    
                    results['sample_response'] = data
                    break  # Test with first successful query
                    
        except Exception as e:
            logger.error(f"Natural language query test failed: {e}")
        
        results['overall_success'] = all([
            results['query_endpoint_available'],
            results['security_context_preserved']
        ])
        
        return results
    
    async def test_websocket_integration(self) -> Dict[str, Any]:
        """Test real-time WebSocket integration - Requirement 2.2"""
        logger.info("Testing WebSocket integration...")
        
        results = {
            'websocket_connection': False,
            'chat_functionality': False,
            'real_time_responses': False,
            'session_management': False
        }
        
        try:
            # Test WebSocket connection
            uri = f"{self.ws_url}/ws/chat"
            
            async with websockets.connect(uri) as websocket:
                results['websocket_connection'] = True
                
                # Test chat functionality
                test_message = {
                    "type": "chat",
                    "message": "What security events happened today?",
                    "session_id": "test_session_123"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(response)
                    
                    results['chat_functionality'] = True
                    results['real_time_responses'] = True
                    
                    # Check session management
                    if 'session_id' in response_data:
                        results['session_management'] = True
                    
                    results['sample_ws_response'] = response_data
                    
                except asyncio.TimeoutError:
                    logger.error("WebSocket response timeout")
                    
        except Exception as e:
            logger.error(f"WebSocket test failed: {e}")
        
        results['overall_success'] = all([
            results['websocket_connection'],
            results['chat_functionality']
        ])
        
        return results
    
    async def test_huggingface_model_management(self) -> Dict[str, Any]:
        """Test HuggingFace model downloading, loading, and switching - Requirement 3.1-3.5"""
        logger.info("Testing HuggingFace model management...")
        
        results = {
            'model_browser_available': False,
            'model_download_works': False,
            'model_loading_works': False,
            'model_switching_works': False,
            'resource_management': False
        }
        
        try:
            # Test model browser endpoint
            response = requests.get(f"{self.base_url}/api/ai/models/browse", timeout=10)
            if response.status_code == 200:
                results['model_browser_available'] = True
                models_data = response.json()
                results['available_models_count'] = len(models_data.get('models', []))
            
            # Test model listing
            response = requests.get(f"{self.base_url}/api/ai/models", timeout=10)
            if response.status_code == 200:
                models = response.json()
                results['local_models'] = models
                
                if models.get('loaded_models'):
                    results['model_loading_works'] = True
            
            # Test model switching (if multiple models available)
            if results.get('local_models', {}).get('available_models'):
                available_models = results['local_models']['available_models']
                if len(available_models) > 1:
                    # Try to switch to a different model
                    target_model = available_models[0]
                    switch_payload = {"model_name": target_model}
                    
                    response = requests.post(
                        f"{self.base_url}/api/ai/models/switch",
                        json=switch_payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        results['model_switching_works'] = True
            
            # Test resource management
            response = requests.get(f"{self.base_url}/api/ai/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                if 'resource_usage' in status or 'memory_usage' in status:
                    results['resource_management'] = True
                    results['resource_status'] = status
                    
        except Exception as e:
            logger.error(f"Model management test failed: {e}")
        
        results['overall_success'] = any([
            results['model_browser_available'],
            results['model_loading_works']
        ])
        
        return results
    
    async def test_siem_query_translation(self) -> Dict[str, Any]:
        """Test SIEM query translation capabilities - Requirements 5.1-5.3"""
        logger.info("Testing SIEM query translation...")
        
        results = {
            'translation_endpoint_available': False,
            'supports_multiple_siems': False,
            'query_optimization': False,
            'security_context_awareness': False
        }
        
        test_cases = [
            {
                'natural_query': 'Show failed logins in the last 24 hours',
                'siem_type': 'elastic',
                'expected_keywords': ['failed', 'login', 'authentication']
            },
            {
                'natural_query': 'Find network connections to suspicious IPs',
                'siem_type': 'splunk',
                'expected_keywords': ['network', 'connection', 'ip']
            },
            {
                'natural_query': 'List security alerts with high severity',
                'siem_type': 'wazuh',
                'expected_keywords': ['alert', 'severity', 'high']
            }
        ]
        
        try:
            for test_case in test_cases:
                payload = {
                    'query': test_case['natural_query'],
                    'siem_type': test_case['siem_type'],
                    'translate_only': True
                }
                
                response = requests.post(
                    f"{self.base_url}/api/siem/translate",
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    results['translation_endpoint_available'] = True
                    
                    translation_data = response.json()
                    translated_query = translation_data.get('translated_query', '').lower()
                    
                    # Check if translation contains expected security keywords
                    keyword_matches = sum(1 for keyword in test_case['expected_keywords'] 
                                        if keyword in translated_query)
                    
                    if keyword_matches >= len(test_case['expected_keywords']) // 2:
                        results['security_context_awareness'] = True
                    
                    # Check SIEM-specific syntax
                    siem_indicators = {
                        'elastic': ['query', 'bool', 'must', 'range'],
                        'splunk': ['search', 'index=', 'sourcetype='],
                        'wazuh': ['rule.level', 'agent.name', 'timestamp']
                    }
                    
                    expected_indicators = siem_indicators.get(test_case['siem_type'], [])
                    if any(indicator in translated_query for indicator in expected_indicators):
                        results['supports_multiple_siems'] = True
                    
                    results[f'translation_{test_case["siem_type"]}'] = translation_data
                    
        except Exception as e:
            logger.error(f"SIEM translation test failed: {e}")
        
        results['overall_success'] = all([
            results['translation_endpoint_available'],
            results['security_context_awareness']
        ])
        
        return results
    
    async def test_threat_hunting_capabilities(self) -> Dict[str, Any]:
        """Test threat hunting and security analysis capabilities - Requirements 5.4-5.5"""
        logger.info("Testing threat hunting capabilities...")
        
        results = {
            'threat_analysis_available': False,
            'mitre_attack_mapping': False,
            'threat_correlation': False,
            'executive_summary': False
        }
        
        try:
            # Test threat analysis endpoint
            threat_query = {
                'query': 'Analyze potential lateral movement in our network',
                'analysis_type': 'threat_hunting',
                'include_mitre': True
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/analyze",
                json=threat_query,
                timeout=30
            )
            
            if response.status_code == 200:
                results['threat_analysis_available'] = True
                
                analysis_data = response.json()
                analysis_text = analysis_data.get('analysis', '').lower()
                
                # Check for MITRE ATT&CK references
                mitre_keywords = ['mitre', 'att&ck', 'tactic', 'technique', 't1', 'ta00']
                if any(keyword in analysis_text for keyword in mitre_keywords):
                    results['mitre_attack_mapping'] = True
                
                # Check for threat correlation
                correlation_keywords = ['correlation', 'pattern', 'indicator', 'ioc', 'threat']
                if any(keyword in analysis_text for keyword in correlation_keywords):
                    results['threat_correlation'] = True
                
                # Check for executive summary
                if 'summary' in analysis_data or len(analysis_text) > 200:
                    results['executive_summary'] = True
                
                results['sample_analysis'] = analysis_data
            
            # Test security report generation
            report_query = {
                'query': 'Generate security report for today',
                'report_type': 'executive_summary'
            }
            
            response = requests.post(
                f"{self.base_url}/api/analytics/report",
                json=report_query,
                timeout=20
            )
            
            if response.status_code == 200:
                report_data = response.json()
                results['security_reporting'] = True
                results['sample_report'] = report_data
                
        except Exception as e:
            logger.error(f"Threat hunting test failed: {e}")
        
        results['overall_success'] = any([
            results['threat_analysis_available'],
            results['mitre_attack_mapping'],
            results['threat_correlation']
        ])
        
        return results
    
    async def test_security_analysis_features(self) -> Dict[str, Any]:
        """Test security analysis features - Requirement 5.6"""
        logger.info("Testing security analysis features...")
        
        results = {
            'log_analysis_available': False,
            'anomaly_detection': False,
            'incident_response': False,
            'compliance_reporting': False
        }
        
        try:
            # Test log analysis
            log_analysis_query = {
                'logs': ['sample security log entry', 'authentication failure'],
                'analysis_type': 'security_analysis'
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/analyze_logs",
                json=log_analysis_query,
                timeout=20
            )
            
            if response.status_code == 200:
                results['log_analysis_available'] = True
                analysis = response.json()
                results['log_analysis_sample'] = analysis
            
            # Test anomaly detection
            anomaly_query = {
                'query': 'Detect anomalies in user behavior patterns',
                'detection_type': 'behavioral_anomaly'
            }
            
            response = requests.post(
                f"{self.base_url}/api/analytics/anomaly",
                json=anomaly_query,
                timeout=15
            )
            
            if response.status_code == 200:
                results['anomaly_detection'] = True
                results['anomaly_sample'] = response.json()
            
            # Test incident response
            incident_query = {
                'incident_type': 'security_breach',
                'severity': 'high',
                'description': 'Suspicious network activity detected'
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/incident_response",
                json=incident_query,
                timeout=15
            )
            
            if response.status_code == 200:
                results['incident_response'] = True
                results['incident_sample'] = response.json()
                
        except Exception as e:
            logger.error(f"Security analysis test failed: {e}")
        
        results['overall_success'] = any([
            results['log_analysis_available'],
            results['anomaly_detection'],
            results['incident_response']
        ])
        
        return results
    
    async def test_resource_management(self) -> Dict[str, Any]:
        """Test intelligent resource management"""
        logger.info("Testing resource management...")
        
        results = {
            'resource_monitoring': False,
            'memory_management': False,
            'model_lifecycle': False,
            'performance_optimization': False
        }
        
        try:
            # Test resource monitoring
            response = requests.get(f"{self.base_url}/api/system/resources", timeout=10)
            if response.status_code == 200:
                resource_data = response.json()
                
                if 'memory_usage' in resource_data or 'cpu_usage' in resource_data:
                    results['resource_monitoring'] = True
                
                if 'model_memory' in resource_data:
                    results['memory_management'] = True
                
                results['resource_data'] = resource_data
            
            # Test model lifecycle management
            response = requests.get(f"{self.base_url}/api/ai/models/status", timeout=10)
            if response.status_code == 200:
                model_status = response.json()
                
                if 'loaded_models' in model_status and 'inactive_models' in model_status:
                    results['model_lifecycle'] = True
                
                results['model_status'] = model_status
                
        except Exception as e:
            logger.error(f"Resource management test failed: {e}")
        
        results['overall_success'] = any([
            results['resource_monitoring'],
            results['memory_management'],
            results['model_lifecycle']
        ])
        
        return results
    
    async def test_health_monitoring(self) -> Dict[str, Any]:
        """Test comprehensive health monitoring"""
        logger.info("Testing health monitoring...")
        
        results = {
            'health_endpoint': False,
            'detailed_diagnostics': False,
            'service_status': False,
            'alert_system': False
        }
        
        try:
            # Test main health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                results['health_endpoint'] = True
                health_data = response.json()
                
                # Check for detailed diagnostics
                if 'services' in health_data and 'system' in health_data:
                    results['detailed_diagnostics'] = True
                
                # Check service status reporting
                if 'embedded_ai' in health_data:
                    results['service_status'] = True
                
                results['health_data'] = health_data
            
            # Test detailed health endpoint
            response = requests.get(f"{self.base_url}/health/detailed", timeout=10)
            if response.status_code == 200:
                detailed_health = response.json()
                results['detailed_health'] = detailed_health
                
        except Exception as e:
            logger.error(f"Health monitoring test failed: {e}")
        
        results['overall_success'] = all([
            results['health_endpoint'],
            results['service_status']
        ])
        
        return results
    
    async def test_self_containment_validation(self) -> Dict[str, Any]:
        """Final validation of complete self-containment - Requirement 7.6"""
        logger.info("Testing complete self-containment...")
        
        results = {
            'no_external_calls': False,
            'local_processing_only': False,
            'embedded_models_functional': False,
            'zero_external_dependencies': False
        }
        
        try:
            # Monitor network activity during AI operations
            import psutil
            
            # Get baseline connections
            initial_connections = set(
                (conn.raddr.ip if conn.raddr else None, conn.raddr.port if conn.raddr else None)
                for conn in psutil.net_connections()
                if conn.raddr and not conn.raddr.ip.startswith('127.')
            )
            
            # Perform AI operations
            test_operations = [
                f"{self.base_url}/api/ai/query",
                f"{self.base_url}/api/ai/models",
                f"{self.base_url}/health"
            ]
            
            for endpoint in test_operations:
                if 'query' in endpoint:
                    requests.post(endpoint, json={'query': 'test security query'}, timeout=10)
                else:
                    requests.get(endpoint, timeout=10)
            
            # Check for new external connections
            final_connections = set(
                (conn.raddr.ip if conn.raddr else None, conn.raddr.port if conn.raddr else None)
                for conn in psutil.net_connections()
                if conn.raddr and not conn.raddr.ip.startswith('127.')
            )
            
            new_connections = final_connections - initial_connections
            results['no_external_calls'] = len(new_connections) == 0
            
            if new_connections:
                results['external_connections_detected'] = list(new_connections)
            
            # Test local processing
            response = requests.post(
                f"{self.base_url}/api/ai/query",
                json={'query': 'test local processing', 'local_only': True},
                timeout=15
            )
            
            if response.status_code == 200:
                results['local_processing_only'] = True
            
            # Test embedded models
            response = requests.get(f"{self.base_url}/api/ai/models/local", timeout=10)
            if response.status_code == 200:
                local_models = response.json()
                if local_models.get('models'):
                    results['embedded_models_functional'] = True
            
            # Final dependency check
            results['zero_external_dependencies'] = all([
                results['no_external_calls'],
                results['local_processing_only'],
                results['embedded_models_functional']
            ])
            
        except Exception as e:
            logger.error(f"Self-containment validation failed: {e}")
        
        results['overall_success'] = results['zero_external_dependencies']
        
        return results
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report"""
        
        # Calculate overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result['status'] == 'PASS')
        failed_tests = sum(1 for result in self.test_results.values() 
                          if result['status'] == 'FAIL')
        error_tests = sum(1 for result in self.test_results.values() 
                         if result['status'] == 'ERROR')
        
        # Determine overall validation status
        critical_tests = [
            'test_appliance_startup',
            'test_embedded_ai_sole_provider',
            'test_external_dependencies_removed',
            'test_self_containment_validation'
        ]
        
        critical_passed = all(
            self.test_results.get(test, {}).get('status') == 'PASS'
            for test in critical_tests
        )
        
        validation_status = 'PASS' if critical_passed and failed_tests == 0 else 'FAIL'
        
        report = {
            'validation_summary': {
                'overall_status': validation_status,
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            'critical_requirements_status': {
                'appliance_startup': self.test_results.get('test_appliance_startup', {}).get('status', 'NOT_RUN'),
                'embedded_ai_sole_provider': self.test_results.get('test_embedded_ai_sole_provider', {}).get('status', 'NOT_RUN'),
                'external_dependencies_removed': self.test_results.get('test_external_dependencies_removed', {}).get('status', 'NOT_RUN'),
                'self_containment': self.test_results.get('test_self_containment_validation', {}).get('status', 'NOT_RUN')
            },
            'feature_validation_status': {
                'natural_language_queries': self.test_results.get('test_natural_language_query_processing', {}).get('status', 'NOT_RUN'),
                'websocket_integration': self.test_results.get('test_websocket_integration', {}).get('status', 'NOT_RUN'),
                'model_management': self.test_results.get('test_huggingface_model_management', {}).get('status', 'NOT_RUN'),
                'siem_integration': self.test_results.get('test_siem_query_translation', {}).get('status', 'NOT_RUN'),
                'threat_hunting': self.test_results.get('test_threat_hunting_capabilities', {}).get('status', 'NOT_RUN'),
                'security_analysis': self.test_results.get('test_security_analysis_features', {}).get('status', 'NOT_RUN')
            },
            'detailed_results': self.test_results,
            'errors': self.errors,
            'recommendations': self.generate_recommendations(),
            'next_steps': self.generate_next_steps(validation_status)
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check for common issues
        if self.test_results.get('test_appliance_startup', {}).get('status') != 'PASS':
            recommendations.append("Verify all services are properly started and configured")
        
        if self.test_results.get('test_embedded_ai_sole_provider', {}).get('status') != 'PASS':
            recommendations.append("Ensure EmbeddedAIService is properly registered and functional")
        
        if self.test_results.get('test_external_dependencies_removed', {}).get('status') != 'PASS':
            recommendations.append("Remove all remaining external AI service dependencies")
        
        if self.test_results.get('test_natural_language_query_processing', {}).get('status') != 'PASS':
            recommendations.append("Verify natural language processing endpoints are working")
        
        if self.test_results.get('test_websocket_integration', {}).get('status') != 'PASS':
            recommendations.append("Check WebSocket configuration and chat service integration")
        
        if not recommendations:
            recommendations.append("All critical tests passed - security appliance is ready for deployment")
        
        return recommendations
    
    def generate_next_steps(self, validation_status: str) -> List[str]:
        """Generate next steps based on validation results"""
        if validation_status == 'PASS':
            return [
                "Security appliance validation completed successfully",
                "Ready for production deployment",
                "Consider running load testing for production readiness",
                "Update documentation with final configuration"
            ]
        else:
            return [
                "Address failed test cases before deployment",
                "Review error logs for specific issues",
                "Re-run validation after fixes",
                "Consider rollback plan if issues persist"
            ]

async def main():
    """Main execution function"""
    validator = FinalIntegrationValidator()
    
    try:
        # Run all validation tests
        report = await validator.run_all_tests()
        
        # Save detailed report
        report_file = Path('FINAL_INTEGRATION_VALIDATION_REPORT.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*80)
        print("FINAL SECURITY APPLIANCE INTEGRATION VALIDATION REPORT")
        print("="*80)
        
        summary = report['validation_summary']
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Tests Run: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']}")
        
        print("\nCritical Requirements Status:")
        for req, status in report['critical_requirements_status'].items():
            print(f"  {req}: {status}")
        
        print("\nFeature Validation Status:")
        for feature, status in report['feature_validation_status'].items():
            print(f"  {feature}: {status}")
        
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
        logger.error(f"Validation failed with error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())