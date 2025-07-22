#!/usr/bin/env python3
"""
Test script to verify vector similarity search functionality.
"""
import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.logging_config import init_logging
from app.core.database import init_database
from app.services.rag import RAGRetriever, init_rag_system

# Initialize logging
init_logging()
logger = logging.getLogger(__name__)


async def test_vector_similarity():
    """Test vector similarity search functionality."""
    try:
        logger.info("🧪 Testing Vector Similarity Search")
        logger.info("=" * 50)
        
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        
        # Initialize RAG system
        logger.info("Initializing RAG system...")
        await init_rag_system()
        
        # Create RAG retriever
        rag_retriever = RAGRetriever()
        await rag_retriever.initialize()
        
        # Test queries
        test_queries = [
            "send email notification",
            "make HTTP request",
            "read spreadsheet data",
            "AI text generation",
            "schedule workflow"
        ]
        
        logger.info("Testing vector similarity search...")
        
        for query in test_queries:
            logger.info(f"\n🔍 Testing query: '{query}'")
            try:
                connectors = await rag_retriever.retrieve_connectors(
                    query=query,
                    limit=5,
                    similarity_threshold=0.1  # Lower threshold for testing
                )
                
                if connectors:
                    logger.info(f"✅ Found {len(connectors)} connectors:")
                    for connector in connectors:
                        logger.info(f"  - {connector.name}: {connector.description[:100]}...")
                else:
                    logger.warning(f"⚠️  No connectors found for query: {query}")
                    
            except Exception as e:
                logger.error(f"❌ Query failed: {e}")
        
        logger.info("\n" + "=" * 50)
        logger.info("✅ Vector similarity test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_vector_similarity())