'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Activity,
  Brain,
  Download,
  Users,
  Settings,
  Monitor,
  HardDrive,
  Cpu,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Shield
} from 'lucide-react';

interface SystemStats {
  cpu: { usage: number; cores: number; };
  memory: { used: number; total: number; };
  gpu: { usage: number; memory: { used: number; total: number; }; temp: number; };
  storage: { models: number; logs: number; available: number; total: number; };
}

interface ModelStatus {
  loaded: Array<{
    id: string;
    name: string;
    memory: number;
    tokensPerSecond: number;
    activeQueries: number;
  }>;
  downloading: Array<{
    id: string;
    name: string;
    progress: number;
    speed: string;
    eta: string;
  }>;
}

interface ActivityMetrics {
  queriesPerMinute: number;
  avgResponseTime: number;
  errorRate: number;
  activeUsers: number;
  totalQueries: number;
}

export function ApplianceDashboard() {
  // Mock data - replace with actual API calls
  const [systemStats] = React.useState<SystemStats>({
    cpu: { usage: 23, cores: 16 },
    memory: { used: 12.4, total: 64 },
    gpu: { usage: 45, memory: { used: 8.2, total: 24 }, temp: 67 },
    storage: { models: 127, logs: 45, available: 373, total: 500 }
  });

  const [modelStatus] = React.useState<ModelStatus>({
    loaded: [
      {
        id: 'security-llama-7b',
        name: 'Security Llama 7B',
        memory: 4.2,
        tokensPerSecond: 35,
        activeQueries: 3
      },
      {
        id: 'threat-hunter-13b',
        name: 'Threat Hunter 13B',
        memory: 8.5,
        tokensPerSecond: 28,
        activeQueries: 1
      }
    ],
    downloading: [
      {
        id: 'code-security-7b',
        name: 'Code Security 7B',
        progress: 67,
        speed: '45 MB/s',
        eta: '12 min'
      }
    ]
  });

  const [activityMetrics] = React.useState<ActivityMetrics>({
    queriesPerMinute: 45,
    avgResponseTime: 1.2,
    errorRate: 0.2,
    activeUsers: 12,
    totalQueries: 2847
  });

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getUsageColor = (usage: number) => {
    if (usage < 50) return 'text-green-600';
    if (usage < 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = (usage: number) => {
    if (usage < 50) return 'bg-green-500';
    if (usage < 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security AI Appliance</h1>
          <p className="text-muted-foreground">
            Standalone security analysis platform with embedded AI models
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="online" className="flex items-center space-x-1">
            <CheckCircle className="h-3 w-3" />
            <span>System Healthy</span>
          </Badge>
          <Badge variant="outline" className="flex items-center space-x-1">
            <Shield className="h-3 w-3" />
            <span>Security Active</span>
          </Badge>
        </div>
      </div>

      {/* System Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.cpu.usage}%</div>
            <Progress 
              value={systemStats.cpu.usage} 
              className="mt-2"
              indicatorClassName={getProgressColor(systemStats.cpu.usage)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {systemStats.cpu.cores} cores available
            </p>
          </CardContent>
        </Card>

        {/* Memory Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory</CardTitle>
            <Monitor className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((systemStats.memory.used / systemStats.memory.total) * 100).toFixed(1)}%
            </div>
            <Progress 
              value={(systemStats.memory.used / systemStats.memory.total) * 100}
              className="mt-2"
              indicatorClassName={getProgressColor((systemStats.memory.used / systemStats.memory.total) * 100)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {systemStats.memory.used} GB / {systemStats.memory.total} GB
            </p>
          </CardContent>
        </Card>

        {/* GPU Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">GPU</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.gpu.usage}%</div>
            <Progress 
              value={systemStats.gpu.usage}
              className="mt-2"
              indicatorClassName={getProgressColor(systemStats.gpu.usage)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {systemStats.gpu.memory.used} GB / {systemStats.gpu.memory.total} GB • {systemStats.gpu.temp}°C
            </p>
          </CardContent>
        </Card>

        {/* Storage Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(((systemStats.storage.total - systemStats.storage.available) / systemStats.storage.total) * 100).toFixed(1)}%
            </div>
            <Progress 
              value={((systemStats.storage.total - systemStats.storage.available) / systemStats.storage.total) * 100}
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Models: {systemStats.storage.models} GB • Available: {systemStats.storage.available} GB
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="models" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="models" className="flex items-center space-x-2">
            <Brain className="h-4 w-4" />
            <span>Models</span>
          </TabsTrigger>
          <TabsTrigger value="downloads" className="flex items-center space-x-2">
            <Download className="h-4 w-4" />
            <span>Downloads</span>
          </TabsTrigger>
          <TabsTrigger value="activity" className="flex items-center space-x-2">
            <Activity className="h-4 w-4" />
            <span>Activity</span>
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center space-x-2">
            <Users className="h-4 w-4" />
            <span>Users</span>
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </TabsTrigger>
        </TabsList>

        {/* Models Tab */}
        <TabsContent value="models">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Loaded Models */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Brain className="h-5 w-5" />
                  <span>Active Models</span>
                  <Badge variant="secondary">{modelStatus.loaded.length}</Badge>
                </CardTitle>
                <CardDescription>
                  Currently loaded and running models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {modelStatus.loaded.map((model) => (
                    <div key={model.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">{model.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {model.memory} GB • {model.tokensPerSecond} tok/s
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="online" className="mb-1">
                          {model.activeQueries} queries
                        </Badge>
                        <div className="text-xs text-muted-foreground">
                          Running
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Model Repository Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <HardDrive className="h-5 w-5" />
                  <span>Model Repository</span>
                </CardTitle>
                <CardDescription>
                  Local model storage and management
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Models</span>
                    <span className="font-medium">15</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Security Models</span>
                    <span className="font-medium">8</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">General Models</span>
                    <span className="font-medium">7</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Storage Used</span>
                    <span className="font-medium">{systemStats.storage.models} GB</span>
                  </div>
                  <Button className="w-full mt-4">
                    Browse HuggingFace Models
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Downloads Tab */}
        <TabsContent value="downloads">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Download className="h-5 w-5" />
                <span>Download Manager</span>
                <Badge variant="secondary">{modelStatus.downloading.length}</Badge>
              </CardTitle>
              <CardDescription>
                Active downloads and queue management
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {modelStatus.downloading.map((download) => (
                  <div key={download.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium">{download.name}</div>
                      <div className="flex items-center space-x-2">
                        <Button size="sm" variant="outline">Pause</Button>
                        <Button size="sm" variant="outline">Cancel</Button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>{download.progress}% complete</span>
                        <span>{download.speed} • ETA {download.eta}</span>
                      </div>
                      <Progress value={download.progress} />
                    </div>
                  </div>
                ))}
                
                {modelStatus.downloading.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Download className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No active downloads</p>
                    <Button className="mt-4">Browse Models</Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activity Tab */}
        <TabsContent value="activity">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Performance Metrics</span>
                </CardTitle>
                <CardDescription>
                  Real-time system performance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Queries/Minute</span>
                    <span className="font-medium">{activityMetrics.queriesPerMinute}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Response Time</span>
                    <span className="font-medium">{activityMetrics.avgResponseTime}s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Error Rate</span>
                    <span className="font-medium text-green-600">{activityMetrics.errorRate}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Active Users</span>
                    <span className="font-medium">{activityMetrics.activeUsers}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Queries</span>
                    <span className="font-medium">{activityMetrics.totalQueries.toLocaleString()}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span>System Alerts</span>
                </CardTitle>
                <CardDescription>
                  Recent alerts and notifications
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-start space-x-3 p-2 bg-yellow-50 rounded">
                    <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
                    <div className="text-sm">
                      <div className="font-medium">GPU Temperature High</div>
                      <div className="text-muted-foreground">Temperature: 82°C</div>
                      <div className="text-xs text-muted-foreground">2 minutes ago</div>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3 p-2 bg-green-50 rounded">
                    <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                    <div className="text-sm">
                      <div className="font-medium">Model Download Completed</div>
                      <div className="text-muted-foreground">Security Llama 13B ready</div>
                      <div className="text-xs text-muted-foreground">15 minutes ago</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Placeholder tabs for Users and Settings */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>
                Manage users, roles, and permissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">User management interface coming soon...</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Appliance Settings</CardTitle>
              <CardDescription>
                System configuration and preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Settings interface coming soon...</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}