#!/usr/bin/env python3
"""
Comprehensive Backup and Recovery Test Script

This script performs end-to-end testing of the backup and recovery system
to ensure data integrity and disaster recovery capabilities.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import logging


class BackupRecoveryTester:
    """Comprehensive backup and recovery testing framework."""
    
    def __init__(self, test_dir: Optional[str] = None):
        self.test_dir = test_dir or tempfile.mkdtemp(prefix="backup_recovery_test_")
        self.backup_dir = os.path.join(self.test_dir, "backups")
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Test results
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
        
        # Setup logging
        self._setup_logging()
        
        # Ensure test directories exist
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = os.path.join(self.test_dir, "backup_recovery_test.log")
        
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
            
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)
    
    def create_test_environment(self) -> bool:
        """Create a test environment with sample data."""
        self.logger.info("Creating test environment...")
        
        try:
            # Create test vector store data
            vectorstore_path = os.path.join(self.test_dir, "data", "vectorstore", "default")
            os.makedirs(vectorstore_path, exist_ok=True)
            
            # Create mock FAISS files
            with open(os.path.join(vectorstore_path, "faiss_index.faiss"), 'wb') as f:
                f.write(b"mock_faiss_index_data" * 100)  # Create some data
            
            with open(os.path.join(vectorstore_path, "faiss_index.pkl"), 'wb') as f:
                f.write(b"mock_faiss_pickle_data" * 50)
            
            # Create metadata
            metadata = {
                "identifier": "default",
                "created_at": datetime.now().isoformat(),
                "embedding_model": "all-MiniLM-L6-v2",
                "document_count": 1000,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(os.path.join(vectorstore_path, "metadata.json"), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create test configuration files
            config_files = {
                "docker-compose.yml": """
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: wazuh_chat
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
  redis:
    image: redis:7-alpine
  app:
    build: .
    depends_on:
      - postgres
      - redis
""",
                "backup-config.yaml": f"""
backup_directory: "{self.backup_dir}"
retention_days: 7
compression: true
databases:
  postgres:
    enabled: true
    container_name: "postgres"
    database_name: "wazuh_chat"
    username: "postgres"
volumes:
  redis_data:
    enabled: true
  ollama_data:
    enabled: true
vector_store:
  enabled: true
  path: "./data/vectorstore"
