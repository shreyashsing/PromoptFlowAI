"""
Registration module for core connectors.

This module handles the registration of all core connectors with the
connector registry system.
"""
import logging
from app.connectors.registry import connector_registry
from app.connectors.core import (
    HttpConnector,
    GmailConnector,
    GoogleSheetsConnector,
    WebhookConnector,
    PerplexityConnector
)
from app.connectors.core.text_summarizer_connector import TextSummarizerConnector
from app.connectors.core.parallel_execution_connector import ParallelExecutionConnector

logger = logging.getLogger(__name__)


def register_core_connectors():
    """
    Register all core connectors with the connector registry.
    
    This function should be called during application startup to ensure
    all core connectors are available for use.
    """
    connectors_to_register = [
        HttpConnector,
        GmailConnector,
        GoogleSheetsConnector,
        WebhookConnector,
        PerplexityConnector,
        TextSummarizerConnector,
        ParallelExecutionConnector
    ]
    
    registered_count = 0
    failed_count = 0
    
    for connector_class in connectors_to_register:
        try:
            connector_registry.register(connector_class)
            registered_count += 1
            logger.info(f"Successfully registered connector: {connector_class.__name__}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to register connector {connector_class.__name__}: {str(e)}")
    
    logger.info(f"Core connector registration complete: {registered_count} successful, {failed_count} failed")
    
    return {
        "registered": registered_count,
        "failed": failed_count,
        "total": len(connectors_to_register)
    }


def get_core_connector_info():
    """
    Get information about all core connectors.
    
    Returns:
        Dictionary with connector information
    """
    return {
        "http": {
            "name": "HTTP Request Connector",
            "description": "Make HTTP requests to REST APIs with full method support",
            "category": "data_sources",
            "auth_types": ["none", "api_key", "basic"]
        },
        "gmail": {
            "name": "Gmail Connector", 
            "description": "Send and receive emails through Gmail API with OAuth",
            "category": "communication",
            "auth_types": ["oauth"]
        },
        "googlesheets": {
            "name": "Google Sheets Connector",
            "description": "Read, write, and manage Google Sheets data with full CRUD operations",
            "category": "data_sources", 
            "auth_types": ["oauth"]
        },
        "webhook": {
            "name": "Webhook Connector",
            "description": "Receive and process external events through webhooks",
            "category": "triggers",
            "auth_types": ["none", "signature"]
        },
        "perplexity": {
            "name": "Perplexity AI Connector",
            "description": "Real-time web-augmented QA and grounded search using Perplexity AI",
            "category": "ai_services",
            "auth_types": ["api_key"]
        }
    }


def validate_core_connectors():
    """
    Validate that all core connectors are properly registered and functional.
    
    Returns:
        Dictionary with validation results
    """
    core_connectors = list(get_core_connector_info().keys())
    validation_results = {}
    
    for connector_name in core_connectors:
        try:
            # Check if connector is registered
            if not connector_registry.is_registered(connector_name):
                validation_results[connector_name] = {
                    "status": "failed",
                    "error": "Connector not registered"
                }
                continue
            
            # Try to create connector instance
            connector = connector_registry.create_connector(connector_name)
            
            # Basic validation
            assert connector.name == connector_name
            assert connector.description is not None
            assert connector.schema is not None
            assert connector.category is not None
            
            validation_results[connector_name] = {
                "status": "passed",
                "name": connector.name,
                "category": connector.category,
                "schema_properties": len(connector.schema.get("properties", {}))
            }
            
        except Exception as e:
            validation_results[connector_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    return validation_results


if __name__ == "__main__":
    # Register connectors when run directly
    result = register_core_connectors()
    print(f"Registration result: {result}")
    
    # Validate connectors
    validation = validate_core_connectors()
    print(f"Validation results: {validation}")