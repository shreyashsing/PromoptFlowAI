"""
Demo script for Notion Connector - shows real usage examples.

NOTE: This script requires a real Notion API key to run.
Set the NOTION_API_KEY environment variable or update the script.
"""
import asyncio
import os
from app.connectors.core.notion_connector import NotionConnector
from app.models.connector import ConnectorExecutionContext


async def demo_notion_connector():
    """Demonstrate Notion connector functionality."""
    print("🚀 Notion Connector Demo")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("⚠️  No API key found!")
        print("   To run this demo with real API calls:")
        print("   1. Get your integration token from https://www.notion.so/my-integrations")
        print("   2. Set environment variable: NOTION_API_KEY=your_token_here")
        print("   3. Run this script again")
        print("\n📋 Demo will show parameter examples without making API calls...")
        api_key = "demo_key"
    else:
        print(f"✅ Found API key: {api_key[:10]}...")
    
    # Initialize connector
    connector = NotionConnector()
    context = ConnectorExecutionContext(
        user_id="demo-user",
        auth_tokens={"api_key": api_key},
        previous_results={}
    )
    
    # Demo scenarios
    scenarios = [
        {
            "title": "🔍 Search for Pages",
            "description": "Search for pages containing specific text",
            "params": {
                "resource": "page",
                "operation": "search_pages",
                "query": "meeting notes",
                "simple_output": True,
                "page_size": 10
            }
        },
        {
            "title": "📄 Get Page Information",
            "description": "Retrieve information about a specific page",
            "params": {
                "resource": "page",
                "operation": "get_page",
                "page_id": "12345678-1234-1234-1234-123456789012",  # Replace with real page ID
                "simple_output": True
            }
        },
        {
            "title": "🗃️ List All Databases",
            "description": "Get all databases you have access to",
            "params": {
                "resource": "database",
                "operation": "get_all_databases",
                "simple_output": True,
                "page_size": 20
            }
        },
        {
            "title": "📝 Create New Page",
            "description": "Create a new page with content",
            "params": {
                "resource": "page",
                "operation": "create_page",
                "parent_page_id": "12345678-1234-1234-1234-123456789012",  # Replace with real parent page ID
                "title": "Demo Page from PromptFlow AI",
                "content": "This page was created by the PromptFlow AI Notion connector!\n\nIt supports multiple paragraphs and rich content.",
                "icon_type": "emoji",
                "icon_value": "🤖"
            }
        },
        {
            "title": "📊 Query Database Pages",
            "description": "Get pages from a database with filtering",
            "params": {
                "resource": "database_page",
                "operation": "get_all_database_pages",
                "database_id": "12345678-1234-1234-1234-123456789012",  # Replace with real database ID
                "simple_output": True,
                "page_size": 10,
                "filter": {
                    "property": "Status",
                    "select": {
                        "equals": "In Progress"
                    }
                }
            }
        },
        {
            "title": "➕ Add Content to Page",
            "description": "Append blocks to an existing page",
            "params": {
                "resource": "block",
                "operation": "append_block",
                "block_id": "12345678-1234-1234-1234-123456789012",  # Replace with real page/block ID
                "content": "This content was added by PromptFlow AI!\n\nYou can add multiple paragraphs this way."
            }
        },
        {
            "title": "👥 List Workspace Users",
            "description": "Get all users in the workspace",
            "params": {
                "resource": "user",
                "operation": "get_all_users",
                "page_size": 50
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['title']}")
        print(f"   {scenario['description']}")
        print(f"   Parameters:")
        
        # Pretty print parameters
        for key, value in scenario['params'].items():
            if isinstance(value, dict):
                print(f"     {key}: {value}")
            else:
                print(f"     {key}: {value}")
        
        if api_key != "demo_key":
            print(f"   🔄 Executing...")
            try:
                result = await connector.execute(scenario['params'], context)
                if result.success:
                    print(f"   ✅ Success: {result.message}")
                    if isinstance(result.data, list):
                        print(f"   📊 Retrieved {len(result.data)} items")
                    elif isinstance(result.data, dict):
                        print(f"   📄 Retrieved data with {len(result.data)} fields")
                else:
                    print(f"   ❌ Failed: {result.error}")
            except Exception as e:
                error_msg = str(e)
                if "not found" in error_msg.lower():
                    print(f"   ⚠️  Resource not found (expected with demo IDs)")
                elif "permission" in error_msg.lower():
                    print(f"   ⚠️  Permission denied (integration needs access)")
                else:
                    print(f"   ❌ Error: {error_msg}")
        else:
            print(f"   📋 (Demo mode - no API calls made)")
    
    print(f"\n🎉 Demo Complete!")
    
    if api_key == "demo_key":
        print(f"\n💡 To see real results:")
        print(f"   1. Create a Notion integration at https://www.notion.so/my-integrations")
        print(f"   2. Copy your integration token")
        print(f"   3. Set NOTION_API_KEY environment variable")
        print(f"   4. Update the page/database IDs in this script")
        print(f"   5. Make sure your integration has access to the pages/databases")
        print(f"   6. Run the script again")


async def demo_block_formatting():
    """Demonstrate block formatting capabilities."""
    print(f"\n🎨 Block Formatting Demo")
    print("=" * 30)
    
    connector = NotionConnector()
    
    # Test different block types
    test_blocks = [
        {"type": "heading_1", "content": "Main Heading"},
        {"type": "paragraph", "content": "This is a regular paragraph with some text."},
        {"type": "heading_2", "content": "Subheading"},
        {"type": "bulleted_list_item", "content": "First bullet point"},
        {"type": "bulleted_list_item", "content": "Second bullet point"},
        {"type": "numbered_list_item", "content": "First numbered item"},
        {"type": "numbered_list_item", "content": "Second numbered item"},
        {"type": "to_do", "content": "Task to complete"},
        {"type": "quote", "content": "This is an inspirational quote."},
        {"type": "code", "content": "console.log('Hello from PromptFlow AI!');"}
    ]
    
    print(f"📝 Formatting {len(test_blocks)} different block types:")
    
    formatted_blocks = connector._format_blocks(test_blocks)
    
    for i, (original, formatted) in enumerate(zip(test_blocks, formatted_blocks)):
        print(f"\n   {i+1}. {original['type'].upper()}")
        print(f"      Input: {original['content']}")
        print(f"      Output: Notion API block with type '{formatted['type']}'")
        
        # Show the structure
        block_content = formatted.get(formatted['type'], {})
        if 'rich_text' in block_content:
            text_content = block_content['rich_text'][0]['text']['content']
            print(f"      Content: {text_content}")
    
    print(f"\n✅ All block types formatted successfully!")


async def demo_text_conversion():
    """Demonstrate text to blocks conversion."""
    print(f"\n📄 Text to Blocks Conversion Demo")
    print("=" * 40)
    
    connector = NotionConnector()
    
    sample_text = """Welcome to PromptFlow AI!

This is the first paragraph of content that will be converted into Notion blocks.

Here's a second paragraph with more information about our platform.

And finally, a third paragraph to demonstrate how multiple paragraphs are handled.

Each paragraph becomes a separate block in Notion."""
    
    print(f"📝 Converting text to blocks:")
    print(f"Input text ({len(sample_text)} characters):")
    print(f"'{sample_text[:100]}...'")
    
    blocks = connector._create_text_blocks(sample_text)
    
    print(f"\n✅ Converted to {len(blocks)} paragraph blocks:")
    
    for i, block in enumerate(blocks, 1):
        content = block['paragraph']['rich_text'][0]['text']['content']
        print(f"   {i}. {content[:50]}{'...' if len(content) > 50 else ''}")
    
    print(f"\n🎯 Each block is properly formatted for Notion API!")


async def main():
    """Run all demos."""
    await demo_notion_connector()
    await demo_block_formatting()
    await demo_text_conversion()
    
    print(f"\n" + "=" * 60)
    print(f"🎉 ALL DEMOS COMPLETE!")
    print(f"=" * 60)
    print(f"The Notion connector is ready for use in PromptFlow AI workflows!")


if __name__ == "__main__":
    asyncio.run(main())