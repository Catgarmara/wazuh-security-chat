# WebSocket Integration

This document describes the WebSocket implementation for real-time chat functionality in the Wazuh AI Companion frontend.

## Architecture

### WebSocket Provider (`/src/providers/websocket-provider.tsx`)

The WebSocket provider manages the real-time connection between the frontend and backend services. It provides:

- **Connection Management**: Automatic connection, reconnection with exponential backoff
- **Authentication**: JWT token-based WebSocket authentication
- **Message Handling**: Bidirectional message processing for chat and system notifications
- **State Management**: Integration with Zustand stores for chat and UI state
- **Error Handling**: Comprehensive error handling with user notifications

### Message Types

The WebSocket supports the following message types:

```typescript
interface WebSocketMessage {
  type: 'chat_message' | 'chat_response' | 'typing_start' | 'typing_stop' | 
        'error' | 'connection' | 'session_created' | 'system_notification';
  data: any;
  timestamp: string;
}
```

### Integration Points

1. **Chat Store** (`/src/stores/chat.ts`)
   - Manages chat sessions and messages
   - Handles typing indicators
   - Supports session creation and management

2. **UI Store** (`/src/stores/ui.ts`)
   - Manages system notifications
   - Toast notifications for connection status

3. **Chat Interface** (`/src/components/chat/chat-interface.tsx`)
   - Real-time message display
   - Connection status indicator
   - Typing indicators

## Environment Configuration

Set the WebSocket URL in your environment:

```bash
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Usage

The WebSocket provider is automatically initialized when a user is authenticated. It connects to the backend WebSocket endpoint with the user's JWT token.

### Sending Messages

```typescript
const { sendMessage } = useWebSocket();
sendMessage("Hello, AI assistant!");
```

### Connection Status

```typescript
const { isConnected, connectionStatus } = useWebSocket();
// connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error'
```

## Security Features

- JWT token authentication
- Automatic token refresh handling
- Connection validation
- Message validation
- Rate limiting (handled by backend)

## Error Handling

The WebSocket provider includes comprehensive error handling:

- **Connection Errors**: Automatic reconnection with exponential backoff
- **Authentication Errors**: Redirects to login
- **Message Errors**: User notifications via toast system
- **Network Errors**: Graceful degradation with retry logic

## Backend Integration

The frontend expects the backend to provide:

1. WebSocket endpoint at `/ws`
2. JWT token validation
3. Message routing and AI response generation
4. Session management
5. System notification broadcasting

## Testing

For testing without a backend, the WebSocket provider includes mock message handling and will gracefully handle connection failures with appropriate user feedback.