#!/usr/bin/env python3
"""
Test script to verify Google Sheets OAuth authentication setup.
"""
import asyncio
import httpx
from app.core.config import settings

async def test_google_sheets_oauth():
    """Test Google Sheets OAuth initiation."""
    
    print("Testing Google Sheets OAuth Setup...")
    print(f"Gmail Client ID configured: {'Yes' if settings.GMAIL_CLIENT_ID else 'No'}")
    print(f"Gmail Client Secret configured: {'Yes' if settings.GMAIL_CLIENT_SECRET else 'No'}")
    
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        print("❌ Google OAuth credentials not configured!")
        print("Please set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in your .env file")
        return False
    
    # Test OAuth initiation endpoint
    try:
        async with httpx.AsyncClient() as client:
            # This would normally require authentication, but we're just testing the endpoint exists
            response = await client.post(
                "http://localhost:8000/api/v1/auth/oauth/initiate",
                json={
                    "connector_name": "google_sheets",
                    "redirect_uri": "http://localhost:3000/auth/oauth/callback"
                },
                headers={"Authorization": "Bearer test-token"}  # This will fail auth but test the endpoint
            )
            
            if response.status_code == 401:
                print("✅ OAuth initiate endpoint exists and requires authentication")
                return True
            elif response.status_code == 200:
                print("✅ OAuth initiate endpoint working")
                return True
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing OAuth endpoint: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_google_sheets_oauth())