# Docker Setup Guide for Wazuh AI Companion

This guide provides comprehensive instructions for setting up and running the Wazuh AI Companion using Docker containers.

## 🏗️ Architecture Overview

The application consists of the following services:

### Core Services
- **Frontend** (`frontend`): Next.js 14 application on port 3000
- **Backend** (`app`): FastAPI application on port 8000
- **Database** (`postgres`): PostgreSQL 15 database on port 5432
- **Cache** (`redis`): Redis cache on port 6379
- **LLM** (`ollama`): Ollama LLM service on port 11434

### Optional Services
- **Nginx** (`nginx`): Reverse proxy on ports 80/443
- **Prometheus** (`prometheus`): Metrics collection on port 9090
- **Grafana** (`grafana`): Monitoring dashboards on port 3001 (production)
- **Alertmanager** (`alertmanager`): Alert handling on port 9093

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose**
   ```bash
   # Install Docker Desktop (recommended)
   # Or install Docker Engine + Docker Compose
   docker --version
   docker-compose --version
   ```

2. **System Requirements**
   - RAM: 8GB minimum, 16GB recommended
   - Disk: 10GB free space
   - CPU: 4 cores recommended
   - GPU: Optional (for Ollama LLM acceleration)

### Development Environment

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd wazuh-ai
   cp .env.example .env  # Configure your environment variables
   ```

2. **Start Development Environment**
   ```bash
   # Using the setup script (recommended)
   ./scripts/docker-setup.sh dev --detach

   # Or using docker-compose directly
   docker-compose up -d
   ```

3. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

### Production Environment

1. **Configure Environment**
   ```bash
   # Copy and configure production environment
   cp .env.example .env
   
   # Set required production variables
   export SECRET_KEY="your-secret-key-here"
   export DB_PASSWORD="secure-database-password"
   export GRAFANA_PASSWORD="secure-grafana-password"
   ```

2. **Start Production Environment**
   ```bash
   ./scripts/docker-setup.sh prod --detach
   ```

3. **Access the Application**
   - Application: http://localhost:80
   - Grafana: http://localhost:3001
   - Prometheus: http://localhost:9090

## 🛠️ Management Commands

### Setup Script Usage

The `docker-setup.sh` script provides easy management:

```bash
# Development
./scripts/docker-setup.sh dev          # Start development environment
./scripts/docker-setup.sh dev --detach # Start in background

# Production
./scripts/docker-setup.sh prod --detach

# Management
./scripts/docker-setup.sh stop         # Stop all services
./scripts/docker-setup.sh restart      # Restart all services
./scripts/docker-setup.sh status       # Show service status
./scripts/docker-setup.sh health       # Check service health
./scripts/docker-setup.sh logs         # Show all logs
./scripts/docker-setup.sh logs frontend # Show specific service logs

# Building
./scripts/docker-setup.sh build        # Build all images
./scripts/docker-setup.sh rebuild      # Rebuild without cache

# Database
./scripts/docker-setup.sh db-init      # Initialize database
./scripts/docker-setup.sh db-migrate   # Run migrations

# Maintenance
./scripts/docker-setup.sh clean        # Clean up containers
./scripts/docker-setup.sh reset        # Complete reset
./scripts/docker-setup.sh shell app    # Open shell in service
```

### Direct Docker Compose Commands

```bash
# Development
docker-compose up -d                    # Start all services
docker-compose up -d frontend          # Start specific service
docker-compose down                     # Stop all services
docker-compose logs -f frontend         # Follow logs
docker-compose exec frontend sh        # Open shell

# Production
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml down

# Building
docker-compose build                    # Build all images
docker-compose build --no-cache frontend # Rebuild specific service
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required for Production
SECRET_KEY=your-secret-key-minimum-32-characters
DB_PASSWORD=secure-database-password
GRAFANA_PASSWORD=secure-grafana-password
GRAFANA_SECRET_KEY=grafana-secret-key

# Optional Database Configuration
DB_NAME=wazuh_chat
DB_USER=postgres

# Frontend URLs (for production)
FRONTEND_API_URL=http://your-domain.com:8000
FRONTEND_WS_URL=ws://your-domain.com:8000

