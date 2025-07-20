#!/usr/bin/env python3
"""
Test script for the connector framework implementation.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.connectors.base import BaseConnector
from app.connectors.registry import ConnectorRegistry
from app.connectors.result_handler import ConnectorResultHandler
from app.core.oauth import OAuthHelper, OAuthConfig
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType


class TestConnector(BaseConnector):
    """Test connector for framework validation."""
    
    def _get_category(self) -> str:
        return "test"
    
    def _define_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Test message to process"
                }
            },
            "required": ["message"]
        }
    
    async def execute(self, params: dict, context: ConnectorExecutionContext) -> ConnectorResult:
        message = params.get("message", "Hello World")
        return ConnectorResult(
            success=True,
            data={"processed_message": f"Processed: {message}"},
            metadata={"connector": self.name}
        )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        return AuthRequirements(
            type=AuthType.NONE,
            fields={},
            instructions="No authentication required for test connector"
        )


async def test_base_connector():
    """Test BaseConnector functionality."""
    print("Testing BaseConnector...")
    
    connector = TestConnector()
    
    # Test properties
    assert connector.name == "test"
    assert connector.category == "test"
    assert "message" in connector.schema["properties"]
    
    # Test parameter validation
    valid_params = {"message": "test"}
    assert await connector.validate_params(valid_params)
    
    # Test execution
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node"
    )
    
    result = await connector.execute(valid_params, context)
    assert result.success
    assert "processed_message" in result.data
    
    print("✓ BaseConnector tests passed")


async def test_connector_registry():
    """Test ConnectorRegistry functionality."""
    print("Testing ConnectorRegistry...")
    
    registry = ConnectorRegistry()
    
    # Test registration
    registry.register(TestConnector)
    
    # Test retrieval
    connector_class = registry.get_connector("test")
    assert connector_class == TestConnector
    
    # Test instance creation
    connector = registry.create_connector("test")
    assert isinstance(connector, TestConnector)
    
    # Test listing
    connectors = registry.list_connectors()
    assert "test" in connectors
    
    # Test metadata
    metadata = registry.get_metadata("test")
    assert metadata.name == "test"
    assert metadata.category == "test"
    
    print("✓ ConnectorRegistry tests passed")


def test_result_handler():
    """Test ConnectorResultHandler functionality."""
    print("Testing ConnectorResultHandler...")
    
    handler = ConnectorResultHandler()
    
    # Test success result
    success_result = handler.create_success_result(
        data={"test": "data"},
        message="Test successful"
    )
    assert success_result.success
    assert success_result.data["test"] == "data"
    
    # Test error result
    error_result = handler.create_error_result(
        error="Test error",
        data=None
    )
    assert not error_result.success
    assert error_result.error == "Test error"
    
    # Test result validation
    assert handler.validate_result(success_result)
    assert handler.validate_result(error_result)
    
    # Test result merging
    results = [success_result, success_result]
    merged = handler.merge_results(results)
    assert merged.success
    assert len(merged.data) == 2
    
    print("✓ ConnectorResultHandler tests passed")


def test_oauth_helper():
    """Test OAuth helper functionality."""
    print("Testing OAuth helper...")
    
    config = OAuthConfig(
        client_id="test_client",
        client_secret="test_secret",
        authorization_url="https://example.com/auth",
        token_url="https://example.com/token",
        scopes=["read", "write"],
        redirect_uri="http://localhost:8000/callback"
    )
    
    oauth = OAuthHelper(config)
    
    # Test authorization URL generation
    auth_url, state = oauth.generate_authorization_url()
    assert "client_id=test_client" in auth_url
    assert "scope=read+write" in auth_url
    assert state is not None
    
    print("✓ OAuth helper tests passed")


async def main():
    """Run all tests."""
    print("Testing Connector Framework Implementation")
    print("=" * 50)
    
    try:
        await test_base_connector()
        await test_connector_registry()
        test_result_handler()
        test_oauth_helper()
        
        print("\n" + "=" * 50)
        print("✅ All connector framework tests passed!")
        print("Task 4: Create base connector framework - COMPLETED")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())