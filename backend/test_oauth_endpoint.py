#!/usr/bin/env python3
"""
Test script to check if the OAuth initiate endpoint is working.
"""
import sys
import os
import asyncio
import httpx

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_oauth_endpoint():
    try:
        async with httpx.AsyncClient() as client:
            # Test the OAuth initiate endpoint
            response = await client.post(
                "http://localhost:8000/api/v1/auth/oauth/initiate",
                json={
                    "connector_name": "gmail_connector",
                    "redirect_uri": "http://localhost:3000/auth/oauth/callback"
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-token"  # This will likely fail auth, but we can see if endpoint exists
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 404:
                print("❌ Endpoint not found - this is the issue!")
            elif response.status_code == 401:
                print("✅ Endpoint exists but authentication failed (expected)")
            else:
                print(f"✅ Endpoint exists, status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error connecting to endpoint: {e}")
        print("Make sure the backend server is running on localhost:8000")

if __name__ == "__main__":
    asyncio.run(test_oauth_endpoint())