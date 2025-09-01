#!/usr/bin/env python3
"""
Test the exact JavaScript code from the workflow logs.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_exact_workflow_code():
    """Test the exact JavaScript code from the workflow logs."""
    print("🧪 Testing exact workflow JavaScript code...")
    
    # This is the exact code from the logs
    exact_code = """// Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step
return items.map(item => {
const { title, content, citation } = item.json || {};
// Helper to clean text: trim, collapse multiple spaces, remove leading/trailing newlines
const cleanText = txt =>
typeof txt === 'string'
? txt.replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '').replace(/(\r?\n){2,}/g, '\n')
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
    
    connector = CodeConnector()
    
    params = {
        "language": "javascript",
        "mode": "runOnceForAllItems",
        "code": exact_code,
        "timeout": 30,
        "safe_mode": True
    }
    
    # Simulate Perplexity search results
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={},
        previous_results={
            "items": [
                {
                    "json": {
                        "text": "This is a sample search result about AI and machine learning. It contains information about recent developments in artificial intelligence.",
                        "url": "https://example.com/ai-article",
                        "title": "AI and Machine Learning Trends",
                        "id": 1
                    }
                },
                {
                    "json": {
                        "text": "Another article about natural language processing and its applications in chatbots and virtual assistants.",
                        "url": "https://example.com/nlp-article", 
                        "title": "NLP Applications",
                        "id": 2
                    }
                }
            ]
        }
    )
    
    try:
        print("📝 Testing exact workflow code...")
        result = await connector.execute(params, context)
        
        if result.success:
            print("✅ Exact workflow code execution successful")
            print(f"📊 Result items: {len(result.data.get('items', []))}")
            if result.data.get('items'):
                print(f"📋 Sample result: {json.dumps(result.data['items'][0], indent=2)}")
            if result.data.get('console_output'):
                print(f"📺 Console output: {result.data['console_output']}")
        else:
            print(f"❌ Exact workflow code execution failed: {result.error}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Exact workflow code execution exception: {e}")
        return False


async def test_fixed_workflow_code():
    """Test a fixed version of the workflow code."""
    print("\n🧪 Testing fixed workflow JavaScript code...")
    
    # Fixed version with proper formatting and error handling
    fixed_code = """
// Process all articles: extract title, main content, and citations if present
try {
    return items.map(item => {
        const { title, content, citation } = item.json || {};
        
        // Helper to clean text: trim, collapse multiple spaces, remove leading/trailing newlines
        const cleanText = txt => {
            if (typeof txt !== 'string') return '';
            return txt.replace(/\\s+/g, ' ').replace(/^\\s+|\\s+$/g, '').replace(/(\\r?\\n){2,}/g, '\\n');
        };
        
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
        console.log('Processing item:', {
            title: cleanText(title),
            mainContent: mainContent.substring(0, 50) + '...',
            citationCount: formattedCitations.length
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
    });
} catch (error) {
    console.error('Processing error:', error.message);
    return items; // Return original items if processing fails
}
"""
    
    connector = CodeConnector()
    
    params = {
        "language": "javascript",
        "mode": "runOnceForAllItems",
        "code": fixed_code,
        "timeout": 30,
        "safe_mode": True
    }
    
    # Same test data
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={},
        previous_results={
            "items": [
                {
                    "json": {
                        "text": "This is a sample search result about AI and machine learning. It contains information about recent developments in artificial intelligence.",
                        "url": "https://example.com/ai-article",
                        "title": "AI and Machine Learning Trends",
                        "id": 1
                    }
                },
                {
                    "json": {
                        "text": "Another article about natural language processing and its applications in chatbots and virtual assistants.",
                        "url": "https://example.com/nlp-article", 
                        "title": "NLP Applications",
                        "id": 2
                    }
                }
            ]
        }
    )
    
    try:
        print("📝 Testing fixed workflow code...")
        result = await connector.execute(params, context)
        
        if result.success:
            print("✅ Fixed workflow code execution successful")
            print(f"📊 Result items: {len(result.data.get('items', []))}")
            if result.data.get('items'):
                print(f"📋 Sample result: {json.dumps(result.data['items'][0], indent=2)}")
            if result.data.get('console_output'):
                print(f"📺 Console output: {result.data['console_output']}")
        else:
            print(f"❌ Fixed workflow code execution failed: {result.error}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Fixed workflow code execution exception: {e}")
        return False


async def main():
    """Run the workflow code tests."""
    print("🚀 Starting workflow code debug tests...\n")
    
    # Test 1: Exact code from logs
    exact_success = await test_exact_workflow_code()
    
    # Test 2: Fixed version
    fixed_success = await test_fixed_workflow_code()
    
    print(f"\n📊 Workflow Code Results:")
    print(f"   - Exact workflow code: {'✅ PASS' if exact_success else '❌ FAIL'}")
    print(f"   - Fixed workflow code: {'✅ PASS' if fixed_success else '❌ FAIL'}")
    
    if not exact_success and fixed_success:
        print("\n💡 The original code has formatting/syntax issues. The fixed version works.")
        print("💡 The AI code generator needs to produce better formatted JavaScript.")
    elif exact_success:
        print("\n🤔 The exact code works in isolation. The issue might be with the input data structure.")
    else:
        print("\n❌ Both versions failed. There might be a deeper issue.")
    
    return fixed_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)