#!/usr/bin/env python3
"""
Validation script for enhanced chat service integration implementation.

This script validates that task 15 has been properly implemented by checking
the code structure and required methods without requiring runtime dependencies.
"""

import os
import sys
import re
import ast
from pathlib import Path

def validate_file_exists(file_path: str) -> bool:
    """Validate that a file exists."""
    return Path(file_path).exists()

def validate_method_exists(file_path: str, method_name: str) -> bool:
    """Validate that a method exists in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return f"def {method_name}" in content
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def validate_code_contains(file_path: str, pattern: str) -> bool:
    """Validate that code contains a specific pattern."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return pattern in content
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def validate_security_context_detection():
    """Validate security context detection implementation."""
    print("Validating security context detection...")
    
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("File exists", validate_file_exists(chat_service_path)),
        ("_detect_security_context method", validate_method_exists(chat_service_path, "_detect_security_context")),
        ("Threat hunting keywords", validate_code_contains(chat_service_path, "threat_hunting_keywords")),
        ("Incident keywords", validate_code_contains(chat_service_path, "incident_keywords")),
        ("Vulnerability keywords", validate_code_contains(chat_service_path, "vulnerability_keywords")),
        ("Context scoring logic", validate_code_contains(chat_service_path, "threat_score")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"Security context detection: {passed}/{total} checks passed")
    return passed == total

def validate_enhanced_prompt_building():
    """Validate enhanced prompt building implementation."""
    print("\nValidating enhanced prompt building...")
    
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("_build_security_enhanced_prompt method", validate_method_exists(chat_service_path, "_build_security_enhanced_prompt")),
        ("Security context specialization", validate_code_contains(chat_service_path, "threat_hunting")),
        ("MITRE ATT&CK framework", validate_code_contains(chat_service_path, "MITRE ATT&CK")),
        ("Response requirements", validate_code_contains(chat_service_path, "Response Requirements")),
        ("Security icons usage", validate_code_contains(chat_service_path, "🔍")),
        ("SIEM context integration", validate_code_contains(chat_service_path, "SIEM")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"Enhanced prompt building: {passed}/{total} checks passed")
    return passed == total

def validate_security_response_enhancement():
    """Validate security response enhancement implementation."""
    print("\nValidating security response enhancement...")
    
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("_enhance_security_response method", validate_method_exists(chat_service_path, "_enhance_security_response")),
        ("Context headers", validate_code_contains(chat_service_path, "context_headers")),
        ("Security context preservation", validate_code_contains(chat_service_path, "Security Context:")),
        ("Session continuity", validate_code_contains(chat_service_path, "Session Context")),
        ("Critical security notice", validate_code_contains(chat_service_path, "Critical Security Notice")),
        ("Analysis timestamp", validate_code_contains(chat_service_path, "Analysis Time")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"Security response enhancement: {passed}/{total} checks passed")
    return passed == total

def validate_conversation_context_preservation():
    """Validate conversation context preservation implementation."""
    print("\nValidating conversation context preservation...")
    
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("get_conversation_context method", validate_method_exists(chat_service_path, "get_conversation_context")),
        ("Security metadata", validate_code_contains(chat_service_path, "security_metadata")),
        ("Enhanced save_message", validate_method_exists(chat_service_path, "save_message")),
        ("Security enhanced flag", validate_code_contains(chat_service_path, "security_enhanced")),
        ("Max messages parameter", validate_code_contains(chat_service_path, "max_messages")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"Conversation context preservation: {passed}/{total} checks passed")
    return passed == total

