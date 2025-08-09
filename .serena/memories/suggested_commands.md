# Suggested Commands for AI-Enhanced Security Query Interface

## Development Environment

### Docker Compose Commands (Primary)
```bash
# Start development environment
make up
# or: docker-compose up -d

# Stop development environment
make down
# or: docker-compose down

# Build Docker images
make build
# or: docker-compose build

# View application logs
make logs
# or: docker-compose logs -f app

# Clean up Docker resources
make clean
# or: docker-compose down -v --remove-orphans && docker system prune -f
```

### Production Commands
```bash
# Build production images
make prod-build
# or: docker-compose -f docker-compose.prod.yml build

# Start production environment
make prod-up
# or: docker-compose -f docker-compose.prod.yml up -d

# Stop production environment
make prod-down
# or: docker-compose -f docker-compose.prod.yml down
```

### Testing Commands
```bash
# Run tests in Docker container
make test
# or: docker-compose exec app python -m pytest tests/ -v

# Run specific test markers
docker-compose exec app python -m pytest tests/ -m unit -v
docker-compose exec app python -m pytest tests/ -m integration -v
docker-compose exec app python -m pytest tests/ -m security -v
```

### Database Operations
```bash
# Run database migrations
make db-migrate
# or: docker-compose exec app alembic upgrade head

# Reset database
make db-reset
# or: docker-compose exec app alembic downgrade base && alembic upgrade head

# Generate new migration
docker-compose exec app alembic revision --autogenerate -m "description"
```

### Monitoring Commands
```bash
# Start with monitoring stack
make monitoring-up
# or: docker-compose --profile monitoring up -d

# Stop monitoring
make monitoring-down
# or: docker-compose --profile monitoring down

# Health check
make health
# or: docker-compose exec app python scripts/health_check.py
```

### Frontend Development
```bash
# Start Next.js development (inside frontend container)
docker-compose exec frontend npm run dev

# Build frontend
docker-compose exec frontend npm run build

# Lint frontend code
docker-compose exec frontend npm run lint

# Type check frontend
docker-compose exec frontend npm run type-check

# Run frontend tests
docker-compose exec frontend npm run test
```

## Direct Python Commands (if running locally)

### Application Startup
```bash
# Start with default settings
python main.py

# Start with custom host/port
python main.py --host 0.0.0.0 --port 8080

# Start with auto-reload for development
python main.py --reload

# Start with multiple workers
python main.py --workers 4
```

### Development Workflow
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt  # for testing

# Run tests locally
pytest tests/ -v
pytest tests/ -m unit  # unit tests only
pytest tests/ -m integration  # integration tests only

# Database operations
alembic upgrade head  # apply migrations
alembic revision --autogenerate -m "description"  # create migration
```

## Service URLs (Development)
- **Main Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:3000
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Environment Configuration
- Copy `.env.example` to `.env` and configure as needed
- Key variables: `SECRET_KEY`, database credentials, AI model paths
- For development: use default Docker Compose environment variables
- For production: ensure proper secrets and security configuration