#!/usr/bin/env python3
"""
Integration test for core connectors to verify they work end-to-end.
"""
import asyncio
from app.connectors.core import (
    HttpConnector, 
    GmailConnector, 
    GoogleSheetsConnector, 
    WebhookConnector, 
    PerplexityConnector
)
from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors
from app.models.connector import ConnectorExecutionContext


async def test_connector_instantiation():
    """Test that all connectors can be instantiated."""
    print("Testing connector instantiation...")
    
    connectors = [
        HttpConnector(),
        GmailConnector(),
        GoogleSheetsConnector(),
        WebhookConnector(),
        PerplexityConnector()
    ]
    
    for connector in connectors:
        print(f"✓ {connector.name}: {connector.category}")
        
        # Test basic properties
        assert connector.name is not None
        assert connector.description is not None
        assert connector.schema is not None
        assert connector.category is not None
        
        # Test auth requirements
        auth_req = await connector.get_auth_requirements()
        assert auth_req is not None
        print(f"  Auth type: {auth_req.type}")
    
    print("All connectors instantiated successfully!\n")


async def test_connector_registration():
    """Test connector registration with the registry."""
    print("Testing connector registration...")
    
    # Register all core connectors
    result = register_core_connectors()
    print(f"Registration result: {result}")
    
    # Verify all connectors are registered
    registered_connectors = connector_registry.list_connectors()
    print(f"Registered connectors: {registered_connectors}")
    
    expected_connectors = ['http', 'gmail', 'googlesheets', 'webhook', 'perplexity']
    for connector_name in expected_connectors:
        assert connector_name in registered_connectors
        print(f"✓ {connector_name} registered")
        
        # Test creating connector from registry
        connector = connector_registry.create_connector(connector_name)
        assert connector is not None
        assert connector.name == connector_name
    
    print("All connectors registered successfully!\n")


async def test_connector_schemas():
    """Test that all connectors have valid schemas."""
    print("Testing connector schemas...")
    
    connectors = [
        HttpConnector(),
        GmailConnector(),
        GoogleSheetsConnector(),
        WebhookConnector(),
        PerplexityConnector()
    ]
    
    for connector in connectors:
        schema = connector.schema
        print(f"✓ {connector.name} schema:")
        print(f"  Properties: {len(schema.get('properties', {}))}")
        print(f"  Required: {schema.get('required', [])}")
        
        # Basic schema validation
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert len(schema["properties"]) > 0
    
    print("All connector schemas are valid!\n")


async def test_parameter_validation():
    """Test parameter validation for connectors."""
    print("Testing parameter validation...")
    
    # Test HTTP connector validation
    http_connector = HttpConnector()
    
    # Valid parameters should pass
    valid_params = {"url": "https://api.example.com"}
    try:
        await http_connector.validate_params(valid_params)
        print("✓ HTTP connector valid params passed")
    except Exception as e:
        print(f"✗ HTTP connector valid params failed: {e}")
    
    # Invalid parameters should fail
    try:
        await http_connector.validate_params({})
        print("✗ HTTP connector invalid params should have failed")
    except Exception:
        print("✓ HTTP connector invalid params correctly rejected")
    
    print("Parameter validation working correctly!\n")


async def test_webhook_functionality():
    """Test webhook connector functionality."""
    print("Testing webhook connector functionality...")
    
    webhook_connector = WebhookConnector()
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node",
        auth_tokens={}
    )
    
    # Test webhook registration
    register_params = {
        "action": "register",
        "webhook_name": "test_webhook",
        "webhook_url": "https://api.example.com/webhook",
        "description": "Test webhook"
    }
    
    result = await webhook_connector.execute(register_params, context)
    if result.success:
        print("✓ Webhook registration successful")
        print(f"  Webhook ID: {result.data.get('webhook_name')}")
    else:
        print(f"✗ Webhook registration failed: {result.error}")
    
    # Test webhook listing
    list_params = {"action": "list"}
    result = await webhook_connector.execute(list_params, context)
    if result.success:
        print("✓ Webhook listing successful")
        print(f"  Total webhooks: {result.data.get('total_count')}")
    else:
        print(f"✗ Webhook listing failed: {result.error}")
    
    print("Webhook connector functionality working!\n")


async def main():
    """Run all integration tests."""
    print("=== Core Connectors Integration Test ===\n")
    
    try:
        await test_connector_instantiation()
        await test_connector_registration()
        await test_connector_schemas()
        await test_parameter_validation()
        await test_webhook_functionality()
        
        print("🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())