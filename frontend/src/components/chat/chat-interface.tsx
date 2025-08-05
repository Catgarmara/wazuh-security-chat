'use client';

import * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Bot, User, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { useChatStore } from '@/stores/chat';
import { useAuthStore } from '@/stores/auth';
import { useWebSocket } from '@/providers/websocket-provider';
import { formatDate } from '@/lib/utils';

export function ChatInterface() {
  const { activeSession, sessions, getActiveSessionMessages, isTyping } = useChatStore();
  const currentSession = sessions.find(s => s.id === activeSession);
  const { user } = useAuthStore();
  const { sendMessage: sendWebSocketMessage, isConnected, connectionStatus } = useWebSocket();
  const [message, setMessage] = React.useState('');
  
  const messages = getActiveSessionMessages();

  const handleSendMessage = async () => {
    if (!message.trim()) return;
    
    if (!isConnected) {
      console.error('WebSocket not connected');
      return;
    }
    
    sendWebSocketMessage(message.trim());
    setMessage('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="h-3 w-3 text-green-500" />;
      case 'connecting':
        return <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />;
      case 'error':
      case 'disconnected':
        return <WifiOff className="h-3 w-3 text-red-500" />;
      default:
        return <WifiOff className="h-3 w-3 text-gray-500" />;
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Connection Status Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/50">
        <div className="flex items-center space-x-2">
          {getConnectionIcon()}
          <span className="text-xs text-muted-foreground capitalize">
            {connectionStatus === 'connected' ? 'Connected' : connectionStatus}
          </span>
        </div>
        {currentSession && (
          <span className="text-xs text-muted-foreground">
            Session: {currentSession.title || 'New Chat'}
          </span>
        )}
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <Bot className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Welcome to Wazuh AI</h3>
              <p className="text-muted-foreground max-w-md">
                Start a conversation about security analysis, threat hunting, or ask questions about your SIEM data.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`flex-shrink-0 ${msg.role === 'user' ? 'ml-3' : 'mr-3'}`}>
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                      {msg.role === 'user' ? (
                        <User className="h-4 w-4 text-primary-foreground" />
                      ) : (
                        <Bot className="h-4 w-4 text-primary-foreground" />
                      )}
                    </div>
                  </div>
                  
                  {/* Message Content */}
                  <div className="flex-1">
                    <Card className={msg.role === 'user' ? 'bg-primary text-primary-foreground' : ''}>
                      <CardContent className="p-3">
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          {msg.content}
                        </div>
                        <div className="mt-2 text-xs opacity-70">
                          {formatDate(msg.created_at)}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </div>
            ))
          )}
          
          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start">
              <div className="flex mr-3">
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary-foreground" />
                </div>
              </div>
              <Card>
                <CardContent className="p-3">
                  <div className="flex items-center space-x-1">
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-2">
            <div className="flex-1 relative">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about security events, threat analysis, or SIEM data..."
                className="pr-12"
              />
              <Button
                size="sm"
                onClick={handleSendMessage}
                disabled={!message.trim() || !isConnected}
                className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 p-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            AI responses are generated based on your security data and may contain errors. Always verify critical information.
          </p>
        </div>
      </div>
    </div>
  );
}