-- Database initialization script for Wazuh AI Companion

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database user if it doesn't exist (for production)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'wazuh_app') THEN
        CREATE ROLE wazuh_app WITH LOGIN PASSWORD 'secure_password_change_in_production';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE wazuh_chat TO wazuh_app;
GRANT USAGE ON SCHEMA public TO wazuh_app;
GRANT CREATE ON SCHEMA public TO wazuh_app;

-- Create indexes for better performance (these will be created by Alembic migrations)
-- This is just a placeholder for any additional setup needed