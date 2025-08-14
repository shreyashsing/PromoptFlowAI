#!/usr/bin/env python3

"""
Test the Google Sheets scope fix.
"""

import asyncio
import httpx
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType
from app.api.connector_fields import _fetch_google_spreadsheets

async def test_scope_fix():
    """Test the Google Sheets scope fix."""
    
    print("🔍 Testing Google Sheets scope fix...")
    
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
            print("⚠️  You need to re-authenticate with the new scopes!")
            print("   1. Go to the Google Sheets modal")
            print("   2. Disconnect your current authentication")
            print("   3. Re-authenticate to get the new scopes")
            return
        
        access_token = oauth_token["token_data"]["access_token"]
        print("✅ OAuth token found")
        
        # Check current scopes
        print("\n2. Checking current token scopes...")
        async with httpx.AsyncClient() as client:
            tokeninfo_response = await client.get(
                f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
            )
            
            if tokeninfo_response.status_code == 200:
                token_info = tokeninfo_response.json()
                scopes = token_info.get("scope", "").split()
                print(f"Current scopes: {scopes}")
                
                required_scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.readonly"
                ]
                
                has_all_scopes = True
                for scope in required_scopes:
                    if scope in scopes:
                        print(f"  ✅ {scope}")
                    else:
                        print(f"  ❌ Missing: {scope}")
                        has_all_scopes = False
                
                if not has_all_scopes:
                    print("\n⚠️  Token doesn't have required scopes!")
                    print("   You need to re-authenticate to get the new scopes.")
                    return
            else:
                print(f"❌ Error checking token info: {tokeninfo_response.text}")
                return
        
        # Test the updated function
        print("\n3. Testing spreadsheet fetching with updated function...")
        result = await _fetch_google_spreadsheets(access_token)
        
        if result.success:
            print(f"✅ Successfully fetched {len(result.options)} spreadsheets!")
            for option in result.options[:5]:  # Show first 5
                print(f"  - {option.label} (ID: {option.value})")
        else:
            print(f"❌ Failed to fetch spreadsheets: {result.error}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scope_fix())