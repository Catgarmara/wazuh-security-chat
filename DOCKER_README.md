# Docker Deployment Guide

This guide covers containerization and deployment of the Wazuh AI Companion application.

## Quick Start

### Development Environment

1. **Copy environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start the development environment:**
   ```bash
   make up
   ```

3. **Access the application:**
   - Application: http://localhost:8000
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

### Production Environment

1. **Set production environment variables:**
   ```bash
   export DB_PASSWORD=your_secure_db_password
   export SECRET_KEY=your_32_character_secret_key
   export GRAFANA_PASSWORD=your_grafana_password
   export GRAFANA_SECRET_KEY=your_grafana_secret_key
   ```

2. **Start production environment:**
   ```bash
   make prod-up
   ```

## Architecture

### Services

- **app**: Main FastAPI application
- **postgres**: PostgreSQL database
- **redis**: Redis cache and session store
- **ollama**: Ollama LLM service
- **nginx**: Reverse proxy (production only)
- **prometheus**: Metrics collection (optional)
- **grafana**: Monitoring dashboards (optional)

### Networking

All services communicate through the `wazuh-network` bridge network.

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

- `ENVIRONMENT`: development/staging/production
- `SECRET_KEY`: JWT signing key (minimum 32 characters)
- `DB_PASSWORD`: PostgreSQL password
- `MODELS_PATH`: Path to store local LLM models (default: ./models)

### Health Checks

All services include health checks:
- **app**: HTTP health endpoint
- **postgres**: pg_isready check
- **redis**: Redis ping
- **ollama**: Service availability

## Docker Images

### Multi-stage Build

The Dockerfile uses multi-stage builds:

1. **base**: Common dependencies and system packages
2. **development**: Includes dev tools and hot reload
3. **production**: Optimized for production deployment

### Image Optimization

- Non-root user for security
- Minimal base image (python:3.11-slim)
- Layer caching optimization
- .dockerignore for build context reduction

## Deployment Options

### Docker Compose (Recommended for Development)

```bash
# Development with hot reload
docker-compose up -d

# Production-like environment
docker-compose -f docker-compose.prod.yml up -d

# With monitoring stack
docker-compose --profile monitoring up -d
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml wazuh-stack
```

### Kubernetes (See kubernetes/ directory)

```bash
# Apply manifests
kubectl apply -f kubernetes/

# Check deployment
kubectl get pods -n wazuh
```

## Monitoring

### Prometheus Metrics

The application exposes metrics at `/metrics`:
- HTTP request metrics
- WebSocket connection metrics
- Database connection pool metrics
- AI processing time metrics

### Grafana Dashboards

Pre-configured dashboards include:
- Application health and performance
- Database metrics
- Redis metrics
- System resource usage

### Log Aggregation

Structured JSON logging is configured for:
- Application logs
- Access logs (nginx)
- Error logs
- Audit logs

## Security

### Container Security

- Non-root user execution
- Read-only root filesystem (where possible)
- Security scanning with Docker Scout
- Minimal attack surface

### Network Security

- Internal network isolation
- TLS termination at nginx
- Rate limiting and DDoS protection
- Security headers

### Secrets Management

- Environment variable injection
- Docker secrets support
- External secret management integration

## Scaling

### Horizontal Scaling

```bash
# Scale application instances
docker-compose up -d --scale app=3

# Load balancing handled by nginx
```

### Resource Limits

Production deployment includes:
- CPU limits and reservations
- Memory limits and reservations
- Disk I/O limits

## Troubleshooting

### Common Issues

1. **Database connection failed:**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U postgres
   
   # Check logs
   docker-compose logs postgres
   ```

2. **Ollama model not found:**
   ```bash
   # Pull model manually
   docker-compose exec ollama ollama pull llama3
   ```

3. **Permission denied errors:**
   ```bash
   # Check file ownership
   docker-compose exec app ls -la /app
   ```

### Health Checks

```bash
# Application health
make health

# Service status
docker-compose ps

# Resource usage
docker stats
```

### Log Analysis

```bash
# Application logs
make logs

# All service logs
docker-compose logs

# Specific service logs
docker-compose logs postgres
```

## Maintenance

### Updates

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
make down && make build && make up
```

### Backups

```bash
# Database backup
docker-compose exec postgres pg_dump -U postgres wazuh_chat > backup.sql

# Volume backup
docker run --rm -v wazuh_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

### Cleanup

```bash
# Remove stopped containers and unused images
make clean

# Full system cleanup
docker system prune -a --volumes
```

## Performance Tuning

### Database Optimization

- Connection pooling configured
- Indexes on frequently queried columns
- Query optimization with EXPLAIN

### Redis Optimization

- Memory limits and eviction policies
- Persistence configuration
- Connection pooling

### Application Optimization

- Async/await for I/O operations
- Connection pooling for external services
- Caching strategies

## Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database passwords changed
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Resource limits set
- [ ] Health checks verified
- [ ] Security scanning completed
- [ ] Load testing performed