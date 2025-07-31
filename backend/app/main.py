"""
FastAPI application entry point for PromptFlow AI platform.
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import init_database, close_database
from app.api.auth import router as auth_router
from app.api.rag import router as rag_router
from app.api.agent import router as agent_router
from app.api.react_agent import router as react_agent_router
from app.api.workflows import router as workflows_router
from app.api.workflows_react import router as workflows_react_router
from app.api.executions import router as executions_router
from app.api.triggers import router as triggers_router
from app.api.monitoring import router as monitoring_router
from app.services.rag import init_rag_system
# Removed old conversational agent - now using True ReAct Agent
from app.services.trigger_system import get_trigger_system
from app.services.monitoring_service import monitoring_service
from app.connectors.core.register import register_core_connectors

# Import new error handling and logging systems
from app.core.logging_config import init_logging, get_logger
from app.core.error_handler import global_error_handler, handle_api_error
from app.core.monitoring import health_checker, get_system_status, record_request_time
from app.core.exceptions import PromptFlowException
from app.core.middleware import ErrorHandlingMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware

# Initialize logging
init_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    try:
        logger.info("Starting PromptFlow AI application...")
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize RAG system
        await init_rag_system()
        logger.info("RAG system initialized successfully")
        
        # True ReAct Agent initializes on-demand
        logger.info("True ReAct Agent system ready")
        
        # Register core connectors
        registration_result = register_core_connectors()
        logger.info(f"Core connectors registered: {registration_result['registered']}/{registration_result['total']}")
        
        # Initialize trigger system
        trigger_system = await get_trigger_system()
        logger.info("Trigger system initialized successfully")
        
        # Initialize monitoring service
        await monitoring_service.start()
        logger.info("Monitoring service initialized successfully")
        
        yield
        
        # Shutdown monitoring service
        await monitoring_service.stop()
        logger.info("Monitoring service stopped")
        
        # Shutdown trigger system
        await trigger_system.stop()
        logger.info("Trigger system stopped")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown
        try:
            logger.info("Shutting down PromptFlow AI application...")
            await close_database()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PromptFlow AI",
        description="No-code AI automation platform",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add comprehensive middleware stack
    # Security headers (first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Error handling middleware (catches all unhandled exceptions)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware, log_level="INFO")
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Note: Global exception handling is now handled by ErrorHandlingMiddleware

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(rag_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(react_agent_router, prefix="/api/v1")
    app.include_router(workflows_router, prefix="/api/v1")
    app.include_router(workflows_react_router, prefix="/api/v1")
    app.include_router(executions_router, prefix="/api/v1")
    app.include_router(triggers_router, prefix="/api/v1")
    app.include_router(monitoring_router, prefix="/api/v1")

    return app

app = create_application()

@app.get("/")
async def root():
    return {"message": "PromptFlow AI Platform"}

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_status = await health_checker.check_health()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/status")
async def system_status():
    """Detailed system status endpoint."""
    try:
        return await get_system_status()
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {
            "error": "Failed to get system status",
            "message": str(e),
            "timestamp": time.time()
        }