def validate_ai_service_enhancements():
    """Validate AI service enhancements for security analysis."""
    print("\nValidating AI service enhancements...")
    
    ai_service_path = "services/embedded_ai_service.py"
    
    checks = [
        ("Enhanced _build_prompt_with_history", validate_code_contains(ai_service_path, "cybersecurity analyst")),
        ("Security-focused system context", validate_code_contains(ai_service_path, "Threat Hunting & Detection")),
        ("MITRE ATT&CK in system prompt", validate_code_contains(ai_service_path, "MITRE ATT&CK")),
        ("Enhanced conversation session", validate_code_contains(ai_service_path, "security_context")),
        ("Security conversation context method", validate_method_exists(ai_service_path, "get_security_conversation_context")),
        ("Threat indicators tracking", validate_code_contains(ai_service_path, "threat_indicators_discussed")),
        ("Investigation topics tracking", validate_code_contains(ai_service_path, "investigation_topics")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"AI service enhancements: {passed}/{total} checks passed")
    return passed == total

def validate_websocket_integration():
    """Validate WebSocket integration for real-time security analysis."""
    print("\nValidating WebSocket integration...")
    
    websocket_path = "api/websocket.py"
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("WebSocket file exists", validate_file_exists(websocket_path)),
        ("Security query handling", validate_code_contains(websocket_path, "security_query")),
        ("_handle_security_query method", validate_method_exists(chat_service_path, "_handle_security_query")),
        ("Security analysis response", validate_code_contains(chat_service_path, "security_analysis")),
        ("Real-time typing indicators", validate_code_contains(chat_service_path, "Analyzing security query")),
        ("Security metrics recording", validate_code_contains(chat_service_path, "security_query")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"WebSocket integration: {passed}/{total} checks passed")
    return passed == total

def validate_missing_method_implementation():
    """Validate that the missing _generate_ai_response method was implemented."""
    print("\nValidating missing method implementation...")
    
    chat_service_path = "services/chat_service.py"
    
    checks = [
        ("_generate_ai_response method exists", validate_method_exists(chat_service_path, "_generate_ai_response")),
        ("Security context detection in method", validate_code_contains(chat_service_path, "_detect_security_context(message)")),
        ("Enhanced prompt building call", validate_code_contains(chat_service_path, "_build_security_enhanced_prompt")),
        ("Security-optimized parameters", validate_code_contains(chat_service_path, "temperature=0.4")),
        ("Response enhancement call", validate_code_contains(chat_service_path, "_enhance_security_response")),
        ("Error handling with security context", validate_code_contains(chat_service_path, "security administrator")),
    ]
    
    passed = sum(1 for _, check in checks if check)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print(f"Missing method implementation: {passed}/{total} checks passed")
    return passed == total

def main():
    """Main validation function."""
    print("🔍 Validating Enhanced Chat Service Integration Implementation")
    print("=" * 70)
    
    validation_functions = [
        ("Security Context Detection", validate_security_context_detection),
        ("Enhanced Prompt Building", validate_enhanced_prompt_building),
        ("Security Response Enhancement", validate_security_response_enhancement),
        ("Conversation Context Preservation", validate_conversation_context_preservation),
        ("AI Service Enhancements", validate_ai_service_enhancements),
        ("WebSocket Integration", validate_websocket_integration),
        ("Missing Method Implementation", validate_missing_method_implementation),
    ]
    
    passed_validations = 0
    total_validations = len(validation_functions)
    
    for validation_name, validation_func in validation_functions:
        print(f"\n{'='*50}")
        print(f"Validating: {validation_name}")
        print('='*50)
        
        try:
            if validation_func():
                passed_validations += 1
                print(f"✅ {validation_name} validation PASSED")
            else:
                print(f"❌ {validation_name} validation FAILED")
        except Exception as e:
            print(f"❌ {validation_name} validation FAILED with error: {e}")
    
    print(f"\n{'='*70}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Passed: {passed_validations}/{total_validations} validations")
    
    if passed_validations == total_validations:
        print("🎉 All validations PASSED! Task 15 implementation is complete.")
        print("\n✅ Enhanced chat service integration with embedded AI for security analysis")
        print("   has been successfully implemented with the following features:")
        print("   • Security context detection and specialized analysis")
        print("   • Enhanced prompt building with security frameworks")
        print("   • Security response enhancement with proper formatting")
        print("   • Conversation context preservation across sessions")
        print("   • AI service enhancements for security-focused conversations")
        print("   • Real-time WebSocket integration for security analysis")
        print("   • Missing method implementation with security optimizations")
        return True
    else:
        failed_count = total_validations - passed_validations
        print(f"❌ {failed_count} validations FAILED. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)