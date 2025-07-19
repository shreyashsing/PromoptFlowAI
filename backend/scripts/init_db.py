#!/usr/bin/env python3
"""
Database initialization script for PromptFlow AI.
This script sets up the database schema and initial data.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_database
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def read_schema_file() -> str:
    """Read the database schema SQL file."""
    schema_path = backend_dir / "app" / "database" / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        return f.read()


async def execute_schema(db_client, schema_sql: str):
    """Execute the database schema SQL."""
    try:
        # Split the schema into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        logger.info(f"Executing {len(statements)} SQL statements...")
        
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    # Use raw SQL execution for schema creation
                    result = db_client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.debug(f"Statement {i} executed successfully")
                except Exception as e:
                    logger.warning(f"Statement {i} failed (may be expected): {e}")
                    # Continue with other statements
        
        logger.info("Schema execution completed")
        
    except Exception as e:
        logger.error(f"Schema execution failed: {e}")
        raise


async def insert_initial_connectors(db_client):
    """Insert initial connector metadata."""
    try:
        # Basic connectors for MVP
        initial_connectors = [
            {
                "name": "http_request",
                "display_name": "HTTP Request",
                "description": "Make HTTP requests to any REST API endpoint with support for GET, POST, PUT, DELETE methods",
                "category": "data_sources",
                "schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to make the request to"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                        "headers": {"type": "object", "description": "HTTP headers to include"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "data": {"type": "object", "description": "Request body data"}
                    },
                    "required": ["url"]
                },
                "auth_type": "api_key",
                "auth_config": {
                    "header_name": "Authorization",
                    "prefix": "Bearer "
                },
                "is_active": True
            },
            {
                "name": "gmail",
                "display_name": "Gmail",
                "description": "Send and receive emails using Gmail API with OAuth authentication",
                "category": "communication",
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["send", "read", "search"]},
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"},
                        "query": {"type": "string", "description": "Search query for reading emails"}
                    },
                    "required": ["action"]
                },
                "auth_type": "oauth2",
                "auth_config": {
                    "scopes": ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"],
                    "auth_url": "https://accounts.google.com/o/oauth2/auth",
                    "token_url": "https://oauth2.googleapis.com/token"
                },
                "is_active": True
            },
            {
                "name": "google_sheets",
                "display_name": "Google Sheets",
                "description": "Read from and write to Google Sheets with full CRUD operations",
                "category": "data_sources",
                "schema": {
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string", "description": "Google Sheets spreadsheet ID"},
                        "range": {"type": "string", "description": "Cell range (e.g., A1:D10)"},
                        "action": {"type": "string", "enum": ["read", "write", "append", "update"]},
                        "values": {"type": "array", "description": "Data to write/append"}
                    },
                    "required": ["spreadsheet_id", "action"]
                },
                "auth_type": "oauth2",
                "auth_config": {
                    "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
                    "auth_url": "https://accounts.google.com/o/oauth2/auth",
                    "token_url": "https://oauth2.googleapis.com/token"
                },
                "is_active": True
            },
            {
                "name": "webhook",
                "display_name": "Webhook",
                "description": "Receive data from external services via HTTP webhooks",
                "category": "triggers",
                "schema": {
                    "type": "object",
                    "properties": {
                        "endpoint_name": {"type": "string", "description": "Unique name for the webhook endpoint"},
                        "method": {"type": "string", "enum": ["POST", "GET", "PUT"], "default": "POST"},
                        "validation": {"type": "object", "description": "Webhook validation settings"}
                    },
                    "required": ["endpoint_name"]
                },
                "auth_type": "none",
                "auth_config": {},
                "is_active": True
            }
        ]
        
        # Insert connectors
        for connector in initial_connectors:
            result = db_client.table('connectors').upsert(connector).execute()
            logger.info(f"Inserted connector: {connector['name']}")
        
        logger.info(f"Inserted {len(initial_connectors)} initial connectors")
        
    except Exception as e:
        logger.error(f"Failed to insert initial connectors: {e}")
        raise


async def main():
    """Main initialization function."""
    try:
        logger.info("Starting database initialization...")
        
        # Check if required environment variables are set
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            return 1
        
        # Get database client
        db_client = await get_database()
        
        # Read and execute schema
        logger.info("Reading database schema...")
        schema_sql = await read_schema_file()
        
        logger.info("Executing database schema...")
        await execute_schema(db_client, schema_sql)
        
        # Insert initial data
        logger.info("Inserting initial connector data...")
        await insert_initial_connectors(db_client)
        
        logger.info("Database initialization completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)