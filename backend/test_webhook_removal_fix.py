#!/usr/bin/env python3
"""
Test script to verify webhook removal works correctly.
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

async def test_webhook_removal():
    """Test that webhook removal works correctly."""
    
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
    
    # Create a mock plan with webhook
    mock_plan = {
        "summary": "Workflow with webhook, Google Sheets, and text summarizer",
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
    
    user_id = "test_user_webhook_removal"
    
    print("🧪 Testing webhook removal...")
    print(f"📋 Original plan has {len(mock_plan['tasks'])} tasks")
    
    # Show original tasks
    print("\n📋 Original tasks:")
    for i, task in enumerate(mock_plan['tasks'], 1):
        print(f"  {i}. {task['description']} ({task['suggested_tool']})")
    
    # Test different removal phrases
    test_phrases = [
        "remove the webhook and maintain everything else",
        "just remove the webhook and maintain the everything regarding workflow",
        "remove webhook",
        "delete the webhook"
    ]
    
    for phrase in test_phrases:
        print(f"\n🧪 Testing phrase: '{phrase}'")
        
        try:
            # Test the refinement directly
            refined_plan = await agent._refine_plan_with_changes(mock_plan, phrase, user_id)
            
            original_count = len(mock_plan['tasks'])
            refined_count = len(refined_plan.get('tasks', []))
            
            print(f"📊 Task count: {original_count} -> {refined_count}")
            
            # Check if webhook was removed
            webhook_tasks = [task for task in refined_plan.get('tasks', []) if task.get('suggested_tool') == 'webhook']
            print(f"🔍 Webhook tasks remaining: {len(webhook_tasks)}")
            
            if len(webhook_tasks) == 0:
                print("✅ Webhook successfully removed")
            else:
                print("❌ Webhook was NOT removed")
            
            # Show remaining tasks
            print("📋 Remaining tasks:")
            for i, task in enumerate(refined_plan.get('tasks', []), 1):
                print(f"  {i}. {task.get('description')} ({task.get('suggested_tool')})")
            
        except Exception as e:
            print(f"❌ Error testing phrase '{phrase}': {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_webhook_removal())