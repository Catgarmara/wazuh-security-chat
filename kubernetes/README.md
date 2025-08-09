# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Wazuh AI Companion application in a production Kubernetes environment.

## Architecture Overview

The deployment consists of the following components:

- **Application Pods**: FastAPI application with auto-scaling
- **PostgreSQL**: Database with persistent storage
- **Redis**: Cache and session store
- **Embedded AI**: Self-contained LLM service with local models
- **Nginx**: Reverse proxy and load balancer
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

## Prerequisites

### Required Tools

- `kubectl` configured to access your Kubernetes cluster
- `docker` for building images
- Kubernetes cluster with:
  - Ingress controller (nginx-ingress recommended)
  - Storage class for persistent volumes
  - Metrics server for HPA

### Cluster Requirements

- **Kubernetes Version**: 1.20+
- **Nodes**: Minimum 3 nodes
- **Resources**: 
  - CPU: 8+ cores total
  - Memory: 16GB+ total
  - Storage: 50GB+ available

## Quick Deployment

### 1. Automated Deployment

```bash
# Make the script executable
chmod +x deploy.sh

# Deploy with image build
./deploy.sh --build

# Deploy with monitoring
./deploy.sh --with-monitoring

# Deploy with both
./deploy.sh --build --with-monitoring
```

### 2. Manual Deployment

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Deploy secrets (update with real values first!)
kubectl apply -f secrets.yaml

# 3. Deploy configuration
kubectl apply -f configmap.yaml

# 4. Deploy storage
kubectl apply -f persistent-volumes.yaml

# 5. Deploy database
kubectl apply -f postgres-deployment.yaml

# 6. Deploy Redis
kubectl apply -f redis-deployment.yaml

# 7. Deploy persistent volumes for embedded AI
kubectl apply -f persistent-volumes.yaml

# 8. Deploy application
kubectl apply -f app-deployment.yaml

# 9. Deploy Nginx
kubectl apply -f nginx-deployment.yaml

# 10. Deploy auto-scaling
kubectl apply -f hpa.yaml

# 11. Deploy monitoring (optional)
kubectl apply -f monitoring-deployment.yaml
```

## Configuration

### Secrets Management

**⚠️ IMPORTANT**: Update `secrets.yaml` with real values before deployment:

```bash
# Generate base64 encoded values
echo -n "your_secret_key_32_chars_minimum" | base64
echo -n "your_db_password" | base64
```

Required secrets:
- `SECRET_KEY`: JWT signing key (32+ characters)
- `DB_PASSWORD`: PostgreSQL password
- `REDIS_PASSWORD`: Redis password (optional)
- `GF_SECURITY_ADMIN_PASSWORD`: Grafana admin password

### Environment Configuration

Modify `configmap.yaml` to adjust:
- Application settings
- Database configuration
- AI model settings
- Log processing parameters

### Storage Configuration

Update `persistent-volumes.yaml` storage class:
```yaml
storageClassName: your-storage-class  # e.g., gp2, fast-ssd
```

## Scaling Configuration

### Horizontal Pod Autoscaler

The deployment includes HPA for automatic scaling:

- **Application**: 3-10 replicas based on CPU/Memory
- **Nginx**: 2-5 replicas based on CPU/Memory

### Manual Scaling

```bash
# Scale application
kubectl scale deployment wazuh-app -n wazuh --replicas=5

