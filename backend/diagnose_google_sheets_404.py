#!/usr/bin/env python3
"""
Diagnostic script to identify the exact cause of Google Sheets 404 error.
"""

import asyncio
import sys
import os
import json
import httpx

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_supabase_client
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType

async def diagnose_google_sheets_404():
    """Diagnose the exact cause of the Google Sheets 404 error."""
    
    print("🔍 Diagnosing Google Sheets 404 Error...")
    print("=" * 50)
    
    # Configuration from your screenshot
    spreadsheet_id = "1SW66Yq-6pILFaYbUkIdHgoRh-1UfKv0g_C9yjK3qaSA"
    sheet_name = "Untitled spreadsheet"
    user_id = "9d729df3-e297-4716-8141-c91d23e1e300"
    
    print(f"📊 Configuration:")
    print(f"   Spreadsheet ID: {spreadsheet_id}")
    print(f"   Sheet Name: {sheet_name}")
    print(f"   User ID: {user_id}")
    print()
    
    try:
        # Get access token
        supabase = get_supabase_client()
        auth_service = await get_auth_token_service(supabase)
        oauth_token = await auth_service.get_token(user_id, "google_sheets", AuthType.OAUTH2)
        
        if not oauth_token:
            print("❌ No OAuth token found - authentication issue")
            return False
            
        token_data = oauth_token["token_data"]
        access_token = token_data.get("access_token")
        
        if not access_token:
            print("❌ No access token in OAuth data")
            return False
            
        print("✅ Access token retrieved successfully")
        print()
        
        # Test 1: Check if spreadsheet exists and is accessible
        print("🧪 Test 1: Spreadsheet Accessibility")
        print("-" * 30)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                spreadsheet_data = response.json()
                print("✅ Spreadsheet is accessible")
                print(f"   Title: {spreadsheet_data.get('properties', {}).get('title', 'Unknown')}")
                
                # List available sheets
                sheets = spreadsheet_data.get('sheets', [])
                print(f"   Available sheets ({len(sheets)}):")
                for i, sheet in enumerate(sheets):
                    sheet_props = sheet.get('properties', {})
                    sheet_title = sheet_props.get('title', f'Sheet{i+1}')
                    sheet_id = sheet_props.get('sheetId', 'Unknown')
                    print(f"     {i+1}. '{sheet_title}' (ID: {sheet_id})")
                    
                # Check if our sheet name exists
                sheet_titles = [sheet.get('properties', {}).get('title') for sheet in sheets]
                if sheet_name in sheet_titles:
                    print(f"✅ Sheet '{sheet_name}' found in spreadsheet")
                    actual_sheet_name = sheet_name
                else:
                    print(f"❌ Sheet '{sheet_name}' NOT found in spreadsheet")
                    if sheets:
                        actual_sheet_name = sheets[0].get('properties', {}).get('title', 'Sheet1')
                        print(f"💡 Suggestion: Use '{actual_sheet_name}' instead")
                    else:
                        print("❌ No sheets found in spreadsheet")
                        return False
                        
            elif response.status_code == 404:
                print("❌ Spreadsheet not found (404)")
                print("   Possible causes:")
                print("   - Spreadsheet ID is incorrect")
                print("   - Spreadsheet has been deleted")
                print("   - Spreadsheet URL is malformed")
                return False
            elif response.status_code == 403:
                print("❌ Access denied (403)")
                print("   Possible causes:")
                print("   - Spreadsheet is not shared with your OAuth app")
                print("   - OAuth token lacks necessary permissions")
                print("   - Spreadsheet is private")
                return False
            else:
                print(f"❌ Unexpected error: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        
        print()
        
        # Test 2: Try the exact append operation that's failing
        print("🧪 Test 2: Append Operation")
        print("-" * 30)
        
        # Use the first available sheet if our target sheet doesn't exist
        if 'actual_sheet_name' in locals():
            test_sheet_name = actual_sheet_name
        else:
            test_sheet_name = sheet_name
            
        print(f"   Testing with sheet: '{test_sheet_name}'")
        
        # Test the exact append operation
        test_values = [["test", "data"]]
        range_param = test_sheet_name  # This is what the connector uses
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}:append",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={
                    "valueInputOption": "USER_ENTERED",
                    "insertDataOption": "INSERT_ROWS"
                },
                json={
                    "values": test_values,
                    "majorDimension": "ROWS"
                }
            )
            
            if response.status_code == 200:
                print("✅ Append operation successful!")
                result = response.json()
                print(f"   Updated range: {result.get('updates', {}).get('updatedRange', 'Unknown')}")
                print(f"   Updated rows: {result.get('updates', {}).get('updatedRows', 'Unknown')}")
                return True
            elif response.status_code == 404:
                print("❌ Append operation failed (404)")
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                print(f"   Error: {error_data}")
                print("   Possible causes:")
                print(f"   - Sheet '{test_sheet_name}' doesn't exist")
                print(f"   - Range parameter '{range_param}' is invalid")
                print("   - Sheet name contains special characters")
                return False
            else:
                print(f"❌ Append operation failed ({response.status_code})")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error during diagnosis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("🎯 Diagnosis completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(diagnose_google_sheets_404())
    sys.exit(0 if success else 1)