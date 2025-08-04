#!/usr/bin/env python3
"""
Debug script to see what the AI is reasoning for completion detection.
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_ai_reasoning():
    """Test what the AI is actually reasoning for completion."""
    print("🧪 Testing AI Reasoning for Completion Detection")
    print("=" * 60)
    
    try:
        # Initialize agent
        agent = TrueReActAgent()
        await agent.initialize()
        
        # Test the complex user request
        user_request = "Find the top 5 recent blog posts by Google using Perplexity. Summarize all 5 into one combined summary. Find 3 relevant YouTube videos related to the blog topics. Save the summary in Google Docs (Drive), log everything to Google Sheets and Airtable, email the summary with links to shreyashbarca10@gmail.com, and create a detailed Notion page with all content and links."
        
        mock_analysis = {
            "original_request": user_request
        }
        
        # Test the 8-step complete scenario
        complete_steps = [
            {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
            {"connector_name": "text_summarizer", "purpose": "Summarize content"},
            {"connector_name": "youtube", "purpose": "Find related videos"},
            {"connector_name": "google_drive", "purpose": "Save to Google Docs"},
            {"connector_name": "google_sheets", "purpose": "Log to spreadsheet"},
            {"connector_name": "airtable", "purpose": "Store in database"},
            {"connector_name": "gmail_connector", "purpose": "Send email"},
            {"connector_name": "notion", "purpose": "Create detailed page"}
        ]
        
        print(f"📋 User Request: {user_request}")
        print()
        print(f"🔧 Complete Workflow Steps ({len(complete_steps)}):")
        for i, step in enumerate(complete_steps, 1):
            print(f"   {i}. {step['connector_name']}: {step['purpose']}")
        print()
        
        # Manually call the AI reasoning to see what it says
        if hasattr(agent, '_client') and agent._client:
            print("🤖 Testing AI reasoning directly...")
            
            # Get available tools
            available_tools = []
            tool_descriptions = {}
            
            if hasattr(agent, 'tool_registry') and agent.tool_registry:
                tools = await agent.tool_registry.get_available_tools()
                for tool in tools:
                    available_tools.append(tool.name)
                    tool_descriptions[tool.name] = tool.description
            
            # Create the same prompt the agent uses
            available_tools_list = "\\n".join([
                f"- {tool}: {tool_descriptions.get(tool, 'Available connector')}" 
                for tool in available_tools
            ])
            
            completed_connectors = [step['connector_name'] for step in complete_steps]
            
            completion_prompt = f"""
            ORIGINAL USER REQUEST: "{user_request}"
            
            AVAILABLE TOOLS IN SYSTEM:
            {available_tools_list}
            
            WORKFLOW STEPS COMPLETED SO FAR:
            {chr(10).join([f"{i+1}. {step['connector_name']}: {step.get('purpose', 'No purpose')}" for i, step in enumerate(complete_steps)])}
            
            INTELLIGENT COMPLETION ANALYSIS:
            
            Your task is to analyze if the user's request has been FULLY satisfied by the completed workflow steps.
            
            ANALYSIS PROCESS:
            1. Break down the user request into individual requirements/actions
            2. For each requirement, identify which available tool(s) could fulfill it
            3. Check if those tools have been used in the completed steps
            4. Determine if ALL requirements have been addressed
            
            COMPLETION CRITERIA:
            - COMPLETE: Every requirement from the user request has been addressed by the completed steps
            - INCOMPLETE: One or more requirements are still missing from the workflow
            
            IMPORTANT GUIDELINES:
            - Consider the user's intent, not just literal word matching
            - If the user mentions specific platforms/services, ensure those tools are used
            - If the user requests multiple outputs (save, email, log, etc.), ensure all are covered
            - Be thorough - missing even one requirement means INCOMPLETE
            
            RESPOND WITH EXACTLY THIS JSON FORMAT:
            {{"status": "COMPLETE", "reasoning": "All requirements satisfied: [list what was completed]"}} 
            OR
            {{"status": "INCOMPLETE", "reasoning": "Missing requirements: [list what's missing]"}}
            
            Be precise and thorough in your analysis.
            """
            
            print("📝 AI Prompt:")
            print(completion_prompt)
            print()
            print("🤖 AI Response:")
            
            try:
                ai_response = await agent._ai_reason(completion_prompt)
                print(f"Raw response: {ai_response}")
                print()
                
                # Parse the response like the agent does
                completion_status = None
                
                if isinstance(ai_response, dict):
                    if 'status' in ai_response:
                        completion_status = ai_response['status'].strip().upper()
                        reasoning = ai_response.get('reasoning', 'No reasoning provided')
                        print(f"✅ Parsed Status: {completion_status}")
                        print(f"💭 AI Reasoning: {reasoning}")
                    elif 'content' in ai_response:
                        print(f"📄 AI Content Response: {ai_response['content']}")
                elif isinstance(ai_response, str):
                    print(f"📝 AI String Response: {ai_response}")
                    try:
                        import json
                        parsed = json.loads(ai_response)
                        if 'status' in parsed:
                            completion_status = parsed['status'].strip().upper()
                            reasoning = parsed.get('reasoning', 'No reasoning provided')
                            print(f"✅ Parsed Status: {completion_status}")
                            print(f"💭 AI Reasoning: {reasoning}")
                    except:
                        print("❌ Could not parse as JSON")
                
            except Exception as e:
                print(f"❌ AI reasoning failed: {e}")
        else:
            print("⚠️  No AI client available - using fallback logic")
            
            # Test the fallback logic
            print("🔧 Testing fallback logic...")
            is_complete = await agent.is_workflow_complete(mock_analysis, complete_steps)
            print(f"Fallback result: {'COMPLETE' if is_complete else 'INCOMPLETE'}")
        
        print()
        print("🎯 Analysis:")
        print("   - The 8-step workflow should cover all requirements")
        print("   - If AI says INCOMPLETE, we need to understand why")
        print("   - This will help us tune the completion detection")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting AI Reasoning Debug Test")
    
    # Run the test
    asyncio.run(test_ai_reasoning())
    
    print("\\n✨ Debug completed!")