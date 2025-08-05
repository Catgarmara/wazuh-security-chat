'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Activity, 
  Shield, 
  AlertTriangle, 
  Server, 
  Users, 
  Zap,
  TrendingUp,
  Clock,
  Database,
  Cpu
} from 'lucide-react';

export function Dashboard() {
  // Mock data - this would come from API calls
  const siemStatus = {
    wazuh_manager: {
      status: 'online' as const,
      version: '4.12.0',
      agents_connected: 245,
      agents_total: 250,
      rules_loaded: 1250,
      last_restart: '2024-01-15T10:30:00Z'
    },
    threat_detection: {
      active_alerts: 12,
      critical_alerts: 2,
      high_alerts: 5,
      medium_alerts: 3,
      low_alerts: 2
    },
    performance_metrics: {
      average_processing_time: 0.85,
      events_per_second: 1250,
      rule_matching_rate: 98.5
    }
  };

  const systemStatus = {
    status: 'healthy' as const,
    services: {
      api: { status: 'healthy' as const, response_time: 45 },
      database: { status: 'healthy' as const, response_time: 12 },
      redis: { status: 'healthy' as const, response_time: 3 },
      ai_service: { status: 'healthy' as const, response_time: 120 },
      websocket: { status: 'healthy' as const, response_time: 8 }
    },
    resources: {
      cpu_usage: 34,
      memory_usage: 67,
      disk_usage: 45,
      gpu_usage: 78,
      active_connections: 23,
      loaded_models: 2
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'healthy':
        return 'online';
      case 'degraded':
        return 'degraded';
      case 'offline':
      case 'unhealthy':
        return 'offline';
      default:
        return 'outline';
    }
  };

  const getSeverityColor = (count: number, severity: string) => {
    if (count === 0) return 'outline';
    switch (severity) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
      default:
        return 'info';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Operations Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time SIEM status and system monitoring
          </p>
        </div>
        <Badge variant={getStatusColor(systemStatus.status)} className="text-sm">
          System {systemStatus.status}
        </Badge>
      </div>

      {/* SIEM Status Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Wazuh Manager</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold mb-1">
              <Badge variant={getStatusColor(siemStatus.wazuh_manager.status)}>
                {siemStatus.wazuh_manager.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              v{siemStatus.wazuh_manager.version} • {siemStatus.wazuh_manager.rules_loaded} rules
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Agents</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {siemStatus.wazuh_manager.agents_connected}
            </div>
            <p className="text-xs text-muted-foreground">
              of {siemStatus.wazuh_manager.agents_total} total agents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {siemStatus.threat_detection.active_alerts}
            </div>
            <p className="text-xs text-muted-foreground">
              {siemStatus.threat_detection.critical_alerts} critical, {siemStatus.threat_detection.high_alerts} high
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Events/Second</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {siemStatus.performance_metrics.events_per_second.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              {siemStatus.performance_metrics.rule_matching_rate}% match rate
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alert Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Security Alerts by Severity</CardTitle>
          <CardDescription>Current active alerts requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            {[
              { label: 'Critical', count: siemStatus.threat_detection.critical_alerts, severity: 'critical' },
              { label: 'High', count: siemStatus.threat_detection.high_alerts, severity: 'high' },
              { label: 'Medium', count: siemStatus.threat_detection.medium_alerts, severity: 'medium' },
              { label: 'Low', count: siemStatus.threat_detection.low_alerts, severity: 'low' },
              { label: 'Info', count: 0, severity: 'info' },
            ].map((alert) => (
              <div key={alert.label} className="flex flex-col items-center p-4 border rounded-lg">
                <Badge variant={getSeverityColor(alert.count, alert.severity)} className="mb-2">
                  {alert.label}
                </Badge>
                <div className="text-2xl font-bold">{alert.count}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* System Resources */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>System Resources</CardTitle>
            <CardDescription>Current resource utilization</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: 'CPU Usage', value: systemStatus.resources.cpu_usage, icon: Cpu },
              { label: 'Memory Usage', value: systemStatus.resources.memory_usage, icon: Database },
              { label: 'Disk Usage', value: systemStatus.resources.disk_usage, icon: Server },
              { label: 'GPU Usage', value: systemStatus.resources.gpu_usage, icon: Zap },
            ].map((resource) => (
              <div key={resource.label} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <resource.icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{resource.label}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-20 bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${resource.value}%` }}
                    />
                  </div>
                  <span className="text-sm font-mono w-12 text-right">{resource.value}%</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Service Health</CardTitle>
            <CardDescription>Application service status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(systemStatus.services).map(([service, health]) => (
              <div key={service} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm capitalize">{service.replace('_', ' ')}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusColor(health.status)} className="text-xs">
                    {health.status}
                  </Badge>
                  <span className="text-sm font-mono w-12 text-right">{health.response_time}ms</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* AI Models Status */}
      <Card>
        <CardHeader>
          <CardTitle>AI Models</CardTitle>
          <CardDescription>Currently loaded AI models and performance</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 rounded-full bg-green-500"></div>
                <span className="text-sm">Llama 3 8B</span>
                <Badge variant="online" className="text-xs">Loaded</Badge>
              </div>
              <div className="text-sm text-muted-foreground">
                45 tok/s • 4.7GB memory
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              {systemStatus.resources.active_connections} active connections
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}