#!/usr/bin/env python3
"""
Debug script to check Google Sheets connector issues.
"""

import asyncio
import sys
import os
import json

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_supabase_client
from app.connectors.core.google_sheets_connector import GoogleSheetsConnector
from app.models.connector import ConnectorExecutionContext

async def debug_google_sheets():
    """Debug the Google Sheets connector issue."""
    
    print("🔍 Debugging Google Sheets connector...")
    
    try:
        # Check authentication tokens
        supabase = get_supabase_client()
        user_id = "9d729df3-e297-4716-8141-c91d23e1e300"  # From the logs
        
        print(f"📊 Checking authentication tokens for user: {user_id}")
        
        # Get auth tokens
        tokens_response = supabase.table("auth_tokens").select("*").eq("user_id", user_id).execute()
        
        if tokens_response.data:
            print(f"✅ Found {len(tokens_response.data)} auth tokens:")
            for i, token in enumerate(tokens_response.data):
                print(f"   Token {i+1}:")
                print(f"     Connector Name: {token.get('connector_name', 'Unknown')}")
                print(f"     Token Type: {token.get('token_type', 'Unknown')}")
                print(f"     Is Active: {token.get('is_active', 'Unknown')}")
                print(f"     Expires: {token.get('expires_at', 'N/A')}")
                print(f"     Has Encrypted Token: {'Yes' if token.get('encrypted_token') else 'No'}")
                
                # Check if this is a Google Sheets token
                if token.get('connector_name') == 'google_sheets':
                    print(f"     ✅ This is a Google Sheets token!")
        else:
            print("❌ No authentication tokens found")
            print("   This explains why Google Sheets is failing!")
            return False
        
        # Test the connector with the spreadsheet ID from the screenshot
        spreadsheet_id = "1SW66Yq-6pILFaYbUkIdHgoRh-1UfKv0g_C9yjK3qaSA"
        sheet_name = "Untitled spreadsheet"
        
        print(f"\n🧪 Testing Google Sheets connector...")
        print(f"   Spreadsheet ID: {spreadsheet_id}")
        print(f"   Sheet Name: {sheet_name}")
        
        # Create connector instance
        connector = GoogleSheetsConnector()
        
        # Create test context
        context = ConnectorExecutionContext(
            user_id=user_id,
            workflow_id="test-workflow",
            node_id="test-node",
            execution_id="test-execution"
        )
        
        # Test parameters (similar to what's in the workflow)
        test_params = {
            "action": "append",
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "values": [["test", "data"]],
            "range": "A1:B1"
        }
        
        print(f"   Test Parameters: {json.dumps(test_params, indent=2)}")
        
        # Test auth token loading directly
        print(f"\n🔧 Testing auth token loading...")
        from app.services.auth_tokens import get_auth_token_service
        from app.models.base import AuthType
        
        auth_service = await get_auth_token_service(supabase)
        oauth_token = await auth_service.get_token(user_id, "google_sheets", AuthType.OAUTH2)
        
        if oauth_token:
            print(f"✅ OAuth token found!")
            token_data = oauth_token["token_data"]
            print(f"   Token keys: {list(token_data.keys())}")
            print(f"   Has access_token: {'access_token' in token_data}")
            print(f"   Has refresh_token: {'refresh_token' in token_data}")
            
            if "access_token" not in token_data:
                print("   ❌ Missing access_token - this explains the failure!")
                if "refresh_token" in token_data:
                    print("   ✅ Refresh token available - should be able to refresh")
                else:
                    print("   ❌ No refresh token either - need to re-authenticate")
        else:
            print(f"❌ No OAuth token found")
        
        # Test the parallel executor's token loading
        print(f"\n🔧 Testing parallel executor token loading...")
        from app.services.parallel_workflow_executor import ParallelWorkflowExecutor
        
        executor = ParallelWorkflowExecutor()
        parallel_tokens = await executor._load_auth_tokens_for_connector(user_id, "google_sheets")
        
        print(f"   Parallel executor tokens: {list(parallel_tokens.keys())}")
        print(f"   Has access_token: {'access_token' in parallel_tokens}")
        
        # Create context with parallel executor tokens
        context_with_parallel_tokens = ConnectorExecutionContext(
            user_id=user_id,
            workflow_id="test-workflow",
            node_id="test-node",
            auth_tokens=parallel_tokens
        )
        
        print(f"   Context auth_tokens: {list(context_with_parallel_tokens.auth_tokens.keys())}")
        
        # Try to execute
        try:
            result = await connector.execute(test_params, context_with_parallel_tokens)
            print(f"✅ Connector execution successful!")
            print(f"   Result: {result.data}")
        except Exception as e:
            print(f"❌ Connector execution failed: {str(e)}")
            
            # Check if it's an authentication issue
            if "access token not found" in str(e).lower():
                print("   → This is an authentication token loading issue")
            elif "401" in str(e) or "Unauthorized" in str(e):
                print("   → This is an authentication issue")
            elif "404" in str(e) or "not found" in str(e).lower():
                print("   → This is a 404 error - spreadsheet or sheet not found")
                print("   → Possible causes:")
                print("     1. Spreadsheet ID is incorrect")
                print("     2. Sheet name doesn't exist")
                print("     3. User doesn't have access to the spreadsheet")
                print("     4. Spreadsheet is private and not shared")
            elif "403" in str(e) or "Forbidden" in str(e):
                print("   → This is a permission issue")
            
            return False
            
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎯 Debug completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_google_sheets())
    sys.exit(0 if success else 1)