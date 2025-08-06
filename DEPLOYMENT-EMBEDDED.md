# Embedded Security AI Appliance - Deployment Guide

## Overview

This deployment guide covers the standalone security AI appliance - a completely self-contained system with embedded LLM capabilities, HuggingFace model management, and zero external dependencies.

**No Ollama Required** - Built with LlamaCpp for embedded model inference.

## 🚀 Quick Start

### 1. Prerequisites

- **Docker & Docker Compose**: Latest versions
- **Hardware Requirements**:
  - CPU: 8+ cores recommended
  - RAM: 16GB minimum, 32GB+ recommended  
  - Storage: 500GB+ for model storage
  - GPU: Optional NVIDIA GPU for acceleration

### 2. Deploy the Appliance

```bash
# Clone and navigate to directory
cd wazuh-ai

# Create required directories
mkdir -p models data logs

# Set permissions
chmod 755 models data logs

# Deploy with Docker Compose
docker-compose up -d

# Check services
docker-compose ps
```

### 3. Access the Interface

- **Web Interface**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📋 System Architecture

### Core Services

```yaml
Services:
  - app: FastAPI backend with embedded AI
  - frontend: Next.js management interface  
  - postgres: User and system data
  - redis: Caching and sessions
  - nginx: Reverse proxy (optional)
  - monitoring: Prometheus/Grafana stack (optional)

Removed:
  - ollama: Replaced with embedded LlamaCpp
```

### Key Features

✅ **Embedded LLM Engine** - LlamaCpp integration  
✅ **Model Management** - HuggingFace browsing and downloading  
✅ **User Management** - Role-based access control  
✅ **Real-time Monitoring** - System resources and performance  
✅ **Vector Store** - FAISS for log analysis  
✅ **Hot-swapping** - Switch models without restart  

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
AI_SERVICE_TYPE=embedded
MODELS_PATH=/app/models
MAX_CONCURRENT_MODELS=3

# Database
DB_HOST=postgres
DB_NAME=wazuh_chat
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
SECRET_KEY=your_secure_secret_key_32_chars_minimum
```

### GPU Support (Optional)

For NVIDIA GPU acceleration:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Deploy with GPU support
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## 📦 Model Management

### Adding Your First Model

1. **Access Model Browser**:
   - Navigate to http://localhost:3000
   - Go to "Models" → "Browse HuggingFace"

2. **Search and Download**:
   - Search for security models or general-purpose models
   - Select quantization (Q4_0 recommended for balance)
   - Click "Download"

3. **Load Model**:
   - Go to "Models" → "Active Models"
   - Click "Load" on downloaded model
   - Model will be available for chat/analysis

### Recommended Models

```yaml
Security Focused:
  - microsoft/SecurityBERT-base (1.2GB)
  - Custom security-trained models

General Purpose:
  - meta-llama/llama-2-7b-chat (Q4_0: ~4GB)
  - mistralai/mistral-7b-instruct (Q4_0: ~4GB)

Code Analysis:
  - codellama/codellama-7b-instruct (Q4_0: ~4GB)
```

## 👥 User Management

### Creating Admin User

```bash
# Connect to app container
docker-compose exec app bash

# Create admin user (run inside container)
python -c "
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
```

### Role Configuration

Available roles with permissions:

- **Administrator**: Full system access
- **Security Analyst**: Model usage, log analysis
- **Viewer**: Read-only access to logs

## 🔍 System Monitoring

### Health Checks

```bash
# Overall system health
curl http://localhost:8000/health

# Detailed service status  
curl http://localhost:8000/health/detailed

# Embedded AI service
curl http://localhost:8000/api/embedded-ai/health

# HuggingFace integration
curl http://localhost:8000/api/huggingface/categories
```

### Resource Monitoring

**Web Dashboard**: http://localhost:3000 → "Dashboard"

- CPU, Memory, GPU usage
- Model performance metrics
- Download progress
- Active users and sessions

### Logs

```bash
# Application logs
docker-compose logs app

