'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  FileText, 
  Search, 
  Filter, 
  RefreshCw, 
  Clock,
  AlertTriangle,
  CheckCircle,
  Info,
  Eye,
  Download,
  Calendar,
  Hash,
  User,
  MapPin,
  Activity,
  Database,
  Server,
  Network,
  Zap,
  Terminal
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface LogAnalysisVisualizationProps {
  className?: string;
  onRefresh?: () => void;
}

type LogLevel = 'error' | 'warning' | 'info' | 'debug' | 'trace';
type LogSource = 'wazuh' | 'system' | 'application' | 'security' | 'network' | 'database';

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  source: LogSource;
  agent_id?: string;
  agent_name?: string;
  message: string;
  raw_log: string;
  parsed_fields: {
    source_ip?: string;
    destination_ip?: string;
    user?: string;
    process?: string;
    command?: string;
    file_path?: string;
    status_code?: number;
    protocol?: string;
    port?: number;
  };
  rule_id?: number;
  rule_description?: string;
  classification: string;
  tags: string[];
  event_count: number;
}

interface LogStats {
  total: number;
  by_level: {
    error: number;
    warning: number;
    info: number;
    debug: number;
    trace: number;
  };
  by_source: {
    wazuh: number;
    system: number;
    application: number;
    security: number;
    network: number;
    database: number;
  };
  trends: {
    last_hour: number;
    last_24h: number;
    last_7d: number;
  };
  top_sources: {
    name: string;
    count: number;
    percentage: number;
  }[];
}

