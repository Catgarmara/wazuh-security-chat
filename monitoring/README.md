# Wazuh AI Companion - Monitoring & Observability

This directory contains the complete monitoring and observability stack for the Wazuh AI Companion application, including Prometheus metrics collection, Grafana dashboards, Alertmanager notifications, and comprehensive alerting rules.

## 📊 Overview

The monitoring stack provides:

- **Metrics Collection**: Prometheus with custom application metrics
- **Visualization**: Grafana dashboards for system and business metrics
- **Alerting**: Comprehensive alerting rules with multi-channel notifications
- **Infrastructure Monitoring**: Node, PostgreSQL, Redis, and container metrics
- **Business Intelligence**: User engagement and AI performance metrics

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│   Prometheus    │───▶│     Grafana     │
│   (Port 8000)   │    │   (Port 9090)   │    │   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Alertmanager   │───▶│  Notifications  │
                       │   (Port 9093)   │    │ (Email/Slack)   │
                       └─────────────────┘    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Node Exporter   │    │Postgres Exporter│    │ Redis Exporter  │
│   (Port 9100)   │    │   (Port 9187)   │    │   (Port 9121)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────┐
│    cAdvisor     │
│   (Port 8080)   │
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Wazuh AI Companion application running
- Network connectivity between services

### Setup (Linux/macOS)

```bash
# Make setup script executable
chmod +x monitoring/setup-monitoring.sh

# Set up development environment
./monitoring/setup-monitoring.sh setup dev

# Set up production environment
./monitoring/setup-monitoring.sh setup prod
```

### Setup (Windows PowerShell)

```powershell
# Set up development environment
.\monitoring\setup-monitoring.ps1 setup dev

# Set up production environment
.\monitoring\setup-monitoring.ps1 setup prod
```

### Manual Setup

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Check status
docker-compose --profile monitoring ps

# View logs
docker-compose --profile monitoring logs -f
```

## 📈 Dashboards

### Available Dashboards

1. **System Overview** (`wazuh-app-dashboard.json`)
   - Application health and status
   - HTTP request metrics
   - WebSocket connections
   - Real-time performance indicators

2. **AI Performance** (`wazuh-ai-performance.json`)
   - AI query processing times
   - Vector search performance
   - LLM response metrics
   - Model accuracy tracking

3. **Business Metrics** (`wazuh-business-metrics.json`)
   - User engagement analytics
   - Session duration and patterns
   - Query volume trends
   - Feature usage statistics

4. **Infrastructure Metrics** (`wazuh-infrastructure.json`)
   - System resource utilization
   - Container performance
   - Database and Redis metrics
   - Network and disk I/O

5. **Alerts & Monitoring** (`wazuh-alerts.json`)
   - Active alerts overview
   - SLA compliance tracking
   - Alert history and trends
   - System health scoring

### Dashboard Access

- **URL**: http://localhost:3000
- **Default Login**: admin/admin
- **Change Password**: Recommended on first login

## 🚨 Alerting

### Alert Categories

#### Critical Alerts
- Application down
- High error rates (>5%)
- Database connection failures
- System resource exhaustion
- SLA violations

#### Warning Alerts
- High response times
- Elevated resource usage
- Authentication failures
- Performance degradation

#### Info Alerts
- Unusual usage patterns
- Capacity planning notifications
- Business metric anomalies

### Alert Rules

#### Application Alerts (`wazuh-app-alerts.yml`)
- HTTP error rate monitoring
- Response time thresholds
- AI service performance
- WebSocket connection health
- Authentication failure tracking

#### Infrastructure Alerts (`wazuh-infrastructure-alerts.yml`)
- System resource monitoring
- Container health checks
- Database performance
- Redis operations
- Network and disk metrics

### Notification Channels

#### Email Notifications
- **Critical**: Immediate notification to ops team
- **Warning**: Notification to dev team
- **Info**: Daily digest format

#### Slack Integration
- **#alerts-critical**: Critical alerts requiring immediate action
- **#alerts-warning**: Warning alerts for monitoring
- **#alerts-info**: Informational alerts
- **#alerts-resolved**: Resolution notifications

#### Webhook Integration
- Custom webhook endpoints for integration with:
  - PagerDuty
  - ServiceNow
  - Custom incident management systems

## 📊 Metrics

### Application Metrics

#### HTTP Metrics
- `wazuh_http_requests_total`: Total HTTP requests by method, endpoint, status
- `wazuh_http_request_duration_seconds`: Request duration histogram

#### WebSocket Metrics
- `wazuh_websocket_connections_total`: WebSocket connection events
- `wazuh_websocket_connections_active`: Active WebSocket connections
- `wazuh_websocket_messages_total`: WebSocket message counts

#### AI Service Metrics
- `wazuh_ai_queries_total`: AI query counts by status
- `wazuh_ai_query_duration_seconds`: AI processing time
- `wazuh_ai_vector_search_duration_seconds`: Vector search performance
- `wazuh_ai_llm_request_duration_seconds`: LLM request timing

#### Database Metrics
- `wazuh_database_connections_active`: Active database connections
- `wazuh_database_queries_total`: Database query counts
- `wazuh_database_query_duration_seconds`: Query execution time

#### Authentication Metrics
- `wazuh_auth_attempts_total`: Authentication attempts by status
- `wazuh_auth_tokens_issued_total`: Token issuance count
- `wazuh_auth_tokens_validated_total`: Token validation attempts

#### Business Metrics
- `wazuh_chat_sessions_total`: Chat session counts
- `wazuh_chat_messages_total`: Message counts by role
- `wazuh_user_queries_per_session`: Queries per session histogram
- `wazuh_session_duration_seconds`: Session duration tracking

### Infrastructure Metrics

#### System Metrics (Node Exporter)
- CPU usage and load average
- Memory utilization
- Disk space and I/O
- Network traffic
- System uptime

#### Container Metrics (cAdvisor)
- Container CPU and memory usage
- Container network and disk I/O
- Container restart counts
- Resource limit utilization

#### Database Metrics (PostgreSQL Exporter)
- Connection counts and states
- Query performance statistics
- Database size and growth
- Lock and deadlock information

#### Cache Metrics (Redis Exporter)
- Memory usage and eviction
- Command execution statistics
- Connection counts
- Keyspace information

## 🔧 Configuration

### Environment Variables

```bash
# Prometheus Configuration
PROMETHEUS_RETENTION=15d
PROMETHEUS_STORAGE_PATH=/prometheus

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure_password
GRAFANA_SECRET_KEY=your_secret_key

