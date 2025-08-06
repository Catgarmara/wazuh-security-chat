'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Search,
  Download,
  Star,
  Eye,
  Calendar,
  HardDrive,
  Cpu,
  Shield,
  Code,
  Brain,
  Filter,
  SortAsc,
  ExternalLink,
  CheckCircle,
  Clock
} from 'lucide-react';

interface HuggingFaceModel {
  id: string;
  name: string;
  displayName: string;
  author: string;
  description: string;
  category: 'security' | 'general' | 'code' | 'reasoning';
  size: string;
  sizeBytes: number;
  downloads: number;
  likes: number;
  lastModified: string;
  tags: string[];
  license: string;
  quantizations: Array<{
    type: string;
    size: string;
    description: string;
  }>;
  isInstalled: boolean;
  isDownloading: boolean;
  downloadProgress?: number;
}

const mockModels: HuggingFaceModel[] = [
  {
    id: 'microsoft/securitybert-base',
    name: 'securitybert-base',
    displayName: 'SecurityBERT Base',
    author: 'Microsoft',
    description: 'A specialized BERT model trained on security-related texts, optimized for threat detection and vulnerability analysis.',
    category: 'security',
    size: '1.2 GB',
    sizeBytes: 1200000000,
    downloads: 15420,
    likes: 89,
    lastModified: '2024-01-15',
    tags: ['security', 'threat-detection', 'bert', 'cybersecurity'],
    license: 'MIT',
    quantizations: [
      { type: 'Q4_0', size: '800 MB', description: 'Good quality, fast inference' },
      { type: 'Q5_0', size: '1.0 GB', description: 'Better quality, moderate speed' },
      { type: 'Q8_0', size: '1.2 GB', description: 'High quality, slower inference' }
    ],
    isInstalled: false,
    isDownloading: false
  },
  {
    id: 'meta-llama/llama-2-7b-chat-hf',
    name: 'llama-2-7b-chat',
    displayName: 'Llama 2 7B Chat',
    author: 'Meta',
    description: 'A fine-tuned version of Llama 2 7B optimized for dialogue and conversation, suitable for general security analysis tasks.',
    category: 'general',
    size: '13.5 GB',
    sizeBytes: 13500000000,
    downloads: 2847592,
    likes: 4521,
    lastModified: '2024-02-01',
    tags: ['llama2', 'chat', 'conversation', 'general-purpose'],
    license: 'Custom',
    quantizations: [
      { type: 'Q4_0', size: '3.8 GB', description: 'Good quality, fast inference' },
      { type: 'Q5_0', size: '4.6 GB', description: 'Better quality, moderate speed' },
      { type: 'Q8_0', size: '7.2 GB', description: 'High quality, slower inference' },
      { type: 'FP16', size: '13.5 GB', description: 'Original quality, requires more resources' }
    ],
    isInstalled: true,
    isDownloading: false
  },
  {
    id: 'codellama/codellama-7b-instruct-hf',
    name: 'codellama-7b-instruct',
    displayName: 'Code Llama 7B Instruct',
    author: 'Meta',
    description: 'Code Llama instruction-tuned model for code generation, analysis, and security code review tasks.',
    category: 'code',
    size: '13.5 GB',
    sizeBytes: 13500000000,
    downloads: 425789,
    likes: 892,
    lastModified: '2024-01-28',
    tags: ['code', 'llama2', 'instruct', 'security-review'],
    license: 'Custom',
    quantizations: [
      { type: 'Q4_0', size: '3.8 GB', description: 'Good quality, fast inference' },
      { type: 'Q5_0', size: '4.6 GB', description: 'Better quality, moderate speed' },
      { type: 'Q8_0', size: '7.2 GB', description: 'High quality, slower inference' }
    ],
    isInstalled: false,
    isDownloading: true,
    downloadProgress: 67
  },
  {
    id: 'mistralai/mistral-7b-instruct-v0.2',
    name: 'mistral-7b-instruct-v0.2',
    displayName: 'Mistral 7B Instruct v0.2',
    author: 'Mistral AI',
    description: 'Advanced instruction-following model with excellent reasoning capabilities for complex security analysis.',
    category: 'reasoning',
    size: '14.5 GB',
    sizeBytes: 14500000000,
    downloads: 1247893,
    likes: 2156,
    lastModified: '2024-02-10',
    tags: ['mistral', 'instruct', 'reasoning', 'analysis'],
    license: 'Apache 2.0',
    quantizations: [
      { type: 'Q4_0', size: '4.1 GB', description: 'Good quality, fast inference' },
      { type: 'Q5_0', size: '5.0 GB', description: 'Better quality, moderate speed' },
      { type: 'Q8_0', size: '7.7 GB', description: 'High quality, slower inference' }
    ],
    isInstalled: false,
    isDownloading: false
  }
];

