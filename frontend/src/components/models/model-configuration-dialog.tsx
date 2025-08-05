'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Settings,
  X,
  Save,
  RotateCcw,
  Sliders,
  Cpu,
  MemoryStick,
  Thermometer,
  Zap,
  Info
} from 'lucide-react';
import { AIModel } from '@/types';
import { formatBytes } from '@/lib/utils';

interface ModelConfigurationDialogProps {
  model: AIModel;
  isOpen: boolean;
  onClose: () => void;
  onSave: (modelId: string, configuration: ModelConfiguration) => void;
}

interface ModelConfiguration {
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  context_length: number;
  gpu_layers: number;
  threads: number;
  batch_size: number;
  rope_freq_base: number;
  rope_freq_scale: number;
}

const defaultConfiguration: ModelConfiguration = {
  temperature: 0.7,
  max_tokens: 2048,
  top_p: 0.9,
  frequency_penalty: 0.0,
  presence_penalty: 0.0,
  context_length: 4096,
  gpu_layers: -1,
  threads: 4,
  batch_size: 512,
  rope_freq_base: 10000,
  rope_freq_scale: 1.0,
};

const configurationPresets = {
  'creative': {
    name: 'Creative Writing',
    description: 'High creativity for creative tasks',
    config: { ...defaultConfiguration, temperature: 0.9, top_p: 0.95 }
  },
  'balanced': {
    name: 'Balanced',
    description: 'Good balance of creativity and consistency',
    config: { ...defaultConfiguration, temperature: 0.7, top_p: 0.9 }
  },
  'precise': {
    name: 'Precise',
    description: 'Low creativity for factual, consistent responses',
    config: { ...defaultConfiguration, temperature: 0.3, top_p: 0.8 }
  },
  'security': {
    name: 'Security Analysis',
    description: 'Optimized for security and threat analysis',
    config: { ...defaultConfiguration, temperature: 0.4, max_tokens: 4096, context_length: 8192 }
  },
  'code': {
    name: 'Code Generation',
    description: 'Optimized for code generation and debugging',
    config: { ...defaultConfiguration, temperature: 0.2, max_tokens: 4096, context_length: 8192 }
  }
};

