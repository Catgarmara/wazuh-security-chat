'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Network, 
  Zap, 
  Eye, 
  AlertTriangle, 
  Target, 
  Clock, 
  Hash, 
  User,
  MapPin,
  Activity,
  TrendingUp,
  RefreshCw,
  Filter,
  Search,
  FileText,
  Shield,
  Globe,
  Link,
  Layers,
  GitBranch
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ThreatCorrelationEngineProps {
  className?: string;
  onCorrelationAction?: (correlationId: string, action: string) => void;
}

type CorrelationSeverity = 'critical' | 'high' | 'medium' | 'low';
type CorrelationType = 'temporal' | 'spatial' | 'behavioral' | 'contextual' | 'tactical';

interface CorrelatedEvent {
  id: string;
  type: 'alert' | 'log' | 'threat_intel' | 'network' | 'endpoint';
  title: string;
  description: string;
  timestamp: string;
  source: string;
  agent_name?: string;
  source_ip?: string;
  destination_ip?: string;
  user?: string;
  process?: string;
  file_path?: string;
  rule_id?: number;
  severity: CorrelationSeverity;
  confidence_score: number;
  tags: string[];
}

interface ThreatCorrelation {
  id: string;
  name: string;
  description: string;
  correlation_type: CorrelationType;
  severity: CorrelationSeverity;
  confidence_score: number;
  created_at: string;
  updated_at: string;
  event_count: number;
  time_window: string;
  status: 'active' | 'investigating' | 'resolved' | 'false_positive';
  attack_chain: string[];
  mitre_techniques: string[];
  threat_actor?: string;
  campaign?: string;
  correlated_events: CorrelatedEvent[];
  correlation_rules: string[];
  risk_score: number;
  affected_assets: string[];
  geographic_distribution: {
    country: string;
    count: number;
  }[];
}

interface CorrelationStats {
  total_correlations: number;
  active_correlations: number;
  high_confidence: number;
  critical_correlations: number;
  by_type: {
    temporal: number;
    spatial: number;
    behavioral: number;
    contextual: number;
    tactical: number;
  };
  avg_confidence: number;
  processing_time: number;
}

