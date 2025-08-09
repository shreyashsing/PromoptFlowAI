"""
API endpoints for connector metadata and AI-friendly information.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from app.connectors.registry import get_connector_registry
from app.core.exceptions import ConnectorException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/connectors", tags=["connector-metadata"])


@router.get("/metadata")
async def get_all_connector_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Get AI-friendly metadata for all registered connectors.
    
    Returns:
        Dictionary mapping connector names to their enhanced metadata
    """
    try:
        registry = get_connector_registry()
        return registry.get_all_ai_metadata()
    except Exception as e:
        logger.error(f"Failed to get connector metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connector metadata")


@router.get("/metadata/{connector_name}")
async def get_connector_metadata(connector_name: str) -> Dict[str, Any]:
    """
    Get AI-friendly metadata for a specific connector.
    
    Args:
        connector_name: Name of the connector
        
    Returns:
        Enhanced metadata for the connector
    """
    try:
        registry = get_connector_registry()
        return registry.get_ai_metadata(connector_name)
    except ConnectorException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get metadata for {connector_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connector metadata")


@router.get("/search")
async def search_connectors(
    query: str = Query(..., description="Search query for connectors"),
    capability: Optional[str] = Query(None, description="Filter by capability")
) -> List[Dict[str, Any]]:
    """
    Search for connectors based on query and optional capability filter.
    
    Args:
        query: Search query (natural language)
        capability: Optional capability filter (e.g., "read", "write", "search")
        
    Returns:
        List of relevant connectors with metadata and relevance scores
    """
    try:
        registry = get_connector_registry()
        
        if capability:
            # Filter by capability first
            matching_names = registry.search_by_capability(capability)
            results = []
            
            for name in matching_names:
                try:
                    metadata = registry.get_ai_metadata(name)
                    # Calculate basic relevance for query
                    score = 0
                    query_lower = query.lower()
                    
                    if name.lower() in query_lower:
                        score += 10
                    if metadata["category"].lower() in query_lower:
                        score += 5
                    
                    metadata["relevance_score"] = score
                    results.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {name}: {str(e)}")
            
            # Sort by relevance
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return results
        else:
            # Use the registry's intelligent search
            return registry.get_connectors_for_prompt(query)
            
    except Exception as e:
        logger.error(f"Failed to search connectors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search connectors")


@router.get("/capabilities")
async def get_connector_capabilities() -> Dict[str, List[str]]:
    """
    Get all available capabilities across connectors.
    
    Returns:
        Dictionary mapping capabilities to lists of connector names
    """
    try:
        registry = get_connector_registry()
        capabilities_map = {}
        
        for name in registry.list_connectors():
            try:
                connector = registry.create_connector(name)
                connector_capabilities = connector.get_capabilities()
                
                for capability in connector_capabilities:
                    if capability not in capabilities_map:
                        capabilities_map[capability] = []
                    capabilities_map[capability].append(name)
                    
            except Exception as e:
                logger.warning(f"Failed to get capabilities for {name}: {str(e)}")
        
        return capabilities_map
        
    except Exception as e:
        logger.error(f"Failed to get capabilities: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve capabilities")


@router.get("/categories")
async def get_connector_categories() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get connectors organized by category with basic metadata.
    
    Returns:
        Dictionary mapping categories to lists of connector metadata
    """
    try:
        registry = get_connector_registry()
        categories_map = {}
        
        for category in registry.list_categories():
            connector_names = registry.list_connectors_by_category(category)
            category_connectors = []
            
            for name in connector_names:
                try:
                    metadata = registry.get_ai_metadata(name)
                    # Include only essential info for category view
                    category_connectors.append({
                        "name": metadata["name"],
                        "display_name": metadata["display_name"],
                        "description": metadata["description"],
                        "capabilities": metadata["capabilities"],
                        "auth_required": metadata["auth_required"]
                    })
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {name}: {str(e)}")
            
            categories_map[category] = category_connectors
        
        return categories_map
        
    except Exception as e:
        logger.error(f"Failed to get categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@router.post("/suggest-parameters/{connector_name}")
async def suggest_parameters(
    connector_name: str,
    request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get parameter suggestions for a connector based on user prompt.
    
    Args:
        connector_name: Name of the connector
        request: Request body with 'user_prompt' and optional 'context'
        
    Returns:
        Dictionary with suggested parameter values
    """
    try:
        user_prompt = request.get("user_prompt", "")
        context = request.get("context", {})
        
        if not user_prompt:
            raise HTTPException(status_code=400, detail="user_prompt is required")
        
        registry = get_connector_registry()
        connector = registry.create_connector(connector_name)
        
        suggestions = connector.generate_parameter_suggestions(user_prompt, context)
        
        return {
            "connector_name": connector_name,
            "user_prompt": user_prompt,
            "suggested_parameters": suggestions,
            "parameter_hints": connector.get_parameter_hints()
        }
        
    except ConnectorException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to suggest parameters for {connector_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate parameter suggestions")


@router.get("/examples/{connector_name}")
async def get_connector_examples(connector_name: str) -> Dict[str, Any]:
    """
    Get examples and use cases for a specific connector.
    
    Args:
        connector_name: Name of the connector
        
    Returns:
        Dictionary with examples, use cases, and prompts
    """
    try:
        registry = get_connector_registry()
        metadata = registry.get_ai_metadata(connector_name)
        
        return {
            "connector_name": connector_name,
            "example_prompts": metadata["example_prompts"],
            "use_cases": metadata["use_cases"],
            "example_parameters": metadata["example_params"],
            "parameter_hints": metadata["parameter_hints"]
        }
        
    except ConnectorException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get examples for {connector_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connector examples")