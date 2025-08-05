'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Settings as SettingsIcon, User, Shield, Palette, Bell } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';

export function Settings() {
  const { user } = useAuthStore();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center space-x-2">
        <SettingsIcon className="h-6 w-6" />
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* User Profile */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <User className="h-5 w-5" />
              <span>User Profile</span>
            </CardTitle>
            <CardDescription>Manage your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Username</label>
              <div className="text-sm">{user?.username}</div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <div className="text-sm">{user?.email}</div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Role</label>
              <Badge variant="secondary" className="capitalize">
                {user?.role}
              </Badge>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Badge variant={user?.is_active ? 'online' : 'offline'}>
                {user?.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>Security</span>
            </CardTitle>
            <CardDescription>Manage security preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Session Timeout</div>
                <div className="text-sm text-muted-foreground">30 minutes</div>
              </div>
              <Button variant="outline" size="sm">
                Change
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Two-Factor Authentication</div>
                <div className="text-sm text-muted-foreground">Not enabled</div>
              </div>
              <Button variant="outline" size="sm">
                Enable
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Login Notifications</div>
                <div className="text-sm text-muted-foreground">Email alerts for new logins</div>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Palette className="h-5 w-5" />
              <span>Appearance</span>
            </CardTitle>
            <CardDescription>Customize the interface</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Theme</div>
                <div className="text-sm text-muted-foreground">System (Auto)</div>
              </div>
              <Button variant="outline" size="sm">
                Change
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Language</div>
                <div className="text-sm text-muted-foreground">English</div>
              </div>
              <Button variant="outline" size="sm">
                Change
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Timezone</div>
                <div className="text-sm text-muted-foreground">UTC</div>
              </div>
              <Button variant="outline" size="sm">
                Change
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>Notifications</span>
            </CardTitle>
            <CardDescription>Manage alert preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Critical Alerts</div>
                <div className="text-sm text-muted-foreground">Immediate notifications</div>
              </div>
              <Badge variant="online">Enabled</Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">High Priority Alerts</div>
                <div className="text-sm text-muted-foreground">Within 5 minutes</div>
              </div>
              <Badge variant="online">Enabled</Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">System Status Changes</div>
                <div className="text-sm text-muted-foreground">Service health updates</div>
              </div>
              <Badge variant="outline">Disabled</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}