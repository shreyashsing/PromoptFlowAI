"""
Test if ReAct agent tables exist in the database.
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client

async def test_react_tables():
    """Test if ReAct agent tables exist."""
    try:
        client = get_supabase_client()
        
        # Test each table
        tables_to_test = [
            'react_conversations',
            'react_conversation_messages', 
            'react_tool_executions',
            'react_reasoning_traces'
        ]
        
        for table_name in tables_to_test:
            try:
                result = client.table(table_name).select('*').limit(1).execute()
                print(f"✓ Table '{table_name}' exists and is accessible")
            except Exception as e:
                print(f"✗ Table '{table_name}' error: {e}")
        
        print("\nTable test completed!")
        
    except Exception as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_react_tables())