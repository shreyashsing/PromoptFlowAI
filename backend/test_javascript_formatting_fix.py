#!/usr/bin/env python3
"""
Test the JavaScript formatting fix for the AI code generator.
"""
import asyncio
import sys
import os
import re

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.ai_code_generator import AICodeGenerator
from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


def test_javascript_formatting_fix():
    """Test the JavaScript formatting fix method."""
    print("🧪 Testing JavaScript formatting fix...")
    
    generator = AICodeGenerator()
    
    # The problematic code from the logs
    broken_code = """// Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step
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
    
    print("📝 Original broken code:")
    print("=" * 50)
    print(broken_code[:200] + "...")
    print("=" * 50)
    
    # Apply the formatting fix
    fixed_code = generator._fix_javascript_formatting(broken_code)
    
    print("\n📝 Fixed code:")
    print("=" * 50)
    print(fixed_code[:200] + "...")
    print("=" * 50)
    
    # Check if the specific regex issue is fixed
    regex_pattern = r'/([^/\n]+)\n\s*([^/\n]*)/([gimuy]*)'
    broken_matches = re.findall(regex_pattern, broken_code)
    fixed_matches = re.findall(regex_pattern, fixed_code)
    
    print(f"\n🔍 Broken regex patterns found: {len(broken_matches)}")
    print(f"🔍 Fixed regex patterns remaining: {len(fixed_matches)}")
    
    if broken_matches:
        print(f"📋 Broken patterns: {broken_matches}")
    
    return fixed_code


async def test_fixed_code_execution():
    """Test execution of the fixed JavaScript code."""
    print("\n🧪 Testing fixed code execution...")
    
    generator = AICodeGenerator()
    
    # The problematic code from the logs
    broken_code = """// Process all articles: extract title, main content, and citations if present, clean up whitespace, and format for next step
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
    
    # Apply the complete enhancement process
    fixed_code = await generator._enhance_code(broken_code, "javascript", "runOnceForAllItems", {})
    
    print("📝 Enhanced code:")
    print("=" * 50)
    print(fixed_code)
    print("=" * 50)
    
    # Test execution
    connector = CodeConnector()
    
    params = {
        "language": "javascript",
        "mode": "runOnceForAllItems",
        "code": fixed_code,
        "timeout": 30,
        "safe_mode": True
    }
    
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={},
        previous_results={
            "items": [
                {
                    "json": {
                        "text": "This is a sample search result about AI and machine learning.",
                        "url": "https://example.com/ai-article",
                        "title": "AI and Machine Learning Trends",
                        "id": 1
                    }
                }
            ]
        }
    )
    
    try:
        result = await connector.execute(params, context)
        
        if result.success:
            print("✅ Fixed code execution successful!")
            print(f"📊 Result items: {len(result.data.get('items', []))}")
            if result.data.get('console_output'):
                print(f"📺 Console output: {result.data['console_output']}")
            return True
        else:
            print(f"❌ Fixed code execution failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Fixed code execution exception: {e}")
        return False


async def main():
    """Run the formatting fix tests."""
    print("🚀 Starting JavaScript formatting fix tests...\n")
    
    # Test 1: Formatting fix
    fixed_code = test_javascript_formatting_fix()
    
    # Test 2: Execution test
    execution_success = await test_fixed_code_execution()
    
    print(f"\n📊 Formatting Fix Results:")
    print(f"   - Code formatting: {'✅ APPLIED' if fixed_code else '❌ FAILED'}")
    print(f"   - Code execution: {'✅ PASS' if execution_success else '❌ FAIL'}")
    
    if execution_success:
        print("\n🎉 JavaScript formatting fix is working! The AI code generator will now produce valid JavaScript.")
    else:
        print("\n❌ The formatting fix needs more work. Check the enhanced code output above.")
    
    return execution_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)