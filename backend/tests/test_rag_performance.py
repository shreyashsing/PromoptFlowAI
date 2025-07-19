"""
Performance tests for the RAG system.
Tests retrieval speed, accuracy, and concurrent usage scenarios.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from app.services.rag import RAGRetriever, EmbeddingService
from app.models.connector import ConnectorMetadata
from app.models.base import AuthType


class TestRAGPerformance:
    """Performance test cases for the RAG system."""
    
    @pytest.fixture
    def mock_rag_retriever(self):
        """Create a mock RAG retriever for performance testing."""
        retriever = RAGRetriever()
        retriever.embedding_service = Mock(spec=EmbeddingService)
        retriever.embedding_service._initialized = True
        retriever.embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        
        retriever.metadata_manager = Mock()
        retriever.metadata_manager.update_usage_count = AsyncMock()
        
        return retriever
    
    @pytest.fixture
    def large_connector_dataset(self):
        """Create a large dataset of connectors for performance testing."""
        connectors = []
        categories = ["data_sources", "communication", "ai_services", "logic", "triggers"]
        
        for i in range(1000):  # 1000 connectors
            connector = ConnectorMetadata(
                name=f"connector_{i}",
                description=f"Test connector {i} for performance testing with various capabilities",
                category=categories[i % len(categories)],
                parameter_schema={"type": "object", "properties": {"param": {"type": "string"}}},
                auth_type=AuthType.API_KEY if i % 2 == 0 else AuthType.OAUTH2,
                usage_count=i % 100  # Varying usage counts
            )
            connectors.append(connector)
        
        return connectors
    
    def create_mock_database_with_large_dataset(self, connectors: List[ConnectorMetadata]):
        """Create a mock database with large connector dataset."""
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        # Convert connectors to database format
        db_data = []
        for i, conn in enumerate(connectors):
            db_data.append({
                "name": conn.name,
                "description": conn.description,
                "category": conn.category,
                "schema": conn.parameter_schema,
                "auth_type": conn.auth_type.value,
                "embedding": [0.1 + (i * 0.001)] * 1536,  # Slightly different embeddings
                "usage_count": conn.usage_count,
                "similarity": 0.1 + (i * 0.001),  # Varying similarity scores
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            })
        
        mock_result = Mock()
        mock_result.data = db_data[:50]  # Return top 50 results
        
        query_builder = Mock()
        query_builder.eq.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.execute.return_value = mock_result
        
        mock_table.select.return_value = query_builder
        
        return mock_db
    
    @pytest.mark.asyncio
    async def test_single_query_performance(self, mock_rag_retriever, large_connector_dataset):
        """Test performance of a single similarity search query."""
        mock_db = self.create_mock_database_with_large_dataset(large_connector_dataset)
        
        # Mock connector conversion
        mock_connector = Mock()
        mock_connector.name = "test_connector"
        mock_rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            start_time = time.time()
            
            results = await mock_rag_retriever.retrieve_connectors(
                "send email notification", 
                limit=10
            )
            
            end_time = time.time()
            query_time = end_time - start_time
            
            # Performance assertion: query should complete within 1 second
            assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"
            assert len(results) <= 10
    
    @pytest.mark.asyncio
    async def test_concurrent_queries_performance(self, mock_rag_retriever, large_connector_dataset):
        """Test performance under concurrent query load."""
        mock_db = self.create_mock_database_with_large_dataset(large_connector_dataset)
        
        mock_connector = Mock()
        mock_connector.name = "test_connector"
        mock_rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        queries = [
            "send email",
            "read spreadsheet",
            "make HTTP request",
            "AI text generation",
            "schedule workflow",
            "process webhook",
            "analyze data",
            "send notification",
            "backup files",
            "generate report"
        ]
        
        async def run_query(query: str):
            """Run a single query and measure time."""
            start_time = time.time()
            results = await mock_rag_retriever.retrieve_connectors(query, limit=5)
            end_time = time.time()
            return end_time - start_time, len(results)
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            start_time = time.time()
            
            # Run 10 concurrent queries
            tasks = [run_query(query) for query in queries]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance assertions
            assert total_time < 5.0, f"Concurrent queries took {total_time:.3f}s, expected < 5.0s"
            
            # Check individual query times
            for i, (query_time, result_count) in enumerate(results):
                assert query_time < 2.0, f"Query {i} took {query_time:.3f}s, expected < 2.0s"
                assert result_count <= 5
    
    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self, mock_rag_retriever):
        """Test performance of batch embedding generation."""
        # Mock batch embedding generation
        mock_rag_retriever.embedding_service.generate_embeddings_batch = AsyncMock()
        
        # Create large batch of texts
        texts = [f"Test connector {i} description" for i in range(100)]
        
        start_time = time.time()
        
        # Mock return embeddings
        mock_embeddings = [[0.1] * 1536 for _ in range(100)]
        mock_rag_retriever.embedding_service.generate_embeddings_batch.return_value = mock_embeddings
        
        result = await mock_rag_retriever.embedding_service.generate_embeddings_batch(texts)
        
        end_time = time.time()
        batch_time = end_time - start_time
        
        # Performance assertion: batch processing should be efficient
        assert batch_time < 2.0, f"Batch embedding took {batch_time:.3f}s, expected < 2.0s"
        assert len(result) == 100
    
    @pytest.mark.asyncio
    async def test_similarity_search_accuracy(self, mock_rag_retriever):
        """Test accuracy of similarity search results."""
        # Create mock database with known similar connectors
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        
        # Mock results with varying similarity scores
        mock_result = Mock()
        mock_result.data = [
            {
                "name": "gmail_connector",
                "description": "Send and receive emails through Gmail",
                "category": "communication",
                "schema": {"type": "object"},
                "auth_type": "oauth2",
                "embedding": [0.1] * 1536,
                "usage_count": 50,
                "similarity": 0.1,  # High similarity (low distance)
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "slack_messenger",
                "description": "Send messages to Slack channels",
                "category": "communication", 
                "schema": {"type": "object"},
                "auth_type": "oauth2",
                "embedding": [0.2] * 1536,
                "usage_count": 30,
                "similarity": 0.2,  # Medium similarity
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "file_processor",
                "description": "Process and analyze files",
                "category": "data_processing",
                "schema": {"type": "object"},
                "auth_type": "api_key",
                "embedding": [0.8] * 1536,
                "usage_count": 10,
                "similarity": 0.8,  # Low similarity (high distance)
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        query_builder = Mock()
        query_builder.eq.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.execute.return_value = mock_result
        
        mock_table.select.return_value = query_builder
        
        # Mock connector conversion
        def mock_convert(data):
            mock_conn = Mock()
            mock_conn.name = data["name"]
            mock_conn.category = data["category"]
            return mock_conn
        
        mock_rag_retriever.metadata_manager._convert_to_connector_metadata.side_effect = mock_convert
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            results = await mock_rag_retriever.retrieve_connectors(
                "send email notification",
                limit=10,
                similarity_threshold=0.5  # Filter out low similarity results
            )
            
            # Accuracy assertions
            assert len(results) == 2  # Should exclude the file_processor (low similarity)
            
            # Results should be ordered by similarity (most similar first)
            assert results[0].name == "gmail_connector"
            assert results[1].name == "slack_messenger"
            
            # Both results should be communication-related
            assert all(conn.category == "communication" for conn in results)
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_dataset(self, mock_rag_retriever, large_connector_dataset):
        """Test memory usage with large connector dataset."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        mock_db = self.create_mock_database_with_large_dataset(large_connector_dataset)
        
        mock_connector = Mock()
        mock_connector.name = "test_connector"
        mock_rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            # Run multiple queries to test memory usage
            for i in range(50):
                await mock_rag_retriever.retrieve_connectors(f"test query {i}", limit=10)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage should not increase significantly
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, expected < 100MB"
    
    @pytest.mark.asyncio
    async def test_category_filter_performance(self, mock_rag_retriever, large_connector_dataset):
        """Test performance of category-filtered queries."""
        mock_db = self.create_mock_database_with_large_dataset(large_connector_dataset)
        
        mock_connector = Mock()
        mock_connector.name = "test_connector"
        mock_rag_retriever.metadata_manager._convert_to_connector_metadata.return_value = mock_connector
        
        with patch('app.services.rag.get_database', return_value=mock_db):
            start_time = time.time()
            
            results = await mock_rag_retriever.retrieve_connectors(
                "process data",
                limit=10,
                category_filter="data_sources"
            )
            
            end_time = time.time()
            query_time = end_time - start_time
            
            # Category-filtered queries should be fast
            assert query_time < 0.5, f"Category-filtered query took {query_time:.3f}s, expected < 0.5s"
            assert len(results) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])