#!/usr/bin/env python3
"""
Test script to verify parameter modification functionality.
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

async def test_parameter_modification():
    """Test parameter modification functionality."""
    
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
    
    user_id = "test_user_params"
    
    print("🧪 Testing Parameter Modification")
    print("=" * 40)
    
    # Create a workflow with Gmail connector
    executed_workflow = {
        "id": "workflow_gmail",
        "name": "Email Processing Workflow",
        "description": "Workflow with Gmail connector",
        "steps": [
            {
                "step_number": 1,
                "connector_name": "perplexity_search",
                "description": "Search for blog posts",
                "purpose": "Find relevant content",
                "parameters": {
                    "query": "AI blog posts",
                    "action": "search"
                },
                "outputs": ["blog_data"]
            },
            {
                "step_number": 2,
                "connector_name": "text_summarizer",
                "description": "Summarize content",
                "purpose": "Create summary",
                "parameters": {
                    "content": "{perplexity_search.blog_data}",
                    "action": "summarize"
                },
                "outputs": ["summary"]
            },
            {
                "step_number": 3,
                "connector_name": "gmail_connector",
                "description": "Send email with summary",
                "purpose": "Email the results",
                "parameters": {
                    "to": "user@example.com",
                    "subject": "Blog Summary",
                    "html_body": "{text_summarizer.summary}",
                    "action": "send"
                },
                "outputs": ["email_sent"]
            }
        ],
        "created_at": "2025-08-03T09:00:00Z",
        "status": "completed"
    }
    
    # Create session context
    session_context = {
        "executed_workflow": executed_workflow,
        "original_plan": {
            "summary": "Email processing workflow",
            "tasks": [
                {"task_number": 1, "suggested_tool": "perplexity_search"},
                {"task_number": 2, "suggested_tool": "text_summarizer"},
                {"task_number": 3, "suggested_tool": "gmail_connector"}
            ]
        },
        "user_id": user_id,
        "completed_at": 1722600000,
        "awaiting_approval": False
    }
    
    print("📋 Original Workflow:")
    for step in executed_workflow["steps"]:
        print(f"  {step['step_number']}. {step['description']} ({step['connector_name']})")
        # Show current parameters
        params = step.get("parameters", {})
        for key, value in params.items():
            print(f"     {key}: {value}")
    
    # Test parameter modification scenarios
    test_scenarios = [
        {
            "name": "Gmail Email Body Visibility Issue",
            "request": "i cannot see the email body in Gmail, can you recheck it.",
            "expected": "Should modify Gmail parameters to improve email body visibility"
        },
        {
            "name": "Data Format Issue",
            "request": "the summary data is not showing properly in the email",
            "expected": "Should adjust formatting parameters"
        },
        {
            "name": "Connection Issue",
            "request": "Gmail connection keeps failing, please fix it",
            "expected": "Should add retry logic and timeout parameters"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test Scenario {i}: {scenario['name']}")
        print(f"👤 User request: '{scenario['request']}'")
        print(f"🎯 Expected: {scenario['expected']}")
        
        try:
            # Test the parameter modification
            result = await agent.handle_workflow_modification(
                scenario["request"], 
                user_id, 
                session_context
            )
            
            print(f"📊 Result success: {result.get('success', False)}")
            
            if result.get("success"):
                print("✅ Parameter modification completed")
                
                # Check changes applied
                changes = result.get("changes", [])
                print(f"🔧 Changes applied: {len(changes)}")
                
                for change in changes:
                    print(f"  - {change}")
                
                # Show modified workflow
                modified_workflow = result.get("workflow", {})
                if modified_workflow.get("steps"):
                    print("\n📋 Modified Parameters:")
                    
                    for step in modified_workflow["steps"]:
                        if step.get("parameter_modified"):
                            print(f"  {step['step_number']}. {step['description']} ({step['connector_name']}) - MODIFIED")
                            
                            # Show parameter changes
                            current_params = step.get("parameters", {})
                            original_params = step.get("original_parameters", {})
                            
                            for key, new_value in current_params.items():
                                old_value = original_params.get(key, "not set")
                                if str(old_value) != str(new_value):
                                    print(f"     {key}: {old_value} → {new_value}")
                            
                            # Show modification reason
                            reason = step.get("parameter_modification_reason", "")
                            if reason:
                                print(f"     Reason: {reason}")
                        else:
                            print(f"  {step['step_number']}. {step['description']} ({step['connector_name']}) - unchanged")
            else:
                print("❌ Parameter modification failed")
                print(f"💬 Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error in scenario {i}: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_parameter_modification())