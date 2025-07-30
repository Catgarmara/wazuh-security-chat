#!/usr/bin/env python3
"""
Production Wazuh AI Companion startup script.
"""
import uvicorn
import argparse
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import get_settings
from app.main import app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Wazuh AI Companion")
    parser.add_argument(
        "--host", 
        type=str, 
        help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        help="Port to bind to (overrides config)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1, 
        help="Number of worker processes"
    )
    
    args = parser.parse_args()
    settings = get_settings()
    
    # Use command line args or fall back to settings
    host = args.host or settings.host
    port = args.port or settings.port
    
    print(f"🚀 Starting {settings.app_name} v{settings.version}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"🔧 Environment: {settings.environment}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()