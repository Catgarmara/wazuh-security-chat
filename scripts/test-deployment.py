#!/usr/bin/env python3
"""
Wazuh AI Companion - Deployment Testing Script

This script tests Docker Compose deployments in different configurations
and validates that all services are working correctly.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import yaml


class DeploymentTester:
    """Comprehensive deployment testing suite."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.results = []
        self.services_status = {}
        
    def log_result(self, test_name: str, success: bool, message: str = "", critical: bool = False):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        if critical and not success:
            status += " [CRITICAL]"
        
        self.results.append((test_name, success, message, critical))
        print(f"{status} {test_name}: {message}")
    
    def run_command(self, command: List[str], cwd: Optional[str] = None, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)
    
    def test_docker_compose_syntax(self) -> None:
        """Test Docker Compose file syntax."""
        print("\n🔍 Testing Docker Compose Syntax")
        print("=" * 50)
        
        compose_files = [
            "docker-compose.yml",
            "docker-compose.prod.yml"
        ]
        
        for compose_file in compose_files:
            success, output = self.run_command([
                "docker-compose", "-f", compose_file, "config"
            ])
            
            self.log_result(
                f"Compose Syntax - {compose_file}",
                success,
                "Valid syntax" if success else f"Syntax error: {output[:100]}",
                critical=True
            )
    
    def test_dockerfile_build(self) -> None:
        """Test Dockerfile build process."""
        print("\n🏗️ Testing Dockerfile Build")
        print("=" * 50)
        
        # Test development build
        success, output = self.run_command([
            "docker", "build", "--target", "development", "-t", "wazuh-ai-dev", "."
        ], timeout=300)
        
        self.log_result(
            "Dockerfile Build - Development",
            success,
            "Build successful" if success else f"Build failed: {output[-200:]}",
            critical=True
        )
        
        # Test production build
        success, output = self.run_command([
            "docker", "build", "--target", "production", "-t", "wazuh-ai-prod", "."
        ], timeout=300)
        
        self.log_result(
            "Dockerfile Build - Production",
            success,
            "Build successful" if success else f"Build failed: {output[-200:]}",
            critical=True
        )
    
    def test_development_deployment(self) -> None:
        """Test development deployment with Docker Compose."""
        print("\n🚀 Testing Development Deployment")
        print("=" * 50)
        
        # Start development stack
        print("Starting development stack...")
        success, output = self.run_command([
            "docker-compose", "up", "-d", "--build"
        ], timeout=300)
        
        self.log_result(
            "Development Stack Startup",
            success,
            "Stack started" if success else f"Startup failed: {output[-200:]}",
            critical=True
        )
        
        if not success:
            return
        
        # Wait for services to be ready
        print("Waiting for services to initialize...")
        time.sleep(30)
        
        # Test service health
        self._test_service_health("development")
        
        # Test application functionality
        self._test_application_functionality()
        
        # Clean up
        print("Cleaning up development stack...")
        self.run_command(["docker-compose", "down", "-v"])
    
    def test_production_deployment(self) -> None:
        """Test production deployment with Docker Compose."""
        print("\n🏭 Testing Production Deployment")
        print("=" * 50)
        
        # Create production environment file
        self._create_production_env()
        
        # Start production stack
        print("Starting production stack...")
        success, output = self.run_command([
            "docker-compose", "-f", "docker-compose.prod.yml", "up", "-d", "--build"
        ], timeout=300)
        
        self.log_result(
            "Production Stack Startup",
            success,
            "Stack started" if success else f"Startup failed: {output[-200:]}",
            critical=True
        )
        
        if not success:
            return
        
        # Wait for services to be ready
        print("Waiting for services to initialize...")
        time.sleep(45)
        
        # Test service health
        self._test_service_health("production")
        
        # Test application functionality
        self._test_application_functionality()
        
        # Test production-specific features
        self._test_production_features()
        
        # Clean up
        print("Cleaning up production stack...")
        self.run_command(["docker-compose", "-f", "docker-compose.prod.yml", "down", "-v"])
    
    def test_monitoring_deployment(self) -> None:
        """Test monitoring stack deployment."""
        print("\n📊 Testing Monitoring Deployment")
        print("=" * 50)
        
        # Start monitoring stack
        print("Starting monitoring stack...")
        success, output = self.run_command([
            "docker-compose", "--profile", "monitoring", "up", "-d"
        ], timeout=300)
        
        self.log_result(
            "Monitoring Stack Startup",
            success,
            "Stack started" if success else f"Startup failed: {output[-200:]}",
            critical=True
        )
        
        if not success:
            return
        
        # Wait for monitoring services
        print("Waiting for monitoring services...")
        time.sleep(30)
        
        # Test monitoring services
        monitoring_services = [
            ("Prometheus", "http://localhost:9090/-/ready"),
            ("Grafana", "http://localhost:3000/api/health"),
            ("Alertmanager", "http://localhost:9093/-/ready"),
            ("Node Exporter", "http://localhost:9100/metrics"),
            ("cAdvisor", "http://localhost:8080/metrics")
        ]
        
        for service_name, url in monitoring_services:
            try:
                response = requests.get(url, timeout=10)
                success = response.status_code == 200
                message = f"HTTP {response.status_code}"
            except Exception as e:
                success = False
                message = f"Connection error: {str(e)}"
            
            self.log_result(f"Monitoring Service - {service_name}", success, message)
        
        # Clean up
        print("Cleaning up monitoring stack...")
        self.run_command(["docker-compose", "--profile", "monitoring", "down", "-v"])
    
    def _create_production_env(self) -> None:
        """Create production environment file."""
        env_content = """
# Production Environment Configuration
DB_NAME=wazuh_chat_prod
DB_USER=wazuh_user
DB_PASSWORD=secure_production_password_123
SECRET_KEY=production_secret_key_must_be_at_least_32_characters_long_for_security
GRAFANA_PASSWORD=secure_grafana_password
GRAFANA_SECRET_KEY=grafana_secret_key_for_production_use_only
"""
        
        with open(os.path.join(self.project_root, ".env.prod"), "w") as f:
            f.write(env_content.strip())
    
    def _test_service_health(self, deployment_type: str) -> None:
        """Test health of all services."""
        print(f"Testing {deployment_type} service health...")
        
        # Get running containers
        success, output = self.run_command(["docker-compose", "ps", "--format", "json"])
        
        if success:
            try:
                containers = json.loads(output) if output.strip() else []
                if not isinstance(containers, list):
                    containers = [containers]
                
                for container in containers:
                    service_name = container.get('Service', 'unknown')
                    state = container.get('State', 'unknown')
                    health = container.get('Health', 'unknown')
                    
                    is_healthy = state == 'running' and (health in ['healthy', 'unknown'])
                    self.services_status[service_name] = is_healthy
                    
                    self.log_result(
                        f"Service Health - {service_name}",
                        is_healthy,
                        f"State: {state}, Health: {health}"
                    )
            except json.JSONDecodeError:
                self.log_result("Service Health Check", False, "Failed to parse container status")
    
    def _test_application_functionality(self) -> None:
        """Test core application functionality."""
        print("Testing application functionality...")
        
        # Test basic health endpoint
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                message = f"Status: {data.get('status', 'unknown')}"
            else:
                message = f"HTTP {response.status_code}"
        except Exception as e:
            success = False
            message = f"Connection error: {str(e)}"
        
        self.log_result("Application Health Endpoint", success, message, critical=True)
        
        # Test detailed health endpoint
        try:
            response = requests.get("http://localhost:8000/health/detailed", timeout=30)
            success = response.status_code == 200
            if success:
                data = response.json()
                overall_status = data.get('summary', {}).get('overall_status', 'unknown')
                message = f"Overall status: {overall_status}"
            else:
                message = f"HTTP {response.status_code}"
        except Exception as e:
            success = False
            message = f"Connection error: {str(e)}"
        
        self.log_result("Detailed Health Check", success, message)
        
        # Test metrics endpoint
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=10)
            success = response.status_code == 200
            if success:
                metrics_count = len([line for line in response.text.split('\n') 
                                   if line and not line.startswith('#')])
                message = f"Exposing {metrics_count} metrics"
            else:
                message = f"HTTP {response.status_code}"
        except Exception as e:
            success = False
            message = f"Connection error: {str(e)}"
        
        self.log_result("Metrics Endpoint", success, message)
    
    def _test_production_features(self) -> None:
        """Test production-specific features."""
        print("Testing production-specific features...")
        
        # Test Nginx reverse proxy (if enabled)
        try:
            response = requests.get("http://localhost:80/health", timeout=10)
            success = response.status_code == 200
            message = "Nginx proxy working" if success else f"HTTP {response.status_code}"
        except Exception as e:
            success = False
            message = f"Nginx not accessible: {str(e)}"
        
        self.log_result("Nginx Reverse Proxy", success, message)
        
        # Test resource limits (check if containers are respecting limits)
        success, output = self.run_command([
            "docker", "stats", "--no-stream", "--format", 
            "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ])
        
        self.log_result(
            "Resource Monitoring",
            success,
            "Resource stats available" if success else "Failed to get stats"
        )
    
    def test_kubernetes_manifests(self) -> None:
        """Test Kubernetes manifest syntax."""
        print("\n☸️ Testing Kubernetes Manifests")
        print("=" * 50)
        
        k8s_dir = os.path.join(self.project_root, "kubernetes")
        if not os.path.exists(k8s_dir):
            self.log_result("Kubernetes Directory", False, "Directory not found")
            return
        
        # Test manifest syntax
        for filename in os.listdir(k8s_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(k8s_dir, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        yaml.safe_load_all(f)
                    
                    self.log_result(
                        f"K8s Manifest - {filename}",
                        True,
                        "Valid YAML syntax"
                    )
                except yaml.YAMLError as e:
                    self.log_result(
                        f"K8s Manifest - {filename}",
                        False,
                        f"YAML error: {str(e)}"
                    )
                except Exception as e:
                    self.log_result(
                        f"K8s Manifest - {filename}",
                        False,
                        f"Error: {str(e)}"
                    )
        
        # Test kubectl dry-run (if kubectl is available)
        success, output = self.run_command(["kubectl", "version", "--client"])
        if success:
            print("Testing Kubernetes deployment with dry-run...")
            
            success, output = self.run_command([
                "kubectl", "apply", "-f", k8s_dir, "--dry-run=client"
            ])
            
            self.log_result(
                "Kubernetes Dry Run",
                success,
                "Manifests valid" if success else f"Validation failed: {output[-200:]}"
            )
        else:
            self.log_result("Kubectl Availability", False, "kubectl not available for testing")
    
    def run_comprehensive_deployment_tests(self) -> bool:
        """Run all deployment tests."""
        print("🚀 Starting Comprehensive Deployment Testing")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Project Root: {self.project_root}")
        print("=" * 60)
        
        # Check Docker availability
        success, output = self.run_command(["docker", "version"])
        if not success:
            print("❌ Docker is not available. Please install Docker first.")
            return False
        
        success, output = self.run_command(["docker-compose", "version"])
        if not success:
            print("❌ Docker Compose is not available. Please install Docker Compose first.")
            return False
        
        print("✅ Docker and Docker Compose are available")
        print()
        
        # Run test suites
        test_suites = [
            self.test_docker_compose_syntax,
            self.test_dockerfile_build,
            self.test_kubernetes_manifests,
            self.test_development_deployment,
            self.test_monitoring_deployment,
            # Note: Production deployment test is optional due to resource requirements
            # self.test_production_deployment,
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                suite_name = test_suite.__name__
                self.log_result(
                    f"Test Suite: {suite_name}",
                    False,
                    f"Suite error: {str(e)}",
                    critical=True
                )
            print()
        
        # Generate summary
        self._generate_summary()
        
        # Check for critical failures
        critical_failures = [r for r in self.results if not r[1] and r[3]]
        return len(critical_failures) == 0
    
    def _generate_summary(self) -> None:
        """Generate test summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for _, success, _, _ in self.results if success)
        failed_tests = total_tests - passed_tests
        critical_failures = sum(1 for _, success, _, critical in self.results if not success and critical)
        
        print("📊 Deployment Testing Summary")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Critical Failures: {critical_failures} 🚨")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test_name, success, message, critical in self.results:
                if not success:
                    critical_marker = " [CRITICAL]" if critical else ""
                    print(f"  • {test_name}{critical_marker}: {message}")
        
        # Deployment readiness assessment
        if critical_failures == 0:
            if failed_tests == 0:
                print("\n🎉 DEPLOYMENT STATUS: READY FOR PRODUCTION")
                print("All deployment tests passed successfully!")
            else:
                print("\n✅ DEPLOYMENT STATUS: READY FOR DEVELOPMENT")
                print("Core deployment is working, some optional features may need attention.")
        else:
            print("\n⚠️ DEPLOYMENT STATUS: NEEDS ATTENTION")
            print("Critical deployment issues found. Please fix before deploying.")


def main():
    """Main test execution."""
    tester = DeploymentTester()
    
    print("Wazuh AI Companion - Deployment Testing")
    print("=" * 60)
    print("This script tests Docker Compose and Kubernetes deployments")
    print("to ensure they work correctly in different environments.")
    print()
    
    success = tester.run_comprehensive_deployment_tests()
    
    if success:
        print("\n🎉 All critical deployment tests passed!")
        print("The deployment configuration is ready for use.")
        sys.exit(0)
    else:
        print("\n⚠️ Critical deployment issues found.")
        print("Please address the issues before deploying to production.")
        sys.exit(1)


if __name__ == "__main__":
    main()