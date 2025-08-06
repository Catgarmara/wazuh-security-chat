# Embedded Security AI Appliance - Installation Guide

Complete installation guide for the self-contained Security AI Appliance with embedded LlamaCpp engine.

## 🚀 Revolution in Security AI

Your appliance is a complete \"LM Studio for Security Operations\" - a turnkey solution that combines:
- **Embedded LLM Engine** (LlamaCpp - no Ollama required)
- **Model Management System** (HuggingFace integration)
- **User Authentication & Permissions** 
- **Resource Monitoring Dashboard**
- **Security Log Analysis Interface**

**Zero External Dependencies**: No API keys, external services, or complex setups required!

---

## Quick Installation (5 Minutes)

### Prerequisites

Only Docker is required - that's it!

```bash
# Verify Docker installation
docker --version          # Should show v24.0+
docker-compose --version  # Should show v2.0+

# If not installed:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### One-Command Deployment

```bash
# 1. Clone repository
git clone https://github.com/your-org/wazuh-ai.git
cd wazuh-ai

# 2. Create storage directories  
mkdir -p models data logs
chmod 755 models data logs

# 3. Launch complete appliance
docker-compose up -d

# 4. Verify deployment
curl http://localhost:8000/health
```

### Access Your Appliance

- 🌐 **Web Interface**: http://localhost:3000
- 📚 **API Documentation**: http://localhost:8000/docs  
- 💚 **Health Dashboard**: http://localhost:8000/health/detailed

---

## Detailed Installation

### System Requirements

**Minimum Configuration:**
- **CPU**: 8 cores (for model inference)
- **RAM**: 16GB (to load 7B models)
- **Storage**: 500GB (for model collection)
- **OS**: Linux, macOS, Windows (with WSL2)

**Recommended Production:**
- **CPU**: 16+ cores (better performance)
- **RAM**: 32GB+ (multiple concurrent models)
- **Storage**: 1TB NVMe SSD (fast model loading)
- **Network**: Stable internet (for initial model downloads)
- **GPU**: Optional NVIDIA GPU (3-10x faster inference)

**Enterprise Configuration:**
- **CPU**: 32+ cores
- **RAM**: 64GB+
- **Storage**: 2TB+ enterprise SSD
- **GPU**: NVIDIA RTX 4090 or A100
- **Network**: Dedicated bandwidth for model downloads

### Pre-Installation Checklist

```bash
# System resource check
echo \"CPU Cores: $(nproc)\"
echo \"RAM: $(free -h | grep Mem: | awk '{print $2}')\"
echo \"Disk Space: $(df -h . | tail -1 | awk '{print $4}')\"
echo \"Docker: $(docker --version)\"

# Recommended minimums check
if [ $(nproc) -ge 8 ] && [ $(free -m | grep Mem: | awk '{print $2}') -ge 16000 ]; then
    echo \"✅ System meets minimum requirements\"
else
    echo \"⚠️  System below recommended specifications\"
    echo \"   Consider upgrading for optimal performance\"
fi
```

### Step-by-Step Installation

#### 1. Environment Setup

```bash
# Create installation directory
mkdir -p ~/security-ai-appliance
cd ~/security-ai-appliance

# Clone repository
git clone https://github.com/your-org/wazuh-ai.git .

# Verify repository contents
ls -la
# Expected: docker-compose.yml, Dockerfile.embedded, requirements-embedded.txt, etc.
```

#### 2. Directory Structure Creation

```bash
# Create required directories
mkdir -p models data logs nginx/ssl monitoring/data

# Set proper permissions
chmod 755 models data logs
chmod 700 nginx/ssl

# Verify directory structure
tree -L 2
```

#### 3. Environment Configuration

```bash
# Create production environment file
cat > .env.production << EOF
# Core Appliance Configuration
AI_SERVICE_TYPE=embedded
MODELS_PATH=/app/models
MAX_CONCURRENT_MODELS=3

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=wazuh_chat
DB_USER=postgres
DB_PASSWORD=$(openssl rand -base64 32)

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Security Configuration
SECRET_KEY=$(openssl rand -base64 32)
ENVIRONMENT=production
DEBUG=false

