#!/usr/bin/env python3
"""
Wazuh AI Companion - Comprehensive Recovery Script

This script provides automated recovery capabilities for:
- PostgreSQL database restoration
- Redis data restoration
- Vector store restoration
- Docker volume restoration
- Configuration restoration
"""

import argparse
import json
import os
import subprocess
import sys
import time
import tarfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml
import logging


class WazuhRecoveryManager:
    """Comprehensive recovery manager for Wazuh AI Companion."""
    
    def __init__(self, backup_dir: str = "/backups"):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.backup_dir = backup_dir
        
        # Setup logging
        self._setup_logging()
        
        # Verify backup directory exists
        if not os.path.exists(self.backup_dir):
            self.logger.error(f"Backup directory does not exist: {self.backup_dir}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = os.path.join(self.backup_dir, 'recovery.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
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
    
    def list_available_backups(self) -> List[Dict]:
        """List all available backup sets."""
        self.logger.info("Scanning for available backups...")
        
        backup_sets = {}
        
        # Scan for backup files
        for filename in os.listdir(self.backup_dir):
            if filename.startswith('backup_manifest_') and filename.endswith('.json'):
                manifest_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    timestamp = manifest.get('timestamp', '')
                    backup_sets[timestamp] = {
                        'timestamp': timestamp,
                        'datetime': manifest.get('datetime', ''),
                        'success': manifest.get('success', False),
                        'files': manifest.get('backup_files', []),
                        'total_size': manifest.get('total_size', 0),
                        'manifest_path': manifest_path
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to read manifest {filename}: {e}")
        
        # Also scan for backup files without manifests
        for filename in os.listdir(self.backup_dir):
            if ('_' in filename and 
                filename.endswith(('.sql', '.sql.gz', '.tar.gz')) and
                not filename.startswith('backup_manifest_')):
                
                parts = filename.split('_')
                if len(parts) >= 2:
                    timestamp = parts[-1].split('.')[0]
                    
                    if timestamp not in backup_sets:
                        backup_sets[timestamp] = {
                            'timestamp': timestamp,
                            'datetime': '',
                            'success': None,
                            'files': [],
                            'total_size': 0,
                            'manifest_path': None
                        }
                    
                    file_path = os.path.join(self.backup_dir, filename)
                    file_size = os.path.getsize(file_path)
                    
                    backup_sets[timestamp]['files'].append({
                        'filename': filename,
                        'path': file_path,
                        'size': file_size
                    })
                    backup_sets[timestamp]['total_size'] += file_size
        
        # Convert to sorted list
        backup_list = list(backup_sets.values())
        backup_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        self.logger.info(f"Found {len(backup_list)} backup sets")
        return backup_list
    
    def verify_backup_integrity(self, backup_set: Dict) -> bool:
        """Verify backup file integrity."""
        self.logger.info(f"Verifying backup integrity for {backup_set['timestamp']}...")
        
        missing_files = []
        corrupted_files = []
        
        for file_info in backup_set['files']:
            file_path = file_info['path']
            
            # Check if file exists
            if not os.path.exists(file_path):
                missing_files.append(file_info['filename'])
                continue
            
            # Check file size
            actual_size = os.path.getsize(file_path)
            expected_size = file_info.get('size', 0)
            
            if expected_size > 0 and actual_size != expected_size:
                corrupted_files.append(f"{file_info['filename']} (size mismatch)")
                continue
            
            # Verify checksum if available
            expected_checksum = file_info.get('checksum')
            if expected_checksum:
                actual_checksum = self._calculate_checksum(file_path)
                if actual_checksum != expected_checksum:
                    corrupted_files.append(f"{file_info['filename']} (checksum mismatch)")
        
        if missing_files:
            self.logger.error(f"Missing backup files: {missing_files}")
        
        if corrupted_files:
            self.logger.error(f"Corrupted backup files: {corrupted_files}")
        
        is_valid = len(missing_files) == 0 and len(corrupted_files) == 0
        
        if is_valid:
            self.logger.info("✅ Backup integrity verification passed")
        else:
            self.logger.error("❌ Backup integrity verification failed")
        
        return is_valid
    
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
    
    def stop_services(self) -> bool:
        """Stop all services before recovery."""
        self.logger.info("Stopping services for recovery...")
        
        # Try to stop with both compose files
        compose_files = ['docker-compose.yml', 'docker-compose.prod.yml']
        
        for compose_file in compose_files:
            if os.path.exists(os.path.join(self.project_root, compose_file)):
                success, output = self.run_command([
                    'docker-compose', '-f', compose_file, 'down'
                ])
                
                if success:
                    self.logger.info(f"Services stopped using {compose_file}")
                    return True
                else:
                    self.logger.warning(f"Failed to stop services with {compose_file}: {output}")
        
        # Fallback: stop all containers
        success, output = self.run_command(['docker', 'stop', '$(docker ps -q)'])
        if success:
            self.logger.info("All Docker containers stopped")
            return True
        else:
            self.logger.error(f"Failed to stop containers: {output}")
            return False
    
    def restore_postgres(self, backup_file: str, database_name: str = 'wazuh_chat') -> bool:
        """Restore PostgreSQL database."""
        self.logger.info(f"Restoring PostgreSQL database from {backup_file}...")
        
        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return False
        
        # Start PostgreSQL container if not running
        success, output = self.run_command([
            'docker-compose', 'up', '-d', 'postgres'
        ])
        
        if not success:
            self.logger.error(f"Failed to start PostgreSQL: {output}")
            return False
        
        # Wait for PostgreSQL to be ready
        self.logger.info("Waiting for PostgreSQL to be ready...")
        for i in range(30):
            success, output = self.run_command([
                'docker-compose', 'exec', '-T', 'postgres',
                'pg_isready', '-U', 'postgres'
            ])
            
            if success:
                break
            
            time.sleep(2)
        else:
            self.logger.error("PostgreSQL did not become ready in time")
            return False
        
        # Drop existing database and recreate
        self.logger.info(f"Recreating database: {database_name}")
        
        success, output = self.run_command([
            'docker-compose', 'exec', '-T', 'postgres',
            'psql', '-U', 'postgres', '-c', f'DROP DATABASE IF EXISTS {database_name};'
        ])
        
        if not success:
            self.logger.error(f"Failed to drop database: {output}")
            return False
        
        success, output = self.run_command([
            'docker-compose', 'exec', '-T', 'postgres',
            'psql', '-U', 'postgres', '-c', f'CREATE DATABASE {database_name};'
        ])
        
        if not success:
            self.logger.error(f"Failed to create database: {output}")
            return False
        
        # Restore database from backup
        self.logger.info("Restoring database data...")
        
        # Handle compressed files
        if backup_file.endswith('.gz'):
            restore_command = f'gunzip -c {backup_file} | docker-compose exec -T postgres psql -U postgres -d {database_name}'
        else:
            restore_command = f'cat {backup_file} | docker-compose exec -T postgres psql -U postgres -d {database_name}'
        
        success, output = self.run_command(['bash', '-c', restore_command], timeout=600)
        
        if success:
            self.logger.info("✅ PostgreSQL database restored successfully")
            return True
        else:
            self.logger.error(f"❌ PostgreSQL restore failed: {output}")
            return False
    
    def restore_docker_volume(self, backup_file: str, volume_name: str) -> bool:
        """Restore Docker volume from backup."""
        self.logger.info(f"Restoring Docker volume {volume_name} from {backup_file}...")
        
        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return False
        
        # Remove existing volume
        success, output = self.run_command([
            'docker', 'volume', 'rm', volume_name
        ])
        
        if not success and "No such volume" not in output:
            self.logger.warning(f"Failed to remove existing volume: {output}")
        
        # Create new volume
        success, output = self.run_command([
            'docker', 'volume', 'create', volume_name
        ])
        
        if not success:
            self.logger.error(f"Failed to create volume: {output}")
            return False
        
        # Restore volume data
        success, output = self.run_command([
            'docker', 'run', '--rm',
            '-v', f'{volume_name}:/data',
            '-v', f'{self.backup_dir}:/backup',
            'alpine',
            'tar', 'xzf', f'/backup/{os.path.basename(backup_file)}',
            '-C', '/data'
        ], timeout=600)
        
        if success:
            self.logger.info(f"✅ Volume {volume_name} restored successfully")
            return True
        else:
            self.logger.error(f"❌ Volume {volume_name} restore failed: {output}")
            return False
    
    def restore_vector_store(self, backup_file: str, target_path: str = './data/vectorstore') -> bool:
        """Restore vector store data."""
        self.logger.info(f"Restoring vector store from {backup_file}...")
        
        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return False
        
        full_target_path = os.path.join(self.project_root, target_path)
        
        # Remove existing vector store
        if os.path.exists(full_target_path):
            shutil.rmtree(full_target_path)
            self.logger.info(f"Removed existing vector store: {full_target_path}")
        
        # Create target directory
        os.makedirs(os.path.dirname(full_target_path), exist_ok=True)
        
        # Extract backup
        try:
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(path=os.path.dirname(full_target_path))
            
            self.logger.info("✅ Vector store restored successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Vector store restore failed: {e}")
            return False
    
    def restore_configuration(self, backup_file: str) -> bool:
        """Restore configuration files."""
        self.logger.info(f"Restoring configuration from {backup_file}...")
        
        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return False
        
        # Create backup of current configuration
        current_config_backup = os.path.join(
            self.backup_dir,
            f"current_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        )
        
        try:
            with tarfile.open(current_config_backup, 'w:gz') as tar:
                config_files = [
                    'docker-compose.yml',
                    'docker-compose.prod.yml',
                    'deployment-config.yaml',
                    'nginx/nginx.conf',
                    'nginx/nginx.prod.conf',
                    'monitoring/prometheus.yml',
                    'monitoring/prometheus.prod.yml',
                    'monitoring/alertmanager.yml',
                    'redis/redis.conf'
                ]
                
                for config_file in config_files:
                    full_path = os.path.join(self.project_root, config_file)
                    if os.path.exists(full_path):
                        tar.add(full_path, arcname=config_file)
            
            self.logger.info(f"Current configuration backed up to: {current_config_backup}")
        except Exception as e:
            self.logger.warning(f"Failed to backup current configuration: {e}")
        
        # Restore configuration
        try:
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(path=self.project_root)
            
            self.logger.info("✅ Configuration restored successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Configuration restore failed: {e}")
            return False
    
    def start_services(self, compose_file: str = 'docker-compose.yml') -> bool:
        """Start services after recovery."""
        self.logger.info("Starting services after recovery...")
        
        success, output = self.run_command([
            'docker-compose', '-f', compose_file, 'up', '-d'
        ], timeout=600)
        
        if success:
            self.logger.info("✅ Services started successfully")
            
            # Wait for services to be healthy
            self.logger.info("Waiting for services to be healthy...")
            time.sleep(30)
            
            # Check application health
            try:
                import requests
                response = requests.get('http://localhost:8000/health', timeout=10)
                if response.status_code == 200:
                    self.logger.info("✅ Application health check passed")
                else:
                    self.logger.warning(f"Application health check failed: HTTP {response.status_code}")
            except Exception as e:
                self.logger.warning(f"Application health check failed: {e}")
            
            return True
        else:
            self.logger.error(f"❌ Failed to start services: {output}")
            return False
    
    def run_recovery(self, backup_timestamp: str, components: List[str], compose_file: str = 'docker-compose.yml') -> bool:
        """Run complete recovery process."""
        self.logger.info(f"Starting recovery process for backup: {backup_timestamp}")
        
        # Find backup set
        backup_sets = self.list_available_backups()
        backup_set = None
        
        for bs in backup_sets:
            if bs['timestamp'] == backup_timestamp:
                backup_set = bs
                break
        
        if not backup_set:
            self.logger.error(f"Backup set not found: {backup_timestamp}")
            return False
        
        # Verify backup integrity
        if not self.verify_backup_integrity(backup_set):
            self.logger.error("Backup integrity check failed. Aborting recovery.")
            return False
        
        # Stop services
        if not self.stop_services():
            self.logger.error("Failed to stop services. Aborting recovery.")
            return False
        
        # Recovery tasks
        recovery_tasks = []
        
        if 'postgres' in components:
            postgres_file = None
            for file_info in backup_set['files']:
                if 'postgres' in file_info['filename']:
                    postgres_file = file_info['path']
                    break
            
            if postgres_file:
                recovery_tasks.append(('PostgreSQL Database', lambda: self.restore_postgres(postgres_file)))
            else:
                self.logger.warning("PostgreSQL backup file not found")
        
        if 'redis' in components:
            redis_file = None
            for file_info in backup_set['files']:
                if 'redis_data' in file_info['filename']:
                    redis_file = file_info['path']
                    break
            
            if redis_file:
                recovery_tasks.append(('Redis Data', lambda: self.restore_docker_volume(redis_file, 'redis_data')))
            else:
                self.logger.warning("Redis backup file not found")
        
        if 'vectorstore' in components:
            vector_file = None
            for file_info in backup_set['files']:
                if 'vectorstore' in file_info['filename']:
                    vector_file = file_info['path']
                    break
            
            if vector_file:
                recovery_tasks.append(('Vector Store', lambda: self.restore_vector_store(vector_file)))
            else:
                self.logger.warning("Vector store backup file not found")
        
        if 'volumes' in components:
            volume_files = []
            for file_info in backup_set['files']:
                filename = file_info['filename']
                if ('_data_' in filename and 
                    filename.endswith('.tar.gz') and 
                    'postgres' not in filename and 
                    'redis' not in filename):
                    
                    volume_name = filename.split('_data_')[0] + '_data'
                    volume_files.append((volume_name, file_info['path']))
            
            for volume_name, volume_file in volume_files:
                recovery_tasks.append((f'Volume {volume_name}', lambda vf=volume_file, vn=volume_name: self.restore_docker_volume(vf, vn)))
        
        if 'configuration' in components:
            config_file = None
            for file_info in backup_set['files']:
                if 'configuration' in file_info['filename']:
                    config_file = file_info['path']
                    break
            
            if config_file:
                recovery_tasks.append(('Configuration', lambda: self.restore_configuration(config_file)))
            else:
                self.logger.warning("Configuration backup file not found")
        
        # Execute recovery tasks
        success_count = 0
        for task_name, task_function in recovery_tasks:
            self.logger.info(f"Running recovery task: {task_name}")
            try:
                success = task_function()
                if success:
                    success_count += 1
                    self.logger.info(f"✅ {task_name} recovery completed")
                else:
                    self.logger.error(f"❌ {task_name} recovery failed")
            except Exception as e:
                self.logger.error(f"❌ {task_name} recovery failed with exception: {e}")
        
        # Start services
        if success_count > 0:
            service_start_success = self.start_services(compose_file)
        else:
            service_start_success = False
        
        # Summary
        overall_success = success_count == len(recovery_tasks) and service_start_success
        self.logger.info(f"Recovery process completed: {success_count}/{len(recovery_tasks)} tasks successful")
        
        if overall_success:
            self.logger.info("🎉 Recovery completed successfully!")
        else:
            self.logger.error("❌ Recovery completed with errors. Check logs for details.")
        
        return overall_success


def main():
    """Main recovery script entry point."""
    parser = argparse.ArgumentParser(description="Wazuh AI Companion Recovery Script")
    parser.add_argument(
        "action",
        choices=["list", "verify", "restore"],
        help="Recovery action to perform"
    )
    parser.add_argument(
        "--backup-dir", "-d",
        default="/backups",
        help="Backup directory path"
    )
    parser.add_argument(
        "--timestamp", "-t",
        help="Backup timestamp to restore"
    )
    parser.add_argument(
        "--components", "-c",
        nargs="+",
        choices=["postgres", "redis", "vectorstore", "volumes", "configuration"],
        default=["postgres", "redis", "vectorstore", "volumes"],
        help="Components to restore"
    )
    parser.add_argument(
        "--compose-file", "-f",
        default="docker-compose.yml",
        help="Docker Compose file to use for service management"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recovery without confirmation"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Create recovery manager
    recovery_manager = WazuhRecoveryManager(backup_dir=args.backup_dir)
    
    if args.verbose:
        recovery_manager.logger.setLevel(logging.DEBUG)
    
    if args.action == "list":
        # List available backups
        backup_sets = recovery_manager.list_available_backups()
        
        if not backup_sets:
            print("No backups found.")
            sys.exit(0)
        
        print("\nAvailable Backup Sets:")
        print("=" * 80)
        print(f"{'Timestamp':<20} {'Date/Time':<20} {'Status':<10} {'Size (MB)':<12} {'Files':<8}")
        print("-" * 80)
        
        for backup_set in backup_sets:
            timestamp = backup_set['timestamp']
            datetime_str = backup_set['datetime'][:19] if backup_set['datetime'] else 'Unknown'
            status = '✅ Success' if backup_set['success'] else ('❌ Failed' if backup_set['success'] is False else '❓ Unknown')
            size_mb = backup_set['total_size'] / (1024 * 1024)
            file_count = len(backup_set['files'])
            
            print(f"{timestamp:<20} {datetime_str:<20} {status:<10} {size_mb:<12.2f} {file_count:<8}")
        
        sys.exit(0)
    
    elif args.action == "verify":
        if not args.timestamp:
            print("Error: --timestamp is required for verify action")
            sys.exit(1)
        
        # Find and verify backup
        backup_sets = recovery_manager.list_available_backups()
        backup_set = None
        
        for bs in backup_sets:
            if bs['timestamp'] == args.timestamp:
                backup_set = bs
                break
        
        if not backup_set:
            print(f"Error: Backup set not found: {args.timestamp}")
            sys.exit(1)
        
        success = recovery_manager.verify_backup_integrity(backup_set)
        sys.exit(0 if success else 1)
    
    elif args.action == "restore":
        if not args.timestamp:
            print("Error: --timestamp is required for restore action")
            sys.exit(1)
        
        # Confirmation
        if not args.force:
            print(f"⚠️  WARNING: This will restore data from backup {args.timestamp}")
            print(f"Components to restore: {', '.join(args.components)}")
            print("This operation will:")
            print("- Stop all running services")
            print("- Replace current data with backup data")
            print("- Restart services")
            print()
            
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Recovery cancelled.")
                sys.exit(0)
        
        # Run recovery
        success = recovery_manager.run_recovery(
            backup_timestamp=args.timestamp,
            components=args.components,
            compose_file=args.compose_file
        )
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()