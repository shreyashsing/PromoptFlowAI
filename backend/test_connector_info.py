#!/usr/bin/env python3
"""
Test script to verify connector info includes Airtable.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.connectors.core.register import get_core_connector_info
import json

def test_connector_info():
    """Test that Airtable is included in core connector info."""
    print("🧪 Testing Core Connector Info")
    print("=" * 40)
    
    try:
        connector_info = get_core_connector_info()
        
        print(f"📊 Found {len(connector_info)} core connectors:")
        for name, info in connector_info.items():
            print(f"   - {name}: {info['name']}")
        
        print()
        
        # Check if Airtable is included
        if 'airtable' in connector_info:
            airtable_info = connector_info['airtable']
            print("✅ Airtable connector found in core connector info!")
            print(f"   📋 Name: {airtable_info['name']}")
            print(f"   📝 Description: {airtable_info['description']}")
            print(f"   📂 Category: {airtable_info['category']}")
            print(f"   🔐 Auth Types: {airtable_info['auth_types']}")
        else:
            print("❌ Airtable connector NOT found in core connector info")
            
        print()
        print("📋 Complete connector info:")
        print(json.dumps(connector_info, indent=2))
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_connector_info()