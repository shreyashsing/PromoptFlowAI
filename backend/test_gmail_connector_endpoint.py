#!/usr/bin/env python3
"""
Test the new Gmail connector test endpoint.
"""
import asyncio
import httpx
import json

async def test_gmail_connector_endpoint():
    """Test the Gmail connector test endpoint."""
    print("🧪 Testing Gmail Connector Test Endpoint")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test the endpoint (this will fail without proper auth, but we can see if the endpoint exists)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/v1/auth/test-connector",
                json={"connector_name": "gmail_connector"},
                headers={"Authorization": "Bearer fake-token"}  # This will fail auth but test the endpoint
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 401:
                print("✅ Endpoint exists but requires authentication (expected)")
            elif response.status_code == 404:
                print("❌ Endpoint not found")
            else:
                print(f"📋 Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(test_gmail_connector_endpoint())