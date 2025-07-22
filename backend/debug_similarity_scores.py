#!/usr/bin/env python3
"""
Debug script to check similarity scores for RAG system.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.logging_config import init_logging
from app.services.rag import RAGRetriever

async def debug_similarity_scores():
    """Debug similarity scores for different queries."""
    
    # Initialize logging
    init_logging()
    
    print("🔍 Debugging Similarity Scores")
    print("=" * 50)
    
    # Initialize RAG system (this will initialize the database too)
    print("Initializing RAG system...")
    rag_retriever = RAGRetriever()
    await rag_retriever.initialize()
    
    # Test query
    query = "send email notification"
    print(f"\nTesting query: '{query}'")
    
    # Generate embedding for the query
    query_embedding = await rag_retriever.embedding_service.generate_embedding(query)
    print(f"Query embedding generated: {len(query_embedding)} dimensions")
    
    # Get all connectors with embeddings
    from app.core.database import get_database
    db = await get_database()
    result = db.table("connectors").select("*").eq("is_active", True).not_.is_("embedding", None).execute()
    
    print(f"\nFound {len(result.data)} connectors with embeddings")
    
    # Calculate similarity scores for all connectors
    connectors_with_scores = []
    for row in result.data:
        connector_embedding = row.get("embedding")
        if connector_embedding:
            similarity_score = rag_retriever._calculate_cosine_similarity(query_embedding, connector_embedding)
            connectors_with_scores.append((row['name'], row['description'][:60], similarity_score))
    
    # Sort by similarity score
    connectors_with_scores.sort(key=lambda x: x[2], reverse=True)
    
    print(f"\nSimilarity scores for query '{query}':")
    print("-" * 80)
    for name, desc, score in connectors_with_scores:
        print(f"{score:.4f} - {name}: {desc}...")
    
    print(f"\nConnectors with score >= 0.5:")
    high_score_connectors = [c for c in connectors_with_scores if c[2] >= 0.5]
    for name, desc, score in high_score_connectors:
        print(f"{score:.4f} - {name}: {desc}...")
    
    print(f"\nConnectors with score >= 0.3:")
    medium_score_connectors = [c for c in connectors_with_scores if c[2] >= 0.3]
    for name, desc, score in medium_score_connectors:
        print(f"{score:.4f} - {name}: {desc}...")

if __name__ == "__main__":
    asyncio.run(debug_similarity_scores())