export function ModelBrowser() {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all');
  const [selectedSize, setSelectedSize] = React.useState<string>('all');
  const [sortBy, setSortBy] = React.useState<string>('popularity');
  const [filteredModels, setFilteredModels] = React.useState<HuggingFaceModel[]>(mockModels);

  React.useEffect(() => {
    let filtered = mockModels;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(model => 
        model.displayName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        model.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        model.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
        model.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Apply category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(model => model.category === selectedCategory);
    }

    // Apply size filter
    if (selectedSize !== 'all') {
      const sizeMap = {
        'small': 5000000000,  // < 5GB
        'medium': 15000000000, // 5-15GB
        'large': 50000000000   // 15-50GB
      };
      
      if (selectedSize === 'small') {
        filtered = filtered.filter(model => model.sizeBytes < sizeMap.small);
      } else if (selectedSize === 'medium') {
        filtered = filtered.filter(model => 
          model.sizeBytes >= sizeMap.small && model.sizeBytes < sizeMap.medium
        );
      } else if (selectedSize === 'large') {
        filtered = filtered.filter(model => 
          model.sizeBytes >= sizeMap.medium && model.sizeBytes < sizeMap.large
        );
      }
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'popularity':
          return b.downloads - a.downloads;
        case 'likes':
          return b.likes - a.likes;
        case 'recent':
          return new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime();
        case 'size-asc':
          return a.sizeBytes - b.sizeBytes;
        case 'size-desc':
          return b.sizeBytes - a.sizeBytes;
        case 'name':
          return a.displayName.localeCompare(b.displayName);
        default:
          return 0;
      }
    });

    setFilteredModels(filtered);
  }, [searchQuery, selectedCategory, selectedSize, sortBy]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'security': return <Shield className="h-4 w-4" />;
      case 'code': return <Code className="h-4 w-4" />;
      case 'reasoning': return <Brain className="h-4 w-4" />;
      default: return <Cpu className="h-4 w-4" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'security': return 'bg-red-100 text-red-800 border-red-200';
      case 'code': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'reasoning': return 'bg-purple-100 text-purple-800 border-purple-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handleDownload = (model: HuggingFaceModel, quantization: string) => {
    console.log(`Downloading ${model.displayName} with ${quantization} quantization`);
    // Implement download logic
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Model Browser</h2>
          <p className="text-muted-foreground">
            Browse and download models from HuggingFace Hub
          </p>
        </div>
        <Button variant="outline" className="flex items-center space-x-2">
          <ExternalLink className="h-4 w-4" />
          <span>Open HuggingFace Hub</span>
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-wrap gap-4 p-4 bg-muted/50 rounded-lg">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
        
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="security">Security</SelectItem>
            <SelectItem value="general">General</SelectItem>
            <SelectItem value="code">Code</SelectItem>
            <SelectItem value="reasoning">Reasoning</SelectItem>
          </SelectContent>
        </Select>

        <Select value={selectedSize} onValueChange={setSelectedSize}>
          <SelectTrigger className="w-[140px]">
            <HardDrive className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Size" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sizes</SelectItem>
            <SelectItem value="small">Small (&lt; 5GB)</SelectItem>
            <SelectItem value="medium">Medium (5-15GB)</SelectItem>
            <SelectItem value="large">Large (15-50GB)</SelectItem>
          </SelectContent>
        </Select>

        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-[140px]">
            <SortAsc className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="popularity">Popularity</SelectItem>
            <SelectItem value="likes">Likes</SelectItem>
            <SelectItem value="recent">Recently Updated</SelectItem>
            <SelectItem value="size-asc">Size (Small to Large)</SelectItem>
            <SelectItem value="size-desc">Size (Large to Small)</SelectItem>
            <SelectItem value="name">Name</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Found {filteredModels.length} models
          </p>
        </div>

        <ScrollArea className="h-[600px]">
          <div className="space-y-4 pr-4">
            {filteredModels.map((model) => (
              <Card key={model.id} className="overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <CardTitle className="text-lg">{model.displayName}</CardTitle>
                        <Badge 
                          variant="outline" 
                          className={`flex items-center space-x-1 ${getCategoryColor(model.category)}`}
                        >
                          {getCategoryIcon(model.category)}
                          <span className="capitalize">{model.category}</span>
                        </Badge>
                        {model.isInstalled && (
                          <Badge variant="online" className="flex items-center space-x-1">
                            <CheckCircle className="h-3 w-3" />
                            <span>Installed</span>
                          </Badge>
                        )}
                        {model.isDownloading && (
                          <Badge variant="secondary" className="flex items-center space-x-1">
                            <Clock className="h-3 w-3 animate-pulse" />
                            <span>{model.downloadProgress}%</span>
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        by <span className="font-medium">{model.author}</span> • {model.size}
                      </p>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <div className="flex items-center space-x-1">
                        <Download className="h-4 w-4" />
                        <span>{formatNumber(model.downloads)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4" />
                        <span>{formatNumber(model.likes)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{new Date(model.lastModified).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <CardDescription className="text-sm">
                    {model.description}
                  </CardDescription>

                  <div className="flex flex-wrap gap-1">
                    {model.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  {/* Quantization Options */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Download Options</h4>
                    <div className="grid gap-2">
                      {model.quantizations.map((quant) => (
                        <div key={quant.type} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium text-sm">{quant.type}</div>
                            <div className="text-xs text-muted-foreground">
                              {quant.size} • {quant.description}
                            </div>
                          </div>
                          <Button
                            size="sm"
                            disabled={model.isInstalled || model.isDownloading}
                            onClick={() => handleDownload(model, quant.type)}
                          >
                            {model.isInstalled ? 'Installed' : 
                             model.isDownloading ? 'Downloading...' : 
                             'Download'}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="text-xs text-muted-foreground">
                      License: {model.license}
                    </div>
                    <Button variant="outline" size="sm" className="flex items-center space-x-1">
                      <Eye className="h-3 w-3" />
                      <span>View Details</span>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}