"""Initial database schema

Revision ID: 000_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema with all core tables."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create indexes for users table
    op.create_index('idx_user_username_active', 'users', ['username', 'is_active'])
    op.create_index('idx_user_email_active', 'users', ['email', 'is_active'])
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_sessions table
    op.create_index('idx_session_user_active', 'chat_sessions', ['user_id', 'is_active'])
    op.create_index('idx_session_created_at', 'chat_sessions', ['created_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for messages table
    op.create_index('idx_message_session_timestamp', 'messages', ['session_id', 'timestamp'])
    op.create_index('idx_message_role', 'messages', ['role'])
    
    # Create log_entries table
    op.create_table(
        'log_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('full_log', sa.Text(), nullable=False),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('embedding_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for log_entries table
    op.create_index('idx_log_timestamp_source', 'log_entries', ['timestamp', 'source'])
    op.create_index('idx_log_level_timestamp', 'log_entries', ['level', 'timestamp'])
    op.create_index('idx_log_embedding', 'log_entries', ['embedding_id'])
    op.create_index('ix_log_entries_timestamp', 'log_entries', ['timestamp'])
    op.create_index('ix_log_entries_source', 'log_entries', ['source'])
    op.create_index('ix_log_entries_level', 'log_entries', ['level'])
    
    # Create query_metrics table
    op.create_table(
        'query_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('response_time', sa.Float(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('logs_searched', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for query_metrics table
    op.create_index('idx_metrics_user_timestamp', 'query_metrics', ['user_id', 'timestamp'])
    op.create_index('idx_metrics_success_timestamp', 'query_metrics', ['success', 'timestamp'])
    op.create_index('idx_metrics_response_time', 'query_metrics', ['response_time'])
    
    # Create system_metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for system_metrics table
    op.create_index('idx_system_metrics_name_timestamp', 'system_metrics', ['metric_name', 'timestamp'])
    op.create_index('ix_system_metrics_metric_name', 'system_metrics', ['metric_name'])


def downgrade():
    """Drop all initial schema tables."""
    
    # Drop system_metrics table and indexes
    op.drop_index('ix_system_metrics_metric_name', table_name='system_metrics')
    op.drop_index('idx_system_metrics_name_timestamp', table_name='system_metrics')
    op.drop_table('system_metrics')
    
    # Drop query_metrics table and indexes
    op.drop_index('idx_metrics_response_time', table_name='query_metrics')
    op.drop_index('idx_metrics_success_timestamp', table_name='query_metrics')
    op.drop_index('idx_metrics_user_timestamp', table_name='query_metrics')
    op.drop_table('query_metrics')
    
    # Drop log_entries table and indexes
    op.drop_index('ix_log_entries_level', table_name='log_entries')
    op.drop_index('ix_log_entries_source', table_name='log_entries')
    op.drop_index('ix_log_entries_timestamp', table_name='log_entries')
    op.drop_index('idx_log_embedding', table_name='log_entries')
    op.drop_index('idx_log_level_timestamp', table_name='log_entries')
    op.drop_index('idx_log_timestamp_source', table_name='log_entries')
    op.drop_table('log_entries')
    
    # Drop messages table and indexes
    op.drop_index('idx_message_role', table_name='messages')
    op.drop_index('idx_message_session_timestamp', table_name='messages')
    op.drop_table('messages')
    
    # Drop chat_sessions table and indexes
    op.drop_index('idx_session_created_at', table_name='chat_sessions')
    op.drop_index('idx_session_user_active', table_name='chat_sessions')
    op.drop_table('chat_sessions')
    
    # Drop users table and indexes
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('idx_user_email_active', table_name='users')
    op.drop_index('idx_user_username_active', table_name='users')
    op.drop_table('users')