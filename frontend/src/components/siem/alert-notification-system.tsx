'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Bell, 
  X, 
  Eye, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  User, 
  MapPin,
  Hash,
  ExternalLink,
  Volume2,
  VolumeX,
  Settings,
  Filter
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface AlertNotificationSystemProps {
  className?: string;
  onAlertAction?: (alertId: string, action: 'acknowledge' | 'resolve' | 'dismiss') => void;
}

type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';
type AlertStatus = 'new' | 'acknowledged' | 'resolved' | 'dismissed';

interface AlertNotification {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  status: AlertStatus;
  timestamp: string;
  source: string;
  agent_name?: string;
  rule_id?: number;
  source_ip?: string;
  user?: string;
  category: string;
  auto_dismiss_in?: number; // seconds
  requires_action: boolean;
  sound_enabled: boolean;
}

interface NotificationSettings {
  sound_enabled: boolean;
  auto_dismiss_low: boolean;
  auto_dismiss_medium: boolean;
  show_only_critical: boolean;
  max_notifications: number;
}

export function AlertNotificationSystem({ className, onAlertAction }: AlertNotificationSystemProps) {
  const [notifications, setNotifications] = React.useState<AlertNotification[]>([]);
  const [settings, setSettings] = React.useState<NotificationSettings>({
    sound_enabled: true,
    auto_dismiss_low: true,
    auto_dismiss_medium: false,
    show_only_critical: false,
    max_notifications: 10
  });
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [unreadCount, setUnreadCount] = React.useState(0);

  // Mock notifications - replace with WebSocket integration
  const mockNotifications: AlertNotification[] = [
    {
      id: 'notif-001',
      title: 'Critical Security Alert',
      message: 'Suspicious process execution detected on workstation-05',
      severity: 'critical',
      status: 'new',
      timestamp: '2024-01-20T14:45:32Z',
      source: 'Wazuh Manager',
      agent_name: 'workstation-05',
      rule_id: 31103,
      user: 'user01',
      category: 'Malware Detection',
      requires_action: true,
      sound_enabled: true
    },
    {
      id: 'notif-002',
      title: 'Authentication Failure',
      message: 'Multiple failed login attempts from 192.168.1.200',
      severity: 'high',
      status: 'new',
      timestamp: '2024-01-20T14:43:15Z',
      source: 'SSH Monitor',
      agent_name: 'web-server-01',
      rule_id: 5716,
      source_ip: '192.168.1.200',
      user: 'admin',
      category: 'Authentication',
      auto_dismiss_in: 300,
      requires_action: true,
      sound_enabled: true
    },
    {
      id: 'notif-003',
      title: 'Network Security Alert',
      message: 'Connection to known malicious IP blocked',
      severity: 'high',
      status: 'acknowledged',
      timestamp: '2024-01-20T14:40:08Z',
      source: 'Firewall Monitor',
      agent_name: 'workstation-05',
      rule_id: 31153,
      source_ip: '185.220.100.240',
      category: 'Network Security',
      requires_action: false,
      sound_enabled: false
    },
    {
      id: 'notif-004',
      title: 'File Integrity Alert',
      message: 'Critical system file modified: /etc/passwd',
      severity: 'medium',
      status: 'new',
      timestamp: '2024-01-20T14:38:45Z',
      source: 'FIM Monitor',
      agent_name: 'db-server-01',
      rule_id: 40111,
      user: 'root',
      category: 'File Integrity',
      auto_dismiss_in: 600,
      requires_action: true,
      sound_enabled: false
    }
  ];

  React.useEffect(() => {
    setNotifications(mockNotifications);
    setUnreadCount(mockNotifications.filter(n => n.status === 'new').length);
  }, []);

  React.useEffect(() => {
    // Auto-dismiss logic
    const interval = setInterval(() => {
      setNotifications(prev => prev.map(notification => {
        if (notification.auto_dismiss_in && notification.auto_dismiss_in > 0) {
          const updatedNotification = { 
            ...notification, 
            auto_dismiss_in: notification.auto_dismiss_in - 1 
          };
          
          if (updatedNotification.auto_dismiss_in <= 0) {
            return { ...updatedNotification, status: 'dismissed' as AlertStatus };
          }
          
          return updatedNotification;
        }
        return notification;
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleAlertAction = (alertId: string, action: 'acknowledge' | 'resolve' | 'dismiss') => {
    setNotifications(prev => prev.map(notification => 
      notification.id === alertId 
        ? { ...notification, status: action === 'acknowledge' ? 'acknowledged' : action === 'resolve' ? 'resolved' : 'dismissed' }
        : notification
    ));

    setUnreadCount(prev => Math.max(0, prev - 1));
    onAlertAction?.(alertId, action);
  };

  const getSeverityIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case 'medium':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'low':
        return <AlertTriangle className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityBadge = (severity: AlertSeverity) => {
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

  const getStatusIcon = (status: AlertStatus) => {
    switch (status) {
      case 'new':
        return <Bell className="h-4 w-4 text-blue-500" />;
      case 'acknowledged':
        return <Eye className="h-4 w-4 text-yellow-500" />;
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'dismissed':
        return <X className="h-4 w-4 text-gray-500" />;
    }
  };

  const filteredNotifications = React.useMemo(() => {
    let filtered = notifications.filter(n => n.status !== 'dismissed');
    
    if (settings.show_only_critical) {
      filtered = filtered.filter(n => n.severity === 'critical');
    }
    
    return filtered
      .sort((a, b) => {
        // Sort by severity first, then by timestamp
        const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        const severityDiff = severityOrder[b.severity] - severityOrder[a.severity];
        if (severityDiff !== 0) return severityDiff;
        
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      })
      .slice(0, settings.max_notifications);
  }, [notifications, settings]);

  const criticalAlerts = filteredNotifications.filter(n => n.severity === 'critical' && n.status === 'new');

  return (
    <div className={`${className}`}>
      {/* Notification Bell */}
      <div className="relative">
        <Button
          variant={criticalAlerts.length > 0 ? "destructive" : unreadCount > 0 ? "default" : "outline"}
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className={`relative ${criticalAlerts.length > 0 ? 'animate-pulse' : ''}`}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <Badge 
              variant={criticalAlerts.length > 0 ? "critical" : "high"}
              className="absolute -top-2 -right-2 h-5 w-5 p-0 text-xs flex items-center justify-center"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
        </Button>

        {/* Notification Panel */}
        {isExpanded && (
          <Card className="absolute right-0 top-12 w-96 max-h-96 overflow-hidden shadow-lg z-50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Bell className="h-5 w-5" />
                  <span>Security Alerts</span>
                </CardTitle>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSettings(prev => ({ ...prev, sound_enabled: !prev.sound_enabled }))}
                  >
                    {settings.sound_enabled ? 
                      <Volume2 className="h-4 w-4" /> : 
                      <VolumeX className="h-4 w-4" />
                    }
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsExpanded(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <CardDescription>
                {unreadCount} unread alert{unreadCount !== 1 ? 's' : ''} • {filteredNotifications.length} total
              </CardDescription>
            </CardHeader>

            <CardContent className="p-0">
              <div className="max-h-80 overflow-y-auto">
                {filteredNotifications.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No active alerts</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {filteredNotifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-4 border-b hover:bg-accent/50 transition-colors ${
                          notification.status === 'new' ? 'bg-accent/30' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-start space-x-2">
                            {getSeverityIcon(notification.severity)}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2 mb-1">
                                <Badge variant={getSeverityBadge(notification.severity)} className="text-xs">
                                  {notification.severity.toUpperCase()}
                                </Badge>
                                {notification.rule_id && (
                                  <Badge variant="outline" className="text-xs">
                                    Rule {notification.rule_id}
                                  </Badge>
                                )}
                              </div>
                              <h4 className="font-medium text-sm mb-1">{notification.title}</h4>
                              <p className="text-xs text-muted-foreground mb-2">{notification.message}</p>
                              
                              <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                                <div className="flex items-center space-x-1">
                                  <Clock className="h-3 w-3" />
                                  <span>{formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}</span>
                                </div>
                                {notification.agent_name && (
                                  <div className="flex items-center space-x-1">
                                    <MapPin className="h-3 w-3" />
                                    <span>{notification.agent_name}</span>
                                  </div>
                                )}
                                {notification.user && (
                                  <div className="flex items-center space-x-1">
                                    <User className="h-3 w-3" />
                                    <span>{notification.user}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(notification.status)}
                          </div>
                        </div>

                        {notification.auto_dismiss_in && notification.auto_dismiss_in > 0 && (
                          <div className="mb-2">
                            <div className="text-xs text-muted-foreground mb-1">
                              Auto-dismiss in {notification.auto_dismiss_in}s
                            </div>
                            <div className="w-full bg-secondary rounded-full h-1">
                              <div
                                className="bg-yellow-500 h-1 rounded-full transition-all"
                                style={{ width: `${(notification.auto_dismiss_in / 600) * 100}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {notification.status === 'new' && notification.requires_action && (
                          <div className="flex items-center space-x-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAlertAction(notification.id, 'acknowledge')}
                              className="text-xs h-7"
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              Acknowledge
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAlertAction(notification.id, 'resolve')}
                              className="text-xs h-7"
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Resolve
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleAlertAction(notification.id, 'dismiss')}
                              className="text-xs h-7"
                            >
                              <X className="h-3 w-3 mr-1" />
                              Dismiss
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-3 border-t bg-accent/20">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-muted-foreground">
                    {filteredNotifications.filter(n => n.status === 'new').length} new alerts
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button variant="ghost" size="sm" className="text-xs h-7">
                      <ExternalLink className="h-3 w-3 mr-1" />
                      View All
                    </Button>
                    <Button variant="ghost" size="sm" className="text-xs h-7">
                      <Settings className="h-3 w-3 mr-1" />
                      Settings
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Critical Alert Overlay */}
      {criticalAlerts.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {criticalAlerts.slice(0, 3).map((alert) => (
            <Card key={alert.id} className="w-80 border-red-500 shadow-lg animate-in slide-in-from-right">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="h-5 w-5 text-red-500 animate-pulse" />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <Badge variant="critical" className="text-xs">CRITICAL</Badge>
                      </div>
                      <h4 className="font-medium text-sm mb-1">{alert.title}</h4>
                      <p className="text-xs text-muted-foreground mb-2">{alert.message}</p>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleAlertAction(alert.id, 'acknowledge')}
                          className="text-xs h-7"
                        >
                          Acknowledge
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAlertAction(alert.id, 'dismiss')}
                          className="text-xs h-7"
                        >
                          Dismiss
                        </Button>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAlertAction(alert.id, 'dismiss')}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}