# Scale nginx
kubectl scale deployment nginx -n wazuh --replicas=3
```

### Resource Limits

Each component has defined resource limits:

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| App       | 500m        | 1000m     | 512Mi          | 1Gi          |
| PostgreSQL| 500m        | 1000m     | 512Mi          | 1Gi          |
| Redis     | 250m        | 500m      | 256Mi          | 512Mi        |
| App (w/ AI)| 1500m      | 3000m     | 3Gi            | 6Gi          |
| Nginx     | 250m        | 500m      | 128Mi          | 256Mi        |

## Networking

### Services

- `wazuh-app-service`: ClusterIP for application pods
- `postgres-service`: ClusterIP for database
- `redis-service`: ClusterIP for Redis
- `app-service`: ClusterIP for application with embedded AI
- `nginx-service`: LoadBalancer for external access

### Ingress

The deployment includes an Ingress resource with:
- SSL termination
- Rate limiting
- WebSocket support
- Security headers

Update the host in `nginx-deployment.yaml`:
```yaml
rules:
- host: your-domain.com  # Change this
```

## Monitoring

### Prometheus Metrics

The application exposes metrics at `/metrics`:
- HTTP request metrics
- WebSocket connections
- Database connections
- AI processing times

### Grafana Dashboards

Access Grafana at `http://your-domain.com:3000`:
- Username: `admin`
- Password: Set in secrets

Pre-configured dashboards show:
- Application performance
- Resource utilization
- Error rates
- Business metrics

### Health Checks

All components include health checks:
- Liveness probes for restart decisions
- Readiness probes for traffic routing
- Startup probes for slow-starting containers

## Security

### Pod Security

- Non-root user execution
- Read-only root filesystem where possible
- Dropped capabilities
- Security contexts applied

### Network Security

- Network policies (implement as needed)
- TLS termination at ingress
- Internal service communication

### RBAC

Create service accounts and RBAC as needed:
```bash
kubectl create serviceaccount wazuh-app -n wazuh
# Add appropriate role bindings
```

## Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   kubectl describe pod <pod-name> -n wazuh
   kubectl logs <pod-name> -n wazuh
   ```

2. **Database connection issues**:
   ```bash
   kubectl exec -it <postgres-pod> -n wazuh -- psql -U postgres -d wazuh_chat
   ```

3. **Storage issues**:
   ```bash
   kubectl get pvc -n wazuh
   kubectl describe pvc <pvc-name> -n wazuh
   ```

### Debugging Commands

```bash
# Check all resources
kubectl get all -n wazuh

# Check events
kubectl get events -n wazuh --sort-by='.lastTimestamp'

# Check logs
kubectl logs -f deployment/wazuh-app -n wazuh

# Port forward for testing
kubectl port-forward service/wazuh-app-service 8000:8000 -n wazuh
```

### Performance Issues

1. **Check resource usage**:
   ```bash
   kubectl top pods -n wazuh
   kubectl top nodes
   ```

2. **Check HPA status**:
   ```bash
   kubectl get hpa -n wazuh
   kubectl describe hpa wazuh-app-hpa -n wazuh
   ```

## Maintenance

### Updates

1. **Update application**:
   ```bash
   # Build new image
   docker build -t wazuh-ai-companion:2.1.0 .
   
   # Update deployment
   kubectl set image deployment/wazuh-app wazuh-app=wazuh-ai-companion:2.1.0 -n wazuh
   ```

2. **Database migrations**:
   ```bash
   kubectl exec -it deployment/wazuh-app -n wazuh -- alembic upgrade head
   ```

### Backups

1. **Database backup**:
   ```bash
   kubectl exec -it deployment/postgres -n wazuh -- pg_dump -U postgres wazuh_chat > backup.sql
   ```

2. **Persistent volume backup**:
   ```bash
   # Use your cloud provider's volume snapshot feature
   # Or use tools like Velero for cluster backups
   ```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace wazuh

# Or delete specific components
kubectl delete -f .
```

## Production Checklist

- [ ] Update all secrets with production values
- [ ] Configure proper storage class
- [ ] Set up ingress with real domain and SSL certificates
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Test disaster recovery procedures
- [ ] Set up CI/CD pipeline
- [ ] Configure network policies
- [ ] Set up RBAC
- [ ] Performance test the deployment
- [ ] Security scan all images
- [ ] Document operational procedures

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Kubernetes events and logs
3. Check application health endpoints
4. Monitor resource usage and scaling