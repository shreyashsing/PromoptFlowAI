"""
RAG (Retrieval-Augmented Generation) system for connector retrieval.
Handles embedding generation, vector storage, and similarity search.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from openai import AsyncAzureOpenAI
from app.core.config import settings
from app.core.database import get_database
from app.models.connector import ConnectorMetadata
from app.core.exceptions import RAGError, EmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI."""
    
    def __init__(self):
        self._client: Optional[AsyncAzureOpenAI] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Azure OpenAI client."""
        if self._initialized:
            return
            
        try:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            self._initialized = True
            logger.info("Embedding service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise EmbeddingError(f"Failed to initialize embedding service: {e}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text."""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await self._client.embeddings.create(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text: {text[:100]}...")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await self._client.embeddings.create(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}")


class ConnectorMetadataManager:
    """Manages connector metadata storage and retrieval."""
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
    
    async def store_connector(self, connector: ConnectorMetadata) -> None:
        """Store connector metadata with embedding in the database."""
        try:
            db = await get_database()
            
            # Generate embedding for connector description and name
            embedding_text = f"{connector.name} {connector.description} {connector.category}"
            embedding = await self.embedding_service.generate_embedding(embedding_text)
            
            # Prepare data for insertion
            connector_data = {
                "name": connector.name,
                "display_name": connector.name.replace("_", " ").title(),
                "description": connector.description,
                "category": connector.category,
                "schema": connector.parameter_schema,
                "auth_type": connector.auth_type.value,
                "embedding": embedding,
                "usage_count": connector.usage_count
            }
            
            # Insert or update connector
            result = db.table("connectors").upsert(
                connector_data,
                on_conflict="name"
            ).execute()
            
            logger.info(f"Stored connector metadata: {connector.name}")
            
        except Exception as e:
            logger.error(f"Failed to store connector {connector.name}: {e}")
            raise RAGError(f"Failed to store connector metadata: {e}")
    
    async def store_connectors_batch(self, connectors: List[ConnectorMetadata]) -> None:
        """Store multiple connectors in batch."""
        try:
            db = await get_database()
            
            # Generate embeddings for all connectors
            embedding_texts = [
                f"{conn.name} {conn.description} {conn.category}"
                for conn in connectors
            ]
            embeddings = await self.embedding_service.generate_embeddings_batch(embedding_texts)
            
            # Prepare data for batch insertion
            connectors_data = []
            for connector, embedding in zip(connectors, embeddings):
                connectors_data.append({
                    "name": connector.name,
                    "display_name": connector.name.replace("_", " ").title(),
                    "description": connector.description,
                    "category": connector.category,
                    "schema": connector.parameter_schema,
                    "auth_type": connector.auth_type.value,
                    "embedding": embedding,
                    "usage_count": connector.usage_count
                })
            
            # Batch insert/update
            result = db.table("connectors").upsert(
                connectors_data,
                on_conflict="name"
            ).execute()
            
            logger.info(f"Stored {len(connectors)} connectors in batch")
            
        except Exception as e:
            logger.error(f"Failed to store connectors batch: {e}")
            raise RAGError(f"Failed to store connectors batch: {e}")
    
    async def get_connector_by_name(self, name: str) -> Optional[ConnectorMetadata]:
        """Retrieve connector metadata by name."""
        try:
            db = await get_database()
            
            result = db.table("connectors").select("*").eq("name", name).eq("is_active", True).execute()
            
            if not result.data:
                return None
            
            connector_data = result.data[0]
            return self._convert_to_connector_metadata(connector_data)
            
        except Exception as e:
            logger.error(f"Failed to get connector {name}: {e}")
            raise RAGError(f"Failed to retrieve connector: {e}")
    
    async def get_all_connectors(self) -> List[ConnectorMetadata]:
        """Retrieve all active connectors."""
        try:
            db = await get_database()
            
            result = db.table("connectors").select("*").eq("is_active", True).execute()
            
            connectors = []
            for connector_data in result.data:
                connectors.append(self._convert_to_connector_metadata(connector_data))
            
            return connectors
            
        except Exception as e:
            logger.error(f"Failed to get all connectors: {e}")
            raise RAGError(f"Failed to retrieve connectors: {e}")
    
    async def update_usage_count(self, connector_name: str) -> None:
        """Increment usage count for a connector."""
        try:
            db = await get_database()
            
            # Get current usage count
            result = db.table("connectors").select("usage_count").eq("name", connector_name).execute()
            
            if result.data:
                current_count = result.data[0]["usage_count"]
                new_count = current_count + 1
                
                # Update usage count
                db.table("connectors").update({"usage_count": new_count}).eq("name", connector_name).execute()
                
                logger.debug(f"Updated usage count for {connector_name}: {new_count}")
            
        except Exception as e:
            logger.error(f"Failed to update usage count for {connector_name}: {e}")
            # Don't raise error for usage count updates as it's not critical
    
    def _convert_to_connector_metadata(self, data: Dict[str, Any]) -> ConnectorMetadata:
        """Convert database row to ConnectorMetadata model."""
        from app.models.base import AuthType
        
        return ConnectorMetadata(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            parameter_schema=data["schema"],
            auth_type=AuthType(data["auth_type"]),
            embedding=data.get("embedding"),
            usage_count=data.get("usage_count", 0),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )


