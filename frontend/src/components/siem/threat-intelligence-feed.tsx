'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Globe, 
  Shield, 
  Search, 
  Filter, 
  RefreshCw, 
  Clock,
  AlertTriangle,
  Target,
  MapPin,
  Hash,
  Eye,
  TrendingUp,
  Activity,
  Database,
  ExternalLink,
  FileText,
  Network,
  Zap,
  Bug
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ThreatIntelligenceFeedProps {
  className?: string;
  onRefresh?: () => void;
}

type ThreatType = 'malware' | 'phishing' | 'c2' | 'botnet' | 'vulnerability' | 'apt' | 'exploit';
type ThreatSeverity = 'critical' | 'high' | 'medium' | 'low';
type ThreatStatus = 'active' | 'monitoring' | 'mitigated' | 'expired';

interface ThreatIndicator {
  id: string;
  type: ThreatType;
  severity: ThreatSeverity;
  status: ThreatStatus;
  indicator: string;
  indicator_type: 'ip' | 'domain' | 'url' | 'hash' | 'email' | 'file';
  description: string;
  source: string;
  confidence_score: number;
  first_seen: string;
  last_seen: string;
  tags: string[];
  country?: string;
  asn?: string;
  malware_family?: string;
  campaign?: string;
  references: string[];
  tlp_level: 'white' | 'green' | 'amber' | 'red';
  ioc_count: number;
}

interface ThreatStats {
  total: number;
  active: number;
  monitoring: number;
  mitigated: number;
  by_type: {
    malware: number;
    phishing: number;
    c2: number;
    botnet: number;
    vulnerability: number;
    apt: number;
    exploit: number;
  };
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  feeds: {
    name: string;
    status: 'online' | 'offline' | 'degraded';
    last_update: string;
    indicators_count: number;
  }[];
}

