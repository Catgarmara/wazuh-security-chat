'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Shield, 
  Server, 
  Activity, 
  RefreshCw, 
  Settings, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Cpu,
  HardDrive
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface WazuhManagerStatusProps {
  className?: string;
  onRefresh?: () => void;
  onConfigure?: () => void;
}

interface WazuhManagerData {
  status: 'online' | 'offline' | 'degraded';
  version: string;
  uptime: string;
  last_restart: string;
  cluster_mode: boolean;
  cluster_nodes: number;
  configuration: {
    rules_loaded: number;
    decoders_loaded: number;
    cdb_lists: number;
    log_level: string;
  };
  performance: {
    events_received: number;
    events_processed: number;
    events_dropped: number;
    average_processing_time: number;
    queue_usage: number;
  };
  modules: {
    vulnerability_detection: boolean;
    osquery: boolean;
    syscollector: boolean;
    sca: boolean;
    rootcheck: boolean;
    file_integrity: boolean;
    log_analysis: boolean;
    active_response: boolean;
  };
}

export function WazuhManagerStatus({ 
  className, 
  onRefresh, 
  onConfigure 
}: WazuhManagerStatusProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [lastUpdate, setLastUpdate] = React.useState(new Date());

  // Mock data - replace with actual API integration
  const managerData: WazuhManagerData = {
    status: 'online',
    version: '4.12.0',
    uptime: '15 days, 7 hours, 23 minutes',
    last_restart: '2024-01-15T10:30:00Z',
    cluster_mode: true,
    cluster_nodes: 3,
    configuration: {
      rules_loaded: 1847,
      decoders_loaded: 425,
      cdb_lists: 67,
      log_level: 'info'
    },
    performance: {
      events_received: 1250000,
      events_processed: 1248750,
      events_dropped: 1250,
      average_processing_time: 0.85,
      queue_usage: 23
    },
    modules: {
      vulnerability_detection: true,
      osquery: true,
      syscollector: true,
      sca: true,
      rootcheck: true,
      file_integrity: true,
      log_analysis: true,
      active_response: true
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setLastUpdate(new Date());
      onRefresh?.();
    } finally {
      setIsRefreshing(false);
    }
  };

  const getStatusIcon = () => {
    switch (managerData.status) {
      case 'online':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'offline':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
    }
  };

  const getStatusBadge = () => {
    switch (managerData.status) {
      case 'online':
        return 'online';
      case 'degraded':
        return 'degraded';
      case 'offline':
        return 'offline';
    }
  };

  const activeModules = Object.entries(managerData.modules).filter(([_, active]) => active);
  const inactiveModules = Object.entries(managerData.modules).filter(([_, active]) => !active);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="h-6 w-6 text-primary" />
              <div>
                <CardTitle>Wazuh Manager</CardTitle>
                <CardDescription>Central security management platform</CardDescription>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={getStatusBadge()} className="flex items-center space-x-1">
                {getStatusIcon()}
                <span className="capitalize">{managerData.status}</span>
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="h-8 w-8 p-0"
              >
                <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>
              {onConfigure && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onConfigure}
                  className="h-8 w-8 p-0"
                >
                  <Settings className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Version</div>
              <div className="font-semibold">{managerData.version}</div>
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Uptime</div>
              <div className="font-semibold">{managerData.uptime}</div>
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Cluster</div>
              <div className="font-semibold">
                {managerData.cluster_mode ? `${managerData.cluster_nodes} nodes` : 'Standalone'}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Last Restart</div>
              <div className="font-semibold">
                {formatDistanceToNow(new Date(managerData.last_restart), { addSuffix: true })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <span>Configuration Status</span>
          </CardTitle>
          <CardDescription>Loaded security rules, decoders, and lists</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-md">
                <Shield className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Security Rules</div>
                <div className="font-semibold">{managerData.configuration.rules_loaded.toLocaleString()}</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-md">
                <Cpu className="h-4 w-4 text-green-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Decoders</div>
                <div className="font-semibold">{managerData.configuration.decoders_loaded.toLocaleString()}</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-md">
                <HardDrive className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">CDB Lists</div>
                <div className="font-semibold">{managerData.configuration.cdb_lists}</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-md">
                <Activity className="h-4 w-4 text-orange-600" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Log Level</div>
                <div className="font-semibold capitalize">{managerData.configuration.log_level}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Performance Metrics</span>
          </CardTitle>
          <CardDescription>Real-time processing performance and statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Events Received</span>
                  <span className="font-mono text-sm">{managerData.performance.events_received.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Events Processed</span>
                  <span className="font-mono text-sm">{managerData.performance.events_processed.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Events Dropped</span>
                  <span className="font-mono text-sm text-red-500">{managerData.performance.events_dropped.toLocaleString()}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Processing Time</span>
                  <span className="font-mono text-sm">{managerData.performance.average_processing_time}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Queue Usage</span>
                  <span className="font-mono text-sm">{managerData.performance.queue_usage}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Success Rate</span>
                  <span className="font-mono text-sm text-green-500">
                    {((managerData.performance.events_processed / managerData.performance.events_received) * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground mb-2">Queue Usage</div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      managerData.performance.queue_usage > 80 ? 'bg-red-500' :
                      managerData.performance.queue_usage > 60 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${managerData.performance.queue_usage}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {managerData.performance.queue_usage}% capacity
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Modules */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Server className="h-5 w-5" />
            <span>Security Modules</span>
          </CardTitle>
          <CardDescription>Enabled security detection and analysis modules</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-muted-foreground mb-2">Active Modules ({activeModules.length})</div>
              <div className="flex flex-wrap gap-2">
                {activeModules.map(([module, _]) => (
                  <Badge key={module} variant="online" className="text-xs">
                    {module.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Badge>
                ))}
              </div>
            </div>
            {inactiveModules.length > 0 && (
              <div>
                <div className="text-sm text-muted-foreground mb-2">Inactive Modules ({inactiveModules.length})</div>
                <div className="flex flex-wrap gap-2">
                  {inactiveModules.map(([module, _]) => (
                    <Badge key={module} variant="outline" className="text-xs">
                      {module.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Last Update Info */}
      <div className="text-xs text-muted-foreground text-center">
        <Clock className="h-3 w-3 inline mr-1" />
        Last updated: {lastUpdate.toLocaleTimeString()}
      </div>
    </div>
  );
}