# Database Migration Setup

## Overview

The Wazuh AI Companion database migration system is now fully configured using Alembic. This setup provides complete database schema management for all application models.

## Migration Files

### 000_initial_schema.py
- **Purpose**: Creates the core database schema
- **Tables Created**:
  - `users` - User authentication and profile data
  - `chat_sessions` - Chat session management
  - `messages` - Chat message history
  - `log_entries` - Wazuh log storage and indexing
  - `query_metrics` - Analytics for user queries
  - `system_metrics` - System performance metrics

### 001_add_audit_logging_tables.py
- **Purpose**: Adds audit logging and security features
- **Tables Created**:
  - `audit_logs` - Comprehensive audit trail
  - `security_events` - Security incident tracking
  - `compliance_reports` - Compliance reporting data

## Database Schema Coverage

All models from `models/database.py` are covered:
- ✅ User
- ✅ ChatSession
- ✅ Message
- ✅ LogEntry
- ✅ QueryMetrics
- ✅ SystemMetrics
- ✅ AuditLog
- ✅ SecurityEvent
- ✅ ComplianceReport

## Indexes and Constraints

All migrations include:
- Primary key constraints
- Foreign key relationships
- Unique constraints
- Performance indexes for common queries
- Composite indexes for complex queries

## Migration Operations

### Upgrade (Up)
- Creates all tables with proper relationships
- Adds all indexes and constraints
- Sets up proper data types and defaults

### Downgrade (Down)
- Safely removes tables in reverse dependency order
- Cleans up all indexes and constraints
- Maintains referential integrity during rollback

## Usage

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migrations
```bash
alembic downgrade -1  # Rollback one migration
alembic downgrade base  # Rollback all migrations
```

### Check Current Version
```bash
alembic current
```

### View Migration History
```bash
alembic history
```

## Testing

The migration setup has been thoroughly tested:
- ✅ Migration file structure validation
- ✅ Table creation verification
- ✅ Index and constraint validation
- ✅ Foreign key relationship testing
- ✅ Up/down operation validation
- ✅ Model-migration consistency check

## Configuration

- **Alembic Config**: `alembic.ini`
- **Environment Setup**: `alembic/env.py`
- **Migration Directory**: `alembic/versions/`

The system is configured to work with PostgreSQL in production and can be adapted for other databases as needed.