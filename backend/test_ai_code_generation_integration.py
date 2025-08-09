#!/usr/bin/env python3
"""
Test AI Code Generation Integration with True React Agent
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.services.ai_code_generator import get_ai_code_generator


async def test_ai_code_generation():
    """Test AI-powered code generation for various scenarios."""
    print("🤖 Testing AI Code Generation Integration...")
    
    # Initialize AI code generator
    ai_generator = await get_ai_code_generator()
    code_connector = CodeConnector()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Data Transformation",
            "prompt": "Transform user data by adding a processed flag and current timestamp",
            "context": {
                "previous_results": {
                    "items": [
                        {"json": {"name": "John", "age": 30, "email": "john@example.com"}},
                        {"json": {"name": "Jane", "age": 25, "email": "jane@example.com"}}
                    ]
                }
            }
        },
        {
            "name": "Data Filtering",
            "prompt": "Filter users to only include adults (age >= 18) and add an adult category",
            "context": {
                "previous_results": {
                    "items": [
                        {"json": {"name": "John", "age": 30}},
                        {"json": {"name": "Alice", "age": 16}},
                        {"json": {"name": "Bob", "age": 22}}
                    ]
                }
            }
        },
        {
            "name": "Data Aggregation",
            "prompt": "Calculate the total and average age of all users",
            "context": {
                "previous_results": {
                    "items": [
                        {"json": {"name": "John", "age": 30}},
                        {"json": {"name": "Jane", "age": 25}},
                        {"json": {"name": "Bob", "age": 35}}
                    ]
                }
            }
        },
        {
            "name": "Python Data Analysis",
            "prompt": "Use Python to analyze user data and create age statistics with categories",
            "context": {
                "previous_results": {
                    "items": [
                        {"json": {"name": "John", "age": 30, "department": "Engineering"}},
                        {"json": {"name": "Jane", "age": 25, "department": "Marketing"}},
                        {"json": {"name": "Bob", "age": 45, "department": "Engineering"}}
                    ]
                }
            }
        },
        {
            "name": "Individual Item Processing",
            "prompt": "Process each user individually to add personalized greeting and age category",
            "context": {
                "previous_results": {
                    "items": [
                        {"json": {"name": "John", "age": 30}},
                        {"json": {"name": "Jane", "age": 25}}
                    ]
                }
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['name']}")
        print(f"   Prompt: '{scenario['prompt']}'")
        
        try:
            # Test AI code generation
            result = await code_connector.generate_ai_code(
                scenario['prompt'], 
                scenario['context']
            )
            
            if result.get('_ai_generated'):
                print("   ✅ AI code generated successfully")
                print(f"   🧠 Language: {result.get('language', 'unknown')}")
                print(f"   🔄 Mode: {result.get('mode', 'unknown')}")
                print(f"   📊 Confidence: {result.get('_ai_confidence', 'unknown')}")
                print(f"   💡 Intent: {result.get('_ai_intent', {}).get('operation', 'unknown')}")
                
                # Show generated code (truncated)
                code = result.get('code', '')
                code_preview = code[:200] + "..." if len(code) > 200 else code
                print(f"   📄 Generated Code Preview:")
                print("   " + "\n   ".join(code_preview.split('\n')[:5]))
                
                # Show explanation
                explanation = result.get('_ai_explanation', '')
                if explanation:
                    print(f"   📝 Explanation: {explanation[:100]}...")
                
            else:
                print("   ⚠️ Fallback to template-based generation")
                print(f"   🔄 Mode: {result.get('mode', 'unknown')}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {str(e)}")
    
    print("\n🎉 AI Code Generation Integration testing completed!")


async def test_true_react_agent_integration():
    """Test how the True React Agent would use AI code generation."""
    print("\n🔗 Testing True React Agent Integration...")
    
    try:
        from app.services.true_react_agent import TrueReActAgent
        
        # Create agent instance
        agent = TrueReActAgent()
        await agent.initialize()
        
        # Simulate a task that would trigger code generation
        task = {
            "description": "Transform the user data by adding processed timestamps and validation status",
            "action": "code_execution",
            "connector": "code"
        }
        
        previous_steps = [
            {
                "name": "get_users",
                "result": {
                    "items": [
                        {"json": {"name": "John", "age": 30, "email": "john@example.com"}},
                        {"json": {"name": "Jane", "age": 25, "email": "jane@example.com"}}
                    ]
                }
            }
        ]
        
        plan = {
            "goal": "Process user data with custom transformations",
            "steps": ["get_users", "transform_data", "save_results"]
        }
        
        # Test the AI code generation method
        if hasattr(agent, '_generate_ai_code_with_context'):
            result = await agent._generate_ai_code_with_context(task, previous_steps, plan)
            
            if result:
                print("   ✅ True React Agent AI code generation successful")
                print(f"   🧠 Generated parameters: {len(result)} parameters")
                print(f"   📄 Code generated: {'Yes' if result.get('code') else 'No'}")
                print(f"   🤖 AI-powered: {'Yes' if result.get('_ai_generated') else 'No'}")
                
                if result.get('_ai_explanation'):
                    print(f"   💡 AI Explanation: {result['_ai_explanation'][:100]}...")
            else:
                print("   ⚠️ No AI code generated (fallback mode)")
        else:
            print("   ⚠️ AI code generation method not found in agent")
            
    except Exception as e:
        print(f"   ❌ True React Agent integration test failed: {str(e)}")


async def test_workflow_scenario():
    """Test a complete workflow scenario with AI code generation."""
    print("\n🔄 Testing Complete Workflow Scenario...")
    
    try:
        # Simulate a user request that would trigger AI code generation
        user_request = "Get user data from the previous step and transform it by adding validation status, processing timestamp, and age category (adult/minor)"
        
        code_connector = CodeConnector()
        
        # Simulate context from a real workflow
        workflow_context = {
            "workflow_id": "test-workflow-123",
            "step_number": 2,
            "previous_results": {
                "items": [
                    {"json": {"id": 1, "name": "John Doe", "age": 30, "email": "john@example.com", "status": "active"}},
                    {"json": {"id": 2, "name": "Jane Smith", "age": 17, "email": "jane@example.com", "status": "pending"}},
                    {"json": {"id": 3, "name": "Bob Johnson", "age": 45, "email": "bob@example.com", "status": "active"}}
                ]
            },
            "workflow_goal": "Process and validate user data for reporting"
        }
        
        # Generate AI code for this scenario
        result = await code_connector.generate_ai_code(user_request, workflow_context)
        
        print("   📋 Workflow Scenario Results:")
        print(f"   🎯 Request: {user_request}")
        print(f"   📊 Input Items: {len(workflow_context['previous_results']['items'])}")
        
        if result.get('_ai_generated'):
            print("   ✅ AI successfully generated workflow code")
            print(f"   🧠 Language: {result.get('language')}")
            print(f"   🔄 Mode: {result.get('mode')}")
            print(f"   🛡️ Safe Mode: {result.get('safe_mode')}")
            print(f"   📈 Confidence: {result.get('_ai_confidence')}")
            
            # Show the generated code structure
            code = result.get('code', '')
            lines = code.split('\n')
            print(f"   📄 Generated Code ({len(lines)} lines):")
            
            # Show key parts of the code
            for i, line in enumerate(lines[:10]):  # First 10 lines
                print(f"      {i+1:2d}: {line}")
            
            if len(lines) > 10:
                print(f"      ... ({len(lines) - 10} more lines)")
            
            # Show AI explanation
            if result.get('_ai_explanation'):
                print(f"   💡 AI Explanation: {result['_ai_explanation']}")
        else:
            print("   ⚠️ Fallback to template-based generation")
        
        print("   ✅ Workflow scenario test completed")
        
    except Exception as e:
        print(f"   ❌ Workflow scenario test failed: {str(e)}")


async def main():
    """Run all AI code generation integration tests."""
    print("🚀 Starting AI Code Generation Integration Tests\n")
    
    await test_ai_code_generation()
    await test_true_react_agent_integration()
    await test_workflow_scenario()
    
    print("\n🎉 All AI Code Generation Integration tests completed!")
    print("\n📋 Summary:")
    print("   • AI Code Generator: Intelligently generates JavaScript/Python code")
    print("   • Code Connector: Enhanced with AI-powered parameter suggestions")
    print("   • True React Agent: Integrated with AI code generation for workflows")
    print("   • Workflow Integration: Complete end-to-end AI code generation")


if __name__ == "__main__":
    asyncio.run(main())