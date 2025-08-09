#!/usr/bin/env python3
"""
Health check script for AI-Enhanced Security Query Interface appliance.
This script monitors only embedded appliance components with no external dependencies.
"""
import sys
import requests
import time
from typing import Dict, Any, List


def check_basic_health() -> Dict[str, Any]:
    """Check basic application health."""
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


def check_detailed_health() -> Dict[str, Any]:
    """Check detailed health including embedded AI status."""
    try:
        response = requests.get(
            "http://localhost:8000/health/detailed",
            timeout=30
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


def check_embedded_ai_status(health_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate embedded AI status from health data."""
    try:
        services = health_data.get("details", {}).get("services", {})
        embedded_ai = services.get("embedded_ai", {})
        
        ai_status = embedded_ai.get("status", "unknown")
        model_count = embedded_ai.get("loaded_models", 0)
        memory_usage = embedded_ai.get("memory_usage", {})
        
        if ai_status in ["healthy", "ready"] and model_count > 0:
            return {
                "status": "healthy",
                "ai_status": ai_status,
                "loaded_models": model_count,
                "memory_usage": memory_usage
            }
        else:
            return {
                "status": "unhealthy",
                "ai_status": ai_status,
                "loaded_models": model_count,
                "memory_usage": memory_usage
            }
    except Exception as e:
        return {
            "status": "error",
            "details": str(e)
        }


def check_appliance_components() -> List[Dict[str, Any]]:
    """Check all embedded appliance components."""
    components = []
    
    # Check basic health
    basic_health = check_basic_health()
    components.append({
        "component": "basic_health",
        "status": basic_health["status"],
        "details": basic_health["details"]
    })
    
    # Check detailed health
    detailed_health = check_detailed_health()
    components.append({
        "component": "detailed_health", 
        "status": detailed_health["status"],
        "details": detailed_health["details"]
    })
    
    # Check embedded AI specifically
    if detailed_health["status"] == "healthy":
        ai_status = check_embedded_ai_status(detailed_health)
        components.append({
            "component": "embedded_ai",
            "status": ai_status["status"],
            "details": ai_status
        })
    
    # Check metrics endpoint
    try:
        response = requests.get("http://localhost:8000/metrics", timeout=10)
        if response.status_code == 200:
            metrics_count = len([line for line in response.text.split('\n') 
                               if line and not line.startswith('#')])
            components.append({
                "component": "metrics",
                "status": "healthy",
                "details": f"{metrics_count} metrics available"
            })
        else:
            components.append({
                "component": "metrics",
                "status": "unhealthy", 
                "details": f"HTTP {response.status_code}"
            })
    except Exception as e:
        components.append({
            "component": "metrics",
            "status": "unhealthy",
            "details": str(e)
        })
    
    return components


def main():
    """Main health check function for embedded AI appliance."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI-Enhanced Security Query Interface Health Check")
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Run detailed health check including embedded AI status"
    )
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=3,
        help="Number of retry attempts"
    )
    parser.add_argument(
        "--delay", 
        type=int,
        default=2,
        help="Delay between retries in seconds"
    )
    
    args = parser.parse_args()
    
    if args.detailed:
        # Run comprehensive appliance health check
        print("🔍 Running comprehensive embedded AI appliance health check...")
        components = check_appliance_components()
        
        healthy_count = sum(1 for c in components if c["status"] == "healthy")
        total_count = len(components)
        
        print(f"\n📊 Health Check Results: {healthy_count}/{total_count} components healthy")
        print("=" * 60)
        
        for component in components:
            status_icon = "✅" if component["status"] == "healthy" else "❌"
            print(f"{status_icon} {component['component']}: {component['status']}")
            if component["status"] != "healthy":
                print(f"   Details: {component['details']}")
        
        if healthy_count == total_count:
            print("\n🎉 All embedded appliance components are healthy!")
            sys.exit(0)
        else:
            print(f"\n⚠️ {total_count - healthy_count} components are unhealthy")
            sys.exit(1)
    else:
        # Run basic health check with retries
        max_retries = args.retries
        retry_delay = args.delay
        
        for attempt in range(max_retries):
            result = check_basic_health()
            
            if result["status"] == "healthy":
                print(f"✅ Embedded AI appliance health check passed: {result['details']}")
                sys.exit(0)
            else:
                print(f"❌ Health check failed (attempt {attempt + 1}/{max_retries}): {result['details']}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        print("🚨 Embedded AI appliance health check failed after all retries")
        sys.exit(1)


if __name__ == "__main__":
    main()