export function ThreatCorrelationEngine({ className, onCorrelationAction }: ThreatCorrelationEngineProps) {
  const [correlations, setCorrelations] = React.useState<ThreatCorrelation[]>([]);
  const [stats, setStats] = React.useState<CorrelationStats | null>(null);
  const [selectedCorrelation, setSelectedCorrelation] = React.useState<ThreatCorrelation | null>(null);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState<string>('all');
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  // Mock correlation data - replace with actual API integration
  const mockCorrelations: ThreatCorrelation[] = [
    {
      id: 'corr-001',
      name: 'Multi-Stage APT Campaign',
      description: 'Coordinated attack campaign showing lateral movement and data exfiltration patterns',
      correlation_type: 'tactical',
      severity: 'critical',
      confidence_score: 92,
      created_at: '2024-01-20T14:30:00Z',
      updated_at: '2024-01-20T14:45:00Z',
      event_count: 47,
      time_window: '6 hours',
      status: 'investigating',
      attack_chain: ['Initial Access', 'Execution', 'Persistence', 'Privilege Escalation', 'Lateral Movement', 'Collection', 'Exfiltration'],
      mitre_techniques: ['T1566.001', 'T1059.001', 'T1547.001', 'T1548.002', 'T1021.001', 'T1005', 'T1041'],
      threat_actor: 'APT29',
      campaign: 'Operation CloudHopper 2024',
      risk_score: 95,
      affected_assets: ['web-server-01', 'db-server-01', 'workstation-05', 'file-server-02'],
      geographic_distribution: [
        { country: 'Russia', count: 12 },
        { country: 'China', count: 8 },
        { country: 'Unknown', count: 27 }
      ],
      correlation_rules: ['Multi-host privilege escalation', 'Lateral movement pattern', 'Data staging activity'],
      correlated_events: [
        {
          id: 'event-001',
          type: 'alert',
          title: 'Spear phishing email detected',
          description: 'Malicious email with weaponized attachment',
          timestamp: '2024-01-20T08:30:00Z',
          source: 'Email Security',
          severity: 'high',
          confidence_score: 87,
          tags: ['phishing', 'malware', 'apt29']
        },
        {
          id: 'event-002',
          type: 'endpoint',
          title: 'Suspicious process execution',
          description: 'PowerShell with encoded command execution',
          timestamp: '2024-01-20T08:45:00Z',
          source: 'EDR',
          agent_name: 'workstation-05',
          user: 'user01',
          process: 'powershell.exe',
          severity: 'critical',
          confidence_score: 95,
          tags: ['powershell', 'encoded-command', 'execution']
        },
        {
          id: 'event-003',
          type: 'network',
          title: 'C2 communication detected',
          description: 'Communication to known APT29 infrastructure',
          timestamp: '2024-01-20T09:15:00Z',
          source: 'Network Monitor',
          source_ip: '192.168.1.205',
          destination_ip: '185.220.100.240',
          severity: 'critical',
          confidence_score: 98,
          tags: ['c2', 'apt29', 'beacon']
        },
        {
          id: 'event-004',
          type: 'alert',
          title: 'Lateral movement detected',
          description: 'Suspicious SMB activity between hosts',
          timestamp: '2024-01-20T10:30:00Z',
          source: 'Network Security',
          source_ip: '192.168.1.205',
          destination_ip: '192.168.1.100',
          user: 'service_account',
          severity: 'high',
          confidence_score: 89,
          tags: ['lateral-movement', 'smb', 'privilege-escalation']
        }
      ]
    },
    {
      id: 'corr-002',
      name: 'Credential Stuffing Campaign',
      description: 'Distributed brute force attack targeting multiple user accounts',
      correlation_type: 'behavioral',
      severity: 'high',
      confidence_score: 78,
      created_at: '2024-01-20T13:15:00Z',
      updated_at: '2024-01-20T14:30:00Z',
      event_count: 156,
      time_window: '2 hours',
      status: 'active',
      attack_chain: ['Initial Access', 'Credential Access'],
      mitre_techniques: ['T1110.003', 'T1110.001'],
      risk_score: 72,
      affected_assets: ['web-server-01', 'mail-server-01', 'vpn-gateway-01'],
      geographic_distribution: [
        { country: 'Various', count: 156 }
      ],
      correlation_rules: ['Multiple auth failures across services', 'Distributed source pattern', 'Common target accounts'],
      correlated_events: [
        {
          id: 'event-101',
          type: 'log',
          title: 'SSH authentication failure',
          description: 'Failed login attempt for admin user',
          timestamp: '2024-01-20T13:15:00Z',
          source: 'SSH',
          agent_name: 'web-server-01',
          source_ip: '203.0.113.45',
          user: 'admin',
          severity: 'medium',
          confidence_score: 65,
          tags: ['ssh', 'auth-failure', 'brute-force']
        },
        {
          id: 'event-102',
          type: 'log',
          title: 'VPN authentication failure',
          description: 'Multiple failed VPN login attempts',
          timestamp: '2024-01-20T13:18:00Z',
          source: 'VPN',
          source_ip: '198.51.100.33',
          user: 'admin',
          severity: 'medium',
          confidence_score: 70,
          tags: ['vpn', 'auth-failure', 'distributed']
        }
      ]
    },
    {
      id: 'corr-003',
      name: 'Insider Threat Pattern',
      description: 'Unusual data access pattern suggesting potential insider threat',
      correlation_type: 'behavioral',
      severity: 'medium',
      confidence_score: 68,
      created_at: '2024-01-20T12:00:00Z',
      updated_at: '2024-01-20T14:15:00Z',
      event_count: 23,
      time_window: '4 hours',
      status: 'investigating',
      attack_chain: ['Collection', 'Exfiltration'],
      mitre_techniques: ['T1005', 'T1041', 'T1537'],
      risk_score: 58,
      affected_assets: ['file-server-02', 'db-server-01'],
      geographic_distribution: [
        { country: 'Internal', count: 23 }
      ],
      correlation_rules: ['Unusual file access pattern', 'Off-hours activity', 'Large data transfers'],
      correlated_events: [
        {
          id: 'event-201',
          type: 'log',
          title: 'Unusual file access',
          description: 'Access to sensitive files outside normal hours',
          timestamp: '2024-01-20T23:30:00Z',
          source: 'File Server',
          agent_name: 'file-server-02',
          user: 'john.smith',
          file_path: '/sensitive/financial_reports/',
          severity: 'medium',
          confidence_score: 72,
          tags: ['file-access', 'after-hours', 'sensitive-data']
        }
      ]
    }
  ];

  const mockStats: CorrelationStats = {
    total_correlations: 47,
    active_correlations: 23,
    high_confidence: 15,
    critical_correlations: 3,
    by_type: {
      temporal: 12,
      spatial: 8,
      behavioral: 15,
      contextual: 7,
      tactical: 5
    },
    avg_confidence: 76.3,
    processing_time: 1.24
  };

  React.useEffect(() => {
    setCorrelations(mockCorrelations);
    setStats(mockStats);
  }, []);

  const filteredCorrelations = React.useMemo(() => {
    return correlations.filter(correlation => {
      const matchesSearch = !searchQuery || 
        correlation.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        correlation.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        correlation.threat_actor?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        correlation.campaign?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesType = typeFilter === 'all' || correlation.correlation_type === typeFilter;
      const matchesSeverity = severityFilter === 'all' || correlation.severity === severityFilter;
      
      return matchesSearch && matchesType && matchesSeverity;
    });
  }, [correlations, searchQuery, typeFilter, severityFilter]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    } finally {
      setIsRefreshing(false);
    }
  };

  const getSeverityBadge = (severity: CorrelationSeverity) => {
    switch (severity) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
    }
  };

  const getTypeBadge = (type: CorrelationType) => {
    switch (type) {
      case 'temporal':
        return 'info';
      case 'spatial':
        return 'medium';
      case 'behavioral':
        return 'high';
      case 'contextual':
        return 'outline';
      case 'tactical':
        return 'critical';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'offline';
      case 'investigating':
        return 'degraded';
      case 'resolved':
        return 'online';
      case 'false_positive':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getEventTypeIcon = (type: string) => {
    switch (type) {
      case 'alert':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'log':
        return <FileText className="h-4 w-4 text-blue-500" />;
      case 'threat_intel':
        return <Globe className="h-4 w-4 text-purple-500" />;
      case 'network':
        return <Network className="h-4 w-4 text-green-500" />;
      case 'endpoint':
        return <Shield className="h-4 w-4 text-orange-500" />;
      default:
        return <Activity className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center space-x-2">
            <Network className="h-6 w-6" />
            <span>Threat Correlation Engine</span>
          </h2>
          <p className="text-muted-foreground">AI-powered threat correlation and attack pattern analysis</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="default" size="sm">
            <Zap className="h-4 w-4 mr-2" />
            Analyze
          </Button>
        </div>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{stats.total_correlations}</div>
                  <div className="text-sm text-muted-foreground">Total Correlations</div>
                </div>
                <Network className="h-5 w-5 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold text-red-600">{stats.critical_correlations}</div>
                  <div className="text-sm text-muted-foreground">Critical</div>
                </div>
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold text-green-600">{stats.high_confidence}</div>
                  <div className="text-sm text-muted-foreground">High Confidence</div>
                </div>
                <Target className="h-5 w-5 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{stats.avg_confidence.toFixed(1)}%</div>
                  <div className="text-sm text-muted-foreground">Avg Confidence</div>
                </div>
                <TrendingUp className="h-5 w-5 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{stats.processing_time}s</div>
                  <div className="text-sm text-muted-foreground">Avg Processing</div>
                </div>
                <Clock className="h-5 w-5 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search correlations by name, threat actor, campaign, or technique..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-background text-sm"
          >
            <option value="all">All Types</option>
            <option value="temporal">Temporal</option>
            <option value="spatial">Spatial</option>
            <option value="behavioral">Behavioral</option>
            <option value="contextual">Contextual</option>
            <option value="tactical">Tactical</option>
          </select>
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
          </select>
        </div>
      </div>

      {/* Correlations List */}
      <div className="space-y-4">
        {filteredCorrelations.map((correlation) => (
          <Card key={correlation.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <GitBranch className="h-5 w-5 text-purple-600" />
                  <div>
                    <CardTitle className="text-lg">{correlation.name}</CardTitle>
                    <CardDescription>{correlation.description}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={getSeverityBadge(correlation.severity)} className="text-xs">
                    {correlation.severity.toUpperCase()}
                  </Badge>
                  <Badge variant={getTypeBadge(correlation.correlation_type)} className="text-xs">
                    {correlation.correlation_type.toUpperCase()}
                  </Badge>
                  <Badge variant={getStatusBadge(correlation.status)} className="text-xs">
                    {correlation.status.replace('_', ' ').toUpperCase()}
                  </Badge>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              <div className="space-y-4">
                {/* Correlation Metrics */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 text-sm">
                  <div className="flex items-center space-x-1">
                    <Target className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Confidence:</span>
                    <span className="font-medium">{correlation.confidence_score}%</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Hash className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Events:</span>
                    <span className="font-medium">{correlation.event_count}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Window:</span>
                    <span className="font-medium">{correlation.time_window}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <AlertTriangle className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Risk Score:</span>
                    <span className="font-medium">{correlation.risk_score}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Activity className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Assets:</span>
                    <span className="font-medium">{correlation.affected_assets.length}</span>
                  </div>
                </div>

                {/* Attack Chain */}
                {correlation.attack_chain.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2 flex items-center space-x-2">
                      <Layers className="h-4 w-4" />
                      <span>Attack Chain</span>
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {correlation.attack_chain.map((stage, index) => (
                        <div key={stage} className="flex items-center">
                          <Badge variant="outline" className="text-xs">
                            {index + 1}. {stage}
                          </Badge>
                          {index < correlation.attack_chain.length - 1 && (
                            <ArrowRight className="h-3 w-3 mx-1 text-muted-foreground" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* MITRE Techniques */}
                {correlation.mitre_techniques.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">MITRE ATT&CK Techniques</h4>
                    <div className="flex flex-wrap gap-2">
                      {correlation.mitre_techniques.map((technique) => (
                        <Badge key={technique} variant="outline" className="text-xs">
                          {technique}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Threat Context */}
                {(correlation.threat_actor || correlation.campaign) && (
                  <div className="grid gap-2 md:grid-cols-2 text-sm">
                    {correlation.threat_actor && (
                      <div className="flex items-center space-x-1">
                        <User className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Threat Actor:</span>
                        <span className="font-medium">{correlation.threat_actor}</span>
                      </div>
                    )}
                    {correlation.campaign && (
                      <div className="flex items-center space-x-1">
                        <Target className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Campaign:</span>
                        <span className="font-medium">{correlation.campaign}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Correlated Events */}
                <div>
                  <h4 className="font-medium mb-2 flex items-center space-x-2">
                    <Link className="h-4 w-4" />
                    <span>Correlated Events ({correlation.correlated_events.length})</span>
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {correlation.correlated_events.slice(0, 5).map((event) => (
                      <div key={event.id} className="p-3 border rounded-lg">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-start space-x-2">
                            {getEventTypeIcon(event.type)}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2 mb-1">
                                <span className="font-medium text-sm">{event.title}</span>
                                <Badge variant={getSeverityBadge(event.severity)} className="text-xs">
                                  {event.severity}
                                </Badge>
                                <Badge variant="outline" className="text-xs capitalize">
                                  {event.type}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground mb-1">{event.description}</p>
                              <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                                <span>{formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}</span>
                                {event.agent_name && <span>Agent: {event.agent_name}</span>}
                                {event.user && <span>User: {event.user}</span>}
                                {event.source_ip && <span>IP: {event.source_ip}</span>}
                              </div>
                            </div>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {event.confidence_score}% confidence
                          </div>
                        </div>
                        {event.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {event.tags.map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {correlation.correlated_events.length > 5 && (
                      <div className="text-center py-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedCorrelation(correlation)}
                        >
                          View All {correlation.correlated_events.length} Events
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center space-x-2">
                    <Button variant="outline" size="sm">
                      <Eye className="h-4 w-4 mr-1" />
                      Investigate
                    </Button>
                    <Button variant="outline" size="sm">
                      <FileText className="h-4 w-4 mr-1" />
                      Export
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Activity className="h-4 w-4 mr-1" />
                      Timeline
                    </Button>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Updated {formatDistanceToNow(new Date(correlation.updated_at), { addSuffix: true })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredCorrelations.length === 0 && (
        <div className="text-center py-8">
          <Network className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No correlations found</h3>
          <p className="text-muted-foreground">
            {searchQuery || typeFilter !== 'all' || severityFilter !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'No threat correlations detected at this time'
            }
          </p>
        </div>
      )}
    </div>
  );
}