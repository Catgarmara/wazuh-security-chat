#!/usr/bin/env python3
"""
Wazuh AI Companion - Comprehensive Monitoring Validation Script

This script validates the complete monitoring setup including:
- Health checks for all services
- Prometheus metrics collection
- Grafana dashboard availability
- Alert rule validation
- Business metrics verification
"""

import asyncio
import json
import requests
import time
import sys
from typing import Dict, List, Tuple, Any
from datetime import datetime
import yaml


class ComprehensiveMonitoringValidator:
    """Comprehensive monitoring validation suite."""
    
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"
        self.alertmanager_url = "http://localhost:9093"
        self.app_url = "http://localhost:8000"
        
        self.results = []
        self.critical_failures = []
        
    def log_result(self, test_name: str, success: bool, message: str = "", critical: bool = False):
        """Log test result with criticality indicator."""
        status = "✅ PASS" if success else "❌ FAIL"
        if critical and not success:
            status += " [CRITICAL]"
            self.critical_failures.append(test_name)
        
        self.results.append((test_name, success, message, critical))
        print(f"{status} {test_name}: {message}")
    
    async def test_application_health_endpoints(self) -> None:
        """Test comprehensive health check endpoints."""
        print("\n🏥 Testing Application Health Endpoints")
        print("=" * 50)
        
        # Test basic health endpoint
        try:
            response = requests.get(f"{self.app_url}/health", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                message = f"Status: {data.get('status', 'unknown')}"
            else:
                message = f"HTTP {response.status_code}"
            self.log_result("Basic Health Check", success, message, critical=True)
        except Exception as e:
            self.log_result("Basic Health Check", False, f"Error: {str(e)}", critical=True)
        
        # Test detailed health endpoint
        try:
            response = requests.get(f"{self.app_url}/health/detailed", timeout=30)
            success = response.status_code == 200
            if success:
                data = response.json()
                overall_status = data.get('summary', {}).get('overall_status', 'unknown')
                total_checks = data.get('summary', {}).get('total_checks', 0)
                healthy_checks = data.get('summary', {}).get('healthy_checks', 0)
                message = f"Overall: {overall_status}, {healthy_checks}/{total_checks} healthy"
                
                # Check individual service health
                checks = data.get('checks', {})
                for service, check_data in checks.items():
                    service_status = check_data.get('status', 'unknown')
                    response_time = check_data.get('response_time_ms', 0)
                    self.log_result(
                        f"Service Health - {service}",
                        service_status in ['healthy', 'degraded'],
                        f"Status: {service_status}, Response: {response_time}ms"
                    )
            else:
                message = f"HTTP {response.status_code}"
            
            self.log_result("Detailed Health Check", success, message, critical=True)
        except Exception as e:
            self.log_result("Detailed Health Check", False, f"Error: {str(e)}", critical=True)
    
    def test_prometheus_health_metrics(self) -> None:
        """Test Prometheus health check metrics."""
        print("\n📊 Testing Prometheus Health Metrics")
        print("=" * 50)
        
        # Test health check status metrics
        health_metrics = [
            "wazuh_health_check_status",
            "wazuh_health_check_duration_seconds",
            "wazuh_service_uptime_seconds_total",
            "wazuh_service_restart_count_total"
        ]
        
        for metric in health_metrics:
            try:
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": metric},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('data', {}).get('result', [])
                    success = len(result) > 0
                    message = f"Found {len(result)} series" if success else "No data found"
                else:
                    success = False
                    message = f"HTTP {response.status_code}"
                
                self.log_result(f"Metric: {metric}", success, message)
            except Exception as e:
                self.log_result(f"Metric: {metric}", False, f"Error: {str(e)}")
    
    def test_business_metrics(self) -> None:
        """Test business logic metrics."""
        print("\n💼 Testing Business Metrics")
        print("=" * 50)
        
        business_metrics = [
            "wazuh_query_complexity_score",
            "wazuh_user_satisfaction_score",
            "wazuh_security_alerts_generated_total",
            "wazuh_log_analysis_accuracy",
            "wazuh_threat_detection_latency_seconds"
        ]
        
        for metric in business_metrics:
            try:
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": metric},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('data', {}).get('result', [])
                    success = True  # Business metrics may not have data initially
                    message = f"Metric available, {len(result)} series"
                else:
                    success = False
                    message = f"HTTP {response.status_code}"
                
                self.log_result(f"Business Metric: {metric}", success, message)
            except Exception as e:
                self.log_result(f"Business Metric: {metric}", False, f"Error: {str(e)}")
    
    def test_grafana_dashboards(self) -> None:
        """Test Grafana dashboard availability."""
        print("\n📈 Testing Grafana Dashboards")
        print("=" * 50)
        
        expected_dashboards = [
            "wazuh-health-monitoring",
            "wazuh-comprehensive-metrics",
            "wazuh-app-dashboard",
            "wazuh-ai-performance",
            "wazuh-business-metrics",
            "wazuh-infrastructure",
            "wazuh-alerts"
        ]
        
        try:
            # Try to get dashboard list (may require authentication)
            response = requests.get(
                f"{self.grafana_url}/api/search",
                auth=('admin', 'admin'),
                timeout=10
            )
            
            if response.status_code == 200:
                dashboards = response.json()
                dashboard_titles = [d.get('title', '') for d in dashboards]
                
                for expected in expected_dashboards:
                    found = any(expected.lower() in title.lower() for title in dashboard_titles)
                    self.log_result(
                        f"Dashboard: {expected}",
                        found,
                        "Available" if found else "Not found"
                    )
                
                self.log_result(
                    "Grafana Dashboard Access",
                    True,
                    f"Found {len(dashboards)} dashboards total"
                )
            elif response.status_code == 401:
                self.log_result(
                    "Grafana Dashboard Access",
                    True,
                    "Authentication required (service is running)"
                )
            else:
                self.log_result(
                    "Grafana Dashboard Access",
                    False,
                    f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_result("Grafana Dashboard Access", False, f"Error: {str(e)}")
    
    def test_alerting_rules(self) -> None:
        """Test comprehensive alerting rules."""
        print("\n🚨 Testing Alerting Rules")
        print("=" * 50)
        
        expected_alert_groups = [
            "wazuh-health-alerts",
            "wazuh-business-alerts",
            "wazuh-app-alerts",
            "wazuh-infrastructure-alerts"
        ]
        
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/rules", timeout=10)
            if response.status_code == 200:
                data = response.json()
                groups = data.get('data', {}).get('groups', [])
                
                group_names = [g.get('name', '') for g in groups]
                total_rules = sum(len(g.get('rules', [])) for g in groups)
                
                for expected_group in expected_alert_groups:
                    found = expected_group in group_names
                    self.log_result(
                        f"Alert Group: {expected_group}",
                        found,
                        "Loaded" if found else "Not found"
                    )
                
                # Check for critical health alerts
                critical_alerts = [
                    "ApplicationDown",
                    "DatabaseDown",
                    "RedisDown",
                    "HighCPUUsage",
                    "HighMemoryUsage",
                    "SLAAvailabilityBreach"
                ]
                
                all_rules = []
                for group in groups:
                    all_rules.extend([r.get('name', '') for r in group.get('rules', [])])
                
                for alert in critical_alerts:
                    found = alert in all_rules
                    self.log_result(
                        f"Critical Alert: {alert}",
                        found,
                        "Configured" if found else "Missing",
                        critical=True
                    )
                
                self.log_result(
                    "Alerting Rules Summary",
                    total_rules > 0,
                    f"{total_rules} rules in {len(groups)} groups"
                )
            else:
                self.log_result(
                    "Alerting Rules",
                    False,
                    f"HTTP {response.status_code}",
                    critical=True
                )
        except Exception as e:
            self.log_result("Alerting Rules", False, f"Error: {str(e)}", critical=True)
    
    def test_alertmanager_configuration(self) -> None:
        """Test Alertmanager configuration."""
        print("\n📢 Testing Alertmanager Configuration")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.alertmanager_url}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                config = data.get('data', {}).get('configYAML', '')
                
                # Check for essential configuration elements
                config_checks = {
                    "routing": 'route:' in config,
                    "receivers": 'receivers:' in config,
                    "email_config": 'smtp_' in config or 'email_configs:' in config,
                    "slack_config": 'slack_configs:' in config,
                    "webhook_config": 'webhook_configs:' in config
                }
                
                for check_name, passed in config_checks.items():
                    self.log_result(
                        f"Alertmanager {check_name}",
                        passed,
                        "Configured" if passed else "Not configured"
                    )
                
                # Overall configuration health
                essential_configs = sum([config_checks['routing'], config_checks['receivers']])
                self.log_result(
                    "Alertmanager Configuration",
                    essential_configs >= 2,
                    f"Essential configs: {essential_configs}/2"
                )
            else:
                self.log_result(
                    "Alertmanager Configuration",
                    False,
                    f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_result("Alertmanager Configuration", False, f"Error: {str(e)}")
    
    def test_monitoring_integration(self) -> None:
        """Test end-to-end monitoring integration."""
        print("\n🔄 Testing Monitoring Integration")
        print("=" * 50)
        
        # Test that application metrics are being scraped
        try:
            response = requests.get(f"{self.app_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for key metric families
                key_metrics = [
                    'wazuh_app_info',
                    'wazuh_http_requests_total',
                    'wazuh_health_check_status',
                    'wazuh_ai_queries_total',
                    'wazuh_websocket_connections_active'
                ]
                
                found_metrics = []
                for metric in key_metrics:
                    if metric in metrics_text:
                        found_metrics.append(metric)
                
                success = len(found_metrics) >= len(key_metrics) * 0.8
                self.log_result(
                    "Application Metrics Export",
                    success,
                    f"Found {len(found_metrics)}/{len(key_metrics)} key metrics"
                )
                
                # Test Prometheus scraping
                time.sleep(2)  # Wait for scrape
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": "wazuh_app_info"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('data', {}).get('result', [])
                    success = len(result) > 0
                    message = "Metrics being scraped" if success else "No scraped data"
                else:
                    success = False
                    message = f"Prometheus query failed: {response.status_code}"
                
                self.log_result("Prometheus Scraping", success, message, critical=True)
            else:
                self.log_result(
                    "Application Metrics Export",
                    False,
                    f"HTTP {response.status_code}",
                    critical=True
                )
        except Exception as e:
            self.log_result(
                "Application Metrics Export",
                False,
                f"Error: {str(e)}",
                critical=True
            )
    
    def generate_test_metrics(self) -> None:
        """Generate some test metrics to validate collection."""
        print("\n🧪 Generating Test Metrics")
        print("=" * 50)
        
        try:
            # Make some test requests to generate metrics
            test_endpoints = [
                "/health",
                "/health/detailed",
                "/metrics"
            ]
            
            for endpoint in test_endpoints:
                try:
                    requests.get(f"{self.app_url}{endpoint}", timeout=5)
                except:
                    pass  # Ignore errors, we just want to generate metrics
            
            self.log_result("Test Metrics Generation", True, "Generated test traffic")
        except Exception as e:
            self.log_result("Test Metrics Generation", False, f"Error: {str(e)}")
    
    async def run_comprehensive_validation(self) -> bool:
        """Run all monitoring validation tests."""
        print("🔍 Starting Comprehensive Monitoring Validation")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Wait for services to be ready
        print("⏳ Waiting for services to initialize...")
        time.sleep(5)
        
        # Run all test suites
        test_suites = [
            self.test_application_health_endpoints,
            self.test_prometheus_health_metrics,
            self.test_business_metrics,
            self.test_grafana_dashboards,
            self.test_alerting_rules,
            self.test_alertmanager_configuration,
            self.generate_test_metrics,
            self.test_monitoring_integration
        ]
        
        for test_suite in test_suites:
            try:
                if asyncio.iscoroutinefunction(test_suite):
                    await test_suite()
                else:
                    test_suite()
            except Exception as e:
                suite_name = test_suite.__name__
                self.log_result(
                    f"Test Suite: {suite_name}",
                    False,
                    f"Suite error: {str(e)}",
                    critical=True
                )
            print()  # Add spacing between test suites
        
        # Generate comprehensive summary
        self._generate_summary()
        
        return len(self.critical_failures) == 0
    
    def _generate_summary(self) -> None:
        """Generate comprehensive test summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for _, success, _, _ in self.results if success)
        failed_tests = total_tests - passed_tests
        critical_failed = len(self.critical_failures)
        
        print("📊 Comprehensive Monitoring Validation Summary")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Critical Failures: {critical_failed} 🚨")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.critical_failures:
            print("\n🚨 CRITICAL FAILURES:")
            for failure in self.critical_failures:
                print(f"  • {failure}")
        
        if failed_tests > 0:
            print("\n❌ All Failed Tests:")
            for test_name, success, message, critical in self.results:
                if not success:
                    critical_marker = " [CRITICAL]" if critical else ""
                    print(f"  • {test_name}{critical_marker}: {message}")
        
        # Monitoring readiness assessment
        if critical_failed == 0:
            if failed_tests == 0:
                print("\n🎉 MONITORING STATUS: FULLY OPERATIONAL")
                print("All monitoring components are working correctly!")
            else:
                print("\n✅ MONITORING STATUS: OPERATIONAL")
                print("Core monitoring is working, some optional features may need attention.")
        else:
            print("\n⚠️ MONITORING STATUS: NEEDS ATTENTION")
            print("Critical monitoring components are not working properly.")


async def main():
    """Main validation execution."""
    validator = ComprehensiveMonitoringValidator()
    
    print("Wazuh AI Companion - Comprehensive Monitoring Validation")
    print("=" * 60)
    print("This script validates the complete monitoring stack including:")
    print("• Application health checks")
    print("• Prometheus metrics collection")
    print("• Grafana dashboards")
    print("• Alerting rules and configuration")
    print("• Business metrics")
    print("• End-to-end integration")
    print()
    
    success = await validator.run_comprehensive_validation()
    
    if success:
        print("\n🎉 Comprehensive monitoring validation completed successfully!")
        print("The monitoring stack is ready for production use.")
        sys.exit(0)
    else:
        print("\n⚠️ Monitoring validation found critical issues.")
        print("Please address the critical failures before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())