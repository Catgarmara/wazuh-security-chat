"""Add audit logging and security event tables

Revision ID: 001_audit_logging
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_audit_logging'
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create audit logging and security event tables."""
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit_logs
    op.create_index('idx_audit_event_type_timestamp', 'audit_logs', ['event_type', 'timestamp'])
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_resource_type_timestamp', 'audit_logs', ['resource_type', 'timestamp'])
    op.create_index('idx_audit_ip_timestamp', 'audit_logs', ['ip_address', 'timestamp'])
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('idx_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('idx_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    op.create_index('idx_audit_logs_session_id', 'audit_logs', ['session_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    
    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for security_events
    op.create_index('idx_security_event_type_timestamp', 'security_events', ['event_type', 'timestamp'])
    op.create_index('idx_security_severity_timestamp', 'security_events', ['severity', 'timestamp'])
    op.create_index('idx_security_resolved_timestamp', 'security_events', ['resolved', 'timestamp'])
    op.create_index('idx_security_user_timestamp', 'security_events', ['user_id', 'timestamp'])
    op.create_index('idx_security_ip_timestamp', 'security_events', ['ip_address', 'timestamp'])
    op.create_index('idx_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('idx_security_events_severity', 'security_events', ['severity'])
    op.create_index('idx_security_events_resolved', 'security_events', ['resolved'])
    op.create_index('idx_security_events_timestamp', 'security_events', ['timestamp'])
    
    # Create compliance_reports table
    op.create_table(
        'compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_data', sa.JSON(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for compliance_reports
    op.create_index('idx_compliance_type_period', 'compliance_reports', ['report_type', 'period_start', 'period_end'])
    op.create_index('idx_compliance_generated_by', 'compliance_reports', ['generated_by'])
    op.create_index('idx_compliance_reports_report_type', 'compliance_reports', ['report_type'])
    op.create_index('idx_compliance_reports_period_start', 'compliance_reports', ['period_start'])
    op.create_index('idx_compliance_reports_period_end', 'compliance_reports', ['period_end'])


def downgrade():
    """Drop audit logging and security event tables."""
    
    # Drop compliance_reports table and indexes
    op.drop_index('idx_compliance_reports_period_end', table_name='compliance_reports')
    op.drop_index('idx_compliance_reports_period_start', table_name='compliance_reports')
    op.drop_index('idx_compliance_reports_report_type', table_name='compliance_reports')
    op.drop_index('idx_compliance_generated_by', table_name='compliance_reports')
    op.drop_index('idx_compliance_type_period', table_name='compliance_reports')
    op.drop_table('compliance_reports')
    
    # Drop security_events table and indexes
    op.drop_index('idx_security_events_timestamp', table_name='security_events')
    op.drop_index('idx_security_events_resolved', table_name='security_events')
    op.drop_index('idx_security_events_severity', table_name='security_events')
    op.drop_index('idx_security_events_event_type', table_name='security_events')
    op.drop_index('idx_security_ip_timestamp', table_name='security_events')
    op.drop_index('idx_security_user_timestamp', table_name='security_events')
    op.drop_index('idx_security_resolved_timestamp', table_name='security_events')
    op.drop_index('idx_security_severity_timestamp', table_name='security_events')
    op.drop_index('idx_security_event_type_timestamp', table_name='security_events')
    op.drop_table('security_events')
    
    # Drop audit_logs table and indexes
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_logs_session_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_ip_address', table_name='audit_logs')
    op.drop_index('idx_audit_logs_resource_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('idx_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('idx_audit_ip_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_resource_type_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_user_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_event_type_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')