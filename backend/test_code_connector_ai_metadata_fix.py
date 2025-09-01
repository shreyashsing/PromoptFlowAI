#!/usr/bin/env python3
"""
Test Code Connector AI Metadata Fix
Tests that AI metadata parameters are properly filtered out during validation.
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_code_connector_ai_metadata_filtering():
    """Test that AI metadata parameters are filtered out and don't cause validation errors."""
    
    print("🧪 Testing Code Connector AI Metadata Filtering...")
    
    # Create code connector instance
    connector = CodeConnector()
    
    # Test parameters with AI metadata (this should have caused the validation error)
    params_with_ai_metadata = {
        "language": "javascript",
        "mode": "runOnceForAllItems", 
        "code": "return items.map(item => ({ json: { ...item.json, processed: true } }));",
        "timeout": 30,
        "safe_mode": True,
        # These AI metadata fields should be filtered out
        "_ai_generated": True,
        "_ai_confidence": 0.9,
        "_ai_explanation": "Generated code to process items",
        "_ai_intent": {"operation": "transform"},
        "_code_complexity": "simple",
        "_decision_reasoning": "Basic transformation",
        "_risk_assessment": "low",
        "_validation": "passed"
    }
    
    print(f"📝 Original parameters: {list(params_with_ai_metadata.keys())}")
    
    # Test parameter filtering
    filtered_params = connector._filter_auth_parameters(params_with_ai_metadata)
    print(f"🔍 Filtered parameters: {list(filtered_params.keys())}")
    
    # Verify AI metadata was filtered out
    ai_fields = ['_ai_generated', '_ai_confidence', '_ai_explanation', '_ai_intent', 
                 '_code_complexity', '_decision_reasoning', '_risk_assessment', '_validation']
    
    filtered_ai_fields = [field for field in ai_fields if field in filtered_params]
    if filtered_ai_fields:
        print(f"❌ ERROR: AI metadata fields still present: {filtered_ai_fields}")
        return False
    else:
        print("✅ SUCCESS: All AI metadata fields filtered out")
    
    # Test parameter validation with filtered parameters
    try:
        await connector.validate_params(filtered_params)
        print("✅ SUCCESS: Parameter validation passed with filtered parameters")
    except Exception as e:
        print(f"❌ ERROR: Parameter validation failed: {str(e)}")
        return False
    
    # Test execution with mock context
    try:
        context = ConnectorExecutionContext(
            user_id="test-user",
            workflow_id="test-workflow",
            execution_id="test-execution",
            auth_tokens={},
            previous_results={"items": [{"json": {"test": "data"}}]}
        )
        
        result = await connector.execute(filtered_params, context)
        
        if result.success:
            print("✅ SUCCESS: Code execution completed successfully")
            print(f"📊 Result: {result.data}")
            return True
        else:
            print(f"❌ ERROR: Code execution failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Code execution threw exception: {str(e)}")
        return False


async def main():
    """Run the test."""
    print("🚀 Starting Code Connector AI Metadata Fix Test\n")
    
    success = await test_code_connector_ai_metadata_filtering()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 ALL TESTS PASSED! AI metadata filtering fix works correctly.")
    else:
        print("💥 TESTS FAILED! AI metadata filtering needs more work.")
    print(f"{'='*50}")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())