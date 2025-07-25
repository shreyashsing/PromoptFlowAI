#!/usr/bin/env python3
"""
Test script to check connector names in RAG system vs registry.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag import RAGRetriever
from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors

async def test_connector_names():
    """Test connector names in RAG vs registry."""
    print("🔍 Testing Connector Names")
    print("=" * 40)
    
    # Register core connectors
    print("1. Registering core connectors...")
    register_core_connectors()
    
    # Get registry connectors
    registry_connectors = connector_registry.list_connectors()
    print(f"Registry connectors: {registry_connectors}")
    
    # Initialize RAG system
    print("2. Initializing RAG system...")
    rag = RAGRetriever()
    await rag.initialize()
    
    # Get RAG connectors
    print("3. Retrieving connectors from RAG...")
    rag_connectors = await rag.retrieve_connectors("search email summarize", limit=20)
    rag_names = [c.name for c in rag_connectors]
    print(f"RAG connectors: {rag_names}")
    
    # Compare
    print("4. Comparison:")
    print(f"Registry has {len(registry_connectors)} connectors")
    print(f"RAG has {len(rag_names)} connectors")
    
    missing_in_rag = set(registry_connectors) - set(rag_names)
    missing_in_registry = set(rag_names) - set(registry_connectors)
    
    if missing_in_rag:
        print(f"❌ Missing in RAG: {missing_in_rag}")
    if missing_in_registry:
        print(f"❌ Missing in Registry: {missing_in_registry}")
    
    if not missing_in_rag and not missing_in_registry:
        print("✅ All connectors match!")
    
    # Show detailed connector info
    print("\n5. Detailed connector info:")
    for connector in rag_connectors:
        print(f"  - {connector.name}: {connector.description[:60]}...")

if __name__ == "__main__":
    asyncio.run(test_connector_names())