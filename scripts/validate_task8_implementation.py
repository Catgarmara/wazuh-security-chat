#!/usr/bin/env python3
"""
Validation script for Task 8: Update appliance deployment and backup scripts
This script validates that external AI service references have been removed
and that the scripts are configured for the embedded AI appliance.
"""

import os
import sys
import yaml
import json
from typing import List, Dict, Any


def validate_backup_script() -> List[str]:
    """Validate backup.py script for embedded AI appliance configuration."""
    issues = []
    
    backup_script_path = "scripts/backup.py"
    if not os.path.exists(backup_script_path):
        issues.append("❌ backup.py script not found")
        return issues
    
    with open(backup_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for embedded AI specific configurations
    required_patterns = [
        "embedded_ai",
        "models_path",
        "vectorstore_path",
        "backup_model_configs",
        "SecurityApplianceBackupManager"
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            issues.append(f"❌ backup.py missing embedded AI pattern: {pattern}")
    
    # Check that external AI service references are removed
    forbidden_patterns = [
        "ollama",
        "openai",
        "anthropic",
        "external_ai"
    ]
    
    for pattern in forbidden_patterns:
        if pattern.lower() in content.lower():
            issues.append(f"❌ backup.py contains external AI reference: {pattern}")
    
    if not issues:
        issues.append("✅ backup.py properly configured for embedded AI appliance")
    
    return issues


def validate_deploy_script() -> List[str]:
    """Validate deploy.py script for embedded AI appliance configuration."""
    issues = []
    
    deploy_script_path = "scripts/deploy.py"
    if not os.path.exists(deploy_script_path):
        issues.append("❌ deploy.py script not found")
        return issues
    
    with open(deploy_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for embedded AI specific configurations
    required_patterns = [
        "AI_SERVICE_TYPE=embedded",
        "MODELS_PATH",
        "VECTORSTORE_PATH",
        "APPLIANCE_MODE=true",
        "SecurityApplianceDeployer",
        "No External Dependencies"
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            issues.append(f"❌ deploy.py missing embedded AI pattern: {pattern}")
    
    # Check that external AI service references are removed
    forbidden_patterns = [
        "OLLAMA_",
        "OPENAI_",
        "ANTHROPIC_",
        "WazuhDeployer"  # Old class name
    ]
    
    for pattern in forbidden_patterns:
        if pattern in content:
            issues.append(f"❌ deploy.py contains external AI reference: {pattern}")
    
    if not issues:
        issues.append("✅ deploy.py properly configured for embedded AI appliance")
    
    return issues


def validate_health_check_script() -> List[str]:
    """Validate health_check.py script for embedded AI appliance monitoring."""
    issues = []
    
    health_script_path = "scripts/health_check.py"
    if not os.path.exists(health_script_path):
        issues.append("❌ health_check.py script not found")
        return issues
    
    with open(health_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for embedded AI specific monitoring
    required_patterns = [
        "embedded_ai",
        "check_embedded_ai_status",
        "check_appliance_components",
        "embedded AI appliance"
    ]
    
    for pattern in required_patterns:
        if pattern not in content:
            issues.append(f"❌ health_check.py missing embedded AI pattern: {pattern}")
    
    if not issues:
        issues.append("✅ health_check.py properly configured for embedded AI appliance")
    
    return issues


def validate_deployment_config() -> List[str]:
    """Validate deployment-config.yaml for embedded AI appliance."""
    issues = []
    
    config_path = "deployment-config.yaml"
    if not os.path.exists(config_path):
        issues.append("❌ deployment-config.yaml not found")
        return issues
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check for embedded AI specific configurations
        if 'kubernetes' in config:
            k8s_config = config['kubernetes']
            if 'storage' in k8s_config:
                storage = k8s_config['storage']
                if 'embedded_models_size' not in storage:
                    issues.append("❌ deployment-config.yaml missing embedded_models_size")
                else:
                    issues.append("✅ deployment-config.yaml has embedded AI storage configuration")
        
        # Check for security appliance namespace
        if config.get('kubernetes', {}).get('namespace') == 'security-ai-appliance':
            issues.append("✅ deployment-config.yaml uses security appliance namespace")
        else:
            issues.append("❌ deployment-config.yaml missing security appliance namespace")
        
        # Check for embedded AI performance settings
        if 'embedded_ai' in config.get('performance', {}):
            issues.append("✅ deployment-config.yaml has embedded AI performance settings")
        else:
            issues.append("❌ deployment-config.yaml missing embedded AI performance settings")
        
    except yaml.YAMLError as e:
        issues.append(f"❌ deployment-config.yaml YAML parsing error: {e}")
    except Exception as e:
        issues.append(f"❌ deployment-config.yaml validation error: {e}")
    
    return issues


def validate_backup_config() -> List[str]:
    """Validate backup-config.yaml for embedded AI appliance."""
    issues = []
    
    config_path = "backup-config.yaml"
    if not os.path.exists(config_path):
        issues.append("❌ backup-config.yaml not found")
        return issues
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check for embedded AI backup configuration
        if 'embedded_ai' in config:
            embedded_ai = config['embedded_ai']
            required_keys = ['enabled', 'models_path', 'vectorstore_path']
            for key in required_keys:
                if key not in embedded_ai:
                    issues.append(f"❌ backup-config.yaml missing embedded_ai.{key}")
            
            if all(key in embedded_ai for key in required_keys):
                issues.append("✅ backup-config.yaml has embedded AI backup configuration")
        else:
            issues.append("❌ backup-config.yaml missing embedded_ai section")
        
        # Check for embedded models volume
        if 'volumes' in config and 'embedded_models' in config['volumes']:
            issues.append("✅ backup-config.yaml has embedded_models volume configuration")
        else:
            issues.append("❌ backup-config.yaml missing embedded_models volume")
        
        # Check for security appliance S3 bucket
        if config.get('s3', {}).get('bucket') == 'security-ai-appliance-backups':
            issues.append("✅ backup-config.yaml uses security appliance S3 bucket")
        else:
            issues.append("❌ backup-config.yaml missing security appliance S3 bucket")
        
    except yaml.YAMLError as e:
        issues.append(f"❌ backup-config.yaml YAML parsing error: {e}")
    except Exception as e:
        issues.append(f"❌ backup-config.yaml validation error: {e}")
    
    return issues


def main():
    """Main validation function."""
    print("🔍 Validating Task 8: Update appliance deployment and backup scripts")
    print("=" * 80)
    
    all_issues = []
    
    # Validate all components
    validation_functions = [
        ("Backup Script", validate_backup_script),
        ("Deploy Script", validate_deploy_script),
        ("Health Check Script", validate_health_check_script),
        ("Deployment Config", validate_deployment_config),
        ("Backup Config", validate_backup_config)
    ]
    
    for component_name, validation_func in validation_functions:
        print(f"\n📋 Validating {component_name}:")
        print("-" * 40)
        
        issues = validation_func()
        for issue in issues:
            print(f"  {issue}")
        
        all_issues.extend(issues)
    
    # Summary
    success_count = len([issue for issue in all_issues if issue.startswith("✅")])
    error_count = len([issue for issue in all_issues if issue.startswith("❌")])
    
    print(f"\n📊 Validation Summary:")
    print("=" * 40)
    print(f"✅ Successful validations: {success_count}")
    print(f"❌ Failed validations: {error_count}")
    
    if error_count == 0:
        print("\n🎉 All validations passed! Task 8 implementation is complete.")
        return True
    else:
        print(f"\n⚠️ {error_count} validation issues found. Please review and fix.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)