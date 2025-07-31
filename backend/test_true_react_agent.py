#!/usr/bin/env python3
"""
Comprehensive test for the Clean ReAct System.
Demonstrates dynamic reasoning, step-by-step building, and real-time UI updates.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent
from app.services.react_ui_manager import ReActUIManager
from app.services.tool_registry import ToolRegistry

async def test_clean_react_system():
    """Test the complete Clean ReAct System."""
    
    print("🤖 Testing Clean ReAct System")
    print("="*80)
    
    # Test 1: Tool Registry
    print("\n1️⃣ Testing Tool Registry (Dynamic Connector Discovery)")
    registry = ToolRegistry()
    await registry.initialize()
    
    connectors = await registry.get_tool_metadata()
    print(f"   ✅ Discovered {len(connectors)} connectors dynamically")
    for connector in connectors[:3]:  # Show first 3
        print(f"   - {connector['name']}: {connector.get('description', 'No description')[:50]}...")
    
    # Test 2: True ReAct Agent
    print(f"\n2️⃣ Testing True ReAct Agent (Dynamic Reasoning)")
    
    # Initialize agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    ui_manager = ReActUIManager()
    
    # Test request
    user_request = "Build me a workflow that finds the top 5 recent blogs posted by Google using Perplexity, summarizes all 5 into one combined summary, and sends the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body"
    user_id = "test_user_123"
    session_id = "test_session_456"
    
    print(f"📝 User Request: {user_request}")
    print("\n🔄 Starting ReAct Process...")
    
    # Start UI session
    await ui_manager.start_session(session_id, user_request)
    
    # Process with ReAct agent
    result = await agent.process_user_request(user_request, user_id)
    
    print(f"\n📊 RESULT:")
    print(f"Success: {result['success']}")
    
    if result["success"]:
        workflow = result["workflow"]
        print(f"Workflow Name: {workflow['name']}")
        print(f"Description: {workflow['description']}")
        print(f"Total Steps: {workflow['total_steps']}")
        
        print(f"\n🔧 WORKFLOW STEPS:")
        for i, step in enumerate(workflow.get("steps", []), 1):
            print(f"{i}. {step['connector_name']}")
            print(f"   Purpose: {step['purpose']}")
            print(f"   Dependencies: {step.get('dependencies', [])}")
            print(f"   Parameters: {list(step.get('parameters', {}).keys())}")
            print()
        
        # Verify expected workflow structure
        step_names = [step['connector_name'] for step in workflow.get("steps", [])]
        print(f"🎯 VERIFICATION:")
        print(f"Steps created: {step_names}")
        
        # Check for logical workflow
        has_search = any("search" in name or "perplexity" in name for name in step_names)
        has_summarizer = any("summariz" in name or "text" in name for name in step_names)
        has_email = any("mail" in name or "gmail" in name for name in step_names)
        
        print(f"Has search component: {'✅' if has_search else '❌'}")
        print(f"Has summarizer component: {'✅' if has_summarizer else '❌'}")
        print(f"Has email component: {'✅' if has_email else '❌'}")
        
        if has_search and (has_summarizer or has_email):
            print("✅ SUCCESS: ReAct agent created a logical workflow!")
        else:
            print("❌ WARNING: Workflow may be incomplete")
    
    else:
        print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
    
    # Show reasoning trace
    print(f"\n🧠 REASONING TRACE:")
    for i, reasoning in enumerate(result.get("reasoning_trace", []), 1):
        print(f"{i}. {reasoning}")
    
    # Show UI session trace
    print(f"\n📱 UI SESSION TRACE:")
    session_trace = ui_manager.get_session_trace(session_id)
    for update in ui_manager.reasoning_history.get(session_id, []):
        print(f"[{update['timestamp']}] {update['update']['type']}: {update['update'].get('message', '')}")

async def test_react_reasoning():
    """Test just the reasoning component."""
    print("\n" + "="*60)
    print("🧠 Testing ReAct Reasoning Only")
    print("="*60)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    request = "Send an email to john@example.com with weather info for New York"
    
    print(f"📝 Request: {request}")
    
    # Test initial reasoning
    analysis = await agent.reason_about_requirements(request)
    print(f"\n🤔 Initial Analysis:")
    print(f"Reasoning: {analysis.get('reasoning', 'No reasoning available')}")
    
    # Test next step reasoning
    next_step = await agent.reason_next_step(analysis, [], request)
    print(f"\n⚡ Next Step:")
    print(f"Action: {next_step}")

async def test_multiple_scenarios():
    """Test multiple workflow scenarios to verify flexibility."""
    
    print("\n" + "="*80)
    print("🔄 Testing Multiple Scenarios (Flexibility)")
    print("="*80)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    scenarios = [
        "Send an email to john@example.com with today's weather",
        "Search for AI news and save to Google Sheets",
        "Get stock prices and send summary to Slack"
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Scenario: {scenario}")
        
        try:
            result = await agent.process_user_request(scenario, f"test_user_{i}")
            
            if result["success"]:
                steps = result["workflow"]["steps"]
                step_names = [step["connector_name"] for step in steps]
                print(f"   ✅ Created workflow: {' → '.join(step_names)}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_clean_react_system())
    asyncio.run(test_multiple_scenarios())