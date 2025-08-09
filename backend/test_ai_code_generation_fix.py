#!/usr/bin/env python3
"""
Test that the AI agent generates code that properly handles the main wrapper
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent

async def test_ai_code_generation():
    """Test that AI-generated code handles the main wrapper correctly"""
    
    print("🧪 Testing AI code generation fix...")
    
    # Create the agent
    agent = TrueReActAgent()
    
    # Test different types of tasks
    test_tasks = [
        {
            "description": "combine blog posts into a single text",
            "reasoning": "Need to merge multiple blog posts for email",
            "expected_pattern": "let actualData = inputData.main"
        },
        {
            "description": "transform search results",
            "reasoning": "Process search results for display",
            "expected_pattern": "let actualData = inputData.main"
        },
        {
            "description": "process data",
            "reasoning": "Generic data processing",
            "expected_pattern": "let actualData = inputData.main"
        }
    ]
    
    previous_steps = [
        {
            "connector_name": "perplexity_search",
            "purpose": "Search for blog posts about AI"
        }
    ]
    
    plan = {
        "goal": "Create email with blog content",
        "steps": ["search", "process", "send"]
    }
    
    success_count = 0
    
    for task in test_tasks:
        print(f"\n📊 Testing task: {task['description']}")
        
        try:
            # Generate code parameters
            code_params = await agent._generate_code_parameters(task, previous_steps, plan)
            
            if code_params and "code" in code_params:
                generated_code = code_params["code"]
                print(f"   Generated code length: {len(generated_code)}")
                
                # Check if the code handles the main wrapper
                if task["expected_pattern"] in generated_code:
                    print("   ✅ Code properly handles main wrapper")
                    success_count += 1
                else:
                    print("   ❌ Code does not handle main wrapper")
                    print(f"   First 200 chars: {generated_code[:200]}...")
            else:
                print("   ❌ No code generated")
                
        except Exception as e:
            print(f"   ❌ Error generating code: {e}")
    
    print(f"\n📈 Results: {success_count}/{len(test_tasks)} tasks generated correct code")
    
    if success_count == len(test_tasks):
        print("🎉 SUCCESS: All AI-generated code handles the main wrapper correctly!")
        return True
    else:
        print("❌ FAILED: Some AI-generated code doesn't handle the main wrapper")
        return False

async def test_fallback_patterns():
    """Test that fallback patterns handle the main wrapper"""
    
    print("\n🧪 Testing fallback patterns...")
    
    agent = TrueReActAgent()
    
    # Test fallback patterns by using tasks that match specific keywords
    fallback_tasks = [
        {
            "description": "combine multiple items",
            "reasoning": "Merge data",
            "pattern_type": "combine"
        },
        {
            "description": "transform the data",
            "reasoning": "Process data",
            "pattern_type": "transform"
        },
        {
            "description": "do something else",
            "reasoning": "Other task",
            "pattern_type": "default"
        }
    ]
    
    success_count = 0
    
    for task in fallback_tasks:
        print(f"\n📊 Testing fallback pattern: {task['pattern_type']}")
        
        try:
            # Generate code parameters (this should use fallback patterns)
            code_params = await agent._generate_code_parameters(task, [], {})
            
            if code_params and "code" in code_params:
                generated_code = code_params["code"]
                
                # Check if the code handles the main wrapper
                if "let actualData = inputData.main" in generated_code:
                    print("   ✅ Fallback pattern handles main wrapper")
                    success_count += 1
                else:
                    print("   ❌ Fallback pattern doesn't handle main wrapper")
                    print(f"   Code snippet: {generated_code[:150]}...")
            else:
                print("   ❌ No code generated")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📈 Fallback Results: {success_count}/{len(fallback_tasks)} patterns handle main wrapper")
    
    if success_count == len(fallback_tasks):
        print("🎉 SUCCESS: All fallback patterns handle the main wrapper correctly!")
        return True
    else:
        print("❌ FAILED: Some fallback patterns don't handle the main wrapper")
        return False

async def main():
    """Run all tests"""
    test1 = await test_ai_code_generation()
    test2 = await test_fallback_patterns()
    
    if test1 and test2:
        print("\n🎉 All tests passed! AI agent will now generate correct code.")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)