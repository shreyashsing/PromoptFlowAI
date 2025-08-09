"""
Test Multi-Step Planning Enhancement
"""
import asyncio
from app.services.true_react_agent import TrueReActAgent

async def test_multi_step():
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test complex multi-step request
    request = 'Search for AI news, summarize it, and save to Notion'
    print(f"🧪 Testing: {request}")
    
    result = await agent.process_user_request(request, 'test_user')
    
    if result.get('success'):
        plan = result.get('plan', {})
        print(f'✅ Enhanced Planning: {plan.get("enhanced_planning", False)}')
        print(f'📋 Sequence: {plan.get("sequence_description", "N/A")}')
        print(f'📊 Tasks: {len(plan.get("tasks", []))}')
        
        for task in plan.get('tasks', []):
            deps = task.get('dependencies', [])
            deps_str = f' (depends on: {deps})' if deps else ''
            print(f'  {task["task_number"]}. {task["description"]} ({task["suggested_tool"]}){deps_str}')
    else:
        print(f'❌ Failed: {result.get("error", "Unknown")}')

if __name__ == "__main__":
    asyncio.run(test_multi_step())