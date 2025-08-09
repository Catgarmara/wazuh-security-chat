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
from core.metrics import metrics
from models.database import User, ChatSession, Message, MessageRole
from models.schemas import ChatMessageRequest, ChatMessageResponse, MessageCreate
# Import services directly to avoid circular imports
from services.auth_service import AuthService
from services.log_service import LogService
from services.siem_service import get_siem_service
from core.ai_factory import AIServiceFactory

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
        
        self.auth_service = AuthService()
        try:
            self.ai_service = AIServiceFactory.get_ai_service()
        except Exception as e:
            logger.warning(f"Failed to initialize Embedded AI service: {e}")
            self.ai_service = None
        
        try:
            self.siem_service = get_siem_service()
        except Exception as e:
            logger.warning(f"Failed to initialize SIEM service: {e}")
            self.siem_service = None
    
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
                
                # Record WebSocket connection metrics
                metrics.record_websocket_connection("connected")
                
                # Send connection confirmation with AI service status
                ai_status = {}
                if self.ai_service:
                    try:
                        ai_status = self.ai_service.get_service_status()
                    except Exception as e:
                        logger.warning(f"Failed to get AI service status: {e}")
                        ai_status = {"service_ready": False, "error": str(e)}
                else:
                    ai_status = {"service_ready": False, "error": "AI service not initialized"}
                
                await self._send_to_connection(connection_id, {
                    "type": "connection_established",
                    "message": f"Connected as {user.username}",
                    "user_id": str(user.id),
                    "ai_status": ai_status,
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
            
            # Record WebSocket disconnection metrics
            metrics.record_websocket_connection("disconnected")
            
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
        try:
            self.log_service = LogService()
        except Exception as e:
            logger.warning(f"Failed to initialize Log service: {e}")
            self.log_service = None
        
        try:
            self.siem_service = get_siem_service()
        except Exception as e:
            logger.warning(f"Failed to initialize SIEM service: {e}")
            self.siem_service = None
        self.commands = {
            'help': self._handle_help_command,
            'reload': self._handle_reload_command,
            'stat': self._handle_stat_command,
            'stats': self._handle_stat_command,  # Alias for stat
            'status': self._handle_status_command,
            'clear': self._handle_clear_command,
            'sessions': self._handle_sessions_command,
            'hunt': self._handle_hunt_command,
            'threats': self._handle_threats_command,
            'alerts': self._handle_alerts_command,
            'agents': self._handle_agents_command,
            'investigate': self._handle_investigate_command
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

**General Commands:**
• `/help` - Show this help message
• `/status` - Show current session and connection status
• `/clear` - Clear current session (end session)
• `/sessions` - List your recent chat sessions

**Security Analysis Commands:**
• `/hunt [query]` - Start threat hunting workflow
• `/threats` - Show current threat intelligence
• `/alerts [filter]` - Display security alerts
• `/agents` - Show SIEM agent status
• `/investigate [alert_id]` - Start incident investigation

**System Commands:**
• `/stat` or `/stats` - Show log statistics and system status
• `/reload [days]` - Reload logs from specified days (Admin/Analyst only)

**Usage Examples:**
• `/hunt suspicious login` - Hunt for suspicious login activities
• `/alerts critical` - Show critical security alerts
• `/investigate alert-12345` - Investigate specific alert
• `/agents` - Check agent connectivity status

**Tips:**
• Commands are case-insensitive
• Use regular messages for AI-powered security analysis
• Commands provide direct access to SIEM data and workflows
• For complex analysis, describe your security question in natural language
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
                if self.log_service is None:
                    return {
                        "type": "command_error",
                        "message": "Log service is currently unavailable.",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                logs = self.log_service.load_logs_from_days(days)
                result = {
                    "total_logs": len(logs),
                    "processing_time": 0.0  # This would be calculated by the service
                }
                
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
            if self.log_service is None:
                return {
                    "type": "command_error",
                    "message": "Log service is currently unavailable.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Load recent logs to get statistics
            logs = self.log_service.load_logs_from_days(7)  # Default to 7 days
            log_stats = self.log_service.get_log_statistics(logs)
            
            stats = {
                "total_logs": log_stats.total_logs,
                "date_range": {"start": "N/A", "end": "N/A"},
                "processing_time": log_stats.processing_time,
                "sources": log_stats.sources,
                "levels": log_stats.levels,
                "vector_store": {"total_embeddings": 0, "index_size": 0},
                "system_healthy": True
            }
            
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
    
    async def _handle_hunt_command(self, args: List[str], user_id: UUID, 
                                 session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /hunt command for threat hunting workflows."""
        if user_role not in ['admin', 'analyst']:
            return {
                "type": "command_error",
                "message": "Access denied. Threat hunting requires Admin or Analyst role.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            hunt_query = " ".join(args) if args else "general threat indicators"
            
            hunt_message = f"""
🔍 **Threat Hunting Initiated**

**Hunt Query:** {hunt_query}

**Recommended Hunting Steps:**
1. **Initial Reconnaissance**
   • Review recent alerts and anomalies
   • Check for unusual network traffic patterns
   • Analyze authentication logs for suspicious activity

2. **Data Collection**
   • Query SIEM for relevant log sources
   • Collect endpoint telemetry data
   • Review threat intelligence feeds

3. **Analysis Phase**
   • Apply behavioral analysis techniques
   • Look for indicators of compromise (IOCs)
   • Correlate events across multiple data sources

4. **Hypothesis Testing**
   • Develop threat scenarios
   • Test hypotheses against available data
   • Refine search criteria based on findings

**Next Steps:**
• Use natural language queries to analyze specific aspects
• Example: "Show me failed login attempts in the last 24 hours"
• Example: "Find processes with unusual network connections"

💡 *Tip: Describe what you're looking for in natural language for AI-powered analysis*
            """.strip()
            
            return {
                "type": "command_response",
                "command": "hunt",
                "message": hunt_message,
                "data": {"hunt_query": hunt_query, "workflow": "threat_hunting"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in hunt command: {e}")
            return {
                "type": "command_error",
                "message": "Failed to initiate threat hunting workflow.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_threats_command(self, args: List[str], user_id: UUID, 
                                    session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /threats command to show threat intelligence."""
        try:
            if self.siem_service is None:
                return {
                    "type": "command_error",
                    "message": "SIEM service is currently unavailable.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Get threat intelligence data
            threat_data = await self.siem_service.get_threat_intelligence(limit=10)
            
            threats_message = f"""
🚨 **Current Threat Intelligence**

**Active Threat Feeds:** {len(threat_data.get('feeds', []))}
**Total Indicators:** {threat_data.get('total', 0)}

**Recent Threat Indicators:**
"""
            
            if threat_data.get('indicators'):
                for indicator in threat_data['indicators'][:5]:
                    threats_message += f"• **{indicator.get('type', 'Unknown')}**: {indicator.get('value', 'N/A')}\n"
                    threats_message += f"  Confidence: {indicator.get('confidence', 'Unknown')} | "
                    threats_message += f"Severity: {indicator.get('severity', 'Unknown')}\n"
            else:
                threats_message += "• No active threat indicators at this time\n"
            
            threats_message += f"""
**Threat Feed Status:**
"""
            for feed in threat_data.get('feeds', []):
                status_icon = "🟢" if feed.get('status') == 'online' else "🔴"
                threats_message += f"• {status_icon} **{feed.get('name', 'Unknown')}**: {feed.get('indicators_count', 0)} indicators\n"
            
            threats_message += """
**Actions:**
• Use `/hunt [threat_type]` to search for specific threats
• Ask: "What are the latest threat indicators?"
• Ask: "Analyze recent malware signatures"
            """.strip()
            
            return {
                "type": "command_response",
                "command": "threats",
                "message": threats_message,
                "data": threat_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in threats command: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve threat intelligence.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_alerts_command(self, args: List[str], user_id: UUID, 
                                   session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /alerts command to show security alerts."""
        try:
            if self.siem_service is None:
                return {
                    "type": "command_error",
                    "message": "SIEM service is currently unavailable.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Parse filter argument
            severity_filter = args[0] if args else None
            
            # Get security alerts
            alerts_data = await self.siem_service.get_security_alerts(
                limit=10,
                severity_filter=severity_filter,
                time_range="24h"
            )
            
            alerts_message = f"""
🚨 **Security Alerts** {f"(Severity: {severity_filter})" if severity_filter else ""}

**Total Alerts:** {alerts_data.get('total', 0)} (Last 24 hours)
**Showing:** {len(alerts_data.get('alerts', []))} most recent

"""
            
            if alerts_data.get('alerts'):
                for alert in alerts_data['alerts'][:5]:
                    severity_icon = {
                        'critical': '🔴',
                        'high': '🟠', 
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(alert.get('severity', 'low'), '⚪')
                    
                    alerts_message += f"{severity_icon} **{alert.get('rule_description', 'Unknown Alert')}**\n"
                    alerts_message += f"   • Severity: {alert.get('severity', 'Unknown').title()}\n"
                    alerts_message += f"   • Agent: {alert.get('agent_name', 'Unknown')}\n"
                    alerts_message += f"   • Time: {alert.get('timestamp', 'Unknown')}\n"
                    if alert.get('source_ip'):
                        alerts_message += f"   • Source IP: {alert.get('source_ip')}\n"
                    alerts_message += "\n"
            else:
                alerts_message += "• No alerts found matching the criteria\n\n"
            
            alerts_message += """
**Actions:**
• Use `/investigate [alert_id]` to investigate specific alerts
• Ask: "Analyze the critical alerts from today"
• Ask: "What are the most common alert types?"
• Use `/alerts critical` to filter by severity
            """.strip()
            
            return {
                "type": "command_response",
                "command": "alerts",
                "message": alerts_message,
                "data": alerts_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in alerts command: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve security alerts.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_agents_command(self, args: List[str], user_id: UUID, 
                                   session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /agents command to show SIEM agent status."""
        try:
            if self.siem_service is None:
                return {
                    "type": "command_error",
                    "message": "SIEM service is currently unavailable.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Get agent data
            agents_data = await self.siem_service.get_wazuh_agents(limit=20)
            
            agents_message = f"""
🖥️ **SIEM Agent Status**

**Total Agents:** {agents_data.get('total', 0)}
**Showing:** {len(agents_data.get('agents', []))} agents

"""
            
            # Group agents by status
            status_counts = {}
            for agent in agents_data.get('agents', []):
                status = agent.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            agents_message += "**Status Summary:**\n"
            for status, count in status_counts.items():
                status_icon = {
                    'active': '🟢',
                    'disconnected': '🔴',
                    'never_connected': '⚪',
                    'pending': '🟡'
                }.get(status, '❓')
                agents_message += f"• {status_icon} {status.replace('_', ' ').title()}: {count}\n"
            
            agents_message += "\n**Recent Agents:**\n"
            
            if agents_data.get('agents'):
                for agent in agents_data['agents'][:8]:
                    status_icon = {
                        'active': '🟢',
                        'disconnected': '🔴',
                        'never_connected': '⚪',
                        'pending': '🟡'
                    }.get(agent.get('status', 'unknown'), '❓')
                    
                    agents_message += f"{status_icon} **{agent.get('name', 'Unknown')}** ({agent.get('id', 'N/A')})\n"
                    agents_message += f"   • IP: {agent.get('ip_address', 'Unknown')}\n"
                    agents_message += f"   • OS: {agent.get('os', 'Unknown')}\n"
                    agents_message += f"   • Last Seen: {agent.get('last_keep_alive', 'Never')}\n\n"
            else:
                agents_message += "• No agents found\n\n"
            
            agents_message += """
**Actions:**
• Ask: "Which agents are disconnected?"
• Ask: "Show me agents with outdated versions"
• Ask: "Analyze agent connectivity patterns"
            """.strip()
            
            return {
                "type": "command_response",
                "command": "agents",
                "message": agents_message,
                "data": agents_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in agents command: {e}")
            return {
                "type": "command_error",
                "message": "Failed to retrieve agent status.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_investigate_command(self, args: List[str], user_id: UUID, 
                                        session_id: UUID, user_role: str) -> Dict[str, Any]:
        """Handle /investigate command to start incident investigation."""
        if user_role not in ['admin', 'analyst']:
            return {
                "type": "command_error",
                "message": "Access denied. Investigation requires Admin or Analyst role.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            if not args:
                return {
                    "type": "command_error",
                    "message": "Please provide an alert ID or investigation target. Usage: /investigate [alert_id]",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            investigation_target = " ".join(args)
            
            investigation_message = f"""
🔍 **Incident Investigation Started**

**Investigation Target:** {investigation_target}

**Investigation Workflow:**

**Phase 1: Initial Assessment**
• ✅ Investigation initiated
• 🔄 Gathering alert details
• 🔄 Identifying affected systems
• 🔄 Assessing initial scope

**Phase 2: Data Collection**
• 📊 Collecting related logs
• 🌐 Analyzing network traffic
• 💻 Reviewing endpoint data
• 👤 Checking user activities

**Phase 3: Analysis**
• 🔗 Correlating events
• 🎯 Identifying attack vectors
• 📈 Timeline reconstruction
• 🚨 Impact assessment

**Phase 4: Response Planning**
• 🛡️ Containment strategies
• 🔧 Remediation steps
• 📋 Documentation requirements
• 📞 Stakeholder notifications

**Next Steps:**
• Use natural language to ask specific questions about the incident
• Example: "What systems were affected by this alert?"
• Example: "Show me the timeline of events"
• Example: "What are the recommended containment actions?"

💡 *Tip: Describe what you want to investigate and I'll help analyze the data*
            """.strip()
            
            return {
                "type": "command_response",
                "command": "investigate",
                "message": investigation_message,
                "data": {
                    "investigation_target": investigation_target,
                    "workflow": "incident_investigation",
                    "phase": "initial_assessment"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in investigate command: {e}")
            return {
                "type": "command_error",
                "message": "Failed to start incident investigation.",
                "timestamp": datetime.utcnow().isoformat()
            }


class ChatService:
    """
    Chat service for managing WebSocket communications and chat sessions.
    
    Handles message processing, session management, and integration with
    AI service for generating responses.
    """
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.auth_service = AuthService()
        try:
            self.ai_service = AIServiceFactory.get_ai_service()
        except Exception as e:
            logger.warning(f"Failed to initialize Embedded AI service: {e}")
            self.ai_service = None
        
        try:
            self.siem_service = get_siem_service()
        except Exception as e:
            logger.warning(f"Failed to initialize SIEM service: {e}")
            self.siem_service = None
            
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
        
        elif message_type == "security_query":
            await self._handle_security_query(connection_id, message_data)
        
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
            
            # Record chat message metrics
            metrics.record_chat_message("user")
            metrics.record_websocket_message("inbound", "chat")
            
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
                ai_response = await self._generate_ai_response(message_content, session_id, user_id)
                
                # Store AI response
                ai_message = self.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=ai_response,
                    metadata={"generated_by": "embedded_ai_service"}
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
    
    async def _handle_security_query(self, connection_id: str, message_data: dict) -> None:
        """
        Handle specialized security query from client for threat hunting and incident analysis.
        
        Args:
            connection_id: Connection ID
            message_data: Security query message data with query and context
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
            
            query = message_data.get("query", "").strip()
            context = message_data.get("context", "general")  # threat_hunting, incident_investigation, etc.
            
            if not query:
                await self.connection_manager._send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Empty security query",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            # Store security query message
            security_message = self.save_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=query,
                metadata={
                    "type": "security_query",
                    "context": context,
                    "connection_id": connection_id
                }
            )
            
            # Record security query metrics
            metrics.record_chat_message("security_query")
            metrics.record_websocket_message("inbound", "security_query")
            
            if not security_message:
                await self.connection_manager._send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Failed to save security query",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            # Broadcast security query to session
            await self.connection_manager.broadcast_to_session(session_id, {
                "type": "message",
                "id": str(security_message.id),
                "role": "user",
                "content": query,
                "timestamp": security_message.timestamp.isoformat(),
                "session_id": str(session_id),
                "metadata": {
                    "type": "security_query",
                    "context": context
                }
            })
            
            # Send typing indicator for security analysis
            await self.connection_manager.broadcast_to_session(session_id, {
                "type": "typing",
                "is_typing": True,
                "message": "Analyzing security query...",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Generate specialized security analysis response
            try:
                security_response = await self._generate_security_analysis(query, context, session_id, user_id)
                
                # Store security analysis response
                analysis_message = self.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=security_response,
                    metadata={
                        "type": "security_analysis",
                        "context": context,
                        "generated_by": "embedded_ai_service"
                    }
                )
                
                if not analysis_message:
                    await self.connection_manager.broadcast_to_session(session_id, {
                        "type": "error",
                        "message": "Failed to save security analysis",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return
                
                # Stop typing indicator
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "typing",
                    "is_typing": False,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Broadcast security analysis response
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "security_analysis",
                    "id": str(analysis_message.id),
                    "role": "assistant",
                    "content": security_response,
                    "timestamp": analysis_message.timestamp.isoformat(),
                    "session_id": str(session_id),
                    "metadata": {
                        "type": "security_analysis",
                        "context": context,
                        "query": query
                    }
                })
                
                # Record successful security analysis
                metrics.record_chat_message("security_analysis")
                metrics.record_websocket_message("outbound", "security_analysis")
                
            except Exception as e:
                logger.error(f"Error generating security analysis: {e}")
                
                # Stop typing indicator
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "typing",
                    "is_typing": False,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Send error message
                await self.connection_manager.broadcast_to_session(session_id, {
                    "type": "error",
                    "message": "Failed to generate security analysis. Please try again or contact your security administrator.",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error handling security query: {e}")
            await self.connection_manager._send_to_connection(connection_id, {
                "type": "error",
                "message": "Failed to process security query",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _generate_ai_response(self, message: str, session_id: UUID, user_id: UUID) -> str:
        """
        Generate AI response using embedded AI service with enhanced security analysis capabilities.
        
        Args:
            message: User message
            session_id: Chat session ID
            user_id: User ID
            
        Returns:
            AI generated response with security-focused analysis
        """
        try:
            # Check if AI service is available
            if self.ai_service is None:
                return "⚠️ Embedded AI service is currently unavailable. Please try again later."
            
            # Check if service is ready
            if not self.ai_service.is_ready():
                return "⚠️ Embedded AI service is initializing. Please wait a moment and try again."
            
            # Detect security context from message
            security_context = self._detect_security_context(message)
            
            # Get conversation context with security focus
            conversation_context = self.get_conversation_context(session_id, user_id, max_messages=6)
            
            # Get SIEM context for security analysis
            siem_context = await self._get_siem_context_for_query(message)
            
            # Build enhanced security-focused prompt
            enhanced_query = await self._build_security_enhanced_prompt(
                message, conversation_context, siem_context, security_context
            )
            
            # Generate response using embedded AI service with security-optimized parameters
            response = self.ai_service.generate_response(
                query=enhanced_query,
                session_id=str(session_id),
                temperature=0.4,  # Lower temperature for more focused security analysis
                max_tokens=1536   # More tokens for detailed security analysis
            )
            
            # Post-process response for security context
            processed_response = self._enhance_security_response(response, message, security_context)
            
            # Record AI response metrics
            metrics.record_chat_message("assistant")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"🚨 **AI Processing Error**\n\nI apologize, but I'm having trouble processing your security query right now. Please try again or contact your security administrator.\n\n**Query:** {message}\n**Error:** {str(e)}"
    
    async def _generate_security_analysis(self, query: str, context: str, session_id: UUID, user_id: UUID) -> str:
        """
        Generate specialized security analysis response using embedded AI service.
        
        Args:
            query: Security query from user
            context: Security context (threat_hunting, incident_investigation, etc.)
            session_id: Chat session ID for conversation context
            user_id: User ID for personalization
            
        Returns:
            Security analysis response focused on the specific context
        """
        try:
            # Check if AI service is available
            if self.ai_service is None:
                return "⚠️ Embedded AI service is currently unavailable. Please try again later."
            
            # Check if service is ready
            if not self.ai_service.is_ready():
                return "⚠️ Embedded AI service is initializing. Please wait a moment and try again."
            
            # Build context-specific security prompt
            enhanced_query = await self._build_security_context_prompt(query, context, session_id, user_id)
            
            # Generate response using embedded AI service with security-optimized parameters
            response = self.ai_service.generate_response(
                query=enhanced_query,
                session_id=str(session_id),
                temperature=0.3,  # Lower temperature for more focused security analysis
                max_tokens=1536   # More tokens for detailed security analysis
            )
            
            # Post-process response for security context
            processed_response = self._format_security_analysis(response, query, context)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error in security analysis generation: {e}")
            return f"🚨 **Security Analysis Error**\n\nI apologize, but I'm having trouble processing your security query right now. Please try again or contact your security administrator.\n\n**Query:** {query}\n**Context:** {context}"
    
    async def _build_security_context_prompt(self, query: str, context: str, session_id: UUID, user_id: UUID) -> str:
        """
        Build context-specific security analysis prompt.
        
        Args:
            query: User security query
            context: Security context type
            session_id: Session ID for conversation context
            user_id: User ID for personalization
            
        Returns:
            Enhanced security prompt for AI processing
        """
        try:
            # Get conversation context
            conversation_context = self.get_conversation_context(session_id, user_id, max_messages=4)
            
            # Get SIEM context
            siem_context = await self._get_siem_context_for_query(query)
            
            # Build context-specific prompt
            prompt_parts = []
            
            # Add specialized system context based on security context type
            if context == "threat_hunting":
                prompt_parts.append("""You are a specialized threat hunting AI assistant. Your role is to help security analysts identify, investigate, and track advanced persistent threats (APTs) and sophisticated attack patterns.

Focus on:
- Behavioral analysis and anomaly detection
- Attack pattern recognition using MITRE ATT&CK framework
- Threat intelligence correlation
- Proactive threat hunting methodologies
- IOC development and validation
- Timeline analysis and attack reconstruction""")
            
            elif context == "incident_investigation":
                prompt_parts.append("""You are an incident response AI assistant specializing in security incident investigation and forensic analysis.

Focus on:
- Incident containment and eradication strategies
- Forensic evidence collection and analysis
- Impact assessment and damage evaluation
- Root cause analysis
- Recovery planning and lessons learned
- Compliance and reporting requirements""")
            
            elif context == "vulnerability_analysis":
                prompt_parts.append("""You are a vulnerability assessment AI assistant specializing in security weakness identification and risk analysis.

Focus on:
- Vulnerability prioritization and risk scoring
- Exploit likelihood and impact assessment
- Remediation planning and patch management
- Compensating controls and mitigation strategies
- Vulnerability lifecycle management
- Security architecture recommendations""")
            
            else:  # general security analysis
                prompt_parts.append("""You are a comprehensive security analysis AI assistant specializing in cybersecurity operations and threat analysis.

Focus on:
- Security event analysis and correlation
- Risk assessment and threat modeling
- Security control effectiveness evaluation
- Compliance and regulatory requirements
- Security awareness and training recommendations
- Strategic security planning and architecture""")
            
            # Add current SIEM status
            if siem_context and siem_context != "SIEM context unavailable.":
                prompt_parts.append(f"\nCurrent SIEM Status: {siem_context}")
            
            # Add conversation context for continuity
            if conversation_context:
                prompt_parts.append("\nRecent Conversation Context:")
                for msg in conversation_context[-2:]:  # Last exchange
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:150]  # Truncate for focus
                    if role in ['user', 'assistant'] and content:
                        prompt_parts.append(f"{role.title()}: {content}")
            
            # Add the current security query
            prompt_parts.append(f"\nSecurity Query ({context}): {query}")
            
            # Add context-specific instructions
            prompt_parts.append(f"""
Please provide a comprehensive security analysis response that:

1. **Addresses the specific {context.replace('_', ' ')} requirements**
2. **Provides actionable intelligence and recommendations**
3. **Uses appropriate security frameworks and methodologies**
4. **Includes specific SIEM queries or investigation steps**
5. **Assesses risk levels and potential impact**
6. **Suggests follow-up actions and monitoring strategies**

Format your response with clear sections using security icons (🔍, 🛡️, ⚠️, 🚨, ✅) and include:
- **Executive Summary** (key findings and risk level)
- **Technical Analysis** (detailed investigation steps)
- **Recommended Actions** (immediate and long-term)
- **SIEM Queries** (specific searches to perform)
- **Monitoring Strategy** (ongoing detection and prevention)""")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Error building security context prompt: {e}")
            # Fallback to basic security prompt
            return f"""You are a security analyst AI assistant. Analyze this {context} query: {query}

Provide detailed security analysis with actionable recommendations."""
    
    def _format_security_analysis(self, response: str, query: str, context: str) -> str:
        """
        Format security analysis response with appropriate structure and indicators.
        
        Args:
            response: Raw AI response
            query: Original security query
            context: Security context type
            
        Returns:
            Formatted security analysis response
        """
        try:
            # Clean up the response
            formatted = response.strip()
            
            # Add context-specific header if not present
            context_headers = {
                "threat_hunting": "🔍 **Threat Hunting Analysis**",
                "incident_investigation": "🚨 **Incident Investigation Analysis**",
                "vulnerability_analysis": "⚠️ **Vulnerability Analysis**",
                "general": "🛡️ **Security Analysis**"
            }
            
            header = context_headers.get(context, context_headers["general"])
            
            # Add header if response doesn't start with security indicators
            security_indicators = ['🔍', '⚠️', '🛡️', '🚨', '✅', '❌', '#', '**']
            if not any(formatted.startswith(indicator) for indicator in security_indicators):
                formatted = f"{header}\n\n{formatted}"
            
            # Add query reference
            formatted += f"\n\n---\n**Query Reference:** {query}"
            if context != "general":
                formatted += f" | **Context:** {context.replace('_', ' ').title()}"
            
            # Add timestamp
            formatted += f" | **Analysis Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
            # Add critical incident disclaimer for high-risk contexts
            high_risk_contexts = ["incident_investigation", "threat_hunting"]
            if context in high_risk_contexts:
                formatted += "\n\n⚠️ **Critical Security Notice:** For active security incidents, ensure your incident response team is notified and follow your organization's security procedures."
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting security analysis: {e}")
            return response  # Return original response if formatting fails
    
    def _detect_security_context(self, message: str) -> str:
        """
        Detect security context from user message to optimize AI response.
        
        Args:
            message: User message to analyze
            
        Returns:
            Security context type (threat_hunting, incident_investigation, vulnerability_analysis, general)
        """
        message_lower = message.lower()
        
        # Threat hunting indicators
        threat_hunting_keywords = [
            'hunt', 'hunting', 'threat', 'apt', 'advanced persistent', 'lateral movement',
            'reconnaissance', 'persistence', 'privilege escalation', 'defense evasion',
            'credential access', 'discovery', 'collection', 'command and control',
            'exfiltration', 'impact', 'mitre', 'att&ck', 'ttp', 'ioc', 'indicator'
        ]
        
        # Incident investigation indicators
        incident_keywords = [
            'incident', 'investigation', 'investigate', 'forensic', 'breach', 'compromise',
            'malware', 'attack', 'intrusion', 'unauthorized', 'suspicious activity',
            'security event', 'alert', 'containment', 'eradication', 'recovery',
            'timeline', 'root cause', 'impact assessment'
        ]
        
        # Vulnerability analysis indicators
        vulnerability_keywords = [
            'vulnerability', 'vuln', 'cve', 'exploit', 'patch', 'remediation',
            'risk assessment', 'security weakness', 'exposure', 'misconfiguration',
            'compliance', 'audit', 'penetration test', 'security scan'
        ]
        
        # Count keyword matches
        threat_score = sum(1 for keyword in threat_hunting_keywords if keyword in message_lower)
        incident_score = sum(1 for keyword in incident_keywords if keyword in message_lower)
        vuln_score = sum(1 for keyword in vulnerability_keywords if keyword in message_lower)
        
        # Determine context based on highest score
        if threat_score > incident_score and threat_score > vuln_score:
            return "threat_hunting"
        elif incident_score > vuln_score:
            return "incident_investigation"
        elif vuln_score > 0:
            return "vulnerability_analysis"
        else:
            return "general"
    
    async def _build_security_enhanced_prompt(self, message: str, conversation_context: List[Dict], 
                                            siem_context: str, security_context: str) -> str:
        """
        Build enhanced security-focused prompt for AI processing.
        
        Args:
            message: User message
            conversation_context: Recent conversation history
            siem_context: SIEM system context
            security_context: Detected security context type
            
        Returns:
            Enhanced prompt for security analysis
        """
        try:
            prompt_parts = []
            
            # Add specialized security system context
            if security_context == "threat_hunting":
                prompt_parts.append("""You are an expert threat hunting analyst specializing in proactive threat detection and advanced persistent threat (APT) analysis. Your expertise includes:

- Behavioral analysis and anomaly detection using MITRE ATT&CK framework
- Threat intelligence correlation and IOC development
- Advanced query techniques for SIEM platforms (Wazuh, Splunk, Elastic)
- Network traffic analysis and endpoint telemetry interpretation
- Attack pattern recognition and timeline reconstruction

Focus on providing actionable threat hunting guidance with specific SIEM queries and investigation steps.""")
            
            elif security_context == "incident_investigation":
                prompt_parts.append("""You are a senior incident response analyst specializing in security incident investigation and digital forensics. Your expertise includes:

- Incident containment, eradication, and recovery procedures
- Forensic evidence collection and chain of custody
- Malware analysis and reverse engineering techniques
- Impact assessment and damage evaluation methodologies
- Compliance reporting and lessons learned documentation

Focus on providing structured incident response guidance with clear investigation steps and containment strategies.""")
            
            elif security_context == "vulnerability_analysis":
                prompt_parts.append("""You are a vulnerability assessment specialist focusing on security weakness identification and risk management. Your expertise includes:

- Vulnerability prioritization using CVSS and business impact analysis
- Exploit likelihood assessment and attack surface analysis
- Remediation planning and compensating controls design
- Security architecture review and hardening recommendations
- Compliance framework mapping and audit preparation

Focus on providing risk-based vulnerability analysis with practical remediation guidance.""")
            
            else:  # general security analysis
                prompt_parts.append("""You are a comprehensive cybersecurity analyst with expertise across all security domains. Your capabilities include:

- Security event analysis and correlation across multiple data sources
- Risk assessment and threat modeling for enterprise environments
- Security control effectiveness evaluation and optimization
- Regulatory compliance and audit support (SOX, PCI-DSS, HIPAA, etc.)
- Security awareness training and strategic planning

Focus on providing holistic security analysis with actionable recommendations.""")
            
            # Add current SIEM context if available
            if siem_context and siem_context != "SIEM context unavailable.":
                prompt_parts.append(f"\n**Current SIEM Environment:**\n{siem_context}")
            
            # Add conversation context for continuity
            if conversation_context:
                prompt_parts.append("\n**Recent Conversation Context:**")
                for msg in conversation_context[-4:]:  # Last 2 exchanges
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:200]  # Truncate for focus
                    if role in ['user', 'assistant'] and content:
                        prompt_parts.append(f"**{role.title()}:** {content}")
            
            # Add the current security query with context
            prompt_parts.append(f"\n**Current Security Query ({security_context.replace('_', ' ').title()}):**\n{message}")
            
            # Add context-specific response instructions
            prompt_parts.append(f"""
**Response Requirements:**

1. **Provide {security_context.replace('_', ' ')} focused analysis** with specific, actionable recommendations
2. **Include relevant SIEM queries** for Wazuh, Splunk, or Elastic Stack where applicable
3. **Use security frameworks** (MITRE ATT&CK, NIST, ISO 27001) to structure your analysis
4. **Assess risk levels** and potential business impact of identified issues
5. **Suggest monitoring strategies** for ongoing detection and prevention
6. **Format response clearly** using security icons (🔍, 🛡️, ⚠️, 🚨, ✅) and structured sections

**Response Structure:**
- **🔍 Analysis Summary:** Key findings and risk assessment
- **🛡️ Technical Details:** Detailed investigation steps and methodologies  
- **⚠️ Risk Assessment:** Impact evaluation and threat severity
- **🚨 Immediate Actions:** Critical steps to take now
- **✅ Long-term Strategy:** Ongoing monitoring and prevention measures
- **📊 SIEM Queries:** Specific searches to perform in your SIEM platform

Provide comprehensive, actionable security guidance that a security analyst can immediately implement.""")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Error building security enhanced prompt: {e}")
            # Fallback to basic security prompt
            return f"""You are a security analyst AI assistant. Analyze this security query with focus on {security_context}: {message}

Provide detailed security analysis with actionable recommendations and specific SIEM queries."""
    
    def _enhance_security_response(self, response: str, message: str, security_context: str) -> str:
        """
        Enhance AI response with security-specific formatting and context.
        
        Args:
            response: Raw AI response
            message: Original user message
            security_context: Security context type
            
        Returns:
            Enhanced security response with proper formatting
        """
        try:
            # Clean up the response
            enhanced = response.strip()
            
            # Add context-specific header if not present
            context_headers = {
                "threat_hunting": "🔍 **Threat Hunting Analysis**",
                "incident_investigation": "🚨 **Incident Investigation Analysis**", 
                "vulnerability_analysis": "⚠️ **Vulnerability Assessment**",
                "general": "🛡️ **Security Analysis**"
            }
            
            header = context_headers.get(security_context, context_headers["general"])
            
            # Add header if response doesn't start with security indicators
            security_indicators = ['🔍', '⚠️', '🛡️', '🚨', '✅', '❌', '#', '**', '##']
            if not any(enhanced.startswith(indicator) for indicator in security_indicators):
                enhanced = f"{header}\n\n{enhanced}"
            
            # Add security context preservation footer
            enhanced += f"\n\n---\n**🔒 Security Context:** {security_context.replace('_', ' ').title()}"
            enhanced += f" | **📝 Query:** {message[:100]}{'...' if len(message) > 100 else ''}"
            enhanced += f" | **⏰ Analysis Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
            # Add session continuity note
            enhanced += "\n\n💡 **Session Context:** This analysis maintains context from your previous security queries in this session for comprehensive threat analysis."
            
            # Add critical security disclaimer for high-risk contexts
            high_risk_contexts = ["incident_investigation", "threat_hunting"]
            if security_context in high_risk_contexts:
                enhanced += "\n\n🚨 **Critical Security Notice:** For active security incidents, ensure your incident response team is notified immediately and follow your organization's established security procedures and escalation protocols."
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing security response: {e}")
            return response  # Return original response if enhancement fails
    
    def get_conversation_context(self, session_id: UUID, user_id: UUID, max_messages: int = 6) -> List[Dict[str, Any]]:
        """
        Get conversation context for security-focused analysis.
        
        Args:
            session_id: Chat session ID
            user_id: User ID
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of recent messages with security context preservation
        """
        try:
            with get_db_session() as db:
                # Get recent messages from the session
                messages = db.query(Message).filter(
                    Message.session_id == session_id
                ).order_by(Message.timestamp.desc()).limit(max_messages).all()
                
                # Convert to context format with security focus
                context = []
                for msg in reversed(messages):  # Reverse to get chronological order
                    context.append({
                        'role': msg.role.value,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'security_metadata': msg.metadata or {}
                    })
                
                return context
                
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    async def _get_siem_context_for_query(self, query: str) -> str:
        """
        Get SIEM context relevant to the security query.
        
        Args:
            query: User security query
            
        Returns:
            SIEM context information for enhanced analysis
        """
        try:
            if self.siem_service is None:
                return "SIEM service unavailable - operating in standalone analysis mode."
            
            # Get basic SIEM status
            siem_status = []
            
            # Check SIEM connectivity and basic stats
            try:
                # Get recent alert summary
                alerts_data = await self.siem_service.get_security_alerts(limit=5, time_range="1h")
                if alerts_data and alerts_data.get('total', 0) > 0:
                    siem_status.append(f"Recent alerts: {alerts_data.get('total', 0)} in last hour")
                    
                    # Add severity breakdown
                    severity_counts = {}
                    for alert in alerts_data.get('alerts', []):
                        severity = alert.get('severity', 'unknown')
                        severity_counts[severity] = severity_counts.get(severity, 0) + 1
                    
                    if severity_counts:
                        severity_summary = ", ".join([f"{sev}: {count}" for sev, count in severity_counts.items()])
                        siem_status.append(f"Alert severity breakdown: {severity_summary}")
                
            except Exception as e:
                logger.warning(f"Could not get SIEM alert context: {e}")
                siem_status.append("Alert data temporarily unavailable")
            
            # Check agent status
            try:
                agents_data = await self.siem_service.get_wazuh_agents(limit=10)
                if agents_data:
                    total_agents = agents_data.get('total', 0)
                    active_agents = len([a for a in agents_data.get('agents', []) if a.get('status') == 'active'])
                    siem_status.append(f"SIEM agents: {active_agents}/{total_agents} active")
                
            except Exception as e:
                logger.warning(f"Could not get SIEM agent context: {e}")
                siem_status.append("Agent status temporarily unavailable")
            
            # Add query-specific context hints
            query_lower = query.lower()
            if any(keyword in query_lower for keyword in ['login', 'authentication', 'auth']):
                siem_status.append("Focus: Authentication and access control events")
            elif any(keyword in query_lower for keyword in ['network', 'traffic', 'connection']):
                siem_status.append("Focus: Network traffic and connection analysis")
            elif any(keyword in query_lower for keyword in ['file', 'process', 'execution']):
                siem_status.append("Focus: Endpoint activity and process monitoring")
            elif any(keyword in query_lower for keyword in ['malware', 'virus', 'threat']):
                siem_status.append("Focus: Malware detection and threat analysis")
            
            if siem_status:
                return "SIEM Status: " + " | ".join(siem_status)
            else:
                return "SIEM context unavailable."
                
        except Exception as e:
            logger.error(f"Error getting SIEM context: {e}")
            return "SIEM context unavailable due to service error."
    
    def save_message(self, session_id: UUID, role: MessageRole, content: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Save a message to the database with security context preservation.
        
        Args:
            session_id: Chat session ID
            role: Message role (USER or ASSISTANT)
            content: Message content
            metadata: Additional metadata including security context
            
        Returns:
            Saved message object or None if failed
        """
        try:
            with get_db_session() as db:
                # Enhance metadata with security context
                enhanced_metadata = metadata or {}
                enhanced_metadata.update({
                    'timestamp': datetime.utcnow().isoformat(),
                    'security_enhanced': True,
                    'service_version': 'embedded_ai_v1.0'
                })
                
                message = Message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata=enhanced_metadata,
                    timestamp=datetime.utcnow()
                )
                
                db.add(message)
                db.commit()
                db.refresh(message)
                
                return message
                
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None
    
    def get_connection_manager(self) -> ConnectionManager:
        """Get the connection manager instance."""
        return self.connection_manager


# Global chat service instance
chat_service = ChatService()


def get_chat_service() -> ChatService:
    """Get chat service instance."""
    return chat_service