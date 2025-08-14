#!/usr/bin/env python3

"""
Debug Google Sheets authentication and API access.
"""

import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType

load_dotenv()

async def test_google_sheets_auth():
    """Test Google Sheets authentication and token retrieval."""
    
    # Get user ID from input
    user_id = input("Enter your user ID (from JWT token): ").strip()
    
    if not user_id:
        print("❌ No user ID provided")
        return
    
    print("🔍 Testing Google Sheets authentication...")
    
    try:
        # Get database connection
        db = get_database()
        token_service = await get_auth_token_service(db)
        
        print("\n1. Checking for stored Google Sheets token...")
        oauth_token = await token_service.get_token(user_id, "google_sheets", AuthType.OAUTH2)
        
        if not oauth_token:
            print("❌ No Google Sheets OAuth token found")
            print("   Make sure you've authenticated with Google Sheets in the UI")
            return
        
        print("✅ Found Google Sheets OAuth token")
        token_data = oauth_token["token_data"]
        
        # Check token structure
        print(f"   Token keys: {list(token_data.keys())}")
        
        if "access_token" not in token_data:
            print("❌ No access_token in token data")
            return
        
        access_token = token_data["access_token"]
        print(f"   Access token length: {len(access_token)}")
        
        print("\n2. Testing Google Drive API for spreadsheets...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": "mimeType='application/vnd.google-apps.spreadsheet'",
                    "pageSize": 10,
                    "fields": "files(id,name,createdTime,modifiedTime)"
                }
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                print(f"✅ Found {len(files)} spreadsheets:")
                
                for file in files:
                    print(f"     - {file['name']} (ID: {file['id']})")
                    
                if len(files) == 0:
                    print("   ⚠️  No spreadsheets found in your Google Drive")
                    print("   Try creating a test spreadsheet in Google Sheets")
                    
            elif response.status_code == 401:
                print("❌ Authentication failed - token may be expired")
                print("   Try re-authenticating in the UI")
            else:
                print(f"❌ API Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Raw error: {response.text}")
        
        print("\n3. Testing token validity with user info...")
        
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            print(f"   Status: {user_response.status_code}")
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                print(f"✅ Token valid for: {user_data.get('email', 'Unknown')}")
            else:
                print(f"❌ Token validation failed: {user_response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_google_sheets_auth())