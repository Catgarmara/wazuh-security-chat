# Embedded Security AI Appliance - Deployment Guide

This comprehensive guide covers deployment of the self-contained Security AI Appliance with embedded LlamaCpp engine and zero external dependencies.

**🚀 Revolutionary Architecture**: Complete standalone appliance with no Ollama, API keys, or external services required.
**🎯 Implementation Status**: All deployment methods fully implemented with embedded AI capabilities.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Configurations](#environment-configurations)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Monitoring Setup](#monitoring-setup)
7. [Production Considerations](#production-considerations)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Prerequisites

### System Requirements

**Minimum Requirements (Embedded Appliance):**
- CPU: 8 cores (for model inference)
- RAM: 16GB (for model loading)
- Storage: 500GB+ (for model storage)
- OS: Linux, macOS, or Windows with WSL2

**Recommended for Production:**
- CPU: 16+ cores (better model performance)
- RAM: 32GB+ (multiple concurrent models)
- Storage: 1TB+ NVMe SSD (faster model loading)
- GPU: Optional NVIDIA GPU (significant acceleration)
- OS: Linux (Ubuntu 20.04+ or CentOS 8+)

### Software Dependencies

**Required (Zero External Dependencies!):**
- Docker 24.0+
- Docker Compose 2.0+
- Git

**That's It! No Additional Software Required:**
- ❌ No Ollama installation
- ❌ No external LLM services 
- ❌ No API key management
- ❌ No model server setup

**Optional Enhancements:**
- NVIDIA Docker runtime (for GPU acceleration)
- kubectl 1.25+ (for Kubernetes deployment)
- CUDA 12.0+ (for optimal GPU performance)

### Installation Commands

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git curl

# CentOS/RHEL
sudo yum install -y docker docker-compose git curl

# macOS (with Homebrew)
brew install docker docker-compose git

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-username/wazuh-ai.git
cd wazuh-ai
```

### 2. Zero-Touch Appliance Deployment

```bash
# Create required directories
mkdir -p models data logs

# Set proper permissions
chmod 755 models data logs

# Launch complete self-contained appliance (one command!)
docker-compose up -d

# Check deployment status
docker-compose ps
```

### 3. Access Your Security AI Appliance

- **🎯 Main Interface**: http://localhost:3000 (Next.js web app)
- **📚 Model Browser**: http://localhost:3000/models/browse
- **👥 User Management**: http://localhost:3000/admin/users  
- **📊 System Dashboard**: http://localhost:3000/dashboard
- **🔧 API Documentation**: http://localhost:8000/docs
- **💚 Health Check**: http://localhost:8000/health
- **📈 Metrics**: http://localhost:8000/metrics

## Environment Configurations

### Development Environment

**Purpose**: Local development and testing
**Features**: 
- Hot reloading
- Debug mode enabled
- Full monitoring stack
- Sample data

**Configuration**:
```yaml
environment: development
debug: true
compose_file: docker-compose.yml
profiles: [monitoring]
```

### Staging Environment

**Purpose**: Pre-production testing
**Features**:
- Production-like configuration
- Monitoring enabled
- Performance testing
- Security hardening

**Configuration**:
```yaml
environment: staging
debug: false
compose_file: docker-compose.prod.yml
profiles: [monitoring]
```

### Production Environment

**Purpose**: Live production deployment
**Features**:
- Optimized performance
- Security hardened
- High availability
- Backup enabled

**Configuration**:
```yaml
environment: production
debug: false
compose_file: docker-compose.prod.yml
profiles: []
```

## Docker Compose Deployment

### Embedded Appliance Deployment

```bash
# Launch complete appliance with monitoring
docker-compose --profile monitoring up -d --build

# Create admin user (first time setup)
docker-compose exec app python -c "
from core.database import SessionLocal
from models.database import User
from core.security import get_password_hash

db = SessionLocal()
admin = User(
    username='admin',
    email='admin@company.com', 
    full_name='System Administrator',
    hashed_password=get_password_hash('admin123'),
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin user created: admin/admin123')
"

# View appliance logs
docker-compose logs -f

# Check all services status
docker-compose ps
```

### Production Appliance Deployment

```bash
# Create production environment file
cp .env.example .env.production

# Configure production settings
cat > .env.production << EOF
# Core Configuration
AI_SERVICE_TYPE=embedded
MODELS_PATH=/app/models
MAX_CONCURRENT_MODELS=3

# Database
DB_HOST=postgres
DB_NAME=wazuh_chat
DB_USER=postgres
DB_PASSWORD=$(openssl rand -base64 32)

# Security
SECRET_KEY=$(openssl rand -base64 32)

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
EOF

# Deploy production appliance
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Verify appliance health
curl -f http://localhost:8000/health/detailed
```

### Service Configuration

#### Application Service
```yaml
app:
  build:
    context: .
    dockerfile: Dockerfile
    target: production
  environment:
    - ENVIRONMENT=production
    - DEBUG=false
  deploy:
    replicas: 2
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
```

#### Database Service
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=${DB_NAME}
    - POSTGRES_USER=${DB_USER}
    - POSTGRES_PASSWORD=${DB_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
```

#### Redis Service
```yaml
redis:
  image: redis:7-alpine
  volumes:
    - redis_data:/data
    - ./redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
  command: redis-server /usr/local/etc/redis/redis.conf
```

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify cluster access
kubectl cluster-info
```

### Deployment Steps

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Create secrets
kubectl apply -f kubernetes/secrets.yaml

# Create persistent volumes
kubectl apply -f kubernetes/persistent-volumes.yaml

# Deploy PostgreSQL
kubectl apply -f kubernetes/postgres-deployment.yaml

# Deploy Redis
kubectl apply -f kubernetes/redis-deployment.yaml

# Note: No Ollama deployment needed - embedded LlamaCpp used instead!

# Deploy application
kubectl apply -f kubernetes/app-deployment.yaml

# Deploy Nginx ingress
kubectl apply -f kubernetes/nginx-deployment.yaml

# Deploy monitoring (optional)
kubectl apply -f kubernetes/monitoring-deployment.yaml

# Configure auto-scaling
kubectl apply -f kubernetes/hpa.yaml
```

### Verification

```bash
# Check pod status
kubectl get pods -n wazuh

# Check services
kubectl get services -n wazuh

# Check ingress
kubectl get ingress -n wazuh

# View logs
kubectl logs -f deployment/wazuh-app -n wazuh

# Port forward for testing
kubectl port-forward service/wazuh-app 8000:8000 -n wazuh
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment wazuh-app --replicas=5 -n wazuh

# Auto-scaling configuration
kubectl autoscale deployment wazuh-app --cpu-percent=70 --min=3 --max=10 -n wazuh

# Check HPA status
kubectl get hpa -n wazuh
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'wazuh-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboards

Available dashboards:
- **System Overview**: Application health and performance
- **AI Performance**: AI query metrics and response times
- **Business Metrics**: User engagement and security alerts
- **Infrastructure**: System resources and container metrics
- **Health Monitoring**: Service health and SLA compliance

### Alerting Rules

Critical alerts configured:
- Application down
- High error rates
- Database connectivity issues
- High resource usage
- Security incidents

## Production Considerations

### Security

#### SSL/TLS Configuration
```bash
# Generate SSL certificates for production
mkdir -p ./nginx/ssl
openssl req -x509 -newkey rsa:4096 -keyout ./nginx/ssl/key.pem \
  -out ./nginx/ssl/cert.pem -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Deploy with SSL profile
docker-compose --profile ssl up -d
```

#### Embedded Appliance Security
```bash
# Required production environment variables
SECRET_KEY=$(openssl rand -base64 32)  # Auto-generate secure key
DB_PASSWORD=$(openssl rand -base64 32) # Auto-generate DB password
AI_SERVICE_TYPE=embedded               # Use embedded engine
MODELS_PATH=/app/models               # Local model storage

# Model access security
MAX_CONCURRENT_MODELS=3               # Resource limits
ALLOW_MODEL_DOWNLOADS=admin           # Restrict who can download
MODEL_SIZE_LIMIT=50GB                # Prevent storage exhaustion
```

#### Network Security
- Use private networks for internal communication
- Configure firewall rules
- Enable rate limiting
- Implement proper authentication

### Performance Optimization

#### Database Tuning
```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET max_connections = 100;
```

#### Redis Configuration
```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### Application Tuning
```bash
# Uvicorn workers configuration
uvicorn app.main:app --workers 4 --worker-connections 1000
```

### High Availability

#### Load Balancing
```nginx
# nginx.conf
upstream wazuh_app {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```

#### Database Replication
```yaml
# PostgreSQL master-slave setup
postgres-master:
  image: postgres:15-alpine
  environment:
    - POSTGRES_REPLICATION_MODE=master
    - POSTGRES_REPLICATION_USER=replicator
    - POSTGRES_REPLICATION_PASSWORD=replication_password

postgres-slave:
  image: postgres:15-alpine
  environment:
    - POSTGRES_REPLICATION_MODE=slave
    - POSTGRES_MASTER_HOST=postgres-master
```

### Backup Strategy

#### Database Backup
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec postgres pg_dump -U postgres wazuh_chat > \
  "$BACKUP_DIR/wazuh_chat_$DATE.sql"

# Retain only last 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
```

#### Volume Backup
```bash
# Backup Docker volumes
docker run --rm -v postgres_data:/data -v /backup:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
docker-compose logs app

# Common causes:
# - Database connection issues
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U postgres

# Check connection from app
docker-compose exec app python -c "
from core.database import engine
print(engine.execute('SELECT 1').scalar())
"
```

#### High Memory Usage
```bash
# Check container resource usage
docker stats

# Check system resources
free -h
df -h

# Optimize container limits
docker-compose up -d --scale app=2
```

#### Monitoring Issues
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana datasource
curl -u admin:admin http://localhost:3000/api/datasources

# Restart monitoring stack
docker-compose --profile monitoring restart
```

### Performance Issues

#### Slow Database Queries
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### High CPU Usage
```bash
# Check container CPU usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Profile application
docker-compose exec app python -m cProfile -o profile.stats app/main.py
```

### Log Analysis

#### Application Logs
```bash
# View real-time logs
docker-compose logs -f app

# Search logs
docker-compose logs app | grep ERROR

# Export logs
docker-compose logs app > app_logs_$(date +%Y%m%d).log
```

#### System Logs
```bash
# Check Docker daemon logs
sudo journalctl -u docker.service

# Check system resources
dmesg | grep -i memory
dmesg | grep -i oom
```

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Monitor application health
- Check error logs
- Verify backup completion
- Review security alerts

#### Weekly
- Update security patches
- Clean up old logs
- Review performance metrics
- Test backup restoration

#### Monthly
- Update dependencies
- Review and rotate secrets
- Capacity planning review
- Security audit

### Update Procedures

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Build new images
docker-compose build --no-cache

# Rolling update
docker-compose up -d --no-deps app

# Verify deployment
python3 scripts/test-deployment.py
```

#### Database Migrations
```bash
# Run migrations
docker-compose exec app alembic upgrade head

# Verify migration
docker-compose exec app alembic current
```

#### Security Updates
```bash
# Update base images
docker-compose pull

# Rebuild with latest patches
docker-compose build --pull --no-cache

# Deploy updates
docker-compose up -d
```

### Appliance Monitoring and Alerting

#### Comprehensive Health Checks
```bash
# Automated appliance health check script
#!/bin/bash
echo "🔍 Checking Embedded Security AI Appliance..."

# Core API health
curl -f http://localhost:8000/health || exit 1
echo "✅ Core API healthy"

# Embedded AI service health  
curl -f http://localhost:8000/api/embedded-ai/health || exit 1
echo "✅ Embedded AI engine healthy"

# HuggingFace integration
curl -f http://localhost:8000/api/huggingface/categories || exit 1
echo "✅ HuggingFace integration working"

# Frontend health
curl -f http://localhost:3000/api/health || exit 1
echo "✅ Web interface healthy"

# Model storage check
if [ -d "./models" ] && [ "$(ls -A ./models)" ]; then
    echo "✅ Models directory accessible with $(ls ./models | wc -l) models"
else
    echo "⚠️ Models directory empty - download models via web interface"
fi

echo "🎉 Embedded Security AI Appliance fully operational!"
```

#### Performance Monitoring
```bash
# Resource usage monitoring
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

#### Log Monitoring
```bash
# Error rate monitoring
docker-compose logs app --since 1h | grep -c ERROR

# Response time monitoring
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
```