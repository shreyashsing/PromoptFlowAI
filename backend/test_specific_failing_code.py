#!/usr/bin/env python3
"""
Test the specific failing JavaScript code from the logs to ensure it works with our improvements.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_failing_code():
    """Test the specific code that was failing in the logs."""
    
    print("🧪 Testing Specific Failing Code")
    print("=" * 50)
    
    # The original failing code from the logs
    original_failing_code = """// Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step
return items.map(item => {
const { title, content, citation } = item.json || {};

// Helper to clean text: trim, collapse multiple spaces, remove leading/trailing newlines
const cleanText = txt =>
typeof txt === 'string'
? txt.replace(/\\s+/g, ' ').replace(/^\\s+|\\s+$/g, '').replace(/(\\r?\\n){2,}/g, '\\n')
: '';

// Extract main content: if 'content' contains sections, try to get 'Introduction' or main body
let mainContent = '';
if (typeof content === 'string') {
mainContent = cleanText(content);
} else if (content && typeof content === 'object') {
// If content is sectioned, try to find 'Introduction' or 'Main' section
const intro = content.Introduction || content.Main || content.Body;
mainContent = cleanText(intro);
}

// Extract citations: handle array or string
let formattedCitations = [];
if (Array.isArray(citation)) {
formattedCitations = citation.map(cleanText).filter(Boolean);
} else if (typeof citation === 'string') {
formattedCitations = [cleanText(citation)];
}

// Debugging output
console.log({
title: cleanText(title),
mainContent,
formattedCitations
});

// Return formatted object
return {
json: {
title: cleanText(title),
content: mainContent,
citations: formattedCitations,
originalId: item.json?.id || null // preserve original id if present
}
};
});"""
    
    # Improved version using our AI code generator patterns
    improved_code = """// Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step

// Safety check for items array
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

return items.map(item => {
  try {
    const { title, content, citation } = item.json || {};

    // Helper to clean text: trim, collapse multiple spaces, remove leading/trailing newlines
    const cleanText = txt =>
      typeof txt === 'string'
        ? txt.replace(/\\s+/g, ' ').replace(/^\\s+|\\s+$/g, '').replace(/(\\r?\\n){2,}/g, '\\n')
        : '';

    // Extract main content: if 'content' contains sections, try to get 'Introduction' or main body
    let mainContent = '';
    if (typeof content === 'string') {
      mainContent = cleanText(content);
    } else if (content && typeof content === 'object') {
      // If content is sectioned, try to find 'Introduction' or 'Main' section
      const intro = content.Introduction || content.Main || content.Body;
      mainContent = cleanText(intro);
    }

    // Extract citations: handle array or string
    let formattedCitations = [];
    if (Array.isArray(citation)) {
      formattedCitations = citation.map(cleanText).filter(Boolean);
    } else if (typeof citation === 'string') {
      formattedCitations = [cleanText(citation)];
    }

    // Debugging output
    console.log({
      title: cleanText(title),
      mainContent,
      formattedCitations
    });

    // Return formatted object
    return {
      json: {
        title: cleanText(title),
        content: mainContent,
        citations: formattedCitations,
        originalId: item.json?.id || null // preserve original id if present
      }
    };
  } catch (error) {
    console.log('Error processing item:', error.message);
    return {
      json: {
        error: error.message,
        original: item.json || {}
      }
    };
  }
});"""
    
    # Test data similar to what might come from Perplexity
    test_items = [
        {
            "json": {
                "title": "Google's Latest AI Developments",
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
    
    # Create connector and context
    connector = CodeConnector()
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        execution_id="test_execution",
        previous_results={"items": test_items}
    )
    
    # Test cases
    test_cases = [
        ("Original Failing Code", original_failing_code),
        ("Improved Code", improved_code)
    ]
    
    for name, code in test_cases:
        print(f"\n🔍 Testing: {name}")
        print("-" * 30)
        
        params = {
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "code": code,
            "timeout": 30,
            "safe_mode": True,
            "return_console_output": True
        }
        
        try:
            result = await connector.execute(params, context)
            
            if result.success:
                print("✅ Code executed successfully!")
                print(f"📊 Items processed: {result.metadata.get('items_processed', 0)}")
                print(f"⏱️  Execution time: {result.metadata.get('execution_time', 0):.3f}s")
                
                # Show first result item
                if result.data and "items" in result.data and result.data["items"]:
                    first_item = result.data["items"][0]
                    print(f"📄 First result item:")
                    print(json.dumps(first_item, indent=2))
                
                # Show console output if available
                if result.data and "console_output" in result.data:
                    print(f"🖥️  Console output:")
                    print(result.data["console_output"])
                    
            else:
                print(f"❌ Code execution failed: {result.error}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Specific Code Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_failing_code())