# Embedded Security AI Appliance - API Reference

Complete API reference for the self-contained Security AI Appliance with embedded LlamaCpp engine.

## Overview

The appliance provides comprehensive REST APIs for:
- **Embedded AI**: Direct model inference without external dependencies
- **Model Management**: HuggingFace integration and local storage
- **User Management**: Authentication and permission control
- **System Monitoring**: Resource usage and health checks

**Base URL**: `http://localhost:8000`  
**API Prefix**: `/api`  
**Authentication**: JWT Bearer tokens

## Authentication Endpoints

### POST `/api/auth/register`
Create a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string", 
  "password": "string",
  "full_name": "string"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@company.com",
  "full_name": "System Administrator",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### POST `/api/auth/login`
Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@company.com",
    "is_admin": true
  }
}
```

## Embedded AI Endpoints

### GET `/api/embedded-ai/health`
Check embedded AI service health and loaded models.

**Response:**
```json
{
  "status": "healthy",
  "service_type": "embedded",
  "engine": "llamacpp",
  "loaded_models": [
    {
      "name": "llama-2-7b-chat-q4_0.gguf",
      "size": "4.2GB",
      "status": "loaded",
      "memory_usage": "3.8GB",
      "load_time": "45.2s"
    }
  ],
  "system_resources": {
    "cpu_usage": "25%",
    "memory_usage": "8.4GB/16GB",
    "gpu_usage": "0%",
    "disk_space": "450GB/1TB"
  }
}
```

### POST `/api/embedded-ai/chat`
Send chat message to embedded AI model.

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Analyze this SSH log for suspicious activity: [log content]",
  "model": "llama-2-7b-chat-q4_0.gguf",
  "max_tokens": 1000,
  "temperature": 0.7,
  "system_prompt": "You are a cybersecurity expert analyzing security logs."
}
```

