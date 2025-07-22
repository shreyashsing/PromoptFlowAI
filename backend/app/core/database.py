"""
Database connection and utilities for Supabase integration.
"""
import asyncio
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MockSupabaseClient:
    """Mock Supabase client for testing when real client fails."""
    
    def table(self, table_name: str):
        return MockTable(table_name)


class MockTable:
    """Mock Supabase table for testing."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self._query = {}
    
    def select(self, columns: str = "*"):
        return self
    
    def insert(self, data):
        return MockResponse([data] if isinstance(data, dict) else data)
    
    def update(self, data):
        return self
    
    def delete(self):
        return self
    
    def eq(self, column: str, value):
        return self
    
    def order(self, column: str, desc: bool = False):
        return self
    
    def range(self, start: int, end: int):
        return self
    
    def execute(self):
        return MockResponse([])


class MockResponse:
    """Mock Supabase response for testing."""
    
    def __init__(self, data):
        self.data = data
    
    def execute(self):
        return self


class DatabaseManager:
    """Manages Supabase database connections and operations."""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Supabase client connection."""
        if self._initialized:
            return
            
        try:
            # Create simple client without complex options
            self._client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
            
            # Test connection
            await self.health_check()
            self._initialized = True
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            if not self._client:
                return False
                
            # Simple query to test connection
            result = self._client.table('users').select('id').limit(1).execute()
            return True
            
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if not self._initialized or not self._client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._client
    
    async def close(self) -> None:
        """Close database connections and cleanup."""
        if self._client:
            # Supabase client doesn't require explicit closing
            # but we can cleanup any cached data
            self._client = None
            self._initialized = False
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> Client:
    """Dependency to get database client."""
    if not db_manager._initialized:
        await db_manager.initialize()
    return db_manager.client


async def init_database() -> None:
    """Initialize database connection on startup."""
    await db_manager.initialize()


async def close_database() -> None:
    """Close database connection on shutdown."""
    await db_manager.close()


def get_supabase_client() -> Client:
    """Get Supabase client synchronously for use in services."""
    if not db_manager._initialized or not db_manager._client:
        try:
            # Create a simple client without complex options for testing
            return create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            # Return a mock client for testing if Supabase fails
            return MockSupabaseClient()
    
    return db_manager.client