# Model Management
ALLOW_MODEL_DOWNLOADS=admin
MODEL_SIZE_LIMIT=50GB
ENABLE_MODEL_SCANNING=true

# HuggingFace Integration
HF_CACHE_DIR=/app/models/.cache
HF_DATASETS_CACHE=/app/data/.cache

# System Limits
MAX_UPLOAD_SIZE=100MB
REQUEST_TIMEOUT=300
WORKER_TIMEOUT=600
EOF

# Secure environment file
chmod 600 .env.production
```

#### 4. SSL Certificate Setup (Production)

```bash
# Generate self-signed certificates
mkdir -p nginx/ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -days 365 -nodes \
  -subj \"/C=US/ST=State/L=City/O=YourOrg/CN=$(hostname)\"

# Or use Let's Encrypt for public deployments
# certbot certonly --standalone -d your-domain.com
# cp /etc/letsencrypt/live/your-domain.com/*.pem nginx/ssl/
```

#### 5. GPU Support Setup (Optional)

```bash
# Install NVIDIA Docker support
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
   && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

#### 6. Appliance Deployment

```bash
# Deploy with production environment
docker-compose --env-file .env.production up -d

# Monitor deployment progress
docker-compose logs -f --tail=50

# Wait for all services to be healthy (2-5 minutes)
echo \"Waiting for services to start...\"
sleep 120

# Verify all services are running
docker-compose ps
```

#### 7. Initial Configuration

```bash
# Create admin user
docker-compose exec app python -c \"
from core.database import SessionLocal
from models.database import User
from core.security import get_password_hash
import sys

db = SessionLocal()
try:
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.username == 'admin').first()
    if existing_admin:
        print('Admin user already exists')
        sys.exit(0)
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@yourcompany.com',
        full_name='System Administrator',
        hashed_password=get_password_hash('admin123'),
        is_admin=True,
        is_active=True
    )
    db.add(admin)
    db.commit()
    print('✅ Admin user created successfully')
    print('   Username: admin')
    print('   Password: admin123')
    print('   Please change this password after first login!')
except Exception as e:
    print(f'❌ Error creating admin user: {e}')
finally:
    db.close()
\"

# Verify admin user creation
curl -X POST \"http://localhost:8000/api/auth/login\" \
  -H \"Content-Type: application/json\" \
  -d '{\"username\":\"admin\",\"password\":\"admin123\"}' | jq '.'
```

#### 8. Health Verification

```bash
# Comprehensive health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
echo \"🔍 === Embedded Security AI Appliance Health Check ===\"

# Core API health
echo \"1. Core API Health:\"
curl -f http://localhost:8000/health || echo \"❌ Core API failed\"

# Detailed system health
echo \"2. System Health Details:\"
curl -s http://localhost:8000/health/detailed | jq '.services' || echo \"❌ Detailed health failed\"

# Embedded AI service
echo \"3. Embedded AI Engine:\"
curl -s http://localhost:8000/api/embedded-ai/health | jq '.status, .engine' || echo \"❌ AI service failed\"

# HuggingFace integration
echo \"4. HuggingFace Integration:\"
curl -s http://localhost:8000/api/huggingface/categories | jq '.categories | length' && echo \"✅ HF integration working\" || echo \"❌ HF integration failed\"

# Frontend accessibility
echo \"5. Web Interface:\"
curl -f http://localhost:3000/api/health >/dev/null 2>&1 && echo \"✅ Frontend accessible\" || echo \"❌ Frontend failed\"

# Database connectivity
echo \"6. Database Connection:\"
docker-compose exec -T postgres pg_isready -U postgres && echo \"✅ PostgreSQL ready\" || echo \"❌ Database failed\"

# Redis connectivity
echo \"7. Redis Cache:\"
docker-compose exec -T redis redis-cli ping >/dev/null 2>&1 && echo \"✅ Redis ready\" || echo \"❌ Redis failed\"

# Model storage
echo \"8. Model Storage:\"
if [ -d \"./models\" ]; then
    echo \"✅ Models directory exists ($(du -sh ./models 2>/dev/null | cut -f1 || echo '0B') used)\"
else
    echo \"❌ Models directory missing\"
fi

# Resource usage
echo \"9. Resource Usage:\"
docker stats --no-stream --format \"table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\" | head -5

echo \"✅ === Health Check Complete ===\"
echo \"\"
echo \"🌐 Access your appliance at:\"
echo \"   Web Interface: http://localhost:3000\"
echo \"   API Documentation: http://localhost:8000/docs\"
echo \"   System Health: http://localhost:8000/health/detailed\"
EOF

chmod +x health_check.sh
./health_check.sh
```