**Response:**
```json
{
  "response": "Based on the SSH log analysis, I detect potential brute force attempts from IP 192.168.1.100...",
  "model_used": "llama-2-7b-chat-q4_0.gguf",
  "tokens_used": 245,
  "response_time": "2.3s",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

### GET `/api/embedded-ai/models`
List all locally available models.

**Response:**
```json
{
  "models": [
    {
      "filename": "llama-2-7b-chat-q4_0.gguf",
      "display_name": "Llama 2 7B Chat (Q4_0)",
      "size": "4.2GB",
      "quantization": "Q4_0",
      "parameters": "7B",
      "status": "loaded",
      "download_date": "2024-01-10T08:00:00Z",
      "last_used": "2024-01-15T10:30:00Z"
    },
    {
      "filename": "mistral-7b-instruct-q4_0.gguf", 
      "display_name": "Mistral 7B Instruct (Q4_0)",
      "size": "4.1GB",
      "quantization": "Q4_0", 
      "parameters": "7B",
      "status": "available",
      "download_date": "2024-01-12T14:20:00Z",
      "last_used": null
    }
  ],
  "total_models": 2,
  "total_size": "8.3GB",
  "available_space": "450GB"
}
```

### POST `/api/embedded-ai/models/{model_name}/load`
Load a specific model into memory.

**Parameters:**
- `model_name`: Filename of the model to load

**Response:**
```json
{
  "status": "success",
  "message": "Model loaded successfully",
  "model": "llama-2-7b-chat-q4_0.gguf",
  "load_time": "45.2s",
  "memory_usage": "3.8GB"
}
```

### DELETE `/api/embedded-ai/models/{model_name}/unload`
Unload a model from memory.

**Response:**
```json
{
  "status": "success", 
  "message": "Model unloaded successfully",
  "freed_memory": "3.8GB"
}
```

### DELETE `/api/embedded-ai/models/{model_name}`
Delete a model file from local storage.

**Response:**
```json
{
  "status": "success",
  "message": "Model deleted successfully", 
  "freed_space": "4.2GB"
}
```

## HuggingFace Integration Endpoints

### GET `/api/huggingface/categories`
Get available model categories for browsing.

**Response:**
```json
{
  "categories": [
    {
      "id": "text-generation",
      "name": "Text Generation",
      "description": "Large language models for text generation and chat",
      "count": 15420,
      "featured": ["llama", "mistral", "codellama"]
    },
    {
      "id": "security",
      "name": "Security Models", 
      "description": "Models specialized for cybersecurity analysis",
      "count": 324,
      "featured": ["securitybert", "threat-detection"]
    }
  ]
}
```

### GET `/api/huggingface/search`
Search HuggingFace models with filters.

**Query Parameters:**
- `q`: Search query (required)
- `category`: Filter by category
- `min_size`: Minimum model size in GB
- `max_size`: Maximum model size in GB
- `quantization`: Filter by quantization type
- `limit`: Results limit (default: 20)

**Example:** `/api/huggingface/search?q=llama-2&category=text-generation&max_size=10&limit=10`

**Response:**
```json
{
  "models": [
    {
      "id": "meta-llama/llama-2-7b-chat-hf",
      "name": "Llama 2 7B Chat",
      "description": "Fine-tuned for dialogue use cases",
      "author": "Meta", 
      "parameters": "7B",
      "size_gb": 13.5,
      "downloads": 2840192,
      "likes": 8432,
      "tags": ["text-generation", "chat", "llama"],
      "quantizations_available": [
        {
          "type": "Q4_0",
          "size_gb": 4.2,
          "filename": "llama-2-7b-chat-q4_0.gguf"
        },
        {
          "type": "Q5_0", 
          "size_gb": 5.1,
          "filename": "llama-2-7b-chat-q5_0.gguf"
        }
      ],
      "compatibility": "llamacpp",
      "license": "custom"
    }
  ],
  "total": 156,
  "page": 1,
  "per_page": 10
}
```

### POST `/api/huggingface/download`
Start downloading a model from HuggingFace.

**Request Body:**
```json
{
  "model_id": "meta-llama/llama-2-7b-chat-hf",
  "quantization": "Q4_0",
  "filename": "llama-2-7b-chat-q4_0.gguf"
}
```

**Response:**
```json
{
  "download_id": "dl_1704360000_llama2_q4",
  "status": "started",
  "model": "llama-2-7b-chat-q4_0.gguf",
  "estimated_size": "4.2GB",
  "estimated_time": "15-30 minutes"
}
```

### GET `/api/huggingface/downloads`
Get all download statuses.

**Response:**
```json
{
  "downloads": [
    {
      "download_id": "dl_1704360000_llama2_q4",
      "model": "llama-2-7b-chat-q4_0.gguf",
      "status": "downloading",
      "progress": 65.4,
      "downloaded_mb": 2753,
      "total_mb": 4210,
      "speed_mbps": 12.5,
      "eta_minutes": 8,
      "started_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### GET `/api/huggingface/downloads/{download_id}`
Get specific download status.

**Response:**
```json
{
  "download_id": "dl_1704360000_llama2_q4",
  "status": "completed",
  "model": "llama-2-7b-chat-q4_0.gguf", 
  "progress": 100.0,
  "file_size": "4.2GB",
  "completed_at": "2024-01-15T10:18:00Z",
  "download_time": "18m 12s"
}
```

### DELETE `/api/huggingface/downloads/{download_id}`
Cancel or remove a download.

**Response:**
```json
{
  "status": "success",
  "message": "Download cancelled/removed successfully"
}
```

## User Management Endpoints

### GET `/api/users`
List all users (admin only).

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@company.com",
      "full_name": "System Administrator", 
      "is_active": true,
      "is_admin": true,
      "created_at": "2024-01-10T08:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "username": "analyst",
      "email": "analyst@company.com", 
      "full_name": "Security Analyst",
      "is_active": true,
      "is_admin": false,
      "created_at": "2024-01-12T14:20:00Z",
      "last_login": "2024-01-15T09:45:00Z"
    }
  ],
  "total": 2
}
```

### GET `/api/users/{user_id}`
Get specific user details.

**Response:**
```json
{
  "id": 2,
  "username": "analyst",
  "email": "analyst@company.com",
  "full_name": "Security Analyst",
  "is_active": true,
  "is_admin": false,
  "permissions": {
    "can_download_models": false,
    "can_use_models": ["llama-2-7b-chat-q4_0.gguf"],
    "can_delete_models": false,
    "max_concurrent_sessions": 2
  },
  "usage_stats": {
    "total_queries": 145,
    "total_tokens": 28450,
    "favorite_model": "llama-2-7b-chat-q4_0.gguf",
    "avg_session_time": "12m 30s"
  }
}
```

### PUT `/api/users/{user_id}`
Update user details and permissions (admin only).

**Request Body:**
```json
{
  "full_name": "Senior Security Analyst",
  "is_active": true,
  "permissions": {
    "can_download_models": true,
    "can_use_models": ["*"], 
    "can_delete_models": false,
    "max_concurrent_sessions": 3
  }
}
```

### DELETE `/api/users/{user_id}`
Delete user account (admin only).

## System Monitoring Endpoints

### GET `/api/system/status`
Get comprehensive system status.

**Response:**
```json
{
  "system": {
    "uptime": "2d 14h 23m",
    "cpu_usage": "25.4%",
    "memory": {
      "total": "32GB", 
      "used": "12.8GB",
      "available": "19.2GB",
      "ai_models": "8.4GB"
    },
    "disk": {
      "total": "1TB",
      "used": "550GB", 
      "available": "450GB",
      "models_directory": "45GB"
    },
    "gpu": {
      "available": false,
      "memory": null
    }
  },
  "services": {
    "embedded_ai": "healthy",
    "database": "healthy", 
    "redis": "healthy",
    "huggingface": "healthy"
  },
  "models": {
    "total_count": 3,
    "loaded_count": 1,
    "total_size": "12.5GB",
    "active_sessions": 2
  }
}
```

### GET `/api/system/metrics`
Get detailed performance metrics.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:40:00Z",
  "metrics": {
    "requests_total": 1248,
    "requests_per_minute": 8.5,
    "avg_response_time_ms": 2340,
    "error_rate": 0.2,
    "active_sessions": 5,
    "models_loaded": 1,
    "memory_usage_mb": 13107,
    "cpu_usage_percent": 25.4,
    "disk_io_mb": 125.6
  },
  "ai_metrics": {
    "total_queries": 892,
    "avg_tokens_per_query": 245,
    "avg_inference_time_ms": 1850,
    "model_utilization": {
      "llama-2-7b-chat-q4_0.gguf": 78.5
    }
  }
}
```

