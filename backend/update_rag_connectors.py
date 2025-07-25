#!/usr/bin/env python3
"""
Update RAG database with actual registered connectors.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag import RAGRetriever
from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors
from app.core.database import init_database

async def update_rag_connectors():
    """Update RAG database with actual registered connectors."""
    print("🔄 Updating RAG Database with Registered Connectors")
    print("=" * 50)
    
    try:
        # Initialize database
        print("1. Initializing database...")
        await init_database()
        
        # Register core connectors
        print("2. Registering core connectors...")
        register_core_connectors()
        
        # Get registered connectors
        registry_connectors = connector_registry.list_connectors()
        print(f"Found {len(registry_connectors)} registered connectors: {registry_connectors}")
        
        # Initialize RAG system
        print("3. Initializing RAG system...")
        rag = RAGRetriever()
        await rag.initialize()
        
        # Clear existing connectors
        print("4. Clearing existing connector data...")
        from app.core.database import get_supabase_client
        supabase = get_supabase_client()
        
        # Delete existing connectors
        delete_result = supabase.table("connectors").delete().gt("usage_count", -1).execute()
        print(f"Deleted {len(delete_result.data) if delete_result.data else 0} existing connectors")
        
        # Add registered connectors to RAG
        print("5. Adding registered connectors to RAG...")
        added_count = 0
        
        for connector_name in registry_connectors:
            try:
                # Get connector metadata from registry
                metadata = connector_registry.get_metadata(connector_name)
                
                # Insert into database
                connector_data = {
                    "name": metadata.name,
                    "display_name": metadata.name.replace('_', ' ').title(),
                    "description": metadata.description,
                    "category": metadata.category,
                    "schema": metadata.parameter_schema,
                    "auth_type": metadata.auth_type.value,
                    "usage_count": 0
                }
                
                result = supabase.table("connectors").insert(connector_data).execute()
                if result.data:
                    added_count += 1
                    print(f"  ✅ Added: {metadata.name}")
                else:
                    print(f"  ❌ Failed to add: {metadata.name}")
                    
            except Exception as e:
                print(f"  ❌ Error adding {connector_name}: {e}")
        
        print(f"\n6. Successfully added {added_count}/{len(registry_connectors)} connectors to RAG database")
        
        # Test retrieval
        print("7. Testing connector retrieval...")
        test_connectors = await rag.retrieve_connectors("email search web", limit=10)
        print(f"Retrieved {len(test_connectors)} connectors: {[c.name for c in test_connectors]}")
        
        print("\n🎉 RAG database updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating RAG database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_rag_connectors())