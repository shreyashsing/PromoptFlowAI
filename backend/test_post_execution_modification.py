#!/usr/bin/env python3
"""
Test script to verify post-execution workflow modification functionality.
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

async def test_post_execution_modification():
    """Test post-execution workflow modification functionality."""
    
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
    
    user_id = "test_user_modification"
    
    print("🧪 Testing Post-Execution Workflow Modification")
    print("=" * 60)
    
    # Create a mock executed workflow (simulating a completed workflow)
    executed_workflow = {
        "id": "workflow_123",
        "name": "Blog Research Workflow",
        "description": "Find recent blog posts and summarize them",
        "steps": [
            {
                "step_number": 1,
                "connector_name": "perplexity_search",
                "description": "Search for recent blog posts using Perplexity",
                "purpose": "Find the latest blog posts on AI",
                "parameters": {
                    "query": "recent AI blog posts",
                    "action": "search"
                },
                "outputs": ["blog_posts_list"]
            },
            {
                "step_number": 2,
                "connector_name": "text_summarizer",
                "description": "Summarize the blog posts",
                "purpose": "Create concise summaries",
                "parameters": {
                    "content": "{perplexity_search.blog_posts_list}",
                    "action": "summarize"
                },
                "outputs": ["summaries"]
            },
            {
                "step_number": 3,
                "connector_name": "google_sheets",
                "description": "Save summaries to Google Sheets",
                "purpose": "Store results for later reference",
                "parameters": {
                    "data": "{text_summarizer.summaries}",
                    "action": "write"
                },
                "outputs": ["sheet_url"]
            }
        ],
        "created_at": "2025-08-02T10:00:00Z",
        "status": "completed"
    }
    
    # Create session context with executed workflow
    session_context = {
        "executed_workflow": executed_workflow,
        "original_plan": {
            "summary": "Research and summarize recent AI blog posts",
            "tasks": [
                {"task_number": 1, "suggested_tool": "perplexity_search"},
                {"task_number": 2, "suggested_tool": "text_summarizer"},
                {"task_number": 3, "suggested_tool": "google_sheets"}
            ]
        },
        "user_id": user_id,
        "completed_at": 1722600000,
        "awaiting_approval": False
    }
    
    print("📋 Original Workflow:")
    for step in executed_workflow["steps"]:
        print(f"  {step['step_number']}. {step['description']} ({step['connector_name']})")
    
    # Test different modification scenarios
    test_scenarios = [
        {
            "name": "Replace Perplexity with Text Summarizer",
            "request": "I want to use text_summarizer instead of perplexity for searching",
            "expected_change": "perplexity_search -> text_summarizer"
        },
        {
            "name": "Replace Google Sheets with Airtable",
            "request": "change google sheets to airtable",
            "expected_change": "google_sheets -> airtable"
        },
        {
            "name": "Non-modification request",
            "request": "create a new workflow for email automation",
            "expected_change": "should_create_new_workflow"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test Scenario {i}: {scenario['name']}")
        print(f"👤 User request: '{scenario['request']}'")
        
        try:
            # Test the workflow modification
            result = await agent.handle_workflow_modification(
                scenario["request"], 
                user_id, 
                session_context
            )
            
            print(f"📊 Result: {result.get('success', False)}")
            
            if result.get("success"):
                if result.get("modification_applied"):
                    print("✅ Modification applied successfully")
                    print(f"💬 Message: {result.get('message', '')[:200]}...")
                    
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
                else:
                    print("🆕 Treated as new workflow request")
                    print(f"💬 Message: {result.get('message', '')[:200]}...")
            else:
                print("❌ Modification failed")
                print(f"💬 Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error in scenario {i}: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
    
    # Test modification analysis directly
    print("\n🧪 Testing Modification Analysis")
    print("=" * 40)
    
    analysis_tests = [
        "use openai instead of perplexity",
        "replace google sheets with notion",
        "create a new email workflow"
    ]
    
    for request in analysis_tests:
        print(f"\n👤 Request: '{request}'")
        
        try:
            analysis = await agent._analyze_modification_request(
                request, 
                executed_workflow, 
                session_context["original_plan"]
            )
            
            print(f"🧠 Is modification: {analysis.get('is_modification', False)}")
            print(f"🎯 Confidence: {analysis.get('confidence', 0.0):.2f}")
            print(f"💭 Reasoning: {analysis.get('reasoning', 'No reasoning')}")
            
            changes = analysis.get('changes', [])
            if changes:
                print(f"🔧 Proposed changes: {len(changes)}")
                for change in changes:
                    print(f"  - {change.get('type', 'unknown')}: {change.get('current_connector', 'N/A')} -> {change.get('new_connector', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error analyzing request: {e}")

if __name__ == "__main__":
    asyncio.run(test_post_execution_modification())