'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Bot, 
  ChevronDown, 
  Cpu, 
  HardDrive, 
  Zap,
  Download,
  Trash2,
  Settings,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowUpDown
} from 'lucide-react';
import { useChatStore } from '@/stores/chat';
import { useModelManagement } from '@/hooks/use-model-management';
import { formatBytes } from '@/lib/utils';

export function ModelSelector() {
  const { 
    availableModels, 
    loadedModels, 
    loadModel, 
    unloadModel, 
    hotSwapModel,
    isModelLoading, 
    isModelUnloading, 
    getLoadingProgress,
    getTotalMemoryUsage,
    getModelError,
    clearModelError
  } = useModelManagement();
  
  const [selectedModel, setSelectedModel] = React.useState<string | null>(null);
  const [isOpen, setIsOpen] = React.useState(false);
  const [showHotSwap, setShowHotSwap] = React.useState(false);

  // Mock data with enhanced features - replace with actual API integration
  const mockModels = React.useMemo(() => [
    {
      id: 'llama3-8b',
      name: 'llama3',
      display_name: 'Llama 3 8B',
      description: 'General purpose conversational AI model',
      size: '4.7GB',
      capabilities: ['chat', 'reasoning', 'code'],
      is_loaded: true,
      is_available: true,
      specialized_for: 'general' as const,
      performance_metrics: {
        tokens_per_second: 45,
        memory_usage: 4700000000,
        response_time: 120
      }
    },
    {
      id: 'security-llama-7b',
      name: 'security-llama',
      display_name: 'Security Llama 7B',
      description: 'Specialized for cybersecurity analysis and threat hunting',
      size: '3.8GB',
      capabilities: ['security', 'threat-analysis', 'incident-response'],
      is_loaded: false,
      is_available: true,
      specialized_for: 'security' as const,
      performance_metrics: {
        tokens_per_second: 38,
        memory_usage: 3800000000,
        response_time: 140
      }
    },
    {
      id: 'code-llama-13b',
      name: 'code-llama',
      display_name: 'Code Llama 13B',
      description: 'Specialized for code generation and analysis',
      size: '7.2GB',
      capabilities: ['code', 'debugging', 'documentation'],
      is_loaded: false,
      is_available: true,
      specialized_for: 'general' as const,
      performance_metrics: {
        tokens_per_second: 32,
        memory_usage: 7200000000,
        response_time: 180
      }
    }
  ], []);

  const currentModel = loadedModels.find(m => m.is_loaded) || mockModels.find(m => m.is_loaded) || mockModels[0];
  const totalMemoryUsage = getTotalMemoryUsage();

  const handleModelAction = async (modelId: string, action: 'load' | 'unload' | 'configure') => {
    const model = mockModels.find(m => m.id === modelId);
    if (!model) return;

    switch (action) {
      case 'load':
        await loadModel(modelId);
        break;
      case 'unload':
        await unloadModel(modelId);
        break;
      case 'configure':
        // Open configuration modal
        console.log('Configure model:', modelId);
        break;
    }
  };

  const handleHotSwap = async (fromModelId: string, toModelId: string) => {
    await hotSwapModel(fromModelId, toModelId);
    setShowHotSwap(false);
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="h-9 min-w-[240px] justify-between"
      >
        <div className="flex items-center space-x-2">
          <Bot className="h-4 w-4" />
          <span className="text-sm font-medium">{currentModel.display_name}</span>
          <Badge 
            variant={currentModel.is_loaded ? 'online' : 'outline'} 
            className="text-xs"
          >
            {currentModel.is_loaded ? 'Loaded' : 'Available'}
          </Badge>
          {isModelLoading(currentModel.id) && (
            <Loader2 className="h-3 w-3 animate-spin" />
          )}
        </div>
        <ChevronDown className="h-4 w-4 opacity-50" />
      </Button>

      {isOpen && (
        <div className="absolute top-full left-0 z-50 mt-1 w-[480px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md">
          {/* System Overview */}
          <div className="p-3 border-b">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm">System Status</h4>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowHotSwap(!showHotSwap)}
                className="h-6 text-xs"
              >
                <ArrowUpDown className="h-3 w-3 mr-1" />
                Hot Swap
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Memory</span>
                  <span className="font-mono">{formatBytes(totalMemoryUsage)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Loaded Models</span>
                  <span className="font-mono">{loadedModels.length}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Performance</span>
                  <span className="font-mono">
                    {currentModel.performance_metrics?.tokens_per_second || 0} tok/s
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Response Time</span>
                  <span className="font-mono">
                    {currentModel.performance_metrics?.response_time || 0}ms
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Current Model Details */}
          {currentModel.is_loaded && (
            <div className="p-3 border-b bg-accent/20">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-sm flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  Active Model
                </h4>
                <Badge variant="online" className="text-xs">
                  {currentModel.specialized_for}
                </Badge>
              </div>
              <div className="text-sm">
                <div className="font-medium">{currentModel.display_name}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {currentModel.description}
                </div>
                <div className="flex items-center space-x-3 mt-2">
                  {currentModel.capabilities.map((cap) => (
                    <span key={cap} className="text-xs text-muted-foreground capitalize">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Model List */}
          <div className="p-3">
            <h4 className="font-medium text-sm mb-2">Available Models</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {mockModels.map((model) => {
                const loading = isModelLoading(model.id);
                const unloading = isModelUnloading(model.id);
                const progress = getLoadingProgress(model.id);
                const error = getModelError(model.id);

                return (
                  <div
                    key={model.id}
                    className={`p-3 rounded-md border transition-colors ${
                      model.is_loaded ? 'bg-accent/30 border-accent' : 'hover:bg-accent/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-sm font-medium truncate">
                            {model.display_name}
                          </span>
                          <Badge 
                            variant={model.is_loaded ? 'online' : 'outline'}
                            className="text-xs flex-shrink-0"
                          >
                            {model.is_loaded ? 'Loaded' : model.size}
                          </Badge>
                          {(loading || unloading) && (
                            <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                          )}
                        </div>
                        
                        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                          {model.description}
                        </p>
                        
                        <div className="flex items-center space-x-3 mb-2">
                          {model.capabilities.slice(0, 3).map((cap) => (
                            <span key={cap} className="text-xs text-muted-foreground capitalize">
                              {cap}
                            </span>
                          ))}
                          {model.capabilities.length > 3 && (
                            <span className="text-xs text-muted-foreground">
                              +{model.capabilities.length - 3} more
                            </span>
                          )}
                        </div>

                        {/* Loading Progress */}
                        {loading && (
                          <div className="mb-2">
                            <div className="text-xs text-muted-foreground mb-1">
                              Loading... {progress}%
                            </div>
                            <div className="w-full bg-secondary rounded-full h-1">
                              <div
                                className="bg-blue-500 h-1 rounded-full transition-all"
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Error Display */}
                        {error && (
                          <div className="flex items-center space-x-2 mb-2 text-xs text-red-500">
                            <AlertCircle className="h-3 w-3" />
                            <span>{error}</span>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => clearModelError(model.id)}
                              className="h-4 w-4 p-0 text-red-500 hover:text-red-700"
                            >
                              ×
                            </Button>
                          </div>
                        )}

                        {/* Performance Metrics for Loaded Models */}
                        {model.is_loaded && model.performance_metrics && (
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div>
                              <div className="text-muted-foreground">Speed</div>
                              <div className="font-mono">
                                {model.performance_metrics.tokens_per_second} tok/s
                              </div>
                            </div>
                            <div>
                              <div className="text-muted-foreground">Memory</div>
                              <div className="font-mono">
                                {formatBytes(model.performance_metrics.memory_usage)}
                              </div>
                            </div>
                            <div>
                              <div className="text-muted-foreground">Latency</div>
                              <div className="font-mono">
                                {model.performance_metrics.response_time}ms
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center space-x-1 ml-3">
                        {model.is_loaded ? (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            onClick={() => handleModelAction(model.id, 'unload')}
                            disabled={unloading}
                            className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                            title="Unload Model"
                          >
                            {unloading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        ) : (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            onClick={() => handleModelAction(model.id, 'load')}
                            disabled={loading}
                            className="h-8 w-8 p-0 text-green-500 hover:text-green-700"
                            title="Load Model"
                          >
                            {loading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Download className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleModelAction(model.id, 'configure')}
                          className="h-8 w-8 p-0"
                          title="Configure Model"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Hot Swap Interface */}
          {showHotSwap && loadedModels.length > 0 && (
            <div className="p-3 border-t bg-accent/10">
              <h4 className="font-medium text-sm mb-2">Hot Swap Models</h4>
              <div className="text-xs text-muted-foreground mb-2">
                Switch models without interrupting conversations
              </div>
              <div className="space-y-2">
                {mockModels.filter(m => !m.is_loaded).map((model) => (
                  <Button
                    key={model.id}
                    size="sm"
                    variant="outline"
                    onClick={() => handleHotSwap(currentModel.id, model.id)}
                    className="w-full justify-start text-xs"
                  >
                    <ArrowUpDown className="h-3 w-3 mr-2" />
                    Swap to {model.display_name}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}