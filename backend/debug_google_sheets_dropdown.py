#!/usr/bin/env python3

"""
Debug Google Sheets dropdown issue - comprehensive testing.
"""

import asyncio
import httpx
import json
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType

async def debug_google_sheets_dropdown():
    """Debug the Google Sheets dropdown issue."""
    
    print("🔍 Debugging Google Sheets dropdown issue...")
    
    # Get database connection
    db = await get_database()
    token_service = await get_auth_token_service(db)
    
    # You'll need to provide a user ID that has Google Sheets authentication
    user_id = input("Enter user ID (from your session): ").strip()
    
    if not user_id:
        print("❌ No user ID provided")
        return
    
    try:
        # Get OAuth token
        print(f"\n1. Fetching OAuth token for user {user_id}...")
        oauth_token = await token_service.get_token(user_id, "google_sheets", AuthType.OAUTH2)
        
        if not oauth_token:
            print("❌ No Google Sheets OAuth token found")
            return
        
        print("✅ OAuth token found")
        access_token = oauth_token["token_data"]["access_token"]
        print(f"Token starts with: {access_token[:20]}...")
        
        # Test API calls
        async with httpx.AsyncClient() as client:
            # Test 1: Check token validity
            print("\n2. Testing token validity...")
            about_response = await client.get(
                "https://www.googleapis.com/drive/v3/about",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "user"}
            )
            
            print(f"About API Status: {about_response.status_code}")
            if about_response.status_code == 200:
                about_data = about_response.json()
                user = about_data.get("user", {})
                print(f"✅ Token valid for: {user.get('emailAddress', 'Unknown')}")
            else:
                print(f"❌ Token validation failed: {about_response.text}")
                return
            
            # Test 2: Fetch spreadsheets with detailed logging
            print("\n3. Fetching spreadsheets from Drive API...")
            
            # First, try without any filters
            print("3a. Fetching all files...")
            all_files_response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "pageSize": 10,
                    "fields": "files(id,name,mimeType)"
                }
            )
            
            print(f"All files Status: {all_files_response.status_code}")
            if all_files_response.status_code == 200:
                all_data = all_files_response.json()
                all_files = all_data.get("files", [])
                print(f"✅ Found {len(all_files)} total files:")
                for file in all_files:
                    print(f"  - {file['name']} ({file['mimeType']})")
            else:
                print(f"❌ Error fetching all files: {all_files_response.text}")
                return
            
            # Now try with spreadsheet filter
            print("\n3b. Fetching spreadsheets specifically...")
            sheets_response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": "mimeType='application/vnd.google-apps.spreadsheet'",
                    "pageSize": 50,
                    "fields": "files(id,name,createdTime,modifiedTime,mimeType)"
                }
            )
            
            print(f"Spreadsheets Status: {sheets_response.status_code}")
            if sheets_response.status_code == 200:
                sheets_data = sheets_response.json()
                spreadsheets = sheets_data.get("files", [])
                print(f"✅ Found {len(spreadsheets)} spreadsheets:")
                for sheet in spreadsheets:
                    print(f"  - {sheet['name']} (ID: {sheet['id']})")
                    
                if len(spreadsheets) == 0:
                    print("⚠️  No spreadsheets found. This could mean:")
                    print("   - User has no Google Sheets in their Drive")
                    print("   - Token doesn't have proper Drive access")
                    print("   - Scopes are insufficient")
            else:
                print(f"❌ Error fetching spreadsheets: {sheets_response.text}")
            
            # Test 3: Check scopes
            print("\n4. Checking token scopes...")
            tokeninfo_response = await client.get(
                f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
            )
            
            print(f"Token info Status: {tokeninfo_response.status_code}")
            if tokeninfo_response.status_code == 200:
                token_info = tokeninfo_response.json()
                scopes = token_info.get("scope", "").split()
                print(f"✅ Token scopes: {scopes}")
                
                required_scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.file"
                ]
                
                for scope in required_scopes:
                    if scope in scopes:
                        print(f"  ✅ {scope}")
                    else:
                        print(f"  ❌ Missing: {scope}")
            else:
                print(f"❌ Error checking token info: {tokeninfo_response.text}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_google_sheets_dropdown())