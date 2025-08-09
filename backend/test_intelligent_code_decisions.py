#!/usr/bin/env python3
"""
Test Intelligent Code Decision System
Demonstrates how the AI agent intelligently decides when to generate code vs use existing connectors.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_code_decision import get_intelligent_code_decision


async def test_intelligent_decisions():
    """Test various scenarios to show intelligent decision making."""
    print("🧠 Testing Intelligent Code Decision System...")
    
    decision_system = await get_intelligent_code_decision()
    
    # Available connectors in the system
    available_connectors = [
        "gmail", "google_sheets", "google_drive", "notion", "airtable", 
        "youtube", "http", "webhook", "perplexity", "text_summarizer", "google_translate"
    ]
    
    # Test scenarios - some need code, some don't
    test_scenarios = [
        {
            "name": "❌ Should NOT Generate Code - Simple Email",
            "request": "Send an email to john@example.com with subject 'Meeting Tomorrow'",
            "expected_needs_code": False,
            "reason": "Gmail connector can handle this directly"
        },
        {
            "name": "❌ Should NOT Generate Code - Get Spreadsheet Data",
            "request": "Get data from my Google Sheets spreadsheet",
            "expected_needs_code": False,
            "reason": "Google Sheets connector can handle this"
        },
        {
            "name": "❌ Should NOT Generate Code - Upload File",
            "request": "Upload a document to Google Drive",
            "expected_needs_code": False,
            "reason": "Google Drive connector can handle this"
        },
        {
            "name": "❌ Should NOT Generate Code - Search Information",
            "request": "Search for information about artificial intelligence",
            "expected_needs_code": False,
            "reason": "Perplexity connector can handle this"
        },
        {
            "name": "❌ Should NOT Generate Code - Translate Text",
            "request": "Translate this text from English to Spanish",
            "expected_needs_code": False,
            "reason": "Google Translate connector can handle this"
        },
        {
            "name": "✅ Should Generate Code - Complex Data Transformation",
            "request": "Transform user data by calculating age categories, adding validation flags, and creating personalized messages based on multiple conditions",
            "expected_needs_code": True,
            "reason": "Complex business logic requires custom code"
        },
        {
            "name": "✅ Should Generate Code - Mathematical Calculations",
            "request": "Calculate compound interest with custom formula and generate financial projections",
            "expected_needs_code": True,
            "reason": "Mathematical calculations need custom code"
        },
        {
            "name": "✅ Should Generate Code - Data Validation Rules",
            "request": "Validate user input data against complex business rules including regex patterns and cross-field validation",
            "expected_needs_code": True,
            "reason": "Custom validation logic requires code"
        },
        {
            "name": "✅ Should Generate Code - Custom Data Processing",
            "request": "Parse JSON data, extract nested fields, apply transformations, and restructure into a custom format",
            "expected_needs_code": True,
            "reason": "Complex data restructuring needs custom code"
        },
        {
            "name": "🤔 Edge Case - Ambiguous Request",
            "request": "Process the data somehow",
            "expected_needs_code": None,  # Could go either way
            "reason": "Ambiguous request - decision depends on context"
        }
    ]
    
    correct_decisions = 0
    total_decisions = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['name']}")
        print(f"   Request: '{scenario['request']}'")
        print(f"   Expected: {'Code needed' if scenario['expected_needs_code'] else 'Use existing connectors' if scenario['expected_needs_code'] is False else 'Ambiguous'}")
        
        try:
            decision = await decision_system.should_generate_code(
                scenario['request'],
                available_connectors
            )
            
            needs_code = decision.get("needs_code", False)
            confidence = decision.get("confidence", 0)
            reasoning = decision.get("reasoning", "")
            alternatives = decision.get("alternative_connectors", [])
            
            print(f"   🤖 AI Decision: {'Code needed' if needs_code else 'Use existing connectors'}")
            print(f"   📊 Confidence: {confidence:.2f}")
            print(f"   💭 Reasoning: {reasoning}")
            
            if alternatives:
                print(f"   🔧 Alternative connectors: {', '.join(alternatives)}")
            
            # Check if decision matches expectation
            if scenario['expected_needs_code'] is not None:
                total_decisions += 1
                if needs_code == scenario['expected_needs_code']:
                    correct_decisions += 1
                    print(f"   ✅ Correct decision!")
                else:
                    print(f"   ❌ Incorrect decision (expected {scenario['expected_needs_code']})")
            else:
                print(f"   🤔 Ambiguous case - decision is reasonable")
            
            print(f"   📋 Expected reason: {scenario['reason']}")
            
        except Exception as e:
            print(f"   ❌ Test failed: {str(e)}")
    
    # Summary
    print(f"\n📊 Decision Accuracy: {correct_decisions}/{total_decisions} ({correct_decisions/total_decisions*100:.1f}%)")
    
    if correct_decisions / total_decisions >= 0.8:
        print("🎉 Excellent decision-making accuracy!")
    elif correct_decisions / total_decisions >= 0.6:
        print("👍 Good decision-making accuracy")
    else:
        print("⚠️ Decision-making needs improvement")


async def test_code_validation():
    """Test code validation to prevent bad code generation."""
    print("\n🔍 Testing Code Validation System...")
    
    decision_system = await get_intelligent_code_decision()
    
    validation_tests = [
        {
            "name": "Good Code - Data Transformation",
            "code": """
