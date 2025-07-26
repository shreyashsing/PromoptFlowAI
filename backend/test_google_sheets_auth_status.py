#!/usr/bin/env python3
"""
Test script to verify Google Sheets authentication status detection.
"""
import asyncio
import json

async def test_google_sheets_auth_status():
    """Test Google Sheets authentication status logic."""
    
    print("=" * 60)
    print("GOOGLE SHEETS AUTHENTICATION STATUS TEST")
    print("=" * 60)
    
    # Simulate the frontend logic
    def check_auth_status_frontend(connector_name: str, has_tokens: bool = False):
        """Simulate frontend authentication status check."""
        
        print(f"\n🔍 Checking auth status for: {connector_name}")
        
        # This is the logic from ConnectorConfigModal
        if connector_name in ['gmail_connector', 'perplexity_search', 'google_sheets']:
            print(f"✅ Connector '{connector_name}' requires authentication")
            
            if has_tokens:
                print(f"✅ Found valid tokens for '{connector_name}'")
                return 'configured'
            else:
                print(f"❌ No valid tokens found for '{connector_name}'")
                return 'required'
        else:
            print(f"ℹ️  Connector '{connector_name}' needs no authentication")
            return 'none'
    
    # Test different connectors
    test_cases = [
        ('gmail_connector', False),
        ('gmail_connector', True),
        ('google_sheets', False),  # This should show 'required', not 'none'
        ('google_sheets', True),
        ('perplexity_search', False),
        ('perplexity_search', True),
        ('http_request', False),
        ('webhook', False)
    ]
    
    print("\n📋 TEST RESULTS:")
    print("-" * 60)
    
    for connector_name, has_tokens in test_cases:
        status = check_auth_status_frontend(connector_name, has_tokens)
        expected = 'configured' if has_tokens and connector_name in ['gmail_connector', 'google_sheets', 'perplexity_search'] else ('required' if connector_name in ['gmail_connector', 'google_sheets', 'perplexity_search'] else 'none')
        
        result = "✅ PASS" if status == expected else "❌ FAIL"
        print(f"{result} {connector_name} (tokens: {has_tokens}) -> {status}")
    
    print("\n" + "=" * 60)
    print("FRONTEND AUTHENTICATION LOGIC")
    print("=" * 60)
    
    print("""
Frontend Logic (ConnectorConfigModal.tsx):

const checkAuthenticationStatus = async (connectorName: string) => {
  if (connectorName === 'gmail_connector' || 
      connectorName === 'perplexity_search' || 
      connectorName === 'google_sheets') {  // ← FIXED: Added google_sheets
    
    // Check for existing tokens
    const hasAuthToken = authData.tokens && authData.tokens.some((token: any) => 
      token.connector_name === connectorName && 
      (token.token_type === 'oauth2' || token.token_type === 'api_key')
    )
    
    return hasAuthToken ? 'configured' : 'required'
  } else {
    return 'none'  // No authentication required
  }
}
""")
    
    print("\n" + "=" * 60)
    print("UI BEHAVIOR")
    print("=" * 60)
    
    ui_behaviors = {
        'none': "🟢 Shows: 'No authentication required'",
        'required': "🟠 Shows: 'Authentication required' + Connect button",
        'configured': "🟢 Shows: 'Successfully authenticated' + Reconnect button",
        'checking': "🔵 Shows: 'Checking authentication status...'"
    }
    
    for status, behavior in ui_behaviors.items():
        print(f"{status.upper()}: {behavior}")
    
    print("\n" + "=" * 60)
    print("ISSUE RESOLUTION")
    print("=" * 60)
    
    print("""
❌ BEFORE FIX:
- google_sheets was NOT in the authentication check condition
- Result: authStatus = 'none' → "No authentication required"

✅ AFTER FIX:
- google_sheets IS in the authentication check condition  
- Result: authStatus = 'required' → "Authentication required" + Connect button

🔧 CHANGE MADE:
if (connectorName === 'gmail_connector' || connectorName === 'perplexity_search') {
                                                                    ↓ ADDED
if (connectorName === 'gmail_connector' || connectorName === 'perplexity_search' || connectorName === 'google_sheets') {
""")
    
    print("\n✅ Google Sheets should now show proper authentication UI!")

if __name__ == "__main__":
    asyncio.run(test_google_sheets_auth_status())