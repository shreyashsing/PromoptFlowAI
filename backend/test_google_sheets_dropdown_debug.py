#!/usr/bin/env python3

"""
Debug Google Sheets dropdown issue - test fetching spreadsheets directly.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_google_sheets_api():
    """Test Google Sheets API directly with a token."""
    
    # You'll need to get a valid access token from your browser's network tab
    # when the Google Sheets modal is open and authenticated
    access_token = input("Enter your Google OAuth access token: ").strip()
    
    if not access_token:
        print("❌ No access token provided")
        return
    
    print("🔍 Testing Google Drive API for spreadsheets...")
    
    async with httpx.AsyncClient() as client:
        # Test 1: Fetch spreadsheets from Drive API
        print("\n1. Fetching spreadsheets from Drive API...")
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": "mimeType='application/vnd.google-apps.spreadsheet'",
                "pageSize": 50,
                "fields": "files(id,name,createdTime,modifiedTime)"
            }
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])
            print(f"✅ Found {len(files)} spreadsheets:")
            for file in files[:5]:  # Show first 5
                print(f"  - {file['name']} (ID: {file['id']})")
        else:
            print(f"❌ Error: {response.text}")
        
        # Test 2: Test token validity with a simple API call
        print("\n2. Testing token validity with Drive about...")
        about_response = await client.get(
            "https://www.googleapis.com/drive/v3/about",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "user"}
        )
        
        print(f"Status: {about_response.status_code}")
        if about_response.status_code == 200:
            about_data = about_response.json()
            user = about_data.get("user", {})
            print(f"✅ Token valid for user: {user.get('emailAddress', 'Unknown')}")
        else:
            print(f"❌ Token validation failed: {about_response.text}")

if __name__ == "__main__":
    asyncio.run(test_google_sheets_api())