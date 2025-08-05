'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Workflow, 
  Play, 
  Pause, 
  CheckCircle, 
  XCircle, 
  Clock, 
  User, 
  FileText,
  AlertTriangle,
  Eye,
  ArrowRight,
  RotateCcw,
  Tag,
  MessageSquare,
  History,
  Settings,
  Filter,
  Search
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface AlertManagementWorkflowsProps {
  className?: string;
  onWorkflowAction?: (workflowId: string, action: string) => void;
}

type WorkflowStatus = 'active' | 'paused' | 'completed' | 'failed';
type AlertAction = 'investigate' | 'escalate' | 'contain' | 'resolve' | 'dismiss';

interface WorkflowStep {
  id: string;
  name: string;
  description: string;
  action: AlertAction;
  automated: boolean;
  required: boolean;
  estimated_time: number; // minutes
  assigned_to?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';
  completed_at?: string;
  notes?: string;
}

interface AlertWorkflow {
  id: string;
  name: string;
  description: string;
  alert_id: string;
  alert_title: string;
  alert_severity: 'critical' | 'high' | 'medium' | 'low';
  status: WorkflowStatus;
  created_at: string;
  updated_at: string;
  created_by: string;
  assigned_to?: string;
  priority: number;
  estimated_completion: string;
  actual_completion?: string;
  steps: WorkflowStep[];
  tags: string[];
  comments: Array<{
    id: string;
    user: string;
    message: string;
    timestamp: string;
  }>;
}

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  severity_filter: string[];
  auto_trigger: boolean;
  steps: Omit<WorkflowStep, 'id' | 'status' | 'completed_at' | 'notes'>[];
}

