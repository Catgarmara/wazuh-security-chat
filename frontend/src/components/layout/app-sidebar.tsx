'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  MessageSquare, 
  Plus, 
  Search, 
  Settings, 
  Shield, 
  Activity,
  ChevronLeft,
  ChevronRight,
  Bot,
  User,
  Clock,
  Archive,
  Star,
  Filter
} from 'lucide-react';
import { useUIStore } from '@/stores/ui';
import { useChatStore } from '@/stores/chat';
import { useAuthStore } from '@/stores/auth';
import { formatRelativeTime } from '@/lib/utils';

interface AppSidebarProps {
  className?: string;
  user?: any;
  onLogout?: () => void;
}

export function AppSidebar({ className, user, onLogout }: AppSidebarProps) {
  const { sidebar_collapsed, toggleSidebar, view_mode, setViewMode, setActiveSession } = useUIStore();
  const { sessions, activeSession } = useChatStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [showArchived, setShowArchived] = React.useState(false);

  const filteredSessions = React.useMemo(() => {
    return sessions.filter(session => {
      const matchesSearch = !searchQuery || 
        session.title?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesArchived = showArchived || session.is_active;
      return matchesSearch && matchesArchived;
    });
  }, [sessions, searchQuery, showArchived]);

  const handleSessionClick = (sessionId: string) => {
    setActiveSession(sessionId);
    setViewMode('chat');
  };

  const handleNewChat = () => {
    // This will be implemented when we add the chat functionality
    setViewMode('chat');
  };

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-background transition-all duration-300',
        sidebar_collapsed ? 'w-16' : 'w-80',
        className
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center border-b px-4">
        {!sidebar_collapsed && (
          <div className="flex items-center space-x-3">
            <Shield className="h-6 w-6 text-primary" />
            <span className="font-semibold text-lg">Wazuh AI</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn('ml-auto', sidebar_collapsed && 'mx-auto')}
        >
          {sidebar_collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {!sidebar_collapsed && (
        <>
          {/* New Chat Button */}
          <div className="p-4 border-b">
            <Button 
              onClick={handleNewChat}
              className="w-full justify-start"
              variant="default"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Chat
            </Button>
          </div>

          {/* Search */}
          <div className="p-4 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-10 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                onClick={() => setShowArchived(!showArchived)}
              >
                <Filter className={cn('h-3 w-3', showArchived && 'text-primary')} />
              </Button>
            </div>
          </div>

          {/* Chat Sessions */}
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {filteredSessions.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  {searchQuery ? 'No conversations found' : 'No conversations yet'}
                </div>
              ) : (
                filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => handleSessionClick(session.id)}
                    className={cn(
                      'group cursor-pointer rounded-lg p-3 hover:bg-accent transition-colors',
                      activeSession === session.id && 'bg-accent'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <h4 className="text-sm font-medium truncate">
                            {session.title || 'Untitled Chat'}
                          </h4>
                        </div>
                        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>{formatRelativeTime(session.updated_at || session.created_at)}</span>
                          {session.message_count > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              {session.message_count}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end space-y-1">
                        {!session.is_active && (
                          <Archive className="h-3 w-3 text-muted-foreground" />
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </>
      )}

      {/* Navigation */}
      <div className="border-t p-2">
        <div className="space-y-1">
          {[
            { 
              icon: MessageSquare, 
              label: 'Chat', 
              value: 'chat' as const,
              active: view_mode === 'chat'
            },
            { 
              icon: Activity, 
              label: 'Dashboard', 
              value: 'dashboard' as const,
              active: view_mode === 'dashboard'
            },
            { 
              icon: Settings, 
              label: 'Settings', 
              value: 'settings' as const,
              active: view_mode === 'settings'
            },
          ].map((item) => (
            <Button
              key={item.value}
              variant={item.active ? 'secondary' : 'ghost'}
              size={sidebar_collapsed ? 'icon' : 'sm'}
              onClick={() => setViewMode(item.value)}
              className={cn(
                'w-full',
                !sidebar_collapsed && 'justify-start',
                item.active && 'bg-accent'
              )}
            >
              <item.icon className={cn('h-4 w-4', !sidebar_collapsed && 'mr-2')} />
              {!sidebar_collapsed && item.label}
            </Button>
          ))}
        </div>
      </div>

      {/* User Info */}
      <div className="border-t p-4">
        {sidebar_collapsed ? (
          <div className="flex justify-center">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
              <User className="h-4 w-4 text-primary-foreground" />
            </div>
          </div>
        ) : (
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
              <User className="h-4 w-4 text-primary-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.username || 'Anonymous'}
              </p>
              <p className="text-xs text-muted-foreground capitalize">
                {user?.role || 'viewer'}
              </p>
            </div>
            <Badge variant={user?.is_active ? 'online' : 'offline'} className="text-xs">
              {user?.is_active ? 'Online' : 'Offline'}
            </Badge>
          </div>
        )}
      </div>
    </div>
  );
}