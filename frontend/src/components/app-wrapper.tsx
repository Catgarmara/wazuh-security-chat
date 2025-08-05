'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/use-auth';
import { ProtectedRoute, SessionStatus } from '@/components/auth/protected-route';
import { AppLayout } from '@/components/layout/app-layout';
import { LoginForm } from '@/components/auth/login-form';
import { Button } from '@/components/ui/button';
import { LogOut, User } from 'lucide-react';

interface AppWrapperProps {
  children: React.ReactNode;
}

export function AppWrapper({ children }: AppWrapperProps) {
  return (
    <ProtectedRoute fallback={<LoginForm />}>
      <AuthenticatedApp>{children}</AuthenticatedApp>
    </ProtectedRoute>
  );
}

function AuthenticatedApp({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <AppLayout
      user={user}
      onLogout={handleLogout}
      headerActions={
        <div className="flex items-center space-x-4">
          <SessionStatus />
          <div className="flex items-center space-x-2 text-sm">
            <User className="h-4 w-4" />
            <span>{user?.username}</span>
            <span className="text-muted-foreground">({user?.role})</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="h-8"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      }
    >
      {children}
    </AppLayout>
  );
}