'use client';

import { AppWrapper } from '@/components/app-wrapper';
import { ChatInterface } from '@/components/chat/chat-interface';
import { Dashboard } from '@/components/dashboard/dashboard';
import { Settings } from '@/components/settings/settings';
import { useUIStore } from '@/stores/ui';

export default function HomePage() {
  const { view_mode } = useUIStore();

  // Render main content based on selected view
  const renderMainContent = () => {
    switch (view_mode) {
      case 'chat':
        return <ChatInterface />;
      case 'dashboard':
        return <Dashboard />;
      case 'settings':
        return <Settings />;
      default:
        return <ChatInterface />;
    }
  };

  return (
    <AppWrapper>
      {renderMainContent()}
    </AppWrapper>
  );
}