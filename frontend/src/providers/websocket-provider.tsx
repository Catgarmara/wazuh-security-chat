'use client';

import * as React from 'react';
import { useAuthStore } from '@/stores/auth';
import { useChatStore } from '@/stores/chat';
import { useUIStore } from '@/stores/ui';
import { WebSocketMessage, ChatMessage, SystemNotification } from '@/types';

interface WebSocketContextType {
  isConnected: boolean;
  isConnecting: boolean;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  sendMessage: (message: string, sessionId?: string) => void;
  reconnect: () => void;
}

const WebSocketContext = React.createContext<WebSocketContextType | null>(null);

export function useWebSocket() {
  const context = React.useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { accessToken, isAuthenticated, user } = useAuthStore();
  const { 
    addMessage, 
    updateMessage, 
    activeSession, 
    createSession,
    setTyping 
  } = useChatStore();
  const { addNotification } = useUIStore();

  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = React.useState(false);
  const [isConnecting, setIsConnecting] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
  const [shouldReconnect, setShouldReconnect] = React.useState(true);

  const maxReconnectAttempts = 5;
  const reconnectDelay = 1000; // Start with 1 second

  const connect = React.useCallback(() => {
    if (!isAuthenticated || !accessToken || socket?.readyState === WebSocket.CONNECTING) {
      return;
    }

    if (socket?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setConnectionStatus('connecting');

    try {
      // Use environment variable or fallback to localhost
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
      const url = `${wsUrl}?token=${accessToken}`;
      
      const newSocket = new WebSocket(url);

      newSocket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setIsConnecting(false);
        setConnectionStatus('connected');
        setReconnectAttempts(0);
        
        addNotification({
          type: 'success',
          title: 'Connected',
          message: 'Real-time connection established',
        });

        // Send initial connection message
        const initMessage: WebSocketMessage = {
          type: 'connection',
          data: {
            user_id: user?.id,
            session_id: activeSession?.id
          },
          timestamp: new Date().toISOString()
        };

        newSocket.send(JSON.stringify(initMessage));
      };

      newSocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      newSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        addNotification({
          type: 'error',
          title: 'Connection Error',
          message: 'Failed to establish real-time connection',
        });
      };

      newSocket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        
        if (event.code !== 1000 && shouldReconnect && reconnectAttempts < maxReconnectAttempts) {
          // Attempt to reconnect with exponential backoff
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts);
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setConnectionStatus('error');
          addNotification({
            type: 'error',
            title: 'Connection Lost',
            message: 'Unable to reconnect to real-time service',
          });
        } else {
          setConnectionStatus('disconnected');
        }
      };

      setSocket(newSocket);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setIsConnecting(false);
      setConnectionStatus('error');
    }
  }, [isAuthenticated, accessToken, socket, activeSession, user, addNotification, reconnectAttempts, shouldReconnect]);

  const handleWebSocketMessage = React.useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'chat_message':
        const chatMessage = message.data as ChatMessage;
        addMessage(chatMessage.session_id, chatMessage);
        break;

      case 'chat_response':
        const responseData = message.data as ChatMessage;
        addMessage(responseData.session_id, responseData);
        setTyping(false);
        break;

      case 'typing_start':
        setTyping(true);
        break;

      case 'typing_stop':
        setTyping(false);
        break;

      case 'system_notification':
        const notification = message.data as SystemNotification;
        addNotification({
          type: notification.type,
          title: notification.title,
          message: notification.message,
        });
        break;

      case 'session_created':
        // Handle new session creation if needed
        break;

      case 'error':
        console.error('WebSocket error message:', message.data);
        addNotification({
          type: 'error',
          title: 'Error',
          message: message.data.message || 'An error occurred',
        });
        break;

      default:
        console.log('Unhandled WebSocket message type:', message.type);
    }
  }, [addMessage, setTyping, addNotification]);

  const sendMessage = React.useCallback((content: string, sessionId?: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      addNotification({
        type: 'error',
        title: 'Connection Error',
        message: 'Not connected to real-time service',
      });
      return;
    }

    // Ensure we have an active session
    let targetSessionId = sessionId || activeSession?.id;
    if (!targetSessionId) {
      // Create a new session if none exists
      const newSession = createSession();
      targetSessionId = newSession.id;
    }

    const message: WebSocketMessage = {
      type: 'chat_message',
      data: {
        id: crypto.randomUUID(),
        session_id: targetSessionId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      timestamp: new Date().toISOString()
    };

    // Add user message to store immediately
    addMessage(targetSessionId, message.data as ChatMessage);
    
    // Send to server
    socket.send(JSON.stringify(message));
    
    // Show typing indicator for AI response
    setTyping(true);
  }, [socket, activeSession, addNotification, addMessage, createSession, setTyping]);

  const reconnect = React.useCallback(() => {
    setReconnectAttempts(0);
    setShouldReconnect(true);
    if (socket) {
      socket.close();
    }
    connect();
  }, [socket, connect]);

  const disconnect = React.useCallback(() => {
    setShouldReconnect(false);
    if (socket) {
      socket.close(1000, 'User initiated disconnect');
    }
  }, [socket]);

  // Connect when authenticated
  React.useEffect(() => {
    if (isAuthenticated && accessToken && !socket) {
      connect();
    }
  }, [isAuthenticated, accessToken, connect, socket]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Handle authentication state changes
  React.useEffect(() => {
    if (!isAuthenticated && socket) {
      disconnect();
      setSocket(null);
    }
  }, [isAuthenticated, socket, disconnect]);

  const contextValue: WebSocketContextType = {
    isConnected,
    isConnecting,
    connectionStatus,
    sendMessage,
    reconnect,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
}