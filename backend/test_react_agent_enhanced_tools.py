"""
Test ReAct Agent with Enhanced Tool Metadata Integration.
"""
import asyncio
import json
from app.services.true_react_agent import TrueReActAgent
from app.connectors.core.register import register_core_connectors


async def test_react_agent_with_enhanced_tools():
    """Test ReAct agent using enhanced tool metadata."""
    print("🤖 Testing ReAct Agent with Enhanced Tool Metadata")
    print("=" * 60)
    
    # Register connectors
    register_core_connectors()
    
    # Initialize ReAct agent with enhanced tool loader
    agent = TrueReActAgent()
    await agent.initialize()
    
    print("✅ ReAct Agent initialized with enhanced tool metadata")
    print()
    
    # Test 1: Tool Selection with Enhanced Descriptions
    print("1️⃣ Testing Enhanced Tool Selection")
    print("-" * 40)
    
    test_requests = [
        "Send an email to john@example.com about the project deadline",
        "Create a new page in my Notion workspace for meeting notes",
        "Search for the latest information about AI developments",
        "Get data from my Google Sheets budget spreadsheet"
    ]
    
    for request in test_requests:
        print(f"📝 Request: '{request}'")
        
        # Test requirement analysis with enhanced metadata
        try:
            analysis = await agent.reason_about_requirements(request)
            
            print(f"   🧠 Reasoning: {analysis.get('reasoning', 'No reasoning available')[:100]}...")
            print(f"   🎯 Goal: {analysis.get('goal', 'No goal identified')}")
            print(f"   🔧 Suggested Connectors: {', '.join(analysis.get('suggested_connectors', []))}")
            
            # Show how enhanced metadata influenced selection
            if agent.tool_loader:
                relevant_tools = agent.tool_loader.get_tools_for_prompt(request, max_tools=3)
                print(f"   📊 Tool Relevance Scores:")
                for tool in relevant_tools:
                    score = getattr(tool, 'relevance_score', 0)
                    print(f"      • {tool.connector_name}: {score}/10")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()
    
    # Test 2: Parameter Configuration with AI Suggestions
    print("2️⃣ Testing Enhanced Parameter Configuration")
    print("-" * 40)
    
    # Test Gmail connector parameter suggestions
    if agent.tool_loader:
        gmail_tool = agent.tool_loader.load_tool("gmail_connector")
        if gmail_tool:
            test_prompts = [
                "Send an email to team@company.com with subject 'Weekly Update'",
                "Find all unread emails from my manager",
                "Search for emails about the budget proposal"
            ]
            
            print("📧 Gmail Connector Parameter Suggestions:")
            for prompt in test_prompts:
                suggestions = gmail_tool.connector.generate_parameter_suggestions(prompt)
                print(f"   📝 '{prompt}'")
                print(f"   💡 Suggestions: {json.dumps(suggestions, indent=6)}")
                print()
    
    # Test 3: Tool Descriptions for Better AI Understanding
    print("3️⃣ Testing Enhanced Tool Descriptions")
    print("-" * 40)
    
    if agent.tool_loader:
        # Get tool descriptions that the AI agent sees
        tool_descriptions = agent.tool_loader.get_tool_descriptions()
        
        print("🔍 Sample Enhanced Descriptions for AI Agent:")
        sample_tools = ["gmail_connector", "notion", "perplexity_search"]
        
        for tool_name in sample_tools:
            if tool_name in tool_descriptions:
                description = tool_descriptions[tool_name]
                print(f"\n🔧 {tool_name.upper()}:")
                # Show first 200 characters of the enhanced description
                print(f"{description[:200]}...")
                print("-" * 30)
    
    # Test 4: Workflow Building with Enhanced Context
    print("\n4️⃣ Testing Workflow Building with Enhanced Context")
    print("-" * 40)
    
    complex_request = "Send a summary email to my team about the latest AI research findings"
    
    try:
        print(f"📋 Complex Request: '{complex_request}'")
        
        # Initial analysis
        analysis = await agent.reason_about_requirements(complex_request)
        print(f"🧠 Initial Analysis:")
        print(f"   Goal: {analysis.get('goal', 'Not identified')}")
        print(f"   Required Steps: {analysis.get('required_steps', [])}")
        print(f"   Suggested Connectors: {analysis.get('suggested_connectors', [])}")
        
        # Show how the agent would reason about next steps
        if analysis.get('required_steps'):
            print(f"\n🔄 Next Step Reasoning:")
            next_step = await agent.reason_next_step(analysis, [], complex_request)
            
            if next_step:
                print(f"   Action: {next_step.get('action_type', 'Unknown')}")
                print(f"   Connector: {next_step.get('connector_name', 'Not specified')}")
                print(f"   Purpose: {next_step.get('purpose', 'Not specified')}")
                
                # Show parameter configuration with enhanced metadata
                if next_step.get('connector_name') and agent.tool_loader:
                    tool = agent.tool_loader.load_tool(next_step['connector_name'])
                    if tool:
                        param_suggestions = tool.connector.generate_parameter_suggestions(complex_request)
                        print(f"   💡 AI Parameter Suggestions: {json.dumps(param_suggestions, indent=6)}")
        
    except Exception as e:
        print(f"❌ Error in workflow building: {str(e)}")
    
    # Test 5: Comparison with Basic vs Enhanced Metadata
    print("\n5️⃣ Testing Basic vs Enhanced Metadata Impact")
    print("-" * 40)
    
    if agent.tool_loader:
        # Show the difference between basic and enhanced descriptions
        gmail_tool = agent.tool_loader.load_tool("gmail_connector")
        if gmail_tool:
            print("📊 Metadata Comparison for Gmail Connector:")
            
            # Basic description (what we had before)
            basic_desc = "Gmail Connector for email operations using OAuth authentication."
            print(f"📝 Basic Description:")
            print(f"   {basic_desc}")
            
            # Enhanced description (what we have now)
            enhanced_desc = gmail_tool.metadata.description
            print(f"\n🚀 Enhanced Description:")
            print(f"   {enhanced_desc[:300]}...")
            
            print(f"\n📈 Enhancement Benefits:")
            print(f"   • Includes capabilities: {', '.join(gmail_tool.metadata.capabilities)}")
            print(f"   • Shows use cases: {len(gmail_tool.metadata.use_cases)} defined")
            print(f"   • Provides examples: {len(gmail_tool.metadata.examples)} prompts")
            print(f"   • Parameter hints: {len(gmail_tool.connector.get_parameter_hints())} parameters")
    
    print("\n✅ ReAct Agent Enhanced Tool Integration Test Complete!")
    print("=" * 60)
    
    # Summary of improvements
    print("🎯 Key Improvements for ReAct Agent:")
    print("   • Rich tool descriptions reduce hallucination")
    print("   • AI-generated parameter suggestions improve accuracy")
    print("   • Relevance scoring helps with tool selection")
    print("   • Use cases and examples provide better context")
    print("   • Parameter hints guide proper usage")
    print("   • Category and capability filtering improves efficiency")


if __name__ == "__main__":
    asyncio.run(test_react_agent_with_enhanced_tools())