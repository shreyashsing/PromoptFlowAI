#!/usr/bin/env python3
"""
Clean RAG database and reload only real registered connectors.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client
from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors
from app.models.connector import ConnectorMetadata
from app.models.base import AuthType


async def clean_rag_database():
    """Clean RAG database and reload only real connectors."""
    print("🧹 Cleaning RAG Database")
    print("=" * 30)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # 1. Check what's currently in the database
        print("1. Checking current connectors in database...")
        current_result = supabase.table("connectors").select("name, description").execute()
        current_connectors = [row["name"] for row in current_result.data]
        print(f"   Found: {current_connectors}")
        
        # 2. Register real connectors
        print("2. Registering real connectors...")
        register_core_connectors()
        real_connectors = connector_registry.list_connectors()
        print(f"   Real connectors: {real_connectors}")
        
        # 3. Delete all existing connectors
        print("3. Clearing existing connectors...")
        delete_result = supabase.table("connectors").delete().gte("id", 0).execute()
        print(f"   Deleted {len(delete_result.data) if delete_result.data else 0} connectors")
        
        # 4. Add only real connectors
        print("4. Adding real connectors...")
        for connector_name in real_connectors:
            try:
                # Create connector instance to get metadata
                connector_instance = connector_registry.create_connector(connector_name)
                
                # Prepare connector data
                connector_data = {
                    "name": connector_name,
                    "display_name": connector_name.replace("_", " ").title(),
                    "description": connector_instance.description,
                    "category": connector_instance.category,
                    "schema": connector_instance.schema,
                    "auth_type": "none",  # Simplified for now
                    "embedding": None,    # Will be generated later
                    "usage_count": 0,
                    "is_active": True
                }
                
                # Insert connector
                result = supabase.table("connectors").insert(connector_data).execute()
                print(f"   ✅ Added: {connector_name}")
                
            except Exception as e:
                print(f"   ❌ Failed to add {connector_name}: {e}")
        
        # 5. Verify final state
        print("5. Verifying final state...")
        final_result = supabase.table("connectors").select("name").execute()
        final_connectors = [row["name"] for row in final_result.data]
        print(f"   Final connectors: {final_connectors}")
        
        print("\n✅ RAG database cleaned successfully!")
        print(f"   Real connectors: {len(real_connectors)}")
        print(f"   Database connectors: {len(final_connectors)}")
        
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(clean_rag_database()) 