---

## Post-Installation Setup

### First Login and Model Download

1. **Access Web Interface**: Navigate to http://localhost:3000
2. **Login**: Use admin/admin123 (change password immediately)
3. **Browse Models**: Go to Models → Browse HuggingFace
4. **Download First Model**:
   - Search for \"llama-2-7b-chat\"
   - Select Q4_0 quantization (4.2GB)
   - Click Download
   - Monitor progress in Downloads tab

### User Management Setup

```bash
# Create additional users via API
create_user() {
    local username=$1
    local email=$2
    local full_name=$3
    local is_admin=${4:-false}
    
    # Get admin JWT token first
    TOKEN=$(curl -s -X POST \"http://localhost:8000/api/auth/login\" \
      -H \"Content-Type: application/json\" \
      -d \"{\\\"username\\\":\\\"admin\\\",\\\"password\\\":\\\"admin123\\\"}\" | jq -r '.access_token')
    
    # Create user
    curl -X POST \"http://localhost:8000/api/auth/register\" \
      -H \"Content-Type: application/json\" \
      -H \"Authorization: Bearer $TOKEN\" \
      -d \"{
        \\\"username\\\": \\\"$username\\\",
        \\\"email\\\": \\\"$email\\\",
        \\\"full_name\\\": \\\"$full_name\\\",
        \\\"password\\\": \\\"temp123\\\",
        \\\"is_admin\\\": $is_admin
      }\"
}

# Create sample users
create_user \"analyst\" \"analyst@yourcompany.com\" \"Security Analyst\" false
create_user \"viewer\" \"viewer@yourcompany.com\" \"Security Viewer\" false
```

### Security Hardening

```bash
# Change default passwords
echo \"🔐 Security Hardening Checklist:\"
echo \"1. Change admin password (do this now!)\"
echo \"2. Configure firewall rules\"
echo \"3. Set up SSL certificates\"
echo \"4. Review user permissions\"
echo \"5. Enable audit logging\"

# Firewall rules
sudo ufw allow 22      # SSH
sudo ufw allow 443     # HTTPS
sudo ufw allow 3000    # Frontend (or restrict to internal network)
sudo ufw deny 8000     # Block direct API access
sudo ufw enable

# SSL redirect configuration
cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream app_backend {
        server app:8000;
    }
    
    upstream frontend {
        server frontend:3000;
    }
    
    server {
        listen 80;
        return 301 https://\$host\$request_uri;
    }
    
    server {
        listen 443 ssl;
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
        
        location /api/ {
            proxy_pass http://app_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
    }
}
EOF

# Deploy with SSL
docker-compose --profile ssl up -d
```

---

## Production Deployment Considerations

### High Availability Setup

```yaml
# docker-compose.prod.yml additions
version: '3.8'
services:
  app:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        
  nginx:
    deploy:
      replicas: 2
      
volumes:
  models:
    driver: local
    driver_opts:
      type: nfs
      o: addr=your-nfs-server,rw
      device: \":/path/to/models\"
```

### Monitoring and Alerting

