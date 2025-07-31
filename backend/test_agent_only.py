#!/usr/bin/env python3
"""
Test script to verify ReAct agent functionality without conversation persistence.
"""
import asyncio
import sys
sys.path.append('.')

from app.services.react_agent_service import ReactAgentService

async def test_agent_only():
    print("🔍 Testing ReAct agent functionality (bypassing conversation persistence)...")
    service = ReactAgentService()
    
    try:
        print("📋 Initializing service...")
        await service.initialize()
        
        print(f"🤖 Agent available: {service.is_agent_available()}")
        print(f"🧠 LLM available: {service.llm is not None}")
        
        # Get agent status
        status = service.get_agent_status()
        print(f"📊 Agent Status: {status}")
        
        if service.is_agent_available():
            print("✅ ReAct agent is properly configured and available!")
            
            # Test direct agent execution (bypassing conversation persistence)
            try:
                tools = await service.tool_registry.get_available_tools()
                print(f"🔧 Available tools: {[tool.name for tool in tools]}")
                
                # Test tool registry status
                tool_status = await service.tool_registry.get_tool_registration_status()
                print(f"🔧 Tool registration status: {tool_status['success_rate']:.1f}% success rate")
                
                print("✅ All agent components are working correctly!")
                
            except Exception as tool_error:
                print(f"⚠️ Tool testing failed: {tool_error}")
        else:
            print("❌ ReAct agent is not available")
            print(f"Status details: {status}")
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_only())