"""
FastAPI application entry point for PromptFlow AI platform.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_database, close_database
from app.api.auth import router as auth_router
from app.api.rag import router as rag_router
from app.services.rag import init_rag_system
from app.connectors.core.register import register_core_connectors
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PromptFlow AI",
        description="No-code AI automation platform",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(rag_router, prefix="/api/v1")

    return app

app = create_application()

@app.get("/")
async def root():
    return {"message": "PromptFlow AI Platform"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        logger.info("Starting PromptFlow AI application...")
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize RAG system
        await init_rag_system()
        logger.info("RAG system initialized successfully")
        
        # Register core connectors
        registration_result = register_core_connectors()
        logger.info(f"Core connectors registered: {registration_result['registered']}/{registration_result['total']}")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    try:
        logger.info("Shutting down PromptFlow AI application...")
        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")