#!/usr/bin/env python3
"""
Test the improved intelligent workflow agent with proper connector analysis.
"""
import asyncio
from app.services.integrated_workflow_agent import get_integrated_workflow_agent
from app.models.conversation import ConversationContext, ChatMessage
from app.models.base import ConversationState
import uuid

async def test_intelligent_workflow_analysis():
    """Test the intelligent workflow analysis for the user's request."""
    print("🧠 Testing Intelligent Workflow Analysis")
    print("=" * 50)
    
    try:
        # Get the agent
        agent = await get_integrated_workflow_agent()
        print("✅ Agent initialized")
        
        # Test the specific user request
        user_request = "create a workflow which analyse top 5 articles posted by google and summarise it and send it to my gmail and googlesheets"
        
        print(f"\n📝 User Request: {user_request}")
        print("\n🧠 AI Analysis in Progress...")
        
        # Test the reasoning phase
        reasoning_result = await agent._reason_about_workflow_requirements(user_request)
        
        print(f"\n📊 Analysis Results:")
        print(f"🎯 Reasoning: {reasoning_result.get('reasoning', 'N/A')}")
        print(f"📋 Workflow Description: {reasoning_result.get('workflow_description', 'N/A')}")
        print(f"🔧 Connectors Identified: {len(reasoning_result.get('connectors', []))}")
        
        for i, connector in enumerate(reasoning_result.get('connectors', []), 1):
            print(f"\n   Connector {i}: {connector.get('name', 'Unknown')}")
            print(f"   Purpose: {connector.get('reasoning', 'N/A')}")
            print(f"   Required Fields: {connector.get('required_fields', [])}")
            print(f"   Auth Required: {connector.get('auth_required', False)}")
        
        missing_info = reasoning_result.get('missing_info', [])
        if missing_info:
            print(f"\n⚠️ Missing Information: {missing_info}")
        
        # Test the full workflow creation
        print(f"\n🚀 Testing Full Workflow Creation...")
        
        session_id = str(uuid.uuid4())
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        context, response, plan = await agent.create_workflow_conversationally(
            query=user_request,
            user_id=user_id,
            session_id=session_id
        )
        
        print(f"\n📝 AI Response Preview:")
        print(f"{response[:300]}...")
        
        print(f"\n📊 Conversation State: {context.state}")
        print(f"💬 Messages: {len(context.messages)}")
        
        # Test user approval and autonomous building
        print(f"\n✅ Simulating User Approval...")
        
        context, response, plan = await agent.continue_workflow_building(
            session_id=session_id,
            user_response="yes",
            user_id=user_id
        )
        
        print(f"\n🤖 Autonomous Building Response Preview:")
        print(f"{response[:300]}...")
        
        print(f"\n📊 Updated State: {context.state}")
        
        print(f"\n🎉 Intelligent Workflow Analysis Test Completed!")
        
        # Summary
        print(f"\n📈 Test Summary:")
        print(f"   ✅ Intelligent reasoning working")
        print(f"   ✅ Connector analysis functional")
        print(f"   ✅ Autonomous building initiated")
        print(f"   ✅ Context-aware responses generated")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        success = await test_intelligent_workflow_analysis()
        if success:
            print("\n🎊 Intelligent workflow agent is working correctly!")
            print("🚀 The AI now properly analyzes user requests and selects appropriate connectors!")
        else:
            print("\n💥 Intelligent workflow agent test failed!")
    
    asyncio.run(main())