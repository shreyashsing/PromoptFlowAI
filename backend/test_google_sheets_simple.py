#!/usr/bin/env python3

"""
Simple test to check Google Sheets access and create a test sheet if needed.
"""

import asyncio
import httpx
import json
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType

async def test_and_create_sheet():
    """Test Google Sheets access and create a test sheet if needed."""
    
    print("🔍 Testing Google Sheets access...")
    
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
        
        access_token = oauth_token["token_data"]["access_token"]
        print("✅ OAuth token found")
        
        async with httpx.AsyncClient() as client:
            # Check existing spreadsheets
            print("\n2. Checking existing spreadsheets...")
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": "mimeType='application/vnd.google-apps.spreadsheet'",
                    "pageSize": 50,
                    "fields": "files(id,name,createdTime,modifiedTime)"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                print(f"✅ Found {len(files)} existing spreadsheets")
                
                if len(files) > 0:
                    print("Existing spreadsheets:")
                    for file in files[:5]:
                        print(f"  - {file['name']} (ID: {file['id']})")
                    return
                else:
                    print("No existing spreadsheets found.")
            else:
                print(f"❌ Error checking spreadsheets: {response.text}")
                return
            
            # Create a test spreadsheet
            print("\n3. Creating a test spreadsheet...")
            create_response = await client.post(
                "https://sheets.googleapis.com/v4/spreadsheets",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "title": "PromptFlow Test Spreadsheet"
                    },
                    "sheets": [{
                        "properties": {
                            "title": "Test Data",
                            "gridProperties": {
                                "rowCount": 100,
                                "columnCount": 10
                            }
                        }
                    }]
                }
            )
            
            if create_response.status_code == 200:
                sheet_data = create_response.json()
                sheet_id = sheet_data["spreadsheetId"]
                sheet_url = sheet_data["spreadsheetUrl"]
                print(f"✅ Created test spreadsheet!")
                print(f"   ID: {sheet_id}")
                print(f"   URL: {sheet_url}")
                
                # Add some test data
                print("\n4. Adding test data...")
                values_response = await client.put(
                    f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/A1:C3",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    params={"valueInputOption": "USER_ENTERED"},
                    json={
                        "values": [
                            ["Name", "Email", "Status"],
                            ["John Doe", "john@example.com", "Active"],
                            ["Jane Smith", "jane@example.com", "Pending"]
                        ]
                    }
                )
                
                if values_response.status_code == 200:
                    print("✅ Added test data to spreadsheet")
                else:
                    print(f"⚠️  Failed to add test data: {values_response.text}")
                
            else:
                print(f"❌ Failed to create test spreadsheet: {create_response.text}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_and_create_sheet())