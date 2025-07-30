#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Wazuh AI Companion...${NC}"

# Wait for database to be ready
echo -e "${YELLOW}⏳ Waiting for database...${NC}"
while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
    echo "Database is unavailable - sleeping"
    sleep 1
done
echo -e "${GREEN}✅ Database is ready!${NC}"

# Wait for Redis to be ready
echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo -e "${GREEN}✅ Redis is ready!${NC}"

# Run database migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
alembic upgrade head
echo -e "${GREEN}✅ Database migrations completed!${NC}"

# Create initial admin user if it doesn't exist
echo -e "${YELLOW}👤 Setting up initial admin user...${NC}"
python -c "
import asyncio
from core.container import get_container
from services.auth_service import AuthService
from models.schemas import UserCreate, UserRole

async def create_admin():
    container = get_container()
    auth_service = container.get(AuthService)
    
    try:
        # Check if admin user exists
        existing_user = await auth_service.get_user_by_username('admin')
        if not existing_user:
            admin_user = UserCreate(
                username='admin',
                email='admin@wazuh.local',
                password='admin123',  # Change this in production!
                role=UserRole.ADMIN
            )
            await auth_service.create_user(admin_user)
            print('✅ Admin user created successfully!')
        else:
            print('ℹ️  Admin user already exists')
    except Exception as e:
        print(f'⚠️  Could not create admin user: {e}')

asyncio.run(create_admin())
"

echo -e "${GREEN}🎉 Initialization completed!${NC}"

# Execute the main command
exec "$@"