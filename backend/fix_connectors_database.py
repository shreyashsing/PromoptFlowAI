#!/usr/bin/env python3
"""
Fix connectors database by generating embeddings and setting correct auth types.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client
from app.services.rag import EmbeddingService
from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors
import json


async def fix_connectors_database():
    """Fix the connectors database with proper embeddings and auth types."""
    print("🔧 Fixing Connectors Database")
    print("=" * 40)
    
    try:
        # 1. Initialize services
        print("1. Initializing services...")
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        register_core_connectors()
        supabase = get_supabase_client()
        
        # 2. Get current connectors
        print("2. Fetching current connectors...")
        result = supabase.table("connectors").select("*").execute()
        db_connectors = result.data
        print(f"   Found {len(db_connectors)} connectors in database")
        
        # 3. Get real connector instances for auth type detection
        print("3. Analyzing real connector auth requirements...")
        real_connectors = {}
        for connector_name in connector_registry.list_connectors():
            try:
                connector_instance = connector_registry.create_connector(connector_name)
                auth_req = await connector_instance.get_auth_requirements()
                real_connectors[connector_name] = {
                    'instance': connector_instance,
                    'auth_type': auth_req.type.value if hasattr(auth_req.type, 'value') else str(auth_req.type)
                }
                print(f"   ✅ {connector_name}: auth_type = {real_connectors[connector_name]['auth_type']}")
            except Exception as e:
                print(f"   ❌ Failed to analyze {connector_name}: {e}")
        
        # 4. Fix each connector
        print("\n4. Fixing connectors...")
        fixed_count = 0
        
        for db_conn in db_connectors:
            connector_name = db_conn['name']
            connector_id = db_conn['id']
            
            print(f"\n🔧 Fixing: {connector_name}")
            
            # Prepare updates
            updates = {}
            
            # Generate embedding if missing
            if db_conn.get('embedding') is None:
                print(f"   📊 Generating embedding...")
                embedding_text = f"{db_conn['name']} {db_conn['description']} {db_conn['category']}"
                try:
                    embedding = await embedding_service.generate_embedding(embedding_text)
                    updates['embedding'] = embedding
                    print(f"   ✅ Generated embedding with {len(embedding)} dimensions")
                except Exception as e:
                    print(f"   ❌ Failed to generate embedding: {e}")
            
            # Fix auth_type
            if connector_name in real_connectors:
                correct_auth_type = real_connectors[connector_name]['auth_type']
                current_auth_type = db_conn.get('auth_type')
                
                if current_auth_type != correct_auth_type:
                    updates['auth_type'] = correct_auth_type
                    print(f"   🔐 Updated auth_type: {current_auth_type} → {correct_auth_type}")
            
            # Apply updates if any
            if updates:
                try:
                    supabase.table("connectors").update(updates).eq("id", connector_id).execute()
                    fixed_count += 1
                    print(f"   ✅ Successfully updated connector")
                except Exception as e:
                    print(f"   ❌ Failed to update connector: {e}")
            else:
                print(f"   ℹ️  No updates needed")
        
        # 5. Verify fixes
        print(f"\n5. Verifying fixes...")
        result = supabase.table("connectors").select("name, auth_type, embedding").execute()
        updated_connectors = result.data
        
        null_embeddings = [c for c in updated_connectors if c.get('embedding') is None]
        auth_type_counts = {}
        for c in updated_connectors:
            auth_type = c.get('auth_type', 'null')
            auth_type_counts[auth_type] = auth_type_counts.get(auth_type, 0) + 1
        
        print("\n📊 VERIFICATION RESULTS:")
        print(f"   🔧 Connectors fixed: {fixed_count}")
        print(f"   ❌ Remaining NULL embeddings: {len(null_embeddings)}")
        print(f"   🔐 Auth type distribution:")
        for auth_type, count in auth_type_counts.items():
            print(f"      - {auth_type}: {count} connectors")
        
        if null_embeddings:
            print(f"   ⚠️  Connectors still missing embeddings:")
            for conn in null_embeddings:
                print(f"      - {conn['name']}")
        
        # 6. Test RAG retrieval
        print(f"\n6. Testing RAG retrieval...")
        try:
            from app.services.rag import RAGRetriever
            rag = RAGRetriever()
            await rag.initialize()
            
            test_queries = [
                "send email",
                "search web blogs", 
                "summarize text",
                "Google Sheets"
            ]
            
            for query in test_queries:
                connectors = await rag.retrieve_connectors(query, limit=3, similarity_threshold=0.1)
                print(f"   📧 Query '{query}': Found {len(connectors)} connectors")
                for conn in connectors[:2]:  # Show top 2
                    print(f"      - {conn.name}")
        
        except Exception as e:
            print(f"   ❌ RAG test failed: {e}")
        
        print("\n✅ Database fix complete!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_connectors_database()) 