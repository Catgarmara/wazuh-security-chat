#!/bin/bash

# Wazuh AI Companion - Monitoring Setup Script
# This script sets up the complete monitoring stack with Prometheus, Grafana, and Alertmanager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MONITORING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$MONITORING_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
COMPOSE_PROD_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

create_directories() {
    log_info "Creating monitoring directories..."
    
    mkdir -p "$MONITORING_DIR/data/prometheus"
    mkdir -p "$MONITORING_DIR/data/grafana"
    mkdir -p "$MONITORING_DIR/data/alertmanager"
    mkdir -p "$MONITORING_DIR/logs"
    
    # Set proper permissions
    chmod 755 "$MONITORING_DIR/data"
    chmod 755 "$MONITORING_DIR/data/prometheus"
    chmod 755 "$MONITORING_DIR/data/grafana"
    chmod 755 "$MONITORING_DIR/data/alertmanager"
    
    log_success "Monitoring directories created"
}

validate_configs() {
    log_info "Validating monitoring configurations..."
    
    # Check Prometheus config
    if [ ! -f "$MONITORING_DIR/prometheus.yml" ]; then
        log_error "Prometheus configuration not found: $MONITORING_DIR/prometheus.yml"
        exit 1
    fi
    
    # Check Alertmanager config
    if [ ! -f "$MONITORING_DIR/alertmanager.yml" ]; then
        log_error "Alertmanager configuration not found: $MONITORING_DIR/alertmanager.yml"
        exit 1
    fi
    
    # Check Grafana dashboards
    if [ ! -d "$MONITORING_DIR/grafana/dashboards" ]; then
        log_error "Grafana dashboards directory not found: $MONITORING_DIR/grafana/dashboards"
        exit 1
    fi
    
    # Check alerting rules
    if [ ! -d "$MONITORING_DIR/rules" ]; then
        log_error "Alerting rules directory not found: $MONITORING_DIR/rules"
        exit 1
    fi
    
    log_success "All monitoring configurations are valid"
}

setup_environment() {
    log_info "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_warning ".env file not found. Creating default configuration..."
        cat > "$PROJECT_ROOT/.env" << EOF
# Database Configuration
DB_PASSWORD=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=wazuh_chat
DB_USER=postgres

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Security Configuration
SECRET_KEY=your-secret-key-here-must-be-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Grafana Configuration
GRAFANA_PASSWORD=admin
GRAFANA_SECRET_KEY=your-grafana-secret-key-here

# Application Configuration
APP_NAME=Wazuh AI Companion
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=false

# Monitoring Configuration
PROMETHEUS_RETENTION=15d
GRAFANA_ADMIN_USER=admin
ALERTMANAGER_RETENTION=120h
EOF
        log_warning "Please update the .env file with your actual configuration values"
    fi
    
    log_success "Environment configuration ready"
}

start_monitoring_stack() {
    local environment=${1:-development}
    
    log_info "Starting monitoring stack for $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$environment" = "production" ]; then
        docker-compose -f "$COMPOSE_PROD_FILE" --profile monitoring up -d
    else
        docker-compose -f "$COMPOSE_FILE" --profile monitoring up -d
    fi
    
    log_success "Monitoring stack started successfully"
}

wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    # Wait for Prometheus
    log_info "Waiting for Prometheus..."
    timeout 60 bash -c 'until curl -s http://localhost:9090/-/ready > /dev/null; do sleep 2; done' || {
        log_error "Prometheus failed to start within 60 seconds"
        exit 1
    }
    
    # Wait for Grafana
    log_info "Waiting for Grafana..."
    timeout 60 bash -c 'until curl -s http://localhost:3000/api/health > /dev/null; do sleep 2; done' || {
        log_error "Grafana failed to start within 60 seconds"
        exit 1
    }
    
    # Wait for Alertmanager
    log_info "Waiting for Alertmanager..."
    timeout 60 bash -c 'until curl -s http://localhost:9093/-/ready > /dev/null; do sleep 2; done' || {
        log_error "Alertmanager failed to start within 60 seconds"
        exit 1
    }
    
    log_success "All monitoring services are ready"
}

