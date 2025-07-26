#!/usr/bin/env python3
"""
Test script to check what the OAuth initiate endpoint returns.
"""
import sys
import os
import asyncio
import httpx
import json

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_oauth_response():
    try:
        async with httpx.AsyncClient() as client:
            # Test the OAuth initiate endpoint with proper auth
            response = await client.post(
                "http://localhost:8000/api/v1/auth/oauth/initiate",
                json={
                    "connector_name": "gmail_connector",
                    "redirect_uri": "http://localhost:3000/auth/oauth/callback"
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-token"  # This will fail auth, but we can see the response structure
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            try:
                data = response.json()
                print(f"Response JSON: {json.dumps(data, indent=2)}")
                
                if response.status_code == 200:
                    if 'authorization_url' in data:
                        print("✅ authorization_url found in response")
                        print(f"Auth URL: {data['authorization_url'][:100]}...")
                    else:
                        print("❌ authorization_url NOT found in response")
                        print(f"Available keys: {list(data.keys())}")
                        
                elif response.status_code == 401:
                    print("⚠️  Authentication failed (expected with test token)")
                    
            except Exception as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error connecting to endpoint: {e}")
        print("Make sure the backend server is running on localhost:8000")

if __name__ == "__main__":
    asyncio.run(test_oauth_response())