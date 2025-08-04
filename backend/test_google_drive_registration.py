#!/usr/bin/env python3
"""
Test script to verify Google Drive connector registration.
"""
import asyncio
from app.connectors.core.register import register_core_connectors, validate_core_connectors
from app.connectors.registry import get_connector_registry


async def test_registration():
    """Test that Google Drive connector is properly registered."""
    print("Testing Google Drive Connector Registration...")
    
    # Register all core connectors
    result = register_core_connectors()
    print(f"Registration result: {result}")
    
    # Get registry instance
    registry = get_connector_registry()
    
    # Check if Google Drive connector is registered
    connectors = registry.list_connectors()
    print(f"Registered connectors: {connectors}")
    
    if "google_drive" in connectors:
        print("✅ Google Drive connector is registered!")
        
        # Get connector metadata
        metadata = registry.get_metadata("google_drive")
        print(f"Connector metadata:")
        print(f"  Name: {metadata.name}")
        print(f"  Description: {metadata.description}")
        print(f"  Category: {metadata.category}")
        print(f"  Auth Type: {metadata.auth_type}")
        
        # Create connector instance
        connector = registry.create_connector("google_drive")
        print(f"✅ Successfully created connector instance: {connector.name}")
        
        # Test auth requirements
        auth_req = await connector.get_auth_requirements()
        print(f"✅ Auth requirements: {auth_req.type}")
        print(f"  OAuth scopes: {auth_req.oauth_scopes}")
        
    else:
        print("❌ Google Drive connector is NOT registered!")
        return False
    
    # Validate all connectors
    print("\nValidating all connectors...")
    validation_results = validate_core_connectors()
    
    if "google_drive" in validation_results:
        result = validation_results["google_drive"]
        if result["status"] == "passed":
            print("✅ Google Drive connector validation passed!")
            print(f"  Schema properties: {result['schema_properties']}")
        else:
            print(f"❌ Google Drive connector validation failed: {result['error']}")
            return False
    
    print("\n✅ All registration tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_registration())
    if success:
        print("\n🎉 Google Drive connector is ready for use!")
    else:
        print("\n💥 Registration test failed!")