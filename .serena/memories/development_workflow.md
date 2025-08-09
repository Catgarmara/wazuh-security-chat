# Development Workflow and Standards

## Development Environment Setup

### Prerequisites
- Docker and Docker Compose (primary development method)
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Quick Start
1. Clone repository
2. Copy `.env.example` to `.env`
3. Run `make up` or `docker-compose up -d`
4. Access application at http://localhost:8000 (API) and http://localhost:3000 (UI)

## Code Style and Conventions

### Backend (Python)
- **Framework**: FastAPI with async/await patterns
- **Type Hints**: Comprehensive type annotations throughout
- **Validation**: Pydantic models for request/response validation
- **Error Handling**: Structured exception handling with proper HTTP status codes
- **Logging**: Structured logging with loguru and correlation IDs
- **Testing**: Pytest with comprehensive unit, integration, and security tests

### Frontend (TypeScript/React)
- **Framework**: Next.js 14 with TypeScript
- **Components**: Functional components with hooks
- **Styling**: Tailwind CSS with component variants
- **State**: Zustand for client state, React Query for server state
- **Testing**: Jest with React Testing Library

### Database
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic for schema versioning
- **Patterns**: Repository pattern for data access
- **Relationships**: Proper foreign key constraints and indexes

## Testing Strategy

### Test Categories (pytest markers)
- `unit`: Fast unit tests for individual components
- `integration`: Service integration tests with database
- `security`: Security-focused tests for authentication and authorization
- `performance`: Performance and load testing
- `e2e`: End-to-end tests with Playwright

### Test Commands
```bash
# Run all tests
make test

# Run specific test categories
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m security
```

### Test Coverage
- Unit tests for all service layer components
- Integration tests for API endpoints
- Security tests for authentication and RBAC
- WebSocket integration tests for real-time features

## Development Workflow

### Branch Strategy
- Feature branches for new functionality
- Pull requests with code review
- Automated testing before merge

### Code Quality
- Type checking with mypy (implicit through Pydantic)
- Linting with built-in FastAPI validation
- Security scanning of dependencies
- Automated testing with pytest

### Database Changes
1. Create migration: `docker-compose exec app alembic revision --autogenerate -m "description"`
2. Review generated migration file
3. Apply migration: `docker-compose exec app alembic upgrade head`
4. Test migration rollback if needed

## Project Structure Patterns

### Service Layer Architecture
- **API Layer**: Route handlers with minimal logic
- **Service Layer**: Business logic and orchestration
- **Data Layer**: Database models and repositories
- **Core Layer**: Shared utilities and configuration

### Dependency Injection
- FastAPI's dependency injection for database sessions
- Service layer dependencies for business logic
- Authentication dependencies for protected routes

### Configuration Management
- Environment-based configuration with Pydantic Settings
- Secure secret management for production deployment
- Development defaults with production overrides

## Security Development Practices

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (Admin/Analyst/Viewer)
- Permission checks at API and service levels
- Session management with Redis

### Input Validation
- Pydantic models for all API inputs
- SQL injection prevention through SQLAlchemy
- XSS protection through proper output encoding
- Command injection prevention in SIEM integrations

### Audit & Compliance
- Comprehensive audit logging for all user actions
- Security event tracking and correlation
- GDPR/SOX compliance features
- Data retention and export capabilities

## AI Development Patterns

### Model Management
- HuggingFace integration for model discovery
- Local model storage with version control
- Resource-aware model loading and unloading
- Hot-swapping for zero-downtime updates

### Inference Optimization
- Async processing for non-blocking requests
- Context management for conversation history
- Memory optimization for large models
- GPU acceleration when available

### SIEM Integration
- Plugin architecture for different SIEM platforms
- Query translation patterns for natural language
- Result processing and correlation
- Error handling and fallback mechanisms

## Deployment Practices

### Container Strategy
- Multi-stage Dockerfiles for production optimization
- Health checks for all services
- Resource limits and monitoring
- Security-hardened base images

### Environment Management
- Development, staging, and production configurations
- Secret management with environment variables
- Database migration automation
- Monitoring and alerting setup

This workflow ensures high-quality, secure, and maintainable code while supporting the complex requirements of a security appliance.