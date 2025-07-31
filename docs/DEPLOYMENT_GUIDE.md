# Wazuh AI Companion - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Wazuh AI Companion system in various environments, from local development to production Kubernetes clusters.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development Deployment](#local-development-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Production Deployment](#production-deployment)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance and Updates](#maintenance-and-updates)

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Memory**: Minimum 8GB RAM, Recommended 16GB+ RAM
- **Storage**: Minimum 50GB, Recommended 100GB+ SSD
- **Network**: Stable internet connection for AI model downloads

### Software Dependencies

- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Kubernetes**: 1.25 or higher (for K8s deployment)
- **kubectl**: Compatible with your Kubernetes version

### External Services

- **PostgreSQL**: 13 or higher
- **Redis**: 6 or higher
- **Ollama**: For LLM processing (can be local or remote)

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Application Configuration
APP_NAME=Wazuh AI Companion
APP_VERSION=2.0.0
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
API_PREFIX=/api/v1

# Security Configuration
SECRET_KEY=your-super-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wazuh_chat
DB_USER=wazuh_user
DB_PASSWORD=secure_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=redis_password
REDIS_MAX_CONNECTIONS=20

# AI Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_TOKENS=2048
TEMPERATURE=0.7

# Log Processing Configuration
WAZUH_LOGS_PATH=/var/ossec/logs/archives
DEFAULT_DAYS_RANGE=7
MAX_DAYS_RANGE=365
SSH_TIMEOUT=10
LOG_BATCH_SIZE=1000

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Security Considerations

1. **Secret Key**: Generate a strong secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Database Passwords**: Use strong, unique passwords
3. **SSL/TLS**: Always use HTTPS in production
4. **Network Security**: Restrict access to internal services

## Local Development Deployment

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/wazuh-ai-companion.git
cd wazuh-ai-companion

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Local Services

```bash
# Start PostgreSQL and Redis using Docker
docker-compose -f docker-compose.dev.yml up -d postgres redis

# Initialize database
python scripts/init_db.py

# Start Ollama (if running locally)
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3
```

### 3. Run the Application

```bash
# Start the application
python main.py --reload

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check API documentation
open http://localhost:8000/docs
```

## Docker Deployment

### 1. Build Docker Image

```bash
# Build the application image
docker build -t wazuh-ai-companion:latest .

# Or build with specific tag
docker build -t wazuh-ai-companion:v2.0.0 .
```

### 2. Docker Compose Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale the application
docker-compose up -d --scale app=3
```

### 3. Docker Compose Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    image: wazuh-ai-companion:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - OLLAMA_HOST=ollama
    depends_on:
      - postgres
      - redis
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: wazuh_chat
      POSTGRES_USER: wazuh_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7
    command: redis-server --requirepass redis_password
    volumes:
      - redis_data:/data
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

## Kubernetes Deployment

### 1. Prerequisites

```bash
# Ensure kubectl is configured
kubectl cluster-info

# Create namespace
kubectl create namespace wazuh-ai-companion
```

### 2. Deploy Dependencies

```bash
# Deploy PostgreSQL
kubectl apply -f kubernetes/postgres-deployment.yaml

# Deploy Redis
kubectl apply -f kubernetes/redis-deployment.yaml

# Deploy Ollama
kubectl apply -f kubernetes/ollama-deployment.yaml
```

### 3. Deploy Application

```bash
# Create ConfigMap and Secrets
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Deploy the application
kubectl apply -f kubernetes/app-deployment.yaml

# Deploy services and ingress
kubectl apply -f kubernetes/nginx-deployment.yaml
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n wazuh-ai-companion

# Check services
kubectl get services -n wazuh-ai-companion

# Check ingress
kubectl get ingress -n wazuh-ai-companion

# View logs
kubectl logs -f deployment/wazuh-ai-companion -n wazuh-ai-companion
```

## Production Deployment

### 1. Pre-deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates obtained and configured
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Load balancer configured
- [ ] DNS records configured
- [ ] Security scanning completed
- [ ] Performance testing completed

### 2. Database Setup

```bash
# Create production database
createdb -h your-db-host -U postgres wazuh_chat_prod

# Run migrations
python scripts/init_db.py --environment production

# Create database user
psql -h your-db-host -U postgres -c "
CREATE USER wazuh_prod WITH PASSWORD 'secure_production_password';
GRANT ALL PRIVILEGES ON DATABASE wazuh_chat_prod TO wazuh_prod;
"
```

### 3. SSL/TLS Configuration

```bash
# Generate SSL certificate (using Let's Encrypt)
certbot certonly --nginx -d yourdomain.com

# Or use your existing certificates
cp your-cert.pem /etc/ssl/certs/wazuh-ai-companion.pem
cp your-key.pem /etc/ssl/private/wazuh-ai-companion.key
```

### 4. Production Deployment Steps

```bash
# 1. Deploy infrastructure components
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/persistent-volumes.yaml
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl apply -f kubernetes/redis-deployment.yaml

# 2. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s

# 3. Deploy application
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/app-deployment.yaml

# 4. Deploy ingress and load balancer
kubectl apply -f kubernetes/nginx-deployment.yaml

# 5. Configure auto-scaling
kubectl apply -f kubernetes/hpa.yaml

