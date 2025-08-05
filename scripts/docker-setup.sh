#!/bin/bash

# Docker Setup Script for Wazuh AI Companion
# This script provides easy management of the Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="wazuh-ai"
DEV_COMPOSE_FILE="docker-compose.yml"
PROD_COMPOSE_FILE="docker-compose.prod.yml"

# Functions
print_help() {
    echo -e "${BLUE}Wazuh AI Companion Docker Management Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  dev                 Start development environment"
    echo "  prod               Start production environment"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  build              Build all images"
    echo "  rebuild            Rebuild all images (no cache)"
    echo "  logs               Show logs for all services"
    echo "  logs [service]     Show logs for specific service"
    echo "  status             Show status of all services"
    echo "  clean              Clean up containers, networks, and volumes"
    echo "  reset              Complete reset (clean + remove volumes)"
    echo "  health             Check health of all services"
    echo "  shell [service]    Open shell in service container"
    echo "  db-init            Initialize database"
    echo "  db-migrate         Run database migrations"
    echo "  test               Run tests in containers"
    echo "  frontend-build     Build frontend for production"
    echo "  help               Show this help message"
    echo ""
    echo "Options:"
    echo "  --no-cache         Don't use cache when building"
    echo "  --pull             Pull latest images before building"
    echo "  --detach           Run in detached mode"
    echo "  --verbose          Show verbose output"
}

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
}

check_env_file() {
    if [ ! -f ".env" ]; then
        warn "No .env file found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log "Created .env file from .env.example"
        else
            warn "No .env.example file found. You may need to create .env manually"
        fi
    fi
}

wait_for_services() {
    local compose_file=$1
    log "Waiting for services to be healthy..."
    
    # Wait for database
    timeout 60 bash -c "until docker-compose -f $compose_file exec -T postgres pg_isready -U postgres; do sleep 2; done" || {
        error "Database failed to start within 60 seconds"
    }
    
    # Wait for Redis
    timeout 30 bash -c "until docker-compose -f $compose_file exec -T redis redis-cli ping; do sleep 2; done" || {
        error "Redis failed to start within 30 seconds"
    }
    
    # Wait for backend app
    timeout 60 bash -c "until curl -f http://localhost:8000/health 2>/dev/null; do sleep 2; done" || {
        error "Backend application failed to start within 60 seconds"
    }
    
    # Wait for frontend (if running)
    if docker-compose -f $compose_file ps frontend | grep -q "Up"; then
        timeout 60 bash -c "until curl -f http://localhost:3000/api/health 2>/dev/null; do sleep 2; done" || {
            error "Frontend application failed to start within 60 seconds"
        }
    fi
    
    log "All services are healthy!"
}

start_dev() {
    log "Starting development environment..."
    check_env_file
    
    local args="up"
    if [[ "$*" == *"--detach"* ]]; then
        args="$args -d"
    fi
    
    docker-compose -f $DEV_COMPOSE_FILE $args
    
    if [[ "$*" == *"--detach"* ]]; then
        wait_for_services $DEV_COMPOSE_FILE
        log "Development environment started successfully!"
        log "Frontend: http://localhost:3000"
        log "Backend API: http://localhost:8000"
        log "Grafana: http://localhost:3000 (admin/admin)"
        log "Prometheus: http://localhost:9090"
    fi
}

start_prod() {
    log "Starting production environment..."
    check_env_file
    
    # Check required environment variables
    if [ -z "$SECRET_KEY" ] || [ -z "$DB_PASSWORD" ]; then
        error "Required environment variables not set. Please check your .env file."
    fi
    
    local args="up"
    if [[ "$*" == *"--detach"* ]]; then
        args="$args -d"
    fi
    
    docker-compose -f $PROD_COMPOSE_FILE $args
    
    if [[ "$*" == *"--detach"* ]]; then
        wait_for_services $PROD_COMPOSE_FILE
        log "Production environment started successfully!"
        log "Application: http://localhost:80"
        log "Grafana: http://localhost:3001"
        log "Prometheus: http://localhost:9090"
    fi
}

stop_services() {
    log "Stopping all services..."
    docker-compose -f $DEV_COMPOSE_FILE down 2>/dev/null || true
    docker-compose -f $PROD_COMPOSE_FILE down 2>/dev/null || true
    log "All services stopped"
}

build_images() {
    log "Building Docker images..."
    local args="build"
    
    if [[ "$*" == *"--no-cache"* ]]; then
        args="$args --no-cache"
    fi
    
    if [[ "$*" == *"--pull"* ]]; then
        args="$args --pull"
    fi
    
    docker-compose -f $DEV_COMPOSE_FILE $args
    log "Images built successfully"
}

