#!/usr/bin/env python3
"""
Wazuh AI Companion - Comprehensive Deployment Script

This script provides automated deployment capabilities for different environments
including development, staging, and production deployments with proper validation.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests


class WazuhDeployer:
    """Comprehensive deployment manager for Wazuh AI Companion."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.deployment_config = self._load_deployment_config()
        
    def _load_deployment_config(self) -> Dict:
        """Load deployment configuration."""
        config_file = os.path.join(self.project_root, "deployment-config.yaml")
        
        # Default configuration if file doesn't exist
        default_config = {
            "environments": {
                "development": {
                    "compose_file": "docker-compose.yml",
                    "profiles": ["monitoring"],
                    "health_check_timeout": 120,
                    "required_services": ["app", "postgres", "redis"],
                    "optional_services": ["ollama", "prometheus", "grafana"]
                },
                "staging": {
                    "compose_file": "docker-compose.prod.yml",
                    "profiles": ["monitoring"],
                    "health_check_timeout": 180,
                    "required_services": ["app", "postgres", "redis", "nginx"],
                    "optional_services": ["ollama", "prometheus", "grafana", "alertmanager"]
                },
                "production": {
                    "compose_file": "docker-compose.prod.yml",
                    "profiles": [],
                    "health_check_timeout": 300,
                    "required_services": ["app", "postgres", "redis", "nginx"],
                    "optional_services": ["ollama"]
                }
            },
            "health_checks": {
                "app": "http://localhost:8000/health",
                "prometheus": "http://localhost:9090/-/ready",
                "grafana": "http://localhost:3000/api/health",
                "alertmanager": "http://localhost:9093/-/ready"
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"⚠️ Warning: Could not load deployment config: {e}")
                print("Using default configuration...")
        
        return default_config
    
    def run_command(self, command: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            print(f"🔧 Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"❌ Command failed with exit code {result.returncode}")
                print(f"Error output: {result.stderr}")
            
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)
    
    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites."""
        print("🔍 Checking deployment prerequisites...")
        
        prerequisites = [
            (["docker", "version"], "Docker"),
            (["docker-compose", "version"], "Docker Compose")
        ]
        
        for command, name in prerequisites:
            success, output = self.run_command(command, timeout=10)
            if not success:
                print(f"❌ {name} is not available: {output}")
                return False
            print(f"✅ {name} is available")
        
        # Check if required files exist
        required_files = [
            "Dockerfile",
            self.deployment_config["environments"][self.environment]["compose_file"]
        ]
        
        for file_path in required_files:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                print(f"❌ Required file not found: {file_path}")
                return False
            print(f"✅ Found required file: {file_path}")
        
        return True
    
    def prepare_environment(self) -> bool:
        """Prepare environment for deployment."""
        print(f"🛠️ Preparing {self.environment} environment...")
        
        # Create environment-specific configuration
        if self.environment == "production":
            return self._prepare_production_environment()
        elif self.environment == "staging":
            return self._prepare_staging_environment()
        else:
            return self._prepare_development_environment()
    
    def _prepare_development_environment(self) -> bool:
        """Prepare development environment."""
        env_content = """
# Development Environment
ENVIRONMENT=development
DEBUG=true
DB_NAME=wazuh_chat
DB_USER=postgres
DB_PASSWORD=postgres
SECRET_KEY=development_secret_key_32_characters_minimum
GRAFANA_PASSWORD=admin
GRAFANA_SECRET_KEY=development_grafana_secret_key
"""
        
        env_file = os.path.join(self.project_root, ".env")
        with open(env_file, "w") as f:
            f.write(env_content.strip())
        
        print("✅ Development environment prepared")
        return True
    
    def _prepare_staging_environment(self) -> bool:
        """Prepare staging environment."""
        env_content = """
# Staging Environment
ENVIRONMENT=staging
DEBUG=false
DB_NAME=wazuh_chat_staging
DB_USER=wazuh_staging
DB_PASSWORD=staging_password_123_secure
SECRET_KEY=staging_secret_key_must_be_32_characters_long
GRAFANA_PASSWORD=staging_grafana_password
GRAFANA_SECRET_KEY=staging_grafana_secret_key_for_security
"""
        
        env_file = os.path.join(self.project_root, ".env.staging")
        with open(env_file, "w") as f:
            f.write(env_content.strip())
        
        print("✅ Staging environment prepared")
        return True
    
    def _prepare_production_environment(self) -> bool:
        """Prepare production environment."""
        # Check if production environment file exists
        env_file = os.path.join(self.project_root, ".env.production")
        
        if not os.path.exists(env_file):
            print("⚠️ Production environment file not found.")
            print("Creating template production environment file...")
            
            env_content = """
# Production Environment - PLEASE UPDATE WITH SECURE VALUES
ENVIRONMENT=production
DEBUG=false
DB_NAME=wazuh_chat_prod
DB_USER=wazuh_prod
DB_PASSWORD=CHANGE_THIS_TO_SECURE_PASSWORD
SECRET_KEY=CHANGE_THIS_TO_SECURE_32_CHARACTER_SECRET_KEY
GRAFANA_PASSWORD=CHANGE_THIS_TO_SECURE_GRAFANA_PASSWORD
GRAFANA_SECRET_KEY=CHANGE_THIS_TO_SECURE_GRAFANA_SECRET_KEY
"""
            
            with open(env_file, "w") as f:
                f.write(env_content.strip())
            
            print(f"❌ Please update {env_file} with secure production values before deploying!")
            return False
        
        # Validate production environment
        with open(env_file, 'r') as f:
            content = f.read()
            
        if "CHANGE_THIS" in content:
            print("❌ Production environment file contains placeholder values!")
            print("Please update all CHANGE_THIS values with secure production values.")
            return False
        
        print("✅ Production environment validated")
        return True
    
    def build_images(self) -> bool:
        """Build Docker images."""
        print("🏗️ Building Docker images...")
        
        # Determine build target
        target = "production" if self.environment in ["staging", "production"] else "development"
        
        success, output = self.run_command([
            "docker-compose",
            "-f", self.deployment_config["environments"][self.environment]["compose_file"],
            "build",
            "--no-cache"
        ], timeout=600)
        
        if success:
            print("✅ Docker images built successfully")
        else:
            print(f"❌ Failed to build Docker images: {output}")
        
        return success
    
    def deploy_services(self) -> bool:
        """Deploy services using Docker Compose."""
        print(f"🚀 Deploying {self.environment} services...")
        
        compose_file = self.deployment_config["environments"][self.environment]["compose_file"]
        profiles = self.deployment_config["environments"][self.environment]["profiles"]
        
        # Build command
        command = ["docker-compose", "-f", compose_file]
        
        # Add profiles if specified
        for profile in profiles:
            command.extend(["--profile", profile])
        
        command.extend(["up", "-d", "--remove-orphans"])
        
        success, output = self.run_command(command, timeout=600)
        
        if success:
            print("✅ Services deployed successfully")
        else:
            print(f"❌ Failed to deploy services: {output}")
        
        return success
    
    def wait_for_services(self) -> bool:
        """Wait for services to be healthy."""
        print("⏳ Waiting for services to be healthy...")
        
        timeout = self.deployment_config["environments"][self.environment]["health_check_timeout"]
        start_time = time.time()
        
        required_services = self.deployment_config["environments"][self.environment]["required_services"]
        health_checks = self.deployment_config["health_checks"]
        
        while time.time() - start_time < timeout:
            all_healthy = True
            
            # Check Docker Compose service status
            success, output = self.run_command([
                "docker-compose",
                "-f", self.deployment_config["environments"][self.environment]["compose_file"],
                "ps", "--format", "json"
            ])
            
            if success and output.strip():
                try:
                    containers = json.loads(output) if output.strip().startswith('[') else [json.loads(output)]
                    
                    for container in containers:
                        service_name = container.get('Service', '')
                        state = container.get('State', '')
                        health = container.get('Health', 'unknown')
                        
                        if service_name in required_services:
                            is_healthy = state == 'running' and health in ['healthy', 'unknown']
                            if not is_healthy:
                                all_healthy = False
                                print(f"⏳ Waiting for {service_name} (State: {state}, Health: {health})")
                
                except json.JSONDecodeError:
                    all_healthy = False
            else:
                all_healthy = False
            
            # Check HTTP health endpoints
            for service, url in health_checks.items():
                if service in required_services or any(service in profiles for profiles in [self.deployment_config["environments"][self.environment]["profiles"]]):
                    try:
                        response = requests.get(url, timeout=5)
                        if response.status_code != 200:
                            all_healthy = False
                            print(f"⏳ Waiting for {service} HTTP health check")
                    except requests.RequestException:
                        all_healthy = False
                        print(f"⏳ Waiting for {service} to be accessible")
            
            if all_healthy:
                print("✅ All services are healthy")
                return True
            
            time.sleep(10)
        
        print(f"❌ Services did not become healthy within {timeout} seconds")
        return False
    
    def run_post_deployment_tests(self) -> bool:
        """Run post-deployment validation tests."""
        print("🧪 Running post-deployment tests...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test application health
        total_tests += 1
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    print("✅ Application health check passed")
                    tests_passed += 1
                else:
                    print(f"❌ Application health check failed: {data}")
            else:
                print(f"❌ Application health check failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Application health check failed: {e}")
        
        # Test detailed health endpoint
        total_tests += 1
        try:
            response = requests.get("http://localhost:8000/health/detailed", timeout=30)
            if response.status_code == 200:
                data = response.json()
                overall_status = data.get('summary', {}).get('overall_status', 'unknown')
                if overall_status in ['healthy', 'degraded']:
                    print(f"✅ Detailed health check passed (Status: {overall_status})")
                    tests_passed += 1
                else:
                    print(f"❌ Detailed health check failed: {overall_status}")
            else:
                print(f"❌ Detailed health check failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Detailed health check failed: {e}")
        
        # Test metrics endpoint
        total_tests += 1
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=10)
            if response.status_code == 200:
                metrics_count = len([line for line in response.text.split('\n') 
                                   if line and not line.startswith('#')])
                if metrics_count > 0:
                    print(f"✅ Metrics endpoint working ({metrics_count} metrics)")
                    tests_passed += 1
                else:
                    print("❌ Metrics endpoint returned no metrics")
            else:
                print(f"❌ Metrics endpoint failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Metrics endpoint failed: {e}")
        
        # Test monitoring services (if enabled)
        if "monitoring" in self.deployment_config["environments"][self.environment]["profiles"]:
            monitoring_tests = [
                ("Prometheus", "http://localhost:9090/-/ready"),
                ("Grafana", "http://localhost:3000/api/health"),
                ("Alertmanager", "http://localhost:9093/-/ready")
            ]
            
            for service_name, url in monitoring_tests:
                total_tests += 1
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        print(f"✅ {service_name} is accessible")
                        tests_passed += 1
                    else:
                        print(f"❌ {service_name} failed: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ {service_name} failed: {e}")
        
        success_rate = (tests_passed / total_tests) * 100 if total_tests > 0 else 0
        print(f"📊 Post-deployment tests: {tests_passed}/{total_tests} passed ({success_rate:.1f}%)")
        
        return tests_passed == total_tests
    
    def deploy(self) -> bool:
        """Execute complete deployment process."""
        print(f"🚀 Starting {self.environment} deployment")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Environment: {self.environment}")
        print(f"Project Root: {self.project_root}")
        print("=" * 60)
        
        deployment_steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Environment Preparation", self.prepare_environment),
            ("Image Building", self.build_images),
            ("Service Deployment", self.deploy_services),
            ("Health Check Wait", self.wait_for_services),
            ("Post-deployment Tests", self.run_post_deployment_tests)
        ]
        
        for step_name, step_function in deployment_steps:
            print(f"\n📋 Step: {step_name}")
            print("-" * 40)
            
            try:
                success = step_function()
                if not success:
                    print(f"❌ Deployment failed at step: {step_name}")
                    return False
                print(f"✅ Step completed: {step_name}")
            except Exception as e:
                print(f"❌ Step failed with exception: {step_name}")
                print(f"Error: {str(e)}")
                return False
        
        print(f"\n🎉 {self.environment.title()} deployment completed successfully!")
        self._print_access_information()
        return True
    
    def _print_access_information(self) -> None:
        """Print access information for deployed services."""
        print("\n📋 Service Access Information:")
        print("=" * 40)
        print("🌐 Application: http://localhost:8000")
        print("🏥 Health Check: http://localhost:8000/health")
        print("📊 Metrics: http://localhost:8000/metrics")
        
        if "monitoring" in self.deployment_config["environments"][self.environment]["profiles"]:
            print("\n📈 Monitoring Services:")
            print("📊 Prometheus: http://localhost:9090")
            print("📈 Grafana: http://localhost:3000 (admin/admin)")
            print("🚨 Alertmanager: http://localhost:9093")
            print("🖥️ Node Exporter: http://localhost:9100")
            print("📦 cAdvisor: http://localhost:8080")
        
        if self.environment in ["staging", "production"]:
            print("\n🌐 Reverse Proxy:")
            print("🔗 Nginx: http://localhost:80")
        
        print(f"\n🛠️ Management Commands:")
        compose_file = self.deployment_config["environments"][self.environment]["compose_file"]
        print(f"📋 View logs: docker-compose -f {compose_file} logs -f")
        print(f"⏹️ Stop services: docker-compose -f {compose_file} down")
        print(f"🔄 Restart services: docker-compose -f {compose_file} restart")
    
    def rollback(self) -> bool:
        """Rollback deployment."""
        print(f"🔄 Rolling back {self.environment} deployment...")
        
        compose_file = self.deployment_config["environments"][self.environment]["compose_file"]
        
        success, output = self.run_command([
            "docker-compose", "-f", compose_file, "down", "-v"
        ])
        
        if success:
            print("✅ Rollback completed successfully")
        else:
            print(f"❌ Rollback failed: {output}")
        
        return success


def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(description="Wazuh AI Companion Deployment Script")
    parser.add_argument(
        "action",
        choices=["deploy", "rollback", "status"],
        help="Deployment action to perform"
    )
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        default="development",
        help="Target deployment environment"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip post-deployment tests"
    )
    
    args = parser.parse_args()
    
    deployer = WazuhDeployer(environment=args.environment)
    
    if args.action == "deploy":
        success = deployer.deploy()
        sys.exit(0 if success else 1)
    elif args.action == "rollback":
        success = deployer.rollback()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        # Show current deployment status
        print("🔍 Checking deployment status...")
        # Implementation for status check would go here
        sys.exit(0)


if __name__ == "__main__":
    main()