"""
Main application entry point.
"""
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from core.container import get_container
from core.database import init_database, shutdown_database
from core.exceptions import WazuhChatException, EXCEPTION_STATUS_MAP
from core.metrics import metrics, metrics_endpoint, setup_metrics_middleware

# Import API routers
from api.auth import router as auth_router
from api.chat import router as chat_router
from api.logs import router as logs_router
from api.websocket import router as websocket_router
from api.audit import router as audit_router
from api.analytics import router as analytics_router
from api.ai import router as ai_router

from api.huggingface import router as huggingface_router
from api.siem import router as siem_router
from api.siem_websocket import router as siem_websocket_router
from api.alert_management import router as alert_management_router
from api.threat_correlation import router as threat_correlation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    container = get_container()
    
    print(f"🚀 Starting {settings.app_name} v{settings.version}")
    print(f"🌍 Environment: {settings.environment}")
    print(f"🔧 Debug mode: {settings.debug}")
    
    # Initialize database
    init_database()
    print("✅ Database initialized")
    
    # Initialize metrics
    metrics.set_app_info(
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment
    )
    print("📊 Metrics initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application")
    shutdown_database()
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
    
    # Add audit logging middleware
    from core.audit_middleware import setup_audit_middleware
    setup_audit_middleware(app)
    
    # Add security middleware
    from core.middleware import setup_middleware
    setup_middleware(app)
    
    # Add metrics middleware
    setup_metrics_middleware(app)
    
    # Add exception handlers
    @app.exception_handler(WazuhChatException)
    async def wazuh_exception_handler(request, exc: WazuhChatException):
        from fastapi import HTTPException
        status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
        raise HTTPException(
            status_code=status_code,
            detail=exc.to_dict()
        )
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with all service statuses."""
        from core.health import get_application_health
        return await get_application_health(use_cache=False)
    
    @app.get("/health/{service_name}")
    async def service_health_check(service_name: str):
        """Health check for a specific service."""
        from core.health import get_service_health
        result = await get_service_health(service_name)
        if result is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        return result
    
    # Metrics endpoint
    @app.get("/metrics")
    async def get_metrics():
        return await metrics_endpoint()
    
    # Include API routers
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)
    app.include_router(logs_router, prefix=settings.api_prefix)
    app.include_router(audit_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)
    app.include_router(ai_router, prefix=settings.api_prefix)
    app.include_router(huggingface_router, prefix=settings.api_prefix)
    app.include_router(siem_router, prefix=settings.api_prefix)
    app.include_router(alert_management_router, prefix=settings.api_prefix)
    app.include_router(threat_correlation_router, prefix=settings.api_prefix)
    app.include_router(websocket_router)  # WebSocket routes don't need API prefix
    app.include_router(siem_websocket_router)  # SIEM WebSocket routes
    
    return app


# Create app instance
app = create_app()