'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Shield, 
  Activity, 
  AlertTriangle, 
  Users, 
  Globe, 
  FileText,
  RefreshCw,
  Settings,
  Filter,
  Bell,
  Eye,
  TrendingUp,
  Clock,
  Zap
} from 'lucide-react';

// Import SIEM components
import { WazuhManagerStatus } from './wazuh-manager-status';
import { AgentConnectivity } from './agent-connectivity';
import { SecurityAlertsDashboard } from './security-alerts-dashboard';
import { ThreatIntelligenceFeed } from './threat-intelligence-feed';
import { LogAnalysisVisualization } from './log-analysis-visualization';

interface SIEMMonitoringDashboardProps {
  className?: string;
}

interface SIEMOverviewStats {
  manager_status: 'online' | 'offline' | 'degraded';
  total_agents: number;
  active_agents: number;
  total_alerts: number;
  critical_alerts: number;
  threat_indicators: number;
  active_threats: number;
  log_events_24h: number;
  security_score: number;
}

export function SIEMMonitoringDashboard({ className }: SIEMMonitoringDashboardProps) {
  const [activeTab, setActiveTab] = React.useState('overview');
  const [lastUpdate, setLastUpdate] = React.useState(new Date());
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [alertsEnabled, setAlertsEnabled] = React.useState(true);

  // Mock overview data - replace with actual API integration
  const overviewStats: SIEMOverviewStats = {
    manager_status: 'online',
    total_agents: 250,
    active_agents: 245,
    total_alerts: 47,
    critical_alerts: 3,
    threat_indicators: 1247,
    active_threats: 8,
    log_events_24h: 15630,
    security_score: 87
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
      setLastUpdate(new Date());
    } finally {
      setIsRefreshing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online':
        return 'online';
      case 'degraded':
        return 'degraded';
      case 'offline':
        return 'offline';
      default:
        return 'outline';
    }
  };

  const getSecurityScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getSecurityScoreBadge = (score: number) => {
    if (score >= 90) return 'online';
    if (score >= 75) return 'medium';
    if (score >= 60) return 'high';
    return 'critical';
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Operations Center</h1>
          <p className="text-muted-foreground">
            Comprehensive SIEM monitoring and threat detection platform
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant={alertsEnabled ? "default" : "outline"}
            size="sm"
            onClick={() => setAlertsEnabled(!alertsEnabled)}
            className="flex items-center space-x-2"
          >
            <Bell className={`h-4 w-4 ${alertsEnabled ? 'text-white' : 'text-muted-foreground'}`} />
            <span>Alerts {alertsEnabled ? 'On' : 'Off'}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Security Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{overviewStats.security_score}</div>
                <div className="text-sm text-muted-foreground">Security Score</div>
              </div>
              <div className="flex flex-col items-end space-y-1">
                <Badge variant={getSecurityScoreBadge(overviewStats.security_score)} className="text-xs">
                  {overviewStats.security_score >= 90 ? 'Excellent' : 
                   overviewStats.security_score >= 75 ? 'Good' :
                   overviewStats.security_score >= 60 ? 'Fair' : 'Poor'}
                </Badge>
                <div className={`text-xs ${getSecurityScoreColor(overviewStats.security_score)}`}>
                  <TrendingUp className="h-3 w-3 inline mr-1" />
                  +2.3%
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{overviewStats.total_alerts}</div>
                <div className="text-sm text-muted-foreground">Active Alerts</div>
              </div>
              <div className="flex flex-col items-end space-y-1">
                <Badge variant={overviewStats.critical_alerts > 0 ? "critical" : "online"} className="text-xs">
                  {overviewStats.critical_alerts} Critical
                </Badge>
                <AlertTriangle className="h-5 w-5 text-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{overviewStats.active_agents}</div>
                <div className="text-sm text-muted-foreground">Active Agents</div>
              </div>
              <div className="flex flex-col items-end space-y-1">
                <Badge variant="online" className="text-xs">
                  {Math.round((overviewStats.active_agents / overviewStats.total_agents) * 100)}% Online
                </Badge>
                <Users className="h-5 w-5 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{overviewStats.active_threats}</div>
                <div className="text-sm text-muted-foreground">Active Threats</div>
              </div>
              <div className="flex flex-col items-end space-y-1">
                <Badge variant={overviewStats.active_threats > 5 ? "critical" : "high"} className="text-xs">
                  {overviewStats.threat_indicators} Indicators
                </Badge>
                <Globe className="h-5 w-5 text-purple-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main SIEM Dashboard Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList className="grid w-full max-w-md grid-cols-5">
            <TabsTrigger value="overview" className="text-xs">
              <Activity className="h-4 w-4 mr-1" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="alerts" className="text-xs">
              <AlertTriangle className="h-4 w-4 mr-1" />
              Alerts
            </TabsTrigger>
            <TabsTrigger value="agents" className="text-xs">
              <Users className="h-4 w-4 mr-1" />
              Agents
            </TabsTrigger>
            <TabsTrigger value="threats" className="text-xs">
              <Globe className="h-4 w-4 mr-1" />
              Threats
            </TabsTrigger>
            <TabsTrigger value="logs" className="text-xs">
              <FileText className="h-4 w-4 mr-1" />
              Logs
            </TabsTrigger>
          </TabsList>
          <div className="text-sm text-muted-foreground flex items-center space-x-1">
            <Clock className="h-3 w-3" />
            <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
          </div>
        </div>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Manager Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>Wazuh Manager Status</span>
                </CardTitle>
                <CardDescription>Real-time manager health and performance</CardDescription>
              </CardHeader>
              <CardContent>
                <WazuhManagerStatus className="border-0 shadow-none p-0" />
              </CardContent>
            </Card>

            {/* Recent Alerts Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span>Recent Security Alerts</span>
                </CardTitle>
                <CardDescription>Latest security events requiring attention</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      <div>
                        <div className="font-medium text-sm">Suspicious process execution</div>
                        <div className="text-xs text-muted-foreground">workstation-05 • 2 min ago</div>
                      </div>
                    </div>
                    <Badge variant="critical" className="text-xs">Critical</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                      <div>
                        <div className="font-medium text-sm">Multiple login failures</div>
                        <div className="text-xs text-muted-foreground">web-server-01 • 5 min ago</div>
                      </div>
                    </div>
                    <Badge variant="high" className="text-xs">High</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <AlertTriangle className="h-4 w-4 text-blue-500" />
                      <div>
                        <div className="font-medium text-sm">File integrity violation</div>
                        <div className="text-xs text-muted-foreground">db-server-01 • 8 min ago</div>
                      </div>
                    </div>
                    <Badge variant="medium" className="text-xs">Medium</Badge>
                  </div>
                  <div className="text-center pt-2">
                    <Button variant="outline" size="sm" onClick={() => setActiveTab('alerts')}>
                      View All Alerts
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Agent Status Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Users className="h-5 w-5" />
                <span>Agent Connectivity Overview</span>
              </CardTitle>
              <CardDescription>Real-time agent status and network health</CardDescription>
            </CardHeader>
            <CardContent>
              <AgentConnectivity className="border-0 shadow-none p-0" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts">
          <SecurityAlertsDashboard />
        </TabsContent>

        <TabsContent value="agents">
          <AgentConnectivity />
        </TabsContent>

        <TabsContent value="threats">
          <ThreatIntelligenceFeed />
        </TabsContent>

        <TabsContent value="logs">
          <LogAnalysisVisualization />
        </TabsContent>
      </Tabs>

      {/* Status Bar */}
      <div className="flex items-center justify-between p-4 bg-accent/50 rounded-lg">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${
              overviewStats.manager_status === 'online' ? 'bg-green-500' :
              overviewStats.manager_status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
            }`}></div>
            <span className="text-sm">Wazuh Manager: {overviewStats.manager_status}</span>
          </div>
          <div className="text-sm text-muted-foreground">
            {overviewStats.log_events_24h.toLocaleString()} events processed (24h)
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-muted-foreground">
            Security Score: <span className={`font-medium ${getSecurityScoreColor(overviewStats.security_score)}`}>
              {overviewStats.security_score}/100
            </span>
          </div>
          <Badge variant={alertsEnabled ? "online" : "outline"} className="text-xs">
            {alertsEnabled ? 'Real-time Monitoring Active' : 'Monitoring Paused'}
          </Badge>
        </div>
      </div>
    </div>
  );
}