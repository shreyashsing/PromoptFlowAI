#!/usr/bin/env python3
"""
Analyze Supabase connectors table for issues.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client
import json


async def analyze_connectors():
    """Analyze the connectors table in Supabase."""
    print("🔍 Analyzing Supabase Connectors Table")
    print("=" * 40)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # 1. Get all connectors
        print("1. Fetching all connectors...")
        result = supabase.table("connectors").select("*").execute()
        connectors = result.data
        
        print(f"   Found {len(connectors)} connectors")
        
        # 2. Analyze each connector
        print("\n2. Analyzing connector details:")
        print("-" * 60)
        
        for i, conn in enumerate(connectors, 1):
            print(f"\n📦 Connector {i}: {conn.get('name', 'UNNAMED')}")
            print(f"   ID: {conn.get('id', 'N/A')}")
            print(f"   Display Name: {conn.get('display_name', 'N/A')}")
            print(f"   Description: {conn.get('description', 'N/A')[:100]}...")
            print(f"   Category: {conn.get('category', 'N/A')}")
            print(f"   Auth Type: {conn.get('auth_type', 'NULL')}")
            print(f"   Is Active: {conn.get('is_active', 'N/A')}")
            print(f"   Usage Count: {conn.get('usage_count', 'N/A')}")
            
            # Check embedding
            embedding = conn.get('embedding')
            if embedding is None:
                print(f"   ❌ Embedding: NULL")
            elif isinstance(embedding, list) and len(embedding) > 0:
                print(f"   ✅ Embedding: Array with {len(embedding)} dimensions")
            else:
                print(f"   ⚠️  Embedding: {type(embedding)} - {str(embedding)[:50]}...")
            
            # Check schema
            schema = conn.get('schema')
            if schema is None:
                print(f"   ❌ Schema: NULL")
            elif isinstance(schema, dict):
                required_fields = schema.get('required', [])
                properties = schema.get('properties', {})
                print(f"   ✅ Schema: {len(properties)} properties, {len(required_fields)} required")
            else:
                print(f"   ⚠️  Schema: {type(schema)}")
            
            # Check auth_config
            auth_config = conn.get('auth_config')
            if auth_config is None:
                print(f"   ⚠️  Auth Config: NULL")
            elif isinstance(auth_config, dict):
                print(f"   ✅ Auth Config: {len(auth_config)} fields")
            else:
                print(f"   ⚠️  Auth Config: {type(auth_config)}")
        
        # 3. Summary of issues
        print("\n" + "=" * 60)
        print("📊 ISSUE SUMMARY:")
        
        null_embeddings = [c for c in connectors if c.get('embedding') is None]
        null_auth_types = [c for c in connectors if c.get('auth_type') is None]
        null_schemas = [c for c in connectors if c.get('schema') is None]
        inactive_connectors = [c for c in connectors if not c.get('is_active', True)]
        
        print(f"❌ Connectors with NULL embeddings: {len(null_embeddings)}")
        if null_embeddings:
            for conn in null_embeddings:
                print(f"   - {conn.get('name', 'UNNAMED')}")
        
        print(f"❌ Connectors with NULL auth_type: {len(null_auth_types)}")
        if null_auth_types:
            for conn in null_auth_types:
                print(f"   - {conn.get('name', 'UNNAMED')}")
        
        print(f"❌ Connectors with NULL schema: {len(null_schemas)}")
        if null_schemas:
            for conn in null_schemas:
                print(f"   - {conn.get('name', 'UNNAMED')}")
        
        print(f"⚠️  Inactive connectors: {len(inactive_connectors)}")
        if inactive_connectors:
            for conn in inactive_connectors:
                print(f"   - {conn.get('name', 'UNNAMED')}")
        
        # 4. Check table structure
        print(f"\n4. Database table structure:")
        if connectors:
            first_connector = connectors[0]
            print(f"   Available columns: {list(first_connector.keys())}")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error analyzing connectors: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_connectors()) 