class RAGRetriever:
    """Main RAG system for connector retrieval using vector similarity search."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.metadata_manager = ConnectorMetadataManager(self.embedding_service)
    
    async def initialize(self) -> None:
        """Initialize the RAG system."""
        await self.embedding_service.initialize()
        logger.info("RAG retriever initialized successfully")
    
    async def retrieve_connectors(
        self, 
        query: str, 
        limit: int = 10,
        category_filter: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[ConnectorMetadata]:
        """
        Retrieve relevant connectors based on semantic similarity.
        
        Args:
            query: Natural language query describing the desired functionality
            limit: Maximum number of connectors to return
            category_filter: Optional category to filter by
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of ConnectorMetadata ordered by relevance
        """
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build the similarity search query
            db = await get_database()
            
            # Use pgvector's cosine similarity search
            query_builder = db.table("connectors").select(
                "*",
                "embedding <=> %s as similarity"
            ).eq("is_active", True)
            
            # Add category filter if specified
            if category_filter:
                query_builder = query_builder.eq("category", category_filter)
            
            # Execute similarity search with limit
            result = query_builder.order("similarity").limit(limit).execute()
            
            # Convert results and filter by similarity threshold
            connectors = []
            for row in result.data:
                # Calculate actual similarity score (1 - cosine_distance)
                similarity_score = 1 - row["similarity"]
                
                if similarity_score >= similarity_threshold:
                    connector = self.metadata_manager._convert_to_connector_metadata(row)
                    connectors.append(connector)
            
            # Update usage counts for retrieved connectors
            for connector in connectors:
                await self.metadata_manager.update_usage_count(connector.name)
            
            logger.info(f"Retrieved {len(connectors)} connectors for query: {query[:100]}...")
            return connectors
            
        except Exception as e:
            logger.error(f"Failed to retrieve connectors for query '{query}': {e}")
            raise RAGError(f"Failed to retrieve connectors: {e}")
    
    async def retrieve_connectors_by_category(self, category: str, limit: int = 20) -> List[ConnectorMetadata]:
        """Retrieve connectors filtered by category."""
        try:
            db = await get_database()
            
            result = db.table("connectors").select("*").eq("category", category).eq("is_active", True).order("usage_count", desc=True).limit(limit).execute()
            
            connectors = []
            for row in result.data:
                connectors.append(self.metadata_manager._convert_to_connector_metadata(row))
            
            logger.info(f"Retrieved {len(connectors)} connectors for category: {category}")
            return connectors
            
        except Exception as e:
            logger.error(f"Failed to retrieve connectors for category '{category}': {e}")
            raise RAGError(f"Failed to retrieve connectors by category: {e}")
    
    async def get_popular_connectors(self, limit: int = 10) -> List[ConnectorMetadata]:
        """Retrieve most popular connectors based on usage count."""
        try:
            db = await get_database()
            
            result = db.table("connectors").select("*").eq("is_active", True).order("usage_count", desc=True).limit(limit).execute()
            
            connectors = []
            for row in result.data:
                connectors.append(self.metadata_manager._convert_to_connector_metadata(row))
            
            logger.info(f"Retrieved {len(connectors)} popular connectors")
            return connectors
            
        except Exception as e:
            logger.error(f"Failed to retrieve popular connectors: {e}")
            raise RAGError(f"Failed to retrieve popular connectors: {e}")
    
    async def update_connector_embeddings(self, connector_names: Optional[List[str]] = None) -> None:
        """
        Update embeddings for connectors (useful for reprocessing).
        
        Args:
            connector_names: Optional list of specific connectors to update. If None, updates all.
        """
        try:
            db = await get_database()
            
            # Get connectors to update
            if connector_names:
                result = db.table("connectors").select("*").in_("name", connector_names).execute()
            else:
                result = db.table("connectors").select("*").execute()
            
            if not result.data:
                logger.info("No connectors found to update embeddings")
                return
            
            # Generate new embeddings
            embedding_texts = []
            connectors_data = []
            
            for row in result.data:
                embedding_text = f"{row['name']} {row['description']} {row['category']}"
                embedding_texts.append(embedding_text)
                connectors_data.append(row)
            
            embeddings = await self.embedding_service.generate_embeddings_batch(embedding_texts)
            
            # Update embeddings in database
            for connector_data, embedding in zip(connectors_data, embeddings):
                db.table("connectors").update({"embedding": embedding}).eq("id", connector_data["id"]).execute()
            
            logger.info(f"Updated embeddings for {len(connectors_data)} connectors")
            
        except Exception as e:
            logger.error(f"Failed to update connector embeddings: {e}")
            raise RAGError(f"Failed to update connector embeddings: {e}")


# Global RAG retriever instance
rag_retriever = RAGRetriever()


async def get_rag_retriever() -> RAGRetriever:
    """Dependency to get RAG retriever instance."""
    if not rag_retriever.embedding_service._initialized:
        await rag_retriever.initialize()
    return rag_retriever


async def init_rag_system() -> None:
    """Initialize RAG system on startup."""
    await rag_retriever.initialize()