#!/usr/bin/env python3
"""
Test script to verify YouTube OAuth disconnect endpoint works.
"""
import asyncio
import httpx
import json

async def test_youtube_oauth_disconnect():
    """Test the YouTube OAuth disconnect endpoint."""
    print("🧪 Testing YouTube OAuth disconnect endpoint...")
    
    base_url = "http://localhost:8000"
    
    # Mock request data
    request_data = {
        "connector_name": "youtube"
    }
    
    print(f"📤 Request data: {json.dumps(request_data, indent=2)}")
    print("📝 Note: This test will fail without proper authentication, but we can verify the endpoint exists")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/auth/oauth/disconnect",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ Expected 401 - Authentication required (endpoint is working)")
            elif response.status_code == 422:
                print("✅ Expected 422 - Validation error (endpoint is working)")
            elif response.status_code == 200:
                print("✅ 200 - Disconnect successful")
                print(f"📄 Response: {response.text}")
            else:
                print(f"📄 Response: {response.text}")
                
    except httpx.ConnectError:
        print("❌ Could not connect to backend server")
        print("💡 Make sure the backend server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_youtube_oauth_disconnect())