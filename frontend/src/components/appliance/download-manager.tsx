'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Download,
  Pause,
  Play,
  X,
  CheckCircle,
  Clock,
  AlertCircle,
  RotateCcw,
  Trash2,
  HardDrive,
  Wifi,
  Settings
} from 'lucide-react';

interface DownloadItem {
  id: string;
  modelName: string;
  modelId: string;
  author: string;
  quantization: string;
  size: string;
  sizeBytes: number;
  status: 'downloading' | 'paused' | 'completed' | 'failed' | 'queued';
  progress: number;
  downloadSpeed: string;
  eta: string;
  downloadedBytes: number;
  priority: 'high' | 'normal' | 'low';
  startTime: string;
  completedTime?: string;
  error?: string;
}

const mockDownloads: DownloadItem[] = [
  {
    id: 'dl-001',
    modelName: 'Code Llama 7B Instruct',
    modelId: 'codellama/codellama-7b-instruct-hf',
    author: 'Meta',
    quantization: 'Q4_0',
    size: '3.8 GB',
    sizeBytes: 3800000000,
    status: 'downloading',
    progress: 67,
    downloadSpeed: '45.2 MB/s',
    eta: '12 min',
    downloadedBytes: 2546000000,
    priority: 'high',
    startTime: '2024-01-15T10:30:00Z'
  },
  {
    id: 'dl-002',
    modelName: 'Security BERT Base',
    modelId: 'microsoft/securitybert-base',
    author: 'Microsoft',
    quantization: 'Q5_0',
    size: '1.0 GB',
    sizeBytes: 1000000000,
    status: 'queued',
    progress: 0,
    downloadSpeed: '0 MB/s',
    eta: 'Waiting...',
    downloadedBytes: 0,
    priority: 'normal',
    startTime: '2024-01-15T11:00:00Z'
  },
  {
    id: 'dl-003',
    modelName: 'Mistral 7B Instruct v0.2',
    modelId: 'mistralai/mistral-7b-instruct-v0.2',
    author: 'Mistral AI',
    quantization: 'Q8_0',
    size: '7.7 GB',
    sizeBytes: 7700000000,
    status: 'completed',
    progress: 100,
    downloadSpeed: '0 MB/s',
    eta: 'Completed',
    downloadedBytes: 7700000000,
    priority: 'normal',
    startTime: '2024-01-15T09:00:00Z',
    completedTime: '2024-01-15T09:45:00Z'
  },
  {
    id: 'dl-004',
    modelName: 'Llama 2 13B Chat',
    modelId: 'meta-llama/llama-2-13b-chat-hf',
    author: 'Meta',
    quantization: 'Q4_0',
    size: '7.3 GB',
    sizeBytes: 7300000000,
    status: 'failed',
    progress: 23,
    downloadSpeed: '0 MB/s',
    eta: 'Failed',
    downloadedBytes: 1679000000,
    priority: 'low',
    startTime: '2024-01-15T08:00:00Z',
    error: 'Network timeout after multiple retries'
  }
];

