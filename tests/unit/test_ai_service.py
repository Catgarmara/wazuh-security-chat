"""
Test script for AI Service functionality.

This script tests the basic functionality of the AIService class
to ensure it works correctly after refactoring from the monolithic chatbot.py.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock


def test_ai_service_initialization():
    """Test AI service initialization."""
    print("Testing AI service initialization...")
    
    try:
        # Mock all the langchain imports at module level
        with patch.dict('sys.modules', {
            'langchain.text_splitter': MagicMock(),
            'langchain_community.vectorstores': MagicMock(),
            'langchain_huggingface': MagicMock(),
            'langchain_ollama': MagicMock(),
            'langchain.chains': MagicMock(),
            'langchain.schema': MagicMock(),
            'langchain.schema.messages': MagicMock(),
            'langchain.memory': MagicMock(),
            'core.exceptions': MagicMock()
        }):
            # Mock the specific classes
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings, \
                 patch('services.ai_service.ChatOllama') as mock_llm, \
                 patch('services.ai_service.Path') as mock_path:
                
                mock_embeddings.return_value = Mock()
                mock_llm.return_value = Mock()
                mock_path.return_value.mkdir = Mock()
                
                from services.ai_service import AIService
                ai_service = AIService()
                
                assert ai_service.embedding_model_name == "all-MiniLM-L6-v2"
                assert ai_service.llm_model == "llama3"
                assert ai_service.max_retries == 3
                assert ai_service.retry_delay == 1.0
                assert ai_service.conversation_memory_size == 10
                
                print("✅ AI service initialization test passed")
                return True
            
    except Exception as e:
        print(f"❌ AI service initialization test failed: {e}")
        return False


def test_conversation_management():
    """Test conversation session management."""
    print("Testing conversation management...")
    
    try:
        with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings, \
             patch('services.ai_service.ChatOllama') as mock_llm:
            
            mock_embeddings.return_value = Mock()
            mock_llm.return_value = Mock()
            
            ai_service = AIService()
            
            # Test session creation
            session_id = "test_session"
            ai_service.create_conversation_session(session_id)
            
            assert session_id in ai_service.conversation_sessions
            assert len(ai_service.conversation_sessions[session_id]["history"]) == 1  # System message
            
            # Test adding messages
            from langchain.schema.messages import HumanMessage
            ai_service.add_to_conversation_history(session_id, HumanMessage(content="Test message"))
            
            assert len(ai_service.conversation_sessions[session_id]["history"]) == 2
            
            # Test clearing history
            ai_service.clear_conversation_history(session_id)
            assert len(ai_service.conversation_sessions[session_id]["history"]) == 1  # Back to system message only
            
            print("✅ Conversation management test passed")
            return True
            
    except Exception as e:
        print(f"❌ Conversation management test failed: {e}")
        return False


def test_vectorstore_management():
    """Test vector store management functionality."""
    print("Testing vector store management...")
    
    try:
        with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings, \
             patch('services.ai_service.ChatOllama') as mock_llm, \
             patch('services.ai_service.FAISS') as mock_faiss:
            
            mock_embeddings.return_value = Mock()
            mock_llm.return_value = Mock()
            mock_vectorstore = Mock()
            mock_faiss.from_documents.return_value = mock_vectorstore
            
            ai_service = AIService()
            
            # Test vector store creation
            test_logs = [
                {"full_log": "Test log entry 1"},
                {"full_log": "Test log entry 2"}
            ]
            
            vectorstore = ai_service.create_vectorstore(test_logs)
            assert vectorstore is not None
            assert ai_service.vectorstore is not None
            
            # Test vector store info
            info = ai_service.get_vectorstore_info()
            assert "status" in info
            
            print("✅ Vector store management test passed")
            return True
            
    except Exception as e:
        print(f"❌ Vector store management test failed: {e}")
        return False


def test_service_readiness():
    """Test service readiness check."""
    print("Testing service readiness...")
    
    try:
        with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings, \
             patch('services.ai_service.ChatOllama') as mock_llm:
            
            mock_embeddings.return_value = Mock()
            mock_llm.return_value = Mock()
            
            ai_service = AIService()
            
            # Service should be ready after initialization
            assert ai_service.is_ready() == True
            
            # Test configuration retrieval
            config = ai_service.get_llm_config()
            assert "llm_model" in config
            assert "embedding_model" in config
            assert "max_retries" in config
            
            print("✅ Service readiness test passed")
            return True
            
    except Exception as e:
        print(f"❌ Service readiness test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running AI Service tests...\n")
    
    tests = [
        test_ai_service_initialization,
        test_conversation_management,
        test_vectorstore_management,
        test_service_readiness
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AI Service refactoring successful.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)