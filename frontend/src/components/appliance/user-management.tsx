'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Users,
  UserPlus,
  Shield,
  Settings,
  Eye,
  Edit,
  Trash2,
  Crown,
  User,
  Lock,
  Unlock,
  Calendar,
  Activity,
  Download,
  HardDrive,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

interface User {
  id: string;
  username: string;
  email: string;
  fullName: string;
  role: 'admin' | 'analyst' | 'viewer' | 'custom';
  status: 'active' | 'inactive' | 'locked';
  lastLogin: string;
  createdAt: string;
  permissions: {
    canDownloadModels: boolean;
    canManageUsers: boolean;
    canViewLogs: boolean;
    canConfigureSystem: boolean;
    canAccessAPI: boolean;
    maxModelSize: '1GB' | '5GB' | '15GB' | 'unlimited';
    allowedCategories: string[];
    storageQuota: number; // in GB
    usedStorage: number; // in GB
  };
  activity: {
    queriesThisWeek: number;
    modelsDownloaded: number;
    lastActivity: string;
  };
}

interface Role {
  id: string;
  name: string;
  description: string;
  permissions: User['permissions'];
  userCount: number;
  isBuiltIn: boolean;
}

const mockUsers: User[] = [
  {
    id: 'user-001',
    username: 'admin',
    email: 'admin@company.com',
    fullName: 'System Administrator',
    role: 'admin',
    status: 'active',
    lastLogin: '2024-01-15T10:30:00Z',
    createdAt: '2024-01-01T00:00:00Z',
    permissions: {
      canDownloadModels: true,
      canManageUsers: true,
      canViewLogs: true,
      canConfigureSystem: true,
      canAccessAPI: true,
      maxModelSize: 'unlimited',
      allowedCategories: ['security', 'general', 'code', 'reasoning'],
      storageQuota: 500,
      usedStorage: 127
    },
    activity: {
      queriesThisWeek: 234,
      modelsDownloaded: 8,
      lastActivity: '2024-01-15T10:30:00Z'
    }
  },
  {
    id: 'user-002',
    username: 'analyst1',
    email: 'analyst1@company.com',
    fullName: 'Sarah Johnson',
    role: 'analyst',
    status: 'active',
    lastLogin: '2024-01-15T09:15:00Z',
    createdAt: '2024-01-05T00:00:00Z',
    permissions: {
      canDownloadModels: true,
      canManageUsers: false,
      canViewLogs: true,
      canConfigureSystem: false,
      canAccessAPI: true,
      maxModelSize: '15GB',
      allowedCategories: ['security', 'general'],
      storageQuota: 100,
      usedStorage: 45
    },
    activity: {
      queriesThisWeek: 156,
      modelsDownloaded: 3,
      lastActivity: '2024-01-15T09:15:00Z'
    }
  },
  {
    id: 'user-003',
    username: 'viewer1',
    email: 'viewer1@company.com',
    fullName: 'Mike Chen',
    role: 'viewer',
    status: 'active',
    lastLogin: '2024-01-14T16:45:00Z',
    createdAt: '2024-01-10T00:00:00Z',
    permissions: {
      canDownloadModels: false,
      canManageUsers: false,
      canViewLogs: true,
      canConfigureSystem: false,
      canAccessAPI: false,
      maxModelSize: '1GB',
      allowedCategories: ['security'],
      storageQuota: 10,
      usedStorage: 0
    },
    activity: {
      queriesThisWeek: 89,
      modelsDownloaded: 0,
      lastActivity: '2024-01-14T16:45:00Z'
    }
  }
];

const mockRoles: Role[] = [
  {
    id: 'role-admin',
    name: 'Administrator',
    description: 'Full system access with all permissions',
    permissions: {
      canDownloadModels: true,
      canManageUsers: true,
      canViewLogs: true,
      canConfigureSystem: true,
      canAccessAPI: true,
      maxModelSize: 'unlimited',
      allowedCategories: ['security', 'general', 'code', 'reasoning'],
      storageQuota: 500,
      usedStorage: 0
    },
    userCount: 1,
    isBuiltIn: true
  },
  {
    id: 'role-analyst',
    name: 'Security Analyst',
    description: 'Can analyze logs, download models, and use APIs',
    permissions: {
      canDownloadModels: true,
      canManageUsers: false,
      canViewLogs: true,
      canConfigureSystem: false,
      canAccessAPI: true,
      maxModelSize: '15GB',
      allowedCategories: ['security', 'general'],
      storageQuota: 100,
      usedStorage: 0
    },
    userCount: 1,
    isBuiltIn: true
  },
  {
    id: 'role-viewer',
    name: 'Viewer',
    description: 'Read-only access to logs and basic functionality',
    permissions: {
      canDownloadModels: false,
      canManageUsers: false,
      canViewLogs: true,
      canConfigureSystem: false,
      canAccessAPI: false,
      maxModelSize: '1GB',
      allowedCategories: ['security'],
      storageQuota: 10,
      usedStorage: 0
    },
    userCount: 1,
    isBuiltIn: true
  }
];

