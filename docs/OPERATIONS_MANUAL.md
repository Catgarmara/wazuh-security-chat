# Wazuh AI Companion - Operations Manual

## Overview

This manual provides comprehensive operational procedures for managing the Wazuh AI Companion system in production. It covers day-to-day operations, maintenance tasks, troubleshooting, and incident response.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Daily Operations](#daily-operations)
3. [Monitoring and Alerting](#monitoring-and-alerting)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Incident Response](#incident-response)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Backup and Recovery](#backup-and-recovery)
8. [Performance Tuning](#performance-tuning)
9. [Security Operations](#security-operations)
10. [Change Management](#change-management)

## System Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Nginx       │    │   Application   │
│    (External)   │────│   (Ingress)     │────│     Pods        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   PostgreSQL    │─────────────┤
                       │   (Database)    │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │     Redis       │─────────────┤
                       │   (Sessions)    │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │     Ollama      │─────────────┘
                       │   (AI Models)   │
                       └─────────────────┘
```

### Service Dependencies

- **Application** depends on: PostgreSQL, Redis, Ollama
- **Nginx** depends on: Application pods
- **Load Balancer** depends on: Nginx
- **Monitoring** observes: All components

## Daily Operations

### Morning Health Check

```bash
#!/bin/bash
# Daily health check script

echo "=== Daily Health Check - $(date) ==="

# 1. Check overall system health
echo "1. System Health Check:"
curl -f https://yourdomain.com/health || echo "❌ Health check failed"

# 2. Check all pods status
echo "2. Pod Status:"
kubectl get pods -n wazuh-ai-companion

# 3. Check resource usage
echo "3. Resource Usage:"
kubectl top pods -n wazuh-ai-companion

# 4. Check recent errors
echo "4. Recent Errors (last 1 hour):"
kubectl logs --since=1h -l app=wazuh-ai-companion | grep -i error | tail -10

# 5. Check database connections
echo "5. Database Status:"
kubectl exec -it deployment/postgres -- pg_isready

# 6. Check Redis status
echo "6. Redis Status:"
kubectl exec -it deployment/redis -- redis-cli ping

# 7. Check disk usage
echo "7. Disk Usage:"
kubectl exec -it deployment/wazuh-ai-companion -- df -h

# 8. Check certificate expiry
echo "8. SSL Certificate:"
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

echo "=== Health Check Complete ==="
```

### Key Metrics to Monitor

1. **Application Metrics**:
   - Response time (< 2 seconds for 95% of requests)
   - Error rate (< 1%)
   - Request throughput
   - Active WebSocket connections

2. **Infrastructure Metrics**:
   - CPU usage (< 80%)
   - Memory usage (< 85%)
   - Disk usage (< 80%)
   - Network I/O

3. **Database Metrics**:
   - Connection count
   - Query performance
   - Lock waits
   - Replication lag (if applicable)

4. **AI Service Metrics**:
   - Model response time
   - Vector store size
   - Embedding generation time
   - LLM availability

## Monitoring and Alerting

### Critical Alerts

#### Application Down
```yaml
alert: ApplicationDown
expr: up{job="wazuh-ai-companion"} == 0
for: 1m
severity: critical
description: "Application is down for more than 1 minute"
```

#### High Error Rate
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
for: 2m
severity: warning
description: "Error rate is above 10% for 2 minutes"
```

#### High Response Time
```yaml
alert: HighResponseTime
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
for: 5m
severity: warning
description: "95th percentile response time is above 2 seconds"
```

### Alert Response Procedures

#### 1. Application Down Alert
```bash
# Immediate actions:
1. Check pod status: kubectl get pods -n wazuh-ai-companion
2. Check recent logs: kubectl logs -l app=wazuh-ai-companion --tail=50
3. Check resource usage: kubectl top pods -n wazuh-ai-companion
4. Restart if necessary: kubectl rollout restart deployment/wazuh-ai-companion
5. Escalate if restart doesn't resolve within 5 minutes
```

#### 2. Database Connection Issues
```bash
# Troubleshooting steps:
1. Check database pod: kubectl get pods -l app=postgres
2. Test connectivity: kubectl exec -it deployment/wazuh-ai-companion -- python -c "from core.database import get_db; next(get_db())"
3. Check database logs: kubectl logs -l app=postgres --tail=100
4. Check connection pool: kubectl exec -it deployment/postgres -- psql -U wazuh_user -c "SELECT * FROM pg_stat_activity;"
```

#### 3. High Memory Usage
```bash
# Memory investigation:
1. Check memory usage: kubectl top pods -n wazuh-ai-companion
2. Check for memory leaks: kubectl exec -it deployment/wazuh-ai-companion -- python -c "import psutil; print(psutil.virtual_memory())"
3. Scale up if needed: kubectl scale deployment wazuh-ai-companion --replicas=5
4. Investigate root cause in application logs
```

## Maintenance Procedures

### Weekly Maintenance

#### Database Maintenance
```bash
#!/bin/bash
# Weekly database maintenance

echo "Starting weekly database maintenance..."

# 1. Database statistics update
kubectl exec -it deployment/postgres -- psql -U wazuh_user -d wazuh_chat -c "ANALYZE;"

# 2. Vacuum database
kubectl exec -it deployment/postgres -- psql -U wazuh_user -d wazuh_chat -c "VACUUM;"

# 3. Check database size
kubectl exec -it deployment/postgres -- psql -U wazuh_user -d wazuh_chat -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# 4. Check for long-running queries
kubectl exec -it deployment/postgres -- psql -U wazuh_user -d wazuh_chat -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

echo "Database maintenance complete."
```

#### Log Cleanup
```bash
#!/bin/bash
# Clean up old logs and metrics

echo "Starting log cleanup..."

# 1. Clean up old analytics data (keep 90 days)
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.analytics_service import AnalyticsService
analytics = AnalyticsService()
deleted = analytics.cleanup_old_metrics(days_to_keep=90)
print(f'Cleaned up {deleted} old metrics records')
"

# 2. Clean up old chat sessions (keep 180 days)
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.chat_service import ChatService
chat = ChatService()
deleted = chat.cleanup_old_sessions(days_old=180)
print(f'Cleaned up {deleted} old chat sessions')
"

# 3. Clean up old audit logs (keep 365 days)
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.audit_service import AuditService
audit = AuditService()
deleted = audit.cleanup_old_logs(days_to_keep=365)
print(f'Cleaned up {deleted} old audit logs')
"

echo "Log cleanup complete."
```

### Monthly Maintenance

#### Security Updates
```bash
#!/bin/bash
# Monthly security updates

echo "Starting monthly security updates..."

# 1. Update base images
docker pull python:3.11-slim
docker pull postgres:15
docker pull redis:7
docker pull nginx:alpine

# 2. Scan for vulnerabilities
trivy image wazuh-ai-companion:latest

# 3. Update Python dependencies
pip-audit --desc --format=json --output=security-audit.json

# 4. Check SSL certificate expiry
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

echo "Security updates complete."
```

#### Performance Review
```bash
#!/bin/bash
# Monthly performance review

echo "Starting monthly performance review..."

# 1. Generate performance report
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.analytics_service import AnalyticsService
from datetime import datetime, timedelta

analytics = AnalyticsService()
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)

metrics = analytics.get_usage_metrics(start_date=start_date, end_date=end_date)
print(f'Monthly Performance Report:')
print(f'Total Queries: {metrics.total_queries}')
print(f'Average Response Time: {metrics.avg_response_time:.3f}s')
print(f'Error Rate: {metrics.error_rate:.2%}')
print(f'Unique Users: {metrics.unique_users}')
"

# 2. Check resource trends
kubectl top pods -n wazuh-ai-companion --sort-by=memory
kubectl top pods -n wazuh-ai-companion --sort-by=cpu

echo "Performance review complete."
```

## Incident Response

### Incident Classification

#### Severity 1 (Critical)
- Complete system outage
- Data loss or corruption
- Security breach
- Response time: Immediate (< 15 minutes)

#### Severity 2 (High)
- Partial system outage
- Significant performance degradation
- Authentication issues
- Response time: < 1 hour

#### Severity 3 (Medium)
- Minor functionality issues
- Non-critical performance issues
- Response time: < 4 hours

#### Severity 4 (Low)
- Cosmetic issues
- Enhancement requests
- Response time: < 24 hours

### Incident Response Procedures

#### 1. Incident Detection
```bash
# Automated detection via monitoring alerts
# Manual detection via user reports or health checks

# Initial assessment:
1. Determine severity level
2. Notify incident response team
3. Create incident ticket
4. Begin investigation
```

#### 2. Investigation and Diagnosis
```bash
# Investigation checklist:
□ Check system health endpoints
□ Review recent deployments
□ Check resource usage
□ Review error logs
□ Check external dependencies
□ Verify network connectivity
□ Check database status
```

#### 3. Resolution and Recovery
```bash
# Common resolution steps:
1. Identify root cause
2. Implement immediate fix
3. Verify system recovery
4. Monitor for stability
5. Document resolution
6. Conduct post-incident review
```

### Common Incident Scenarios

#### Database Connection Pool Exhaustion
```bash
# Symptoms: Connection timeout errors, slow response times
# Investigation:
kubectl exec -it deployment/postgres -- psql -U wazuh_user -c "SELECT count(*) FROM pg_stat_activity;"

# Resolution:
1. Increase connection pool size in application config
2. Restart application pods
3. Monitor connection usage
```

#### Memory Leak in Application
```bash
# Symptoms: Increasing memory usage, OOM kills
# Investigation:
kubectl top pods -n wazuh-ai-companion
kubectl describe pod <pod-name>

# Resolution:
1. Restart affected pods immediately
2. Investigate memory usage patterns
3. Deploy fix in next release
```

#### AI Service Unavailable
```bash
# Symptoms: AI queries failing, timeout errors
# Investigation:
kubectl exec -it deployment/ollama -- curl localhost:11434/api/tags

# Resolution:
1. Restart Ollama service
2. Verify model availability
3. Check resource allocation
```

## Troubleshooting Guide

### Application Issues

#### High CPU Usage
```bash
# Investigation:
1. kubectl top pods -n wazuh-ai-companion
2. kubectl exec -it <pod> -- top
3. Check for inefficient queries or loops

# Resolution:
1. Scale horizontally if needed
2. Optimize code if identified
3. Increase CPU limits if necessary
```

#### Memory Leaks
```bash
# Investigation:
1. Monitor memory usage over time
2. Check for unclosed connections
3. Review garbage collection logs

# Resolution:
1. Restart pods as immediate fix
2. Identify and fix memory leaks
3. Implement memory monitoring
```

#### Slow Database Queries
```bash
# Investigation:
kubectl exec -it deployment/postgres -- psql -U wazuh_user -d wazuh_chat -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# Resolution:
1. Add database indexes
2. Optimize query structure
3. Consider query caching
```

### Infrastructure Issues

#### Pod Crashes
```bash
# Investigation:
kubectl describe pod <pod-name>
kubectl logs <pod-name> --previous

# Common causes:
- Resource limits exceeded
- Application errors
- Health check failures
- Node issues
```

#### Network Issues
```bash
# Investigation:
kubectl exec -it <pod> -- nslookup <service-name>
kubectl get endpoints
kubectl describe service <service-name>

# Resolution:
1. Check service definitions
2. Verify network policies
3. Restart networking components if needed
```

## Backup and Recovery

### Automated Backup Procedures

#### Database Backup
```bash
#!/bin/bash
# Automated database backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="wazuh_chat_backup_${DATE}.sql"

# Create backup
kubectl exec -it deployment/postgres -- pg_dump -U wazuh_user wazuh_chat > ${BACKUP_FILE}

# Compress backup
gzip ${BACKUP_FILE}

# Upload to cloud storage
aws s3 cp ${BACKUP_FILE}.gz s3://your-backup-bucket/database/

# Clean up local file
rm ${BACKUP_FILE}.gz

# Verify backup
aws s3 ls s3://your-backup-bucket/database/${BACKUP_FILE}.gz

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

#### Application Data Backup
```bash
#!/bin/bash
# Backup application data (Redis, vector store)

DATE=$(date +%Y%m%d_%H%M%S)

# Backup Redis data
kubectl exec -it deployment/redis -- redis-cli BGSAVE
kubectl cp redis-pod:/data/dump.rdb ./redis_backup_${DATE}.rdb

# Backup vector store
kubectl exec -it deployment/wazuh-ai-companion -- tar -czf /tmp/vectorstore_${DATE}.tar.gz /app/data/vectorstore
kubectl cp wazuh-ai-companion-pod:/tmp/vectorstore_${DATE}.tar.gz ./

# Upload to cloud storage
aws s3 cp redis_backup_${DATE}.rdb s3://your-backup-bucket/redis/
aws s3 cp vectorstore_${DATE}.tar.gz s3://your-backup-bucket/vectorstore/

echo "Application data backup completed"
```

### Recovery Procedures

#### Database Recovery
```bash
#!/bin/bash
# Database recovery procedure

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Download backup from cloud storage
aws s3 cp s3://your-backup-bucket/database/${BACKUP_FILE} ./

# Decompress if needed
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip ${BACKUP_FILE}
    BACKUP_FILE=${BACKUP_FILE%.gz}
fi

# Stop application to prevent new connections
kubectl scale deployment wazuh-ai-companion --replicas=0

# Restore database
kubectl exec -i deployment/postgres -- psql -U wazuh_user -d wazuh_chat < ${BACKUP_FILE}

# Start application
kubectl scale deployment wazuh-ai-companion --replicas=3

# Verify recovery
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from core.database import get_db
db = next(get_db())
print('Database connection successful')
"

echo "Database recovery completed"
```

## Performance Tuning

### Application Performance

#### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_messages_session_timestamp ON messages(session_id, timestamp);
CREATE INDEX CONCURRENTLY idx_query_metrics_user_timestamp ON query_metrics(user_id, timestamp);
CREATE INDEX CONCURRENTLY idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Update table statistics
ANALYZE;

-- Check query performance
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

#### Redis Optimization
```bash
# Redis configuration tuning
kubectl exec -it deployment/redis -- redis-cli CONFIG SET maxmemory-policy allkeys-lru
kubectl exec -it deployment/redis -- redis-cli CONFIG SET maxmemory 2gb
kubectl exec -it deployment/redis -- redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

#### Application Scaling
```bash
# Horizontal scaling
kubectl scale deployment wazuh-ai-companion --replicas=5

# Vertical scaling
kubectl patch deployment wazuh-ai-companion -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"requests":{"memory":"2Gi","cpu":"1000m"},"limits":{"memory":"4Gi","cpu":"2000m"}}}]}}}}'

# Auto-scaling
kubectl apply -f kubernetes/hpa.yaml
```

## Security Operations

### Security Monitoring

#### Log Analysis
```bash
# Check for suspicious activities
kubectl logs -l app=wazuh-ai-companion | grep -E "(failed|error|unauthorized|forbidden)" | tail -20

# Check authentication failures
kubectl exec -it deployment/wazuh-ai-companion -- python -c "
from services.audit_service import AuditService
audit = AuditService()
failed_logins = audit.get_failed_login_attempts(hours=24)
print(f'Failed login attempts in last 24 hours: {len(failed_logins)}')
"
```

#### Security Scans
```bash
# Container vulnerability scan
trivy image wazuh-ai-companion:latest

# Network security scan
nmap -sS -O yourdomain.com

# SSL/TLS configuration check
testssl.sh yourdomain.com
```

### Incident Response

#### Security Incident Procedures
1. **Immediate Response**:
   - Isolate affected systems
   - Preserve evidence
   - Notify security team
   - Document timeline

2. **Investigation**:
   - Analyze logs and metrics
   - Identify attack vectors
   - Assess damage scope
   - Collect forensic data

3. **Containment**:
   - Block malicious IPs
   - Revoke compromised credentials
   - Apply security patches
   - Update security rules

4. **Recovery**:
   - Restore from clean backups
   - Verify system integrity
   - Monitor for reoccurrence
   - Update security measures

## Change Management

### Deployment Process

#### Pre-deployment
```bash
# 1. Code review and approval
# 2. Security scan
# 3. Testing in staging
# 4. Performance validation
# 5. Rollback plan preparation
```

#### Deployment
```bash
# 1. Maintenance window notification
# 2. Database migration (if needed)
# 3. Application deployment
# 4. Health check verification
# 5. Performance monitoring
```

#### Post-deployment
```bash
# 1. Functional testing
# 2. Performance validation
# 3. Error monitoring
# 4. User feedback collection
# 5. Documentation update
```

### Emergency Procedures

#### Emergency Rollback
```bash
#!/bin/bash
# Emergency rollback procedure

echo "Starting emergency rollback..."

# Get current deployment
CURRENT_REVISION=$(kubectl rollout history deployment/wazuh-ai-companion -n wazuh-ai-companion | tail -1 | awk '{print $1}')
echo "Current revision: $CURRENT_REVISION"

# Rollback to previous version
kubectl rollout undo deployment/wazuh-ai-companion -n wazuh-ai-companion

# Wait for rollback to complete
kubectl rollout status deployment/wazuh-ai-companion -n wazuh-ai-companion --timeout=300s

# Verify health
curl -f https://yourdomain.com/health

echo "Emergency rollback completed"
```


