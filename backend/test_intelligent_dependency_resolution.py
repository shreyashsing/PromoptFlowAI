#!/usr/bin/env python3
"""
Test script to verify intelligent dependency resolution functionality.
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

async def test_intelligent_dependency_resolution():
    """Test intelligent dependency resolution functionality."""
    
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
    
    user_id = "test_user_dependency"
    
    print("🧪 Testing Intelligent Dependency Resolution")
    print("=" * 50)
    
    # Create a complex workflow with dependencies
    executed_workflow = {
        "id": "workflow_complex",
        "name": "Complex Blog Processing Workflow",
        "description": "Multi-step workflow with dependencies",
        "steps": [
            {
                "step_number": 1,
                "connector_name": "perplexity_search",
                "description": "Search for recent AI blog posts",
                "purpose": "Find relevant blog posts",
                "parameters": {
                    "query": "recent AI blog posts",
                    "action": "search"
                },
                "outputs": ["blog_urls", "blog_titles"]
            },
            {
                "step_number": 2,
                "connector_name": "http_request",
                "description": "Fetch full blog content",
                "purpose": "Get complete blog content from URLs",
                "parameters": {
                    "urls": "{perplexity_search.blog_urls}",
                    "action": "fetch_content"
                },
                "outputs": ["blog_content", "blog_metadata"]
            },
            {
                "step_number": 3,
                "connector_name": "text_summarizer",
                "description": "Summarize blog content",
                "purpose": "Create concise summaries",
                "parameters": {
                    "content": "{http_request.blog_content}",
                    "metadata": "{http_request.blog_metadata}",
                    "action": "summarize"
                },
                "outputs": ["summaries", "key_points"]
            },
            {
                "step_number": 4,
                "connector_name": "google_sheets",
                "description": "Save results to spreadsheet",
                "purpose": "Store summaries and metadata",
                "parameters": {
                    "data": "{text_summarizer.summaries}",
                    "titles": "{perplexity_search.blog_titles}",
                    "key_points": "{text_summarizer.key_points}",
                    "action": "write"
                },
                "outputs": ["sheet_url"]
            }
        ],
        "created_at": "2025-08-02T10:00:00Z",
        "status": "completed"
    }
    
    # Create session context
    session_context = {
        "executed_workflow": executed_workflow,
        "original_plan": {
            "summary": "Complex blog processing with dependencies",
            "tasks": [
                {"task_number": 1, "suggested_tool": "perplexity_search"},
                {"task_number": 2, "suggested_tool": "http_request"},
                {"task_number": 3, "suggested_tool": "text_summarizer"},
                {"task_number": 4, "suggested_tool": "google_sheets"}
            ]
        },
        "user_id": user_id,
        "completed_at": 1722600000,
        "awaiting_approval": False
    }
    
    print("📋 Original Complex Workflow:")
    for step in executed_workflow["steps"]:
        print(f"  {step['step_number']}. {step['description']} ({step['connector_name']})")
        # Show key dependencies
        params = step.get("parameters", {})
        dependencies = [k for k, v in params.items() if isinstance(v, str) and "{" in v]
        if dependencies:
            print(f"     Dependencies: {dependencies}")
    
    # Test removal with dependency resolution
    removal_request = "remove the http_request connector and maintain workflow functionality"
    
    print(f"\n👤 User request: '{removal_request}'")
    print("\n🧠 Expected intelligent behavior:")
    print("  1. Remove http_request step")
    print("  2. Update text_summarizer to use perplexity_search output instead")
    print("  3. Maintain google_sheets dependencies")
    print("  4. Ensure workflow remains functional")
    
    try:
        # Test the workflow modification with dependency resolution
        result = await agent.handle_workflow_modification(
            removal_request, 
            user_id, 
            session_context
        )
        
        print(f"\n📊 Result success: {result.get('success', False)}")
        
        if result.get("success"):
            print("✅ Modification with dependency resolution completed")
            
            # Check changes applied
            changes = result.get("changes", [])
            print(f"\n🔧 Total changes applied: {len(changes)}")
            
            for i, change in enumerate(changes, 1):
                print(f"  {i}. {change}")
            
            # Analyze the modified workflow
            modified_workflow = result.get("workflow", {})
            if modified_workflow.get("steps"):
                print("\n📋 Modified Workflow with Dependency Resolution:")
                
                for step in modified_workflow["steps"]:
                    indicators = []
                    if step.get("modified"):
                        indicators.append("MODIFIED")
                    if step.get("dependency_resolved"):
                        indicators.append("DEPS_RESOLVED")
                    if step.get("ai_dependency_fix"):
                        indicators.append("AI_FIXED")
                    
                    indicator_str = f" ({', '.join(indicators)})" if indicators else ""
                    print(f"  {step['step_number']}. {step['description']} ({step['connector_name']}){indicator_str}")
                    
                    # Show updated parameters
                    params = step.get("parameters", {})
                    for param_key, param_value in params.items():
                        if isinstance(param_value, str) and "{" in param_value:
                            print(f"     {param_key}: {param_value}")
                    
                    # Show dependency resolution info
                    if step.get("dependency_resolution_reason"):
                        print(f"     Reason: {step['dependency_resolution_reason']}")
                    if step.get("ai_fix_reason"):
                        print(f"     AI Fix: {step['ai_fix_reason']}")
                
                # Verify dependency integrity
                print("\n🔍 Dependency Integrity Check:")
                
                # Check if any step still references the removed connector
                broken_dependencies = []
                for step in modified_workflow["steps"]:
                    params = step.get("parameters", {})
                    for param_key, param_value in params.items():
                        if isinstance(param_value, str) and "{http_request." in param_value:
                            broken_dependencies.append(f"{step['connector_name']}.{param_key}")
                
                if broken_dependencies:
                    print(f"❌ Found broken dependencies: {broken_dependencies}")
                else:
                    print("✅ No broken dependencies found - workflow integrity maintained")
                
                # Check if text_summarizer now uses perplexity_search
                text_summarizer_step = None
                for step in modified_workflow["steps"]:
                    if step.get("connector_name") == "text_summarizer":
                        text_summarizer_step = step
                        break
                
                if text_summarizer_step:
                    params = text_summarizer_step.get("parameters", {})
                    uses_perplexity = any("{perplexity_search." in str(v) for v in params.values())
                    if uses_perplexity:
                        print("✅ Text summarizer now uses perplexity_search output")
                    else:
                        print("⚠️ Text summarizer may not be properly connected to perplexity_search")
        else:
            print("❌ Modification failed")
            print(f"💬 Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_intelligent_dependency_resolution())