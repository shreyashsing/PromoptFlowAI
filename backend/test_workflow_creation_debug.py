#!/usr/bin/env python3
"""
Debug workflow creation and execution flow.
"""
import asyncio
import httpx
import json

async def test_workflow_creation_debug():
    """Test workflow creation and verify it exists."""
    print("🧪 Testing Workflow Creation and Verification")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # This would need a real auth token - for testing purposes
    auth_token = "your-real-auth-token-here"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Create a test workflow
            print("📝 Step 1: Creating test workflow...")
            
            workflow_data = {
                "name": "Debug Test Workflow",
                "description": "Test workflow for debugging 404 issues",
                "steps": [
                    {
                        "connector_name": "perplexity_search",
                        "purpose": "Search for AI/ML blogs",
                        "parameters": {
                            "query": "AI machine learning latest news",
                            "max_results": 5
                        }
                    },
                    {
                        "connector_name": "gmail_connector", 
                        "purpose": "Send email with results",
                        "parameters": {
                            "action": "send",
                            "to": "test@example.com",
                            "subject": "AI/ML News Summary",
                            "body": "Here are the latest AI/ML news articles..."
                        }
                    }
                ],
                "status": "active"
            }
            
            print(f"📤 Sending workflow data: {json.dumps(workflow_data, indent=2)}")
            
            create_response = await client.post(
                f"{base_url}/api/v1/workflows",
                json=workflow_data,
                headers=headers
            )
            
            print(f"📥 Create response status: {create_response.status_code}")
            print(f"📥 Create response headers: {dict(create_response.headers)}")
            
            if create_response.status_code == 201:
                workflow = create_response.json()
                workflow_id = workflow["id"]
                print(f"✅ Workflow created with ID: {workflow_id}")
                print(f"📋 Created workflow: {json.dumps(workflow, indent=2)}")
            else:
                print(f"❌ Failed to create workflow: {create_response.status_code}")
                print(f"Response: {create_response.text}")
                return
            
            # Step 2: Verify the workflow exists
            print(f"\n🔍 Step 2: Verifying workflow {workflow_id} exists...")
            
            verify_response = await client.get(
                f"{base_url}/api/v1/workflows/{workflow_id}",
                headers=headers
            )
            
            print(f"📥 Verify response status: {verify_response.status_code}")
            
            if verify_response.status_code == 200:
                verified_workflow = verify_response.json()
                print(f"✅ Workflow verified: {json.dumps(verified_workflow, indent=2)}")
            else:
                print(f"❌ Failed to verify workflow: {verify_response.status_code}")
                print(f"Response: {verify_response.text}")
                return
            
            # Step 3: Try to execute the workflow
            print(f"\n🚀 Step 3: Attempting to execute workflow {workflow_id}...")
            
            execute_response = await client.post(
                f"{base_url}/api/v1/workflows/{workflow_id}/execute",
                json={
                    "trigger_type": "manual",
                    "parameters": {}
                },
                headers=headers
            )
            
            print(f"📥 Execute response status: {execute_response.status_code}")
            
            if execute_response.status_code == 200:
                execution_result = execute_response.json()
                print(f"✅ Workflow execution started: {json.dumps(execution_result, indent=2)}")
            else:
                print(f"❌ Failed to execute workflow: {execute_response.status_code}")
                print(f"Response: {execute_response.text}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")

if __name__ == "__main__":
    print("⚠️  Note: This test requires a valid authentication token.")
    print("Update the 'auth_token' variable with a real token to run this test.")
    print()
    asyncio.run(test_workflow_creation_debug())