export function AlertManagementWorkflows({ className, onWorkflowAction }: AlertManagementWorkflowsProps) {
  const [workflows, setWorkflows] = React.useState<AlertWorkflow[]>([]);
  const [templates, setTemplates] = React.useState<WorkflowTemplate[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = React.useState<AlertWorkflow | null>(null);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [newComment, setNewComment] = React.useState('');

  // Mock workflow data - replace with actual API integration
  const mockWorkflows: AlertWorkflow[] = [
    {
      id: 'workflow-001',
      name: 'Critical Malware Investigation',
      description: 'Comprehensive investigation workflow for critical malware alerts',
      alert_id: 'alert-001',
      alert_title: 'Suspicious process execution detected',
      alert_severity: 'critical',
      status: 'active',
      created_at: '2024-01-20T14:45:00Z',
      updated_at: '2024-01-20T14:50:00Z',
      created_by: 'system',
      assigned_to: 'john.doe',
      priority: 1,
      estimated_completion: '2024-01-20T16:45:00Z',
      tags: ['malware', 'investigation', 'workstation'],
      comments: [
        {
          id: 'comment-001',
          user: 'john.doe',
          message: 'Initial investigation shows potential Cobalt Strike beacon activity',
          timestamp: '2024-01-20T14:48:00Z'
        }
      ],
      steps: [
        {
          id: 'step-001',
          name: 'Initial Alert Triage',
          description: 'Review alert details and assess severity',
          action: 'investigate',
          automated: false,
          required: true,
          estimated_time: 15,
          assigned_to: 'john.doe',
          status: 'completed',
          completed_at: '2024-01-20T14:47:00Z',
          notes: 'Alert verified as legitimate threat'
        },
        {
          id: 'step-002',
          name: 'Isolate Affected System',
          description: 'Isolate the affected workstation from network',
          action: 'contain',
          automated: true,
          required: true,
          estimated_time: 5,
          status: 'in_progress'
        },
        {
          id: 'step-003',
          name: 'Collect Forensic Evidence',
          description: 'Gather memory dump and system artifacts',
          action: 'investigate',
          automated: false,
          required: true,
          estimated_time: 45,
          assigned_to: 'forensics.team',
          status: 'pending'
        },
        {
          id: 'step-004',
          name: 'Malware Analysis',
          description: 'Analyze collected samples for IOCs',
          action: 'investigate',
          automated: false,
          required: true,
          estimated_time: 60,
          assigned_to: 'malware.analyst',
          status: 'pending'
        },
        {
          id: 'step-005',
          name: 'Threat Hunting',
          description: 'Hunt for similar threats across environment',
          action: 'investigate',
          automated: false,
          required: false,
          estimated_time: 90,
          status: 'pending'
        },
        {
          id: 'step-006',
          name: 'System Remediation',
          description: 'Clean and restore affected systems',
          action: 'resolve',
          automated: false,
          required: true,
          estimated_time: 30,
          status: 'pending'
        }
      ]
    },
    {
      id: 'workflow-002',
      name: 'Failed Authentication Response',
      description: 'Standard response workflow for authentication failures',
      alert_id: 'alert-002',
      alert_title: 'Multiple failed login attempts',
      alert_severity: 'high',
      status: 'completed',
      created_at: '2024-01-20T14:30:00Z',
      updated_at: '2024-01-20T14:45:00Z',
      created_by: 'system',
      assigned_to: 'security.team',
      priority: 2,
      estimated_completion: '2024-01-20T15:00:00Z',
      actual_completion: '2024-01-20T14:45:00Z',
      tags: ['authentication', 'brute-force', 'automated'],
      comments: [],
      steps: [
        {
          id: 'step-101',
          name: 'Block Source IP',
          description: 'Automatically block the attacking IP address',
          action: 'contain',
          automated: true,
          required: true,
          estimated_time: 1,
          status: 'completed',
          completed_at: '2024-01-20T14:31:00Z'
        },
        {
          id: 'step-102',
          name: 'Notify Security Team',
          description: 'Send notification to security team',
          action: 'escalate',
          automated: true,
          required: true,
          estimated_time: 1,
          status: 'completed',
          completed_at: '2024-01-20T14:31:00Z'
        },
        {
          id: 'step-103',
          name: 'Review Account Status',
          description: 'Check if targeted account needs protection',
          action: 'investigate',
          automated: false,
          required: true,
          estimated_time: 10,
          assigned_to: 'security.team',
          status: 'completed',
          completed_at: '2024-01-20T14:40:00Z',
          notes: 'Account locked as precaution'
        },
        {
          id: 'step-104',
          name: 'Generate Report',
          description: 'Create incident report for records',
          action: 'resolve',
          automated: true,
          required: true,
          estimated_time: 5,
          status: 'completed',
          completed_at: '2024-01-20T14:45:00Z'
        }
      ]
    }
  ];

  const mockTemplates: WorkflowTemplate[] = [
    {
      id: 'template-001',
      name: 'Critical Malware Response',
      description: 'Standard workflow for critical malware alerts',
      category: 'Malware',
      severity_filter: ['critical'],
      auto_trigger: true,
      steps: [
        {
          name: 'Initial Alert Triage',
          description: 'Review alert details and assess severity',
          action: 'investigate',
          automated: false,
          required: true,
          estimated_time: 15
        },
        {
          name: 'Isolate Affected System',
          description: 'Isolate the affected system from network',
          action: 'contain',
          automated: true,
          required: true,
          estimated_time: 5
        }
      ]
    }
  ];

  React.useEffect(() => {
    setWorkflows(mockWorkflows);
    setTemplates(mockTemplates);
  }, []);

  const filteredWorkflows = React.useMemo(() => {
    return workflows.filter(workflow => {
      const matchesSearch = !searchQuery || 
        workflow.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        workflow.alert_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        workflow.assigned_to?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || workflow.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [workflows, searchQuery, statusFilter]);

  const handleStepAction = (workflowId: string, stepId: string, action: 'start' | 'complete' | 'skip') => {
    setWorkflows(prev => prev.map(workflow => {
      if (workflow.id === workflowId) {
        const updatedSteps = workflow.steps.map(step => {
          if (step.id === stepId) {
            switch (action) {
              case 'start':
                return { ...step, status: 'in_progress' as const };
              case 'complete':
                return { 
                  ...step, 
                  status: 'completed' as const, 
                  completed_at: new Date().toISOString() 
                };
              case 'skip':
                return { ...step, status: 'skipped' as const };
              default:
                return step;
            }
          }
          return step;
        });

        const allCompleted = updatedSteps.every(step => 
          step.status === 'completed' || step.status === 'skipped' || !step.required
        );

        return {
          ...workflow,
          steps: updatedSteps,
          status: allCompleted ? 'completed' as const : workflow.status,
          actual_completion: allCompleted ? new Date().toISOString() : workflow.actual_completion,
          updated_at: new Date().toISOString()
        };
      }
      return workflow;
    }));

    onWorkflowAction?.(workflowId, action);
  };

  const handleAddComment = (workflowId: string) => {
    if (!newComment.trim()) return;

    setWorkflows(prev => prev.map(workflow => {
      if (workflow.id === workflowId) {
        return {
          ...workflow,
          comments: [...workflow.comments, {
            id: `comment-${Date.now()}`,
            user: 'current.user',
            message: newComment,
            timestamp: new Date().toISOString()
          }],
          updated_at: new Date().toISOString()
        };
      }
      return workflow;
    }));

    setNewComment('');
  };

  const getStatusBadge = (status: WorkflowStatus) => {
    switch (status) {
      case 'active':
        return 'online';
      case 'paused':
        return 'degraded';
      case 'completed':
        return 'info';
      case 'failed':
        return 'critical';
    }
  };

  const getStepStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'online';
      case 'in_progress':
        return 'degraded';
      case 'failed':
        return 'critical';
      case 'skipped':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
      default:
        return 'outline';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Alert Management Workflows</h2>
          <p className="text-muted-foreground">Automated and manual incident response workflows</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Templates
          </Button>
          <Button variant="default" size="sm">
            <Play className="h-4 w-4 mr-2" />
            New Workflow
          </Button>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search workflows by name, alert, or assignee..."
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
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Workflows List */}
      <div className="space-y-4">
        {filteredWorkflows.map((workflow) => (
          <Card key={workflow.id} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Workflow className="h-5 w-5 text-blue-600" />
                  <div>
                    <CardTitle className="text-lg">{workflow.name}</CardTitle>
                    <CardDescription>{workflow.description}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={getSeverityBadge(workflow.alert_severity)} className="text-xs">
                    {workflow.alert_severity.toUpperCase()}
                  </Badge>
                  <Badge variant={getStatusBadge(workflow.status)} className="text-xs">
                    {workflow.status.toUpperCase()}
                  </Badge>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              <div className="space-y-4">
                {/* Workflow Info */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 text-sm">
                  <div className="flex items-center space-x-1">
                    <AlertTriangle className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Alert:</span>
                    <span className="font-medium">{workflow.alert_title}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <User className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Assigned:</span>
                    <span className="font-medium">{workflow.assigned_to || 'Unassigned'}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Created:</span>
                    <span className="font-medium">{formatDistanceToNow(new Date(workflow.created_at), { addSuffix: true })}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Progress:</span>
                    <span className="font-medium">
                      {workflow.steps.filter(s => s.status === 'completed').length}/{workflow.steps.length}
                    </span>
                  </div>
                </div>

                {/* Tags */}
                {workflow.tags.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <Tag className="h-4 w-4 text-muted-foreground" />
                    <div className="flex flex-wrap gap-1">
                      {workflow.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Workflow Steps */}
                <div>
                  <h4 className="font-medium mb-2">Workflow Steps</h4>
                  <div className="space-y-2">
                    {workflow.steps.map((step, index) => (
                      <div key={step.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                        <div className="flex items-center space-x-2">
                          <div className={`h-2 w-2 rounded-full ${
                            step.status === 'completed' ? 'bg-green-500' :
                            step.status === 'in_progress' ? 'bg-yellow-500' :
                            step.status === 'failed' ? 'bg-red-500' :
                            step.status === 'skipped' ? 'bg-gray-400' : 'bg-gray-300'
                          }`}></div>
                          <span className="text-sm font-mono">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-medium text-sm">{step.name}</span>
                            <Badge variant={getStepStatusBadge(step.status)} className="text-xs">
                              {step.status.replace('_', ' ')}
                            </Badge>
                            {step.automated && (
                              <Badge variant="info" className="text-xs">Auto</Badge>
                            )}
                            {step.required && (
                              <Badge variant="outline" className="text-xs">Required</Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mb-1">{step.description}</p>
                          {step.assigned_to && (
                            <div className="text-xs text-muted-foreground">
                              Assigned to: {step.assigned_to}
                            </div>
                          )}
                          {step.notes && (
                            <div className="text-xs text-blue-600 mt-1">
                              Note: {step.notes}
                            </div>
                          )}
                        </div>

                        <div className="flex items-center space-x-1">
                          <span className="text-xs text-muted-foreground">
                            {step.estimated_time}min
                          </span>
                          {step.status === 'pending' && !step.automated && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleStepAction(workflow.id, step.id, 'start')}
                              className="text-xs h-7"
                            >
                              <Play className="h-3 w-3 mr-1" />
                              Start
                            </Button>
                          )}
                          {step.status === 'in_progress' && (
                            <div className="flex space-x-1">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleStepAction(workflow.id, step.id, 'complete')}
                                className="text-xs h-7"
                              >
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Complete
                              </Button>
                              {!step.required && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleStepAction(workflow.id, step.id, 'skip')}
                                  className="text-xs h-7"
                                >
                                  Skip
                                </Button>
                              )}
                            </div>
                          )}
                          {step.completed_at && (
                            <div className="text-xs text-green-600">
                              {formatDistanceToNow(new Date(step.completed_at), { addSuffix: true })}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Comments Section */}
                {(workflow.comments.length > 0 || selectedWorkflow?.id === workflow.id) && (
                  <div>
                    <h4 className="font-medium mb-2 flex items-center space-x-2">
                      <MessageSquare className="h-4 w-4" />
                      <span>Comments ({workflow.comments.length})</span>
                    </h4>
                    <div className="space-y-2">
                      {workflow.comments.map((comment) => (
                        <div key={comment.id} className="p-3 bg-accent/30 rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-sm">{comment.user}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(comment.timestamp), { addSuffix: true })}
                            </span>
                          </div>
                          <p className="text-sm">{comment.message}</p>
                        </div>
                      ))}
                      
                      {selectedWorkflow?.id === workflow.id && (
                        <div className="flex items-center space-x-2">
                          <Textarea
                            placeholder="Add a comment..."
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            className="min-h-[60px]"
                          />
                          <Button
                            onClick={() => handleAddComment(workflow.id)}
                            disabled={!newComment.trim()}
                            size="sm"
                          >
                            Post
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center space-x-2">
                    {workflow.status === 'active' && (
                      <Button variant="ghost" size="sm">
                        <Pause className="h-4 w-4 mr-1" />
                        Pause
                      </Button>
                    )}
                    {workflow.status === 'paused' && (
                      <Button variant="ghost" size="sm">
                        <Play className="h-4 w-4 mr-1" />
                        Resume
                      </Button>
                    )}
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => setSelectedWorkflow(selectedWorkflow?.id === workflow.id ? null : workflow)}
                    >
                      <MessageSquare className="h-4 w-4 mr-1" />
                      Comment
                    </Button>
                    <Button variant="ghost" size="sm">
                      <History className="h-4 w-4 mr-1" />
                      History
                    </Button>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Updated {formatDistanceToNow(new Date(workflow.updated_at), { addSuffix: true })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredWorkflows.length === 0 && (
        <div className="text-center py-8">
          <Workflow className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No workflows found</h3>
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'No active workflows at this time'
            }
          </p>
        </div>
      )}
    </div>
  );
}