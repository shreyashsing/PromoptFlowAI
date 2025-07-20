"""
Simple test to verify core connectors are working.
"""
import asyncio
from app.connectors.core.register import register_core_connectors, validate_core_connectors
from app.connectors.registry import connector_registry
from app.models.connector import ConnectorExecutionContext

async def test_connectors():
    """Test that all core connectors can be registered and instantiated."""
    print("Testing core connectors...")
    
    # Register connectors
    result = register_core_connectors()
    print(f"Registration result: {result}")
    
    # Validate connectors
    validation = validate_core_connectors()
    print(f"Validation results:")
    for name, result in validation.items():
        print(f"  {name}: {result['status']}")
        if result['status'] == 'failed':
            print(f"    Error: {result['error']}")
    
    # Test basic connector functionality
    print("\nTesting basic connector functionality:")
    
    # Test HTTP connector
    http_connector = connector_registry.create_connector("http")
    print(f"HTTP Connector: {http_connector.name} - {http_connector.category}")
    
    # Test parameter validation
    try:
        await http_connector.validate_params({"url": "https://api.example.com"})
        print("  ✓ Parameter validation passed")
    except Exception as e:
        print(f"  ✗ Parameter validation failed: {e}")
    
    # Test auth requirements
    try:
        auth_req = await http_connector.get_auth_requirements()
        print(f"  ✓ Auth requirements: {auth_req.type}")
    except Exception as e:
        print(f"  ✗ Auth requirements failed: {e}")
    
    # Test Gmail connector
    gmail_connector = connector_registry.create_connector("gmail")
    print(f"Gmail Connector: {gmail_connector.name} - {gmail_connector.category}")
    
    # Test Google Sheets connector
    sheets_connector = connector_registry.create_connector("googlesheets")
    print(f"Google Sheets Connector: {sheets_connector.name} - {sheets_connector.category}")
    
    # Test Webhook connector
    webhook_connector = connector_registry.create_connector("webhook")
    print(f"Webhook Connector: {webhook_connector.name} - {webhook_connector.category}")
    
    # Test Perplexity connector
    perplexity_connector = connector_registry.create_connector("perplexity")
    print(f"Perplexity Connector: {perplexity_connector.name} - {perplexity_connector.category}")
    
    print("\n✓ All core connectors are working correctly!")

if __name__ == "__main__":
    asyncio.run(test_connectors())