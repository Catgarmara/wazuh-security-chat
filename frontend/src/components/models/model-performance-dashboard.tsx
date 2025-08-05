'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Zap, 
  TrendingUp, 
  TrendingDown,
  Clock,
  MemoryStick,
  Gauge,
  RefreshCw
} from 'lucide-react';
import { useModelManagement } from '@/hooks/use-model-management';
import { formatBytes } from '@/lib/utils';

interface PerformanceMetric {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  status?: 'good' | 'warning' | 'critical';
}

export function ModelPerformanceDashboard() {
  const { loadedModels, getTotalMemoryUsage, getModelMetrics } = useModelManagement();
  const [refreshKey, setRefreshKey] = React.useState(0);

  // Auto-refresh every 5 seconds
  React.useEffect(() => {
    const interval = setInterval(() => {
      setRefreshKey(prev => prev + 1);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const totalMemoryUsage = getTotalMemoryUsage();
  
  // Calculate aggregate metrics
  const aggregateMetrics = React.useMemo(() => {
    if (loadedModels.length === 0) return null;

    const totalTokensPerSecond = loadedModels.reduce((sum, model) => 
      sum + (model.performance_metrics?.tokens_per_second || 0), 0
    );
    
    const avgResponseTime = loadedModels.reduce((sum, model) => 
      sum + (model.performance_metrics?.response_time || 0), 0
    ) / loadedModels.length;

    return {
      totalTokensPerSecond,
      avgResponseTime,
      totalMemoryUsage,
      loadedModelCount: loadedModels.length
    };
  }, [loadedModels, totalMemoryUsage, refreshKey]);

  const performanceMetrics: PerformanceMetric[] = aggregateMetrics ? [
    {
      label: 'Total Throughput',
      value: aggregateMetrics.totalTokensPerSecond,
      unit: 'tok/s',
      trend: 'stable',
      status: aggregateMetrics.totalTokensPerSecond > 40 ? 'good' : 
              aggregateMetrics.totalTokensPerSecond > 20 ? 'warning' : 'critical'
    },
    {
      label: 'Avg Response Time',
      value: Math.round(aggregateMetrics.avgResponseTime),
      unit: 'ms',
      trend: 'stable',
      status: aggregateMetrics.avgResponseTime < 150 ? 'good' : 
              aggregateMetrics.avgResponseTime < 300 ? 'warning' : 'critical'
    },
    {
      label: 'Memory Usage',
      value: formatBytes(aggregateMetrics.totalMemoryUsage),
      trend: 'stable',
      status: aggregateMetrics.totalMemoryUsage < 8000000000 ? 'good' : 
              aggregateMetrics.totalMemoryUsage < 16000000000 ? 'warning' : 'critical'
    },
    {
      label: 'Active Models',
      value: aggregateMetrics.loadedModelCount,
      trend: 'stable',
      status: 'good'
    }
  ] : [];

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'good': return 'text-green-500';
      case 'warning': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      default: return 'text-muted-foreground';
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'good': return 'online';
      case 'warning': return 'degraded';
      case 'critical': return 'offline';
      default: return 'outline';
    }
  };

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="h-3 w-3 text-green-500" />;
      case 'down': return <TrendingDown className="h-3 w-3 text-red-500" />;
      default: return <Activity className="h-3 w-3 text-muted-foreground" />;
    }
  };

  if (loadedModels.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Gauge className="h-5 w-5" />
            <span>Model Performance</span>
          </CardTitle>
          <CardDescription>Real-time performance metrics for loaded AI models</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Cpu className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Models Loaded</h3>
            <p className="text-muted-foreground">
              Load an AI model to see performance metrics
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Aggregate Performance Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Gauge className="h-5 w-5" />
                <span>Performance Overview</span>
              </CardTitle>
              <CardDescription>System-wide AI model performance metrics</CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRefreshKey(prev => prev + 1)}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {performanceMetrics.map((metric, index) => (
              <div key={index} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">{metric.label}</span>
                  <div className="flex items-center space-x-1">
                    {getTrendIcon(metric.trend)}
                    <Badge variant={getStatusBadge(metric.status)} className="text-xs">
                      {metric.status}
                    </Badge>
                  </div>
                </div>
                <div className={`text-2xl font-bold ${getStatusColor(metric.status)}`}>
                  {metric.value}{metric.unit && <span className="text-sm ml-1">{metric.unit}</span>}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Individual Model Performance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Individual Model Metrics</span>
          </CardTitle>
          <CardDescription>Detailed performance metrics for each loaded model</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {loadedModels.map((model) => {
              const metrics = model.performance_metrics;
              if (!metrics) return null;

              return (
                <div key={model.id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold">{model.display_name}</h3>
                      <p className="text-sm text-muted-foreground">{model.description}</p>
                    </div>
                    <Badge variant="online" className="capitalize">
                      {model.specialized_for}
                    </Badge>
                  </div>

                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-md">
                        <Zap className="h-4 w-4 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Throughput</div>
                        <div className="font-semibold">
                          {metrics.tokens_per_second} <span className="text-sm">tok/s</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-green-100 dark:bg-green-900 rounded-md">
                        <Clock className="h-4 w-4 text-green-600" />
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Response Time</div>
                        <div className="font-semibold">
                          {metrics.response_time} <span className="text-sm">ms</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-md">
                        <MemoryStick className="h-4 w-4 text-purple-600" />
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Memory Usage</div>
                        <div className="font-semibold">
                          {formatBytes(metrics.memory_usage)}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Performance Bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">Performance Score</span>
                      <span className="text-xs font-mono">
                        {Math.round((metrics.tokens_per_second / 60) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min((metrics.tokens_per_second / 60) * 100, 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Capabilities */}
                  <div className="mt-4">
                    <div className="text-xs text-muted-foreground mb-2">Capabilities</div>
                    <div className="flex flex-wrap gap-1">
                      {model.capabilities.map((capability) => (
                        <Badge key={capability} variant="secondary" className="text-xs">
                          {capability}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Resource Usage Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <HardDrive className="h-5 w-5" />
            <span>Resource Utilization</span>
          </CardTitle>
          <CardDescription>Memory and compute resource usage breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {loadedModels.map((model, index) => {
              const metrics = model.performance_metrics;
              if (!metrics) return null;

              const memoryPercentage = (metrics.memory_usage / totalMemoryUsage) * 100;

              return (
                <div key={model.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{model.display_name}</span>
                    <span className="text-sm text-muted-foreground">
                      {formatBytes(metrics.memory_usage)} ({memoryPercentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        index === 0 ? 'bg-blue-500' :
                        index === 1 ? 'bg-green-500' :
                        index === 2 ? 'bg-purple-500' : 'bg-orange-500'
                      }`}
                      style={{ width: `${memoryPercentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}