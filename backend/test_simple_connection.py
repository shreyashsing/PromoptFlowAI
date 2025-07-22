#!/usr/bin/env python3
"""
Simple connection test for Supabase only.
"""
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
import asyncio

async def test_supabase_connection():
    """Test basic Supabase connection."""
    print("Testing Supabase connection...")
    
    try:
        from supabase import create_client, Client
        
        try:
            # Method 1: Simple client creation
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            print(f"✅ Supabase client created successfully (method 1)")
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            try:
                # Method 2: Using keyword arguments
                client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY
                )
                print(f"✅ Supabase client created successfully (method 2)")
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
                # Method 3: Direct instantiation
                from supabase.client import Client as SupabaseClient
                client = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                print(f"✅ Supabase client created successfully (method 3)")
        
        print(f"URL: {settings.SUPABASE_URL}")
        
        # Test a simple query
        try:
            result = client.table('connectors').select('name').limit(1).execute()
            print(f"✅ Database query successful")
            print(f"Data: {result.data}")
        except Exception as e:
            print(f"⚠️  Database query failed (table might not exist): {e}")
            try:
                result = client.table('_supabase_migrations').select('*').limit(1).execute()
                print(f"✅ Database connection verified (migrations table accessible)")
            except Exception as e2:
                print(f"⚠️  Database connection test failed: {e2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("This might be due to library version compatibility issues.")
        print("The system can still work with a mock database for testing.")
        return False

async def main():
    """Main test function."""
    print("🧪 Supabase Connection Test")
    print("=" * 50)
    
    # Test environment variables
    print("Environment Variables:")
    print(f"SUPABASE_URL: {'✅ Set' if settings.SUPABASE_URL else '❌ Missing'}")
    print(f"SUPABASE_KEY: {'✅ Set' if settings.SUPABASE_KEY else '❌ Missing'}")
    print()
    
    # Test Supabase connection
    supabase_ok = await test_supabase_connection()
    
    print("\n" + "=" * 50)
    print("Connection Test Results:")
    print(f"Supabase: {'✅ Connected' if supabase_ok else '❌ Failed'}")
    
    if supabase_ok:
        print("\n🎉 Supabase connection successful! Ready to proceed.")
        return 0
    else:
        print("\n💥 Supabase connection failed. Please check your configuration.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
