"""
Test the AI code generation functionality in the True ReAct agent
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_code_generation():
    """Test the AI code generation for different task types."""
    print("🤖 Testing AI Code Generation...")
    
    # Initialize the agent (without full setup)
    agent = TrueReActAgent()
    
    # Test 1: Combine task
    print("\n1. Testing 'combine' task code generation...")
    combine_task = {
        "task_number": 2,
        "description": "Combine the content of all 5 blog posts into a single text block for summarization",
        "suggested_tool": "code",
        "reasoning": "Need to merge multiple blog post contents into one text for the summarizer",
        "inputs": ["blog posts from perplexity search"],
        "outputs": ["combined text block"]
    }
    
    previous_steps = [
        {
            "connector_name": "perplexity_search",
            "purpose": "Search for blog posts",
            "parameters": {"query": "recent Google blog posts"}
        }
    ]
    
    plan = {
        "original_request": "Find top 5 recent Google blogs and summarize them",
        "summary": "Search, combine, summarize, and email workflow"
    }
    
    try:
        code_params = await agent._generate_code_parameters(combine_task, previous_steps, plan)
        print("✅ Combine task code generated successfully")
        print(f"   Language: {code_params.get('language', 'unknown')}")
        print(f"   Code length: {len(code_params.get('code', ''))}")
        print(f"   Code preview: {code_params.get('code', '')[:100]}...")
    except Exception as e:
        print(f"❌ Combine task failed: {e}")
    
    # Test 2: Transform task
    print("\n2. Testing 'transform' task code generation...")
    transform_task = {
        "task_number": 2,
        "description": "Transform and process the search results data structure",
        "suggested_tool": "code",
        "reasoning": "Need to modify data format for next step",
        "inputs": ["raw search results"],
        "outputs": ["processed data structure"]
    }
    
    try:
        code_params = await agent._generate_code_parameters(transform_task, previous_steps, plan)
        print("✅ Transform task code generated successfully")
        print(f"   Language: {code_params.get('language', 'unknown')}")
        print(f"   Code length: {len(code_params.get('code', ''))}")
        print(f"   Code preview: {code_params.get('code', '')[:100]}...")
    except Exception as e:
        print(f"❌ Transform task failed: {e}")
    
    # Test 3: Default task
    print("\n3. Testing default task code generation...")
    default_task = {
        "task_number": 2,
        "description": "Process the data for the next step",
        "suggested_tool": "code",
        "reasoning": "Generic data processing needed",
        "inputs": ["input data"],
        "outputs": ["processed data"]
    }
    
    try:
        code_params = await agent._generate_code_parameters(default_task, previous_steps, plan)
        print("✅ Default task code generated successfully")
        print(f"   Language: {code_params.get('language', 'unknown')}")
        print(f"   Code length: {len(code_params.get('code', ''))}")
        print(f"   Code preview: {code_params.get('code', '')[:100]}...")
    except Exception as e:
        print(f"❌ Default task failed: {e}")
    
    print("\n🎉 AI Code Generation tests completed!")

if __name__ == "__main__":
    asyncio.run(test_code_generation())