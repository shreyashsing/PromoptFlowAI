#!/usr/bin/env python3
"""
Test the professional AI Code Generator to ensure it produces high-quality, Pipedream-style code.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_professional_code_generation():
    """Test professional code generation with real-world scenarios."""
    
    print("🚀 Testing Professional AI Code Generation")
    print("=" * 60)
    
    # Create connector
    connector = CodeConnector()
    
    # Test cases that mirror real workflow scenarios
    test_cases = [
        {
            "name": "Article Processing (Like the failing case)",
            "prompt": "Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step",
            "test_data": [
                {
                    "json": {
                        "title": "  Google's Latest AI Developments  ",
                        "content": {
                            "Introduction": "Google has announced several new AI features...",
                            "Main": "The main developments include improvements to search algorithms..."
                        },
                        "citation": "https://blog.google.com/ai-developments",
                        "id": "article_1"
                    }
                },
                {
                    "json": {
                        "title": "Machine Learning Advances",
                        "content": "Recent advances in machine learning have shown promising results...",
                        "citation": ["https://research.google.com/ml", "https://ai.google/research"],
                        "id": "article_2"
                    }
                }
            ]
        },
        {
            "name": "Data Transformation",
            "prompt": "Transform user data by adding computed fields and cleaning text",
            "test_data": [
                {
                    "json": {
                        "name": "  John Doe  ",
                        "email": "john@example.com",
                        "age": 30,
                        "status": "active"
                    }
                },
                {
                    "json": {
                        "name": "Jane Smith",
                        "email": "jane@example.com",
                        "age": 25,
                        "status": "inactive"
                    }
                }
            ]
        },
        {
            "name": "E-commerce Order Processing",
            "prompt": "Process orders: calculate totals, validate data, and add processing metadata",
            "test_data": [
                {
                    "json": {
                        "orderId": "ORD-001",
                        "items": [
                            {"name": "Product A", "price": 29.99, "quantity": 2},
                            {"name": "Product B", "price": 15.50, "quantity": 1}
                        ],
                        "customer": "customer@example.com"
                    }
                }
            ]
        },
        {
            "name": "API Response Processing",
            "prompt": "Clean and structure API response data for downstream processing",
            "test_data": [
                {
                    "json": {
                        "status": "success",
                        "data": {
                            "users": [
                                {"id": 1, "name": "User 1", "active": True},
                                {"id": 2, "name": "User 2", "active": False}
                            ]
                        },
                        "metadata": {
                            "total": 2,
                            "page": 1
                        }
                    }
                }
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Create context with test data
        context = ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            execution_id=f"test_execution_{i}",
            previous_results={"items": test_case["test_data"]}
        )
        
        try:
            # Generate AI code
            ai_params = await connector.generate_ai_code(
                user_prompt=test_case["prompt"],
                context={"previous_results": {"items": test_case["test_data"]}}
            )
            
            print(f"✅ Generated AI code successfully")
            print(f"📊 Confidence: {ai_params.get('_ai_confidence', 'N/A')}")
            print(f"🎯 Style: {ai_params.get('style', 'standard')}")
            
            # Show generated code (first 500 chars)
            code = ai_params.get("code", "")
            print(f"\n📄 Generated Code Preview:")
            print("```javascript")
            print(code[:500] + ("..." if len(code) > 500 else ""))
            print("```")
            
            # Execute the generated code
            params = {
                "language": "javascript",
                "mode": "runOnceForAllItems",
                "code": code,
                "timeout": 30,
                "safe_mode": True,
                "return_console_output": True
            }
            
            result = await connector.execute(params, context)
            
            if result.success:
                print(f"✅ Code executed successfully!")
                print(f"📊 Items processed: {result.metadata.get('items_processed', 0)}")
                print(f"⏱️  Execution time: {result.metadata.get('execution_time', 0):.3f}s")
                
                # Show first result
                if result.data and "items" in result.data and result.data["items"]:
                    first_result = result.data["items"][0]
                    print(f"\n📄 First Result:")
                    print(json.dumps(first_result, indent=2)[:300] + "...")
                
                # Show console output
                if result.data and "console_output" in result.data:
                    console_lines = result.data["console_output"].split('\n')[:3]
                    print(f"\n🖥️  Console Output (first 3 lines):")
                    for line in console_lines:
                        print(f"   {line}")
                
                # Analyze code quality
                quality_score = analyze_code_quality(code)
                print(f"\n🏆 Code Quality Score: {quality_score}/10")
                
            else:
                print(f"❌ Code execution failed: {result.error}")
                
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎉 Professional Code Generation Testing Complete!")


def analyze_code_quality(code: str) -> int:
    """Analyze the quality of generated code."""
    
    quality_checks = [
        ("Input validation", any(check in code for check in ["Array.isArray", "typeof", "!item"])),
        ("Error handling", "try {" in code and "catch" in code),
        ("Logging", "console.log" in code),
        ("Professional comments", "//" in code and len([line for line in code.split('\n') if line.strip().startswith('//')]) >= 3),
        ("Proper return structure", "return {" in code and "json:" in code),
        ("Data safety", any(check in code for check in ["|| {}", "|| []", "|| ''"])),
        ("Progress tracking", any(check in code for check in ["index", "length", "processed"])),
        ("Structured processing", "map(" in code or "forEach(" in code),
        ("Error context", "originalData" in code or "itemIndex" in code),
        ("Professional naming", any(name in code for name in ["processedData", "extractedData", "results"]))
    ]
    
    return sum(1 for _, check in quality_checks if check)


async def test_edge_cases():
    """Test edge cases and error handling."""
    
    print("\n🧪 Testing Edge Cases")
    print("=" * 40)
    
    connector = CodeConnector()
    
    edge_cases = [
        {
            "name": "Empty items array",
            "data": []
        },
        {
            "name": "Invalid item structure",
            "data": [{"invalid": "structure"}]
        },
        {
            "name": "Mixed valid/invalid items",
            "data": [
                {"json": {"valid": "item"}},
                {"invalid": "structure"},
                {"json": {"another": "valid"}}
            ]
        }
    ]
    
    for edge_case in edge_cases:
        print(f"\n🔍 Testing: {edge_case['name']}")
        
        context = ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            execution_id="edge_test",
            previous_results={"items": edge_case["data"]}
        )
        
        try:
            # Generate and execute code
            ai_params = await connector.generate_ai_code(
                user_prompt="Process items safely with error handling",
                context={"previous_results": {"items": edge_case["data"]}}
            )
            
            params = {
                "language": "javascript",
                "mode": "runOnceForAllItems",
                "code": ai_params.get("code", ""),
                "timeout": 30,
                "safe_mode": True,
                "return_console_output": True
            }
            
            result = await connector.execute(params, context)
            
            if result.success:
                print(f"✅ Handled edge case successfully")
                print(f"📊 Results: {len(result.data.get('items', []))} items")
            else:
                print(f"❌ Failed to handle edge case: {result.error}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_professional_code_generation())
    asyncio.run(test_edge_cases())