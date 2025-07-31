#!/usr/bin/env python3
"""
Test the improved autonomous workflow building functionality.
"""
import asyncio
from app.services.integrated_workflow_agent import get_integrated_workflow_agent
from app.models.conversation import ConversationContext, ChatMessage
from app.models.base import ConversationState
import uuid

async def test_autonomous_building():
    """Test the autonomous workflow building process."""
    print("🤖 Testing Autonomous Workflow Building")
    print("=" * 50)
    
    try:
        # Get the agent
        agent = await get_integrated_workflow_agent()
        print("✅ Agent initialized")
        
        # Create initial conversation
        session_id = str(uuid.uuid4())
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Step 1: Initial request
        print("\n📝 Step 1: User makes initial request")
        context, response, plan = await agent.create_workflow_conversationally(
            query="send me daily ai summaries via email, use perplexity for searching ai",
            user_id=user_id,
            session_id=session_id
        )
        
        print(f"🤖 AI Response: {response[:200]}...")
        print(f"📊 State: {context.state}")
        
        # Step 2: User approves plan
        print("\n✅ Step 2: User approves the plan")
        context, response, plan = await agent.continue_workflow_building(
            session_id=session_id,
            user_response="yes",
            user_id=user_id
        )
        
        print(f"🤖 Autonomous Response: {response[:300]}...")
        print(f"📊 State: {context.state}")
        
        # Step 3: Continue autonomous building
        print("\n🔧 Step 3: Continue autonomous building")
        context, response, plan = await agent.continue_workflow_building(
            session_id=session_id,
            user_response="continue",
            user_id=user_id
        )
        
        print(f"🤖 Continuation Response: {response[:300]}...")
        print(f"📊 State: {context.state}")
        
        # Step 4: Finalize workflow
        print("\n🎯 Step 4: Finalize workflow")
        context, response, plan = await agent.continue_workflow_building(
            session_id=session_id,
            user_response="finalize",
            user_id=user_id
        )
        
        print(f"🎉 Final Response: {response[:300]}...")
        print(f"📊 Final State: {context.state}")
        
        if plan:
            print(f"\n✅ Workflow Created:")
            print(f"   📝 Name: {plan.name}")
            print(f"   📄 Description: {plan.description}")
            print(f"   🔗 Nodes: {len(plan.nodes)}")
            
            if plan.nodes:
                node = plan.nodes[0]
                print(f"   🔌 Connector: {node.connector_name}")
                print(f"   📧 Recipient: {node.parameters.get('recipient', 'N/A')}")
        
        print("\n🎊 Autonomous Building Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        success = await test_autonomous_building()
        if success:
            print("\n✅ Autonomous workflow building is working!")
        else:
            print("\n❌ Autonomous workflow building failed!")
    
    asyncio.run(main())