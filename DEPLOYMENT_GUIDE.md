# Self-Contained Security Appliance Deployment Guide

## Overview

This guide covers the deployment of the AI-Enhanced Security Query Interface as a complete self-contained appliance with embedded LLM processing.

## Prerequisites

- Docker and Docker Compose installed
- Minimum 8GB RAM (16GB recommended)
- 100GB available disk space for models
- Optional: NVIDIA GPU for enhanced performance

## Quick Start - Single Command Deployment

### 1. Deploy the Complete Appliance

```bash
# Clone and deploy in one command
docker-compose up -d
```

This single command will:
- Build the security appliance container with embedded AI
- Start PostgreSQL database
- Start Redis cache
- Start the web interface
- Configure all networking and volumes
- Set up health monitoring

### 2. Access the Appliance

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Configuration Options

### CPU-Only Deployment (Default)

The default configuration uses CPU-only inference:

```bash
docker-compose up -d
```

### GPU-Accelerated Deployment

For enhanced performance with NVIDIA GPU:

1. Uncomment GPU support in `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

2. Rebuild with GPU support:
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Production Deployment

For production with monitoring and reverse proxy:

```bash
# Deploy with monitoring stack
docker-compose --profile monitoring --profile production up -d
```

This includes:
- Nginx reverse proxy
- Prometheus metrics
- Grafana dashboards
- Alert manager

## Embedded AI Configuration

### Environment Variables

Key configuration options in `docker-compose.yml`:

```yaml
environment:
  # Core AI settings
  - AI_SERVICE_TYPE=embedded
  - MODELS_PATH=/app/models
  - VECTORSTORE_PATH=/app/data/vectorstore
  - MAX_CONCURRENT_MODELS=3
  
  # Model configuration
  - EMBEDDING_MODEL=all-MiniLM-L6-v2
  - DEFAULT_TEMPERATURE=0.7
  - DEFAULT_MAX_TOKENS=1024
  - CONVERSATION_MEMORY_SIZE=10
  
  # Appliance settings
  - APPLIANCE_MODE=true
  - SIEM_INTEGRATION_ENABLED=true
  - MODEL_AUTO_DOWNLOAD=true
```

### Model Management

Models are automatically downloaded and stored in persistent volumes:

- **Local Storage**: `model_data` volume mounted at `/app/models`
- **Vector Store**: `vectorstore_data` volume mounted at `/app/data`
- **Auto-Download**: Models downloaded on first use

## Validation and Testing

### Pre-Deployment Validation

```bash
# Validate configuration
python scripts/validate_build_config.py

# Test deployment configuration
python scripts/test_deployment.py
```

### Post-Deployment Health Checks

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f app

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:3000/api/health
```

## Service Architecture

### Core Services

1. **app**: Main security appliance with embedded AI
2. **postgres**: Database for persistent data
3. **redis**: Cache and session storage
4. **frontend**: Web interface

### Optional Services (with profiles)

1. **nginx**: Reverse proxy and SSL termination
2. **prometheus**: Metrics collection
3. **grafana**: Monitoring dashboards
4. **alertmanager**: Alert handling

## Data Persistence

All critical data is persisted in Docker volumes:

- `model_data`: AI models and configurations
- `vectorstore_data`: Vector embeddings and cache
- `postgres_data`: Application database
- `redis_data`: Cache and sessions

## Security Features

### Built-in Security

- Non-root container execution
- Network isolation
- Health monitoring
- Automatic restarts
- Input validation
- JWT authentication

### SIEM Integration

The appliance integrates with existing SIEM platforms:

- **Wazuh**: Native API integration
- **Splunk**: REST API queries
- **Elastic**: Elasticsearch queries
- **Custom**: Configurable connectors

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :3000
   netstat -tulpn | grep :8000
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats
   ```

3. **Model Loading Failures**
   ```bash
   # Check model directory
   docker-compose exec app ls -la /app/models
   
   # View AI service logs
   docker-compose logs app | grep -i "model"
   ```

### Log Analysis

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# All services
docker-compose logs -f
```

## Scaling and Performance

### Resource Requirements

- **Minimum**: 8GB RAM, 4 CPU cores, 100GB storage
- **Recommended**: 16GB RAM, 8 CPU cores, 500GB storage
- **High Performance**: 32GB RAM, 16 CPU cores, 1TB SSD, GPU

### Performance Tuning

1. **Model Concurrency**
   ```yaml
   - MAX_CONCURRENT_MODELS=5  # Increase for more parallel processing
   ```

2. **Database Connections**
   ```yaml
   - DB_POOL_SIZE=20  # Increase for higher concurrency
   ```

3. **Worker Processes**
   ```dockerfile
   CMD ["uvicorn", "app.main:app", "--workers", "8"]  # Scale workers
   ```

## Backup and Recovery

### Data Backup

```bash
# Backup volumes
docker run --rm -v model_data:/data -v $(pwd):/backup alpine tar czf /backup/models-backup.tar.gz -C /data .
docker run --rm -v vectorstore_data:/data -v $(pwd):/backup alpine tar czf /backup/vectorstore-backup.tar.gz -C /data .

# Database backup
docker-compose exec postgres pg_dump -U postgres wazuh_chat > backup.sql
```

### Recovery

```bash
# Restore volumes
docker run --rm -v model_data:/data -v $(pwd):/backup alpine tar xzf /backup/models-backup.tar.gz -C /data
docker run --rm -v vectorstore_data:/data -v $(pwd):/backup alpine tar xzf /backup/vectorstore-backup.tar.gz -C /data

# Database restore
docker-compose exec -T postgres psql -U postgres wazuh_chat < backup.sql
```

## Updates and Maintenance

### Updating the Appliance

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Model Updates

Models are automatically updated when new versions are available. Manual update:

```bash
# Clear model cache
docker-compose exec app rm -rf /app/models/cache/*

# Restart to trigger re-download
docker-compose restart app
```

## Support and Monitoring

### Health Monitoring

- **Application**: http://localhost:8000/health
- **Database**: Automatic health checks
- **Redis**: Connection monitoring
- **Models**: Load status and performance metrics

### Metrics (with monitoring profile)

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **System Metrics**: http://localhost:9100

## Complete Self-Containment

This appliance is completely self-contained:

- ✅ No external AI service dependencies
- ✅ Local model storage and processing
- ✅ Embedded LLM inference engine
- ✅ Single-command deployment
- ✅ Persistent data storage
- ✅ Built-in monitoring and health checks
- ✅ SIEM integration capabilities
- ✅ Web interface included

Deploy with confidence knowing all AI processing happens locally within your infrastructure.