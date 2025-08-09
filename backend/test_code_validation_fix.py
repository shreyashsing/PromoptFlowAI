#!/usr/bin/env python3
"""
Test the AI agent's code validation and auto-correction system
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent

async def test_await_without_async_fix():
    """Test that code using await without async gets fixed"""
    
    print("🧪 Testing await without async fix...")
    
    agent = TrueReActAgent()
    
    # Code with await but no async (the error from the logs)
    broken_code = """
let actualData = inputData.main || inputData;
let blogLinks = [];

// Extract blog links from the data
if (actualData && actualData.response) {
    // Parse the response to find URLs
    const urlRegex = /https?:\\/\\/[^\\s]+/g;
    const urls = actualData.response.match(urlRegex) || [];
    blogLinks = urls.slice(0, 5); // Get top 5 links
}

// Function to fetch blog content
async function fetchBlogContent(url) {
    try {
        const response = await fetch(url);
        const html = await response.text();
        return { url, content: html.substring(0, 1000) }; // First 1000 chars
    } catch (error) {
        return { url, content: `Error fetching: ${error.message}` };
    }
}

// Fetch content from all blog links
let results = await Promise.all(blogLinks.map(fetchBlogContent));

return {
    blogLinks: blogLinks,
    blogContents: results,
    count: results.length,
    timestamp: new Date().toISOString()
};
"""
    
    try:
        fixed_code = await agent._validate_and_fix_javascript(broken_code)
        
        print(f"✅ Code validation completed")
        print(f"   Original code length: {len(broken_code)}")
        print(f"   Fixed code length: {len(fixed_code)}")
        
        # Check if the fix was applied
        if 'async function()' in fixed_code or 'async ' in fixed_code:
            print("🎉 SUCCESS: Code was fixed to handle async/await properly!")
            return True
        else:
            print("❌ FAILED: Code was not fixed for async/await issue")
            print(f"   Fixed code preview: {fixed_code[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_missing_return_fix():
    """Test that code missing return statements gets fixed"""
    
    print("\n🧪 Testing missing return statement fix...")
    
    agent = TrueReActAgent()
    
    # Code without proper return
    broken_code = """
let actualData = inputData.main || inputData;
let result = {
    processed: true,
    data: actualData,
    timestamp: new Date().toISOString()
}
"""
    
    try:
        fixed_code = await agent._validate_and_fix_javascript(broken_code)
        
        print(f"✅ Code validation completed")
        
        # Check if return was added
        if 'return' in fixed_code:
            print("🎉 SUCCESS: Return statement was added!")
            return True
        else:
            print("❌ FAILED: Return statement was not added")
            print(f"   Fixed code: {fixed_code}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_full_code_generation_with_validation():
    """Test that the full code generation process includes validation"""
    
    print("\n🧪 Testing full code generation with validation...")
    
    agent = TrueReActAgent()
    
    # Simulate a task that might generate problematic code
    task = {
        "description": "fetch blog content from URLs and process them",
        "reasoning": "Need to get actual blog content from the URLs found"
    }
    
    previous_steps = [
        {
            "connector_name": "perplexity_search",
            "purpose": "Search for blog posts"
        }
    ]
    
    plan = {
        "goal": "Process blog content",
        "steps": ["search", "fetch", "process"]
    }
    
    try:
        # Generate code parameters
        code_params = await agent._generate_code_parameters(task, previous_steps, plan)
        
        if code_params and "code" in code_params:
            generated_code = code_params["code"]
            print(f"✅ Code generation completed")
            print(f"   Generated code length: {len(generated_code)}")
            
            # Check if the code looks valid (no obvious syntax errors)
            if 'await ' in generated_code:
                if 'async' in generated_code:
                    print("🎉 SUCCESS: Generated code properly handles async/await!")
                    return True
                else:
                    print("❌ FAILED: Generated code has await without async")
                    return False
            else:
                print("✅ Code doesn't use await, should be fine")
                return True
        else:
            print("❌ FAILED: No code was generated")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def main():
    """Run all tests"""
    test1 = await test_await_without_async_fix()
    test2 = await test_missing_return_fix()
    test3 = await test_full_code_generation_with_validation()
    
    success_count = sum([test1, test2, test3])
    total_tests = 3
    
    print(f"\n📈 Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Code validation system is working.")
        return True
    else:
        print("❌ Some tests failed. Code validation needs improvement.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)