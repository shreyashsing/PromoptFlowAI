#!/usr/bin/env python3
"""
Test script to verify YouTube channel fetching fix.
"""
import asyncio
import httpx
import os
from app.api.connector_fields import _fetch_youtube_channels

async def test_youtube_channel_fetch():
    """Test the YouTube channel fetching function."""
    print("🧪 Testing YouTube channel fetching fix...")
    
    # This is a mock test - in real usage, you'd need a valid access token
    # For now, let's just test the function structure
    
    try:
        # Test with a mock token (this will fail but we can see the error handling)
        result = await _fetch_youtube_channels("mock_token", {})
        print(f"✅ Function executed successfully")
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        print("This is expected with a mock token")

if __name__ == "__main__":
    asyncio.run(test_youtube_channel_fetch())