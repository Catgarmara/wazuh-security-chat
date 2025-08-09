#!/usr/bin/env python3
"""
Build Configuration Validation Script

This script validates the self-contained appliance build system configuration
to ensure all dependencies and settings are correct for embedded AI integration.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

def validate_requirements_txt() -> Dict[str, Any]:
    """Validate requirements.txt for embedded AI dependencies."""
    print("🔍 Validating requirements.txt...")
    
    required_packages = {
        'llama-cpp-python': '0.2.20',
        'psutil': '5.9.6',
        'GPUtil': '1.4.0',
        'transformers': '4.36.0',
        'huggingface-hub': '0.19.4',
        'tokenizers': '0.15.0',
        'langchain': '0.1.0',
        'langchain-community': '0.0.10',
        'langchain-huggingface': '0.0.1',
        'faiss-cpu': '1.7.4',
        'sentence-transformers': '2.2.2',
        'fastapi': '0.104.1',
        'uvicorn': '0.24.0',
        'pydantic': '2.5.0',
        'sqlalchemy': '2.0.23',
        'redis': '5.0.1'
    }
    
    issues = []
    found_packages = {}
    
    try:
        with open('requirements.txt', 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' in line:
                        package_spec = line.split('==')
                        if len(package_spec) == 2:
                            package_name = package_spec[0].strip()
                            version = package_spec[1].strip()
                            found_packages[package_name] = version
    
        # Check for required packages
        for package, expected_version in required_packages.items():
            if package not in found_packages:
                issues.append(f"Missing required package: {package}=={expected_version}")
            elif found_packages[package] != expected_version:
                issues.append(f"Version mismatch for {package}: expected {expected_version}, found {found_packages[package]}")
        
        # Check for duplicates
        package_counts = {}
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '==' in line:
                    package_name = line.split('==')[0].strip()
                    package_counts[package_name] = package_counts.get(package_name, 0) + 1
        
        duplicates = [pkg for pkg, count in package_counts.items() if count > 1]
        if duplicates:
            issues.append(f"Duplicate packages found: {', '.join(duplicates)}")
        
        print(f"✅ Found {len(found_packages)} packages in requirements.txt")
        if issues:
            print(f"❌ {len(issues)} issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All required packages present with correct versions")
            
    except FileNotFoundError:
        issues.append("requirements.txt file not found")
    except Exception as e:
        issues.append(f"Error reading requirements.txt: {str(e)}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'packages_found': len(found_packages),
        'required_packages': len(required_packages)
    }

def validate_dockerfile() -> Dict[str, Any]:
    """Validate Dockerfile for embedded AI support."""
    print("\n🔍 Validating Dockerfile...")
    
    required_elements = [
        'AI_SERVICE_TYPE=embedded',
        'MODELS_PATH=/app/models',
        'VECTORSTORE_PATH=/app/data/vectorstore',
        'MAX_CONCURRENT_MODELS=3',
        'EMBEDDING_MODEL=all-MiniLM-L6-v2',
        'llama-cpp-python',
        'mkdir -p /app/models',
        'gcc',
        'g++',
        'cmake',
        'build-essential'
    ]
    
    issues = []
    found_elements = []
    
    try:
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()
        
        for element in required_elements:
            if element in dockerfile_content:
                found_elements.append(element)
            else:
                issues.append(f"Missing required element: {element}")
        
        # Check for multi-stage build
        if 'FROM python:3.11-slim as base' not in dockerfile_content:
            issues.append("Multi-stage build not properly configured")
        
        # Check for health checks
        if 'HEALTHCHECK' not in dockerfile_content:
            issues.append("Health check not configured")
        
        # Check for non-root user
        if 'USER wazuh' not in dockerfile_content:
            issues.append("Non-root user not configured")
        
        print(f"✅ Found {len(found_elements)}/{len(required_elements)} required elements")
        if issues:
            print(f"❌ {len(issues)} issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Dockerfile properly configured for embedded AI")
            
    except FileNotFoundError:
        issues.append("Dockerfile not found")
    except Exception as e:
        issues.append(f"Error reading Dockerfile: {str(e)}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'elements_found': len(found_elements),
        'required_elements': len(required_elements)
    }

def validate_docker_compose() -> Dict[str, Any]:
    """Validate docker-compose.yml for self-contained deployment."""
    print("\n🔍 Validating docker-compose.yml...")
    
    required_services = ['app', 'postgres', 'redis', 'frontend']
    required_env_vars = [
        'AI_SERVICE_TYPE=embedded',
        'MODELS_PATH=/app/models',
        'VECTORSTORE_PATH=/app/data/vectorstore',
        'APPLIANCE_MODE=true',
        'SIEM_INTEGRATION_ENABLED=true'
    ]
    
    issues = []
    found_services = []
    found_env_vars = []
    
    try:
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()
        
        # Parse YAML
        try:
            compose_data = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            issues.append(f"Invalid YAML syntax: {str(e)}")
            return {'valid': False, 'issues': issues}
        
        # Check services
        services = compose_data.get('services', {})
        for service in required_services:
            if service in services:
                found_services.append(service)
            else:
                issues.append(f"Missing required service: {service}")
        
        # Check environment variables in app service
        app_service = services.get('app', {})
        app_env = app_service.get('environment', [])
        
        for env_var in required_env_vars:
            env_found = False
            for env_entry in app_env:
                if isinstance(env_entry, str) and env_var in env_entry:
                    found_env_vars.append(env_var)
                    env_found = True
                    break
            if not env_found:
                issues.append(f"Missing environment variable: {env_var}")
        
        # Check volumes
        volumes = compose_data.get('volumes', {})
        required_volumes = ['model_data', 'vectorstore_data', 'postgres_data', 'redis_data']
        for volume in required_volumes:
            if volume not in volumes:
                issues.append(f"Missing volume: {volume}")
        
        # Check networks
        networks = compose_data.get('networks', {})
        if 'security-appliance-network' not in networks:
            issues.append("Missing security-appliance-network")
        
        # Check health checks
        if 'healthcheck' not in app_service:
            issues.append("App service missing health check")
        
        print(f"✅ Found {len(found_services)}/{len(required_services)} required services")
        print(f"✅ Found {len(found_env_vars)}/{len(required_env_vars)} required environment variables")
        
        if issues:
            print(f"❌ {len(issues)} issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Docker Compose properly configured for self-contained deployment")
            
    except FileNotFoundError:
        issues.append("docker-compose.yml not found")
    except Exception as e:
        issues.append(f"Error reading docker-compose.yml: {str(e)}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'services_found': len(found_services),
        'env_vars_found': len(found_env_vars)
    }

def validate_embedded_ai_service() -> Dict[str, Any]:
    """Validate embedded AI service implementation."""
    print("\n🔍 Validating embedded AI service...")
    
    issues = []
    
    try:
        service_path = Path('services/embedded_ai_service.py')
        if not service_path.exists():
            issues.append("embedded_ai_service.py not found")
            return {'valid': False, 'issues': issues}
        
        with open(service_path, 'r') as f:
            service_content = f.read()
        
        required_classes = ['EmbeddedAIService', 'ModelConfig', 'SystemStats']
        required_methods = [
            'load_model', 'unload_model', 'generate_response', 
            'hot_swap_model', 'get_system_stats', 'register_model'
        ]
        
        for cls in required_classes:
            if f"class {cls}" not in service_content:
                issues.append(f"Missing class: {cls}")
        
        for method in required_methods:
            if f"def {method}" not in service_content:
                issues.append(f"Missing method: {method}")
        
        # Check for llama-cpp-python import
        if 'from llama_cpp import Llama' not in service_content:
            issues.append("Missing llama-cpp-python import")
        
        # Check for error handling
        if 'try:' not in service_content or 'except' not in service_content:
            issues.append("Insufficient error handling")
        
        if issues:
            print(f"❌ {len(issues)} issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Embedded AI service properly implemented")
            
    except Exception as e:
        issues.append(f"Error validating embedded AI service: {str(e)}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }

def main():
    """Main validation function."""
    print("🚀 Validating Self-Contained Appliance Build System")
    print("=" * 60)
    
    # Change to project root if script is run from scripts directory
    if Path.cwd().name == 'scripts':
        os.chdir('..')
    
    results = {}
    
    # Run all validations
    results['requirements'] = validate_requirements_txt()
    results['dockerfile'] = validate_dockerfile()
    results['docker_compose'] = validate_docker_compose()
    results['embedded_ai'] = validate_embedded_ai_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_valid = True
    total_issues = 0
    
    for component, result in results.items():
        status = "✅ PASS" if result['valid'] else "❌ FAIL"
        issue_count = len(result['issues'])
        total_issues += issue_count
        
        print(f"{component.upper():15} {status:8} ({issue_count} issues)")
        
        if not result['valid']:
            all_valid = False
    
    print("-" * 60)
    
    if all_valid:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Self-contained appliance build system is properly configured")
        print("✅ Ready for deployment with: docker-compose up")
        return 0
    else:
        print(f"❌ VALIDATION FAILED ({total_issues} total issues)")
        print("🔧 Please fix the issues above before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())