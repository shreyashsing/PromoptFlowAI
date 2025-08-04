#!/usr/bin/env python3
"""
Test to verify that the ReAct agent properly selects Google Drive connector.
"""
import asyncio
import logging
from app.services.true_react_agent import TrueReActAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_google_drive_selection():
    """Test that the ReAct agent selects Google Drive for upload requests."""
    print("🧪 Testing Google Drive Connector Selection...")
    
    # Initialize agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test requests that should use Google Drive
    test_requests = [
        "search for top 5 articles on ai and upload it in my google drive",
        "find latest news about machine learning and save to drive",
        "search for python tutorials and upload to google drive",
        "get information about blockchain and store in drive"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🔍 Test {i}: '{request}'")
        
        try:
            # Test the reasoning process
            initial_analysis = await agent.reason_about_requirements(request)
            print(f"   Initial analysis: {initial_analysis.get('reasoning', 'No reasoning')[:100]}...")
            
            # Test first step selection
            first_step = await agent.reason_next_step(initial_analysis, [], request)
            print(f"   First step: {first_step.get('connector_name')} - {first_step.get('purpose', 'No purpose')}")
            
            # Simulate first step completion (search)
            mock_first_step = {
                "connector_name": first_step.get('connector_name'),
                "purpose": first_step.get('purpose'),
                "parameters": {"action": "search", "query": "test"},
                "step_number": 1
            }
            
            # Test second step selection
            second_step = await agent.reason_next_step(initial_analysis, [mock_first_step], request)
            if second_step:
                print(f"   Second step: {second_step.get('connector_name')} - {second_step.get('purpose', 'No purpose')}")
                
                # Check if Google Drive is selected
                if second_step.get('connector_name') == 'google_drive':
                    print("   ✅ Google Drive correctly selected!")
                else:
                    print(f"   ❌ Expected google_drive, got {second_step.get('connector_name')}")
            else:
                print("   ⚠️ No second step suggested")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test fallback logic specifically
    print(f"\n🔧 Testing Fallback Logic...")
    
    fallback_tests = [
        ("upload to drive", "Should select google_drive"),
        ("save to google drive", "Should select google_drive"),
        ("store in drive", "Should select google_drive")
    ]
    
    for request, expected in fallback_tests:
        try:
            # Test with one existing step (search completed)
            mock_step = {"connector_name": "perplexity_search", "purpose": "search"}
            fallback_result = await agent._fallback_next_step([mock_step], request)
            
            connector = fallback_result.get('connector_name') if fallback_result else None
            print(f"   '{request}' -> {connector} ({expected})")
            
            if connector == 'google_drive':
                print("     ✅ Correct!")
            else:
                print(f"     ❌ Expected google_drive, got {connector}")
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    # Test available connectors list
    print(f"\n📋 Testing Available Connectors List...")
    try:
        available_connectors = await agent.tool_registry.get_tool_metadata()
        connector_names = [c["name"] for c in available_connectors]
        print(f"   Available connectors: {connector_names}")
        
        if 'google_drive' in connector_names:
            print("   ✅ google_drive is in available connectors")
        else:
            print("   ❌ google_drive is NOT in available connectors")
            
    except Exception as e:
        print(f"   ❌ Error getting connectors: {e}")


async def test_full_workflow_creation():
    """Test creating a full workflow that uses Google Drive."""
    print(f"\n🚀 Testing Full Workflow Creation...")
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    test_request = "search for top 5 articles on ai and upload it in my google drive"
    user_id = "test_user_123"
    
    try:
        result = await agent.process_user_request(test_request, user_id)
        
        if result.get("success"):
            workflow = result.get("workflow", {})
            steps = workflow.get("steps", [])
            
            print(f"   ✅ Workflow created successfully with {len(steps)} steps")
            
            # Check if Google Drive is used
            google_drive_used = any(
                step.get("connector_name") == "google_drive" 
                for step in steps
            )
            
            if google_drive_used:
                print("   ✅ Google Drive connector is used in the workflow!")
                
                # Show the steps
                for i, step in enumerate(steps, 1):
                    connector = step.get("connector_name")
                    purpose = step.get("purpose", "No purpose")
                    print(f"     Step {i}: {connector} - {purpose}")
            else:
                print("   ❌ Google Drive connector is NOT used in the workflow")
                print("   Workflow steps:")
                for i, step in enumerate(steps, 1):
                    connector = step.get("connector_name")
                    purpose = step.get("purpose", "No purpose")
                    print(f"     Step {i}: {connector} - {purpose}")
        else:
            error = result.get("error", "Unknown error")
            print(f"   ❌ Workflow creation failed: {error}")
            
    except Exception as e:
        print(f"   ❌ Error creating workflow: {e}")


async def main():
    """Run all tests."""
    print("=" * 80)
    print("🧪 Google Drive Agent Selection Test Suite")
    print("=" * 80)
    
    await test_google_drive_selection()
    await test_full_workflow_creation()
    
    print("\n" + "=" * 80)
    print("✅ Test suite completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())