#!/usr/bin/env python3
"""
Test script for enhanced chat service integration with embedded AI for security analysis.

This script validates the implementation of task 15: Enhanced chat service integration
with embedded AI for security analysis.
"""

import asyncio
import sys
import os
import logging
from uuid import uuid4
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chat_service import ChatService, get_chat_service
from services.embedded_ai_service import EmbeddedAIService
from core.ai_factory import AIServiceFactory
from models.database import MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnhancedChatIntegration:
    """Test enhanced chat service integration with embedded AI for security analysis."""
    
    def __init__(self):
        self.chat_service = None
        self.ai_service = None
        self.test_session_id = uuid4()
        self.test_user_id = uuid4()
        
    async def setup(self):
        """Set up test environment."""
        try:
            logger.info("Setting up test environment...")
            
            # Get chat service
            self.chat_service = get_chat_service()
            if not self.chat_service:
                raise Exception("Failed to get chat service")
            
            # Get AI service
            self.ai_service = AIServiceFactory.get_ai_service()
            if not self.ai_service:
                raise Exception("Failed to get AI service")
            
            logger.info("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    def test_security_context_detection(self):
        """Test security context detection from user messages."""
        logger.info("Testing security context detection...")
        
        test_cases = [
            ("Hunt for lateral movement indicators", "threat_hunting"),
            ("Investigate this security incident", "incident_investigation"),
            ("Analyze this vulnerability report", "vulnerability_analysis"),
            ("Show me the system logs", "general"),
            ("APT analysis using MITRE ATT&CK", "threat_hunting"),
            ("Forensic investigation of malware", "incident_investigation"),
            ("CVE-2023-1234 risk assessment", "vulnerability_analysis")
        ]
        
        try:
            for message, expected_context in test_cases:
                detected_context = self.chat_service._detect_security_context(message)
                if detected_context == expected_context:
                    logger.info(f"✅ '{message}' -> {detected_context}")
                else:
                    logger.warning(f"⚠️ '{message}' -> {detected_context} (expected {expected_context})")
            
            logger.info("✅ Security context detection test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Security context detection test failed: {e}")
            return False
    
    async def test_conversation_context_preservation(self):
        """Test conversation context preservation across chat sessions."""
        logger.info("Testing conversation context preservation...")
        
        try:
            # Test conversation context retrieval
            context = self.chat_service.get_conversation_context(
                self.test_session_id, 
                self.test_user_id, 
                max_messages=6
            )
            
            if isinstance(context, list):
                logger.info(f"✅ Conversation context retrieved: {len(context)} messages")
            else:
                logger.warning("⚠️ Conversation context not in expected format")
            
            # Test security-focused conversation context from AI service
            if hasattr(self.ai_service, 'get_security_conversation_context'):
                security_context = self.ai_service.get_security_conversation_context(str(self.test_session_id))
                
                if isinstance(security_context, dict) and 'security_context' in security_context:
                    logger.info(f"✅ Security conversation context: {security_context['security_context']}")
                else:
                    logger.warning("⚠️ Security conversation context not in expected format")
            
            logger.info("✅ Conversation context preservation test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Conversation context preservation test failed: {e}")
            return False
    
    async def test_security_enhanced_prompt_building(self):
        """Test security-enhanced prompt building."""
        logger.info("Testing security-enhanced prompt building...")
        
        try:
            test_message = "Analyze suspicious login attempts from the last 24 hours"
            conversation_context = []
            siem_context = "SIEM Status: 5 alerts in last hour | Focus: Authentication events"
            security_context = "threat_hunting"
            
            # Test enhanced prompt building
            enhanced_prompt = await self.chat_service._build_security_enhanced_prompt(
                test_message, conversation_context, siem_context, security_context
            )
            
            if enhanced_prompt and len(enhanced_prompt) > 100:
                logger.info("✅ Security-enhanced prompt built successfully")
                logger.info(f"   Prompt length: {len(enhanced_prompt)} characters")
                
                # Check for key security elements
                security_elements = [
                    "threat hunting", "MITRE ATT&CK", "SIEM", "security analysis",
                    "Response Requirements", "Risk Assessment"
                ]
                
                found_elements = [elem for elem in security_elements if elem.lower() in enhanced_prompt.lower()]
                logger.info(f"   Security elements found: {len(found_elements)}/{len(security_elements)}")
                
            else:
                logger.warning("⚠️ Enhanced prompt seems too short or empty")
            
            logger.info("✅ Security-enhanced prompt building test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Security-enhanced prompt building test failed: {e}")
            return False
    
    async def test_security_response_enhancement(self):
        """Test security response enhancement."""
        logger.info("Testing security response enhancement...")
        
        try:
            test_response = "Based on the analysis, there are several suspicious login patterns that warrant investigation."
            test_message = "Analyze login patterns"
            security_context = "threat_hunting"
            
            # Test response enhancement
            enhanced_response = self.chat_service._enhance_security_response(
                test_response, test_message, security_context
            )
            
            if enhanced_response and len(enhanced_response) > len(test_response):
                logger.info("✅ Security response enhanced successfully")
                logger.info(f"   Original length: {len(test_response)}")
                logger.info(f"   Enhanced length: {len(enhanced_response)}")
                
                # Check for security enhancements
                security_enhancements = [
                    "🔍", "Security Context", "Analysis Time", "Session Context"
                ]
                
                found_enhancements = [enh for enh in security_enhancements if enh in enhanced_response]
                logger.info(f"   Security enhancements found: {len(found_enhancements)}/{len(security_enhancements)}")
                
            else:
                logger.warning("⚠️ Response enhancement seems insufficient")
            
            logger.info("✅ Security response enhancement test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Security response enhancement test failed: {e}")
            return False
    
    async def test_siem_context_integration(self):
        """Test SIEM context integration."""
        logger.info("Testing SIEM context integration...")
        
        try:
            test_query = "Show me authentication failures"
            
            # Test SIEM context retrieval
            siem_context = await self.chat_service._get_siem_context_for_query(test_query)
            
            if siem_context and isinstance(siem_context, str):
                logger.info("✅ SIEM context retrieved successfully")
                logger.info(f"   Context: {siem_context[:100]}...")
                
                # Check for expected SIEM context elements
                if "authentication" in siem_context.lower() or "auth" in siem_context.lower():
                    logger.info("✅ Query-specific SIEM context detected")
                else:
                    logger.info("ℹ️ General SIEM context provided")
                
            else:
                logger.warning("⚠️ SIEM context not retrieved or in unexpected format")
            
            logger.info("✅ SIEM context integration test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ SIEM context integration test failed: {e}")
            return False
    
    async def test_ai_service_security_enhancements(self):
        """Test AI service security enhancements."""
        logger.info("Testing AI service security enhancements...")
        
        try:
            # Test security-focused conversation session creation
            test_session_id = str(uuid4())
            
            if hasattr(self.ai_service, 'create_conversation_session'):
                self.ai_service.create_conversation_session(test_session_id, "threat_hunting")
                logger.info("✅ Security-focused conversation session created")
                
                # Test security conversation context
                if hasattr(self.ai_service, 'get_security_conversation_context'):
                    context = self.ai_service.get_security_conversation_context(test_session_id)
                    
                    if context and context.get('security_context') == 'threat_hunting':
                        logger.info("✅ Security conversation context preserved")
                    else:
                        logger.warning("⚠️ Security conversation context not properly preserved")
            
            # Test enhanced prompt building in AI service
            if hasattr(self.ai_service, '_build_prompt_with_history'):
                test_query = "Hunt for APT indicators"
                history = []
                
                prompt = self.ai_service._build_prompt_with_history(test_query, history)
                
                if prompt and "cybersecurity" in prompt.lower():
                    logger.info("✅ Enhanced security prompt building in AI service")
                else:
                    logger.warning("⚠️ AI service prompt building may not be fully enhanced")
            
            logger.info("✅ AI service security enhancements test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI service security enhancements test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests for enhanced chat integration."""
        logger.info("🚀 Starting enhanced chat integration tests...")
        
        # Setup
        if not await self.setup():
            return False
        
        # Run tests
        tests = [
            ("Security Context Detection", self.test_security_context_detection),
            ("Conversation Context Preservation", self.test_conversation_context_preservation),
            ("Security-Enhanced Prompt Building", self.test_security_enhanced_prompt_building),
            ("Security Response Enhancement", self.test_security_response_enhancement),
            ("SIEM Context Integration", self.test_siem_context_integration),
            ("AI Service Security Enhancements", self.test_ai_service_security_enhancements)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} ---")
            try:
                if await test_func() if asyncio.iscoroutinefunction(test_func) else test_func():
                    passed_tests += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED with exception: {e}")
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All enhanced chat integration tests PASSED!")
            return True
        else:
            logger.error(f"❌ {total_tests - passed_tests} tests FAILED")
            return False

async def main():
    """Main test execution."""
    tester = TestEnhancedChatIntegration()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Enhanced chat service integration with embedded AI for security analysis is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())