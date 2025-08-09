#!/usr/bin/env python3
"""
AI-Enhanced Security Query Interface - Comprehensive Backup Script

This script provides automated backup capabilities for the self-contained security appliance:
- PostgreSQL database
- Redis data
- Embedded AI models and vector store data
- Application configuration
- Monitoring data

This backup script is designed for the embedded AI appliance with no external dependencies.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import tarfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yaml
import logging


class SecurityApplianceBackupManager:
    """Comprehensive backup manager for AI-Enhanced Security Query Interface appliance."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.backup_config = self._load_backup_config(config_file)
        self.backup_dir = self.backup_config.get('backup_directory', '/backups')
        self.retention_days = self.backup_config.get('retention_days', 30)
        
        # Setup logging
        self._setup_logging()
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.backup_config.get('log_level', 'INFO')
        log_file = os.path.join(self.backup_dir, 'backup.log')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _load_backup_config(self, config_file: Optional[str] = None) -> Dict:
        """Load backup configuration."""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration for self-contained security appliance
        return {
            'backup_directory': '/backups',
            'retention_days': 30,
            'compression': True,
            'encryption': False,
            'log_level': 'INFO',
            'databases': {
                'postgres': {
                    'enabled': True,
                    'container_name': 'postgres',
                    'database_name': 'wazuh_chat',
                    'username': 'postgres'
                }
            },
            'volumes': {
                'redis_data': {'enabled': True, 'description': 'Redis cache data'},
                'model_data': {'enabled': True, 'description': 'Embedded AI models'},
                'vectorstore_data': {'enabled': True, 'description': 'Vector store and embeddings'},
                'prometheus_data': {'enabled': True, 'description': 'Monitoring metrics'},
                'grafana_data': {'enabled': True, 'description': 'Dashboard configurations'}
            },
            'embedded_ai': {
                'enabled': True,
                'models_path': './models',
                'vectorstore_path': './data/vectorstore',
                'backup_model_configs': True,
                'backup_huggingface_cache': True
            },
            's3': {
                'enabled': False,
                'bucket': '',
                'region': 'us-east-1',
                'access_key': '',
                'secret_key': ''
            }
        }
    
    def run_command(self, command: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            self.logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Command failed: {' '.join(command)}")
                self.logger.error(f"Error output: {result.stderr}")
            
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return False, str(e)
    
    def backup_postgres(self, timestamp: str) -> bool:
        """Backup PostgreSQL database."""
        self.logger.info("Starting PostgreSQL backup...")
        
        db_config = self.backup_config['databases']['postgres']
        if not db_config.get('enabled', True):
            self.logger.info("PostgreSQL backup disabled, skipping...")
            return True
        
        container_name = db_config.get('container_name', 'postgres')
        database_name = db_config.get('database_name', 'wazuh_chat')
        username = db_config.get('username', 'postgres')
        
        backup_file = os.path.join(
            self.backup_dir,
            f"postgres_{database_name}_{timestamp}.sql"
        )
        
        # Create database dump
        success, output = self.run_command([
            'docker', 'exec', container_name,
            'pg_dump', '-U', username, '-d', database_name
        ], timeout=600)
        
        if success:
            # Write dump to file
            with open(backup_file, 'w') as f:
                f.write(output)
            
            # Compress if enabled
            if self.backup_config.get('compression', True):
                compressed_file = f"{backup_file}.gz"
                success, _ = self.run_command(['gzip', backup_file])
                if success:
                    backup_file = compressed_file
                    self.logger.info(f"PostgreSQL backup compressed: {backup_file}")
            
            # Get file size
            file_size = os.path.getsize(backup_file)
            self.logger.info(f"PostgreSQL backup completed: {backup_file} ({file_size} bytes)")
            return True
        else:
            self.logger.error(f"PostgreSQL backup failed: {output}")
            return False
    
    def backup_redis(self, timestamp: str) -> bool:
        """Backup Redis data."""
        self.logger.info("Starting Redis backup...")
        
        if not self.backup_config['volumes']['redis_data'].get('enabled', True):
            self.logger.info("Redis backup disabled, skipping...")
            return True
        
        backup_file = os.path.join(
            self.backup_dir,
            f"redis_data_{timestamp}.tar.gz"
        )
        
        # Create Redis backup using docker volume backup
        success, output = self.run_command([
            'docker', 'run', '--rm',
            '-v', 'redis_data:/data',
            '-v', f'{self.backup_dir}:/backup',
            'alpine',
            'tar', 'czf', f'/backup/redis_data_{timestamp}.tar.gz',
            '-C', '/data', '.'
        ], timeout=300)
        
        if success:
            file_size = os.path.getsize(backup_file)
            self.logger.info(f"Redis backup completed: {backup_file} ({file_size} bytes)")
            return True
        else:
            self.logger.error(f"Redis backup failed: {output}")
            return False
    
    def backup_embedded_ai_data(self, timestamp: str) -> bool:
        """Backup embedded AI models and vector store data."""
        self.logger.info("Starting embedded AI data backup...")
        
        ai_config = self.backup_config.get('embedded_ai', {})
        if not ai_config.get('enabled', True):
            self.logger.info("Embedded AI backup disabled, skipping...")
            return True
        
        success_count = 0
        total_count = 0
        
        # Backup models directory
        models_path = ai_config.get('models_path', './models')
        full_models_path = os.path.join(self.project_root, models_path)
        
        if os.path.exists(full_models_path):
            total_count += 1
            backup_file = os.path.join(
                self.backup_dir,
                f"embedded_ai_models_{timestamp}.tar.gz"
            )
            
            try:
                with tarfile.open(backup_file, 'w:gz') as tar:
                    tar.add(full_models_path, arcname='models')
                
                file_size = os.path.getsize(backup_file)
                self.logger.info(f"AI models backup completed: {backup_file} ({file_size} bytes)")
                success_count += 1
            except Exception as e:
                self.logger.error(f"AI models backup failed: {e}")
        else:
            self.logger.warning(f"Models path does not exist: {full_models_path}")
        
        # Backup vector store directory
        vectorstore_path = ai_config.get('vectorstore_path', './data/vectorstore')
        full_vectorstore_path = os.path.join(self.project_root, vectorstore_path)
        
        if os.path.exists(full_vectorstore_path):
            total_count += 1
            backup_file = os.path.join(
                self.backup_dir,
                f"vectorstore_{timestamp}.tar.gz"
            )
            
            try:
                with tarfile.open(backup_file, 'w:gz') as tar:
                    tar.add(full_vectorstore_path, arcname='vectorstore')
                
                file_size = os.path.getsize(backup_file)
                self.logger.info(f"Vector store backup completed: {backup_file} ({file_size} bytes)")
                success_count += 1
            except Exception as e:
                self.logger.error(f"Vector store backup failed: {e}")
        else:
            self.logger.warning(f"Vector store path does not exist: {full_vectorstore_path}")
        
        self.logger.info(f"Embedded AI data backup completed: {success_count}/{total_count} successful")
        return success_count == total_count or total_count == 0
    
    def backup_docker_volumes(self, timestamp: str) -> bool:
        """Backup Docker volumes."""
        self.logger.info("Starting Docker volumes backup...")
        
        volumes_config = self.backup_config['volumes']
        success_count = 0
        total_count = 0
        
        for volume_name, config in volumes_config.items():
            if not config.get('enabled', True):
                self.logger.info(f"Volume {volume_name} backup disabled, skipping...")
                continue
            
            total_count += 1
            backup_file = os.path.join(
                self.backup_dir,
                f"{volume_name}_{timestamp}.tar.gz"
            )
            
            # Check if volume exists
            success, output = self.run_command([
                'docker', 'volume', 'inspect', volume_name
            ])
            
            if not success:
                self.logger.warning(f"Volume {volume_name} does not exist, skipping...")
                continue
            
            # Backup volume
            success, output = self.run_command([
                'docker', 'run', '--rm',
                '-v', f'{volume_name}:/data',
                '-v', f'{self.backup_dir}:/backup',
                'alpine',
                'tar', 'czf', f'/backup/{volume_name}_{timestamp}.tar.gz',
                '-C', '/data', '.'
            ], timeout=600)
            
            if success:
                file_size = os.path.getsize(backup_file)
                self.logger.info(f"Volume {volume_name} backup completed: {backup_file} ({file_size} bytes)")
                success_count += 1
            else:
                self.logger.error(f"Volume {volume_name} backup failed: {output}")
        
        self.logger.info(f"Docker volumes backup completed: {success_count}/{total_count} successful")
        return success_count == total_count
    
    def backup_configuration(self, timestamp: str) -> bool:
        """Backup application configuration files."""
        self.logger.info("Starting configuration backup...")
        
        config_files = [
            'docker-compose.yml',
            'docker-compose.prod.yml',
            'deployment-config.yaml',
            '.env.example',
            'nginx/nginx.conf',
            'nginx/nginx.prod.conf',
            'monitoring/prometheus.yml',
            'monitoring/prometheus.prod.yml',
            'monitoring/alertmanager.yml',
            'redis/redis.conf'
        ]
        
        backup_file = os.path.join(
            self.backup_dir,
            f"configuration_{timestamp}.tar.gz"
        )
        
        try:
            with tarfile.open(backup_file, 'w:gz') as tar:
                for config_file in config_files:
                    full_path = os.path.join(self.project_root, config_file)
                    if os.path.exists(full_path):
                        tar.add(full_path, arcname=config_file)
                        self.logger.debug(f"Added to config backup: {config_file}")
                    else:
                        self.logger.warning(f"Configuration file not found: {config_file}")
            
            file_size = os.path.getsize(backup_file)
            self.logger.info(f"Configuration backup completed: {backup_file} ({file_size} bytes)")
            return True
        except Exception as e:
            self.logger.error(f"Configuration backup failed: {e}")
            return False
    
    def upload_to_s3(self, backup_files: List[str]) -> bool:
        """Upload backup files to S3."""
        s3_config = self.backup_config.get('s3', {})
        if not s3_config.get('enabled', False):
            self.logger.info("S3 upload disabled, skipping...")
            return True
        
        self.logger.info("Starting S3 upload...")
        
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.logger.error("boto3 not installed. Install with: pip install boto3")
            return False
        
        try:
            s3_client = boto3.client(
                's3',
                region_name=s3_config.get('region', 'us-east-1'),
                aws_access_key_id=s3_config.get('access_key'),
                aws_secret_access_key=s3_config.get('secret_key')
            )
            
            bucket = s3_config.get('bucket')
            success_count = 0
            
            for backup_file in backup_files:
                if not os.path.exists(backup_file):
                    continue
                
                file_name = os.path.basename(backup_file)
                s3_key = f"security-appliance/{datetime.now().strftime('%Y/%m/%d')}/{file_name}"
                
                try:
                    s3_client.upload_file(backup_file, bucket, s3_key)
                    self.logger.info(f"Uploaded to S3: {s3_key}")
                    success_count += 1
                except ClientError as e:
                    self.logger.error(f"Failed to upload {file_name} to S3: {e}")
            
            self.logger.info(f"S3 upload completed: {success_count}/{len(backup_files)} successful")
            return success_count == len(backup_files)
        
        except Exception as e:
            self.logger.error(f"S3 upload failed: {e}")
            return False
    
    def cleanup_old_backups(self) -> bool:
        """Clean up old backup files."""
        self.logger.info(f"Cleaning up backups older than {self.retention_days} days...")
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.endswith(('.sql', '.sql.gz', '.tar.gz', '.log')):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        self.logger.debug(f"Deleted old backup: {filename}")
                        deleted_count += 1
            
            self.logger.info(f"Cleanup completed: {deleted_count} old backup files deleted")
            return True
        
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False
    
    def create_backup_manifest(self, timestamp: str, backup_files: List[str], success: bool) -> bool:
        """Create backup manifest with metadata."""
        manifest_file = os.path.join(self.backup_dir, f"backup_manifest_{timestamp}.json")
        
        manifest = {
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'success': success,
            'backup_files': [],
            'total_size': 0,
            'configuration': self.backup_config
        }
        
        for backup_file in backup_files:
            if os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file)
                manifest['backup_files'].append({
                    'filename': os.path.basename(backup_file),
                    'path': backup_file,
                    'size': file_size,
                    'checksum': self._calculate_checksum(backup_file)
                })
                manifest['total_size'] += file_size
        
        try:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Backup manifest created: {manifest_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup manifest: {e}")
            return False
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def run_full_backup(self) -> bool:
        """Run complete backup process."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.logger.info(f"Starting full backup process: {timestamp}")
        
        backup_tasks = [
            ("PostgreSQL Database", self.backup_postgres),
            ("Redis Data", self.backup_redis),
            ("Embedded AI Data", self.backup_embedded_ai_data),
            ("Docker Volumes", self.backup_docker_volumes),
            ("Configuration", self.backup_configuration)
        ]
        
        backup_files = []
        success_count = 0
        
        for task_name, task_function in backup_tasks:
            self.logger.info(f"Running backup task: {task_name}")
            try:
                success = task_function(timestamp)
                if success:
                    success_count += 1
                    self.logger.info(f"✅ {task_name} backup completed")
                else:
                    self.logger.error(f"❌ {task_name} backup failed")
            except Exception as e:
                self.logger.error(f"❌ {task_name} backup failed with exception: {e}")
        
        # Collect backup files
        for filename in os.listdir(self.backup_dir):
            if timestamp in filename and filename.endswith(('.sql', '.sql.gz', '.tar.gz')):
                backup_files.append(os.path.join(self.backup_dir, filename))
        
        # Upload to S3 if configured
        s3_success = self.upload_to_s3(backup_files)
        
        # Create backup manifest
        overall_success = success_count == len(backup_tasks) and s3_success
        self.create_backup_manifest(timestamp, backup_files, overall_success)
        
        # Cleanup old backups
        self.cleanup_old_backups()
        
        # Summary
        total_size = sum(os.path.getsize(f) for f in backup_files if os.path.exists(f))
        self.logger.info(f"Backup process completed: {success_count}/{len(backup_tasks)} tasks successful")
        self.logger.info(f"Total backup size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
        
        return overall_success


def main():
    """Main backup script entry point."""
    parser = argparse.ArgumentParser(description="AI-Enhanced Security Query Interface Backup Script")
    parser.add_argument(
        "--config", "-c",
        help="Path to backup configuration file"
    )
    parser.add_argument(
        "--backup-dir", "-d",
        help="Backup directory path"
    )
    parser.add_argument(
        "--retention-days", "-r",
        type=int,
        help="Number of days to retain backups"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Create backup manager
    backup_manager = SecurityApplianceBackupManager(config_file=args.config)
    
    # Override configuration with command line arguments
    if args.backup_dir:
        backup_manager.backup_dir = args.backup_dir
        os.makedirs(backup_manager.backup_dir, exist_ok=True)
    
    if args.retention_days:
        backup_manager.retention_days = args.retention_days
    
    if args.verbose:
        backup_manager.logger.setLevel(logging.DEBUG)
    
    # Run backup
    success = backup_manager.run_full_backup()
    
    if success:
        print("🎉 Backup completed successfully!")
        sys.exit(0)
    else:
        print("❌ Backup completed with errors. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()