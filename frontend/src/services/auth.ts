'use client';

import { LoginRequest, TokenResponse, User } from '@/types';

class AuthService {
  private baseURL: string;
  private tokenKey = 'wazuh-ai-auth';

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  /**
   * Authenticate user with credentials
   */
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    try {
      const response = await fetch(`${this.baseURL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Authentication failed: ${response.status}`);
      }

      const data: TokenResponse = await response.json();
      
      // Validate response structure
      if (!data.access_token || !data.user) {
        throw new Error('Invalid authentication response');
      }

      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Authentication request failed');
    }
  }

  /**
   * Refresh authentication tokens
   */
  async refreshTokens(refreshToken: string): Promise<TokenResponse> {
    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${refreshToken}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Token refresh failed');
      }

      const data: TokenResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Token refresh request failed');
    }
  }

  /**
   * Logout user and invalidate tokens
   */
  async logout(accessToken: string): Promise<void> {
    try {
      await fetch(`${this.baseURL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Accept': 'application/json',
        },
      });
    } catch (error) {
      // Log error but don't throw - logout should always succeed locally
      console.warn('Logout request failed:', error);
    }
  }

  /**
   * Get current user profile
   */
  async getProfile(accessToken: string): Promise<User> {
    try {
      const response = await fetch(`${this.baseURL}/auth/profile`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Profile fetch failed');
      }

      const user: User = await response.json();
      return user;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Profile request failed');
    }
  }

  /**
   * Validate JWT token
   */
  async validateToken(accessToken: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/auth/validate`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Accept': 'application/json',
        },
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Parse JWT token payload (client-side only for non-sensitive data)
   */
  parseToken(token: string): any {
    try {
      const payload = token.split('.')[1];
      const decoded = atob(payload);
      return JSON.parse(decoded);
    } catch (error) {
      return null;
    }
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token: string): boolean {
    try {
      const payload = this.parseToken(token);
      if (!payload || !payload.exp) {
        return true;
      }

      const currentTime = Math.floor(Date.now() / 1000);
      return payload.exp < currentTime;
    } catch (error) {
      return true;
    }
  }

  /**
   * Get token expiry time
   */
  getTokenExpiry(token: string): Date | null {
    try {
      const payload = this.parseToken(token);
      if (!payload || !payload.exp) {
        return null;
      }

      return new Date(payload.exp * 1000);
    } catch (error) {
      return null;
    }
  }

  /**
   * Check if token expires within specified minutes
   */
  willTokenExpireSoon(token: string, minutes: number = 5): boolean {
    try {
      const expiry = this.getTokenExpiry(token);
      if (!expiry) {
        return true;
      }

      const warningTime = new Date();
      warningTime.setMinutes(warningTime.getMinutes() + minutes);
      
      return expiry <= warningTime;
    } catch (error) {
      return true;
    }
  }

  /**
   * Create authentication headers for API requests
   */
  createAuthHeaders(accessToken: string): Record<string, string> {
    return {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Mock login for development (remove in production)
   */
  async mockLogin(credentials: LoginRequest): Promise<TokenResponse> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Mock validation
    if (!credentials.username || !credentials.password) {
      throw new Error('Username and password are required');
    }

    // Mock response
    const mockResponse: TokenResponse = {
      access_token: this.generateMockToken(credentials.username),
      refresh_token: this.generateMockToken(credentials.username, true),
      token_type: 'Bearer',
      expires_in: 3600,
      user: {
        id: '1',
        username: credentials.username,
        email: `${credentials.username}@wazuh-ai.local`,
        role: credentials.username === 'admin' ? 'admin' : 'analyst',
        is_active: true,
        created_at: new Date().toISOString(),
      }
    };

    return mockResponse;
  }

  /**
   * Generate mock JWT token for development
   */
  private generateMockToken(username: string, isRefresh: boolean = false): string {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({
      sub: username,
      username,
      role: username === 'admin' ? 'admin' : 'analyst',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + (isRefresh ? 86400 : 3600), // 24h for refresh, 1h for access
      token_type: isRefresh ? 'refresh' : 'access'
    }));
    const signature = btoa('mock-signature');
    
    return `${header}.${payload}.${signature}`;
  }
}

// Export singleton instance
export const authService = new AuthService();
export default authService;