export function ThreatIntelligenceFeed({ className, onRefresh }: ThreatIntelligenceFeedProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState<string>('all');
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');
  const [lastUpdate, setLastUpdate] = React.useState(new Date());

  // Mock threat intelligence data - replace with actual API integration
  const threats: ThreatIndicator[] = [
    {
      id: 'threat-001',
      type: 'malware',
      severity: 'critical',
      status: 'active',
      indicator: '185.220.100.240',
      indicator_type: 'ip',
      description: 'Known malware C2 server hosting TrickBot infrastructure',
      source: 'AlienVault OTX',
      confidence_score: 95,
      first_seen: '2024-01-15T10:00:00Z',
      last_seen: '2024-01-20T14:30:00Z',
      tags: ['trickbot', 'banking-trojan', 'c2-server'],
      country: 'Russia',
      asn: 'AS13335',
      malware_family: 'TrickBot',
      campaign: 'Operation TrickBot 2024',
      references: ['https://otx.alienvault.com/indicator/ip/185.220.100.240'],
      tlp_level: 'amber',
      ioc_count: 47
    },
    {
      id: 'threat-002',
      type: 'phishing',
      severity: 'high',
      status: 'active',
      indicator: 'secure-bank-update.com',
      indicator_type: 'domain',
      description: 'Phishing domain impersonating major banking institution',
      source: 'PhishTank',
      confidence_score: 87,
      first_seen: '2024-01-20T08:15:00Z',
      last_seen: '2024-01-20T14:45:00Z',
      tags: ['phishing', 'banking', 'credential-theft'],
      country: 'Netherlands',
      asn: 'AS16509',
      campaign: 'Banking Phish Campaign Q1-2024',
      references: ['https://phishtank.com/phish_detail.php?phish_id=8234567'],
      tlp_level: 'white',
      ioc_count: 12
    },
    {
      id: 'threat-003',
      type: 'vulnerability',
      severity: 'critical',
      status: 'monitoring',
      indicator: 'CVE-2024-1234',
      indicator_type: 'hash',
      description: 'Critical RCE vulnerability in Apache Struts framework',
      source: 'MITRE CVE',
      confidence_score: 100,
      first_seen: '2024-01-18T12:00:00Z',
      last_seen: '2024-01-20T14:00:00Z',
      tags: ['rce', 'apache-struts', 'web-application'],
      references: ['https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-1234'],
      tlp_level: 'white',
      ioc_count: 8
    },
    {
      id: 'threat-004',
      type: 'c2',
      severity: 'high',
      status: 'active',
      indicator: 'hxxps://evil-c2-server[.]net/panel',
      indicator_type: 'url',
      description: 'Command and control server for Cobalt Strike beacons',
      source: 'ThreatConnect',
      confidence_score: 92,
      first_seen: '2024-01-19T16:30:00Z',
      last_seen: '2024-01-20T13:15:00Z',
      tags: ['cobalt-strike', 'c2', 'apt', 'beacon'],
      country: 'China',
      asn: 'AS4134',
      malware_family: 'Cobalt Strike',
      campaign: 'APT29 Infrastructure',
      references: ['https://threatconnect.com/blog/apt29-cobalt-strike'],
      tlp_level: 'red',
      ioc_count: 23
    },
    {
      id: 'threat-005',
      type: 'apt',
      severity: 'critical',
      status: 'monitoring',
      indicator: 'd41d8cd98f00b204e9800998ecf8427e',
      indicator_type: 'hash',
      description: 'APT28 malware sample targeting government entities',
      source: 'MISP',
      confidence_score: 98,
      first_seen: '2024-01-17T09:00:00Z',
      last_seen: '2024-01-20T11:30:00Z',
      tags: ['apt28', 'government', 'espionage', 'nation-state'],
      malware_family: 'Sofacy',
      campaign: 'APT28 Government Campaign 2024',
      references: ['https://attack.mitre.org/groups/G0007/'],
      tlp_level: 'red',
      ioc_count: 156
    },
    {
      id: 'threat-006',
      type: 'botnet',
      severity: 'medium',
      status: 'mitigated',
      indicator: 'botnet-node-tracker.org',
      indicator_type: 'domain',
      description: 'Mirai botnet communication domain (sinkholed)',
      source: 'Shadowserver',
      confidence_score: 85,
      first_seen: '2024-01-10T14:20:00Z',
      last_seen: '2024-01-18T16:45:00Z',
      tags: ['mirai', 'botnet', 'iot', 'sinkholed'],
      country: 'United States',
      asn: 'AS15169',
      malware_family: 'Mirai',
      references: ['https://www.shadowserver.org/what-we-do/network-reporting/'],
      tlp_level: 'green',
      ioc_count: 342
    }
  ];

  const threatStats: ThreatStats = React.useMemo(() => {
    const total = threats.length;
    const active = threats.filter(t => t.status === 'active').length;
    const monitoring = threats.filter(t => t.status === 'monitoring').length;
    const mitigated = threats.filter(t => t.status === 'mitigated').length;
    
    const by_type = {
      malware: threats.filter(t => t.type === 'malware').length,
      phishing: threats.filter(t => t.type === 'phishing').length,
      c2: threats.filter(t => t.type === 'c2').length,
      botnet: threats.filter(t => t.type === 'botnet').length,
      vulnerability: threats.filter(t => t.type === 'vulnerability').length,
      apt: threats.filter(t => t.type === 'apt').length,
      exploit: threats.filter(t => t.type === 'exploit').length,
    };

    const by_severity = {
      critical: threats.filter(t => t.severity === 'critical').length,
      high: threats.filter(t => t.severity === 'high').length,
      medium: threats.filter(t => t.severity === 'medium').length,
      low: threats.filter(t => t.severity === 'low').length,
    };

    const feeds = [
      { name: 'AlienVault OTX', status: 'online' as const, last_update: '2024-01-20T14:30:00Z', indicators_count: 1247 },
      { name: 'PhishTank', status: 'online' as const, last_update: '2024-01-20T14:25:00Z', indicators_count: 892 },
      { name: 'MISP', status: 'online' as const, last_update: '2024-01-20T14:20:00Z', indicators_count: 2156 },
      { name: 'ThreatConnect', status: 'degraded' as const, last_update: '2024-01-20T13:45:00Z', indicators_count: 567 },
      { name: 'Shadowserver', status: 'online' as const, last_update: '2024-01-20T14:35:00Z', indicators_count: 3421 }
    ];

    return {
      total,
      active,
      monitoring,
      mitigated,
      by_type,
      by_severity,
      feeds
    };
  }, [threats]);

  const filteredThreats = React.useMemo(() => {
    return threats.filter(threat => {
      const matchesSearch = !searchQuery || 
        threat.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.indicator.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())) ||
        threat.malware_family?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.campaign?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesType = typeFilter === 'all' || threat.type === typeFilter;
      const matchesSeverity = severityFilter === 'all' || threat.severity === severityFilter;
      
      return matchesSearch && matchesType && matchesSeverity;
    });
  }, [threats, searchQuery, typeFilter, severityFilter]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
      setLastUpdate(new Date());
      onRefresh?.();
    } finally {
      setIsRefreshing(false);
    }
  };

  const getTypeIcon = (type: ThreatType) => {
    switch (type) {
      case 'malware':
        return <Bug className="h-4 w-4 text-red-500" />;
      case 'phishing':
        return <Target className="h-4 w-4 text-yellow-500" />;
      case 'c2':
        return <Network className="h-4 w-4 text-purple-500" />;
      case 'botnet':
        return <Activity className="h-4 w-4 text-orange-500" />;
      case 'vulnerability':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'apt':
        return <Shield className="h-4 w-4 text-red-700" />;
      case 'exploit':
        return <Zap className="h-4 w-4 text-yellow-600" />;
    }
  };

  const getSeverityBadge = (severity: ThreatSeverity) => {
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

  const getStatusBadge = (status: ThreatStatus) => {
    switch (status) {
      case 'active':
        return 'offline';
      case 'monitoring':
        return 'degraded';
      case 'mitigated':
        return 'online';
      case 'expired':
        return 'outline';
    }
  };

  const getTLPBadge = (tlp: string) => {
    switch (tlp) {
      case 'red':
        return 'critical';
      case 'amber':
        return 'high';
      case 'green':
        return 'medium';
      case 'white':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getFeedStatusBadge = (status: string) => {
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

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Threat Feed Statistics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Globe className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{threatStats.total}</div>
                <div className="text-sm text-muted-foreground">Total Indicators</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <div>
                <div className="text-2xl font-bold text-red-600">{threatStats.active}</div>
                <div className="text-sm text-muted-foreground">Active Threats</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Eye className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="text-2xl font-bold text-yellow-600">{threatStats.monitoring}</div>
                <div className="text-sm text-muted-foreground">Monitoring</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-2xl font-bold text-green-600">{threatStats.mitigated}</div>
                <div className="text-sm text-muted-foreground">Mitigated</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Threat Intelligence Feeds Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <span>Intelligence Feed Sources</span>
          </CardTitle>
          <CardDescription>External threat intelligence feed status and metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {threatStats.feeds.map((feed) => (
              <div key={feed.name} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center space-x-3">
                  <Database className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{feed.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {feed.indicators_count.toLocaleString()} indicators
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="text-right text-sm">
                    <div className="text-muted-foreground">
                      {formatDistanceToNow(new Date(feed.last_update), { addSuffix: true })}
                    </div>
                  </div>
                  <Badge variant={getFeedStatusBadge(feed.status)} className="text-xs">
                    {feed.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Threat Indicators List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Target className="h-5 w-5" />
                <span>Threat Intelligence Indicators</span>
              </CardTitle>
              <CardDescription>Real-time threat indicators and intelligence feeds</CardDescription>
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
                placeholder="Search indicators by description, IOC, source, tags, or campaign..."
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
                <option value="malware">Malware</option>
                <option value="phishing">Phishing</option>
                <option value="c2">C2</option>
                <option value="botnet">Botnet</option>
                <option value="vulnerability">Vulnerability</option>
                <option value="apt">APT</option>
                <option value="exploit">Exploit</option>
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

          {/* Threat Indicators Table */}
          <div className="space-y-2">
            {filteredThreats.map((threat) => (
              <div key={threat.id} className="p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start space-x-3">
                    <div className="flex flex-col items-center space-y-1">
                      {getTypeIcon(threat.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge variant={getSeverityBadge(threat.severity)} className="text-xs">
                          {threat.severity.toUpperCase()}
                        </Badge>
                        <Badge variant={getStatusBadge(threat.status)} className="text-xs">
                          {threat.status.toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="text-xs capitalize">
                          {threat.type}
                        </Badge>
                        <Badge variant={getTLPBadge(threat.tlp_level)} className="text-xs">
                          TLP:{threat.tlp_level.toUpperCase()}
                        </Badge>
                      </div>
                      <h4 className="font-semibold text-sm mb-1">{threat.description}</h4>
                      <div className="text-xs text-muted-foreground mb-2">
                        Source: {threat.source} • Confidence: {threat.confidence_score}% • IOCs: {threat.ioc_count}
                      </div>
                      <div className="font-mono text-sm bg-accent/50 p-2 rounded break-all">
                        {threat.indicator}
                      </div>
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div className="flex items-center space-x-1 mb-1">
                      <Clock className="h-3 w-3" />
                      <span>Last seen: {formatDistanceToNow(new Date(threat.last_seen), { addSuffix: true })}</span>
                    </div>
                    <div>#{threat.id.split('-')[1]}</div>
                  </div>
                </div>

                <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4 text-xs mb-3">
                  <div className="flex items-center space-x-1">
                    <Hash className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Type:</span>
                    <span className="font-medium capitalize">{threat.indicator_type}</span>
                  </div>
                  {threat.country && (
                    <div className="flex items-center space-x-1">
                      <MapPin className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Country:</span>
                      <span className="font-medium">{threat.country}</span>
                    </div>
                  )}
                  {threat.malware_family && (
                    <div className="flex items-center space-x-1">
                      <Bug className="h-3 w-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Family:</span>
                      <span className="font-medium">{threat.malware_family}</span>
                    </div>
                  )}
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">First seen:</span>
                    <span className="font-medium">{formatDistanceToNow(new Date(threat.first_seen), { addSuffix: true })}</span>
                  </div>
                </div>

                {threat.tags.length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs text-muted-foreground mb-1">Tags:</div>
                    <div className="flex flex-wrap gap-1">
                      {threat.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {(threat.campaign || threat.asn) && (
                  <div className="pt-2 border-t">
                    <div className="grid gap-2 md:grid-cols-2 text-xs">
                      {threat.campaign && (
                        <div className="flex items-start space-x-1">
                          <FileText className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">Campaign:</span>
                          <span className="font-medium">{threat.campaign}</span>
                        </div>
                      )}
                      {threat.asn && (
                        <div className="flex items-start space-x-1">
                          <Network className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">ASN:</span>
                          <span className="font-medium">{threat.asn}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {threat.references.length > 0 && (
                  <div className="mt-2 pt-2 border-t">
                    <div className="text-xs text-muted-foreground mb-1">References:</div>
                    <div className="space-y-1">
                      {threat.references.slice(0, 2).map((ref, index) => (
                        <div key={index} className="flex items-center space-x-1 text-xs">
                          <ExternalLink className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                          <a href={ref} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                            {ref}
                          </a>
                        </div>
                      ))}
                      {threat.references.length > 2 && (
                        <div className="text-xs text-muted-foreground">
                          +{threat.references.length - 2} more references
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {filteredThreats.length === 0 && (
            <div className="text-center py-8">
              <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No threat indicators found</h3>
              <p className="text-muted-foreground">
                {searchQuery || typeFilter !== 'all' || severityFilter !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'No threat intelligence indicators available'
                }
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <div>
              Showing {filteredThreats.length} of {threats.length} indicators
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