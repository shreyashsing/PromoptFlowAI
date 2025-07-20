"""
Connector registry for managing available connectors.
"""
import logging
import inspect
from typing import Dict, List, Type, Optional, Set
from app.connectors.base import BaseConnector
from app.models.connector import ConnectorMetadata
from app.core.exceptions import ConnectorException, ValidationException


logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing and discovering available connectors.
    
    This class maintains a registry of all available connectors and provides
    methods for registration, discovery, and instantiation with validation.
    """
    
    def __init__(self):
        self._connectors: Dict[str, Type[BaseConnector]] = {}
        self._metadata: Dict[str, ConnectorMetadata] = {}
        self._categories: Dict[str, Set[str]] = {}  # category -> set of connector names
    
    def register(self, connector_class: Type[BaseConnector]) -> None:
        """
        Register a connector class in the registry with validation.
        
        Args:
            connector_class: The connector class to register
            
        Raises:
            ConnectorException: If connector is invalid or already registered
            ValidationException: If connector doesn't meet requirements
        """
        # Validate that it's a proper connector class
        if not inspect.isclass(connector_class):
            raise ValidationException("Connector must be a class")
        
        if not issubclass(connector_class, BaseConnector):
            raise ValidationException("Connector must inherit from BaseConnector")
        
        # Check if all abstract methods are implemented
        try:
            temp_instance = connector_class()
        except TypeError as e:
            raise ValidationException(f"Connector class is not properly implemented: {str(e)}")
        
        name = temp_instance.name
        
        if not name:
            raise ValidationException("Connector name cannot be empty")
        
        if name in self._connectors:
            raise ConnectorException(f"Connector '{name}' is already registered")
        
        # Validate connector implementation
        # Note: This should be called in an async context, but for registration we'll skip async validation
        # The validation will happen during actual connector usage
        
        # Register the connector
        self._connectors[name] = connector_class
        
        # Create metadata for RAG system
        # Note: Auth requirements will be determined at runtime
        auth_type = "none"  # Default, will be updated when connector is used
        
        metadata = ConnectorMetadata(
            name=name,
            description=temp_instance.description,
            category=temp_instance.category,
            parameter_schema=temp_instance.schema,
            auth_type=auth_type
        )
        self._metadata[name] = metadata
        
        # Update category index
        category = temp_instance.category
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(name)
        
        logger.info(f"Registered connector: {name} (category: {category})")
    
    async def _validate_connector_implementation(self, connector: BaseConnector) -> None:
        """
        Validate that a connector implementation meets requirements.
        
        Args:
            connector: Connector instance to validate
            
        Raises:
            ValidationException: If connector implementation is invalid
        """
        # Check required properties
        if not connector.name:
            raise ValidationException("Connector must have a non-empty name")
        
        if not connector.description:
            raise ValidationException("Connector must have a description")
        
        if not connector.schema:
            raise ValidationException("Connector must define a parameter schema")
        
        # Validate schema structure
        if not isinstance(connector.schema, dict):
            raise ValidationException("Connector schema must be a dictionary")
        
        if "type" not in connector.schema:
            raise ValidationException("Connector schema must have a 'type' field")
        
        # Test auth requirements
        try:
            auth_req = await connector.get_auth_requirements()
            if not hasattr(auth_req, 'type'):
                raise ValidationException("Auth requirements must have a 'type' field")
        except Exception as e:
            raise ValidationException(f"Invalid auth requirements implementation: {str(e)}")
    
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
            available = ", ".join(self.list_connectors())
            raise ConnectorException(f"Connector '{name}' not found. Available: {available}")
        
        return self._connectors[name]
    
    def create_connector(self, name: str) -> BaseConnector:
        """
        Create a new instance of a connector.
        
        Args:
            name: Name of the connector
            
        Returns:
            New connector instance
            
        Raises:
            ConnectorException: If connector not found or cannot be instantiated
        """
        connector_class = self.get_connector(name)
        
        try:
            return connector_class()
        except Exception as e:
            raise ConnectorException(f"Failed to create connector '{name}': {str(e)}")
    
    def list_connectors(self) -> List[str]:
        """
        List all registered connector names.
        
        Returns:
            List of connector names sorted alphabetically
        """
        return sorted(self._connectors.keys())
    
    def list_connectors_by_category(self, category: str) -> List[str]:
        """
        List connectors in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of connector names in the category
        """
        return sorted(self._categories.get(category, set()))
    
    def list_categories(self) -> List[str]:
        """
        List all available connector categories.
        
        Returns:
            List of category names
        """
        return sorted(self._categories.keys())
    
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
            List of ConnectorMetadata objects sorted by name
        """
        return sorted(self._metadata.values(), key=lambda x: x.name)
    
    def search_connectors(self, query: str) -> List[str]:
        """
        Search for connectors by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching connector names
        """
        query_lower = query.lower()
        matches = []
        
        for name, metadata in self._metadata.items():
            if (query_lower in name.lower() or 
                query_lower in metadata.description.lower() or
                query_lower in metadata.category.lower()):
                matches.append(name)
        
        return sorted(matches)
    
    def unregister(self, name: str) -> None:
        """
        Unregister a connector from the registry.
        
        Args:
            name: Name of the connector to unregister
            
        Raises:
            ConnectorException: If connector not found
        """
        if name not in self._connectors:
            raise ConnectorException(f"Connector '{name}' not found")
        
        # Remove from main registry
        del self._connectors[name]
        
        # Remove metadata
        metadata = self._metadata.pop(name, None)
        
        # Remove from category index
        if metadata and metadata.category in self._categories:
            self._categories[metadata.category].discard(name)
            # Remove empty categories
            if not self._categories[metadata.category]:
                del self._categories[metadata.category]
        
        logger.info(f"Unregistered connector: {name}")
    
    def get_connector_count(self) -> int:
        """Get the total number of registered connectors."""
        return len(self._connectors)
    
    def is_registered(self, name: str) -> bool:
        """Check if a connector is registered."""
        return name in self._connectors


# Global connector registry instance
connector_registry = ConnectorRegistry()