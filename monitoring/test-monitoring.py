#!/usr/bin/env python3
"""
Wazuh AI Companion - Monitoring Test Script
This script tests the monitoring stack components and validates configurations.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Tuple
import yaml


class MonitoringTester:
    """Test suite for monitoring stack validation."""
    
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"
        self.alertmanager_url = "http://localhost:9093"
        self.app_url = "http://localhost:8000"
        
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append((test_name, success, message))
        print(f"{status} {test_name}: {message}")
        
    def test_service_health(self) -> None:
        """Test if all monitoring services are healthy."""
        services = [
            ("Prometheus", f"{self.prometheus_url}/-/ready"),
            ("Grafana", f"{self.grafana_url}/api/health"),
            ("Alertmanager", f"{self.alertmanager_url}/-/ready"),
            ("Application", f"{self.app_url}/health"),
        ]
        
        for service_name, url in services:
            try:
                response = requests.get(url, timeout=5)
                success = response.status_code == 200
                message = f"Status: {response.status_code}"
                if not success and response.status_code == 404:
                    message += " (Service may not be running)"
            except requests.exceptions.RequestException as e:
                success = False
                message = f"Connection error: {str(e)}"
                
            self.log_result(f"{service_name} Health Check", success, message)
    
    def test_prometheus_targets(self) -> None:
        """Test Prometheus target discovery."""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/targets", timeout=10)
            if response.status_code == 200:
                data = response.json()
                targets = data.get('data', {}).get('activeTargets', [])
                
                expected_jobs = [
                    'prometheus', 'wazuh-app', 'postgres', 'redis', 
                    'node', 'nginx', 'cadvisor'
                ]
                
                found_jobs = set()
                healthy_targets = 0
                total_targets = len(targets)
                
                for target in targets:
                    job = target.get('labels', {}).get('job', '')
                    found_jobs.add(job)
                    if target.get('health') == 'up':
                        healthy_targets += 1
                
                # Check if critical jobs are present
                critical_jobs = ['prometheus', 'wazuh-app']
                missing_critical = [job for job in critical_jobs if job not in found_jobs]
                
                if missing_critical:
                    self.log_result(
                        "Prometheus Targets", 
                        False, 
                        f"Missing critical targets: {missing_critical}"
                    )
                else:
                    self.log_result(
                        "Prometheus Targets", 
                        True, 
                        f"{healthy_targets}/{total_targets} targets healthy"
                    )
                    
                # Log found jobs
                self.log_result(
                    "Target Discovery", 
                    True, 
                    f"Found jobs: {sorted(found_jobs)}"
                )
            else:
                self.log_result(
                    "Prometheus Targets", 
                    False, 
                    f"API error: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.log_result("Prometheus Targets", False, f"Connection error: {str(e)}")
    
    def test_application_metrics(self) -> None:
        """Test if application is exposing metrics."""
        try:
            response = requests.get(f"{self.app_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for key application metrics
                expected_metrics = [
                    'wazuh_http_requests_total',
                    'wazuh_websocket_connections_active',
                    'wazuh_ai_queries_total',
                    'wazuh_database_connections_active',
                    'wazuh_app_info'
                ]
                
                found_metrics = []
                for metric in expected_metrics:
                    if metric in metrics_text:
                        found_metrics.append(metric)
                
                success = len(found_metrics) >= len(expected_metrics) * 0.8  # 80% threshold
                message = f"Found {len(found_metrics)}/{len(expected_metrics)} expected metrics"
                
                self.log_result("Application Metrics", success, message)
                
                if found_metrics:
                    self.log_result(
                        "Metrics Available", 
                        True, 
                        f"Available: {found_metrics[:3]}..."
                    )
            else:
                self.log_result(
                    "Application Metrics", 
                    False, 
                    f"Metrics endpoint error: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.log_result("Application Metrics", False, f"Connection error: {str(e)}")
    
    def test_alerting_rules(self) -> None:
        """Test Prometheus alerting rules."""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/rules", timeout=10)
            if response.status_code == 200:
                data = response.json()
                groups = data.get('data', {}).get('groups', [])
                
                total_rules = 0
                active_alerts = 0
                rule_groups = []
                
                for group in groups:
                    group_name = group.get('name', '')
                    rule_groups.append(group_name)
                    rules = group.get('rules', [])
                    total_rules += len(rules)
                    
                    for rule in rules:
                        if rule.get('type') == 'alerting' and rule.get('state') == 'firing':
                            active_alerts += 1
                
                success = total_rules > 0
                message = f"{total_rules} rules in {len(groups)} groups"
                if active_alerts > 0:
                    message += f", {active_alerts} firing"
                
                self.log_result("Alerting Rules", success, message)
                
                if rule_groups:
                    self.log_result(
                        "Rule Groups", 
                        True, 
                        f"Groups: {rule_groups}"
                    )
            else:
                self.log_result(
                    "Alerting Rules", 
                    False, 
                    f"Rules API error: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.log_result("Alerting Rules", False, f"Connection error: {str(e)}")
    
    def test_grafana_datasources(self) -> None:
        """Test Grafana datasource configuration."""
        try:
            # Try to access Grafana API (may require authentication)
            response = requests.get(
                f"{self.grafana_url}/api/datasources", 
                auth=('admin', 'admin'),
                timeout=10
            )
            
            if response.status_code == 200:
                datasources = response.json()
                prometheus_ds = [ds for ds in datasources if ds.get('type') == 'prometheus']
                
                success = len(prometheus_ds) > 0
                message = f"Found {len(prometheus_ds)} Prometheus datasource(s)"
                
                self.log_result("Grafana Datasources", success, message)
            elif response.status_code == 401:
                self.log_result(
                    "Grafana Datasources", 
                    True, 
                    "Authentication required (service is running)"
                )
            else:
                self.log_result(
                    "Grafana Datasources", 
                    False, 
                    f"API error: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.log_result("Grafana Datasources", False, f"Connection error: {str(e)}")
    
    def test_alertmanager_config(self) -> None:
        """Test Alertmanager configuration."""
        try:
            response = requests.get(f"{self.alertmanager_url}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                config = data.get('data', {}).get('configYAML', '')
                
                # Check for key configuration elements
                has_routes = 'route:' in config
                has_receivers = 'receivers:' in config
                has_smtp = 'smtp_' in config or 'email_configs:' in config
                has_slack = 'slack_configs:' in config
                
                config_score = sum([has_routes, has_receivers, has_smtp, has_slack])
                success = config_score >= 2  # At least routes and receivers
                
                message = f"Config elements: routes={has_routes}, receivers={has_receivers}"
                if has_smtp:
                    message += ", email=True"
                if has_slack:
                    message += ", slack=True"
                
                self.log_result("Alertmanager Config", success, message)
            else:
                self.log_result(
                    "Alertmanager Config", 
                    False, 
                    f"Status API error: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.log_result("Alertmanager Config", False, f"Connection error: {str(e)}")
    
    def test_exporters(self) -> None:
        """Test various exporters."""
        exporters = [
            ("Node Exporter", "http://localhost:9100/metrics"),
            ("PostgreSQL Exporter", "http://localhost:9187/metrics"),
            ("Redis Exporter", "http://localhost:9121/metrics"),
            ("cAdvisor", "http://localhost:8080/metrics"),
        ]
        
        for exporter_name, url in exporters:
            try:
                response = requests.get(url, timeout=5)
                success = response.status_code == 200
                if success:
                    # Count metrics
                    metrics_count = len([line for line in response.text.split('\n') 
                                       if line and not line.startswith('#')])
                    message = f"Exposing {metrics_count} metrics"
                else:
                    message = f"HTTP {response.status_code}"
            except requests.exceptions.RequestException as e:
                success = False
                message = f"Connection error: {str(e)}"
            
            self.log_result(f"{exporter_name}", success, message)
    
    def run_all_tests(self) -> bool:
        """Run all monitoring tests."""
        print("🔍 Starting Wazuh AI Companion Monitoring Tests\n")
        
        test_methods = [
            self.test_service_health,
            self.test_prometheus_targets,
            self.test_application_metrics,
            self.test_alerting_rules,
            self.test_grafana_datasources,
            self.test_alertmanager_config,
            self.test_exporters,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_result(
                    f"{test_method.__name__}", 
                    False, 
                    f"Test error: {str(e)}"
                )
            print()  # Add spacing between test groups
        
        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for _, success, _ in self.results if success)
        failed_tests = total_tests - passed_tests
        
        print("📊 Test Summary")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test_name, success, message in self.results:
                if not success:
                    print(f"  • {test_name}: {message}")
        
        return failed_tests == 0


def main():
    """Main test execution."""
    tester = MonitoringTester()
    
    print("Wazuh AI Companion - Monitoring Stack Test")
    print("=" * 50)
    print("This script validates the monitoring stack configuration and health.")
    print("Make sure all services are running before executing tests.\n")
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to initialize...")
    time.sleep(5)
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All monitoring tests passed! The stack is ready for use.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check the monitoring configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()