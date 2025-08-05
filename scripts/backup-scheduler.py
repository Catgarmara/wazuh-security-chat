#!/usr/bin/env python3
"""
Wazuh AI Companion - Backup Scheduler

This script provides automated backup scheduling and management,
including cron job setup, backup monitoring, and notification handling.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml
import logging
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart


class BackupScheduler:
    """Automated backup scheduler and monitor."""
    
    def __init__(self, config_file: str = "backup-config.yaml"):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(self.project_root, config_file)
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config.get('log_level', 'INFO')
        backup_dir = self.config.get('backup_directory', '/backups')
        log_file = os.path.join(backup_dir, 'scheduler.log')
        
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> Dict:
        """Load backup configuration."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            self.logger.error(f"Configuration file not found: {self.config_file}")
            sys.exit(1)
    
    def setup_cron_jobs(self) -> bool:
        """Setup cron jobs for automated backups."""
        self.logger.info("Setting up cron jobs for automated backups...")
        
        schedule_config = self.config.get('schedule', {})
        
        # Cron job entries
        cron_entries = []
        
        # Full backup
        if 'full_backup' in schedule_config:
            full_backup_schedule = schedule_config['full_backup']
            full_backup_command = f"{sys.executable} {os.path.join(self.project_root, 'scripts/backup.py')} --config {self.config_file}"
            cron_entries.append(f"{full_backup_schedule} {full_backup_command} >> /var/log/wazuh-backup.log 2>&1")
        
        # Incremental backup
        if 'incremental' in schedule_config:
            incremental_schedule = schedule_config['incremental']
            incremental_command = f"{sys.executable} {os.path.join(self.project_root, 'scripts/backup-scheduler.py')} run-incremental --config {self.config_file}"
            cron_entries.append(f"{incremental_schedule} {incremental_command} >> /var/log/wazuh-backup.log 2>&1")
        
        # Database-only backup
        if 'database_only' in schedule_config:
            db_schedule = schedule_config['database_only']
            db_command = f"{sys.executable} {os.path.join(self.project_root, 'scripts/backup-scheduler.py')} run-database --config {self.config_file}"
            cron_entries.append(f"{db_schedule} {db_command} >> /var/log/wazuh-backup.log 2>&1")
        
        # Backup validation
        validation_command = f"{sys.executable} {os.path.join(self.project_root, 'scripts/backup-scheduler.py')} validate --config {self.config_file}"
        cron_entries.append(f"0 3 * * * {validation_command} >> /var/log/wazuh-backup.log 2>&1")
        
        # Cleanup old backups
        cleanup_command = f"{sys.executable} {os.path.join(self.project_root, 'scripts/backup-