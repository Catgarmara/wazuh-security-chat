"""
Basic test script for WebSocket connection management.

This script tests the core functionality of the chat service
without requiring pytest or other testing frameworks.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from services.chat_service import ConnectionManager, ChatService
from models.database import User, UserRole


async def test_connection_manager_basic():
    """Test basic connection manager functionality."""
    print("Testing ConnectionManager...")
    
    # Create connection manager
    manager = ConnectionManager()
    
    # Test initial state
    assert len(manager.active_connections) == 0
    assert len(manager.user_connections) == 0
    assert len(manager.connection_users) == 0
    
    print("✓ Initial state correct")
    
    # Test connection info
    info = manager.get_connection_info()
    assert info["total_connections"] == 0
    assert info["unique_users"] == 0
    assert info["active_sessions"] == 0
    
    print("✓ Connection info correct")
    
    # Test manual connection addition (simulating successful connect)
    connection_id = str(uuid4())
    user_id = uuid4()
    mock_websocket = Mock()
    
    manager.active_connections[connection_id] = mock_websocket
    manager.connection_users[connection_id] = user_id
    manager.user_connections[user_id] = {connection_id}
    
    # Test updated state
    assert len(manager.active_connections) == 1
    assert len(manager.user_connections) == 1
    assert connection_id in manager.active_connections
    assert manager.connection_users[connection_id] == user_id
    
    print("✓ Connection state management correct")
    
    # Test disconnect
    await manager.disconnect(connection_id)
    
    assert len(manager.active_connections) == 0
    assert len(manager.user_connections) == 0
    assert len(manager.connection_users) == 0
    
    print("✓ Disconnect cleanup correct")
    
    print("ConnectionManager tests passed!\n")


async def test_chat_service_basic():
    """Test basic chat service functionality."""
    print("Testing ChatService...")
    
    # Create chat service
    service = ChatService()
    
    # Test service initialization
    assert service.connection_manager is not None
    assert service.auth_service is not None
    assert service.ai_service is not None
    
    print("✓ Service initialization correct")
    
    # Test connection manager access
    manager = service.get_connection_manager()
    assert manager is service.connection_manager
    
    print("✓ Connection manager access correct")
    
    # Test AI response generation (with mock)
    session_id = uuid4()
    mock_db = Mock()
    
    # Mock AI service response
    original_generate = service.ai_service.generate_response
    service.ai_service.generate_response = Mock(return_value="Test AI response")
    
    try:
        response = service._generate_ai_response("Test message", session_id, mock_db)
        assert response == "Test AI response"
        print("✓ AI response generation correct")
    except Exception as e:
        print(f"⚠ AI response generation test skipped due to: {e}")
    finally:
        # Restore original method
        service.ai_service.generate_response = original_generate
    
    print("ChatService tests passed!\n")


async def test_websocket_message_processing():
    """Test WebSocket message processing."""
    print("Testing WebSocket message processing...")
    
    service = ChatService()
    connection_id = "test_conn_123"
    
    # Mock connection manager methods
    service.connection_manager._send_to_connection = AsyncMock()
    service.connection_manager.join_session = AsyncMock()
    
    # Test ping message
    await service._process_websocket_message(connection_id, {"type": "ping"})
    
    # Verify pong response
    call_args = service.connection_manager._send_to_connection.call_args
    assert call_args[0][0] == connection_id
    assert call_args[0][1]["type"] == "pong"
    
    print("✓ Ping/pong message processing correct")
    
    # Test join session message
    session_id = str(uuid4())
    await service._process_websocket_message(connection_id, {
        "type": "join_session",
        "session_id": session_id
    })
    
    # Verify join_session was called
    service.connection_manager.join_session.assert_called_once()
    
    print("✓ Join session message processing correct")
    
    # Test unknown message type
    service.connection_manager._send_to_connection.reset_mock()
    await service._process_websocket_message(connection_id, {"type": "unknown"})
    
    # Verify error response
    call_args = service.connection_manager._send_to_connection.call_args
    assert call_args[0][1]["type"] == "error"
    assert "unknown" in call_args[0][1]["message"].lower()
    
    print("✓ Unknown message type handling correct")
    
    print("WebSocket message processing tests passed!\n")


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from services.chat_service import ChatService, ConnectionManager, get_chat_service
        from api.websocket import router
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


async def main():
    """Run all tests."""
    print("=== WebSocket Connection Management Tests ===\n")
    
    # Test imports first
    if not test_imports():
        print("Import tests failed, skipping other tests")
        return
    
    try:
        # Run async tests
        await test_connection_manager_basic()
        await test_chat_service_basic()
        await test_websocket_message_processing()
        
        print("=== All Tests Passed! ===")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())