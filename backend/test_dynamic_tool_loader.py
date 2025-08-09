"""
Test Dynamic Tool Loader for ReAct Agent Integration.
"""
import asyncio
import json
from app.services.dynamic_tool_loader import get_tool_loader, DynamicToolLoader
from app.connectors.core.register import register_core_connectors


async def test_dynamic_tool_loader():
    """Test the dynamic tool loader functionality."""
    print("🚀 Testing Dynamic Tool Loader for ReAct Agent")
    print("=" * 60)
    
    # Register connectors
    register_core_connectors()
    
    # Initialize tool loader
    tool_loader = get_tool_loader()
    
    print(f"📊 Tool Loader initialized successfully")
    print()
    
    # Test 1: Load all tools
    print("1️⃣ Testing Load All Tools")
    print("-" * 40)
    
    all_tools = tool_loader.load_all_tools()
    print(f"✅ Loaded {len(all_tools)} tools")
    
    for i, tool in enumerate(all_tools[:3], 1):  # Show first 3
        print(f"{i}. {tool.connector_name}")
        print(f"   📝 Description: {tool.metadata.description[:100]}...")
        print(f"   🏷️  Category: {tool.metadata.category}")
        print(f"   ⚡ Capabilities: {', '.join(tool.metadata.capabilities)}")
        print()
    
    # Test 2: Get tools for specific prompts
    print("2️⃣ Testing Prompt-Based Tool Selection")
    print("-" * 40)
    
    test_prompts = [
        "Send an email to my team about the project update",
        "Create a new document in my workspace",
        "Search for the latest AI research papers",
        "Get data from my spreadsheet"
    ]
    
    for prompt in test_prompts:
        relevant_tools = tool_loader.get_tools_for_prompt(prompt, max_tools=3)
        print(f"🎯 Prompt: '{prompt}'")
        print(f"   📋 Relevant Tools ({len(relevant_tools)}):")
        
        for tool in relevant_tools:
            score = getattr(tool, 'relevance_score', 0)
            print(f"   • {tool.connector_name} (relevance: {score})")
        print()
    
    # Test 3: Test tool execution
    print("3️⃣ Testing Tool Execution")
    print("-" * 40)
    
    # Test Gmail connector tool
    gmail_tool = tool_loader.load_tool("gmail_connector")
    if gmail_tool:
        print(f"📧 Testing Gmail Tool:")
        print(f"   Name: {gmail_tool.connector_name}")
        print(f"   Description: {gmail_tool.metadata.description[:150]}...")
        
        # Test parameter suggestions
        test_prompt = "Send an email to john@example.com about the meeting"
        suggestions = gmail_tool.connector.generate_parameter_suggestions(test_prompt)
        print(f"   💡 Parameter Suggestions for '{test_prompt}':")
        print(f"   {json.dumps(suggestions, indent=6)}")
        print()
    
    # Test 4: LangChain Tool Conversion
    print("4️⃣ Testing LangChain Tool Conversion")
    print("-" * 40)
    
    try:
        # Convert first few tools to LangChain format
        langchain_tools = tool_loader.to_langchain_tools(["gmail_connector", "notion", "http_request"])
        print(f"✅ Converted {len(langchain_tools)} tools to LangChain format")
        
        for tool in langchain_tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                print(f"🔧 {tool.name}")
                print(f"   📝 Description: {tool.description[:100]}...")
            else:
                print(f"🔧 Custom Tool Format: {type(tool)}")
        print()
        
    except Exception as e:
        print(f"⚠️  LangChain conversion failed (expected if LangChain not installed): {str(e)}")
        print()
    
    # Test 5: Tool Registry JSON
    print("5️⃣ Testing Tool Registry JSON Export")
    print("-" * 40)
    
    registry_json = tool_loader.get_tool_registry_json()
    
    print(f"📊 Registry Statistics:")
    print(f"   • Total Tools: {registry_json['metadata']['total_tools']}")
    print(f"   • Categories: {len(registry_json['categories'])}")
    print(f"   • Capabilities: {len(registry_json['capabilities'])}")
    
    print(f"\n📂 Categories:")
    for category, tools in registry_json['categories'].items():
        print(f"   • {category.title()}: {len(tools)} tools")
    
    print(f"\n⚡ Capabilities:")
    for capability, tools in registry_json['capabilities'].items():
        print(f"   • {capability.title()}: {len(tools)} tools")
    
    # Test 6: Category and Capability Filtering
    print("\n6️⃣ Testing Category and Capability Filtering")
    print("-" * 40)
    
    # Test category filtering
    communication_tools = tool_loader.load_tools_by_category("communication")
    print(f"📞 Communication Tools: {len(communication_tools)}")
    for tool in communication_tools:
        print(f"   • {tool.connector_name}")
    
    # Test capability filtering
    search_tools = tool_loader.load_tools_by_capability("search")
    print(f"\n🔍 Search-capable Tools: {len(search_tools)}")
    for tool in search_tools:
        print(f"   • {tool.connector_name}")
    
    # Test 7: Enhanced Descriptions for ReAct Agent
    print("\n7️⃣ Testing Enhanced Descriptions for ReAct Agent")
    print("-" * 40)
    
    tool_descriptions = tool_loader.get_tool_descriptions()
    
    print("📋 Sample Enhanced Tool Descriptions:")
    sample_tools = list(tool_descriptions.keys())[:2]
    
    for tool_name in sample_tools:
        description = tool_descriptions[tool_name]
        print(f"\n🔧 {tool_name.upper()}:")
        print(f"{description}")
        print("-" * 30)
    
    print("\n✅ Dynamic Tool Loader Test Complete!")
    print("=" * 60)
    
    # Summary for ReAct Agent Integration
    print(f"🤖 ReAct Agent Integration Summary:")
    print(f"   • {len(all_tools)} tools available with enhanced metadata")
    print(f"   • Rich descriptions include capabilities, use cases, and examples")
    print(f"   • Intelligent parameter suggestions based on user prompts")
    print(f"   • Relevance scoring for better tool selection")
    print(f"   • LangChain compatibility for easy integration")
    print(f"   • Category and capability-based filtering")


if __name__ == "__main__":
    asyncio.run(test_dynamic_tool_loader())