"""
Database connection and management using Supabase.
"""
import logging
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


# Database connection instance
database_manager: Optional['DatabaseManager'] = None


async def init_database():
    """Initialize the database connection."""
    global database_manager
    database_manager = DatabaseManager()
    await database_manager.initialize()


async def close_database():
    """Close the database connection."""
    global database_manager
    if database_manager:
        await database_manager.close()


async def get_database() -> Client:
    """Get the database client instance."""
    if not database_manager or not database_manager._initialized:
        await init_database()
    return database_manager.client


def get_supabase_client() -> Client:
    """Get Supabase client for synchronous operations."""
    # Use service role key for backend operations to bypass RLS
    key_to_use = settings.SUPABASE_SERVICE_ROLE_KEY if settings.SUPABASE_SERVICE_ROLE_KEY else settings.SUPABASE_KEY
    
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=key_to_use
    )


class HealthCheckResult:
    def __init__(self, status: str, details: dict):
        self.status = status
        self.details = details


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
            # Use service role key for backend operations to bypass RLS policies
            key_to_use = settings.SUPABASE_SERVICE_ROLE_KEY if settings.SUPABASE_SERVICE_ROLE_KEY else settings.SUPABASE_KEY
            
            logger.info(f"Initializing database with:")
            logger.info(f"- SUPABASE_URL: {'SET' if settings.SUPABASE_URL else 'MISSING'}")
            logger.info(f"- SUPABASE_KEY (anon): {'SET' if settings.SUPABASE_KEY else 'MISSING'}")
            logger.info(f"- SUPABASE_SERVICE_ROLE_KEY: {'SET' if settings.SUPABASE_SERVICE_ROLE_KEY else 'MISSING'}")
            
            if settings.SUPABASE_SERVICE_ROLE_KEY:
                logger.info("Using service role key for database operations (bypasses RLS)")
            else:
                logger.warning("Service role key not found, using anon key (may hit RLS restrictions)")
            
            self._client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=key_to_use
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
        """Close database connections."""
        # Supabase client doesn't need explicit closing
        self._initialized = False
        self._client = None
        logger.info("Database connections closed")


class DatabaseConnection:
    """Context manager for database connections."""
    
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def __aenter__(self) -> Client:
        self.client = await get_database()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # No explicit cleanup needed for Supabase client
        pass


# Convenience function for getting database in FastAPI dependencies
async def get_supabase_dependency() -> Client:
    """FastAPI dependency for getting Supabase client."""
    return await get_database()