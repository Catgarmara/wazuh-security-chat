#!/usr/bin/env python3
"""
Docker Configuration Validation Script
Validates docker-compose.yml and docker-compose.prod.yml for embedded AI appliance
"""

import yaml
import sys
from pathlib import Path

def validate_yaml_file(file_path):
    """Validate YAML syntax and structure"""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✓ {file_path}: Valid YAML syntax")
        
        # Check required sections
        required_sections = ['version', 'services', 'volumes', 'networks']
        for section in required_sections:
            if section not in config:
                print(f"✗ {file_path}: Missing required section '{section}'")
                return False
        
        # Check for embedded AI configuration
        app_service = config.get('services', {}).get('app', {})
        environment = app_service.get('environment', [])
        
        # Convert environment list to dict for easier checking
        env_dict = {}
        for env_var in environment:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                env_dict[key] = value
        
        # Check for embedded AI settings
        embedded_ai_vars = [
            'AI_SERVICE_TYPE',
            'MODELS_PATH',
            'VECTORSTORE_PATH',
            'APPLIANCE_MODE'
        ]
        
        for var in embedded_ai_vars:
            if var not in env_dict:
                print(f"✗ {file_path}: Missing embedded AI environment variable '{var}'")
                return False
            elif var == 'AI_SERVICE_TYPE' and env_dict[var] != 'embedded':
                print(f"✗ {file_path}: AI_SERVICE_TYPE should be 'embedded', got '{env_dict[var]}'")
                return False
            elif var == 'APPLIANCE_MODE' and env_dict[var] != 'true':
                print(f"✗ {file_path}: APPLIANCE_MODE should be 'true', got '{env_dict[var]}'")
                return False
        
        # Check for required volumes
        volumes = config.get('volumes', {})
        required_volumes = ['model_data', 'vectorstore_data', 'postgres_data', 'redis_data']
        
        for volume in required_volumes:
            if volume not in volumes:
                print(f"✗ {file_path}: Missing required volume '{volume}'")
                return False
        
        # Check network configuration
        networks = config.get('networks', {})
        if 'security-appliance-network' not in networks:
            print(f"✗ {file_path}: Missing 'security-appliance-network' network")
            return False
        
        # Check that no external AI services are present
        services = config.get('services', {})
        forbidden_services = ['ollama']  # Services that should not exist
        
        for service in forbidden_services:
            if service in services:
                print(f"✗ {file_path}: Found forbidden external AI service '{service}'")
                return False
        
        print(f"✓ {file_path}: All embedded AI appliance requirements met")
        return True
        
    except yaml.YAMLError as e:
        print(f"✗ {file_path}: YAML syntax error - {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path}: Validation error - {e}")
        return False

def validate_deployment_config():
    """Validate deployment-config.yaml"""
    try:
        with open('deployment-config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print("✓ deployment-config.yaml: Valid YAML syntax")
        
        # Check for embedded AI specific configurations
        if 'embedded_ai' not in config.get('performance', {}):
            print("✗ deployment-config.yaml: Missing embedded_ai performance configuration")
            return False
        
        # Check backup configuration includes embedded AI
        if 'embedded_ai' not in config.get('backup', {}):
            print("✗ deployment-config.yaml: Missing embedded_ai backup configuration")
            return False
        
        print("✓ deployment-config.yaml: Embedded AI appliance configuration valid")
        return True
        
    except Exception as e:
        print(f"✗ deployment-config.yaml: Validation error - {e}")
        return False

def validate_backup_config():
    """Validate backup-config.yaml"""
    try:
        with open('backup-config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print("✓ backup-config.yaml: Valid YAML syntax")
        
        # Check for embedded AI backup configuration
        if not config.get('embedded_ai', {}).get('enabled', False):
            print("✗ backup-config.yaml: Embedded AI backup not enabled")
            return False
        
        # Check for model_data volume backup
        volumes = config.get('volumes', {})
        if 'model_data' not in volumes:
            print("✗ backup-config.yaml: Missing model_data volume backup configuration")
            return False
        
        if 'vectorstore_data' not in volumes:
            print("✗ backup-config.yaml: Missing vectorstore_data volume backup configuration")
            return False
        
        print("✓ backup-config.yaml: Embedded AI backup configuration valid")
        return True
        
    except Exception as e:
        print(f"✗ backup-config.yaml: Validation error - {e}")
        return False

def main():
    """Main validation function"""
    print("Validating Docker configuration for embedded AI appliance...")
    print("=" * 60)
    
    all_valid = True
    
    # Validate docker-compose files
    for file_path in ['docker-compose.yml', 'docker-compose.prod.yml']:
        if Path(file_path).exists():
            if not validate_yaml_file(file_path):
                all_valid = False
        else:
            print(f"✗ {file_path}: File not found")
            all_valid = False
    
    # Validate configuration files
    if not validate_deployment_config():
        all_valid = False
    
    if not validate_backup_config():
        all_valid = False
    
    print("=" * 60)
    if all_valid:
        print("✓ All Docker configurations are valid for embedded AI appliance")
        return 0
    else:
        print("✗ Some Docker configurations have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())