rebuild_images() {
    log "Rebuilding Docker images (no cache)..."
    docker-compose -f $DEV_COMPOSE_FILE build --no-cache --pull
    log "Images rebuilt successfully"
}

show_logs() {
    local service=$1
    if [ -n "$service" ]; then
        log "Showing logs for service: $service"
        docker-compose -f $DEV_COMPOSE_FILE logs -f "$service" 2>/dev/null || \
        docker-compose -f $PROD_COMPOSE_FILE logs -f "$service"
    else
        log "Showing logs for all services"
        docker-compose -f $DEV_COMPOSE_FILE logs -f 2>/dev/null || \
        docker-compose -f $PROD_COMPOSE_FILE logs -f
    fi
}

show_status() {
    log "Service status:"
    echo ""
    docker-compose -f $DEV_COMPOSE_FILE ps 2>/dev/null || \
    docker-compose -f $PROD_COMPOSE_FILE ps
}

clean_up() {
    log "Cleaning up containers and networks..."
    docker-compose -f $DEV_COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    docker-compose -f $PROD_COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    docker system prune -f
    log "Cleanup completed"
}

reset_environment() {
    log "Resetting entire environment (including volumes)..."
    docker-compose -f $DEV_COMPOSE_FILE down -v --remove-orphans 2>/dev/null || true
    docker-compose -f $PROD_COMPOSE_FILE down -v --remove-orphans 2>/dev/null || true
    docker system prune -af
    docker volume prune -f
    log "Environment reset completed"
}

check_health() {
    log "Checking service health..."
    echo ""
    
    # Check if any containers are running
    if ! docker ps | grep -q "$PROJECT_NAME"; then
        warn "No containers are currently running"
        return
    fi
    
    # Check backend health
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo -e "${GREEN}✓ Backend API: Healthy${NC}"
    else
        echo -e "${RED}✗ Backend API: Unhealthy${NC}"
    fi
    
    # Check frontend health
    if curl -f http://localhost:3000/api/health 2>/dev/null; then
        echo -e "${GREEN}✓ Frontend: Healthy${NC}"
    else
        echo -e "${RED}✗ Frontend: Unhealthy or not running${NC}"
    fi
    
    # Check database
    if docker-compose -f $DEV_COMPOSE_FILE exec -T postgres pg_isready -U postgres 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL: Ready${NC}"
    else
        echo -e "${RED}✗ PostgreSQL: Not ready${NC}"
    fi
    
    # Check Redis
    if docker-compose -f $DEV_COMPOSE_FILE exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo -e "${GREEN}✓ Redis: Ready${NC}"
    else
        echo -e "${RED}✗ Redis: Not ready${NC}"
    fi
}

open_shell() {
    local service=$1
    if [ -z "$service" ]; then
        error "Please specify a service name"
    fi
    
    log "Opening shell in $service container..."
    docker-compose -f $DEV_COMPOSE_FILE exec "$service" /bin/bash 2>/dev/null || \
    docker-compose -f $DEV_COMPOSE_FILE exec "$service" /bin/sh 2>/dev/null || \
    docker-compose -f $PROD_COMPOSE_FILE exec "$service" /bin/bash 2>/dev/null || \
    docker-compose -f $PROD_COMPOSE_FILE exec "$service" /bin/sh
}

init_database() {
    log "Initializing database..."
    docker-compose -f $DEV_COMPOSE_FILE exec app python scripts/init_db.py
    log "Database initialized"
}

run_migrations() {
    log "Running database migrations..."
    docker-compose -f $DEV_COMPOSE_FILE exec app alembic upgrade head
    log "Migrations completed"
}

run_tests() {
    log "Running tests..."
    docker-compose -f $DEV_COMPOSE_FILE exec app pytest tests/ -v
    log "Tests completed"
}

build_frontend() {
    log "Building frontend for production..."
    docker-compose -f $DEV_COMPOSE_FILE exec frontend npm run build
    log "Frontend build completed"
}

# Main script logic
check_docker

case "$1" in
    "dev")
        start_dev "$@"
        ;;
    "prod")
        start_prod "$@"
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_dev "$@"
        ;;
    "build")
        build_images "$@"
        ;;
    "rebuild")
        rebuild_images
        ;;
    "logs")
        show_logs "$2"
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_up
        ;;
    "reset")
        reset_environment
        ;;
    "health")
        check_health
        ;;
    "shell")
        open_shell "$2"
        ;;
    "db-init")
        init_database
        ;;
    "db-migrate")
        run_migrations
        ;;
    "test")
        run_tests
        ;;
    "frontend-build")
        build_frontend
        ;;
    "help"|"--help"|"-h"|"")
        print_help
        ;;
    *)
        error "Unknown command: $1. Use '$0 help' for available commands."
        ;;
esac