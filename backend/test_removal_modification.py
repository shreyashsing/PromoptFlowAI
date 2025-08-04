#!/usr/bin/env python3
"""
Test script to verify removal modification functionality.
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

async def test_removal_modification():
    """Test removal modification functionality."""
    
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
    
    user_id = "test_user_removal"
    
    print("🧪 Testing Removal Modification")
    print("=" * 40)
    
    # Create a mock executed workflow with HTTP request
    executed_workflow = {
        "id": "workflow_456",
        "name": "Blog Processing Workflow",
        "description": "Process blog posts with multiple steps",
        "steps": [
            {
                "step_number": 1,
                "connector_name": "perplexity_search",
                "description": "Search for recent blog posts",
                "purpose": "Find blog posts",
                "parameters": {"query": "AI blog posts"},
                "outputs": ["blog_urls"]
            },
            {
                "step_number": 2,
                "connector_name": "http_request",
                "description": "Fetch blog content via HTTP",
                "purpose": "Get full blog content",
                "parameters": {"urls": "{perplexity_search.blog_urls}"},
                "outputs": ["blog_content"]
            },
            {
                "step_number": 3,
                "connector_name": "text_summarizer",
                "description": "Summarize blog content",
                "purpose": "Create summaries",
                "parameters": {"content": "{http_request.blog_content}"},
                "outputs": ["summaries"]
            }
        ],
        "created_at": "2025-08-02T10:00:00Z",
        "status": "completed"
    }
    
    # Create session context
    session_context = {
        "executed_workflow": executed_workflow,
        "original_plan": {
            "summary": "Process blog posts with HTTP fetching",
            "tasks": [
                {"task_number": 1, "suggested_tool": "perplexity_search"},
                {"task_number": 2, "suggested_tool": "http_request"},
                {"task_number": 3, "suggested_tool": "text_summarizer"}
            ]
        },
        "user_id": user_id,
        "completed_at": 1722600000,
        "awaiting_approval": False
    }
    
    print("📋 Original Workflow:")
    for step in executed_workflow["steps"]:
        print(f"  {step['step_number']}. {step['description']} ({step['connector_name']})")
    
    # Test removal request
    removal_request = "remove the Http request and maintain everything."
    
    print(f"\n👤 User request: '{removal_request}'")
    
    try:
        # Test the workflow modification
        result = await agent.handle_workflow_modification(
            removal_request, 
            user_id, 
            session_context
        )
        
        print(f"📊 Result success: {result.get('success', False)}")
        
        if result.get("success"):
            print("✅ Modification applied successfully")
            print(f"💬 Message: {result.get('message', '')[:300]}...")
            
            # Check if changes were applied
            changes = result.get("changes", [])
            print(f"🔧 Changes applied: {len(changes)}")
            
            for change in changes:
                print(f"  - {change}")
            
            # Show modified workflow
            modified_workflow = result.get("workflow", {})
            if modified_workflow.get("steps"):
                print("\n📋 Modified Workflow:")
                for step in modified_workflow["steps"]:
                    modified_indicator = " (MODIFIED)" if step.get("modified") else ""
                    print(f"  {step['step_number']}. {step['description']} ({step['connector_name']}){modified_indicator}")
                
                # Check if HTTP request was removed
                http_steps = [s for s in modified_workflow["steps"] if s.get("connector_name") == "http_request"]
                print(f"\n🔍 HTTP request steps remaining: {len(http_steps)}")
                
                if len(http_steps) == 0:
                    print("✅ HTTP request successfully removed")
                else:
                    print("❌ HTTP request was NOT removed")
        else:
            print("❌ Modification failed")
            print(f"💬 Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_removal_modification())