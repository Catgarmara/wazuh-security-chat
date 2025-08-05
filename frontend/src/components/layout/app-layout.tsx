'use client';

import * as React from 'react';
import { AppSidebar } from './app-sidebar';
import { ModelSelector } from '@/components/models/model-selector';
import { useUIStore } from '@/stores/ui';
import { cn } from '@/lib/utils';

interface AppLayoutProps {
  children: React.ReactNode;
  user?: any;
  onLogout?: () => void;
  headerActions?: React.ReactNode;
}

export function AppLayout({ children, user, onLogout, headerActions }: AppLayoutProps) {
  const { view_mode } = useUIStore();

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <AppSidebar user={user} onLogout={onLogout} />
      
      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar - Model Selector and Header Actions */}
        {view_mode === 'chat' && (
          <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-14 items-center justify-between px-4">
              <ModelSelector />
              {headerActions && (
                <div className="flex items-center">{headerActions}</div>
              )}
            </div>
          </div>
        )}
        
        {/* Header Actions for non-chat views */}
        {view_mode !== 'chat' && headerActions && (
          <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-14 items-center justify-end px-4">
              {headerActions}
            </div>
          </div>
        )}
        
        {/* Main Content Area */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}