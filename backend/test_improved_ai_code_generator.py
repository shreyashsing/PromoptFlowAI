#!/usr/bin/env python3
"""
Test the improved AI Code Generator to ensure it produces robust, executable JavaScript code.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.ai_code_generator import AICodeGenerator


async def test_ai_code_generator():
    """Test the AI code generator with various scenarios."""
    
    print("🧪 Testing Improved AI Code Generator")
    print("=" * 50)
    
    # Initialize the AI code generator
    generator = AICodeGenerator()
    await generator.initialize()
    
    # Test cases
    test_cases = [
        {
            "name": "Data Transformation",
            "prompt": "Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step",
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "context": {
                "previous_results": {
                    "items": [
                        {
                            "json": {
                                "title": "Sample Article",
                                "content": "This is sample content",
                                "citation": "Sample citation"
                            }
                        }
                    ]
                }
            }
        },
        {
            "name": "Simple Processing",
            "prompt": "Add a processed flag to each item",
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "context": None
        },
        {
            "name": "Individual Item Processing",
            "prompt": "Transform each item by adding timestamp",
            "language": "javascript",
            "mode": "runOnceForEachItem",
            "context": None
        },
        {
            "name": "Python Data Processing",
            "prompt": "Calculate statistics for all items",
            "language": "python",
            "mode": "runOnceForAllItems",
            "context": None
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Generate code
            result = await generator.generate_code(
                user_prompt=test_case["prompt"],
                language=test_case["language"],
                mode=test_case["mode"],
                context=test_case["context"]
            )
            
            print(f"✅ Generated {test_case['language']} code successfully")
            print(f"📊 Confidence: {result['confidence']}")
            print(f"🎯 Intent: {result['intent']}")
            print(f"📝 Explanation: {result['explanation']}")
            print("\n📄 Generated Code:")
            print("```" + test_case['language'])
            print(result['code'])
            print("```")
            
            # Validate the code structure
            code = result['code']
            
            if test_case['language'] == 'javascript':
                # Check for safety features
                safety_checks = [
                    "Array.isArray" in code or "!item" in code,  # Input validation
                    "try {" in code or "catch" in code,  # Error handling
                    "return" in code,  # Return statement
                    "console.log" in code  # Debugging output
                ]
                
                safety_score = sum(safety_checks)
                print(f"🛡️  Safety Score: {safety_score}/4")
                
                if safety_score >= 3:
                    print("✅ Code has good safety features")
                else:
                    print("⚠️  Code could use more safety features")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Code Generator Testing Complete!")


async def test_fallback_templates():
    """Test the fallback code templates."""
    
    print("\n🔧 Testing Fallback Templates")
    print("=" * 50)
    
    generator = AICodeGenerator()
    
    # Test fallback generation
    test_cases = [
        ("Transform data", "javascript", "runOnceForAllItems"),
        ("Filter items", "javascript", "runOnceForEachItem"),
        ("Aggregate values", "python", "runOnceForAllItems"),
        ("Process item", "python", "runOnceForEachItem")
    ]
    
    for prompt, language, mode in test_cases:
        print(f"\n🔍 Testing: {prompt} ({language}, {mode})")
        
        result = generator._fallback_code_generation(prompt, language, mode)
        
        print(f"✅ Generated fallback code")
        print(f"📊 Confidence: {result['confidence']}")
        print("\n📄 Fallback Code:")
        print("```" + language)
        print(result['code'])
        print("```")


if __name__ == "__main__":
    asyncio.run(test_ai_code_generator())
    asyncio.run(test_fallback_templates())