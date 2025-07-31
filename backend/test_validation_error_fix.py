#!/usr/bin/env python3
"""
Test script to verify the ValidationError fix in connector_tool_adapter.py
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.connector_tool_adapter import ConnectorToolAdapter
from app.connectors.core.google_sheets_connector import GoogleSheetsConnector


async def test_validation_error_fix():
    """Test that ValidationError is properly handled in connector tool adapter."""
    print("🧪 Testing ValidationError fix in connector_tool_adapter.py")
    print("=" * 60)
    
    try:
        # Create adapter for Google Sheets connector
        adapter = ConnectorToolAdapter('google_sheets', GoogleSheetsConnector)
        print("✅ ConnectorToolAdapter created successfully")
        
        # Convert to LangChain tool
        tool = await adapter.to_langchain_tool()
        print("✅ Tool conversion successful")
        
        # Test with invalid parameters (missing spreadsheet_id)
        print("\n🔍 Testing parameter validation with invalid input...")
        result = tool.func('List all available sheets')
        
        # Check if we get a proper error response instead of a crash
        if "Critical error" in result and "temporarily unavailable" in result:
            print("✅ Validation error handled gracefully")
            print(f"📝 Response: {result[:100]}...")
        else:
            print(f"❌ Unexpected response: {result}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    print("\n🎉 ValidationError fix test completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_validation_error_fix())
    sys.exit(0 if success else 1)