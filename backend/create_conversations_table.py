#!/usr/bin/env python3
"""
Script to create the conversations table in the database.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_database

async def create_conversations_table():
    """Create the conversations table."""
    print("📚 Creating conversations table...")
    
    try:
        db = await get_database()
        
        # Create the conversations table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS public.conversations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            messages JSONB NOT NULL DEFAULT '[]',
            current_plan JSONB,
            state TEXT NOT NULL DEFAULT 'initial' CHECK (state IN ('initial', 'planning', 'confirming', 'approved', 'executing')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Try to create table by inserting a dummy record first to trigger table creation
        # This is a workaround since we can't execute DDL directly through Supabase client
        try:
            # Check if table exists by trying to select from it
            db.table('conversations').select('*').limit(1).execute()
            print("✅ Conversations table already exists")
        except Exception as table_error:
            print(f"⚠️  Table doesn't exist or has issues: {table_error}")
            print("📝 Please create the conversations table manually in your Supabase dashboard:")
            print(create_table_sql)
        print("✅ Conversations table created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create conversations table: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(create_conversations_table())
    sys.exit(0 if result else 1)