export function UserManagement() {
  const [users, setUsers] = React.useState<User[]>(mockUsers);
  const [roles, setRoles] = React.useState<Role[]>(mockRoles);
  const [selectedUser, setSelectedUser] = React.useState<User | null>(null);
  const [isCreateUserOpen, setIsCreateUserOpen] = React.useState(false);
  const [isEditUserOpen, setIsEditUserOpen] = React.useState(false);

  const formatTime = (timeString: string) => {
    return new Date(timeString).toLocaleString();
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin': return <Crown className="h-4 w-4 text-yellow-600" />;
      case 'analyst': return <Shield className="h-4 w-4 text-blue-600" />;
      case 'viewer': return <Eye className="h-4 w-4 text-green-600" />;
      default: return <User className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'inactive': return 'text-gray-600';
      case 'locked': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'inactive': return <User className="h-4 w-4 text-gray-600" />;
      case 'locked': return <Lock className="h-4 w-4 text-red-600" />;
      default: return <User className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatBytes = (gb: number) => {
    return `${gb} GB`;
  };

  const getStorageUsage = (used: number, quota: number) => {
    return (used / quota) * 100;
  };

  const handleLockUser = (userId: string) => {
    setUsers(prev => prev.map(user => 
      user.id === userId 
        ? { ...user, status: user.status === 'locked' ? 'active' : 'locked' }
        : user
    ));
  };

  const handleDeleteUser = (userId: string) => {
    setUsers(prev => prev.filter(user => user.id !== userId));
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setIsEditUserOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">User Management</h2>
          <p className="text-muted-foreground">
            Manage users, roles, and permissions
          </p>
        </div>
        <Button onClick={() => setIsCreateUserOpen(true)}>
          <UserPlus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium">Total Users</p>
                <p className="text-2xl font-bold">{users.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">Active Users</p>
                <p className="text-2xl font-bold">{users.filter(u => u.status === 'active').length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Crown className="h-5 w-5 text-yellow-600" />
              <div>
                <p className="text-sm font-medium">Administrators</p>
                <p className="text-2xl font-bold">{users.filter(u => u.role === 'admin').length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium">Active Sessions</p>
                <p className="text-2xl font-bold">12</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="users" className="space-y-4">
        <TabsList>
          <TabsTrigger value="users" className="flex items-center space-x-2">
            <Users className="h-4 w-4" />
            <span>Users</span>
          </TabsTrigger>
          <TabsTrigger value="roles" className="flex items-center space-x-2">
            <Shield className="h-4 w-4" />
            <span>Roles</span>
          </TabsTrigger>
        </TabsList>

        {/* Users Tab */}
        <TabsContent value="users">
          <ScrollArea className="h-[600px]">
            <div className="space-y-4 pr-4">
              {users.map((user) => (
                <Card key={user.id}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      {/* User Info */}
                      <div className="space-y-3">
                        <div className="flex items-center space-x-3">
                          {getStatusIcon(user.status)}
                          <div>
                            <h3 className="font-semibold text-lg">{user.fullName}</h3>
                            <p className="text-sm text-muted-foreground">@{user.username} • {user.email}</p>
                          </div>
                          <div className="flex items-center space-x-2">
                            {getRoleIcon(user.role)}
                            <Badge variant="outline" className="capitalize">
                              {user.role}
                            </Badge>
                            <Badge variant={user.status === 'active' ? 'online' : 'secondary'}>
                              {user.status}
                            </Badge>
                          </div>
                        </div>

                        {/* Activity Stats */}
                        <div className="grid grid-cols-3 gap-6 text-sm">
                          <div>
                            <p className="text-muted-foreground">Queries This Week</p>
                            <p className="font-semibold">{user.activity.queriesThisWeek}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Models Downloaded</p>
                            <p className="font-semibold">{user.activity.modelsDownloaded}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Last Login</p>
                            <p className="font-semibold">{formatTime(user.lastLogin)}</p>
                          </div>
                        </div>

                        {/* Storage Usage */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Storage Usage</span>
                            <span className="font-medium">
                              {formatBytes(user.permissions.usedStorage)} / {formatBytes(user.permissions.storageQuota)}
                            </span>
                          </div>
                          <div className="w-full bg-secondary rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full transition-all"
                              style={{ 
                                width: `${Math.min(getStorageUsage(user.permissions.usedStorage, user.permissions.storageQuota), 100)}%` 
                              }}
                            />
                          </div>
                        </div>

                        {/* Permissions Summary */}
                        <div className="flex flex-wrap gap-2">
                          {user.permissions.canDownloadModels && (
                            <Badge variant="secondary" className="text-xs">
                              <Download className="h-3 w-3 mr-1" />
                              Can Download Models
                            </Badge>
                          )}
                          {user.permissions.canManageUsers && (
                            <Badge variant="secondary" className="text-xs">
                              <Users className="h-3 w-3 mr-1" />
                              User Management
                            </Badge>
                          )}
                          {user.permissions.canConfigureSystem && (
                            <Badge variant="secondary" className="text-xs">
                              <Settings className="h-3 w-3 mr-1" />
                              System Config
                            </Badge>
                          )}
                          <Badge variant="outline" className="text-xs">
                            Max: {user.permissions.maxModelSize}
                          </Badge>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleEditUser(user)}
                        >
                          <Edit className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleLockUser(user.id)}
                          className={user.status === 'locked' ? 'text-green-600' : 'text-yellow-600'}
                        >
                          {user.status === 'locked' ? <Unlock className="h-3 w-3 mr-1" /> : <Lock className="h-3 w-3 mr-1" />}
                          {user.status === 'locked' ? 'Unlock' : 'Lock'}
                        </Button>
                        {user.role !== 'admin' && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleDeleteUser(user.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            Delete
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles">
          <div className="grid gap-4">
            {roles.map((role) => (
              <Card key={role.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center space-x-2">
                        {getRoleIcon(role.name.toLowerCase())}
                        <span>{role.name}</span>
                        {role.isBuiltIn && (
                          <Badge variant="outline" className="text-xs">Built-in</Badge>
                        )}
                      </CardTitle>
                      <CardDescription>{role.description}</CardDescription>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{role.userCount} users</p>
                      <p className="text-xs text-muted-foreground">assigned</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Permissions</p>
                        <div className="space-y-1">
                          {role.permissions.canDownloadModels && <p className="text-xs text-muted-foreground">• Download Models</p>}
                          {role.permissions.canManageUsers && <p className="text-xs text-muted-foreground">• Manage Users</p>}
                          {role.permissions.canViewLogs && <p className="text-xs text-muted-foreground">• View Logs</p>}
                          {role.permissions.canConfigureSystem && <p className="text-xs text-muted-foreground">• System Config</p>}
                          {role.permissions.canAccessAPI && <p className="text-xs text-muted-foreground">• API Access</p>}
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Model Limits</p>
                        <p className="text-xs text-muted-foreground">Max Size: {role.permissions.maxModelSize}</p>
                        <p className="text-xs text-muted-foreground">Storage: {formatBytes(role.permissions.storageQuota)}</p>
                      </div>
                      
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Categories</p>
                        <div className="flex flex-wrap gap-1">
                          {role.permissions.allowedCategories.map(cat => (
                            <Badge key={cat} variant="secondary" className="text-xs">{cat}</Badge>
                          ))}
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Actions</p>
                        <div className="flex items-center space-x-2">
                          {!role.isBuiltIn && (
                            <>
                              <Button variant="outline" size="sm">
                                <Edit className="h-3 w-3 mr-1" />
                                Edit
                              </Button>
                              <Button variant="outline" size="sm" className="text-red-600">
                                <Trash2 className="h-3 w-3 mr-1" />
                                Delete
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create User Dialog - Placeholder */}
      <Dialog open={isCreateUserOpen} onOpenChange={setIsCreateUserOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New User</DialogTitle>
            <DialogDescription>
              Add a new user to the system with specified permissions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" placeholder="Enter username" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="Enter email" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input id="fullName" placeholder="Enter full name" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map(role => (
                    <SelectItem key={role.id} value={role.id}>{role.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateUserOpen(false)}>Cancel</Button>
            <Button onClick={() => setIsCreateUserOpen(false)}>Create User</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}