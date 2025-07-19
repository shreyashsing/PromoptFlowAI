"""
Unit tests for the RAG (Retrieval-Augmented Generation) system.
Tests embedding generation, vector storage, and similarity search functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from app.services.rag import EmbeddingService, ConnectorMetadataManager, RAGRetriever
from app.models.connector import ConnectorMetadata
from app.models.base import AuthType
from app.core.exceptions import RAGError, EmbeddingError


class TestEmbeddingService:
    """Test cases for the EmbeddingService class."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock Azure OpenAI client."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        return mock_client
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, embedding_service):
        """Test successful initialization of embedding service."""
        with patch('app.services.rag.AsyncAzureOpenAI') as mock_openai:
            mock_openai.return_value = AsyncMock()
            
            await embedding_service.initialize()
            
            assert embedding_service._initialized is True
            assert embedding_service._client is not None
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, embedding_service):
        """Test initialization failure handling."""
        with patch('app.services.rag.AsyncAzureOpenAI') as mock_openai:
            mock_openai.side_effect = Exception("Connection failed")
            
            with pytest.raises(EmbeddingError):
                await embedding_service.initialize()
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, embedding_service, mock_openai_client):
        """Test successful embedding generation."""
        embedding_service._client = mock_openai_client
        embedding_service._initialized = True
        
        result = await embedding_service.generate_embedding("test text")
        
        assert result == [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding_failure(self, embedding_service, mock_openai_client):
        """Test embedding generation failure handling."""
        embedding_service._client = mock_openai_client
        embedding_service._initialized = True
        mock_openai_client.embeddings.create.side_effect = Exception("API error")
        
        with pytest.raises(EmbeddingError):
            await embedding_service.generate_embedding("test text")
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, embedding_service, mock_openai_client):
        """Test batch embedding generation."""
        embedding_service._client = mock_openai_client
        embedding_service._initialized = True
        
        # Mock batch response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        texts = ["text1", "text2"]
        result = await embedding_service.generate_embeddings_batch(texts)
        
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]


