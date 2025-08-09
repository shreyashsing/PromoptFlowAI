"""
Test Enhanced Planning Integration

This test verifies that the TrueReActAgent now has enhanced planning capabilities
with tool chaining, state machine modeling, and advanced workflow orchestration.
"""
import asyncio
import logging
from app.services.true_react_agent import TrueReActAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_planning():
    """Test the enhanced planning capabilities."""
    
    print("🧪 Testing Enhanced Planning Integration")
    print("=" * 50)
    
    # Initialize the agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test requests that should trigger enhanced planning
    test_requests = [
        "Search for AI news, summarize it, and save to Notion",
        "Find information about Python best practices and email it to me",
        "Get YouTube video data, process it, and store in Google Sheets",
        "Search for market trends, analyze the data, and create a report"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🔍 Test {i}: {request}")
        print("-" * 40)
        
        try:
            # Process the request
            result = await agent.process_user_request(request, "test_user")
            
            # Check if enhanced planning was used
            if result.get("success"):
                plan = result.get("plan", {})
                
                print(f"✅ Plan created successfully")
                print(f"📋 Summary: {plan.get('summary', 'N/A')}")
                print(f"🔗 Sequence: {plan.get('sequence_description', 'N/A')}")
                print(f"🧠 Enhanced Planning: {plan.get('enhanced_planning', False)}")
                print(f"📊 Tasks: {len(plan.get('tasks', []))}")
                
                # Show task sequence
                for task in plan.get('tasks', []):
                    print(f"  {task['task_number']}. {task['description']} ({task['suggested_tool']})")
                
                # Test plan approval (simulate user approval)
                if result.get("awaiting_approval"):
                    print(f"\n🔄 Simulating plan approval...")
                    
                    approval_result = await agent.handle_user_response(
                        "approve", 
                        "test_user", 
                        plan
                    )
                    
                    if approval_result.get("success"):
                        print(f"✅ Plan execution initiated")
                        if approval_result.get("enhanced_execution"):
                            print(f"🚀 Used advanced workflow orchestrator")
                        print(f"📈 Status: {approval_result.get('status', 'N/A')}")
                    else:
                        print(f"❌ Plan execution failed: {approval_result.get('error', 'Unknown error')}")
                
            else:
                print(f"❌ Plan creation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
        
        print()
    
    print("🎯 Enhanced Planning Integration Test Complete")

async def test_planning_features():
    """Test specific enhanced planning features."""
    
    print("\n🔬 Testing Specific Planning Features")
    print("=" * 50)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test 1: Tool Chaining Detection
    print("\n1. Testing Tool Chaining Detection")
    request = "Search for Python tutorials, summarize the best ones, and email the summary"
    result = await agent.process_user_request(request, "test_user")
    
    if result.get("success"):
        plan = result.get("plan", {})
        tasks = plan.get("tasks", [])
        
        print(f"   Tasks created: {len(tasks)}")
        
        # Check for proper chaining
        has_search = any("search" in task.get("description", "").lower() for task in tasks)
        has_summarize = any("summarize" in task.get("description", "").lower() for task in tasks)
        has_email = any("email" in task.get("description", "").lower() for task in tasks)
        
        print(f"   ✅ Search task: {has_search}")
        print(f"   ✅ Summarize task: {has_summarize}")
        print(f"   ✅ Email task: {has_email}")
        
        if has_search and has_summarize and has_email:
            print("   🎯 Tool chaining detected successfully!")
        else:
            print("   ⚠️ Tool chaining may not be optimal")
    
    # Test 2: State Machine Modeling
    print("\n2. Testing State Machine Modeling")
    complex_request = "Find market data, analyze trends, create visualizations, save to drive, and notify team"
    result = await agent.process_user_request(complex_request, "test_user")
    
    if result.get("success"):
        plan = result.get("plan", {})
        
        print(f"   Enhanced planning: {plan.get('enhanced_planning', False)}")
        print(f"   Plan ID: {plan.get('plan_id', 'N/A')}")
        print(f"   Sequence: {plan.get('sequence_description', 'N/A')}")
        
        # Check for dependencies
        tasks_with_deps = [task for task in plan.get("tasks", []) if task.get("dependencies")]
        print(f"   Tasks with dependencies: {len(tasks_with_deps)}")
        
        if plan.get('enhanced_planning'):
            print("   🎯 State machine modeling active!")
        else:
            print("   ⚠️ Using fallback planning")
    
    # Test 3: Sequence Optimization
    print("\n3. Testing Sequence Optimization")
    optimization_request = "Get weather data and news, combine them, and create a daily briefing"
    result = await agent.process_user_request(optimization_request, "test_user")
    
    if result.get("success"):
        plan = result.get("plan", {})
        tasks = plan.get("tasks", [])
        
        print(f"   Total tasks: {len(tasks)}")
        print(f"   Data flow: {plan.get('data_flow', 'N/A')}")
        
        # Check for efficiency
        estimated_duration = sum(task.get('estimated_duration', 5) for task in tasks)
        print(f"   Estimated duration: {estimated_duration}s")
        
        if len(tasks) <= 4 and estimated_duration <= 30:
            print("   🎯 Sequence appears optimized!")
        else:
            print("   ⚠️ Sequence may need optimization")
    
    print("\n🎯 Planning Features Test Complete")

async def main():
    """Run all enhanced planning tests."""
    try:
        await test_enhanced_planning()
        await test_planning_features()
        
        print("\n" + "=" * 60)
        print("🎉 ALL ENHANCED PLANNING TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())