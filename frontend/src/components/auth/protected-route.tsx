'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/use-auth';
import { LoginForm } from '@/components/auth/login-form';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Shield, Lock } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'analyst' | 'viewer';
  fallback?: React.ReactNode;
}

export function ProtectedRoute({ 
  children, 
  requiredRole,
  fallback 
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading, validateSession } = useAuth();
  const [isValidating, setIsValidating] = React.useState(true);

  // Validate session on mount
  React.useEffect(() => {
    const validate = async () => {
      if (isAuthenticated) {
        await validateSession();
      }
      setIsValidating(false);
    };

    validate();
  }, [isAuthenticated, validateSession]);

  // Show loading spinner while validating
  if (isLoading || isValidating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mx-auto mb-4" />
          <div className="text-lg font-medium">Authenticating...</div>
          <div className="text-sm text-muted-foreground mt-2">
            Verifying your credentials
          </div>
        </div>
      </div>
    );
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return fallback || <LoginForm />;
  }

  // Check role-based access
  if (requiredRole && user?.role !== requiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-md text-center">
          <div className="flex items-center justify-center mb-6">
            <div className="p-3 bg-red-100 dark:bg-red-900 rounded-full">
              <Lock className="h-8 w-8 text-red-600" />
            </div>
          </div>
          
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground mb-6">
            You don't have permission to access this resource.
          </p>
          
          <div className="bg-muted/50 rounded-lg p-4 mb-6">
            <div className="text-sm">
              <div className="flex justify-between mb-2">
                <span>Your Role:</span>
                <span className="font-medium capitalize">{user?.role}</span>
              </div>
              <div className="flex justify-between">
                <span>Required Role:</span>
                <span className="font-medium capitalize">{requiredRole}</span>
              </div>
            </div>
          </div>
          
          <p className="text-xs text-muted-foreground">
            Contact your administrator if you believe this is an error.
          </p>
        </div>
      </div>
    );
  }

  // Render protected content
  return <>{children}</>;
}

// Higher-order component for role-based protection
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requiredRole?: 'admin' | 'analyst' | 'viewer'
) {
  const AuthenticatedComponent = (props: P) => {
    return (
      <ProtectedRoute requiredRole={requiredRole}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };

  AuthenticatedComponent.displayName = `withAuth(${Component.displayName || Component.name})`;
  return AuthenticatedComponent;
}

// Role-based access control component
interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: Array<'admin' | 'analyst' | 'viewer'>;
  fallback?: React.ReactNode;
}

export function RoleGuard({ children, allowedRoles, fallback }: RoleGuardProps) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return null;
  }

  if (!allowedRoles.includes(user.role)) {
    return fallback || null;
  }

  return <>{children}</>;
}

// Session status indicator component
export function SessionStatus() {
  const { user, isAuthenticated, getTokenExpiry, willTokenExpireSoon } = useAuth();
  const [timeLeft, setTimeLeft] = React.useState<string>('');

  React.useEffect(() => {
    if (!isAuthenticated) return;

    const updateTimeLeft = () => {
      const expiry = getTokenExpiry();
      if (!expiry) return;

      const now = new Date();
      const diff = expiry.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeLeft('Expired');
        return;
      }

      const minutes = Math.floor(diff / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      if (minutes > 60) {
        const hours = Math.floor(minutes / 60);
        setTimeLeft(`${hours}h ${minutes % 60}m`);
      } else if (minutes > 0) {
        setTimeLeft(`${minutes}m ${seconds}s`);
      } else {
        setTimeLeft(`${seconds}s`);
      }
    };

    updateTimeLeft();
    const interval = setInterval(updateTimeLeft, 1000);

    return () => clearInterval(interval);
  }, [isAuthenticated, getTokenExpiry]);

  if (!isAuthenticated) return null;

  const isExpiringSoon = willTokenExpireSoon(5);

  return (
    <div className="flex items-center space-x-2 text-xs">
      <Shield className={`h-3 w-3 ${isExpiringSoon ? 'text-yellow-500' : 'text-green-500'}`} />
      <span className="text-muted-foreground">
        Session: <span className={isExpiringSoon ? 'text-yellow-500' : 'text-foreground'}>{timeLeft}</span>
      </span>
    </div>
  );
}