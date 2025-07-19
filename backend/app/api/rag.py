"""
RAG system API endpoints for connector retrieval.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.rag import get_rag_retriever, RAGRetriever
from app.models.connector import ConnectorMetadata
from app.core.exceptions import RAGError, EmbeddingError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG System"])


class ConnectorSearchRequest(BaseModel):
    """Request model for connector search."""
    query: str
    limit: int = 10
    category_filter: Optional[str] = None
    similarity_threshold: float = 0.7


class ConnectorSearchResponse(BaseModel):
    """Response model for connector search."""
    query: str
    connectors: List[ConnectorMetadata]
    total_found: int
    search_time_ms: float


class ConnectorCategoriesResponse(BaseModel):
    """Response model for connector categories."""
    categories: List[str]
    total_connectors: int


@router.post("/search", response_model=ConnectorSearchResponse)
async def search_connectors(
    request: ConnectorSearchRequest,
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Search for connectors using semantic similarity.
    
    This endpoint uses the RAG system to find connectors that are semantically
    similar to the user's query. Results are ranked by relevance.
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Searching connectors for query: '{request.query}'")
        
        # Perform semantic search
        connectors = await rag_retriever.retrieve_connectors(
            query=request.query,
            limit=request.limit,
            category_filter=request.category_filter,
            similarity_threshold=request.similarity_threshold
        )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"Found {len(connectors)} connectors in {search_time:.2f}ms")
        
        return ConnectorSearchResponse(
            query=request.query,
            connectors=connectors,
            total_found=len(connectors),
            search_time_ms=search_time
        )
        
    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except RAGError as e:
        logger.error(f"RAG system error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Search system error. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in connector search: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during search."
        )


@router.get("/search", response_model=ConnectorSearchResponse)
async def search_connectors_get(
    query: str = Query(..., description="Search query for connectors"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold"),
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Search for connectors using GET request (for simple queries).
    """
    request = ConnectorSearchRequest(
        query=query,
        limit=limit,
        category_filter=category,
        similarity_threshold=threshold
    )
    return await search_connectors(request, rag_retriever)


@router.get("/connectors/popular", response_model=List[ConnectorMetadata])
async def get_popular_connectors(
    limit: int = Query(10, ge=1, le=50, description="Number of popular connectors to return"),
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Get the most popular connectors based on usage count.
    """
    try:
        logger.info(f"Fetching {limit} popular connectors")
        
        connectors = await rag_retriever.get_popular_connectors(limit=limit)
        
        logger.info(f"Retrieved {len(connectors)} popular connectors")
        return connectors
        
    except RAGError as e:
        logger.error(f"Failed to get popular connectors: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve popular connectors."
        )


@router.get("/connectors/category/{category}", response_model=List[ConnectorMetadata])
async def get_connectors_by_category(
    category: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Get connectors filtered by category.
    """
    try:
        logger.info(f"Fetching connectors for category: {category}")
        
        connectors = await rag_retriever.retrieve_connectors_by_category(
            category=category,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(connectors)} connectors for category {category}")
        return connectors
        
    except RAGError as e:
        logger.error(f"Failed to get connectors by category: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve connectors for category: {category}"
        )


@router.get("/categories", response_model=ConnectorCategoriesResponse)
async def get_connector_categories(
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Get all available connector categories.
    """
    try:
        logger.info("Fetching connector categories")
        
        # Get all connectors to extract categories
        all_connectors = await rag_retriever.metadata_manager.get_all_connectors()
        
        # Extract unique categories
        categories = list(set(conn.category for conn in all_connectors))
        categories.sort()
        
        logger.info(f"Found {len(categories)} categories")
        
        return ConnectorCategoriesResponse(
            categories=categories,
            total_connectors=len(all_connectors)
        )
        
    except RAGError as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve connector categories."
        )


@router.get("/connectors/{connector_name}", response_model=ConnectorMetadata)
async def get_connector_details(
    connector_name: str,
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Get detailed information about a specific connector.
    """
    try:
        logger.info(f"Fetching details for connector: {connector_name}")
        
        connector = await rag_retriever.metadata_manager.get_connector_by_name(connector_name)
        
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found."
            )
        
        logger.info(f"Retrieved details for connector: {connector_name}")
        return connector
        
    except HTTPException:
        raise
    except RAGError as e:
        logger.error(f"Failed to get connector details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve connector details: {connector_name}"
        )


@router.post("/admin/update-embeddings")
async def update_connector_embeddings(
    connector_names: Optional[List[str]] = None,
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Admin endpoint to update connector embeddings.
    Use this when connector descriptions change or to reprocess embeddings.
    """
    try:
        logger.info("Updating connector embeddings...")
        
        await rag_retriever.update_connector_embeddings(connector_names)
        
        count = len(connector_names) if connector_names else "all"
        logger.info(f"Updated embeddings for {count} connectors")
        
        return {
            "message": f"Successfully updated embeddings for {count} connectors",
            "updated_connectors": connector_names or "all"
        }
        
    except EmbeddingError as e:
        logger.error(f"Failed to update embeddings: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable for embedding updates."
        )
    except RAGError as e:
        logger.error(f"Failed to update embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update connector embeddings."
        )


@router.get("/health")
async def rag_health_check(
    rag_retriever: RAGRetriever = Depends(get_rag_retriever)
):
    """
    Health check endpoint for the RAG system.
    """
    try:
        # Test a simple search to verify the system is working
        test_connectors = await rag_retriever.retrieve_connectors("test", limit=1)
        
        return {
            "status": "healthy",
            "embedding_service": "operational",
            "database": "connected",
            "total_connectors": len(await rag_retriever.metadata_manager.get_all_connectors())
        }
        
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="RAG system is not healthy"
        )