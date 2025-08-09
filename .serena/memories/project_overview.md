# Project Overview: AI-Enhanced Security Query Interface

## Purpose
A practical turnkey security appliance that provides natural language querying capabilities for existing SIEM infrastructure. Self-contained deployment with embedded LLM processing, designed to work alongside current security operations without requiring data migration or platform replacement.

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (0.104.1) with async support
- **Server**: Uvicorn (0.24.0)
- **Database**: PostgreSQL 15 (primary data), Redis 7 (cache/sessions)
- **ORM**: SQLAlchemy 2.0.23 with Alembic migrations
- **Authentication**: JWT tokens with bcrypt password hashing
- **WebSocket**: Real-time chat communication

### AI Components
- **LLM Engine**: LlamaCpp with direct model inference (embedded, no external dependencies)
- **Model Management**: HuggingFace integration for model browsing and downloading
- **Vector Store**: FAISS-powered semantic search for log analysis
- **Embeddings**: Sentence-transformers (all-MiniLM-L6-v2)
- **Context Management**: Conversation history and progressive query building

### Frontend
- **Framework**: Next.js 14 with TypeScript
- **UI Library**: Tailwind CSS with Radix UI components
- **State Management**: Zustand for client state
- **API Client**: React Query (TanStack) with Axios
- **Real-time**: WebSocket integration for chat

### Infrastructure
- **Containerization**: Docker and Docker Compose
- **Reverse Proxy**: Nginx (optional for production)
- **Monitoring**: Prometheus, Grafana, Alertmanager stack
- **Architecture**: Microservices with clear separation of concerns

## System Architecture
- **Frontend Layer**: Next.js UI, Model Management UI, SIEM Dashboard, Admin Console
- **API Gateway**: FastAPI with Auth, Chat, AI, SIEM, and WebSocket APIs
- **Microservices**: AuthService, ChatService, SIEMService, AnalyticsService
- **AI Service Factory**: EmbeddedAIService with Model Manager, HuggingFace Service, Resource Manager
- **Data Layer**: PostgreSQL, Redis, Model Storage, Vector Store
- **Monitoring**: Comprehensive observability with Prometheus/Grafana

## Key Features
- **SIEM Integration**: Query existing Wazuh, Splunk, Elastic platforms through APIs
- **Conversational Interface**: Natural language queries converted to SIEM-specific searches
- **Local Processing**: Embedded LLM engine processes query results locally
- **Existing Infrastructure**: Works with current security tools and data sources
- **Minimal Footprint**: Lightweight appliance that enhances rather than replaces systems
- **Role-based Access**: Admin/Analyst/Viewer roles with model permissions
- **Resource Monitoring**: Real-time CPU/GPU/Memory tracking