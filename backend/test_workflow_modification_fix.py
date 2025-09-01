#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent

async def test_workflow_modification_fix():
    """Test that workflow modification handles float task numbers correctly."""
    
    print("🧪 Testing workflow modification with float task number...")
    
    # Create agent instance
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Create a sample workflow
    workflow = {
        "steps": [
            {
                "task_number": 1,
                "connector_name": "youtube",
                "parameters": {"video_url": "https://example.com"},
                "purpose": "Extract video content"
            },
            {
                "task_number": 2,
                "connector_name": "text_summarizer",
                "parameters": {"text": "{youtube.result}"},
                "purpose": "Summarize content"
            }
        ],
        "total_steps": 2
    }
    
    # Create a change with float task number (like the AI generated)
    change = {
        "type": "task_addition",
        "task_number": 3.5,  # This was causing the error
        "new_connector": "code",
        "reason": "Insert a transcription step after extracting video content from YouTube"
    }
    
    print(f"📝 Original workflow has {len(workflow['steps'])} steps")
    print(f"🔧 Adding task at position {change['task_number']} (float)")
    
    # Test the fix
    try:
        result = await agent._add_task_to_workflow(workflow, change, "test_user")
        
        if result.get("success"):
            print("✅ Workflow modification succeeded!")
            print(f"📊 New workflow has {len(workflow['steps'])} steps")
            
            # Print the updated workflow
            for i, step in enumerate(workflow["steps"]):
                print(f"   Step {step.get('task_number', i+1)}: {step.get('connector_name')} - {step.get('purpose')}")
                
            return True
        else:
            print(f"❌ Workflow modification failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"💥 Exception during workflow modification: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow_modification_fix())
    if success:
        print("\n🎉 Test passed! The float task number fix works correctly.")
    else:
        print("\n💔 Test failed! The fix needs more work.")