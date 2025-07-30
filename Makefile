# Wazuh AI Companion Docker Operations

.PHONY: help build up down logs clean test prod-build prod-up prod-down

# Default target
help:
	@echo "Available commands:"
	@echo "  build      - Build Docker images"
	@echo "  up         - Start development environment"
	@echo "  down       - Stop development environment"
	@echo "  logs       - Show application logs"
	@echo "  clean      - Clean up Docker resources"
	@echo "  test       - Run tests in Docker"
	@echo "  prod-build - Build production images"
	@echo "  prod-up    - Start production environment"
	@echo "  prod-down  - Stop production environment"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Application starting at http://localhost:8000"
	@echo "Grafana dashboard at http://localhost:3000 (admin/admin)"

down:
	docker-compose down

logs:
	docker-compose logs -f app

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

test:
	docker-compose exec app python -m pytest tests/ -v

# Production commands
prod-build:
	docker-compose -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Production application starting at https://localhost"
	@echo "Grafana dashboard at http://localhost:3000"

prod-down:
	docker-compose -f docker-compose.prod.yml down

# Health check
health:
	docker-compose exec app python scripts/health_check.py

# Database operations
db-migrate:
	docker-compose exec app alembic upgrade head

db-reset:
	docker-compose exec app alembic downgrade base
	docker-compose exec app alembic upgrade head

# Monitoring
monitoring-up:
	docker-compose --profile monitoring up -d

monitoring-down:
	docker-compose --profile monitoring down