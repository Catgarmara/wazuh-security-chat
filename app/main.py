"""
Main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from core.container import get_container
from core.exceptions import WazuhChatException, EXCEPTION_STATUS_MAP


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    container = get_container()
    
    print(f"🚀 Starting {settings.app_name} v{settings.version}")
    print(f"🌍 Environment: {settings.environment}")
    print(f"🔧 Debug mode: {settings.debug}")
    
    # TODO: Initialize services, database connections, etc.
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application")
    container.clear_scoped()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handlers
    @app.exception_handler(WazuhChatException)
    async def wazuh_exception_handler(request, exc: WazuhChatException):
        from fastapi import HTTPException
        status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
        raise HTTPException(
            status_code=status_code,
            detail=exc.to_dict()
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment
        }
    
    # TODO: Include API routers
    # app.include_router(auth_router, prefix=settings.api_prefix)
    # app.include_router(chat_router, prefix=settings.api_prefix)
    # etc.
    
    return app


# Create app instance
app = create_app()