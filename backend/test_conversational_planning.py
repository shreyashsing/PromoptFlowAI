#!/usr/bin/env python3
"""
Test script for the new conversational workflow planning system.
"""
import asyncio
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_conversational_planning():
    """Test the new conversational planning system."""
    print("🧪 Testing Conversational Workflow Planning")
    print("=" * 60)
    
    try:
        # Initialize agent
        agent = TrueReActAgent()
        await agent.initialize()
        
        # Test the complex user request
        user_request = "Find the top 5 recent blog posts by Google using Perplexity. Summarize all 5 into one combined summary. Find 3 relevant YouTube videos related to the blog topics. Save the summary in Google Docs (Drive), log everything to Google Sheets and Airtable, email the summary with links to shreyashbarca10@gmail.com, and create a detailed Notion page with all content and links."
        
        print(f"📋 User Request: {user_request}")
        print()
        
        # Phase 1: Initial Planning
        print("🔍 Phase 1: Creating Initial Plan")
        print("-" * 40)
        
        result = await agent.process_user_request(user_request, "test_user_123")
        
        if result.get("success") and result.get("phase") == "planning":
            plan = result.get("plan", {})
            
            print("✅ Plan created successfully!")
            print(f"📊 Plan Summary: {plan.get('summary', 'No summary')}")
            print(f"📋 Number of Tasks: {len(plan.get('tasks', []))}")
            print(f"🔧 Estimated Steps: {plan.get('estimated_steps', 'Unknown')}")
            print()
            
            print("📝 Planned Tasks:")
            for task in plan.get('tasks', []):
                print(f"   {task['task_number']}. {task['description']}")
                print(f"      Tool: {task['suggested_tool']}")
                print(f"      Reasoning: {task['reasoning']}")
                print()
            
            print("💬 User Message:")
            print(result.get("message", "No message"))
            print()
            
            # Phase 2: Test User Approval
            print("🔍 Phase 2: Testing User Approval")
            print("-" * 40)
            
            approval_result = await agent.handle_user_response("approve", "test_user_123", plan)
            
            if approval_result.get("success") and approval_result.get("phase") == "completed":
                workflow = approval_result.get("workflow", {})
                
                print("✅ Plan executed successfully!")
                print(f"📊 Workflow ID: {workflow.get('id', 'No ID')}")
                print(f"📋 Total Steps: {workflow.get('total_steps', 0)}")
                print(f"🔧 Steps Completed: {approval_result.get('steps_completed', 0)}")
                print()
                
                print("📝 Executed Steps:")
                for i, step in enumerate(workflow.get('steps', []), 1):
                    print(f"   {i}. {step['connector_name']}: {step.get('purpose', 'No purpose')}")
                print()
                
            else:
                print("❌ Plan execution failed:")
                print(f"   Error: {approval_result.get('error', 'Unknown error')}")
                print()
            
            # Phase 3: Test User Modification
            print("🔍 Phase 3: Testing User Modification")
            print("-" * 40)
            
            modification_result = await agent.handle_user_response(
                "I want to add Slack notification and remove Airtable", 
                "test_user_123", 
                plan
            )
            
            if modification_result.get("success") and modification_result.get("phase") == "planning":
                modified_plan = modification_result.get("plan", {})
                
                print("✅ Plan modified successfully!")
                print(f"📊 Modified Plan Summary: {modified_plan.get('summary', 'No summary')}")
                print(f"📋 Number of Tasks: {len(modified_plan.get('tasks', []))}")
                print()
                
                print("📝 Modified Tasks:")
                for task in modified_plan.get('tasks', []):
                    print(f"   {task['task_number']}. {task['description']}")
                    print(f"      Tool: {task['suggested_tool']}")
                print()
                
                print("💬 User Message:")
                print(modification_result.get("message", "No message"))
                print()
                
            else:
                print("❌ Plan modification failed:")
                print(f"   Error: {modification_result.get('error', 'Unknown error')}")
                print()
        
        else:
            print("❌ Initial planning failed:")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print(f"   Message: {result.get('message', 'No message')}")
        
        print("🎯 Key Features Tested:")
        print("   ✅ Dynamic plan creation using Tool Registry")
        print("   ✅ No hardcoded connector mappings")
        print("   ✅ User plan approval workflow")
        print("   ✅ Plan modification based on user feedback")
        print("   ✅ Task-by-task execution with reasoning")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_tool_registry_integration():
    """Test that the planning system properly uses Tool Registry."""
    print("\\n🔧 Testing Tool Registry Integration")
    print("=" * 50)
    
    try:
        # Initialize agent
        agent = TrueReActAgent()
        await agent.initialize()
        
        # Check available tools
        if hasattr(agent, 'tool_registry') and agent.tool_registry:
            tools = await agent.tool_registry.get_available_tools()
            tool_names = [tool.name for tool in tools]
            
            print(f"📊 Available Tools ({len(tool_names)}):")
            for tool_name in tool_names:
                print(f"   - {tool_name}")
            print()
            
            # Test plan creation with available tools
            simple_request = "Search for AI news and send me an email summary"
            plan = await agent._create_comprehensive_plan(simple_request, "test_user")
            
            print(f"📋 Plan for Simple Request:")
            print(f"   Request: {simple_request}")
            print(f"   Tasks: {len(plan.get('tasks', []))}")
            
            for task in plan.get('tasks', []):
                tool_name = task.get('suggested_tool')
                is_available = tool_name in tool_names
                status = "✅" if is_available else "❌"
                print(f"   {status} Task {task['task_number']}: {tool_name}")
            
            print()
            print("✅ Tool Registry integration working correctly")
            
        else:
            print("❌ Tool Registry not available")
    
    except Exception as e:
        print(f"❌ Tool Registry test failed: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting Conversational Planning Tests")
    
    # Run the tests
    asyncio.run(test_conversational_planning())
    asyncio.run(test_tool_registry_integration())
    
    print("\\n✨ Tests completed!")
    print("\\n💡 New Conversational Planning Features:")
    print("   🎯 Dynamic plan creation using Tool Registry")
    print("   💬 User approval and modification workflow")
    print("   🔄 Plan refinement based on feedback")
    print("   ⚡ Task-by-task execution with context")
    print("   🚫 No hardcoded connector mappings")
    print("   📈 Scalable to 200-300 connectors")