### GET `/api/system/logs`
Get system logs with filtering.

**Query Parameters:**
- `level`: Log level (debug, info, warning, error)
- `service`: Filter by service name
- `since`: ISO timestamp to start from
- `limit`: Number of entries (default: 100)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-15T10:39:45Z",
      "level": "INFO",
      "service": "embedded_ai",
      "message": "Model inference completed",
      "details": {
        "model": "llama-2-7b-chat-q4_0.gguf",
        "response_time": "2.1s",
        "tokens": 189
      }
    }
  ],
  "total": 1,
  "has_more": false
}
```

## WebSocket Endpoints

### `/ws/chat`
Real-time chat with embedded AI models.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=<jwt_token>');
```

**Message Format:**
```json
{
  "type": "chat_message",
  "data": {
    "message": "Analyze this security log...",
    "model": "llama-2-7b-chat-q4_0.gguf",
    "session_id": "sess_1704360000"
  }
}
```

**Response Format:**
```json
{
  "type": "ai_response",
  "data": {
    "response": "Based on the log analysis...",
    "model": "llama-2-7b-chat-q4_0.gguf",
    "tokens": 234,
    "session_id": "sess_1704360000"
  }
}
```

### `/ws/downloads`
Real-time download progress updates.

**Message Types:**
- `download_started`
- `download_progress` 
- `download_completed`
- `download_failed`

## Error Responses

All endpoints return consistent error formats:

```json
{
  "error": {
    "code": "MODEL_NOT_FOUND",
    "message": "Requested model not found in local storage",
    "details": {
      "model": "nonexistent-model.gguf",
      "available_models": ["llama-2-7b-chat-q4_0.gguf"]
    }
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

**Common Error Codes:**
- `AUTH_REQUIRED`: Authentication token required
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `MODEL_NOT_FOUND`: Requested model not available
- `MODEL_LOAD_FAILED`: Failed to load model into memory
- `DOWNLOAD_FAILED`: Model download failed
- `STORAGE_FULL`: Insufficient disk space
- `MEMORY_FULL`: Insufficient memory for model loading
- `RATE_LIMITED`: Too many requests from user

## Rate Limiting

API endpoints are rate limited per user:
- **Authentication**: 5 requests/minute
- **Chat/AI**: 30 requests/minute
- **Downloads**: 3 concurrent downloads
- **System Monitoring**: 60 requests/minute

Rate limit headers included in responses:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1704360060
```

---

## Getting Started

1. **Deploy appliance**: `docker-compose up -d`
2. **Create admin user**: Use `/api/auth/register` 
3. **Browse models**: Visit web interface at http://localhost:3000
4. **Download first model**: Use HuggingFace integration
5. **Start chatting**: Access chat interface or use API directly

The appliance is completely self-contained with no external dependencies required!