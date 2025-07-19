"""
Connector registry for managing available connectors.
"""
from typing import Dict, List, Type
from app.connectors.base import BaseConnector
from app.models.connector import ConnectorMetadata
from app.core.exceptions import ConnectorException


class ConnectorRegistry:
    """
    Registry for managing and discovering available connectors.
    
    This class maintains a registry of all available connectors and provides
    methods for registration, discovery, and instantiation.
    """
    
    def __init__(self):
        self._connectors: Dict[str, Type[BaseConnector]] = {}
        self._metadata: Dict[str, ConnectorMetadata] = {}
    
    def register(self, connector_class: Type[BaseConnector]) -> None:
        """
        Register a connector class in the registry.
        
        Args:
            connector_class: The connector class to register
        """
        # Create a temporary instance to get metadata
        temp_instance = connector_class()
        name = temp_instance.name
        
        if name in self._connectors:
            raise ConnectorException(f"Connector '{name}' is already registered")
        
        self._connectors[name] = connector_class
        
        # Create metadata for RAG system
        metadata = ConnectorMetadata(
            name=name,
            description=temp_instance.description,
            category="general",  # This should be set by individual connectors
            parameter_schema=temp_instance.schema,
            auth_type=temp_instance.get_auth_requirements().type if hasattr(temp_instance, 'get_auth_requirements') else "none"
        )
        self._metadata[name] = metadata
    
    def get_connector(self, name: str) -> Type[BaseConnector]:
        """
        Get a connector class by name.
        
        Args:
            name: Name of the connector
            
        Returns:
            The connector class
            
        Raises:
            ConnectorException: If connector not found
        """
        if name not in self._connectors:
            raise ConnectorException(f"Connector '{name}' not found")
        
        return self._connectors[name]
    
    def list_connectors(self) -> List[str]:
        """
        List all registered connector names.
        
        Returns:
            List of connector names
        """
        return list(self._connectors.keys())
    
    def get_metadata(self, name: str) -> ConnectorMetadata:
        """
        Get metadata for a connector.
        
        Args:
            name: Name of the connector
            
        Returns:
            ConnectorMetadata object
            
        Raises:
            ConnectorException: If connector not found
        """
        if name not in self._metadata:
            raise ConnectorException(f"Connector metadata for '{name}' not found")
        
        return self._metadata[name]
    
    def get_all_metadata(self) -> List[ConnectorMetadata]:
        """
        Get metadata for all registered connectors.
        
        Returns:
            List of ConnectorMetadata objects
        """
        return list(self._metadata.values())


# Global connector registry instance
connector_registry = ConnectorRegistry()