# All services
docker-compose logs

# Follow logs
docker-compose logs -f app
```

## 🛠 Maintenance

### Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/wazuh-ai-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T postgres pg_dump -U postgres wazuh_chat > $BACKUP_DIR/database.sql

# Model storage
tar -czf $BACKUP_DIR/models.tar.gz ./models

# Configuration
cp docker-compose.yml $BACKUP_DIR/
cp .env $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d

# Check status
docker-compose ps
```

### Model Cleanup

```bash
# Remove unused models (via API)
curl -X DELETE "http://localhost:8000/api/embedded-ai/models/unused"

# Clear completed downloads
curl -X DELETE "http://localhost:8000/api/huggingface/downloads/completed"
```

## 🔒 Security Hardening

### SSL/TLS Configuration

```bash
# Generate certificates
mkdir -p ./nginx/ssl
openssl req -x509 -newkey rsa:4096 -keyout ./nginx/ssl/key.pem -out ./nginx/ssl/cert.pem -days 365 -nodes

# Update nginx configuration for HTTPS
# Deploy with SSL profile
docker-compose --profile ssl up -d
```

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 443   # HTTPS
sudo ufw deny 8000   # Block direct API access
sudo ufw deny 3000   # Block direct frontend access
sudo ufw enable
```

### User Access Control

- Enable 2FA in user settings
- Regular password rotation
- Limit model download permissions
- Monitor user activity logs

## 📊 Performance Optimization

### Resource Allocation

```yaml
Model Loading Strategy:
  - Small models (1-3B): Q4_0 quantization
  - Medium models (7B): Q4_0 for speed, Q5_0 for quality
  - Large models (13B+): Careful resource planning

Memory Management:
  - Reserve 4GB for system
  - 4-8GB per loaded 7B model
  - Monitor swap usage

CPU Optimization:
  - 2-4 cores per active model
  - Enable CPU affinity for performance
```

### Performance Tuning

```bash
# Increase file descriptors
echo "fs.file-max = 65536" >> /etc/sysctl.conf

# Memory optimization
echo "vm.swappiness = 10" >> /etc/sysctl.conf

# Apply changes
sysctl -p
```

## 🚨 Troubleshooting

### Common Issues

**Models not loading**:
```bash
# Check disk space
df -h
# Check model file integrity
ls -la ./models/
# Check service logs
docker-compose logs app
```

**Download failures**:
```bash
# Check network connectivity
curl -I https://huggingface.co
# Verify download directory permissions
ls -la ./models/
# Restart HuggingFace service
docker-compose restart app
```

**Performance issues**:
```bash
# Monitor resource usage
docker stats
# Check GPU utilization (if available)
nvidia-smi
# Review memory usage
free -h
```

### Recovery Procedures

**Database corruption**:
```bash
# Restore from backup
docker-compose down
docker-compose exec postgres psql -U postgres -c "DROP DATABASE wazuh_chat;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE wazuh_chat;"
docker-compose exec -T postgres psql -U postgres wazuh_chat < backup/database.sql
docker-compose up -d
```

**Model corruption**:
```bash
# Clear and re-download
rm -rf ./models/*
# Access web interface and re-download models
```

## 📞 Support

### Logs Collection

```bash
# Generate support bundle
./scripts/collect-logs.sh

# Manual collection
docker-compose logs > support-logs-$(date +%Y%m%d).txt
docker-compose ps > support-status-$(date +%Y%m%d).txt
df -h > support-disk-$(date +%Y%m%d).txt
```

### Health Report

```bash
# System health report
curl -s http://localhost:8000/health/detailed | jq '.'
```

---

## 🎉 Success!

Your standalone security AI appliance is now running! 

**Next Steps**:
1. Log in as admin and create users
2. Download your first security model
3. Start analyzing security logs
4. Configure alerts and monitoring

**Web Interface**: http://localhost:3000  
**Admin Panel**: http://localhost:3000/admin  

The appliance is completely self-contained with no external dependencies!