# 6. Verify deployment
kubectl get all -n wazuh-ai-companion
```

### 5. Post-deployment Verification

```bash
# Health check
curl -f https://yourdomain.com/health

# Metrics check
curl -f https://yourdomain.com/metrics

# API functionality test
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin_password"}'

# WebSocket test
wscat -c wss://yourdomain.com/ws/chat?token=your-jwt-token
```

## Monitoring and Observability

### 1. Prometheus and Grafana Setup

```bash
# Deploy monitoring stack
kubectl apply -f monitoring/prometheus.yml
kubectl apply -f monitoring/grafana/

# Access Grafana dashboard
kubectl port-forward svc/grafana 3000:3000
# Open http://localhost:3000 (admin/admin)
```

### 2. Log Aggregation

```bash
# Deploy ELK stack or use cloud logging
kubectl apply -f monitoring/elasticsearch.yaml
kubectl apply -f monitoring/logstash.yaml
kubectl apply -f monitoring/kibana.yaml
```

### 3. Alerting Configuration

```bash
# Configure Alertmanager
kubectl apply -f monitoring/alertmanager.yml

# Set up notification channels (Slack, email, etc.)
# Edit monitoring/notification-templates/
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check logs
kubectl logs deployment/wazuh-ai-companion -n wazuh-ai-companion

# Common causes:
# - Database connection issues
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

#### 2. Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from core.database import get_db
try:
    db = next(get_db())
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### 3. Redis Connection Issues

```bash
# Test Redis connectivity
kubectl exec -it deployment/redis -- redis-cli ping
```

#### 4. AI Service Issues

```bash
# Check Ollama connectivity
curl http://ollama-service:11434/api/tags

# Check if models are loaded
kubectl exec -it deployment/ollama -- ollama list
```

### Performance Issues

#### 1. High Memory Usage

```bash
# Check memory usage
kubectl top pods -n wazuh-ai-companion

# Scale up resources
kubectl patch deployment wazuh-ai-companion -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"requests":{"memory":"2Gi"},"limits":{"memory":"4Gi"}}}]}}}}'
```

#### 2. Slow Response Times

```bash
# Check application metrics
curl https://yourdomain.com/metrics | grep http_request_duration

# Scale horizontally
kubectl scale deployment wazuh-ai-companion --replicas=5
```

## Maintenance and Updates

### 1. Regular Maintenance Tasks

```bash
# Update dependencies
pip-compile requirements.in
pip-compile requirements-test.in

# Database maintenance
python scripts/db_manager.py --vacuum
python scripts/db_manager.py --analyze

# Clean up old logs
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.analytics_service import AnalyticsService
analytics = AnalyticsService()
deleted = analytics.cleanup_old_metrics(days_to_keep=90)
print(f'Cleaned up {deleted} old metrics')
"
```

### 2. Application Updates

```bash
# Rolling update
kubectl set image deployment/wazuh-ai-companion app=wazuh-ai-companion:v2.1.0

# Monitor rollout
kubectl rollout status deployment/wazuh-ai-companion

# Rollback if needed
kubectl rollout undo deployment/wazuh-ai-companion
```

### 3. Database Migrations

```bash
# Backup database before migration
kubectl exec -it deployment/postgres -- pg_dump -U wazuh_user wazuh_chat > backup.sql

# Run migrations
python scripts/migrate.py --version latest

# Verify migration
python scripts/db_manager.py --check-health
```

### 4. Security Updates

```bash
# Update base images
docker pull python:3.11-slim
docker pull postgres:15
docker pull redis:7

# Rebuild and deploy
docker build -t wazuh-ai-companion:v2.1.0 .
kubectl set image deployment/wazuh-ai-companion app=wazuh-ai-companion:v2.1.0
```

## Backup and Recovery

### 1. Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
kubectl exec -it deployment/postgres -- pg_dump -U wazuh_user wazuh_chat | gzip > backup_${DATE}.sql.gz
aws s3 cp backup_${DATE}.sql.gz s3://your-backup-bucket/database/
```

### 2. Application State Backup

```bash
# Backup Redis data
kubectl exec -it deployment/redis -- redis-cli BGSAVE
kubectl cp redis-pod:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb

# Backup vector store data
kubectl exec -it deployment/wazuh-ai-companion -- tar -czf /tmp/vectorstore.tar.gz /app/data/vectorstore
kubectl cp wazuh-ai-companion-pod:/tmp/vectorstore.tar.gz ./vectorstore_backup_$(date +%Y%m%d).tar.gz
```

### 3. Disaster Recovery

```bash
# Restore database
kubectl exec -i deployment/postgres -- psql -U wazuh_user wazuh_chat < backup.sql

# Restore Redis
kubectl cp redis_backup.rdb redis-pod:/data/dump.rdb
kubectl exec -it deployment/redis -- redis-cli DEBUG RESTART

# Restore vector store
kubectl cp vectorstore_backup.tar.gz wazuh-ai-companion-pod:/tmp/
kubectl exec -it deployment/wazuh-ai-companion -- tar -xzf /tmp/vectorstore_backup.tar.gz -C /app/data/
```

## Support and Documentation

- **API Documentation**: https://yourdomain.com/docs
- **Monitoring Dashboard**: https://yourdomain.com/grafana
- **Health Checks**: https://yourdomain.com/health
- **Metrics**: https://yourdomain.com/metrics

For additional support, please refer to the project repository or contact the development team.