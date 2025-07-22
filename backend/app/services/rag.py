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
from app.core.error_utils import handle_external_api_errors, handle_database_errors, log_function_performance

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
            # Initialize with minimal parameters to avoid version compatibility issues
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                timeout=30.0  # Add timeout instead of proxies
            )
            self._initialized = True
            logger.info("Embedding service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            # Set client to None and mark as initialized to prevent blocking
            self._client = None
            self._initialized = True
            logger.warning("RAG system will run in degraded mode without embeddings")
    
    @handle_external_api_errors("Azure OpenAI Embeddings", retryable=True)
    @log_function_performance("generate_embedding")
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text."""
        if not self._initialized:
            await self.initialize()
            
        # If client is None (initialization failed), return dummy embedding
        if self._client is None:
            logger.warning("Embedding service not available, returning dummy embedding")
            # Return a dummy embedding vector (1536 dimensions for text-embedding-ada-002)
            return [0.0] * 1536
            
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
            # Return dummy embedding as fallback
            logger.warning("Returning dummy embedding due to API failure")
            return [0.0] * 1536
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        if not self._initialized:
            await self.initialize()
            
        # If client is None (initialization failed), return dummy embeddings
        if self._client is None:
            logger.warning("Embedding service not available, returning dummy embeddings")
            return [[0.0] * 1536 for _ in texts]
            
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
            # Return dummy embeddings as fallback
            logger.warning("Returning dummy embeddings due to API failure")
            return [[0.0] * 1536 for _ in texts]


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
        import json
        
        # Parse embedding if it's a string
        embedding = data.get("embedding")
        if embedding and isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                embedding = None
        
        return ConnectorMetadata(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            parameter_schema=data["schema"],
            auth_type=AuthType(data["auth_type"]),
            embedding=embedding,
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
        try:
            await self.embedding_service.initialize()
            logger.info("RAG retriever initialized successfully")
        except Exception as e:
            logger.warning(f"RAG retriever initialized in degraded mode: {e}")
    
    def _calculate_cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector (can be list or string)
            vec2: Second vector (can be list or string)
            
        Returns:
            float: Cosine similarity score between 0 and 1
        """
        import json
        
        if not vec1 or not vec2:
            return 0.0
        
        # Parse vectors if they're strings
        if isinstance(vec1, str):
            try:
                vec1 = json.loads(vec1)
            except (json.JSONDecodeError, TypeError):
                return 0.0
                
        if isinstance(vec2, str):
            try:
                vec2 = json.loads(vec2)
            except (json.JSONDecodeError, TypeError):
                return 0.0
            
        # Convert to lists if they're not already
        if not isinstance(vec1, list):
            vec1 = list(vec1)
        if not isinstance(vec2, list):
            vec2 = list(vec2)
            
        # Ensure vectors are the same length
        if len(vec1) != len(vec2):
            # Pad the shorter vector with zeros
            if len(vec1) < len(vec2):
                vec1 = vec1 + [0.0] * (len(vec2) - len(vec1))
            else:
                vec2 = vec2 + [0.0] * (len(vec1) - len(vec2))
        
        try:
            # Calculate dot product
            dot_product = sum(float(a) * float(b) for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = sum(float(a) * float(a) for a in vec1) ** 0.5
            magnitude2 = sum(float(b) * float(b) for b in vec2) ** 0.5
            
            # Avoid division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
                
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Ensure the result is between 0 and 1
            return max(0.0, min(1.0, similarity))
            
        except (TypeError, ValueError) as e:
            logger.warning(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    @handle_database_errors("retrieve_connectors")
    @log_function_performance("retrieve_connectors")
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
            db = await get_database()
            
            # Check if embedding service is available
            if self.embedding_service._client is None:
                logger.warning("Embedding service not available, falling back to text search")
                # Fallback to simple text search
                query_builder = db.table("connectors").select("*").eq("is_active", True)
                
                # Add category filter if specified
                if category_filter:
                    query_builder = query_builder.eq("category", category_filter)
                
                # Simple text search in name and description
                result = query_builder.or_(
                    f"name.ilike.%{query}%,description.ilike.%{query}%"
                ).order("usage_count", desc=True).limit(limit).execute()
                
                connectors = []
                for row in result.data:
                    connector = self.metadata_manager._convert_to_connector_metadata(row)
                    connectors.append(connector)
                
                logger.info(f"Retrieved {len(connectors)} connectors using text search for query: {query[:100]}...")
                return connectors
            
            # Generate embedding for the query
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Use Supabase RPC function for vector similarity search
            # This avoids URL length limits by using POST instead of GET
            # For Supabase, we need to use a different approach since we can't use custom SQL functions
            # We'll use a POST request with the embedding data in the body instead of URL
            try:
                # Use the Supabase Filter API to get all connectors first
                # Then we'll do the vector similarity calculation in Python
                query_builder = db.table("connectors").select("*").eq("is_active", True).not_.is_("embedding", None)
                
                # Add category filter if specified
                if category_filter:
                    query_builder = query_builder.eq("category", category_filter)
                
                # Execute the query
                result = query_builder.execute()
                
                if not result.data:
                    logger.info("No connectors found in database")
                    return []
                
                # Calculate similarity scores in Python
                connectors_with_scores = []
                for row in result.data:
                    # Get the embedding from the row
                    connector_embedding = row.get("embedding")
                    
                    if connector_embedding:
                        # Calculate cosine similarity
                        similarity_score = self._calculate_cosine_similarity(query_embedding, connector_embedding)
                        
                        if similarity_score >= similarity_threshold:
                            connectors_with_scores.append((row, similarity_score))
                
                # Sort by similarity score (highest first)
                connectors_with_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Take the top 'limit' results
                top_connectors = connectors_with_scores[:limit]
                
                # Convert to connector objects
                connectors = []
                for row, score in top_connectors:
                    connector = self.metadata_manager._convert_to_connector_metadata(row)
                    connectors.append(connector)
                
                # Update usage counts for retrieved connectors
                for connector in connectors:
                    await self.metadata_manager.update_usage_count(connector.name)
                
                logger.info(f"Retrieved {len(connectors)} connectors using Python vector similarity")
                return connectors
                
            except Exception as vector_error:
                logger.warning(f"Vector similarity search failed: {vector_error}, falling back to text search")
                
                # Fallback to text search if vector search fails
                query_builder = db.table("connectors").select("*").eq("is_active", True)
                
                # Add category filter if specified
                if category_filter:
                    query_builder = query_builder.eq("category", category_filter)
                
                # Simple text search in name and description
                result = query_builder.or_(
                    f"name.ilike.%{query}%,description.ilike.%{query}%"
                ).order("usage_count", desc=True).limit(limit).execute()
                
                # Convert results
                connectors = []
                for row in result.data:
                    connector = self.metadata_manager._convert_to_connector_metadata(row)
                    connectors.append(connector)
                
                # Update usage counts for retrieved connectors
                for connector in connectors:
                    await self.metadata_manager.update_usage_count(connector.name)
                
                logger.info(f"Retrieved {len(connectors)} connectors using text search fallback")
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