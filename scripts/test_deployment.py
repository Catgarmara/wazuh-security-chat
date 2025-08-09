#!/usr/bin/env python3
"""
Deployment Test Script

Tests the self-contained appliance deployment configuration
without actually starting the containers.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

def test_docker_compose_syntax():
    """Test docker-compose.yml syntax without starting services."""
    print("🔍 Testing Docker Compose syntax...")
    
    try:
        # Test if docker-compose/docker compose is available
        docker_cmd = None
        try:
            subprocess.run(['docker-compose', '--version'], 
                         capture_output=True, check=True)
            docker_cmd = ['docker-compose']
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['docker', 'compose', 'version'], 
                             capture_output=True, check=True)
                docker_cmd = ['docker', 'compose']
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️  Docker Compose not available - skipping syntax test")
                return {'valid': True, 'skipped': True, 'reason': 'Docker not available'}
        
        # Test configuration syntax
        result = subprocess.run(
            docker_cmd + ['config'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Docker Compose syntax is valid")
            return {'valid': True, 'output': result.stdout}
        else:
            print(f"❌ Docker Compose syntax error: {result.stderr}")
            return {'valid': False, 'error': result.stderr}
            
    except Exception as e:
        print(f"❌ Error testing Docker Compose: {str(e)}")
        return {'valid': False, 'error': str(e)}

def test_environment_variables():
    """Test that all required environment variables are properly set."""
    print("\n🔍 Testing environment variable configuration...")
    
    required_env_vars = {
        'AI_SERVICE_TYPE': 'embedded',
        'MODELS_PATH': '/app/models',
        'VECTORSTORE_PATH': '/app/data/vectorstore',
        'MAX_CONCURRENT_MODELS': '3',
        'EMBEDDING_MODEL': 'all-MiniLM-L6-v2',
        'DEFAULT_TEMPERATURE': '0.7',
        'DEFAULT_MAX_TOKENS': '1024',
        'CONVERSATION_MEMORY_SIZE': '10'
    }
    
    issues = []
    
    # Read docker-compose.yml to check environment variables
    try:
        import yaml
        with open('docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)
        
        app_env = compose_data.get('services', {}).get('app', {}).get('environment', [])
        
        for var_name, expected_value in required_env_vars.items():
            found = False
            for env_entry in app_env:
                if isinstance(env_entry, str) and f"{var_name}={expected_value}" in env_entry:
                    found = True
                    break
            
            if not found:
                issues.append(f"Environment variable {var_name}={expected_value} not found")
        
        if issues:
            print(f"❌ {len(issues)} environment variable issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All required environment variables properly configured")
            
    except Exception as e:
        issues.append(f"Error reading environment variables: {str(e)}")
    
    return {'valid': len(issues) == 0, 'issues': issues}

def test_volume_configuration():
    """Test volume configuration for data persistence."""
    print("\n🔍 Testing volume configuration...")
    
    required_volumes = [
        'model_data',
        'vectorstore_data', 
        'postgres_data',
        'redis_data'
    ]
    
    issues = []
    
    try:
        import yaml
        with open('docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)
        
        volumes = compose_data.get('volumes', {})
        
        for volume in required_volumes:
            if volume not in volumes:
                issues.append(f"Missing volume: {volume}")
        
        # Check app service volume mounts
        app_service = compose_data.get('services', {}).get('app', {})
        app_volumes = app_service.get('volumes', [])
        
        required_mounts = [
            'model_data:/app/models',
            'vectorstore_data:/app/data'
        ]
        
        for mount in required_mounts:
            mount_found = any(mount in vol for vol in app_volumes)
            if not mount_found:
                issues.append(f"Missing volume mount: {mount}")
        
        if issues:
            print(f"❌ {len(issues)} volume configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Volume configuration is correct")
            
    except Exception as e:
        issues.append(f"Error checking volumes: {str(e)}")
    
    return {'valid': len(issues) == 0, 'issues': issues}

def test_network_configuration():
    """Test network configuration for service communication."""
    print("\n🔍 Testing network configuration...")
    
    issues = []
    
    try:
        import yaml
        with open('docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)
        
        # Check network definition
        networks = compose_data.get('networks', {})
        if 'security-appliance-network' not in networks:
            issues.append("Missing security-appliance-network definition")
        
        # Check that all services use the correct network
        services = compose_data.get('services', {})
        core_services = ['app', 'postgres', 'redis', 'frontend']
        
        for service_name in core_services:
            service = services.get(service_name, {})
            service_networks = service.get('networks', [])
            
            if 'security-appliance-network' not in service_networks:
                issues.append(f"Service {service_name} not connected to security-appliance-network")
        
        if issues:
            print(f"❌ {len(issues)} network configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Network configuration is correct")
            
    except Exception as e:
        issues.append(f"Error checking networks: {str(e)}")
    
    return {'valid': len(issues) == 0, 'issues': issues}

def test_health_checks():
    """Test health check configuration."""
    print("\n🔍 Testing health check configuration...")
    
    issues = []
    
    try:
        import yaml
        with open('docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get('services', {})
        services_with_health_checks = ['app', 'postgres', 'redis', 'frontend']
        
        for service_name in services_with_health_checks:
            service = services.get(service_name, {})
            if 'healthcheck' not in service:
                issues.append(f"Service {service_name} missing health check")
            else:
                health_check = service['healthcheck']
                if 'test' not in health_check:
                    issues.append(f"Service {service_name} health check missing test command")
        
        if issues:
            print(f"❌ {len(issues)} health check issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Health checks properly configured")
            
    except Exception as e:
        issues.append(f"Error checking health checks: {str(e)}")
    
    return {'valid': len(issues) == 0, 'issues': issues}

def test_security_configuration():
    """Test security-related configuration."""
    print("\n🔍 Testing security configuration...")
    
    issues = []
    
    try:
        # Check Dockerfile for non-root user
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()
        
        if 'USER wazuh' not in dockerfile_content:
            issues.append("Dockerfile missing non-root user configuration")
        
        if 'groupadd -r wazuh' not in dockerfile_content:
            issues.append("Dockerfile missing user group creation")
        
        # Check docker-compose for restart policies
        import yaml
        with open('docker-compose.yml', 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get('services', {})
        core_services = ['app', 'postgres', 'redis']
        
        for service_name in core_services:
            service = services.get(service_name, {})
            restart_policy = service.get('restart')
            
            if restart_policy != 'unless-stopped':
                issues.append(f"Service {service_name} missing proper restart policy")
        
        if issues:
            print(f"❌ {len(issues)} security configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Security configuration is correct")
            
    except Exception as e:
        issues.append(f"Error checking security configuration: {str(e)}")
    
    return {'valid': len(issues) == 0, 'issues': issues}

def main():
    """Main test function."""
    print("🧪 Testing Self-Contained Appliance Deployment Configuration")
    print("=" * 70)
    
    # Change to project root if script is run from scripts directory
    if Path.cwd().name == 'scripts':
        os.chdir('..')
    
    results = {}
    
    # Run all tests
    results['docker_syntax'] = test_docker_compose_syntax()
    results['environment'] = test_environment_variables()
    results['volumes'] = test_volume_configuration()
    results['networks'] = test_network_configuration()
    results['health_checks'] = test_health_checks()
    results['security'] = test_security_configuration()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DEPLOYMENT TEST SUMMARY")
    print("=" * 70)
    
    all_valid = True
    total_issues = 0
    
    for component, result in results.items():
        if result.get('skipped'):
            status = "⚠️  SKIP"
            issue_count = 0
        else:
            status = "✅ PASS" if result['valid'] else "❌ FAIL"
            issue_count = len(result.get('issues', []))
            total_issues += issue_count
        
        print(f"{component.upper():15} {status:8} ({issue_count} issues)")
        
        if not result.get('valid', True) and not result.get('skipped'):
            all_valid = False
    
    print("-" * 70)
    
    if all_valid:
        print("🎉 ALL DEPLOYMENT TESTS PASSED!")
        print("✅ Self-contained appliance is ready for deployment")
        print("🚀 Deploy with: docker-compose up -d")
        print("🌐 Access at: http://localhost:3000 (frontend) and http://localhost:8000 (API)")
        return 0
    else:
        print(f"❌ DEPLOYMENT TESTS FAILED ({total_issues} total issues)")
        print("🔧 Please fix the issues above before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())