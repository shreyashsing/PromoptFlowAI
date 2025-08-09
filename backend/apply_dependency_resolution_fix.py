#!/usr/bin/env python3
"""
Apply dependency resolution column fix to the database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def apply_fix():
    """Apply the dependency resolution column fix."""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        # Connect to database
        print("🔗 Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        # Read and execute the SQL fix
        with open('add_dependency_resolution_column.sql', 'r') as f:
            sql_fix = f.read()
        
        print("📝 Applying dependency resolution column fix...")
        await conn.execute(sql_fix)
        
        # Verify the column was added
        result = await conn.fetchrow("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'workflow_executions' 
            AND column_name = 'dependency_resolution_time_ms'
        """)
        
        if result:
            print("✅ dependency_resolution_time_ms column added successfully!")
        else:
            print("❌ Failed to add dependency_resolution_time_ms column")
            return False
        
        await conn.close()
        print("🎉 Database fix applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_fix())
    if not success:
        exit(1)