#!/usr/bin/env python3
"""
Debug script to test ReAct agent initialization.
"""
import asyncio
import sys
import os
sys.path.append('.')

from app.services.react_agent_service import ReactAgentService

async def test_initialization():
    print("🔍 Testing ReAct agent initialization...")
    service = ReactAgentService()
    
    try:
        print("📋 Initializing service...")
        await service.initialize()
        print('✅ Agent initialized successfully')
        
        print(f'🤖 Agent available: {service.react_agent is not None}')
        print(f'🧠 LLM available: {service.llm is not None}')
        
        # Test tool registry
        tools = await service.tool_registry.get_available_tools()
        print(f'🔧 Tools count: {len(tools)}')
        print(f'🔧 Available tools: {[tool.name for tool in tools]}')
        
        # Check configuration
        from app.core.config import settings
        print(f"🔑 Azure OpenAI Endpoint: {settings.AZURE_OPENAI_ENDPOINT[:50]}...")
        print(f"🔑 Azure OpenAI Key configured: {bool(settings.AZURE_OPENAI_API_KEY)}")
        print(f"🔑 Azure OpenAI Deployment: {settings.AZURE_OPENAI_DEPLOYMENT_NAME}")
        
        # Check LangGraph availability
        try:
            from langgraph.prebuilt import create_agent_executor
            from langgraph.checkpoint.memory import MemorySaver
            print("✅ LangGraph is available")
        except ImportError as e:
            print(f"❌ LangGraph not available: {e}")
        
        # Check LangChain ReAct agent availability
        try:
            from langchain.agents import create_react_agent
            print("✅ LangChain ReAct agent is available")
        except ImportError as e:
            print(f"❌ LangChain ReAct agent not available: {e}")
        
        # Test a simple request
        print("\n🧪 Testing simple request...")
        response = await service.process_request(
            query="Hello, can you help me?",
            session_id="test-session",
            user_id="test-user",
            skip_session_validation=True
        )
        print(f"📝 Response: {response['response'][:100]}...")
        print(f"📊 Status: {response.get('status', 'unknown')}")
        
    except Exception as e:
        print(f'❌ Initialization failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_initialization())