# Alertmanager Configuration
ALERTMANAGER_RETENTION=120h
SMTP_HOST=smtp.company.com
SMTP_FROM=alerts@company.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Customization

#### Adding Custom Metrics

1. **Application Code**:
```python
from core.metrics import metrics

# Record custom metric
metrics.record_custom_metric("my_metric", value, labels)
```

2. **Prometheus Configuration**:
```yaml
# Add scrape target
- job_name: 'custom-service'
  static_configs:
    - targets: ['custom-service:8080']
```

#### Creating Custom Dashboards

1. Create dashboard in Grafana UI
2. Export JSON configuration
3. Save to `monitoring/grafana/dashboards/`
4. Restart Grafana container

#### Adding Alert Rules

1. Create new rule file in `monitoring/rules/`
2. Follow Prometheus alerting syntax
3. Restart Prometheus container
4. Verify rules in Prometheus UI

### Security Considerations

#### Authentication
- Change default Grafana credentials
- Use strong passwords and secret keys
- Enable HTTPS in production

#### Network Security
- Restrict access to monitoring ports
- Use VPN or private networks
- Implement firewall rules

#### Data Protection
- Encrypt sensitive configuration
- Use secrets management
- Regular security updates

## 🔍 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check container logs
docker-compose --profile monitoring logs [service_name]

# Check port conflicts
netstat -tulpn | grep [port_number]

# Verify configuration files
./monitoring/setup-monitoring.sh test
```

#### Missing Metrics
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify application metrics endpoint
curl http://localhost:8000/metrics

# Check service discovery
docker-compose --profile monitoring ps
```

#### Alert Not Firing
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Verify Alertmanager configuration
curl http://localhost:9093/api/v1/status

# Test notification channels
curl -X POST http://localhost:9093/api/v1/alerts
```

### Performance Optimization

#### Prometheus
- Adjust retention period based on storage
- Optimize scrape intervals
- Use recording rules for complex queries

#### Grafana
- Limit dashboard refresh rates
- Use template variables efficiently
- Optimize query performance

#### Alertmanager
- Configure appropriate grouping
- Set reasonable repeat intervals
- Use inhibition rules to reduce noise

## 📚 Additional Resources

### Documentation
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)

### Best Practices
- [Monitoring Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Alert Rule Best Practices](https://prometheus.io/docs/practices/alerting/)

### Community
- [Prometheus Community](https://prometheus.io/community/)
- [Grafana Community](https://community.grafana.com/)
- [Docker Monitoring Examples](https://github.com/vegasbrianc/prometheus)

## 🤝 Contributing

When adding new monitoring components:

1. Update relevant configuration files
2. Add appropriate alert rules
3. Create or update dashboards
4. Update documentation
5. Test thoroughly in development environment

## 📄 License

This monitoring configuration is part of the Wazuh AI Companion project and follows the same licensing terms.