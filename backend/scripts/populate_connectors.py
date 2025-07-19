#!/usr/bin/env python3
"""
Script to populate the database with sample connector metadata.
This script initializes the RAG system with sample connectors for testing.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.rag import rag_retriever
from app.data.sample_connectors import SAMPLE_CONNECTORS
from app.core.database import init_database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def populate_connectors():
    """Populate the database with sample connector metadata."""
    try:
        # Initialize database and RAG system
        logger.info("Initializing database and RAG system...")
        await init_database()
        await rag_retriever.initialize()
        
        # Store sample connectors
        logger.info(f"Storing {len(SAMPLE_CONNECTORS)} sample connectors...")
        await rag_retriever.metadata_manager.store_connectors_batch(SAMPLE_CONNECTORS)
        
        logger.info("Successfully populated database with sample connectors!")
        
        # Test retrieval
        logger.info("Testing connector retrieval...")
        test_queries = [
            "send email",
            "read spreadsheet data",
            "make HTTP request",
            "AI text generation",
            "schedule workflow"
        ]
        
        for query in test_queries:
            connectors = await rag_retriever.retrieve_connectors(query, limit=3)
            logger.info(f"Query: '{query}' -> Found {len(connectors)} connectors")
            for conn in connectors:
                logger.info(f"  - {conn.name}: {conn.description[:100]}...")
        
    except Exception as e:
        logger.error(f"Failed to populate connectors: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(populate_connectors())