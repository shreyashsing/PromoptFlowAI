#!/usr/bin/env python3
"""
Test script to verify datetime serialization fix for conversation context.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.conversational_agent import ConversationalAgent
from app.models.conversation import ConversationContext, ChatMessage, ConversationState
from app.models.base import WorkflowPlan, WorkflowStatus
from datetime import datetime
import uuid

async def test_datetime_serialization():
    """Test that conversation context with datetime fields can be saved and loaded."""
    print("🧪 Testing datetime serialization fix...")
    
    try:
        # Initialize required systems
        from app.core.database import init_database
        from app.services.rag import init_rag_system
        from app.services.conversational_agent import get_conversational_agent
        
        print("📚 Initializing database...")
        await init_database()
        
        print("🔍 Initializing RAG system...")
        await init_rag_system()
        
        print("🤖 Initializing conversational agent...")
        agent = await get_conversational_agent()
        
        # Create a test conversation context with datetime fields
        session_id = str(uuid.uuid4())
        user_id = "test-user-123"
        
        # Create a test message with timestamp
        test_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content="Hello, create a workflow for me",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        # Create a test workflow plan with datetime fields
        test_plan = WorkflowPlan(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name="Test Workflow",
            description="A test workflow",
            nodes=[],
            edges=[],
            triggers=[],
            status=WorkflowStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create conversation context
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            messages=[test_message],
            current_plan=test_plan,
            state=ConversationState.PLANNING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        print(f"📝 Created test context with session_id: {session_id}")
        
        # Test saving the context (this should not fail with datetime serialization error)
        await agent._save_conversation_context(context)
        print("✅ Successfully saved conversation context with datetime fields")
        
        # Test loading the context back
        loaded_context = await agent._load_conversation_context(session_id)
        
        if loaded_context:
            print("✅ Successfully loaded conversation context")
            print(f"   - Session ID: {loaded_context.session_id}")
            print(f"   - Messages: {len(loaded_context.messages)}")
            print(f"   - Has plan: {loaded_context.current_plan is not None}")
            print(f"   - State: {loaded_context.state}")
            
            # Verify datetime fields are properly reconstructed
            if loaded_context.messages:
                msg = loaded_context.messages[0]
                print(f"   - Message timestamp type: {type(msg.timestamp)}")
                print(f"   - Message timestamp: {msg.timestamp}")
            
            if loaded_context.current_plan:
                plan = loaded_context.current_plan
                print(f"   - Plan created_at type: {type(plan.created_at)}")
                print(f"   - Plan updated_at type: {type(plan.updated_at)}")
            
            print("🎉 Datetime serialization test PASSED!")
            return True
        else:
            print("❌ Failed to load conversation context")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_datetime_serialization())
    sys.exit(0 if result else 1)