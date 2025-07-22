#!/usr/bin/env python3
"""
Setup and test script for PromptFlow AI platform.
This script initializes the database, populates it with data, and runs comprehensive tests.
"""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logging_config import init_logging

# Initialize logging
init_logging()
logger = logging.getLogger(__name__)


async def check_environment():
    """Check if all required environment variables are set."""
    logger.info("Checking environment variables...")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY', 
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True


async def initialize_database():
    """Initialize the database with schema and data."""
    logger.info("Initializing database...")
    
    try:
        # Import and run the database initialization
        from scripts.init_db import main as init_db_main
        result = await init_db_main()
        
        if result == 0:
            logger.info("✅ Database initialization completed successfully")
            return True
        else:
            logger.error("❌ Database initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        return False


async def populate_rag_embeddings():
    """Populate RAG system with connector embeddings."""
    logger.info("Populating RAG system with connector embeddings...")
    
    try:
        # Set non-interactive mode for the setup script
        os.environ['RAG_SETUP_NON_INTERACTIVE'] = 'true'
        from scripts.setup_rag_database import main as setup_rag_main
        result = await setup_rag_main()
        
        if result == True:
            logger.info("✅ RAG system populated successfully")
            return True
        else:
            logger.error("❌ RAG system population failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG system population error: {e}")
        return False


async def run_integration_tests():
    """Run comprehensive integration tests."""
    logger.info("Running comprehensive integration tests...")
    
    try:
        from test_end_to_end_integration import main as test_main
        result = await test_main()
        
        if result == 0:
            logger.info("✅ All integration tests passed")
            return True
        else:
            logger.error("❌ Some integration tests failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration tests error: {e}")
        return False


async def test_api_endpoints():
    """Test key API endpoints with sample requests."""
    logger.info("Testing API endpoints...")
    
    try:
        import httpx
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        logger.info("✅ Health endpoint working")
        
        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200, f"Status check failed: {response.status_code}"
        logger.info("✅ Status endpoint working")
        
        # Test RAG endpoint
        response = client.post("/api/v1/rag/search", json={
            "query": "send email using gmail",
            "limit": 5
        })
        assert response.status_code == 200, f"RAG search failed: {response.status_code}"
        rag_data = response.json()
        assert len(rag_data.get('connectors', [])) > 0, "No connectors returned from RAG search"
        logger.info(f"✅ RAG endpoint working - found {len(rag_data['connectors'])} connectors")
        
        # Test agent planning endpoint
        response = client.post("/api/v1/agent/plan", json={
            "prompt": "Create a workflow that sends an email when a webhook receives data"
        })
        assert response.status_code == 200, f"Agent planning failed: {response.status_code}"
        plan_data = response.json()
        assert 'workflow' in plan_data, "No workflow in agent response"
        logger.info("✅ Agent planning endpoint working")
        
        logger.info("✅ All API endpoints working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ API endpoint testing failed: {e}")
        return False


async def main():
    """Main setup and test function."""
    logger.info("🚀 Starting PromptFlow AI Platform Setup and Testing")
    logger.info("="*60)
    
    # Step 1: Check environment
    if not await check_environment():
        return 1
    
    # Step 2: Initialize database
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Database Initialization")
    logger.info("="*60)
    if not await initialize_database():
        return 1
    
    # Step 3: Populate RAG system
    logger.info("\n" + "="*60)
    logger.info("STEP 2: RAG System Population")
    logger.info("="*60)
    if not await populate_rag_embeddings():
        return 1
    
    # Step 4: Run integration tests
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Integration Tests")
    logger.info("="*60)
    if not await run_integration_tests():
        return 1
    
    # Step 5: Test API endpoints
    logger.info("\n" + "="*60)
    logger.info("STEP 4: API Endpoint Testing")
    logger.info("="*60)
    if not await test_api_endpoints():
        return 1
    
    # Success!
    logger.info("\n" + "="*60)
    logger.info("🎉 SETUP AND TESTING COMPLETED SUCCESSFULLY! 🎉")
    logger.info("="*60)
    logger.info("The PromptFlow AI platform is fully operational and ready for use!")
    logger.info("\nYou can now:")
    logger.info("1. Start the FastAPI server: uvicorn app.main:app --reload")
    logger.info("2. Test the API endpoints manually")
    logger.info("3. Proceed with frontend development (Task 10)")
    logger.info("4. Use the conversational agent to create workflows")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)