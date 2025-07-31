#!/usr/bin/env python3
"""
Test to verify the ConversationState import fix.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_conversation_state_import():
    """Test that ConversationState can be imported and used."""
    print("🧪 Testing ConversationState import fix...")
    
    try:
        # Test 1: Import ConversationState from models
        from app.models.base import ConversationState
        print("✅ ConversationState imported from models.base")
        
        # Test 2: Check all states are available
        states = [
            ConversationState.INITIAL,
            ConversationState.PLANNING,
            ConversationState.CONFIGURING,
            ConversationState.CONFIRMING,
            ConversationState.APPROVED,
            ConversationState.EXECUTING
        ]
        print(f"✅ All conversation states available: {[s.value for s in states]}")
        
        # Test 3: Import from API module (this was failing before)
        from app.api.agent import continue_workflow_build
        print("✅ continue_workflow_build function imported successfully")
        
        # Test 4: Test the integrated workflow agent
        from app.services.integrated_workflow_agent import get_integrated_workflow_agent
        agent = await get_integrated_workflow_agent()
        print("✅ Integrated workflow agent initialized")
        
        print("\n🎉 All tests passed! The ConversationState import fix is working.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_conversation_state_import())
    if success:
        print("\n✅ ConversationState import fix verified successfully!")
    else:
        print("\n❌ ConversationState import fix failed!")
        sys.exit(1)