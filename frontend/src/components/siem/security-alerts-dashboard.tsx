'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  AlertTriangle, 
  Shield, 
  Search, 
  Filter, 
  RefreshCw, 
  Clock,
  Eye,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
  TrendingUp,
  TrendingDown,
  Activity,
  Calendar,
  MapPin,
  User,
  FileText,
  Hash
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface SecurityAlertsDashboardProps {
  className?: string;
  onRefresh?: () => void;
}

type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
type AlertStatus = 'open' | 'acknowledged' | 'resolved' | 'false_positive';

interface SecurityAlert {
  id: string;
  rule_id: number;
  rule_description: string;
  severity: AlertSeverity;
  status: AlertStatus;
  timestamp: string;
  agent_id?: string;
  agent_name?: string;
  source_ip?: string;
  destination_ip?: string;
  user?: string;
  process?: string;
  file_path?: string;
  command?: string;
  category: string;
  mitre_technique?: string;
  mitre_tactic?: string;
  event_count: number;
  raw_log?: string;
}

interface AlertStats {
  total: number;
  open: number;
  acknowledged: number;
  resolved: number;
  false_positive: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  trends: {
    last_hour: number;
    last_24h: number;
    last_7d: number;
  };
}

export function SecurityAlertsDashboard({ className, onRefresh }: SecurityAlertsDashboardProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [lastUpdate, setLastUpdate] = React.useState(new Date());

  // Mock alert data - replace with actual API integration
  const alerts: SecurityAlert[] = [
    {
      id: 'alert-001',
      rule_id: 5712,
      rule_description: 'Multiple authentication failures from same source',
      severity: 'high',
      status: 'open',
      timestamp: '2024-01-20T14:45:00Z',
      agent_id: '001',
      agent_name: 'web-server-01',
      source_ip: '192.168.1.100',
      user: 'admin',
      category: 'Authentication',
      mitre_technique: 'T1110',
      mitre_tactic: 'Credential Access',
      event_count: 15
    },
    {
      id: 'alert-002',
      rule_id: 31103,
      rule_description: 'Suspicious process execution detected',
      severity: 'critical',
      status: 'acknowledged',
      timestamp: '2024-01-20T14:30:00Z',
      agent_id: '003',
      agent_name: 'workstation-05',
      source_ip: '192.168.1.205',
      user: 'user01',
      process: 'powershell.exe',
      command: 'powershell -EncodedCommand <base64>',
      category: 'Malware',
      mitre_technique: 'T1059.001',
      mitre_tactic: 'Execution',
      event_count: 1
    },
    {
      id: 'alert-003',
      rule_id: 40111,
      rule_description: 'File integrity monitoring: critical file modified',
      severity: 'medium',
      status: 'open',
      timestamp: '2024-01-20T14:15:00Z',
      agent_id: '002',
      agent_name: 'db-server-01',
      source_ip: '192.168.1.101',
      file_path: '/etc/passwd',
      user: 'root',
      category: 'Integrity Monitoring',
      mitre_technique: 'T1078',
      mitre_tactic: 'Defense Evasion',
      event_count: 3
    },
    {
      id: 'alert-004',
      rule_id: 5403,
      rule_description: 'Privilege escalation attempt detected',
      severity: 'high',
      status: 'resolved',
      timestamp: '2024-01-20T13:45:00Z',
      agent_id: '001',
      agent_name: 'web-server-01',
      source_ip: '192.168.1.100',
      user: 'www-data',
      process: 'sudo',
      category: 'Privilege Escalation',
      mitre_technique: 'T1548.003',
      mitre_tactic: 'Privilege Escalation',
      event_count: 2
    },
    {
      id: 'alert-005',
      rule_id: 31151,
      rule_description: 'Suspicious network connection to known malicious IP',
      severity: 'critical',
      status: 'open',
      timestamp: '2024-01-20T13:30:00Z',
      agent_id: '003',
      agent_name: 'workstation-05',
      source_ip: '192.168.1.205',
      destination_ip: '185.220.100.240',
      category: 'Network Activity',
      mitre_technique: 'T1071.001',
      mitre_tactic: 'Command and Control',
      event_count: 8
    },
    {
      id: 'alert-006',
      rule_id: 18108,
      rule_description: 'Vulnerability scanner activity detected',
      severity: 'low',
      status: 'false_positive',
      timestamp: '2024-01-20T12:15:00Z',
      agent_id: '001',
      agent_name: 'web-server-01',
      source_ip: '192.168.1.100',
      category: 'Web Attack',
      mitre_technique: 'T1595.002',
      mitre_tactic: 'Reconnaissance',
      event_count: 45
    }
  ];

  const alertStats: AlertStats = React.useMemo(() => {
    const total = alerts.length;
    const open = alerts.filter(a => a.status === 'open').length;
    const acknowledged = alerts.filter(a => a.status === 'acknowledged').length;
    const resolved = alerts.filter(a => a.status === 'resolved').length;
    const false_positive = alerts.filter(a => a.status === 'false_positive').length;
    
    const by_severity = {
      critical: alerts.filter(a => a.severity === 'critical').length,
      high: alerts.filter(a => a.severity === 'high').length,
      medium: alerts.filter(a => a.severity === 'medium').length,
      low: alerts.filter(a => a.severity === 'low').length,
      info: alerts.filter(a => a.severity === 'info').length,
    };

    return {
      total,
      open,
      acknowledged,
      resolved,
      false_positive,
      by_severity,
      trends: {
        last_hour: 8,
        last_24h: 23,
        last_7d: 145
      }
    };
  }, [alerts]);

  const filteredAlerts = React.useMemo(() => {
    return alerts.filter(alert => {
      const matchesSearch = !searchQuery || 
        alert.rule_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.agent_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.source_ip?.includes(searchQuery) ||
        alert.user?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesSeverity = severityFilter === 'all' || alert.severity === severityFilter;
      const matchesStatus = statusFilter === 'all' || alert.status === statusFilter;
      
      return matchesSearch && matchesSeverity && matchesStatus;
    });
  }, [alerts, searchQuery, severityFilter, statusFilter]);

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

  const getSeverityIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'high':
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case 'medium':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'low':
        return <AlertCircle className="h-4 w-4 text-blue-500" />;
      case 'info':
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusIcon = (status: AlertStatus) => {
    switch (status) {
      case 'open':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'acknowledged':
        return <Eye className="h-4 w-4 text-yellow-500" />;
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'false_positive':
        return <XCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityBadge = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
      case 'info':
        return 'info';
    }
  };

  const getStatusBadge = (status: AlertStatus) => {
    switch (status) {
      case 'open':
        return 'offline';
      case 'acknowledged':
        return 'degraded';
      case 'resolved':
        return 'online';
      case 'false_positive':
        return 'outline';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Alert Statistics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{alertStats.total}</div>
                <div className="text-sm text-muted-foreground">Total Alerts</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <XCircle className="h-5 w-5 text-red-600" />
              <div>
                <div className="text-2xl font-bold text-red-600">{alertStats.open}</div>
                <div className="text-sm text-muted-foreground">Open</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Eye className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="text-2xl font-bold text-yellow-600">{alertStats.acknowledged}</div>
                <div className="text-sm text-muted-foreground">Acknowledged</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-2xl font-bold text-green-600">{alertStats.resolved}</div>
                <div className="text-sm text-muted-foreground">Resolved</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{alertStats.trends.last_24h}</div>
                <div className="text-sm text-muted-foreground">Last 24h</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Severity Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Alert Severity Distribution</span>
          </CardTitle>
          <CardDescription>Current alerts by severity level</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            {[
              { label: 'Critical', count: alertStats.by_severity.critical, severity: 'critical' as const },
              { label: 'High', count: alertStats.by_severity.high, severity: 'high' as const },
              { label: 'Medium', count: alertStats.by_severity.medium, severity: 'medium' as const },
              { label: 'Low', count: alertStats.by_severity.low, severity: 'low' as const },
              { label: 'Info', count: alertStats.by_severity.info, severity: 'info' as const },
            ].map((item) => (
              <div key={item.label} className="flex flex-col items-center p-4 border rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  {getSeverityIcon(item.severity)}
                  <Badge variant={getSeverityBadge(item.severity)} className="text-xs">
                    {item.label}
                  </Badge>
                </div>
                <div className="text-2xl font-bold">{item.count}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Alert List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <AlertTriangle className="h-5 w-5" />
                <span>Security Alerts</span>
              </CardTitle>
              <CardDescription>Real-time security alerts and incidents</CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filter Controls */}
          <div className="flex items-center space-x-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search alerts by description, category, agent, IP, or user..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="all">All Status</option>
                <option value="open">Open</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="resolved">Resolved</option>
                <option value="false_positive">False Positive</option>
              </select>
            </div>
          </div>

          {/* Alert Table */}
          <div className="space-y-2">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start space-x-3">
                    <div className="flex flex-col items-center space-y-1">
                      {getSeverityIcon(alert.severity)}
                      {getStatusIcon(alert.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <Badge variant={getSeverityBadge(alert.severity)} className="text-xs">
                          {alert.severity.toUpperCase()}
                        </Badge>
                        <Badge variant={getStatusBadge(alert.status)} className="text-xs">
                          {alert.status.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {alert.category}
                        </Badge>
                      </div>
                      <h4 className="font-semibold text-sm mb-1">{alert.rule_description}</h4>
                      <div className="text-xs text-muted-foreground">
                        Rule ID: {alert.rule_id} • {alert.event_count} event{alert.event_count !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div className="flex items-center space-x-1 mb-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}</span>
                    </div>
                    <div>#{alert.id.split('-')[1]}</div>
                  </div>
                </div>

                <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4 text-xs">
                  {alert.agent_name && (
                    <div className="flex items-center space-x-1">
                      <MapPin className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Agent:</span>
                      <span className="font-medium">{alert.agent_name}</span>
                    </div>
                  )}
                  {alert.source_ip && (
                    <div className="flex items-center space-x-1">
                      <Activity className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Source IP:</span>
                      <span className="font-medium font-mono">{alert.source_ip}</span>
                    </div>
                  )}
                  {alert.user && (
                    <div className="flex items-center space-x-1">
                      <User className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">User:</span>
                      <span className="font-medium">{alert.user}</span>
                    </div>
                  )}
                  {alert.mitre_technique && (
                    <div className="flex items-center space-x-1">
                      <Hash className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">MITRE:</span>
                      <span className="font-medium">{alert.mitre_technique}</span>
                    </div>
                  )}
                </div>

                {(alert.process || alert.file_path || alert.destination_ip || alert.command) && (
                  <div className="mt-2 pt-2 border-t">
                    <div className="text-xs space-y-1">
                      {alert.process && (
                        <div className="flex items-start space-x-1">
                          <span className="text-muted-foreground min-w-0">Process:</span>
                          <span className="font-mono text-xs break-all">{alert.process}</span>
                        </div>
                      )}
                      {alert.file_path && (
                        <div className="flex items-start space-x-1">
                          <FileText className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">File:</span>
                          <span className="font-mono text-xs break-all">{alert.file_path}</span>
                        </div>
                      )}
                      {alert.destination_ip && (
                        <div className="flex items-start space-x-1">
                          <span className="text-muted-foreground">Destination:</span>
                          <span className="font-mono text-xs">{alert.destination_ip}</span>
                        </div>
                      )}
                      {alert.command && (
                        <div className="flex items-start space-x-1">
                          <span className="text-muted-foreground">Command:</span>
                          <span className="font-mono text-xs break-all">{alert.command}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {filteredAlerts.length === 0 && (
            <div className="text-center py-8">
              <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No alerts found</h3>
              <p className="text-muted-foreground">
                {searchQuery || severityFilter !== 'all' || statusFilter !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'No security alerts at this time'
                }
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <div>
              Showing {filteredAlerts.length} of {alerts.length} alerts
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}