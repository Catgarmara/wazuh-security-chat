'use client';

import * as React from 'react';
import { useAuthStore } from '@/stores/auth';
import authService from '@/services/auth';
import { useUIStore } from '@/stores/ui';
import { LoginRequest } from '@/types';

interface UseAuthReturn {
  // State
  user: any;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  validateSession: () => Promise<boolean>;
  clearError: () => void;
  
  // Utilities
  isTokenExpired: () => boolean;
  willTokenExpireSoon: (minutes?: number) => boolean;
  getTokenExpiry: () => Date | null;
}

export function useAuth(): UseAuthReturn {
  const { 
    user, 
    accessToken, 
    refreshToken: storedRefreshToken,
    isAuthenticated, 
    isLoading,
    error,
    setAuth, 
    clearAuth, 
    setLoading,
    setError,
    updateTokens
  } = useAuthStore();
  
  const { addNotification } = useUIStore();
  
  // Auto-refresh token when it's about to expire
  React.useEffect(() => {
    if (!accessToken || !isAuthenticated) return;

    const checkTokenExpiry = () => {
      if (authService.willTokenExpireSoon(accessToken, 5)) {
        refreshToken();
      }
    };

    // Check immediately
    checkTokenExpiry();

    // Check every minute
    const interval = setInterval(checkTokenExpiry, 60000);
    return () => clearInterval(interval);
  }, [accessToken, isAuthenticated]);

  // Validate session on mount
  React.useEffect(() => {
    if (accessToken && isAuthenticated) {
      validateSession();
    }
  }, []);

  const login = React.useCallback(async (credentials: LoginRequest) => {
    try {
      setLoading(true);
      setError(null);

      // Use mock login for development, replace with real service in production
      const response = process.env.NODE_ENV === 'development' 
        ? await authService.mockLogin(credentials)
        : await authService.login(credentials);

      setAuth(response);

      addNotification({
        type: 'success',
        title: 'Login Successful',
        message: `Welcome back, ${response.user.username}!`,
      });

    } catch (error: any) {
      const errorMessage = error.message || 'Login failed. Please try again.';
      setError(errorMessage);
      
      addNotification({
        type: 'error',
        title: 'Login Failed',
        message: errorMessage,
      });
      
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setAuth, setLoading, setError, addNotification]);

  const logout = React.useCallback(async () => {
    try {
      setLoading(true);

      // Call logout endpoint if we have a token
      if (accessToken) {
        await authService.logout(accessToken);
      }

      clearAuth();

      addNotification({
        type: 'info',
        title: 'Logged Out',
        message: 'You have been logged out successfully.',
      });

    } catch (error: any) {
      // Always clear auth locally even if server logout fails
      clearAuth();
      console.warn('Logout error:', error);
    } finally {
      setLoading(false);
    }
  }, [accessToken, clearAuth, setLoading, addNotification]);

  const refreshToken = React.useCallback(async (): Promise<boolean> => {
    try {
      if (!storedRefreshToken) {
        throw new Error('No refresh token available');
      }

      if (authService.isTokenExpired(storedRefreshToken)) {
        throw new Error('Refresh token expired');
      }

      const response = process.env.NODE_ENV === 'development'
        ? await authService.mockLogin({ username: user?.username || 'user', password: 'mock' })
        : await authService.refreshTokens(storedRefreshToken);

      setAuth(response);
      return true;

    } catch (error: any) {
      console.error('Token refresh failed:', error);
      
      // Clear auth if refresh fails
      clearAuth();
      
      addNotification({
        type: 'warning',
        title: 'Session Expired',
        message: 'Please log in again to continue.',
      });
      
      return false;
    }
  }, [storedRefreshToken, user, setAuth, clearAuth, addNotification]);

  const validateSession = React.useCallback(async (): Promise<boolean> => {
    try {
      if (!accessToken) {
        return false;
      }

      // Check if token is expired locally first
      if (authService.isTokenExpired(accessToken)) {
        // Try to refresh the token
        return await refreshToken();
      }

      // Validate with server in production
      if (process.env.NODE_ENV !== 'development') {
        const isValid = await authService.validateToken(accessToken);
        if (!isValid) {
          clearAuth();
          return false;
        }
      }

      return true;

    } catch (error: any) {
      console.error('Session validation failed:', error);
      clearAuth();
      return false;
    }
  }, [accessToken, clearAuth, refreshToken]);

  const clearError = React.useCallback(() => {
    setError(null);
  }, [setError]);

  const isTokenExpired = React.useCallback((): boolean => {
    if (!accessToken) return true;
    return authService.isTokenExpired(accessToken);
  }, [accessToken]);

  const willTokenExpireSoon = React.useCallback((minutes: number = 5): boolean => {
    if (!accessToken) return true;
    return authService.willTokenExpireSoon(accessToken, minutes);
  }, [accessToken]);

  const getTokenExpiry = React.useCallback((): Date | null => {
    if (!accessToken) return null;
    return authService.getTokenExpiry(accessToken);
  }, [accessToken]);

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,
    
    // Actions
    login,
    logout,
    refreshToken,
    validateSession,
    clearError,
    
    // Utilities
    isTokenExpired,
    willTokenExpireSoon,
    getTokenExpiry,
  };
}