"""
Tests for the chat service and WebSocket connection management.

This module tests WebSocket connection handling, user authentication,
session management, and message broadcasting functionality.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import WebSocket, HTTPException, status
from sqlalchemy.orm import Session

from services.chat_service import ChatService, ConnectionManager, get_chat_service
from models.database import User, ChatSession, Message, MessageRole, UserRole
from models.schemas import ChatMessageRequest, ChatMessageResponse


class TestConnectionManager:
    """Test cases for WebSocket connection manager."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a connection manager instance for testing."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.ANALYST,
            is_active=True
        )
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock chat session for testing."""
        return ChatSession(
            id=uuid4(),
            user_id=uuid4(),
            title="Test Session",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_connect_success(self, connection_manager, mock_websocket, mock_user):
        """Test successful WebSocket connection with authentication."""
        token = "valid_jwt_token"
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Test connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Verify connection was established
            assert connection_id in connection_manager.active_connections
            assert connection_manager.active_connections[connection_id] == mock_websocket
            assert connection_manager.connection_users[connection_id] == mock_user.id
            assert mock_user.id in connection_manager.user_connections
            assert connection_id in connection_manager.user_connections[mock_user.id]
            
            # Verify WebSocket was accepted and confirmation sent
            mock_websocket.accept.assert_called_once()
            mock_websocket.send_text.assert_called_once()
            
            # Verify confirmation message
            sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_message["type"] == "connection_established"
            assert sent_message["user_id"] == str(mock_user.id)
    
    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, connection_manager, mock_websocket):
        """Test WebSocket connection with authentication failure."""
        token = "invalid_jwt_token"
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', 
                         side_effect=HTTPException(status_code=401, detail="Invalid token")):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Test connection should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await connection_manager.connect(mock_websocket, token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            
            # Verify WebSocket was accepted but then closed
            mock_websocket.accept.assert_called_once()
            mock_websocket.close.assert_called_once_with(code=status.WS_1008_POLICY_VIOLATION)
    
    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_websocket, mock_user):
        """Test WebSocket disconnection and cleanup."""
        token = "valid_jwt_token"
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Establish connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Verify connection exists
            assert connection_id in connection_manager.active_connections
            
            # Disconnect
            await connection_manager.disconnect(connection_id)
            
            # Verify cleanup
            assert connection_id not in connection_manager.active_connections
            assert connection_id not in connection_manager.connection_users
            assert mock_user.id not in connection_manager.user_connections
    
    @pytest.mark.asyncio
    async def test_join_session_success(self, connection_manager, mock_websocket, mock_user, mock_session):
        """Test successfully joining a chat session."""
        token = "valid_jwt_token"
        mock_session.user_id = mock_user.id
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_session
            
            # Establish connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Join session
            await connection_manager.join_session(connection_id, mock_session.id)
            
            # Verify session joined
            assert connection_manager.connection_sessions[connection_id] == mock_session.id
            assert mock_session.id in connection_manager.session_connections
            assert connection_id in connection_manager.session_connections[mock_session.id]
            
            # Verify confirmation message sent
            assert mock_websocket.send_text.call_count >= 2  # Connection + session joined
    
    @pytest.mark.asyncio
    async def test_join_session_access_denied(self, connection_manager, mock_websocket, mock_user):
        """Test joining a session with access denied."""
        token = "valid_jwt_token"
        session_id = uuid4()
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None  # Session not found
            
            # Establish connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Try to join session
            await connection_manager.join_session(connection_id, session_id)
            
            # Verify session not joined
            assert connection_id not in connection_manager.connection_sessions
            
            # Verify error message sent
            sent_messages = [call[0][0] for call in mock_websocket.send_text.call_args_list]
            error_message = next((json.loads(msg) for msg in sent_messages 
                                if json.loads(msg).get("type") == "error"), None)
            assert error_message is not None
            assert "access denied" in error_message["message"].lower()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, connection_manager, mock_websocket, mock_user):
        """Test broadcasting message to all connections in a session."""
        token = "valid_jwt_token"
        session_id = uuid4()
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Establish connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Manually add to session (simulating successful join)
            connection_manager.connection_sessions[connection_id] = session_id
            connection_manager.session_connections[session_id] = {connection_id}
            
            # Broadcast message
            test_message = {"type": "test", "content": "Hello"}
            await connection_manager.broadcast_to_session(session_id, test_message)
            
            # Verify message was sent
            sent_messages = [call[0][0] for call in mock_websocket.send_text.call_args_list]
            broadcast_message = next((json.loads(msg) for msg in sent_messages 
                                    if json.loads(msg).get("type") == "test"), None)
            assert broadcast_message is not None
            assert broadcast_message["content"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_send_to_user(self, connection_manager, mock_websocket, mock_user):
        """Test sending message to all connections of a specific user."""
        token = "valid_jwt_token"
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(connection_manager.auth_service, 'get_current_user', return_value=mock_user):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Establish connection
            connection_id = await connection_manager.connect(mock_websocket, token)
            
            # Send message to user
            test_message = {"type": "notification", "content": "User message"}
            await connection_manager.send_to_user(mock_user.id, test_message)
            
            # Verify message was sent
            sent_messages = [call[0][0] for call in mock_websocket.send_text.call_args_list]
            user_message = next((json.loads(msg) for msg in sent_messages 
                               if json.loads(msg).get("type") == "notification"), None)
            assert user_message is not None
            assert user_message["content"] == "User message"
    
    def test_get_connection_info(self, connection_manager):
        """Test getting connection information."""
        # Add some mock connections
        user_id1 = uuid4()
        user_id2 = uuid4()
        session_id = uuid4()
        
        connection_manager.active_connections = {"conn1": Mock(), "conn2": Mock(), "conn3": Mock()}
        connection_manager.user_connections = {
            user_id1: {"conn1", "conn2"},
            user_id2: {"conn3"}
        }
        connection_manager.session_connections = {session_id: {"conn1", "conn2"}}
        
        info = connection_manager.get_connection_info()
        
        assert info["total_connections"] == 3
        assert info["unique_users"] == 2
        assert info["active_sessions"] == 1
        assert len(info["connections_per_user"]) == 2


class TestChatService:
    """Test cases for chat service."""
    
    @pytest.fixture
    def chat_service(self):
        """Create a chat service instance for testing."""
        return ChatService()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.receive_text = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.ANALYST,
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_handle_websocket_connection_success(self, chat_service, mock_websocket, mock_user):
        """Test successful WebSocket connection handling."""
        token = "valid_jwt_token"
        
        with patch.object(chat_service.connection_manager, 'connect', return_value="conn123") as mock_connect, \
             patch.object(chat_service.connection_manager, 'disconnect') as mock_disconnect:
            
            # Mock WebSocket to disconnect after one message
            mock_websocket.receive_text.side_effect = [
                json.dumps({"type": "ping"}),
                Exception("WebSocketDisconnect")  # Simulate disconnect
            ]
            
            # Handle connection (should not raise exception)
            await chat_service.handle_websocket_connection(mock_websocket, token)
            
            # Verify connection and disconnection were called
            mock_connect.assert_called_once_with(mock_websocket, token)
            mock_disconnect.assert_called_once_with("conn123")
    
    @pytest.mark.asyncio
    async def test_process_ping_message(self, chat_service):
        """Test processing ping message."""
        connection_id = "conn123"
        message_data = {"type": "ping"}
        
        with patch.object(chat_service.connection_manager, '_send_to_connection') as mock_send:
            await chat_service._process_websocket_message(connection_id, message_data)
            
            # Verify pong response was sent
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][1]
            assert sent_message["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_process_join_session_message(self, chat_service):
        """Test processing join session message."""
        connection_id = "conn123"
        session_id = str(uuid4())
        message_data = {"type": "join_session", "session_id": session_id}
        
        with patch.object(chat_service.connection_manager, 'join_session') as mock_join:
            await chat_service._process_websocket_message(connection_id, message_data)
            
            # Verify join_session was called
            mock_join.assert_called_once_with(connection_id, UUID(session_id))
    
    @pytest.mark.asyncio
    async def test_process_unknown_message_type(self, chat_service):
        """Test processing unknown message type."""
        connection_id = "conn123"
        message_data = {"type": "unknown_type"}
        
        with patch.object(chat_service.connection_manager, '_send_to_connection') as mock_send:
            await chat_service._process_websocket_message(connection_id, message_data)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][1]
            assert sent_message["type"] == "error"
            assert "unknown_type" in sent_message["message"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_chat_message_success(self, chat_service, mock_user):
        """Test successful chat message handling."""
        connection_id = "conn123"
        session_id = uuid4()
        user_id = mock_user.id
        message_content = "Hello, AI!"
        
        message_data = {"message": message_content}
        
        # Mock connection manager state
        chat_service.connection_manager.connection_users[connection_id] = user_id
        chat_service.connection_manager.connection_sessions[connection_id] = session_id
        
        with patch('services.chat_service.get_db_session') as mock_db_session, \
             patch.object(chat_service.connection_manager, 'broadcast_to_session') as mock_broadcast, \
             patch.object(chat_service, '_generate_ai_response', return_value="AI response"):
            
            mock_db = Mock(spec=Session)
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Mock message creation
            mock_user_message = Mock()
            mock_user_message.id = uuid4()
            mock_user_message.timestamp = datetime.utcnow()
            mock_ai_message = Mock()
            mock_ai_message.id = uuid4()
            mock_ai_message.timestamp = datetime.utcnow()
            
            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.side_effect = [mock_user_message, mock_ai_message]
            
            await chat_service._handle_chat_message(connection_id, message_data)
            
            # Verify messages were broadcast
            assert mock_broadcast.call_count >= 4  # User message, typing on, typing off, AI response
    
    @pytest.mark.asyncio
    async def test_handle_chat_message_no_session(self, chat_service):
        """Test chat message handling when not connected to session."""
        connection_id = "conn123"
        message_data = {"message": "Hello"}
        
        with patch.object(chat_service.connection_manager, '_send_to_connection') as mock_send:
            await chat_service._handle_chat_message(connection_id, message_data)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][1]
            assert sent_message["type"] == "error"
            assert "not connected to a session" in sent_message["message"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_chat_message_empty_message(self, chat_service, mock_user):
        """Test chat message handling with empty message."""
        connection_id = "conn123"
        session_id = uuid4()
        user_id = mock_user.id
        
        message_data = {"message": "   "}  # Empty/whitespace message
        
        # Mock connection manager state
        chat_service.connection_manager.connection_users[connection_id] = user_id
        chat_service.connection_manager.connection_sessions[connection_id] = session_id
        
        with patch.object(chat_service.connection_manager, '_send_to_connection') as mock_send:
            await chat_service._handle_chat_message(connection_id, message_data)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][1]
            assert sent_message["type"] == "error"
            assert "empty message" in sent_message["message"].lower()
    
    def test_generate_ai_response_success(self, chat_service):
        """Test successful AI response generation."""
        message = "What are the latest security alerts?"
        session_id = uuid4()
        mock_db = Mock(spec=Session)
        
        with patch.object(chat_service.ai_service, 'generate_response', return_value="AI response"):
            response = chat_service._generate_ai_response(message, session_id, mock_db)
            
            assert response == "AI response"
            chat_service.ai_service.generate_response.assert_called_once_with(
                query=message,
                session_id=str(session_id)
            )
    
    def test_generate_ai_response_error(self, chat_service):
        """Test AI response generation with error."""
        message = "Test message"
        session_id = uuid4()
        mock_db = Mock(spec=Session)
        
        with patch.object(chat_service.ai_service, 'generate_response', 
                         side_effect=Exception("AI service error")):
            response = chat_service._generate_ai_response(message, session_id, mock_db)
            
            assert "trouble processing your request" in response
    
    def test_get_connection_manager(self, chat_service):
        """Test getting connection manager instance."""
        manager = chat_service.get_connection_manager()
        assert manager is chat_service.connection_manager


def test_get_chat_service():
    """Test getting chat service singleton."""
    service1 = get_chat_service()
    service2 = get_chat_service()
    
    assert service1 is service2
    assert isinstance(service1, ChatService)


if __name__ == "__main__":
    pytest.main([__file__])