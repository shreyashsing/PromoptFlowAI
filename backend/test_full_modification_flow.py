#!/usr/bin/env python3
"""
Test script to simulate the full modification flow that was failing in the logs.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent
from app.services.react_ui_manager import ReActUIManager
from app.services.tool_registry import ToolRegistry
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_modification_flow():
    """Test the complete modification flow as seen in the logs."""
    
    # Initialize components
    agent = TrueReActAgent()
    ui_manager = ReActUIManager()
    tool_registry = ToolRegistry()
    
    # Set up agent with UI manager and tool registry
    agent.ui_manager = ui_manager
    agent.tool_registry = tool_registry
    
    # Initialize tool registry
    await tool_registry.initialize()
    await agent.initialize()
    
    # Create a session context similar to what's in the logs
    session_id = "react_1754139180"
    user_id = "9d729df3-e297-4716-8141-c91d23e1e300"
    
    # Create a mock plan that includes webhook (similar to what would be in session)
    mock_current_plan = {
        "summary": "Workflow with webhook and other components",
        "tasks": [
            {
                "task_number": 1,
                "description": "Send webhook notification",
                "suggested_tool": "webhook",
                "reasoning": "User wants to send notifications",
                "inputs": ["data"],
                "outputs": ["notification_sent"]
            },
            {
                "task_number": 2,
                "description": "Process data with Google Sheets",
                "suggested_tool": "google_sheets",
                "reasoning": "Process data in spreadsheet",
                "inputs": ["raw_data"],
                "outputs": ["processed_data"]
            },
            {
                "task_number": 3,
                "description": "Summarize results",
                "suggested_tool": "text_summarizer",
                "reasoning": "Create summary of results",
                "inputs": ["processed_data"],
                "outputs": ["summary"]
            }
        ],
        "data_flow": "webhook -> google_sheets -> text_summarizer",
        "estimated_steps": "3",
        "original_request": "create a workflow with webhook and data processing"
    }
    
    # Start UI session
    await ui_manager.start_session(session_id, "remove the webhook and maintain the everything of the workflow")
    
    print("🧪 Testing full modification flow...")
    print(f"📋 Original plan has {len(mock_current_plan['tasks'])} tasks")
    
    # Test the handle_user_response method (this is what's called in the actual flow)
    try:
        user_response = "remove the webhook and maintain the everything of the workflow"
        
        print(f"👤 User response: {user_response}")
        
        # This simulates the actual flow from the logs
        result = await agent.handle_user_response(user_response, user_id, mock_current_plan)
        
        print("✅ handle_user_response completed successfully")
        print(f"📊 Result keys: {list(result.keys())}")
        print(f"🎯 Success: {result.get('success')}")
        print(f"📝 Phase: {result.get('phase')}")
        print(f"⏳ Awaiting approval: {result.get('awaiting_approval')}")
        
        if 'plan' in result:
            refined_plan = result['plan']
            print(f"📋 Refined plan has {len(refined_plan.get('tasks', []))} tasks")
            
            # Check if webhook was removed
            webhook_tasks = [task for task in refined_plan.get('tasks', []) if 'webhook' in task.get('suggested_tool', '')]
            print(f"🔍 Webhook tasks remaining: {len(webhook_tasks)}")
            
            if len(webhook_tasks) == 0:
                print("✅ Webhook successfully removed from plan")
            else:
                print("❌ Webhook was not removed from plan")
                
            # Show remaining tasks
            print("\n📋 Remaining tasks:")
            for i, task in enumerate(refined_plan.get('tasks', []), 1):
                print(f"  {i}. {task.get('description')} ({task.get('suggested_tool')})")
        
        if 'message' in result:
            print(f"\n💬 Message to user: {result['message'][:200]}...")
        
        # Check UI updates
        session_trace = ui_manager.get_session_trace(session_id)
        reasoning_updates = session_trace.get("reasoning_trace", [])
        print(f"\n📊 Total reasoning updates sent: {len(reasoning_updates)}")
        
        for i, update in enumerate(reasoning_updates):
            print(f"  {i+1}. {update.get('type', 'unknown')} - {update.get('content', '')[:100]}...")
        
        # Also check the UI history (stored separately)
        ui_history = ui_manager.reasoning_history.get(session_id, [])
        print(f"📊 Total UI history entries: {len(ui_history)}")
        
        for i, entry in enumerate(ui_history):
            update = entry.get('update', {})
            print(f"  {i+1}. {update.get('type', 'unknown')} - {update.get('message', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_modification_flow())