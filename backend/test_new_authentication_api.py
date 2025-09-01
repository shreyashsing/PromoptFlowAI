"""
Test the new step-by-step authentication API endpoints
"""
import asyncio
import json
import aiohttp
from datetime import datetime

async def test_new_authentication_endpoints():
    """Test the new authentication-enabled endpoints"""
    
    print("🧪 Testing New Step-by-Step Authentication API")
    print("=" * 60)
    
    # Test data
    test_requests = [
        "Send an email using Gmail",
        "Create a Google Sheets document", 
        "Search with Perplexity then send email",
        "Upload file to Google Drive and notify via Gmail"
    ]
    
    base_url = "http://localhost:8000"
    
    # You'll need to get a real auth token from your frontend
    # For now, we'll test without auth (will fail but show the flow)
    headers = {
        "Content-Type": "application/json",
        # "Authorization": "Bearer YOUR_TOKEN_HERE"
    }
    
    async with aiohttp.ClientSession() as session:
        
        for i, user_request in enumerate(test_requests, 1):
            print(f"\n🔍 Test {i}: {user_request}")
            print("-" * 40)
            
            try:
                # Test the new step-by-step endpoint
                payload = {
                    "user_request": user_request,
                    "session_id": f"test_session_{i}_{int(datetime.utcnow().timestamp())}"
                }
                
                async with session.post(
                    f"{base_url}/api/enhanced-workflows/execute-step-by-step",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    print(f"📡 Status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"✅ Success: {result.get('success', False)}")
                        print(f"📝 Message: {result.get('message', 'No message')}")
                        print(f"🔐 Requires Auth: {result.get('requires_authentication', False)}")
                        
                        if result.get('auth_requests'):
                            print(f"🔑 Auth Requests: {len(result['auth_requests'])}")
                            for auth_req in result['auth_requests']:
                                print(f"   - {auth_req.get('connector_display_name', 'Unknown')} ({auth_req.get('auth_type', 'unknown')})")
                        
                        if result.get('workflow_key'):
                            print(f"🔗 Workflow Key: {result['workflow_key']}")
                        
                        steps = result.get('steps', [])
                        print(f"📊 Steps: {len(steps)}")
                        for j, step in enumerate(steps[:3], 1):  # Show first 3 steps
                            print(f"   {j}. {step.get('step_type', 'unknown')}: {step.get('content', 'No content')[:60]}...")
                    
                    elif response.status == 401:
                        print("🔒 Authentication required (expected for this test)")
                        
                    elif response.status == 404:
                        print("❌ Endpoint not found - make sure enhanced workflows are registered")
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Error {response.status}: {error_text}")
                        
            except Exception as e:
                print(f"❌ Request failed: {str(e)}")
    
    print(f"\n🎉 New Authentication API Test Complete!")
    print("\n💡 To activate this system:")
    print("   1. Update frontend to call /api/enhanced-workflows/execute-step-by-step")
    print("   2. Or replace the old endpoint with the new system")
    print("   3. Make sure authentication tokens are passed correctly")

if __name__ == "__main__":
    asyncio.run(test_new_authentication_endpoints())