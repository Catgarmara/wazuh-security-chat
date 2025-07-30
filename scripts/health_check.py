#!/usr/bin/env python3
"""
Health check script for Docker containers.
"""
import sys
import requests
import time
from typing import Dict, Any


def check_health() -> Dict[str, Any]:
    """Check application health."""
    try:
        response = requests.get(
            "http://localhost:8000/health",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "healthy",
                "details": data
            }
        else:
            return {
                "status": "unhealthy",
                "details": f"HTTP {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "unhealthy",
            "details": str(e)
        }


def main():
    """Main health check function."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        result = check_health()
        
        if result["status"] == "healthy":
            print(f"✅ Health check passed: {result['details']}")
            sys.exit(0)
        else:
            print(f"❌ Health check failed (attempt {attempt + 1}/{max_retries}): {result['details']}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    print("🚨 Health check failed after all retries")
    sys.exit(1)


if __name__ == "__main__":
    main()