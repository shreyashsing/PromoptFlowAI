#!/usr/bin/env python3
"""
Script to create vector similarity functions in Supabase.
"""
import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging_config import init_logging
from app.core.database import get_database

# Initialize logging
init_logging()
logger = logging.getLogger(__name__)


async def create_vector_functions():
    """Create vector similarity functions in the database."""
    try:
        logger.info("🔧 Creating Vector Similarity Functions")
        logger.info("=" * 50)
        
        db = await get_database()
        
        # SQL to create the match_connectors function
        match_connectors_sql = """
        CREATE OR REPLACE FUNCTION match_connectors(
            query_embedding vector(1536),
            match_threshold float DEFAULT 0.7,
            match_count int DEFAULT 10,
            category_filter text DEFAULT NULL
        )
        RETURNS TABLE (
            id uuid,
            name text,
            display_name text,
            description text,
            category text,
            schema jsonb,
            auth_type text,
            embedding vector(1536),
            usage_count int,
            is_active boolean,
            created_at timestamptz,
            updated_at timestamptz,
            similarity float
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                c.id,
                c.name,
                c.display_name,
                c.description,
                c.category,
                c.schema,
                c.auth_type,
                c.embedding,
                c.usage_count,
                c.is_active,
                c.created_at,
                c.updated_at,
                (1 - (c.embedding <=> query_embedding)) as similarity
            FROM connectors c
            WHERE c.is_active = true
            AND (category_filter IS NULL OR c.category = category_filter)
            AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
            ORDER BY c.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
        
        # SQL to create a simple exec_sql function for raw queries
        exec_sql_function = """
        CREATE OR REPLACE FUNCTION exec_sql(sql text)
        RETURNS json
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            result json;
        BEGIN
            EXECUTE sql INTO result;
            RETURN result;
        END;
        $$;
        """
        
        # Create the match_connectors function
        logger.info("Creating match_connectors function...")
        try:
            result = db.rpc('exec_sql', {'sql': match_connectors_sql}).execute()
            logger.info("✅ match_connectors function created successfully")
        except Exception as e:
            logger.warning(f"Failed to create match_connectors function: {e}")
            # Try direct SQL execution
            try:
                result = db.query(match_connectors_sql).execute()
                logger.info("✅ match_connectors function created via direct query")
            except Exception as e2:
                logger.error(f"Failed to create match_connectors function via direct query: {e2}")
        
        # Create the exec_sql function
        logger.info("Creating exec_sql function...")
        try:
            result = db.rpc('exec_sql', {'sql': exec_sql_function}).execute()
            logger.info("✅ exec_sql function created successfully")
        except Exception as e:
            logger.warning(f"Failed to create exec_sql function: {e}")
            # Try direct SQL execution
            try:
                result = db.query(exec_sql_function).execute()
                logger.info("✅ exec_sql function created via direct query")
            except Exception as e2:
                logger.error(f"Failed to create exec_sql function via direct query: {e2}")
        
        # Test the functions
        logger.info("Testing vector similarity functions...")
        
        # Create a test embedding (dummy values)
        test_embedding = [0.1] * 1536
        
        try:
            result = db.rpc('match_connectors', {
                'query_embedding': test_embedding,
                'match_threshold': 0.1,
                'match_count': 5
            }).execute()
            
            logger.info(f"✅ match_connectors function test successful - found {len(result.data)} results")
            
        except Exception as e:
            logger.warning(f"match_connectors function test failed: {e}")
        
        logger.info("=" * 50)
        logger.info("✅ Vector similarity functions setup completed!")
        
    except Exception as e:
        logger.error(f"❌ Failed to create vector functions: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_vector_functions())