export function LogAnalysisVisualization({ className, onRefresh }: LogAnalysisVisualizationProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [levelFilter, setLevelFilter] = React.useState<string>('all');
  const [sourceFilter, setSourceFilter] = React.useState<string>('all');
  const [timeRange, setTimeRange] = React.useState<string>('24h');
  const [lastUpdate, setLastUpdate] = React.useState(new Date());

  // Mock log data - replace with actual API integration
  const logs: LogEntry[] = [
    {
      id: 'log-001',
      timestamp: '2024-01-20T14:45:32Z',
      level: 'error',
      source: 'security',
      agent_id: '001',
      agent_name: 'web-server-01',
      message: 'Failed login attempt detected from suspicious IP',
      raw_log: 'Jan 20 14:45:32 web-server-01 sshd[12345]: Failed login for user admin from 192.168.1.200 port 22 ssh2',
      parsed_fields: {
        source_ip: '192.168.1.200',
        user: 'admin',
        process: 'sshd',
        port: 22,
        protocol: 'ssh'
      },
      rule_id: 5716,
      rule_description: 'SSH authentication failure',
      classification: 'Authentication Failure',
      tags: ['ssh', 'authentication', 'failed-login'],
      event_count: 1
    },
    {
      id: 'log-002',
      timestamp: '2024-01-20T14:44:15Z',
      level: 'warning',
      source: 'application',
      agent_id: '002',
      agent_name: 'db-server-01',
      message: 'Database connection pool near capacity',
      raw_log: '[2024-01-20 14:44:15] WARNING: Connection pool usage at 85% (85/100 connections)',
      parsed_fields: {
        process: 'postgresql'
      },
      classification: 'Performance Warning',
      tags: ['database', 'performance', 'connection-pool'],
      event_count: 3
    },
    {
      id: 'log-003',
      timestamp: '2024-01-20T14:43:08Z',
      level: 'info',
      source: 'wazuh',
      message: 'Agent connectivity check completed successfully',
      raw_log: '2024/01/20 14:43:08 wazuh-remoted: INFO: Agent connectivity check completed. Active agents: 245/250',
      parsed_fields: {},
      classification: 'System Information',
      tags: ['agent-check', 'connectivity', 'status'],
      event_count: 1
    },
    {
      id: 'log-004',
      timestamp: '2024-01-20T14:42:30Z',
      level: 'error',
      source: 'network',
      agent_id: '003',
      agent_name: 'workstation-05',
      message: 'Suspicious network traffic to known malicious IP blocked',
      raw_log: 'Jan 20 14:42:30 workstation-05 iptables: BLOCK IN=eth0 OUT= SRC=192.168.1.205 DST=185.220.100.240 PROTO=TCP SPT=54321 DPT=443',
      parsed_fields: {
        source_ip: '192.168.1.205',
        destination_ip: '185.220.100.240',
        protocol: 'TCP',
        port: 443
      },
      rule_id: 31153,
      rule_description: 'Connection to known malicious IP blocked',
      classification: 'Network Security',
      tags: ['firewall', 'blocked', 'malicious-ip', 'network-security'],
      event_count: 1
    },
    {
      id: 'log-005',
      timestamp: '2024-01-20T14:41:45Z',
      level: 'warning',
      source: 'system',
      agent_id: '001',
      agent_name: 'web-server-01',
      message: 'High CPU usage detected',
      raw_log: 'Jan 20 14:41:45 web-server-01 kernel: CPU usage: 89% (threshold: 80%)',
      parsed_fields: {
        process: 'kernel'
      },
      classification: 'System Performance',
      tags: ['cpu', 'performance', 'threshold'],
      event_count: 5
    },
    {
      id: 'log-006',
      timestamp: '2024-01-20T14:40:22Z',
      level: 'info',
      source: 'application',
      agent_id: '002',
      agent_name: 'db-server-01',
      message: 'Backup process completed successfully',
      raw_log: '[2024-01-20 14:40:22] INFO: Database backup completed - Size: 2.5GB, Duration: 45min',
      parsed_fields: {
        process: 'backup'
      },
      classification: 'Backup Operation',
      tags: ['backup', 'database', 'successful'],
      event_count: 1
    },
    {
      id: 'log-007',
      timestamp: '2024-01-20T14:39:10Z',
      level: 'error',
      source: 'security',
      agent_id: '003',
      agent_name: 'workstation-05',
      message: 'Privilege escalation attempt detected',
      raw_log: 'Jan 20 14:39:10 workstation-05 sudo: user01 : TTY=pts/0 ; PWD=/home/user01 ; USER=root ; COMMAND=/bin/bash',
      parsed_fields: {
        user: 'user01',
        command: '/bin/bash',
        process: 'sudo'
      },
      rule_id: 5403,
      rule_description: 'Privilege escalation attempt',
      classification: 'Security Violation',
      tags: ['privilege-escalation', 'sudo', 'security'],
      event_count: 2
    },
    {
      id: 'log-008',
      timestamp: '2024-01-20T14:38:55Z',
      level: 'debug',
      source: 'wazuh',
      message: 'Rule engine processing performance metrics',
      raw_log: '2024/01/20 14:38:55 wazuh-analysisd: DEBUG: Rules processed: 15,247 | Processing time: 0.85ms avg',
      parsed_fields: {},
      classification: 'Debug Information',
      tags: ['rule-engine', 'performance', 'debug'],
      event_count: 1
    }
  ];

  const logStats: LogStats = React.useMemo(() => {
    const total = logs.length;
    
    const by_level = {
      error: logs.filter(l => l.level === 'error').length,
      warning: logs.filter(l => l.level === 'warning').length,
      info: logs.filter(l => l.level === 'info').length,
      debug: logs.filter(l => l.level === 'debug').length,
      trace: logs.filter(l => l.level === 'trace').length,
    };

    const by_source = {
      wazuh: logs.filter(l => l.source === 'wazuh').length,
      system: logs.filter(l => l.source === 'system').length,
      application: logs.filter(l => l.source === 'application').length,
      security: logs.filter(l => l.source === 'security').length,
      network: logs.filter(l => l.source === 'network').length,
      database: logs.filter(l => l.source === 'database').length,
    };

    const top_sources = [
      { name: 'web-server-01', count: 234, percentage: 35.2 },
      { name: 'db-server-01', count: 189, percentage: 28.4 },
      { name: 'workstation-05', count: 156, percentage: 23.5 },
      { name: 'wazuh-manager', count: 87, percentage: 13.1 }
    ];

    return {
      total,
      by_level,
      by_source,
      trends: {
        last_hour: 1247,
        last_24h: 15630,
        last_7d: 89420
      },
      top_sources
    };
  }, [logs]);

  const filteredLogs = React.useMemo(() => {
    return logs.filter(log => {
      const matchesSearch = !searchQuery || 
        log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.raw_log.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.classification.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.agent_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.parsed_fields.source_ip?.includes(searchQuery) ||
        log.parsed_fields.user?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesLevel = levelFilter === 'all' || log.level === levelFilter;
      const matchesSource = sourceFilter === 'all' || log.source === sourceFilter;
      
      return matchesSearch && matchesLevel && matchesSource;
    });
  }, [logs, searchQuery, levelFilter, sourceFilter]);

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

  const getLevelIcon = (level: LogLevel) => {
    switch (level) {
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      case 'debug':
        return <Terminal className="h-4 w-4 text-gray-500" />;
      case 'trace':
        return <Eye className="h-4 w-4 text-gray-400" />;
    }
  };

  const getSourceIcon = (source: LogSource) => {
    switch (source) {
      case 'wazuh':
        return <Activity className="h-4 w-4 text-blue-600" />;
      case 'system':
        return <Server className="h-4 w-4 text-green-600" />;
      case 'application':
        return <Zap className="h-4 w-4 text-purple-600" />;
      case 'security':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'network':
        return <Network className="h-4 w-4 text-orange-600" />;
      case 'database':
        return <Database className="h-4 w-4 text-teal-600" />;
    }
  };

  const getLevelBadge = (level: LogLevel) => {
    switch (level) {
      case 'error':
        return 'critical';
      case 'warning':
        return 'high';
      case 'info':
        return 'info';
      case 'debug':
        return 'outline';
      case 'trace':
        return 'outline';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Log Statistics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{logStats.trends.last_24h.toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">Events (24h)</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <div>
                <div className="text-2xl font-bold text-red-600">{logStats.by_level.error}</div>
                <div className="text-sm text-muted-foreground">Errors</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="text-2xl font-bold text-yellow-600">{logStats.by_level.warning}</div>
                <div className="text-sm text-muted-foreground">Warnings</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-2xl font-bold">{logStats.trends.last_hour.toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">Last Hour</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Log Sources Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <span>Log Sources Distribution</span>
          </CardTitle>
          <CardDescription>Distribution of log events by source and agent</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="text-sm font-medium">By Source Type</div>
              {Object.entries(logStats.by_source).map(([source, count]) => (
                <div key={source} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {getSourceIcon(source as LogSource)}
                    <span className="text-sm capitalize">{source}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-secondary rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${(count / logStats.total) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="text-sm font-medium">Top Agents</div>
              {logStats.top_sources.map((agent) => (
                <div key={agent.name} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{agent.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-secondary rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${agent.percentage}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono w-12 text-right">{agent.count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Log Events List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Log Analysis</span>
              </CardTitle>
              <CardDescription>Real-time log events and security analysis</CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
              >
                <Download className="h-4 w-4" />
              </Button>
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
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filter Controls */}
          <div className="flex items-center space-x-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search logs by message, classification, agent, IP, user, or tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={levelFilter}
                onChange={(e) => setLevelFilter(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="all">All Levels</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
                <option value="debug">Debug</option>
                <option value="trace">Trace</option>
              </select>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="all">All Sources</option>
                <option value="wazuh">Wazuh</option>
                <option value="system">System</option>
                <option value="application">Application</option>
                <option value="security">Security</option>
                <option value="network">Network</option>
                <option value="database">Database</option>
              </select>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="1h">Last Hour</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>
          </div>

          {/* Log Events Table */}
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div key={log.id} className="p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start space-x-3">
                    <div className="flex flex-col items-center space-y-1">
                      {getLevelIcon(log.level)}
                      {getSourceIcon(log.source)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge variant={getLevelBadge(log.level)} className="text-xs">
                          {log.level.toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="text-xs capitalize">
                          {log.source}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {log.classification}
                        </Badge>
                        {log.rule_id && (
                          <Badge variant="outline" className="text-xs">
                            Rule {log.rule_id}
                          </Badge>
                        )}
                      </div>
                      <h4 className="font-semibold text-sm mb-1">{log.message}</h4>
                      <div className="text-xs text-muted-foreground mb-2">
                        {log.agent_name && `Agent: ${log.agent_name} • `}
                        Events: {log.event_count}
                        {log.rule_description && ` • ${log.rule_description}`}
                      </div>
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div className="flex items-center space-x-1 mb-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}</span>
                    </div>
                    <div>#{log.id.split('-')[1]}</div>
                  </div>
                </div>

                {/* Parsed Fields */}
                {Object.keys(log.parsed_fields).length > 0 && (
                  <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4 text-xs mb-3">
                    {log.parsed_fields.source_ip && (
                      <div className="flex items-center space-x-1">
                        <MapPin className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Source IP:</span>
                        <span className="font-medium font-mono">{log.parsed_fields.source_ip}</span>
                      </div>
                    )}
                    {log.parsed_fields.user && (
                      <div className="flex items-center space-x-1">
                        <User className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">User:</span>
                        <span className="font-medium">{log.parsed_fields.user}</span>
                      </div>
                    )}
                    {log.parsed_fields.process && (
                      <div className="flex items-center space-x-1">
                        <Terminal className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Process:</span>
                        <span className="font-medium">{log.parsed_fields.process}</span>
                      </div>
                    )}
                    {log.parsed_fields.port && (
                      <div className="flex items-center space-x-1">
                        <Hash className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Port:</span>
                        <span className="font-medium">{log.parsed_fields.port}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Tags */}
                {log.tags.length > 0 && (
                  <div className="mb-3">
                    <div className="flex flex-wrap gap-1">
                      {log.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw Log */}
                <div className="pt-2 border-t">
                  <div className="text-xs text-muted-foreground mb-1">Raw Log:</div>
                  <div className="font-mono text-xs bg-accent/30 p-2 rounded text-wrap break-all">
                    {log.raw_log}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredLogs.length === 0 && (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No log events found</h3>
              <p className="text-muted-foreground">
                {searchQuery || levelFilter !== 'all' || sourceFilter !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'No log events available for the selected time range'
                }
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <div>
              Showing {filteredLogs.length} of {logs.length} log events
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