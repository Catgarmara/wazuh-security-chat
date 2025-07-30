#!/usr/bin/env python3
"""
Test script for log management API endpoints.

This script tests the log management API endpoints to ensure they work correctly
with proper authentication and return expected responses.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient

from app.main import app
from core.config import get_settings


class LogAPITester:
    """Test class for log management API endpoints."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.settings = get_settings()
        self.base_url = f"{self.settings.api_prefix}/logs"
        self.auth_token = None
        
    def authenticate(self) -> bool:
        """Authenticate and get access token."""
        try:
            # Try to login with test credentials
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = self.client.post(
                f"{self.settings.api_prefix}/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_headers(self) -> dict:
        """Get headers with authentication token."""
        if not self.auth_token:
            raise ValueError("Not authenticated")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    def test_health_check(self) -> bool:
        """Test log health check endpoint."""
        try:
            print("\n🔍 Testing log health check...")
            
            response = self.client.get(
                f"{self.base_url}/health",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check successful")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_log_statistics(self) -> bool:
        """Test log statistics endpoint."""
        try:
            print("\n📊 Testing log statistics...")
            
            response = self.client.get(
                f"{self.base_url}/stats?days=1&include_metadata=true",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Statistics retrieved successfully")
                print(f"   Total logs: {data.get('total_logs', 0)}")
                print(f"   Date range: {data.get('date_range', 'N/A')}")
                print(f"   Processing time: {data.get('processing_time', 0):.3f}s")
                
                # Check for metadata
                if data.get('agents'):
                    print(f"   Agents found: {len(data['agents'])}")
                if data.get('rules'):
                    print(f"   Rules found: {len(data['rules'])}")
                
                return True
            else:
                print(f"❌ Statistics failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Statistics error: {e}")
            return False
    
    def test_log_search(self) -> bool:
        """Test log search endpoint."""
        try:
            print("\n🔍 Testing log search...")
            
            # Test basic search
            response = self.client.get(
                f"{self.base_url}/search?days=1&limit=10",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Search successful")
                print(f"   Total results: {data.get('total', 0)}")
                print(f"   Results returned: {len(data.get('results', []))}")
                print(f"   Current page: {data.get('current_page', 1)}")
                
                # Test search with query
                response2 = self.client.get(
                    f"{self.base_url}/search?days=1&query=error&limit=5",
                    headers=self.get_headers()
                )
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    print(f"   Search with 'error' query: {data2.get('total', 0)} results")
                
                return True
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return False
    
    def test_log_sources(self) -> bool:
        """Test log sources endpoint."""
        try:
            print("\n📂 Testing log sources...")
            
            response = self.client.get(
                f"{self.base_url}/sources?days=1",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Sources retrieved successfully")
                print(f"   Total sources: {data.get('total_sources', 0)}")
                
                sources = data.get('sources', {})
                if sources:
                    print("   Top sources:")
                    for source, count in list(sources.items())[:5]:
                        print(f"     - {source}: {count}")
                
                return True
            else:
                print(f"❌ Sources failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Sources error: {e}")
            return False
    
    def test_log_agents(self) -> bool:
        """Test log agents endpoint."""
        try:
            print("\n🤖 Testing log agents...")
            
            response = self.client.get(
                f"{self.base_url}/agents?days=1",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Agents retrieved successfully")
                print(f"   Total agents: {data.get('total_agents', 0)}")
                
                agents = data.get('agents', {})
                if agents:
                    print("   Top agents:")
                    for agent, count in list(agents.items())[:5]:
                        print(f"     - {agent}: {count}")
                
                return True
            else:
                print(f"❌ Agents failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Agents error: {e}")
            return False
    
    def test_log_rules(self) -> bool:
        """Test log rules endpoint."""
        try:
            print("\n📋 Testing log rules...")
            
            response = self.client.get(
                f"{self.base_url}/rules?days=1&limit=10",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Rules retrieved successfully")
                print(f"   Total unique rules: {data.get('total_unique_rules', 0)}")
                print(f"   Showing top: {data.get('showing_top', 0)}")
                
                rules = data.get('rules', {})
                if rules:
                    print("   Top rules:")
                    for rule_id, count in list(rules.items())[:5]:
                        print(f"     - {rule_id}: {count}")
                
                return True
            else:
                print(f"❌ Rules failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Rules error: {e}")
            return False
    
    def test_log_configuration(self) -> bool:
        """Test log configuration endpoints."""
        try:
            print("\n⚙️ Testing log configuration...")
            
            # Test get configuration
            response = self.client.get(
                f"{self.base_url}/config",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Configuration retrieved successfully")
                print(f"   Log base path: {data.get('log_base_path')}")
                print(f"   Supported formats: {data.get('supported_formats')}")
                print(f"   Max days range: {data.get('max_days_range')}")
                
                return True
            else:
                print(f"❌ Configuration failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            return False
    
    def test_log_reload(self) -> bool:
        """Test log reload endpoint (admin only)."""
        try:
            print("\n🔄 Testing log reload...")
            
            response = self.client.post(
                f"{self.base_url}/reload?days=1&force=false",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Reload initiated successfully")
                print(f"   Status: {data.get('status')}")
                print(f"   Days: {data.get('days')}")
                print(f"   Initiated by: {data.get('initiated_by')}")
                return True
            elif response.status_code == 403:
                print(f"⚠️ Reload requires admin privileges (403)")
                return True  # Expected for non-admin users
            else:
                print(f"❌ Reload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Reload error: {e}")
            return False
    
    def test_date_range_reload(self) -> bool:
        """Test date range reload endpoint (admin only)."""
        try:
            print("\n📅 Testing date range reload...")
            
            # Create date range for yesterday
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            date_range_data = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            response = self.client.post(
                f"{self.base_url}/reload/date-range",
                json=date_range_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Date range reload initiated successfully")
                print(f"   Status: {data.get('status')}")
                print(f"   Days: {data.get('days')}")
                print(f"   Start date: {data.get('start_date')}")
                print(f"   End date: {data.get('end_date')}")
                return True
            elif response.status_code == 403:
                print(f"⚠️ Date range reload requires admin privileges (403)")
                return True  # Expected for non-admin users
            else:
                print(f"❌ Date range reload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Date range reload error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all log API tests."""
        print("🚀 Starting Log Management API Tests")
        print("=" * 50)
        
        if not self.authenticate():
            return False
        
        tests = [
            self.test_health_check,
            self.test_log_statistics,
            self.test_log_search,
            self.test_log_sources,
            self.test_log_agents,
            self.test_log_rules,
            self.test_log_configuration,
            self.test_log_reload,
            self.test_date_range_reload
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️ Some tests failed")
            return False


def main():
    """Main test function."""
    tester = LogAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Log Management API implementation is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Log Management API implementation has issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()