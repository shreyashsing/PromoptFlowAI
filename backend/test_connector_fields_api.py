#!/usr/bin/env python3

"""
Test the connector fields API endpoint directly to debug Google Sheets dropdown issue.
"""

import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def test_connector_fields_api():
    """Test the connector fields API endpoint."""
    
    # Get the API base URL
    base_url = os.getenv("API_URL", "http://localhost:8000")
    
    # You'll need to get a valid JWT token from your browser
    jwt_token = input("Enter your JWT access token (from browser): ").strip()
    
    if not jwt_token:
        print("❌ No JWT token provided")
        return
    
    print("🔍 Testing connector fields API...")
    
    async with httpx.AsyncClient() as client:
        # Test the connector fields API
        request_data = {
            "connector_name": "google_sheets",
            "field_name": "spreadsheet_id",
            "context": {}
        }
        
        print(f"\n📤 Sending request to {base_url}/api/v1/connector-fields/fetch")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        response = await client.post(
            f"{base_url}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            },
            json=request_data
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('success')}")
            print(f"Options count: {len(data.get('options', []))}")
            
            if data.get('options'):
                print("📋 First few options:")
                for option in data['options'][:3]:
                    print(f"  - {option.get('label')} (ID: {option.get('value')})")
            else:
                print("❌ No options returned")
                
            if data.get('error'):
                print(f"❌ Error: {data['error']}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_connector_fields_api())