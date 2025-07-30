"""
Chat service for WebSocket connection management and real-time communication.

This module provides WebSocket connection handling with user authentication,
connection pooling, session management, and message broadcasting capabilities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db_session
from models.database import User, ChatSession, Message, MessageRole
from models.schemas import ChatMessageRequest, ChatMessageResponse, MessageCreate
from services.auth_service import get_auth_service
from services.ai_service import get_ai_service
from services.log_service import get_log_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager for handling multiple client connections.
    
    Manages active connections, user sessions, and message broadcasting
    with proper authentication and session management.
    """
    
    def __init__(self):
        # Active WebSocket connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to connection mapping: {user_id: Set[connection_id]}
        self.user_connections: Dict[UUID, Set[str]] = {}
        
        # Connection to user mapping: {connection_id: user_id}
        self.connection_users: Dict[str, UUID] = {}
        
        # Connection to session mapping: {connection_id: session_id}
        self.connection_sessions: Dict[str, UUID] = {}
        
        # Session to connections mapping: {session_id: Set[connection_id]}
        self.session_connections: Dict[UUID, Set[str]] = {}
        
        self.auth_service = get_auth_service()
        self.ai_service = get_ai_service()
    
    async def connect(self, websocket: WebSocket, token: str) -> str:
        """
        Accept WebSocket connection and authenticate user.
        
        Args:
            websocket: WebSocket connection
            token: JWT authentication token
            
        Returns:
            Connection ID for the established connection
            
        Raises:
            HTTPException: If authentication fails
        """
        # Accept WebSocket connection
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid4())
        
        try:
            # Authenticate user
            with get_db_session() as db:
                user = self.auth_service.get_current_user(token, db)
                
                # Store connection
                self.active_connections[connection_id] = websocket
                self.connection_users[connection_id] = user.id
                
                # Add to user connections
                if user.id not in self.user_connections:
                    self.user_connections[user.id] = set()
                self.user_connections[user.id].add(connection_id)
                
                logger.info(f"WebSocket connection established for user {user.username} (ID: {user.id})")
                
                # Send connection confirmation
                await self._send_to_connection(connection_id, {
                    "type": "connection_established",
                    "message": f"Connected as {user.username}",
                    "user_id": str(user.id),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return connection_id
                
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Handle WebSocket disconnection and cleanup.
        
        Args:
            connection_id: Connection ID to disconnect
        """
        if connection_id not in self.active_connections:
            return
        
        try:
            # Get user ID
            user_id = self.connection_users.get(connection_id)
            
            # Remove from active connections
            del self.active_connections[connection_id]
            del self.connection_users[connection_id]
            
            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from session connections
            session_id = self.connection_sessions.get(connection_id)
            if session_id:
                del self.connection_sessions[connection_id]
                if session_id in self.session_connections:
                    self.session_connections[session_id].discard(connection_id)
                    if not self.session_connections[session_id]:
                        del self.session_connections[session_id]
            
            logger.info(f"WebSocket connection {connection_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnection: {e}")
    
    async def join_session(self, connection_id: str, session_id: UUID) -> None:
        """
        Join a chat session.
        
        Args:
            connection_id: Connection ID
            session_id: Chat session ID to join
        """
        if connection_id not in self.active_connections:
            return
        
        try:
            # Verify session exists and user has access
            user_id = self.connection_users.get(connection_id)
            if not user_id:
                return
            
            with get_db_session() as db:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                    ChatSession.is_active == True
                ).first()
                
                if not session:
                    await self._send_to_connection(connection_id, {
                        "type": "error",
                        "message": "Session not found or access denied",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return
                
                # Remove from previous session if any
                old_session_id = self.connection_sessions.get(connection_id)
                if old_session_id and old_session_id in self.session_connections:
                    self.session_connections[old_session_id].discard(connection_id)
                    if not self.session_connections[old_session_id]:
                        del self.session_connections[old_session_id]
                
                # Join new session
                self.connection_sessions[connection_id] = session_id
                if session_id not in self.session_connections:
                    self.session_connections[session_id] = set()
                self.session_connections[session_id].add(connection_id)
                
                # Send session joined confirmation
                await self._send_to_connection(connection_id, {
                    "type": "session_joined",
                    "session_id": str(session_id),
                    "session_title": session.title,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Connection {connection_id} joined session {session_id}")
                
        except Exception as e:
            logger.error(f"Error joining session: {e}")
            await self._send_to_connection(connection_id, {
                "type": "error",
                "message": "Failed to join session",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def broadcast_to_session(self, session_id: UUID, message: dict) -> None:
        """
        Broadcast message to all connections in a session.
        
        Args:
            session_id: Session ID to broadcast to
            message: Message to broadcast
        """
        if session_id not in self.session_connections:
            return
        
        connections = self.session_connections[session_id].copy()
        for connection_id in connections:
            await self._send_to_connection(connection_id, message)
    
    async def send_to_user(self, user_id: UUID, message: dict) -> None:
        """
        Send message to all connections of a specific user.
        
        Args:
            user_id: User ID to send message to
            message: Message to send
        """
        if user_id not in self.user_connections:
            return
        
        connections = self.user_connections[user_id].copy()
        for connection_id in connections:
            await self._send_to_connection(connection_id, message)
    
    async def _send_to_connection(self, connection_id: str, message: dict) -> None:
        """
        Send message to a specific connection.
        
        Args:
            connection_id: Connection ID to send to
            message: Message to send
        """
        if connection_id not in self.active_connections:
            return
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            # Remove broken connection
            await self.disconnect(connection_id)
    
    def get_connection_info(self) -> dict:
        """
        Get information about active connections.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "active_sessions": len(self.session_connections),
            "connections_per_user": {
                str(user_id): len(connections) 
                for user_id, connections in self.user_connections.items()
            }
        }


class CommandProcessor:
    """
    Command processor for handling chat commands.
    
    Processes special commands like /help, /reload, /stat with proper
    authorization and validation.
    """
    
    def __init__(self):
        self.log_service = get_log_service()
        self.commands = {
            'help': self._handle_help_command,
            'reload': self._handle_reload_command,
            'stat': self._handle_stat_command,
            'stats': self._handle_stat_command,  # Alias for stat
            'status': self._handle_status_command,
            'clear': self._handle_clear_command,
            'sessions': self._handle_sessions_command
        }
    
    def is_command(self, message: str) -> bool:
        """
        Check if a message is a command.
        
        Args:
            message: Message to check
            
        Returns:
            True if message is a command, False otherwise
        """
        return message.strip().startswith('/')
    
    def parse_command(self, message: str) -> tuple[str, List[str]]:
        """
        Parse a command message into command and arguments.
        
        Args:
            message: Command message to parse
            
        Returns:
            Tuple of (command, arguments)
        """
        message = message.strip()
        if not message.startswith('/'):
            return '', []
        
        parts = message[1:].split()
        command = parts[0].lower() if parts else ''
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    async def process_command(self, message: str, user_id: UUID, session_id: UUID, 
                            user_role: str) -> Dict[str, Any]:
        """
        Process a command message.
        
        Args:
            message: Command message
            user_id: User ID executing the command
            session_id: Current session ID
            user_role: User role for authorization
            
        Returns:
            Command response dictionary
        """
        try:
            command, args = self.parse_command(message)
            
            if not command:
                return {
                    "type": "command_error",
                    "message": "Invalid command format. Use /help for available commands.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            if command not in self.commands:
                return {
                    "type": "command_error",
                    "message": f"Unknown command: /{command}. Use /help for available commands.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Execute command
            handler = self.commands[command]
            return await handler(args, user_id, session_id, user_role)
            
        except Exception as e:
            logger.error(f"Error processing command '{message}': {e}")
            return {
                "type": "command_error",
                "message": "An error occurred while processing the command.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_help_command(self, args: List[str], user_id: UUID, 
                                 session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /help command."""
        help_text = """
**Available Commands:**

• `/help` - Show this help message
• `/stat` or `/stats` - Show log statistics and system status
• `/status` - Show current session and connection status
• `/clear` - Clear current session (end session)
• `/sessions` - List your recent chat sessions
• `/reload [days]` - Reload logs from specified days (Admin/Analyst only)

**Usage Examples:**
• `/stat` - Show current log statistics
• `/reload 7` - Reload logs from last 7 days
• `/sessions` - List your chat sessions

**Tips:**
• Commands are case-insensitive
• Use regular messages for AI queries
• Commands provide system information and controls
        """.strip()
        
        return {
            "type": "command_response",
            "command": "help",
            "message": help_text,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_reload_command(self, args: List[str], user_id: UUID, 
                                   session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /reload command."""
        # Check authorization
        if user_role not in ['admin', 'analyst']:
            return {
                "type": "command_error",
                "message": "Access denied. Reload command requires Admin or Analyst role.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Parse days argument
            days = 7  # Default
            if args:
                try:
                    days = int(args[0])
                    if days < 1 or days > 365:
                        return {
                            "type": "command_error",
                            "message": "Days must be between 1 and 365.",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                except ValueError:
                    return {
                        "type": "command_error",
                        "message": "Invalid days value. Please provide a number.",
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Reload logs
            try:
                result = self.log_service.reload_logs_from_days(days)
                
                return {
                    "type": "command_response",
                    "command": "reload",
                    "message": f"✅ Successfully reloaded logs from last {days} days.\n"
                              f"Processed {result.get('total_logs', 0)} log entries.\n"
                              f"Processing time: {result.get('processing_time', 0):.2f} seconds.",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error reloading logs: {e}")
                return {
                    "type": "command_error",
                    "message": f"Failed to reload logs: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in reload command: {e}")
            return {
                "type": "command_error",
                "message": "An error occurred while reloading logs.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_stat_command(self, args: List[str], user_id: UUID, 
                                 session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /stat or /stats command."""
        try:
            # Get log statistics
            stats = self.log_service.get_log_statistics()
            
            # Format statistics message
            stats_message = f"""
**📊 System Statistics**

**Log Data:**
• Total logs: {stats.get('total_logs', 0):,}
• Date range: {stats.get('date_range', {}).get('start', 'N/A')} to {stats.get('date_range', {}).get('end', 'N/A')}
• Processing time: {stats.get('processing_time', 0):.2f} seconds

**Log Sources:**
{self._format_dict_stats(stats.get('sources', {}))}

**Log Levels:**
{self._format_dict_stats(stats.get('levels', {}))}

**Vector Store:**
• Embeddings: {stats.get('vector_store', {}).get('total_embeddings', 0):,}
• Index size: {stats.get('vector_store', {}).get('index_size', 0):,}

**System Status:** {'🟢 Healthy' if stats.get('system_healthy', True) else '🔴 Issues Detected'}
            """.strip()
            
            return {
                "type": "command_response",
                "command": "stat",
                "message": stats_message,
                "data": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve system statistics.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_status_command(self, args: List[str], user_id: UUID, 
                                   session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /status command."""
        try:
            # Get current session info
            with get_db_session() as db:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if not session:
                    return {
                        "type": "command_error",
                        "message": "Current session not found.",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                # Get message count
                message_count = db.query(Message).filter(
                    Message.session_id == session_id
                ).count()
                
                # Format status message
                status_message = f"""
**📋 Session Status**

**Current Session:**
• Session ID: {str(session.id)[:8]}...
• Title: {session.title}
• Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}
• Messages: {message_count}
• Status: {'🟢 Active' if session.is_active else '🔴 Inactive'}

**User Info:**
• Role: {user_role.title()}
• User ID: {str(user_id)[:8]}...

**Connection:** 🟢 Connected via WebSocket
                """.strip()
                
                return {
                    "type": "command_response",
                    "command": "status",
                    "message": status_message,
                    "data": {
                        "session_id": str(session_id),
                        "session_title": session.title,
                        "message_count": message_count,
                        "user_role": user_role
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve session status.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_clear_command(self, args: List[str], user_id: UUID, 
                                  session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /clear command."""
        try:
            # End current session
            with get_db_session() as db:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if session:
                    session.is_active = False
                    session.ended_at = datetime.utcnow()
                    db.commit()
                    
                    return {
                        "type": "command_response",
                        "command": "clear",
                        "message": "✅ Session cleared. You can start a new conversation.",
                        "action": "session_ended",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "type": "command_error",
                        "message": "Current session not found.",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return {
                "type": "command_error",
                "message": "Failed to clear session.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_sessions_command(self, args: List[str], user_id: UUID, 
                                     session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /sessions command."""
        try:
            with get_db_session() as db:
                # Get recent sessions
                sessions = db.query(ChatSession).filter(
                    ChatSession.user_id == user_id
                ).order_by(ChatSession.updated_at.desc()).limit(10).all()
                
                if not sessions:
                    return {
                        "type": "command_response",
                        "command": "sessions",
                        "message": "No chat sessions found.",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                # Format sessions list
                sessions_text = "**📝 Recent Chat Sessions:**\n\n"
                for i, sess in enumerate(sessions, 1):
                    status = "🟢 Active" if sess.is_active else "🔴 Ended"
                    current = " (Current)" if sess.id == session_id else ""
                    sessions_text += f"{i}. **{sess.title}**{current}\n"
                    sessions_text += f"   • Created: {sess.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    sessions_text += f"   • Status: {status}\n"
                    sessions_text += f"   • ID: {str(sess.id)[:8]}...\n\n"
                
                return {
                    "type": "command_response",
                    "command": "sessions",
                    "message": sessions_text.strip(),
                    "data": {
                        "sessions": [
                            {
                                "id": str(sess.id),
                                "title": sess.title,
                                "is_active": sess.is_active,
                                "created_at": sess.created_at.isoformat(),
                                "is_current": sess.id == session_id
                            }
                            for sess in sessions
                        ]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve sessions.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _format_dict_stats(self, stats_dict: Dict[str, int]) -> str:
        """Format dictionary statistics for display."""
        if not stats_dict:
            return "• No data available"
        
        formatted = []
        for key, value in sorted(stats_dict.items(), key=lambda x: x[1], reverse=True):
            formatted.append(f"• {key}: {value:,}")
        
        return "\n".join(formatted)


class ChatService:
    """
    Chat service for managing WebSocket communications and chat sessions.
    
    Handles message processing, session management, and integration with
    AI service for generating responses.
    """
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.auth_service = get_auth_service()
        self.ai_service = get_ai_service()
        self.command_processor = CommandProcessor()
    
    async def handle_websocket_connection(self, websocket: WebSocket, token: str) -> None:
        """
        Handle WebSocket connection lifecycle.
        
        Args:
            websocket: WebSocket connection
            token: Authentication token
        """
        connection_id = None
        try:
            # Establish connection
            connection_id = await self.connection_manager.connect(websocket, token)
            
            # Handle messages
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    # Process message
                    await self._process_websocket_message(connection_id, message_data)
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {connection_id}")
                    break
                except json.JSONDecodeError:
                    await self.connection_manager._send_to_connection(connection_id, {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    await self.connection_manager._send_to_connection(connection_id, {
                        "type": "error",
                        "message": "Error processing message",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        
        finally:
            # Clean up connection
            if connection_id:
                await self.connection_manager.disconnect(connection_id)
    
    async def _process_websocket_message(self, connection_id: str, message_data: dict) -> None:
        """
        Process incoming WebSocket message.
        
        Args:
            connection_id: Connection ID
            message_data: Message data from client
        """
        message_type = message_data.get("type")
        
        if message_type == "join_session":
            session_id = message_data.get("session_id")
            if session_id:
                await self.connection_manager.join_session(connection_id, UUID(session_id))
        
        elif message_type == "chat_message":
            await self._handle_chat_message(connection_id, message_data)
        
        elif message_type == "ping":
            await self.connection_manager._send_to_connection(connection_id, {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        else:
            await self.connection_manager._send_to_connection(connection_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_chat_message(self, connection_id: str, message_data: dict) -> None:
        """
        Handle chat message from client.
        
        Args:
            connection_id: Connection ID
            message_data: Chat message data
        """
        try:
            # Get user and session
            user_id = self.connection_manager.connection_users.get(connection_id)
            session_id = self.connection_manager.connection_sessions.get(connection_id)
            
            if not user_id or not session_id:
                await self.connection_manager._send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Not connected to a session",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            message_content = message_data.get("message", "").strip()
            if not message_content:
                await self.connection_manager._send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Empty message",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            # Check if message is a command
            if self.command_processor.is_command(message_content):
                await self._handle_command_message(connection_id, message_content, user_id, session_id)
                return
            
            # Store user message
            user_message = self.save_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=message_content,
                metadata={"connection_id": connection_id}
            )
            
            if not user_message:
                await self.connection_manager._send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Failed to save message",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
                
                # Broadcast user message to session
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "message",
                    "id": str(user_message.id),
                    "role": "user",
                    "content": message_content,
                    "timestamp": user_message.timestamp.isoformat(),
                    "session_id": str(session_id)
                })
                
                # Send typing indicator
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "typing",
                    "is_typing": True,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            # Generate AI response
            try:
                ai_response = self._generate_ai_response(message_content, session_id, user_id)
                
                # Store AI response
                ai_message = self.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=ai_response,
                    metadata={"generated_by": "ai_service"}
                )
                
                if not ai_message:
                    await self.connection_manager.broadcast_to_session(session_id, {
                        "type": "error",
                        "message": "Failed to save AI response",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return
                    
                    # Stop typing indicator
                    await self.connection_manager.broadcast_to_session(session_id, {
                        "type": "typing",
                        "is_typing": False,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                # Broadcast AI response
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "message",
                    "id": str(ai_message.id),
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": ai_message.timestamp.isoformat(),
                    "session_id": str(session_id)
                })
                
            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                
                # Stop typing indicator
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "typing",
                    "is_typing": False,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Send error message
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "error",
                    "message": "Failed to generate AI response",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await self.connection_manager._send_to_connection(connection_id, {
                "type": "error",
                "message": "Failed to process message",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_command_message(self, connection_id: str, command_message: str, 
                                    user_id: UUID, session_id: UUID) -> None:
        """
        Handle command message from client.
        
        Args:
            connection_id: Connection ID
            command_message: Command message content
            user_id: User ID
            session_id: Session ID
        """
        try:
            # Get user role for authorization
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    await self.connection_manager._send_to_connection(connection_id, {
                        "type": "error",
                        "message": "User not found",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return
                
                # Process command
                response = await self.command_processor.process_command(
                    message=command_message,
                    user_id=user_id,
                    session_id=session_id,
                    user_role=user.role
                )
                
                # Store command in message history
                command_message_obj = self.save_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=command_message,
                    metadata={"type": "command", "connection_id": connection_id}
                )
                
                if command_message_obj:
                    # Broadcast command message
                    await self.connection_manager.broadcast_to_session(session_id, {
                        "type": "message",
                        "id": str(command_message_obj.id),
                        "role": "user",
                        "content": command_message,
                        "timestamp": command_message_obj.timestamp.isoformat(),
                        "session_id": str(session_id),
                        "metadata": {"type": "command"}
                    })
                
                # Store command response
                response_message_obj = self.save_message(
                    session_id=session_id,
                    role=MessageRole.SYSTEM,
                    content=response.get("message", "Command processed"),
                    metadata={
                        "type": "command_response",
                        "command": response.get("command"),
                        "data": response.get("data")
                    }
                )
                
                if response_message_obj:
                    # Broadcast command response
                    await self.connection_manager.broadcast_to_session(session_id, {
                        "type": "message",
                        "id": str(response_message_obj.id),
                        "role": "system",
                        "content": response.get("message", "Command processed"),
                        "timestamp": response_message_obj.timestamp.isoformat(),
                        "session_id": str(session_id),
                        "metadata": {
                            "type": "command_response",
                            "command": response.get("command"),
                            "data": response.get("data")
                        }
                    })
                
                # Handle special command actions
                if response.get("action") == "session_ended":
                    # Notify client that session ended
                    await self.connection_manager._send_to_connection(connection_id, {
                        "type": "session_ended",
                        "message": "Session has been ended",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
        except Exception as e:
            logger.error(f"Error handling command message: {e}")
            await self.connection_manager._send_to_connection(connection_id, {
                "type": "error",
                "message": "Failed to process command",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def _generate_ai_response(self, message: str, session_id: UUID, user_id: UUID) -> str:
        """
        Generate AI response for user message.
        
        Args:
            message: User message
            session_id: Chat session ID
            user_id: User ID for context
            
        Returns:
            AI generated response
        """
        try:
            # Generate response using AI service with session ID
            response = self.ai_service.generate_response(
                query=message,
                session_id=str(session_id)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in AI response generation: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."
    
    def create_chat_session(self, user_id: UUID, title: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session for a user.
        
        Args:
            user_id: User ID to create session for
            title: Optional session title
            
        Returns:
            Created chat session
        """
        try:
            with get_db_session() as db:
                # Create new session
                session = ChatSession(
                    user_id=user_id,
                    title=title or f"Chat Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                    is_active=True
                )
                
                db.add(session)
                db.commit()
                db.refresh(session)
                
                logger.info(f"Created new chat session {session.id} for user {user_id}")
                return session
                
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat session"
            )
    
    def get_user_sessions(self, user_id: UUID, include_inactive: bool = False) -> List[ChatSession]:
        """
        Get all chat sessions for a user.
        
        Args:
            user_id: User ID to get sessions for
            include_inactive: Whether to include inactive sessions
            
        Returns:
            List of chat sessions
        """
        try:
            with get_db_session() as db:
                query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
                
                if not include_inactive:
                    query = query.filter(ChatSession.is_active == True)
                
                sessions = query.order_by(ChatSession.updated_at.desc()).all()
                
                logger.debug(f"Retrieved {len(sessions)} sessions for user {user_id}")
                return sessions
                
        except Exception as e:
            logger.error(f"Error retrieving user sessions: {e}")
            return []
    
    def get_session_by_id(self, session_id: UUID, user_id: UUID) -> Optional[ChatSession]:
        """
        Get a specific chat session by ID.
        
        Args:
            session_id: Session ID to retrieve
            user_id: User ID for access control
            
        Returns:
            Chat session if found and accessible, None otherwise
        """
        try:
            with get_db_session() as db:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                    ChatSession.is_active == True
                ).first()
                
                return session
                
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: UUID, user_id: UUID, title: Optional[str] = None, 
                      is_active: Optional[bool] = None) -> Optional[ChatSession]:
        """
        Update a chat session.
        
        Args:
            session_id: Session ID to update
            user_id: User ID for access control
            title: New session title (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated session if successful, None otherwise
        """
        try:
            with get_db_session() as db:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if not session:
                    return None
                
                # Update fields
                if title is not None:
                    session.title = title
                if is_active is not None:
                    session.is_active = is_active
                    if not is_active:
                        session.ended_at = datetime.utcnow()
                
                session.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(session)
                
                logger.info(f"Updated session {session_id}")
                return session
                
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return None
    
    def end_session(self, session_id: UUID, user_id: UUID) -> bool:
        """
        End a chat session.
        
        Args:
            session_id: Session ID to end
            user_id: User ID for access control
            
        Returns:
            True if session was ended successfully, False otherwise
        """
        try:
            session = self.update_session(session_id, user_id, is_active=False)
            return session is not None
            
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            return False
    
    def get_session_messages(self, session_id: UUID, user_id: UUID, 
                           limit: int = 50, offset: int = 0) -> List[Message]:
        """
        Get messages from a chat session.
        
        Args:
            session_id: Session ID to get messages from
            user_id: User ID for access control
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages from the session
        """
        try:
            with get_db_session() as db:
                # Verify user has access to session
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if not session:
                    logger.warning(f"User {user_id} attempted to access session {session_id}")
                    return []
                
                # Get messages
                messages = db.query(Message).filter(
                    Message.session_id == session_id
                ).order_by(Message.timestamp.asc()).offset(offset).limit(limit).all()
                
                logger.debug(f"Retrieved {len(messages)} messages from session {session_id}")
                return messages
                
        except Exception as e:
            logger.error(f"Error retrieving messages from session {session_id}: {e}")
            return []
    
    def save_message(self, session_id: UUID, role: MessageRole, content: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Save a message to a chat session.
        
        Args:
            session_id: Session ID to save message to
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            Saved message if successful, None otherwise
        """
        try:
            with get_db_session() as db:
                # Verify session exists and is active
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.is_active == True
                ).first()
                
                if not session:
                    logger.warning(f"Attempted to save message to inactive/non-existent session {session_id}")
                    return None
                
                # Create message
                message = Message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    message_metadata=metadata
                )
                
                db.add(message)
                
                # Update session timestamp
                session.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(message)
                
                logger.debug(f"Saved message {message.id} to session {session_id}")
                return message
                
        except Exception as e:
            logger.error(f"Error saving message to session {session_id}: {e}")
            return None
    
    def get_conversation_context(self, session_id: UUID, user_id: UUID, 
                               max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation context for AI processing.
        
        Args:
            session_id: Session ID to get context from
            user_id: User ID for access control
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of message dictionaries for AI context
        """
        try:
            messages = self.get_session_messages(session_id, user_id, limit=max_messages)
            
            # Convert to format expected by AI service
            context = []
            for message in reversed(messages):  # Most recent first for context
                context.append({
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat()
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context for session {session_id}: {e}")
            return []
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old inactive sessions.
        
        Args:
            days_old: Number of days after which to clean up sessions
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with get_db_session() as db:
                # Find old inactive sessions
                old_sessions = db.query(ChatSession).filter(
                    ChatSession.is_active == False,
                    ChatSession.ended_at < cutoff_date
                ).all()
                
                count = len(old_sessions)
                
                # Delete associated messages first
                for session in old_sessions:
                    db.query(Message).filter(Message.session_id == session.id).delete()
                
                # Delete sessions
                db.query(ChatSession).filter(
                    ChatSession.is_active == False,
                    ChatSession.ended_at < cutoff_date
                ).delete()
                
                db.commit()
                
                logger.info(f"Cleaned up {count} old sessions")
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0
    
    def get_connection_manager(self) -> ConnectionManager:
        """Get the connection manager instance."""
        return self.connection_manager


# Global chat service instance
chat_service = ChatService()


def get_chat_service() -> ChatService:
    """Get chat service instance."""
    return chat_service