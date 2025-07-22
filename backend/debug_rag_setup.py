#!/usr/bin/env python3
"""Debug script to test RAG system in setup context."""

import asyncio
from app.core.logging_config import init_logging
from app.services.rag import RAGRetriever

async def debug_rag():
    """Debug RAG system setup."""
    init_logging()
    
    print("🔍 Debugging RAG System")
    print("=" * 50)
    
    # Initialize RAG system
    rag_retriever = RAGRetriever()
    await rag_retriever.initialize()
    
    # Test a simple query
    print("Testing query: 'send email notification' with lower threshold")
    connectors = await rag_retriever.retrieve_connectors("send email notification", limit=5, similarity_threshold=0.3)
    
    print(f"Found {len(connectors)} connectors:")
    for connector in connectors:
        print(f"  - {connector.name}: {connector.description[:100]}...")

if __name__ == "__main__":
    asyncio.run(debug_rag())