"""
            }
            
            for filename, content in config_files.items():
                with open(os.path.join(self.test_dir, filename), 'w') as f:
                    f.write(content)
            
            self.logger.info("✅ Test environment created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create test environment: {e}")
            return False
    
    def test_vector_store_backup(self) -> bool:
        """Test vector store backup functionality."""
        self.logger.info("Testing vector store backup...")
        
        try:
            # Import AI service
            sys.path.insert(0, self.project_root)
            from services.ai_service import AIService
            from unittest.mock import Mock, patch
            
            # Create AI service with test vector store
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings:
                mock_embeddings.return_value = Mock()
                with patch('services.ai_service.ChatOllama') as mock_llm:
                    mock_llm.return_value = Mock()
                    
                    vectorstore_path = os.path.join(self.test_dir, "data", "vectorstore")
                    ai_service = AIService(
                        vectorstore_path=vectorstore_path,
                        embedding_model_name="all-MiniLM-L6-v2"
                    )
                    
                    # Create mock vector store
                    mock_vectorstore = Mock()
                    mock_vectorstore.index.ntotal = 1000
                    ai_service.vectorstore = mock_vectorstore
                    
                    # Test backup
                    backup_result = ai_service.backup_vectorstore_to_path(self.backup_dir, "test")
                    
                    if backup_result:
                        # Verify backup files exist
                        backup_path = Path(self.backup_dir) / "test"
                        manifest_path = Path(self.backup_dir) / "vectorstore_backup_manifest_test.json"
                        
                        if backup_path.exists() and manifest_path.exists():
                            self.logger.info("✅ Vector store backup test passed")
                            return True
                        else:
                            self.logger.error("❌ Backup files not found")
                            return False
                    else:
                        self.logger.error("❌ Vector store backup failed")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Vector store backup test failed: {e}")
            return False
    
    def test_vector_store_recovery(self) -> bool:
        """Test vector store recovery functionality."""
        self.logger.info("Testing vector store recovery...")
        
        try:
            sys.path.insert(0, self.project_root)
            from services.ai_service import AIService
            from unittest.mock import Mock, patch
            
            # Create AI service
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings:
                mock_embeddings.return_value = Mock()
                with patch('services.ai_service.ChatOllama') as mock_llm:
                    mock_llm.return_value = Mock()
                    
                    vectorstore_path = os.path.join(self.test_dir, "data", "vectorstore")
                    ai_service = AIService(
                        vectorstore_path=vectorstore_path,
                        embedding_model_name="all-MiniLM-L6-v2"
                    )
                    
                    # Mock load_vectorstore method
                    with patch.object(ai_service, 'load_vectorstore', return_value=True):
                        # Test restore
                        restore_result = ai_service.restore_vectorstore_from_path(self.backup_dir, "test")
                        
                        if restore_result:
                            self.logger.info("✅ Vector store recovery test passed")
                            return True
                        else:
                            self.logger.error("❌ Vector store recovery failed")
                            return False
                            
        except Exception as e:
            self.logger.error(f"❌ Vector store recovery test failed: {e}")
            return False
    
    def test_backup_verification(self) -> bool:
        """Test backup verification functionality."""
        self.logger.info("Testing backup verification...")
        
        try:
            sys.path.insert(0, self.project_root)
            from services.ai_service import AIService
            from unittest.mock import Mock, patch
            
            # Create AI service
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings:
                mock_embeddings.return_value = Mock()
                with patch('services.ai_service.ChatOllama') as mock_llm:
                    mock_llm.return_value = Mock()
                    
                    vectorstore_path = os.path.join(self.test_dir, "data", "vectorstore")
                    ai_service = AIService(
                        vectorstore_path=vectorstore_path,
                        embedding_model_name="all-MiniLM-L6-v2"
                    )
                    
                    # Test verification
                    verification_result = ai_service.verify_vectorstore_backup(self.backup_dir, "test")
                    
                    if verification_result.get("valid", False):
                        self.logger.info("✅ Backup verification test passed")
                        return True
                    else:
                        errors = verification_result.get("errors", [])
                        self.logger.error(f"❌ Backup verification failed: {errors}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Backup verification test failed: {e}")
            return False
    
    def test_database_backup_script(self) -> bool:
        """Test database backup script functionality."""
        self.logger.info("Testing database backup script...")
        
        try:
            # Test backup script import and basic functionality
            backup_script_path = os.path.join(self.project_root, "scripts", "backup.py")
            
            if not os.path.exists(backup_script_path):
                self.logger.error("❌ Backup script not found")
                return False
            
            # Test script execution (dry run)
            success, output = self.run_command([
                sys.executable, backup_script_path, "--help"
            ])
            
            if success and "Wazuh AI Companion Backup Script" in output:
                self.logger.info("✅ Database backup script test passed")
                return True
            else:
                self.logger.error(f"❌ Database backup script test failed: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Database backup script test failed: {e}")
            return False
    
    def test_recovery_script(self) -> bool:
        """Test recovery script functionality."""
        self.logger.info("Testing recovery script...")
        
        try:
            # Test recovery script import and basic functionality
            recovery_script_path = os.path.join(self.project_root, "scripts", "recovery.py")
            
            if not os.path.exists(recovery_script_path):
                self.logger.error("❌ Recovery script not found")
                return False
            
            # Test script execution (dry run)
            success, output = self.run_command([
                sys.executable, recovery_script_path, "--help"
            ])
            
            if success and "Wazuh AI Companion Recovery Script" in output:
                self.logger.info("✅ Recovery script test passed")
                return True
            else:
                self.logger.error(f"❌ Recovery script test failed: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Recovery script test failed: {e}")
            return False
    
    def test_backup_manifest_creation(self) -> bool:
        """Test backup manifest creation and validation."""
        self.logger.info("Testing backup manifest creation...")
        
        try:
            # Create test backup files
            test_files = [
                os.path.join(self.backup_dir, "postgres_test_20240131_120000.sql"),
                os.path.join(self.backup_dir, "vectorstore_20240131_120000.tar.gz")
            ]
            
            for file_path in test_files:
                with open(file_path, 'w') as f:
                    f.write(f"test backup content for {os.path.basename(file_path)}")
            
            # Test manifest creation
            sys.path.insert(0, os.path.join(self.project_root, "scripts"))
            from backup import WazuhBackupManager
            
            backup_manager = WazuhBackupManager()
            backup_manager.backup_dir = self.backup_dir
            backup_manager.logger = logging.getLogger("test")
            
            timestamp = "20240131_120000"
            result = backup_manager.create_backup_manifest(timestamp, test_files, True)
            
            if result:
                # Verify manifest file exists and is valid
                manifest_path = os.path.join(self.backup_dir, f"backup_manifest_{timestamp}.json")
                
                if os.path.exists(manifest_path):
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    if (manifest.get("timestamp") == timestamp and 
                        manifest.get("success") == True and
                        len(manifest.get("backup_files", [])) == 2):
                        self.logger.info("✅ Backup manifest creation test passed")
                        return True
                    else:
                        self.logger.error("❌ Invalid manifest content")
                        return False
                else:
                    self.logger.error("❌ Manifest file not created")
                    return False
            else:
                self.logger.error("❌ Manifest creation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Backup manifest creation test failed: {e}")
            return False
    
    def test_disaster_recovery_scenario(self) -> bool:
        """Test complete disaster recovery scenario."""
        self.logger.info("Testing disaster recovery scenario...")
        
        try:
            # Step 1: Create initial data
            original_vectorstore = os.path.join(self.test_dir, "data", "vectorstore", "disaster_test")
            os.makedirs(original_vectorstore, exist_ok=True)
            
            test_files = {
                "faiss_index.faiss": b"original_faiss_data" * 100,
                "faiss_index.pkl": b"original_pickle_data" * 50,
                "metadata.json": json.dumps({
                    "identifier": "disaster_test",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "document_count": 500
                })
            }
            
            for filename, content in test_files.items():
                file_path = os.path.join(original_vectorstore, filename)
                if isinstance(content, str):
                    with open(file_path, 'w') as f:
                        f.write(content)
                else:
                    with open(file_path, 'wb') as f:
                        f.write(content)
            
            # Step 2: Create backup
            sys.path.insert(0, self.project_root)
            from services.ai_service import AIService
            from unittest.mock import Mock, patch
            
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings:
                mock_embeddings.return_value = Mock()
                with patch('services.ai_service.ChatOllama') as mock_llm:
                    mock_llm.return_value = Mock()
                    
                    vectorstore_path = os.path.join(self.test_dir, "data", "vectorstore")
                    ai_service = AIService(
                        vectorstore_path=vectorstore_path,
                        embedding_model_name="all-MiniLM-L6-v2"
                    )
                    
                    # Create mock vector store
                    mock_vectorstore = Mock()
                    mock_vectorstore.index.ntotal = 500
                    ai_service.vectorstore = mock_vectorstore
                    
                    # Backup
                    backup_result = ai_service.backup_vectorstore_to_path(self.backup_dir, "disaster_test")
                    
                    if not backup_result:
                        self.logger.error("❌ Disaster recovery backup failed")
                        return False
            
            # Step 3: Simulate disaster (delete original data)
            if os.path.exists(original_vectorstore):
                shutil.rmtree(original_vectorstore)
            
            # Verify data is gone
            if os.path.exists(original_vectorstore):
                self.logger.error("❌ Failed to simulate disaster - data still exists")
                return False
            
            # Step 4: Perform recovery
            with patch('services.ai_service.HuggingFaceEmbeddings') as mock_embeddings:
                mock_embeddings.return_value = Mock()
                with patch('services.ai_service.ChatOllama') as mock_llm:
                    mock_llm.return_value = Mock()
                    
                    ai_service_recovery = AIService(
                        vectorstore_path=vectorstore_path,
                        embedding_model_name="all-MiniLM-L6-v2"
                    )
                    
                    # Mock load_vectorstore method
                    with patch.object(ai_service_recovery, 'load_vectorstore', return_value=True):
                        restore_result = ai_service_recovery.restore_vectorstore_from_path(
                            self.backup_dir, "disaster_test"
                        )
                        
                        if not restore_result:
                            self.logger.error("❌ Disaster recovery restore failed")
                            return False
            
            # Step 5: Verify recovery
            restored_path = os.path.join(vectorstore_path, "disaster_test")
            if os.path.exists(restored_path):
                self.logger.info("✅ Disaster recovery scenario test passed")
                return True
            else:
                self.logger.error("❌ Disaster recovery verification failed - restored data not found")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Disaster recovery scenario test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all backup and recovery tests."""
        self.logger.info("Starting comprehensive backup and recovery tests...")
        
        # Test cases
        test_cases = [
            ("Environment Setup", self.create_test_environment),
            ("Vector Store Backup", self.test_vector_store_backup),
            ("Vector Store Recovery", self.test_vector_store_recovery),
            ("Backup Verification", self.test_backup_verification),
            ("Database Backup Script", self.test_database_backup_script),
            ("Recovery Script", self.test_recovery_script),
            ("Backup Manifest Creation", self.test_backup_manifest_creation),
            ("Disaster Recovery Scenario", self.test_disaster_recovery_scenario)
        ]
        
        # Run tests
        for test_name, test_function in test_cases:
            self.test_results["total_tests"] += 1
            
            self.logger.info(f"Running test: {test_name}")
            start_time = time.time()
            
            try:
                success = test_function()
                end_time = time.time()
                duration = end_time - start_time
                
                test_detail = {
                    "name": test_name,
                    "success": success,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                if success:
                    self.test_results["passed_tests"] += 1
                    self.logger.info(f"✅ {test_name} - PASSED ({duration:.2f}s)")
                else:
                    self.test_results["failed_tests"] += 1
                    self.logger.error(f"❌ {test_name} - FAILED ({duration:.2f}s)")
                
                self.test_results["test_details"].append(test_detail)
                
            except Exception as e:
                self.test_results["failed_tests"] += 1
                self.logger.error(f"❌ {test_name} - ERROR: {e}")
                
                test_detail = {
                    "name": test_name,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time,
                    "timestamp": datetime.now().isoformat()
                }
                self.test_results["test_details"].append(test_detail)
        
        # Generate summary
        self.generate_test_report()
        
        return self.test_results
    
    def generate_test_report(self) -> None:
        """Generate a comprehensive test report."""
        report_path = os.path.join(self.test_dir, "backup_recovery_test_report.json")
        
        # Add summary information
        self.test_results.update({
            "test_run_timestamp": datetime.now().isoformat(),
            "test_directory": self.test_dir,
            "backup_directory": self.backup_dir,
            "success_rate": (self.test_results["passed_tests"] / self.test_results["total_tests"] * 100) if self.test_results["total_tests"] > 0 else 0
        })
        
        # Write report
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Print summary
        self.logger.info("\n" + "="*80)
        self.logger.info("BACKUP AND RECOVERY TEST SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Total Tests: {self.test_results['total_tests']}")
        self.logger.info(f"Passed: {self.test_results['passed_tests']}")
        self.logger.info(f"Failed: {self.test_results['failed_tests']}")
        self.logger.info(f"Success Rate: {self.test_results['success_rate']:.1f}%")
        self.logger.info(f"Test Report: {report_path}")
        self.logger.info("="*80)
    
    def cleanup(self) -> None:
        """Clean up test environment."""
        try:
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
            self.logger.info("Test environment cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to clean up test environment: {e}")


def main():
    """Main test script entry point."""
    parser = argparse.ArgumentParser(description="Wazuh AI Companion Backup and Recovery Test Script")
    parser.add_argument(
        "--test-dir", "-d",
        help="Test directory path (temporary directory will be created if not specified)"
    )
    parser.add_argument(
        "--keep-test-data",
        action="store_true",
        help="Keep test data after completion (useful for debugging)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--test-case", "-t",
        choices=[
            "environment", "vector-backup", "vector-recovery", "verification",
            "database-script", "recovery-script", "manifest", "disaster-recovery"
        ],
        help="Run specific test case only"
    )
    
    args = parser.parse_args()
    
    # Create tester
    tester = BackupRecoveryTester(test_dir=args.test_dir)
    
    if args.verbose:
        tester.logger.setLevel(logging.DEBUG)
    
    try:
        # Run tests
        if args.test_case:
            # Run specific test case
            test_methods = {
                "environment": tester.create_test_environment,
                "vector-backup": tester.test_vector_store_backup,
                "vector-recovery": tester.test_vector_store_recovery,
                "verification": tester.test_backup_verification,
                "database-script": tester.test_database_backup_script,
                "recovery-script": tester.test_recovery_script,
                "manifest": tester.test_backup_manifest_creation,
                "disaster-recovery": tester.test_disaster_recovery_scenario
            }
            
            if args.test_case in test_methods:
                # Setup environment first
                if args.test_case != "environment":
                    tester.create_test_environment()
                
                success = test_methods[args.test_case]()
                print(f"Test {args.test_case}: {'PASSED' if success else 'FAILED'}")
                sys.exit(0 if success else 1)
            else:
                print(f"Unknown test case: {args.test_case}")
                sys.exit(1)
        else:
            # Run all tests
            results = tester.run_all_tests()
            
            # Exit with appropriate code
            if results["failed_tests"] == 0:
                print("🎉 All backup and recovery tests passed!")
                sys.exit(0)
            else:
                print(f"❌ {results['failed_tests']} out of {results['total_tests']} tests failed.")
                sys.exit(1)
    
    finally:
        # Cleanup unless requested to keep data
        if not args.keep_test_data:
            tester.cleanup()


if __name__ == "__main__":
    main()