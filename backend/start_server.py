#!/usr/bin/env python3
"""
Start the PromptFlow AI FastAPI server for testing.
"""
import uvicorn
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def main():
    """Start the FastAPI server."""
    print("🚀 Starting PromptFlow AI FastAPI Server...")
    print("="*50)
    print(f"App Name: {settings.APP_NAME}")
    print(f"Debug Mode: {settings.DEBUG}")
    print("="*50)
    print("Server will be available at:")
    print("- Main API: http://localhost:8000")
    print("- Health Check: http://localhost:8000/health")
    print("- System Status: http://localhost:8000/status")
    print("- API Documentation: http://localhost:8000/docs")
    print("- RAG Search: http://localhost:8000/api/v1/rag/search")
    print("- Agent Planning: http://localhost:8000/api/v1/agent/plan")
    print("="*50)
    print("Press Ctrl+C to stop the server")
    print()
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()