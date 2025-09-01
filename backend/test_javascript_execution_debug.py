#!/usr/bin/env python3
"""
Debug JavaScript execution issues in the code connector.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_simple_javascript():
    """Test simple JavaScript execution."""
    print("🧪 Testing simple JavaScript execution...")
    
    connector = CodeConnector()
    
    # Very simple JavaScript code
    simple_params = {
        "language": "javascript",
        "mode": "runOnceForAllItems",
        "code": "return items;",
        "timeout": 30,
        "safe_mode": True
    }
    
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={},
        previous_results={
            "items": [
                {"json": {"id": 1, "name": "test1"}},
                {"json": {"id": 2, "name": "test2"}}
            ]
        }
    )
    
    try:
        result = await connector.execute(simple_params, context)
        if result.success:
            print("✅ Simple JavaScript execution successful")
            print(f"📊 Result: {result.data}")
        else:
            print(f"❌ Simple JavaScript execution failed: {result.error}")
        return result.success
    except Exception as e:
        print(f"❌ Simple JavaScript execution exception: {e}")
        return False


async def test_complex_javascript():
    """Test the complex JavaScript code from the logs."""
    print("\n🧪 Testing complex JavaScript execution...")
    
    connector = CodeConnector()
    
    # The complex code from the logs (simplified)
    complex_code = """
// Process all articles: extract title, main content, and citations if present
return items.map(item => {
    const { title, content, citation } = item.json || {};
    
    // Helper to clean text
    const cleanText = txt => 
        typeof txt === 'string' 
            ? txt.replace(/\\s+/g, ' ').replace(/^\\s+|\\s+$/g, '').replace(/(\\r?\\n){2,}/g, '\\n')
            : '';
    
    // Extract main content
    let mainContent = '';
    if (typeof content === 'string') {
        mainContent = cleanText(content);
    } else if (content && typeof content === 'object') {
        const intro = content.Introduction || content.Main || content.Body;
        mainContent = cleanText(intro);
    }
    
    // Extract citations
    let formattedCitations = [];
    if (Array.isArray(citation)) {
        formattedCitations = citation.map(cleanText).filter(Boolean);
    } else if (typeof citation === 'string') {
        formattedCitations = [cleanText(citation)];
    }
    
    // Return formatted object
    return {
        json: {
            title: cleanText(title),
            content: mainContent,
            citations: formattedCitations,
            originalId: item.json?.id || null
        }
    };
});
"""
    
    complex_params = {
        "language": "javascript",
        "mode": "runOnceForAllItems",
        "code": complex_code,
        "timeout": 30,
        "safe_mode": True
    }
    
    # Sample data that might come from Perplexity
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={},
        previous_results={
            "items": [
                {
                    "json": {
                        "title": "AI Research Article",
                        "content": "This is a comprehensive article about AI research. It covers multiple topics including machine learning, deep learning, and neural networks.",
                        "citation": "Smith, J. (2024). AI Research Trends. Tech Journal.",
                        "id": 1
                    }
                },
                {
                    "json": {
                        "title": "Machine Learning Guide",
                        "content": {
                            "Introduction": "Machine learning is a subset of AI that focuses on algorithms.",
                            "Main": "The main concepts include supervised and unsupervised learning."
                        },
                        "citation": ["Doe, A. (2024). ML Guide.", "Brown, B. (2024). Learning Systems."],
                        "id": 2
                    }
                }
            ]
        }
    )
    
    try:
        result = await connector.execute(complex_params, context)
        if result.success:
            print("✅ Complex JavaScript execution successful")
            print(f"📊 Result items: {len(result.data.get('items', []))}")
            if result.data.get('items'):
                print(f"📋 Sample result: {json.dumps(result.data['items'][0], indent=2)}")
        else:
            print(f"❌ Complex JavaScript execution failed: {result.error}")
        return result.success
    except Exception as e:
        print(f"❌ Complex JavaScript execution exception: {e}")
        return False


async def test_node_js_availability():
    """Test if Node.js is available and working."""
    print("\n🧪 Testing Node.js availability...")
    
    try:
        process = await asyncio.create_subprocess_exec(
            'node', '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            version = stdout.decode('utf-8').strip()
            print(f"✅ Node.js is available: {version}")
            return True
        else:
            error = stderr.decode('utf-8').strip()
            print(f"❌ Node.js check failed: {error}")
            return False
            
    except Exception as e:
        print(f"❌ Node.js not available: {e}")
        return False


async def test_direct_node_execution():
    """Test direct Node.js execution with the problematic code."""
    print("\n🧪 Testing direct Node.js execution...")
    
    # Create a simple test script
    test_script = """
const items = [
    {"json": {"title": "Test", "content": "Sample content", "id": 1}}
];

console.log('Items loaded:', items.length);

try {
    const result = items.map(item => {
        const { title, content } = item.json || {};
        
        const cleanText = txt => 
            typeof txt === 'string' 
                ? txt.replace(/\\s+/g, ' ').trim()
                : '';
        
        return {
            json: {
                title: cleanText(title),
                content: cleanText(content),
                processed: true
            }
        };
    });
    
    console.log('Processing successful');
    console.log(JSON.stringify({result: result}));
    
} catch (error) {
    console.error('Processing failed:', error.message);
    console.log(JSON.stringify({error: error.message}));
}
"""
    
    try:
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_script)
            temp_file = f.name
        
        process = await asyncio.create_subprocess_exec(
            'node', temp_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        print(f"📤 Node.js stdout: {stdout.decode('utf-8')}")
        print(f"📤 Node.js stderr: {stderr.decode('utf-8')}")
        print(f"📤 Return code: {process.returncode}")
        
        # Clean up
        os.unlink(temp_file)
        
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Direct Node.js execution failed: {e}")
        return False


async def main():
    """Run all debug tests."""
    print("🚀 Starting JavaScript execution debug tests...\n")
    
    # Test 1: Node.js availability
    node_available = await test_node_js_availability()
    
    # Test 2: Direct Node.js execution
    direct_execution = await test_direct_node_execution()
    
    # Test 3: Simple JavaScript through connector
    simple_js = await test_simple_javascript()
    
    # Test 4: Complex JavaScript through connector
    complex_js = await test_complex_javascript()
    
    print(f"\n📊 Debug Results:")
    print(f"   - Node.js available: {'✅ YES' if node_available else '❌ NO'}")
    print(f"   - Direct execution: {'✅ PASS' if direct_execution else '❌ FAIL'}")
    print(f"   - Simple JS connector: {'✅ PASS' if simple_js else '❌ FAIL'}")
    print(f"   - Complex JS connector: {'✅ PASS' if complex_js else '❌ FAIL'}")
    
    if not node_available:
        print("\n💡 Node.js is not available. Install Node.js to fix JavaScript execution.")
    elif not simple_js:
        print("\n💡 Basic JavaScript execution is failing. Check connector implementation.")
    elif not complex_js:
        print("\n💡 Complex JavaScript is failing. Likely a syntax or logic issue in the generated code.")
    else:
        print("\n🎉 All JavaScript execution tests passed!")
    
    return all([node_available, simple_js])


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)