```bash
# Deploy with monitoring stack
docker-compose --profile monitoring up -d

# Configure Grafana dashboards
curl -X POST \"http://admin:admin@localhost:3001/api/dashboards/db\" \
  -H \"Content-Type: application/json\" \
  -d @monitoring/grafana/dashboards/embedded-ai-dashboard.json

# Set up alerts
curl -X POST \"http://admin:admin@localhost:3001/api/alert-notifications\" \
  -H \"Content-Type: application/json\" \
  -d '{
    \"name\": \"slack-alerts\",
    \"type\": \"slack\",
    \"settings\": {
      \"url\": \"YOUR_SLACK_WEBHOOK_URL\",
      \"channel\": \"#security-alerts\"
    }
  }'
```

### Backup Configuration

```bash
# Automated backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=\"/backup/security-ai-$(date +%Y%m%d)\"
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T postgres pg_dump -U postgres wazuh_chat > $BACKUP_DIR/database.sql

# Model storage backup
tar -czf $BACKUP_DIR/models.tar.gz ./models

# Configuration backup
cp -r docker-compose.yml .env.production nginx/ $BACKUP_DIR/

# Vector store backup
tar -czf $BACKUP_DIR/data.tar.gz ./data

echo \"✅ Backup completed: $BACKUP_DIR\"
find /backup -name \"security-ai-*\" -mtime +30 -delete  # Clean old backups
EOF

chmod +x backup.sh

# Setup automated backups
echo \"0 2 * * * /path/to/backup.sh\" | crontab -
```

---

## Troubleshooting Installation

### Common Installation Issues

**Docker Permission Issues:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Test docker access
docker run hello-world
```

**Port Conflicts:**
```bash
# Check port usage
netstat -tlnp | grep -E ':(3000|8000|5432|6379)'

# Change ports in docker-compose.yml if needed
sed -i 's/3000:3000/3001:3000/' docker-compose.yml
```

**Insufficient Disk Space:**
```bash
# Check available space
df -h

# Clean Docker system
docker system prune -a -f

# Move models directory to larger drive
sudo mv ./models /path/to/larger/drive/models
ln -s /path/to/larger/drive/models ./models
```

**Memory Issues:**
```bash
# Check memory usage
free -h

# Add swap space
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Service-Specific Issues

**Database Won't Start:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Reset database if corrupted
docker-compose down
docker volume rm wazuh-ai_postgres_data
docker-compose up -d postgres
```

**Embedded AI Service Issues:**
```bash
# Check AI service logs
docker-compose logs app | grep -i \"embedded_ai\"

# Restart AI service
docker-compose restart app

# Check model loading
curl http://localhost:8000/api/embedded-ai/health
```

### Recovery Procedures

**Complete System Recovery:**
```bash
# Stop all services
docker-compose down

# Backup current state
cp -r models models.backup
cp -r data data.backup

# Clean and restart
docker-compose down -v
docker system prune -a -f
docker-compose up -d --build

# Restore data
cp -r models.backup/* models/
cp -r data.backup/* data/
```

---

## Maintenance

### Regular Maintenance Tasks

**Weekly:**
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean unused resources
docker system prune -f

# Check health
./health_check.sh
```

**Monthly:**
```bash
# Full system backup
./backup.sh

# Update models
# Review and update model collection

# Security updates
sudo apt update && sudo apt upgrade -y
```

**Quarterly:**
```bash
# Full security audit
# Review user permissions
# Update SSL certificates
# Performance optimization review
```

---

## Success! 🎉

Your Embedded Security AI Appliance is now installed and ready for use!

**Next Steps:**
1. 🔐 Change the default admin password
2. 📥 Download your first AI model
3. 👥 Create user accounts for your team
4. 🔧 Configure SIEM integration
5. 📊 Set up monitoring dashboards
6. 🛡️ Enable security hardening features

**Key URLs:**
- **Main Interface**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Dashboard**: http://localhost:8000/health/detailed
- **Model Browser**: http://localhost:3000/models/browse

**Support Resources:**
- 📖 Model Management Guide: `docs/MODEL_MANAGEMENT_GUIDE.md`
- 🔧 Operations Manual: `docs/OPERATIONS_MANUAL.md`
- 🐛 Troubleshooting: `docs/TROUBLESHOOTING.md`

Your appliance is completely self-contained with no external dependencies - everything you need for advanced security AI analysis is included!