export function DownloadManager() {
  const [downloads, setDownloads] = React.useState<DownloadItem[]>(mockDownloads);
  const [selectedTab, setSelectedTab] = React.useState('active');

  // Filter downloads by status
  const activeDownloads = downloads.filter(d => d.status === 'downloading' || d.status === 'queued');
  const completedDownloads = downloads.filter(d => d.status === 'completed');
  const failedDownloads = downloads.filter(d => d.status === 'failed');

  // Calculate total stats
  const totalDownloaded = downloads.reduce((sum, d) => sum + d.downloadedBytes, 0);
  const activeDownloadCount = activeDownloads.length;
  const currentSpeed = downloads
    .filter(d => d.status === 'downloading')
    .reduce((sum, d) => sum + parseFloat(d.downloadSpeed.replace(' MB/s', '')), 0);

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatTime = (timeString: string) => {
    return new Date(timeString).toLocaleTimeString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'downloading': return 'text-blue-600';
      case 'completed': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'paused': return 'text-yellow-600';
      case 'queued': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'downloading': return <Download className="h-4 w-4 text-blue-600" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed': return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'paused': return <Pause className="h-4 w-4 text-yellow-600" />;
      case 'queued': return <Clock className="h-4 w-4 text-gray-600" />;
      default: return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'normal': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'low': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handlePause = (id: string) => {
    setDownloads(prev => prev.map(d => 
      d.id === id && d.status === 'downloading' 
        ? { ...d, status: 'paused', downloadSpeed: '0 MB/s', eta: 'Paused' }
        : d
    ));
  };

  const handleResume = (id: string) => {
    setDownloads(prev => prev.map(d => 
      d.id === id && d.status === 'paused' 
        ? { ...d, status: 'downloading', downloadSpeed: '45.2 MB/s', eta: '12 min' }
        : d
    ));
  };

  const handleCancel = (id: string) => {
    setDownloads(prev => prev.filter(d => d.id !== id));
  };

  const handleRetry = (id: string) => {
    setDownloads(prev => prev.map(d => 
      d.id === id && d.status === 'failed' 
        ? { ...d, status: 'downloading', progress: 0, downloadedBytes: 0, error: undefined }
        : d
    ));
  };

  const handleClearCompleted = () => {
    setDownloads(prev => prev.filter(d => d.status !== 'completed'));
  };

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Download Manager</h2>
          <p className="text-muted-foreground">
            Manage model downloads and queue
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-sm font-medium">Current Speed</div>
            <div className="text-2xl font-bold text-blue-600">{currentSpeed.toFixed(1)} MB/s</div>
          </div>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Download className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium">Active Downloads</p>
                <p className="text-2xl font-bold">{activeDownloadCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">Completed</p>
                <p className="text-2xl font-bold">{completedDownloads.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <HardDrive className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium">Total Downloaded</p>
                <p className="text-2xl font-bold">{formatBytes(totalDownloaded)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Wifi className="h-5 w-5 text-orange-600" />
              <div>
                <p className="text-sm font-medium">Network Usage</p>
                <p className="text-2xl font-bold">87%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Downloads List */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="active" className="flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>Active ({activeDownloads.length})</span>
            </TabsTrigger>
            <TabsTrigger value="completed" className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4" />
              <span>Completed ({completedDownloads.length})</span>
            </TabsTrigger>
            <TabsTrigger value="failed" className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4" />
              <span>Failed ({failedDownloads.length})</span>
            </TabsTrigger>
          </TabsList>

          {selectedTab === 'completed' && completedDownloads.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleClearCompleted}>
              <Trash2 className="h-4 w-4 mr-2" />
              Clear Completed
            </Button>
          )}
        </div>

        <TabsContent value="active" className="space-y-4">
          <ScrollArea className="h-[500px]">
            <div className="space-y-3 pr-4">
              {activeDownloads.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-8">
                    <Download className="h-12 w-12 text-muted-foreground mb-2" />
                    <p className="text-lg font-medium">No active downloads</p>
                    <p className="text-muted-foreground">Browse models to start downloading</p>
                  </CardContent>
                </Card>
              ) : (
                activeDownloads.map((download) => (
                  <Card key={download.id}>
                    <CardContent className="p-4">
                      <div className="space-y-4">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              {getStatusIcon(download.status)}
                              <h3 className="font-semibold">{download.modelName}</h3>
                              <Badge variant="outline" className={getPriorityColor(download.priority)}>
                                {download.priority}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {download.author} • {download.quantization} • {download.size}
                            </p>
                          </div>
                          
                          <div className="flex items-center space-x-1">
                            {download.status === 'downloading' && (
                              <Button size="sm" variant="outline" onClick={() => handlePause(download.id)}>
                                <Pause className="h-3 w-3" />
                              </Button>
                            )}
                            {download.status === 'paused' && (
                              <Button size="sm" variant="outline" onClick={() => handleResume(download.id)}>
                                <Play className="h-3 w-3" />
                              </Button>
                            )}
                            <Button 
                              size="sm" 
                              variant="outline" 
                              onClick={() => handleCancel(download.id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className={getStatusColor(download.status)}>
                              {download.status === 'queued' ? 'Waiting in queue' : 
                               download.status === 'downloading' ? `${download.progress}% • ${download.downloadSpeed}` :
                               download.status === 'paused' ? 'Paused' : 'Unknown'}
                            </span>
                            <span className="text-muted-foreground">
                              {download.status === 'downloading' ? `ETA: ${download.eta}` : 
                               download.status === 'queued' ? `Started: ${formatTime(download.startTime)}` : ''}
                            </span>
                          </div>
                          
                          <Progress 
                            value={download.progress}
                            className="h-2"
                            indicatorClassName={
                              download.status === 'downloading' ? 'bg-blue-500' :
                              download.status === 'paused' ? 'bg-yellow-500' :
                              'bg-gray-500'
                            }
                          />
                          
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>{formatBytes(download.downloadedBytes)} / {download.size}</span>
                            <span>{download.modelId}</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="completed" className="space-y-4">
          <ScrollArea className="h-[500px]">
            <div className="space-y-3 pr-4">
              {completedDownloads.map((download) => (
                <Card key={download.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <h3 className="font-semibold">{download.modelName}</h3>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {download.author} • {download.quantization} • {download.size}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Completed at {formatTime(download.completedTime!)}
                        </p>
                      </div>
                      
                      <div className="text-right">
                        <Badge variant="online">Installed</Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatBytes(download.sizeBytes)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="failed" className="space-y-4">
          <ScrollArea className="h-[500px]">
            <div className="space-y-3 pr-4">
              {failedDownloads.map((download) => (
                <Card key={download.id} className="border-red-200">
                  <CardContent className="p-4">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                            <h3 className="font-semibold">{download.modelName}</h3>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {download.author} • {download.quantization} • {download.size}
                          </p>
                          <p className="text-sm text-red-600">
                            Failed at {download.progress}% • {download.error}
                          </p>
                        </div>
                        
                        <div className="flex items-center space-x-1">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => handleRetry(download.id)}
                            className="text-blue-600 hover:text-blue-700"
                          >
                            <RotateCcw className="h-3 w-3 mr-1" />
                            Retry
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => handleCancel(download.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>

                      <Progress 
                        value={download.progress}
                        className="h-2"
                        indicatorClassName="bg-red-500"
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}