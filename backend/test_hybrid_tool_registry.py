"""
Test Hybrid Tool Registry combining validation with AI-enhanced metadata.
"""
import asyncio
import json
from app.services.tool_registry import get_tool_registry
from app.connectors.core.register import register_core_connectors


async def test_hybrid_tool_registry():
    """Test the hybrid tool registry functionality."""
    print("🔄 Testing Hybrid Tool Registry (Validation + AI Enhancement)")
    print("=" * 70)
    
    # Register connectors
    register_core_connectors()
    
    # Initialize enhanced tool registry
    auth_context = {"user_id": "test_user"}
    registry = await get_tool_registry(auth_context)
    
    print(f"✅ Hybrid Tool Registry initialized successfully")
    print(f"📊 Total tools registered: {registry.get_tool_count()}")
    print()
    
    # Test 1: Original ToolRegistry Features (Validation & LangChain)
    print("1️⃣ Testing Original ToolRegistry Features")
    print("-" * 50)
    
    # Get registration status (original feature)
    status = await registry.get_tool_registration_status()
    print(f"📋 Registration Status:")
    print(f"   • Success Rate: {status['success_rate']:.1f}%")
    print(f"   • Registered Tools: {status['successfully_registered']}")
    print(f"   • Failed Registrations: {status['registration_failures']}")
    
    # Get LangChain tools (original feature)
    langchain_tools = await registry.get_available_tools()
    print(f"🔧 LangChain Tools: {len(langchain_tools)} available")
    
    # Show first tool details
    if langchain_tools:
        first_tool = langchain_tools[0]
        print(f"   Sample Tool: {first_tool.name}")
        print(f"   Description: {first_tool.description[:100]}...")
    print()
    
    # Test 2: AI-Enhanced Features (from DynamicToolLoader)
    print("2️⃣ Testing AI-Enhanced Features")
    print("-" * 50)
    
    # Test prompt-based tool discovery
    test_prompts = [
        "Send an email to my team about the project update",
        "Create a new document in my workspace",
        "Search for the latest AI research"
    ]
    
    for prompt in test_prompts:
        relevant_tools = await registry.get_tools_for_prompt(prompt, max_tools=3)
        print(f"🎯 Prompt: '{prompt}'")
        print(f"   📋 Relevant Tools ({len(relevant_tools)}):")
        
        for tool_meta in relevant_tools:
            score = tool_meta.get('relevance_score', 0)
            name = tool_meta.get('name', 'Unknown')
            print(f"      • {name} (relevance: {score})")
        print()
    
    # Test 3: Enhanced Metadata Comparison
    print("3️⃣ Testing Enhanced vs Original Metadata")
    print("-" * 50)
    
    # Compare Gmail connector metadata
    gmail_metadata = await registry.get_tool_metadata_by_name("gmail_connector")
    if gmail_metadata:
        print("📧 Gmail Connector Metadata Comparison:")
        
        # Original metadata fields
        print("   📝 Original Fields:")
        print(f"      • Description: {gmail_metadata.get('description', 'N/A')[:60]}...")
        print(f"      • Category: {gmail_metadata.get('category', 'N/A')}")
        print(f"      • Required Params: {len(gmail_metadata.get('required_params', []))}")
        
        # Enhanced metadata fields
        print("   🚀 Enhanced Fields:")
        print(f"      • AI Description: {gmail_metadata.get('ai_description', 'N/A')[:60]}...")
        print(f"      • Capabilities: {', '.join(gmail_metadata.get('capabilities', []))}")
        print(f"      • Use Cases: {len(gmail_metadata.get('use_cases', []))}")
        print(f"      • Example Prompts: {len(gmail_metadata.get('example_prompts', []))}")
        print(f"      • Parameter Suggestions: {gmail_metadata.get('supports_parameter_suggestions', False)}")
        print()
    
    # Test 4: AI Parameter Suggestions
    print("4️⃣ Testing AI Parameter Suggestions")
    print("-" * 50)
    
    test_cases = [
        ("gmail_connector", "Send an email to john@example.com about the meeting"),
        ("notion", "Create a new page for meeting notes"),
        ("perplexity_search", "Find the latest AI research papers")
    ]
    
    for tool_name, prompt in test_cases:
        try:
            suggestions = await registry.generate_parameter_suggestions(tool_name, prompt)
            print(f"🔧 {tool_name}:")
            print(f"   📝 Prompt: '{prompt}'")
            print(f"   💡 Suggestions: {json.dumps(suggestions, indent=6)}")
            print()
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Test 5: Capability-Based Filtering
    print("5️⃣ Testing Capability-Based Filtering")
    print("-" * 50)
    
    capabilities_to_test = ["read", "write", "search"]
    
    for capability in capabilities_to_test:
        tools = await registry.get_tools_by_capability(capability)
        print(f"🔍 Tools with '{capability}' capability:")
        tool_names = [tool.get('name', 'Unknown') for tool in tools]
        print(f"   {', '.join(tool_names[:5])}{'...' if len(tool_names) > 5 else ''}")
        print(f"   Total: {len(tool_names)} tools")
        print()
    
    # Test 6: Enhanced Tool Descriptions
    print("6️⃣ Testing Enhanced Tool Descriptions")
    print("-" * 50)
    
    descriptions = await registry.get_enhanced_tool_descriptions()
    sample_tools = list(descriptions.keys())[:2]
    
    for tool_name in sample_tools:
        description = descriptions[tool_name]
        print(f"🔧 {tool_name.upper()}:")
        print(f"{description[:200]}...")
        print("-" * 30)
    
    # Test 7: Tool Usage Examples
    print("\n7️⃣ Testing Tool Usage Examples")
    print("-" * 50)
    
    if "gmail_connector" in descriptions:
        examples = await registry.get_tool_usage_examples("gmail_connector")
        print("📧 Gmail Connector Usage Examples:")
        print(f"   📝 Example Prompts: {len(examples['example_prompts'])}")
        for i, prompt in enumerate(examples['example_prompts'][:3], 1):
            print(f"      {i}. {prompt}")
        
        print(f"   🎯 Use Cases: {len(examples['use_cases'])}")
        print(f"   💡 Parameter Hints: {len(examples['parameter_hints'])}")
    
    print("\n✅ Hybrid Tool Registry Test Complete!")
    print("=" * 70)
    
    # Summary of hybrid benefits
    print("🎯 Hybrid Approach Benefits:")
    print("   ✅ Robust validation and error handling (Original ToolRegistry)")
    print("   ✅ LangChain compatibility and tool conversion (Original ToolRegistry)")
    print("   ✅ AI-enhanced metadata and descriptions (DynamicToolLoader)")
    print("   ✅ Relevance scoring and prompt-based discovery (DynamicToolLoader)")
    print("   ✅ Parameter suggestions and usage examples (DynamicToolLoader)")
    print("   ✅ Capability-based filtering and search (DynamicToolLoader)")
    print("   🚀 Best of both worlds for ReAct agent performance!")


if __name__ == "__main__":
    asyncio.run(test_hybrid_tool_registry())