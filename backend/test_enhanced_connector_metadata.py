"""
Test enhanced connector metadata system for AI understanding.
"""
import asyncio
import json
from app.connectors.registry import get_connector_registry
from app.connectors.core.register import register_core_connectors


async def test_enhanced_metadata():
    """Test the enhanced metadata system."""
    print("🚀 Testing Enhanced Connector Metadata System")
    print("=" * 60)
    
    # Register connectors
    register_core_connectors()
    registry = get_connector_registry()
    
    print(f"📊 Total registered connectors: {registry.get_connector_count()}")
    print()
    
    # Test 1: Get AI metadata for all connectors
    print("1️⃣ Testing AI Metadata for All Connectors")
    print("-" * 40)
    
    all_metadata = registry.get_all_ai_metadata()
    
    for name, metadata in list(all_metadata.items())[:3]:  # Show first 3
        print(f"🔧 {metadata['display_name']} ({name})")
        print(f"   📝 Description: {metadata['description'][:80]}...")
        print(f"   🏷️  Category: {metadata['category']}")
        print(f"   ⚡ Capabilities: {', '.join(metadata['capabilities'])}")
        print(f"   🎯 Operations: {len(metadata['supported_operations'])} operations")
        print(f"   🔐 Auth Required: {metadata['auth_required']}")
        print()
    
    # Test 2: Test specific connector metadata
    print("2️⃣ Testing Gmail Connector Detailed Metadata")
    print("-" * 40)
    
    if "gmail_connector" in all_metadata:
        gmail_metadata = all_metadata["gmail_connector"]
        
        print(f"📧 Gmail Connector Details:")
        print(f"   Capabilities: {gmail_metadata['capabilities']}")
        print(f"   Use Cases: {len(gmail_metadata['use_cases'])} defined")
        
        print(f"\n   Example Prompts:")
        for i, prompt in enumerate(gmail_metadata['example_prompts'][:3], 1):
            print(f"   {i}. {prompt}")
        
        print(f"\n   Parameter Hints:")
        for param, hint in list(gmail_metadata['parameter_hints'].items())[:3]:
            print(f"   • {param}: {hint[:60]}...")
    
    # Test 3: Test parameter suggestions
    print("\n3️⃣ Testing Parameter Suggestions")
    print("-" * 40)
    
    if "gmail_connector" in all_metadata:
        gmail_connector = registry.create_connector("gmail_connector")
        
        test_prompts = [
            "Send an email to john@example.com about the meeting",
            "Find all unread emails from my boss",
            "Get the latest 10 emails from my inbox"
        ]
        
        for prompt in test_prompts:
            suggestions = gmail_connector.generate_parameter_suggestions(prompt)
            print(f"📝 Prompt: '{prompt}'")
            print(f"   💡 Suggestions: {json.dumps(suggestions, indent=6)}")
            print()
    
    # Test 4: Test capability-based search
    print("4️⃣ Testing Capability-Based Search")
    print("-" * 40)
    
    capabilities_to_test = ["read", "write", "search"]
    
    for capability in capabilities_to_test:
        matching_connectors = registry.search_by_capability(capability)
        print(f"🔍 Connectors with '{capability}' capability:")
        print(f"   {', '.join(matching_connectors[:5])}{'...' if len(matching_connectors) > 5 else ''}")
        print(f"   Total: {len(matching_connectors)} connectors")
        print()
    
    # Test 5: Test prompt-based connector discovery
    print("5️⃣ Testing Prompt-Based Connector Discovery")
    print("-" * 40)
    
    test_user_prompts = [
        "I want to send an email",
        "Create a new page in my workspace",
        "Search for videos on YouTube",
        "Get data from a spreadsheet"
    ]
    
    for prompt in test_user_prompts:
        relevant_connectors = registry.get_connectors_for_prompt(prompt)
        print(f"🎯 Prompt: '{prompt}'")
        
        if relevant_connectors:
            top_3 = relevant_connectors[:3]
            for connector in top_3:
                score = connector.get('relevance_score', 0)
                print(f"   • {connector['display_name']} (score: {score})")
        else:
            print("   No relevant connectors found")
        print()
    
    # Test 6: Test use cases generation
    print("6️⃣ Testing Use Cases Generation")
    print("-" * 40)
    
    test_connectors = ["notion", "youtube", "gmail_connector"]
    
    for connector_name in test_connectors:
        if connector_name in all_metadata:
            connector = registry.create_connector(connector_name)
            use_cases = connector.get_use_cases()
            
            print(f"📋 {connector_name.title()} Use Cases:")
            for i, use_case in enumerate(use_cases[:2], 1):  # Show first 2
                print(f"   {i}. {use_case['title']} ({use_case['complexity']})")
                print(f"      {use_case['description']}")
            print()
    
    # Test 7: Test categories overview
    print("7️⃣ Testing Categories Overview")
    print("-" * 40)
    
    categories = registry.list_categories()
    print(f"📂 Available Categories: {len(categories)}")
    
    for category in categories:
        connectors_in_category = registry.list_connectors_by_category(category)
        print(f"   • {category.title()}: {len(connectors_in_category)} connectors")
        print(f"     {', '.join(connectors_in_category[:3])}{'...' if len(connectors_in_category) > 3 else ''}")
    
    print("\n✅ Enhanced Metadata System Test Complete!")
    print("=" * 60)
    
    # Summary statistics
    total_connectors = len(all_metadata)
    total_capabilities = len(set(cap for metadata in all_metadata.values() for cap in metadata['capabilities']))
    total_use_cases = sum(len(metadata['use_cases']) for metadata in all_metadata.values())
    total_prompts = sum(len(metadata['example_prompts']) for metadata in all_metadata.values())
    
    print(f"📈 Summary Statistics:")
    print(f"   • Total Connectors: {total_connectors}")
    print(f"   • Unique Capabilities: {total_capabilities}")
    print(f"   • Total Use Cases: {total_use_cases}")
    print(f"   • Total Example Prompts: {total_prompts}")
    print(f"   • Categories: {len(categories)}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_metadata())