export function ModelConfigurationDialog({ 
  model, 
  isOpen, 
  onClose, 
  onSave 
}: ModelConfigurationDialogProps) {
  const [config, setConfig] = React.useState<ModelConfiguration>(defaultConfiguration);
  const [selectedPreset, setSelectedPreset] = React.useState<string>('balanced');
  const [hasChanges, setHasChanges] = React.useState(false);

  React.useEffect(() => {
    if (isOpen) {
      // Load existing configuration or use defaults
      setConfig(defaultConfiguration);
      setSelectedPreset('balanced');
      setHasChanges(false);
    }
  }, [isOpen]);

  const handleConfigChange = (key: keyof ModelConfiguration, value: number) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setSelectedPreset(''); // Clear preset selection when manually changing values
  };

  const handlePresetSelect = (presetKey: string) => {
    const preset = configurationPresets[presetKey as keyof typeof configurationPresets];
    if (preset) {
      setConfig(preset.config);
      setSelectedPreset(presetKey);
      setHasChanges(true);
    }
  };

  const handleSave = () => {
    onSave(model.id, config);
    setHasChanges(false);
    onClose();
  };

  const handleReset = () => {
    setConfig(defaultConfiguration);
    setSelectedPreset('balanced');
    setHasChanges(true);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background border rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Configure {model.display_name}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Adjust model parameters for optimal performance
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-6 space-y-6">
          {/* Model Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Model Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-sm text-muted-foreground">Model</div>
                  <div className="font-medium">{model.display_name}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Specialization</div>
                  <Badge variant="secondary" className="capitalize">
                    {model.specialized_for}
                  </Badge>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Size</div>
                  <div className="font-medium">{model.size}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Status</div>
                  <Badge variant={model.is_loaded ? 'online' : 'outline'}>
                    {model.is_loaded ? 'Loaded' : 'Available'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Configuration Presets */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Presets</CardTitle>
              <CardDescription>
                Choose a preset configuration optimized for specific use cases
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {Object.entries(configurationPresets).map(([key, preset]) => (
                  <Button
                    key={key}
                    variant={selectedPreset === key ? "default" : "outline"}
                    onClick={() => handlePresetSelect(key)}
                    className="h-auto p-3 text-left justify-start"
                  >
                    <div>
                      <div className="font-medium">{preset.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {preset.description}
                      </div>
                    </div>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Generation Parameters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Sliders className="h-5 w-5 mr-2" />
                Generation Parameters
              </CardTitle>
              <CardDescription>
                Control how the model generates responses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Temperature</label>
                      <span className="text-sm text-muted-foreground">{config.temperature}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={config.temperature}
                      onChange={(e) => handleConfigChange('temperature', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="text-xs text-muted-foreground">
                      Controls randomness: 0 = deterministic, 2 = very random
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Top P</label>
                      <span className="text-sm text-muted-foreground">{config.top_p}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={config.top_p}
                      onChange={(e) => handleConfigChange('top_p', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="text-xs text-muted-foreground">
                      Nucleus sampling: considers top P% of probable tokens
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Max Tokens</label>
                      <Input
                        type="number"
                        value={config.max_tokens}
                        onChange={(e) => handleConfigChange('max_tokens', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="1"
                        max="8192"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Maximum tokens in response (1-8192)
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Frequency Penalty</label>
                      <span className="text-sm text-muted-foreground">{config.frequency_penalty}</span>
                    </div>
                    <input
                      type="range"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={config.frequency_penalty}
                      onChange={(e) => handleConfigChange('frequency_penalty', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="text-xs text-muted-foreground">
                      Reduces repetition based on frequency
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Presence Penalty</label>
                      <span className="text-sm text-muted-foreground">{config.presence_penalty}</span>
                    </div>
                    <input
                      type="range"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={config.presence_penalty}
                      onChange={(e) => handleConfigChange('presence_penalty', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="text-xs text-muted-foreground">
                      Encourages new topics and ideas
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Context Length</label>
                      <Input
                        type="number"
                        value={config.context_length}
                        onChange={(e) => handleConfigChange('context_length', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="512"
                        max="32768"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Maximum context window size
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Performance Parameters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Cpu className="h-5 w-5 mr-2" />
                Performance Parameters
              </CardTitle>
              <CardDescription>
                Optimize model loading and inference performance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">GPU Layers</label>
                      <Input
                        type="number"
                        value={config.gpu_layers}
                        onChange={(e) => handleConfigChange('gpu_layers', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="-1"
                        max="100"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Number of layers to run on GPU (-1 = auto)
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">CPU Threads</label>
                      <Input
                        type="number"
                        value={config.threads}
                        onChange={(e) => handleConfigChange('threads', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="1"
                        max="32"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Number of CPU threads for inference
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">Batch Size</label>
                      <Input
                        type="number"
                        value={config.batch_size}
                        onChange={(e) => handleConfigChange('batch_size', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="1"
                        max="2048"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Batch size for parallel processing
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">RoPE Frequency Base</label>
                      <Input
                        type="number"
                        value={config.rope_freq_base}
                        onChange={(e) => handleConfigChange('rope_freq_base', parseInt(e.target.value))}
                        className="w-20 h-6 text-xs"
                        min="1000"
                        max="100000"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      RoPE frequency base for positional encoding
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Performance Impact */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Info className="h-5 w-5 mr-2" />
                Performance Impact
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-md">
                    <MemoryStick className="h-4 w-4 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Est. Memory</div>
                    <div className="font-semibold">
                      {formatBytes((config.context_length / 1000) * 1000000000)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-green-100 dark:bg-green-900 rounded-md">
                    <Zap className="h-4 w-4 text-green-600" />
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Est. Speed</div>
                    <div className="font-semibold">
                      {Math.round(50 * (config.gpu_layers === -1 ? 1.5 : config.gpu_layers > 0 ? 1.3 : 1.0))} tok/s
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-md">
                    <Thermometer className="h-4 w-4 text-orange-600" />
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Quality</div>
                    <div className="font-semibold">
                      {config.temperature < 0.5 ? 'Precise' : 
                       config.temperature < 1.0 ? 'Balanced' : 'Creative'}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-muted/20">
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={handleReset}>
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset to Defaults
            </Button>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!hasChanges}>
              <Save className="h-4 w-4 mr-2" />
              Save Configuration
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}