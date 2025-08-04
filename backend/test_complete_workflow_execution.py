#!/usr/bin/env python3
"""
Test complete workflow execution flow including:
1. Workflow creation
2. Workflow execution
3. Status polling
4. Gmail connector execution
"""
import asyncio
import httpx
import json
import time

async def test_complete_workflow_execution():
    """Test the complete workflow execution flow."""
    print("🧪 Testing Complete Workflow Execution Flow")
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
                "name": "Test Gmail Workflow",
                "description": "Test workflow for Gmail connector",
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
            
            create_response = await client.post(
                f"{base_url}/api/v1/workflows",
                json=workflow_data,
                headers=headers
            )
            
            if create_response.status_code == 201:
                workflow = create_response.json()
                workflow_id = workflow["id"]
                print(f"✅ Workflow created with ID: {workflow_id}")
            else:
                print(f"❌ Failed to create workflow: {create_response.status_code}")
                print(f"Response: {create_response.text}")
                return
            
            # Step 2: Execute the workflow
            print(f"\n🚀 Step 2: Executing workflow {workflow_id}...")
            
            execute_response = await client.post(
                f"{base_url}/api/v1/workflows/{workflow_id}/execute",
                json={
                    "trigger_type": "manual",
                    "parameters": {}
                },
                headers=headers
            )
            
            if execute_response.status_code == 200:
                execution_result = execute_response.json()
                execution_id = execution_result["execution_id"]
                print(f"✅ Workflow execution started with ID: {execution_id}")
            else:
                print(f"❌ Failed to execute workflow: {execute_response.status_code}")
                print(f"Response: {execute_response.text}")
                return
            
            # Step 3: Poll execution status
            print(f"\n🔍 Step 3: Polling execution status for {execution_id}...")
            
            max_polls = 10
            poll_interval = 5  # seconds
            
            for i in range(max_polls):
                print(f"Poll {i+1}/{max_polls}...")
                
                status_response = await client.get(
                    f"{base_url}/api/v1/executions/{execution_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"Status: {status_data.get('status', 'unknown')}")
                    
                    if status_data.get("status") == "completed":
                        print("🎉 Workflow execution completed successfully!")
                        print(f"Results: {json.dumps(status_data.get('result', {}), indent=2)}")
                        break
                    elif status_data.get("status") == "failed":
                        print("❌ Workflow execution failed!")
                        print(f"Error: {status_data.get('error', 'Unknown error')}")
                        break
                    else:
                        print(f"⏳ Still running... ({status_data.get('status', 'unknown')})")
                        if i < max_polls - 1:
                            await asyncio.sleep(poll_interval)
                else:
                    print(f"❌ Failed to get execution status: {status_response.status_code}")
                    break
            
            # Step 4: Test connector authentication status
            print(f"\n🔐 Step 4: Checking Gmail connector authentication...")
            
            auth_test_response = await client.post(
                f"{base_url}/api/v1/auth/test-connector",
                json={"connector_name": "gmail_connector"},
                headers=headers
            )
            
            if auth_test_response.status_code == 200:
                auth_result = auth_test_response.json()
                if auth_result.get("success"):
                    print("✅ Gmail connector authentication successful")
                else:
                    print(f"❌ Gmail connector authentication failed: {auth_result.get('error')}")
            else:
                print(f"❌ Failed to test connector auth: {auth_test_response.status_code}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")

if __name__ == "__main__":
    print("⚠️  Note: This test requires a valid authentication token.")
    print("Update the 'auth_token' variable with a real token to run this test.")
    print()
    asyncio.run(test_complete_workflow_execution())