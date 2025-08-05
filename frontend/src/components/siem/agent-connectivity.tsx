'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Users, 
  Search, 
  Filter, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  Monitor,
  Wifi,
  WifiOff,
  Clock,
  MapPin,
  Server,
  Activity
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface AgentConnectivityProps {
  className?: string;
  onRefresh?: () => void;
}

interface Agent {
  id: string;
  name: string;
  ip_address: string;
  os: string;
  version: string;
  status: 'active' | 'disconnected' | 'never_connected' | 'pending';
  last_keep_alive: string;
  registration_date: string;
  groups: string[];
  node_name: string;
  manager_host: string;
  os_platform: string;
  os_version: string;
  config_sum: string;
  merged_sum: string;
  sync_status: 'synced' | 'not_synced';
}

export function AgentConnectivity({ className, onRefresh }: AgentConnectivityProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [lastUpdate, setLastUpdate] = React.useState(new Date());

  // Mock agent data - replace with actual API integration
  const agents: Agent[] = [
    {
      id: '001',
      name: 'web-server-01',
      ip_address: '192.168.1.100',
      os: 'ubuntu',
      version: '4.12.0',
      status: 'active',
      last_keep_alive: '2024-01-20T14:30:00Z',
      registration_date: '2024-01-15T09:00:00Z',
      groups: ['web-servers', 'production'],
      node_name: 'wazuh-manager-master',
      manager_host: '192.168.1.10',
      os_platform: 'ubuntu',
      os_version: '20.04',
      config_sum: 'ab4f63f9',
      merged_sum: 'cd8e92a1',
      sync_status: 'synced'
    },
    {
      id: '002',
      name: 'db-server-01',
      ip_address: '192.168.1.101',
      os: 'centos',
      version: '4.12.0',
      status: 'active',
      last_keep_alive: '2024-01-20T14:29:45Z',
      registration_date: '2024-01-15T09:15:00Z',
      groups: ['database-servers', 'production'],
      node_name: 'wazuh-manager-worker-1',
      manager_host: '192.168.1.10',
      os_platform: 'centos',
      os_version: '8.4',
      config_sum: 'ef7d23b5',
      merged_sum: 'gh9i45c2',
      sync_status: 'synced'
    },
    {
      id: '003',
      name: 'workstation-05',
      ip_address: '192.168.1.205',
      os: 'windows',
      version: '4.11.2',
      status: 'disconnected',
      last_keep_alive: '2024-01-20T12:15:30Z',
      registration_date: '2024-01-10T14:30:00Z',
      groups: ['workstations', 'development'],
      node_name: 'wazuh-manager-worker-2',
      manager_host: '192.168.1.10',
      os_platform: 'windows',
      os_version: '10',
      config_sum: 'jk8m67n3',
      merged_sum: 'lp0q89r4',
      sync_status: 'not_synced'
    },
    {
      id: '004',
      name: 'web-server-02',
      ip_address: '192.168.1.102',
      os: 'ubuntu',
      version: '4.12.0',
      status: 'pending',
      last_keep_alive: '1970-01-01T00:00:00Z',
      registration_date: '2024-01-20T14:00:00Z',
      groups: ['web-servers', 'staging'],
      node_name: 'wazuh-manager-master',
      manager_host: '192.168.1.10',
      os_platform: 'ubuntu',
      os_version: '22.04',
      config_sum: 'st4u67v8',
      merged_sum: 'wx9y01z2',
      sync_status: 'not_synced'
    }
  ];

  const filteredAgents = React.useMemo(() => {
    return agents.filter(agent => {
      const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           agent.ip_address.includes(searchQuery) ||
                           agent.os.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || agent.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [agents, searchQuery, statusFilter]);

  const agentStats = React.useMemo(() => {
    const total = agents.length;
    const active = agents.filter(a => a.status === 'active').length;
    const disconnected = agents.filter(a => a.status === 'disconnected').length;
    const pending = agents.filter(a => a.status === 'pending').length;
    const never_connected = agents.filter(a => a.status === 'never_connected').length;
    
    return { total, active, disconnected, pending, never_connected };
  }, [agents]);

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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'disconnected':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'never_connected':
        return <WifiOff className="h-4 w-4 text-gray-500" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'online';
      case 'disconnected':
        return 'offline';
      case 'pending':
        return 'degraded';
      case 'never_connected':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getOSIcon = (os: string) => {
    switch (os.toLowerCase()) {
      case 'ubuntu':
      case 'debian':
      case 'centos':
      case 'rhel':
      case 'linux':
        return '🐧';
      case 'windows':
        return '🪟';
      case 'macos':
      case 'darwin':
        return '🍎';
      default:
        return '💻';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Agent Statistics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{agentStats.total}</div>
                <div className="text-sm text-muted-foreground">Total Agents</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-2xl font-bold text-green-600">{agentStats.active}</div>
                <div className="text-sm text-muted-foreground">Active</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <XCircle className="h-5 w-5 text-red-600" />
              <div>
                <div className="text-2xl font-bold text-red-600">{agentStats.disconnected}</div>
                <div className="text-sm text-muted-foreground">Disconnected</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="text-2xl font-bold text-yellow-600">{agentStats.pending}</div>
                <div className="text-sm text-muted-foreground">Pending</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">
                  {agentStats.total > 0 ? Math.round((agentStats.active / agentStats.total) * 100) : 0}%
                </div>
                <div className="text-sm text-muted-foreground">Uptime</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agent List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Monitor className="h-5 w-5" />
                <span>Agent Connectivity</span>
              </CardTitle>
              <CardDescription>Real-time agent status and connectivity monitoring</CardDescription>
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
                placeholder="Search agents by name, IP, or OS..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="disconnected">Disconnected</option>
                <option value="pending">Pending</option>
                <option value="never_connected">Never Connected</option>
              </select>
            </div>
          </div>

          {/* Agent Table */}
          <div className="space-y-2">
            {filteredAgents.map((agent) => (
              <div key={agent.id} className="p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{getOSIcon(agent.os)}</span>
                      {getStatusIcon(agent.status)}
                    </div>
                    <div>
                      <div className="font-semibold">{agent.name}</div>
                      <div className="text-sm text-muted-foreground">ID: {agent.id}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-6">
                    <div className="text-right">
                      <div className="text-sm font-medium">{agent.ip_address}</div>
                      <div className="text-sm text-muted-foreground">{agent.os_platform} {agent.os_version}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">v{agent.version}</div>
                      <div className="text-sm text-muted-foreground">{agent.node_name}</div>
                    </div>
                    <div className="text-right">
                      <Badge variant={getStatusBadge(agent.status)} className="mb-1">
                        {agent.status.replace('_', ' ')}
                      </Badge>
                      <div className="text-xs text-muted-foreground">
                        {agent.status === 'active' || agent.status === 'disconnected' 
                          ? formatDistanceToNow(new Date(agent.last_keep_alive), { addSuffix: true })
                          : 'Never connected'
                        }
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      <span>Groups: {agent.groups.join(', ')}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                      <Server className="h-3 w-3" />
                      <span>Registered: {formatDistanceToNow(new Date(agent.registration_date), { addSuffix: true })}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant={agent.sync_status === 'synced' ? 'online' : 'degraded'} className="text-xs">
                      {agent.sync_status === 'synced' ? (
                        <>
                          <Wifi className="h-3 w-3 mr-1" />
                          Synced
                        </>
                      ) : (
                        <>
                          <WifiOff className="h-3 w-3 mr-1" />
                          Not Synced
                        </>
                      )}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredAgents.length === 0 && (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No agents found</h3>
              <p className="text-muted-foreground">
                {searchQuery || statusFilter !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'No agents are currently registered with this manager'
                }
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <div>
              Showing {filteredAgents.length} of {agents.length} agents
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