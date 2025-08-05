// User and Authentication Types
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer';
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Chat and Messaging Types
export interface ChatSession {
  id: string;
  user_id?: string;
  title?: string;
  is_active?: boolean;
  created_at: string;
  updated_at?: string;
  ended_at?: string;
  message_count?: number;
  model_id?: string | null;
  system_prompt?: string | null;
  metadata?: Record<string, any>;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
  metadata?: Record<string, any>;
}

export interface ChatMessageResponse {
  id: string;
  content: string;
  role: 'assistant';
  session_id: string;
  metadata?: Record<string, any>;
  created_at: string;
}

// Unified ChatMessage type for WebSocket and UI
export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

// AI Model Types
export interface AIModel {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  size?: string;
  capabilities: string[];
  is_loaded: boolean;
  is_available: boolean;
  performance_metrics?: {
    tokens_per_second?: number;
    memory_usage?: number;
    response_time?: number;
  };
  specialized_for?: 'general' | 'security' | 'threat_hunting' | 'malware_analysis';
}

export interface ModelLoadRequest {
  model_id: string;
  configuration?: Record<string, any>;
}

export interface ModelStatus {
  model_id: string;
  status: 'loading' | 'loaded' | 'unloading' | 'unloaded' | 'error';
  progress?: number;
  error_message?: string;
  memory_usage?: number;
  last_used?: string;
}

// System Status and Health Types
export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  services: {
    api: ServiceHealth;
    database: ServiceHealth;
    redis: ServiceHealth;
    ai_service: ServiceHealth;
    websocket: ServiceHealth;
  };
  resources: ResourceMetrics;
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  response_time?: number;
  last_check: string;
  details?: Record<string, any>;
}

export interface ResourceMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  gpu_usage?: number;
  active_connections: number;
  loaded_models: number;
}

// SIEM and Security Types
export interface SIEMStatus {
  wazuh_manager: {
    status: 'online' | 'offline' | 'degraded';
    version: string;
    agents_connected: number;
    agents_total: number;
    rules_loaded: number;
    last_restart?: string;
  };
  log_processing: {
    ingestion_rate: number;
    processing_queue: number;
    failed_events: number;
    storage_usage: number;
  };
  threat_detection: {
    active_alerts: number;
    critical_alerts: number;
    high_alerts: number;
    medium_alerts: number;
    low_alerts: number;
  };
  performance_metrics: {
    average_processing_time: number;
    events_per_second: number;
    rule_matching_rate: number;
  };
}

export interface SecurityAlert {
  id: string;
  timestamp: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  rule_id: string;
  rule_description: string;
  source_ip?: string;
  destination_ip?: string;
  agent_name?: string;
  event_type: string;
  mitre_technique?: string[];
  raw_log: string;
  status: 'new' | 'investigating' | 'resolved' | 'false_positive';
  assigned_to?: string;
  notes?: string;
}

export interface WazuhAgent {
  id: string;
  name: string;
  ip: string;
  status: 'active' | 'disconnected' | 'never_connected';
  version: string;
  os_platform: string;
  os_version: string;
  last_keep_alive?: string;
  node_name: string;
  groups: string[];
}

export interface ThreatIntelligence {
  iocs: {
    total: number;
    by_type: Record<string, number>;
    last_updated: string;
  };
  feeds: {
    name: string;
    status: 'active' | 'inactive' | 'error';
    last_update: string;
    entries_count: number;
  }[];
  reputation: {
    sources: number;
    total_entries: number;
    last_sync: string;
  };
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'chat_message' | 'chat_response' | 'typing_start' | 'typing_stop' | 'error' | 'connection' | 'session_created' | 'system_notification';
  data: any;
  timestamp: string;
}

export interface TypingIndicator {
  session_id: string;
  user_id: string;
  is_typing: boolean;
}

export interface SystemNotification {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
}

// API Response Types
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  meta?: {
    total?: number;
    page?: number;
    per_page?: number;
    timestamp?: string;
  };
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// UI State Types
export interface UIState {
  theme: 'light' | 'dark' | 'system';
  sidebar_collapsed: boolean;
  active_session?: string;
  selected_model?: string;
  view_mode: 'chat' | 'dashboard' | 'settings';
  notifications: Notification[];
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  action: string;
  variant?: 'primary' | 'secondary' | 'destructive';
}

// Settings Types
export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  chat_settings: {
    message_history_limit: number;
    auto_scroll: boolean;
    show_timestamps: boolean;
    enable_sounds: boolean;
  };
  security_settings: {
    session_timeout: number;
    require_2fa: boolean;
    login_notifications: boolean;
  };
  model_preferences: {
    default_model: string;
    auto_unload_timeout: number;
    memory_limit_percentage: number;
  };
}

// File Upload Types
export interface FileUpload {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  url?: string;
  error?: string;
}

// Search and Filter Types
export interface SearchFilters {
  query?: string;
  date_from?: string;
  date_to?: string;
  severity?: string[];
  status?: string[];
  agent?: string[];
  rule_id?: string[];
}

export interface SearchResult {
  id: string;
  type: 'message' | 'alert' | 'log' | 'session';
  title: string;
  content: string;
  metadata: Record<string, any>;
  timestamp: string;
  relevance_score: number;
}

// Chart and Visualization Types
export interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

export interface ChartConfig {
  type: 'line' | 'bar' | 'area' | 'pie' | 'scatter';
  title: string;
  x_axis: string;
  y_axis: string;
  color_scheme?: string[];
  show_legend?: boolean;
  height?: number;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
  user_id?: string;
  session_id?: string;
  stack_trace?: string;
}