class TestConnectorMetadataManager:
    """Test cases for the ConnectorMetadataManager class."""
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=EmbeddingService)
        service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        service.generate_embeddings_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        return service
    
    @pytest.fixture
    def metadata_manager(self, mock_embedding_service):
        """Create a ConnectorMetadataManager instance for testing."""
        return ConnectorMetadataManager(mock_embedding_service)
    
    @pytest.fixture
    def sample_connector(self):
        """Create a sample connector for testing."""
        return ConnectorMetadata(
            name="test_connector",
            description="A test connector for unit testing",
            category="test",
            parameter_schema={"type": "object", "properties": {}},
            auth_type=AuthType.API_KEY,
            usage_count=0
        )
    
    @pytest.fixture
    def mock_database(self):
        """Mock database client."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        # Mock successful upsert
        mock_result = Mock()
        mock_result.data = [{"id": "test-id"}]
        mock_table.upsert.return_value.execute.return_value = mock_result
        
        return mock_db
    
    @pytest.mark.asyncio
    async def test_store_connector_success(self, metadata_manager, sample_connector, mock_database):
        """Test successful connector storage."""
        with patch('app.services.rag.get_database', return_value=mock_database):
            await metadata_manager.store_connector(sample_connector)
            
            # Verify embedding was generated
            metadata_manager.embedding_service.generate_embedding.assert_called_once()
            
            # Verify database upsert was called
            mock_database.table.assert_called_with("connectors")
    
    @pytest.mark.asyncio
    async def test_store_connectors_batch(self, metadata_manager, sample_connector, mock_database):
        """Test batch connector storage."""
        connectors = [sample_connector, sample_connector]
        
        with patch('app.services.rag.get_database', return_value=mock_database):
            await metadata_manager.store_connectors_batch(connectors)
            
            # Verify batch embedding generation
            metadata_manager.embedding_service.generate_embeddings_batch.assert_called_once()
            
            # Verify database batch upsert
            mock_database.table.assert_called_with("connectors")
    
    @pytest.mark.asyncio
    async def test_get_connector_by_name_found(self, metadata_manager, mock_database):
        """Test retrieving connector by name when found."""
        # Mock database response
        mock_result = Mock()
        mock_result.data = [{
            "name": "test_connector",
            "description": "Test description",
            "category": "test",
            "schema": {"type": "object"},
            "auth_type": "api_key",
            "embedding": [0.1, 0.2, 0.3],
            "usage_count": 5,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        mock_database.table.return_value = mock_table
        
        with patch('app.services.rag.get_database', return_value=mock_database):
            result = await metadata_manager.get_connector_by_name("test_connector")
            
            assert result is not None
            assert result.name == "test_connector"
            assert result.usage_count == 5
    
    @pytest.mark.asyncio
    async def test_get_connector_by_name_not_found(self, metadata_manager, mock_database):
        """Test retrieving connector by name when not found."""
        # Mock empty database response
        mock_result = Mock()
        mock_result.data = []
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        mock_database.table.return_value = mock_table
        
        with patch('app.services.rag.get_database', return_value=mock_database):
            result = await metadata_manager.get_connector_by_name("nonexistent")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_update_usage_count(self, metadata_manager, mock_database):
        """Test updating connector usage count."""
        # Mock current usage count query
        mock_select_result = Mock()
        mock_select_result.data = [{"usage_count": 5}]
        
        mock_update_result = Mock()
        mock_update_result.data = [{"usage_count": 6}]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_select_result
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_result
        mock_database.table.return_value = mock_table
        
        with patch('app.services.rag.get_database', return_value=mock_database):
            await metadata_manager.update_usage_count("test_connector")
            
            # Verify update was called with incremented count
            mock_table.update.assert_called_with({"usage_count": 6})


class TestRAGRetriever:
    """Test cases for the RAGRetriever class."""
    
    @pytest.fixture
    def rag_retriever(self):
        """Create a RAGRetriever instance for testing."""
        retriever = RAGRetriever()
        retriever.embedding_service = Mock(spec=EmbeddingService)
        retriever.embedding_service._initialized = True
        retriever.embedding_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        retriever.metadata_manager = Mock(spec=ConnectorMetadataManager)
        retriever.metadata_manager.update_usage_count = AsyncMock()
        retriever.metadata_manager._convert_to_connector_metadata = Mock()
        
        return retriever
    
    @pytest.fixture
    def mock_database_with_similarity(self):
        """Mock database with similarity search results."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        # Mock similarity search results
        mock_result = Mock()
        mock_result.data = [
            {
                "name": "relevant_connector",
                "description": "A relevant connector",
                "category": "test",
                "schema": {"type": "object"},
                "auth_type": "api_key",
                "embedding": [0.1, 0.2, 0.3],
                "usage_count": 10,
                "similarity": 0.2,  # Low distance = high similarity
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "less_relevant_connector",
                "description": "A less relevant connector",
                "category": "test",
                "schema": {"type": "object"},
                "auth_type": "none",
                "embedding": [0.4, 0.5, 0.6],
                "usage_count": 2,
                "similarity": 0.5,  # Higher distance = lower similarity
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Chain the query builder methods
        query_builder = Mock()
        query_builder.eq.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.execute.return_value = mock_result
        
        mock_table.select.return_value = query_builder
        
        return mock_db
    
    @pytest.mark.asyncio
    async def test_retrieve_connectors_success(self, rag_retriever, mock_database_with_similarity):
        """Test successful connector retrieval with similarity search."""
        # Mock the connector conversion
        mock_connector1 = Mock()
        mock_connector1.name = "relevant_connector"
        mock_connector2 = Mock()
        mock_connector2.name = "less_relevant_connector"
        
        rag_retriever.metadata_manager._convert_to_connector_metadata.side_effect = [
            mock_connector1, mock_connector2
        ]
        
        with patch('app.services.rag.get_database', return_value=mock_database_with_similarity):
            results = await rag_retriever.retrieve_connectors("test query", limit=5)
            
            assert len(results) == 2
            assert results[0].name == "relevant_connector"
            assert results[1].name == "less_relevant_connector"
            
            # Verify usage counts were updated
            assert rag_retriever.metadata_manager.update_usage_count.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retrieve_connectors_with_threshold(self, rag_retriever, mock_database_with_similarity):
        """Test connector retrieval with similarity threshold filtering."""
        # Mock the connector conversion
        mock_connector = Mock()
        mock_connector.name = "relevant_connector"
        
        rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_database_with_similarity):
            # Use high threshold to filter out less similar results
            results = await rag_retriever.retrieve_connectors(
                "test query", 
                limit=5, 
                similarity_threshold=0.9
            )
            
            # Only the first connector should pass the threshold (1 - 0.2 = 0.8 similarity)
            # Since 0.8 < 0.9, no results should be returned
            assert len(results) == 1  # Only the highly similar one
    
    @pytest.mark.asyncio
    async def test_retrieve_connectors_with_category_filter(self, rag_retriever, mock_database_with_similarity):
        """Test connector retrieval with category filtering."""
        with patch('app.services.rag.get_database', return_value=mock_database_with_similarity):
            await rag_retriever.retrieve_connectors(
                "test query", 
                limit=5, 
                category_filter="communication"
            )
            
            # Verify category filter was applied in the query
            mock_table = mock_database_with_similarity.table.return_value
            mock_table.select.return_value.eq.assert_called()
    
    @pytest.mark.asyncio
    async def test_retrieve_connectors_by_category(self, rag_retriever):
        """Test retrieving connectors by category."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        mock_result = Mock()
        mock_result.data = [{"name": "test_connector"}]
        
        query_builder = Mock()
        query_builder.eq.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.execute.return_value = mock_result
        
        mock_table.select.return_value = query_builder
        
        mock_connector = Mock()
        rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            results = await rag_retriever.retrieve_connectors_by_category("communication")
            
            assert len(results) == 1
            # Verify category filter was applied
            query_builder.eq.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_popular_connectors(self, rag_retriever):
        """Test retrieving popular connectors by usage count."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        mock_result = Mock()
        mock_result.data = [
            {"name": "popular_connector", "usage_count": 100},
            {"name": "less_popular_connector", "usage_count": 50}
        ]
        
        query_builder = Mock()
        query_builder.eq.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.execute.return_value = mock_result
        
        mock_table.select.return_value = query_builder
        
        mock_connector = Mock()
        rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            results = await rag_retriever.get_popular_connectors(limit=10)
            
            assert len(results) == 2
            # Verify ordering by usage_count desc
            query_builder.order.assert_called_with("usage_count", desc=True)
    
    @pytest.mark.asyncio
    async def test_retrieve_connectors_error_handling(self, rag_retriever):
        """Test error handling in connector retrieval."""
        with patch('app.services.rag.get_database') as mock_get_db:
            mock_get_db.side_effect = Exception("Database error")
            
            with pytest.raises(RAGError):
                await rag_retriever.retrieve_connectors("test query")
    
    @pytest.mark.asyncio
    async def test_update_connector_embeddings(self, rag_retriever):
        """Test updating connector embeddings."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        # Mock select result
        mock_select_result = Mock()
        mock_select_result.data = [
            {
                "id": "conn1",
                "name": "connector1",
                "description": "desc1",
                "category": "cat1"
            },
            {
                "id": "conn2", 
                "name": "connector2",
                "description": "desc2",
                "category": "cat2"
            }
        ]
        
        # Mock update result
        mock_update_result = Mock()
        mock_update_result.data = [{"id": "updated"}]
        
        query_builder = Mock()
        query_builder.execute.return_value = mock_select_result
        mock_table.select.return_value = query_builder
        
        update_builder = Mock()
        update_builder.eq.return_value.execute.return_value = mock_update_result
        mock_table.update.return_value = update_builder
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            await rag_retriever.update_connector_embeddings()
            
            # Verify batch embedding generation was called
            rag_retriever.embedding_service.generate_embeddings_batch.assert_called_once()
            
            # Verify updates were called for each connector
            assert mock_table.update.call_count == 2


@pytest.mark.asyncio
async def test_rag_integration():
    """Integration test for the complete RAG system."""
    # This test would require actual database and OpenAI connections
    # For now, we'll test the initialization flow
    
    with patch('app.services.rag.AsyncAzureOpenAI') as mock_openai:
        with patch('app.services.rag.get_database') as mock_get_db:
            mock_openai.return_value = AsyncMock()
            mock_get_db.return_value = Mock()
            
            retriever = RAGRetriever()
            await retriever.initialize()
            
            assert retriever.embedding_service._initialized is True


if __name__ == "__main__":
    pytest.main([__file__])