#!/usr/bin/env python3
"""
Script to set up the database for the RAG system.
This script initializes the database schema and populates it with sample connectors.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, get_database
from app.services.rag import rag_retriever
from app.data.sample_connectors import SAMPLE_CONNECTORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database_schema():
    """Set up the database schema if not already done."""
    logger.info("Setting up database schema...")
    
    try:
        db = await get_database()
        
        # Check if connectors table exists
        result = db.table("connectors").select("count", count="exact").execute()
        logger.info(f"Connectors table exists with {result.count} records")
        
    except Exception as e:
        logger.error(f"Database schema setup failed: {e}")
        logger.info("Please run the database initialization script first:")
        logger.info("python scripts/init_db.py")
        raise


async def populate_sample_connectors(force_replace: bool = False):
    """Populate the database with sample connectors and their embeddings."""
    logger.info("Populating sample connectors...")
    
    try:
        # Initialize RAG system
        await rag_retriever.initialize()
        
        # Check if connectors already exist
        db = await get_database()
        result = db.table("connectors").select("count", count="exact").execute()
        
        if result.count > 0:
            logger.info(f"Database already has {result.count} connectors")
            # Check for non-interactive mode via environment variable
            non_interactive = os.getenv('RAG_SETUP_NON_INTERACTIVE', 'false').lower() == 'true'
            if not force_replace and not non_interactive:
                user_input = input("Do you want to replace them? (y/N): ")
                if user_input.lower() != 'y':
                    logger.info("Skipping connector population")
                    return
            elif non_interactive:
                logger.info("Non-interactive mode: skipping connector population")
                return
            else:
                logger.info("Force replacing existing connectors")
            
            # Clear existing connectors
            db.table("connectors").delete().neq("name", "").execute()
            logger.info("Cleared existing connectors")
        
        # Store sample connectors with embeddings
        logger.info(f"Storing {len(SAMPLE_CONNECTORS)} sample connectors...")
        await rag_retriever.metadata_manager.store_connectors_batch(SAMPLE_CONNECTORS)
        
        logger.info("✅ Sample connectors populated successfully!")
        
    except Exception as e:
        logger.error(f"Failed to populate connectors: {e}")
        if "AZURE_OPENAI" in str(e) or "openai" in str(e).lower():
            logger.error("❌ Azure OpenAI configuration is missing or invalid")
            logger.error("Please configure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your .env file")
        raise


async def test_rag_system():
    """Test the RAG system with sample queries."""
    logger.info("Testing RAG system...")
    
    try:
        test_queries = [
            "send email notification",
            "read spreadsheet data", 
            "make HTTP request",
            "AI text generation",
            "schedule workflow"
        ]
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            connectors = await rag_retriever.retrieve_connectors(query, limit=3, similarity_threshold=0.3)
            
            if connectors:
                logger.info(f"  Found {len(connectors)} relevant connectors:")
                for conn in connectors:
                    logger.info(f"    - {conn.name}: {conn.description[:60]}...")
            else:
                logger.warning(f"  No connectors found for query: {query}")
        
        logger.info("✅ RAG system test completed!")
        
    except Exception as e:
        logger.error(f"RAG system test failed: {e}")
        raise


async def main():
    """Main setup function."""
    logger.info("🚀 Setting up RAG System Database")
    logger.info("=" * 50)
    
    try:
        # Initialize database connection
        await init_database()
        
        # Set up schema
        await setup_database_schema()
        
        # Populate connectors
        await populate_sample_connectors()
        
        # Test the system
        await test_rag_system()
        
        logger.info("=" * 50)
        logger.info("🎉 RAG System setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start the FastAPI server: uvicorn app.main:app --reload")
        logger.info("2. Test the RAG endpoints")
        logger.info("3. Integrate with the conversational agent")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)