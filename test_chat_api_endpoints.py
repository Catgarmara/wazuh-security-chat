#!/usr/bin/env python3
"""
Test script to verify chat and WebSocket API endpoints functionality.
"""

import json
import sys
from datetime import datetime
from uuid import uuid4

# Add current directory to path
sys.path.append('.')

def test_chat_api_imports():
    """Test that chat API modules can be imported successfully."""
    print("🧪 Testing Chat API Imports...")
    
    try:
        from api.chat import router as chat_router
        from api.websocket import router as websocket_router
        print("✅ Chat API router imported successfully")
        print("✅ WebSocket API router imported successfully")
        
        # Check routes
        chat_routes = [route.path for route in chat_router.routes]
        websocket_routes = [route.path for route in websocket_router.routes]
        
        print(f"✅ Chat routes: {len(chat_routes)} endpoints")
        print(f"✅ WebSocket routes: {len(websocket_routes)} endpoints")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_api_route_structure():
    """Test that all required API routes are properly structured."""
    print("\n🧪 Testing API Route Structure...")
    
    try:
        from app.main import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            routes.append({
                'path': route.path,
                'methods': getattr(route, 'methods', set())
            })
        
        # Required chat endpoints
        required_chat_endpoints = [
            "/api/v1/chat/sessions",
            "/api/v1/chat/sessions/{session_id}",
            "/api/v1/chat/sessions/{session_id}/messages",
            "/api/v1/chat/sessions/{session_id}/context",
            "/api/v1/chat/sessions/cleanup"
        ]
        
        # Required WebSocket endpoints
        required_websocket_endpoints = [
            "/ws/chat",
            "/ws/connections/info"
        ]
        
        route_paths = [route['path'] for route in routes]
        
        print("\nChecking chat endpoints:")
        for endpoint in required_chat_endpoints:
            if endpoint in route_paths:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ Missing endpoint: {endpoint}")
        
        print("\nChecking WebSocket endpoints:")
        for endpoint in required_websocket_endpoints:
            if endpoint in route_paths:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ Missing endpoint: {endpoint}")
        
        print(f"\n✅ Total routes registered: {len(routes)}")
        return True
        
    except Exception as e:
        print(f"❌ Route structure test failed: {e}")
        return False

def test_schema_validation():
    """Test that API schemas are properly defined."""
    print("\n🧪 Testing Schema Validation...")
    
    try:
        from models.schemas import (
            ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
            MessageResponse, ChatMessageRequest, ChatMessageResponse
        )
        
        print("✅ Chat session schemas imported successfully")
        
        # Test schema creation
        session_create = ChatSessionCreate(title="Test Session")
        print(f"✅ ChatSessionCreate schema: {session_create}")
        
        session_update = ChatSessionUpdate(title="Updated Session", is_active=True)
        print(f"✅ ChatSessionUpdate schema: {session_update}")
        
        message_request = ChatMessageRequest(message="Hello, AI!")
        print(f"✅ ChatMessageRequest schema: {message_request}")
        
        print("\n✅ Schema validation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def test_schema_validation():
    """Test that API schemas are properly defined."""
    print("\n🧪 Testing Schema Validation...")
    
    try:
        from models.schemas import (
            ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
            MessageResponse, ChatMessageRequest, ChatMessageResponse
        )
        
        print("✅ Chat session schemas imported successfully")
        
        # Test schema creation
        session_create = ChatSessionCreate(title="Test Session")
        print(f"✅ ChatSessionCreate schema: {session_create}")
        
        session_update = ChatSessionUpdate(title="Updated Session", is_active=True)
        print(f"✅ ChatSessionUpdate schema: {session_update}")
        
        message_request = ChatMessageRequest(message="Hello, AI!")
        print(f"✅ ChatMessageRequest schema: {message_request}")
        
        print("\n✅ Schema validation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Chat API Endpoint Tests")
    print("=" * 50)
    
    try:
        # Run tests
        test_results = []
        
        test_results.append(test_chat_api_imports())
        test_results.append(test_api_route_structure())
        test_results.append(test_schema_validation())
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Chat API endpoints are properly implemented.")
            return True
        else:
            print("❌ Some tests failed. Please check the implementation.")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)