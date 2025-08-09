# Architecture and Code Structure

## High-Level Architecture

The system follows a microservices architecture with clear separation of concerns:

### Layer Organization
1. **Frontend Layer**: Next.js TypeScript application with real-time WebSocket communication
2. **API Gateway Layer**: FastAPI with middleware stack for security, authentication, and routing
3. **Microservices Layer**: Domain-specific services (Auth, Chat, SIEM, Analytics)
4. **AI Service Factory**: Embedded LlamaCpp engine with model management and resource optimization
5. **Data Layer**: PostgreSQL for persistence, Redis for caching and sessions
6. **Monitoring Layer**: Prometheus/Grafana stack for observability

## Code Structure

### Backend Services (`/api`, `/services`, `/core`)

**API Layer (`/api/`)**:
- `auth.py` - JWT authentication and user management endpoints
- `chat.py` - Chat session management and message handling
- `ai.py` - AI model management and inference endpoints
- `siem.py` - SIEM platform integration and query translation
- `websocket.py` - Real-time WebSocket communication
- `huggingface.py` - Model browsing and downloading from HuggingFace
- `alert_management.py` - Security alert processing
- `threat_correlation.py` - Advanced threat analysis

**Core Infrastructure (`/core/`)**:
- `config.py` - Application settings with security appliance validation
- `database.py` - PostgreSQL connection and session management
- `redis_client.py` - Redis connection and caching utilities
- `middleware.py` - Security middleware stack (CORS, rate limiting, input sanitization)
- `permissions.py` - Role-based access control (RBAC) system
- `ai_factory.py` - AI service factory for model management
- `resource_manager.py` - System resource monitoring and optimization
- `health.py` - Health check endpoints and system status

**Business Logic (`/services/`)**:
- `auth_service.py` - User authentication and session management
- `chat_service.py` - Conversation context and WebSocket handling
- `embedded_ai_service.py` - LlamaCpp model inference and management
- `siem_service.py` - External SIEM platform integration
- `huggingface_service.py` - Model discovery and download management
- `analytics_service.py` - Query metrics and performance tracking
- `audit_service.py` - Security event logging and compliance

### Frontend Structure (`/frontend/src`)

**Component Architecture**:
- Modern React with TypeScript
- Tailwind CSS for styling with Radix UI component library
- Zustand for state management
- React Query for server state and API interactions
- WebSocket integration for real-time chat

### Data Models (`/models`)

**Database Schema**:
- User management with role-based permissions
- Chat sessions and conversation history
- AI model configurations and metadata
- SIEM integration settings
- Audit logs and security events
- System metrics and performance data

## Key Architectural Patterns

### Embedded AI Architecture
- **Self-Contained**: No external AI service dependencies
- **LlamaCpp Integration**: Direct model inference without Ollama
- **Model Management**: HuggingFace browser, downloader, local storage
- **Resource Awareness**: Intelligent model loading based on system capabilities
- **Hot Swapping**: Zero-downtime model switching with fallback mechanisms

### Security-First Design
- **Multi-Layer Security**: Request pipeline with host validation, CORS, rate limiting
- **JWT Authentication**: Secure token-based auth with role-based access control
- **Input Sanitization**: Protection against SQL injection, XSS, command injection
- **Audit Logging**: Comprehensive security event tracking and compliance

### SIEM Integration Pattern
- **Query Translation**: Natural language to SIEM-specific query conversion
- **Result Processing**: Analyzes returned data sets rather than bulk log processing
- **Progressive Analysis**: Combines multiple targeted queries for comprehensive insights
- **Flexible Data Sources**: API connections or local vector storage

### Microservices Communication
- **API Gateway**: Central routing and middleware through FastAPI
- **Service Layer**: Clear separation between API, business logic, and data access
- **Event-Driven**: WebSocket for real-time communication
- **Database Per Service**: Each service owns its data domain

## Deployment Architecture

### Container Orchestration
- **Docker Compose**: Development and production configurations
- **Service Dependencies**: Health checks and proper startup ordering
- **Volume Management**: Persistent storage for models, data, and configurations
- **Network Isolation**: Dedicated network for security appliance services

### Resource Management
- **GPU Support**: Optional NVIDIA GPU acceleration for model inference
- **Memory Optimization**: Intelligent model loading and caching strategies
- **Scaling**: Horizontal scaling support with load balancing
- **Monitoring**: Real-time resource tracking and alerting

This architecture provides a complete security appliance that enhances existing SIEM infrastructure while maintaining data privacy through local processing.