// Transform user data
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    age_category: item.json.age >= 18 ? 'adult' : 'minor'
  }
}));
""",
            "request": "Transform user data by adding processed flag and age category",
            "language": "javascript",
            "expected_quality": "high"
        },
        {
            "name": "Bad Code - Security Risk",
            "code": """
// Dangerous code
eval(item.json.userInput);
return items;
""",
            "request": "Process user input",
            "language": "javascript",
            "expected_quality": "low"
        },
        {
            "name": "Irrelevant Code",
            "code": """
// This code doesn't match the request
return items.map(item => ({
  json: {
    random_number: Math.random()
  }
}));
""",
            "request": "Send an email to users",
            "language": "javascript",
            "expected_quality": "low"
        }
    ]
    
    for i, test in enumerate(validation_tests, 1):
        print(f"\n📝 Validation Test {i}: {test['name']}")
        print(f"   Request: '{test['request']}'")
        
        try:
            validation = await decision_system.validate_generated_code(
                test['code'],
                test['request'],
                test['language']
            )
            
            print(f"   🎯 Relevance: {'Yes' if validation.get('is_relevant') else 'No'}")
            print(f"   ✅ Addresses request: {'Yes' if validation.get('addresses_request') else 'No'}")
            print(f"   🛡️ Security score: {validation.get('security_score', 0):.2f}")
            print(f"   📈 Quality score: {validation.get('quality_score', 0):.2f}")
            
            issues = validation.get('issues', [])
            if issues:
                print(f"   ⚠️ Issues found: {', '.join(issues)}")
            
            recommendations = validation.get('recommendations', [])
            if recommendations:
                print(f"   💡 Recommendations: {', '.join(recommendations)}")
            
        except Exception as e:
            print(f"   ❌ Validation failed: {str(e)}")


async def test_workflow_integration():
    """Test how the system works in a real workflow context."""
    print("\n🔄 Testing Workflow Integration...")
    
    # Simulate a workflow scenario
    workflow_scenarios = [
        {
            "name": "Email Campaign Workflow",
            "steps": [
                {
                    "request": "Get user data from Google Sheets",
                    "should_use_code": False,
                    "expected_connector": "google_sheets"
                },
                {
                    "request": "Transform user data by calculating engagement scores and personalizing messages",
                    "should_use_code": True,
                    "expected_connector": "code"
                },
                {
                    "request": "Send personalized emails to users",
                    "should_use_code": False,
                    "expected_connector": "gmail"
                }
            ]
        },
        {
            "name": "Data Analysis Workflow",
            "steps": [
                {
                    "request": "Search for market research data",
                    "should_use_code": False,
                    "expected_connector": "perplexity"
                },
                {
                    "request": "Analyze data trends and calculate statistical metrics",
                    "should_use_code": True,
                    "expected_connector": "code"
                },
                {
                    "request": "Save analysis results to spreadsheet",
                    "should_use_code": False,
                    "expected_connector": "google_sheets"
                }
            ]
        }
    ]
    
    decision_system = await get_intelligent_code_decision()
    available_connectors = ["gmail", "google_sheets", "perplexity", "code"]
    
    for workflow in workflow_scenarios:
        print(f"\n📋 Workflow: {workflow['name']}")
        
        for i, step in enumerate(workflow['steps'], 1):
            print(f"\n   Step {i}: {step['request']}")
            
            try:
                decision = await decision_system.should_generate_code(
                    step['request'],
                    available_connectors
                )
                
                needs_code = decision.get("needs_code", False)
                alternatives = decision.get("alternative_connectors", [])
                
                print(f"   🤖 Decision: {'Use Code connector' if needs_code else 'Use existing connector'}")
                
                if step['should_use_code'] == needs_code:
                    print(f"   ✅ Correct workflow decision!")
                else:
                    print(f"   ❌ Incorrect workflow decision")
                
                if alternatives:
                    print(f"   🔧 Suggested connectors: {', '.join(alternatives)}")
                
            except Exception as e:
                print(f"   ❌ Step analysis failed: {str(e)}")


async def main():
    """Run all intelligent decision tests."""
    print("🚀 Starting Intelligent Code Decision Tests\n")
    
    await test_intelligent_decisions()
    await test_code_validation()
    await test_workflow_integration()
    
    print("\n🎉 All Intelligent Decision tests completed!")
    print("\n📋 Key Features Demonstrated:")
    print("   • ✅ Smart decision-making: Only generates code when truly needed")
    print("   • 🛡️ Anti-hallucination: Prevents unnecessary code injection")
    print("   • 🔍 Code validation: Ensures generated code is relevant and safe")
    print("   • 🔧 Connector preference: Prefers existing connectors over custom code")
    print("   • 🎯 Context awareness: Makes decisions based on workflow context")
    print("   • 📊 Confidence scoring: Provides confidence levels for decisions")


if __name__ == "__main__":
    asyncio.run(main())