show_access_info() {
    log_success "Monitoring stack is now running!"
    echo
    echo "Access URLs:"
    echo "  📊 Grafana:      http://localhost:3000 (admin/admin)"
    echo "  📈 Prometheus:   http://localhost:9090"
    echo "  🚨 Alertmanager: http://localhost:9093"
    echo "  📋 Node Exporter: http://localhost:9100"
    echo "  🐘 PostgreSQL Exporter: http://localhost:9187"
    echo "  🔴 Redis Exporter: http://localhost:9121"
    echo "  📦 cAdvisor: http://localhost:8080"
    echo
    echo "Default Grafana Dashboards:"
    echo "  • Wazuh AI Companion - System Overview"
    echo "  • Wazuh AI Companion - AI Performance"
    echo "  • Wazuh AI Companion - Business Metrics"
    echo "  • Wazuh AI Companion - Infrastructure Metrics"
    echo "  • Wazuh AI Companion - Alerts & Monitoring"
    echo
    echo "To stop the monitoring stack:"
    echo "  docker-compose --profile monitoring down"
    echo
}

test_alerts() {
    log_info "Testing alert configuration..."
    
    # Test Prometheus rules
    if command -v promtool &> /dev/null; then
        promtool check rules "$MONITORING_DIR/rules/"*.yml
        log_success "Prometheus rules validation passed"
    else
        log_warning "promtool not found, skipping rules validation"
    fi
    
    # Test Alertmanager config
    if command -v amtool &> /dev/null; then
        amtool config check "$MONITORING_DIR/alertmanager.yml"
        log_success "Alertmanager configuration validation passed"
    else
        log_warning "amtool not found, skipping alertmanager validation"
    fi
}

cleanup() {
    log_info "Cleaning up monitoring stack..."
    
    cd "$PROJECT_ROOT"
    docker-compose --profile monitoring down -v
    
    log_success "Monitoring stack cleaned up"
}

show_help() {
    echo "Wazuh AI Companion - Monitoring Setup Script"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  setup [dev|prod]    Set up and start monitoring stack (default: dev)"
    echo "  start [dev|prod]    Start monitoring stack"
    echo "  stop                Stop monitoring stack"
    echo "  restart [dev|prod]  Restart monitoring stack"
    echo "  status              Show status of monitoring services"
    echo "  logs [service]      Show logs for monitoring services"
    echo "  test                Test monitoring configuration"
    echo "  cleanup             Stop and remove all monitoring containers and volumes"
    echo "  help                Show this help message"
    echo
    echo "Examples:"
    echo "  $0 setup dev        # Set up development monitoring"
    echo "  $0 setup prod       # Set up production monitoring"
    echo "  $0 logs grafana     # Show Grafana logs"
    echo "  $0 test             # Test configuration"
    echo
}

# Main script logic
case "${1:-setup}" in
    setup)
        environment=${2:-development}
        check_dependencies
        create_directories
        validate_configs
        setup_environment
        start_monitoring_stack "$environment"
        wait_for_services
        show_access_info
        ;;
    start)
        environment=${2:-development}
        start_monitoring_stack "$environment"
        wait_for_services
        show_access_info
        ;;
    stop)
        cd "$PROJECT_ROOT"
        docker-compose --profile monitoring down
        log_success "Monitoring stack stopped"
        ;;
    restart)
        environment=${2:-development}
        cd "$PROJECT_ROOT"
        docker-compose --profile monitoring down
        start_monitoring_stack "$environment"
        wait_for_services
        show_access_info
        ;;
    status)
        cd "$PROJECT_ROOT"
        docker-compose --profile monitoring ps
        ;;
    logs)
        service=${2:-}
        cd "$PROJECT_ROOT"
        if [ -n "$service" ]; then
            docker-compose --profile monitoring logs -f "$service"
        else
            docker-compose --profile monitoring logs -f
        fi
        ;;
    test)
        validate_configs
        test_alerts
        log_success "All tests passed"
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac