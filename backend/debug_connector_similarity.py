#!/usr/bin/env python3
"""
Debug script to test connector similarity matching for the specific workflow request.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag import RAGRetriever
from app.core.database import get_database

async def debug_connector_similarity():
    """Debug connector similarity matching."""
    
    # Your specific workflow request
    query = "Build me a workflow that finds the top 5 recent blogs posted by Google using Perplexity, summarizes all 5 into one combined summary, and sends the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body."
    
    print(f"🔍 Testing query: {query[:100]}...")
    print("=" * 80)
    
    try:
        # Initialize RAG retriever
        rag_retriever = RAGRetriever()
        await rag_retriever.initialize()
        
        # Get database connection
        db = await get_database()
        
        # Get all active connectors with embeddings
        result = db.table("connectors").select("name, category, description, embedding").eq("is_active", True).not_.is_("embedding", None).execute()
        
        if not result.data:
            print("❌ No connectors found in database")
            return
        
        print(f"📊 Found {len(result.data)} connectors with embeddings")
        print()
        
        # Generate embedding for the query
        query_embedding = await rag_retriever.embedding_service.generate_embedding(query)
        print(f"✅ Generated query embedding (length: {len(query_embedding)})")
        print()
        
        # Calculate similarity for each connector
        similarities = []
        for row in result.data:
            connector_embedding = row.get("embedding")
            if connector_embedding:
                similarity_score = rag_retriever._calculate_cosine_similarity(query_embedding, connector_embedding)
                similarities.append({
                    'name': row['name'],
                    'category': row['category'],
                    'description': row['description'][:100] + "..." if len(row['description']) > 100 else row['description'],
                    'similarity': similarity_score
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        print("🎯 Similarity Scores:")
        print("-" * 80)
        for i, conn in enumerate(similarities, 1):
            status = "✅ MATCH" if conn['similarity'] >= 0.3 else "❌ NO MATCH"
            print(f"{i:2d}. {conn['name']:20} ({conn['category']:15}) | {conn['similarity']:.4f} | {status}")
            print(f"    {conn['description']}")
            print()
        
        # Show which connectors would be returned with different thresholds
        print("🔧 Threshold Analysis:")
        print("-" * 80)
        for threshold in [0.2, 0.3, 0.4, 0.5]:
            matches = [c for c in similarities if c['similarity'] >= threshold]
            print(f"Threshold {threshold}: {len(matches)} connectors would match")
            if matches:
                print(f"  Top matches: {', '.join([c['name'] for c in matches[:3]])}")
        
        print()
        print("🎯 Expected connectors for your workflow:")
        expected = ['perplexity_search', 'gmail_connector', 'text_summarizer']
        for exp in expected:
            found = next((c for c in similarities if c['name'] == exp), None)
            if found:
                status = "✅ FOUND" if found['similarity'] >= 0.3 else f"⚠️  LOW SCORE ({found['similarity']:.4f})"
                print(f"  {exp}: {status}")
            else:
                print(f"  {exp}: ❌ NOT FOUND")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_connector_similarity())