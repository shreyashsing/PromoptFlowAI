#!/usr/bin/env python3
"""
Test script to verify that UI updates are sent correctly after plan modification.
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

async def test_ui_update_after_modification():
    """Test that UI updates are sent after plan modification."""
    
    # Initialize components
    agent = TrueReActAgent()
    ui_manager = ReActUIManager()
    tool_registry = ToolRegistry()
    
    # Set up agent with UI manager
    agent.ui_manager = ui_manager
    agent.tool_registry = tool_registry
    
    # Initialize tool registry
    await tool_registry.initialize()
    
    # Create a mock plan
    mock_plan = {
        "summary": "Test workflow with webhook",
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
                "description": "Process data",
                "suggested_tool": "text_summarizer",
                "reasoning": "Process the data",
                "inputs": ["raw_data"],
                "outputs": ["processed_data"]
            }
        ],
        "data_flow": "webhook -> text_summarizer",
        "estimated_steps": "2",
        "original_request": "create a workflow with webhook and text processing"
    }
    
    user_id = "test_user_123"
    
    print("🧪 Testing UI update after plan modification...")
    
    # Start a UI session
    await ui_manager.start_session(user_id, "test modification")
    
    # Test the _present_plan_to_user method
    try:
        await agent._present_plan_to_user(mock_plan, user_id)
        print("✅ _present_plan_to_user executed successfully")
        
        # Check if UI update was sent
        session_trace = ui_manager.get_session_trace(user_id)
        updates = session_trace.get("reasoning_trace", [])
        
        print(f"📊 Total UI updates sent: {len(updates)}")
        for i, update in enumerate(updates):
            print(f"  {i+1}. {update.get('type', 'unknown')} - {update.get('content', '')[:100]}...")
        
        # Test plan refinement
        print("\n🔄 Testing plan refinement...")
        refined_plan = await agent._refine_plan_with_changes(
            mock_plan, 
            "remove the webhook and maintain everything else", 
            user_id
        )
        
        print("✅ Plan refinement completed")
        print(f"📋 Original tasks: {len(mock_plan.get('tasks', []))}")
        print(f"📋 Refined tasks: {len(refined_plan.get('tasks', []))}")
        
        # Check if webhook was removed
        webhook_tasks = [task for task in refined_plan.get('tasks', []) if 'webhook' in task.get('suggested_tool', '')]
        print(f"🔍 Webhook tasks remaining: {len(webhook_tasks)}")
        
        if len(webhook_tasks) == 0:
            print("✅ Webhook successfully removed from plan")
        else:
            print("❌ Webhook was not removed from plan")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ui_update_after_modification())