# Feature Flags
NEXT_PUBLIC_SIEM_ENABLED=true
NEXT_PUBLIC_FEATURE_MODEL_MANAGEMENT=true
NEXT_PUBLIC_FEATURE_SIEM_DASHBOARD=true
NEXT_PUBLIC_FEATURE_THREAT_CORRELATION=true
NEXT_PUBLIC_FEATURE_ALERT_MANAGEMENT=true
```

### Frontend Configuration

Frontend-specific environment variables (in `frontend/.env.docker`):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME="Wazuh AI Companion"
NEXT_PUBLIC_APP_VERSION="2.0.0"
NEXT_PUBLIC_THEME=dark
NEXT_PUBLIC_AUTH_ENABLED=true
```

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000/api/health
- Detailed Backend Health: http://localhost:8000/health/detailed

### Service Monitoring

```bash
# Check all service health
./scripts/docker-setup.sh health

# View service status
./scripts/docker-setup.sh status

# Monitor logs in real-time
./scripts/docker-setup.sh logs

# Monitor specific service
docker-compose logs -f frontend
```

### Prometheus Metrics

Access Prometheus at http://localhost:9090 for:
- Application metrics
- Container metrics
- Database metrics
- Redis metrics
- System metrics

### Grafana Dashboards

Access Grafana at http://localhost:3001 (production) with preconfigured dashboards for:
- Application performance
- SIEM monitoring
- Infrastructure metrics
- Business metrics

## 🔐 Security Considerations

### Development Environment
- Uses default passwords (change for production)
- Debug mode enabled
- No SSL/TLS encryption
- All ports exposed

### Production Environment
- Requires secure passwords
- Debug mode disabled
- SSL/TLS recommended (configure nginx)
- Rate limiting enabled
- Security headers configured

### Recommended Production Setup

1. **Use Environment Variables**
   ```bash
   # Never hardcode secrets
   export SECRET_KEY=$(openssl rand -base64 32)
   export DB_PASSWORD=$(openssl rand -base64 24)
   ```

2. **Configure SSL/TLS**
   ```bash
   # Place SSL certificates in nginx/ssl/
   cp your-cert.pem nginx/ssl/
   cp your-key.pem nginx/ssl/
   ```

3. **Network Security**
   ```bash
   # Use custom networks
   # Restrict port exposure
   # Configure firewall rules
   ```

## 🚨 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :3000
   
   # Kill processes using ports
   sudo kill -9 $(lsof -t -i:3000)
   ```

2. **Memory Issues**
   ```bash
   # Check Docker memory usage
   docker stats
   
   # Increase Docker memory limit
   # Docker Desktop: Settings > Resources > Memory
   ```

3. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   
   # Fix script permissions
   chmod +x scripts/docker-setup.sh
   ```

4. **Database Connection Issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U postgres
   
   # Reset database
   ./scripts/docker-setup.sh reset
   ```

5. **Frontend Build Issues**
   ```bash
   # Clear node_modules and rebuild
   docker-compose exec frontend rm -rf node_modules .next
   docker-compose exec frontend npm install
   docker-compose exec frontend npm run build
   ```

### Log Analysis

```bash
# View all logs
./scripts/docker-setup.sh logs

# View specific service logs
./scripts/docker-setup.sh logs frontend
./scripts/docker-setup.sh logs app

# Follow logs in real-time
docker-compose logs -f --tail=100

# Search logs for errors
docker-compose logs app 2>&1 | grep -i error
```

### Performance Optimization

1. **Resource Allocation**
   ```yaml
   # In docker-compose.prod.yml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 1G
   ```

2. **Volume Optimization**
   ```bash
   # Use named volumes for better performance
   # Avoid binding large directories
   # Use .dockerignore files
   ```

3. **Network Optimization**
   ```bash
   # Use custom networks
   # Enable HTTP/2 in nginx
   # Configure caching headers
   ```

## 📖 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [FastAPI Docker Documentation](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL Docker Documentation](https://hub.docker.com/_/postgres)

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Docker and service logs
3. Check GitHub issues
4. Create a new issue with logs and configuration details

---

*This Docker setup provides a complete containerized environment for the Wazuh AI Companion with both development and production configurations.*