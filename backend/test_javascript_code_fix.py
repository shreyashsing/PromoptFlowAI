#!/usr/bin/env python3
"""
Test that JavaScript code is not treated as node references
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.workflow_graph import WorkflowGraph
from app.models.base import WorkflowNode

async def test_javascript_code_handling():
    """Test that JavaScript code with braces is not treated as node references"""
    
    print("🧪 Testing JavaScript code handling...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Add a perplexity node
    perplexity_node = WorkflowNode(
        id="perplexity_search-0",
        connector_name="perplexity_search",
        parameters={"query": "blog posts about AI"},
        position={"x": 100, "y": 100}
    )
    graph.add_node(perplexity_node)
    
    # Simulate perplexity node completion
    perplexity_context = graph.node_contexts["perplexity_search-0"]
    perplexity_context.output_data = {"main": {"results": "Some blog data"}}
    perplexity_context.transition_to(NodeState.SUCCESS, "Search completed")
    
    # Create a code node with JavaScript that contains braces
    code_node = WorkflowNode(
        id="code-1",
        connector_name="code",
        parameters={
            "code": """
// Inspect inputData and extract blog post contents
let blogContents = [];
let blogCount = 0;

// Helper function to extract content from a blog post object
function extractContent(blog) {
  if (!blog || typeof blog !== 'object') return '';
  // Try common content fields
  const possibleFields = ['content', 'body', 'text', 'description'];
  for (let field of possibleFields) {
    if (typeof blog[field] === 'string' && blog[field].length > 0) {
      return blog[field];
    }
  }
  return '';
}

// Process the input data
if (inputData && typeof inputData === 'object') {
  // Try to find an array property
  for (let key in inputData) {
    if (Array.isArray(inputData[key])) {
      const blogsArray = inputData[key];
      for (let blog of blogsArray) {
        let content = extractContent(blog);
        if (content) {
          blogContents.push(content);
          blogCount++;
        }
      }
      break;
    }
  }
  
  // If inputData is a string, treat as single blog content
  if (blogContents.length === 0 && typeof inputData === 'string') {
    blogContents.push(inputData);
    blogCount = 1;
  }
}

const combinedText = blogContents.join('\\n\\n');

return {
  combinedText,
  blogCount,
  timestamp: new Date().toISOString(),
  sourceType: typeof inputData,
  originalKeys: Object.keys(inputData || {})
};
"""
        },
        position={"x": 300, "y": 100}
    )
    graph.add_node(code_node)
    
    # Add connection
    graph.add_connection("perplexity_search-0", "code-1", "main", "main")
    
    # Create context for code node
    code_context = graph.node_contexts["code-1"]
    code_context.workflow_graph = graph
    
    # Prepare input data
    input_data = graph.prepare_node_input("code-1")
    print(f"📊 Input data: {input_data}")
    
    # Resolve parameters
    resolved_params = await resolver.resolve_parameters(code_node, input_data, code_context)
    
    print(f"✅ Resolved parameters:")
    print(f"   Code length: {len(resolved_params.get('code', ''))}")
    
    # Check that the JavaScript code was not modified
    original_code = code_node.parameters["code"]
    resolved_code = resolved_params.get("code", "")
    
    if original_code == resolved_code:
        print("🎉 SUCCESS: JavaScript code was not modified by reference resolution!")
        return True
    else:
        print("❌ FAILED: JavaScript code was incorrectly modified")
        print(f"   Original length: {len(original_code)}")
        print(f"   Resolved length: {len(resolved_code)}")
        
        # Show differences
        if len(resolved_code) < len(original_code):
            print("   Code was truncated or modified")
        
        return False

async def test_valid_references():
    """Test that valid node references still work"""
    
    print("\n🧪 Testing valid node references...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Add a code node
    code_node = WorkflowNode(
        id="code-1",
        connector_name="code",
        parameters={"code": "return {'result': 'Hello World'}"},
        position={"x": 100, "y": 100}
    )
    graph.add_node(code_node)
    
    # Simulate code node completion
    code_context = graph.node_contexts["code-1"]
    code_context.output_data = {"main": {"result": "Hello World"}}
    code_context.transition_to(NodeState.SUCCESS, "Code executed")
    
    # Create a gmail node that references the code node
    gmail_node = WorkflowNode(
        id="gmail-2",
        connector_name="gmail_connector",
        parameters={
            "to": "test@example.com",
            "subject": "Test",
            "body": "The result is: {code.result}"  # This should still work
        },
        position={"x": 300, "y": 100}
    )
    graph.add_node(gmail_node)
    
    # Add connection
    graph.add_connection("code-1", "gmail-2", "main", "main")
    
    # Create context for gmail node
    gmail_context = graph.node_contexts["gmail-2"]
    gmail_context.workflow_graph = graph
    
    # Prepare input data
    input_data = graph.prepare_node_input("gmail-2")
    
    # Resolve parameters
    resolved_params = await resolver.resolve_parameters(gmail_node, input_data, gmail_context)
    
    expected_body = "The result is: Hello World"
    actual_body = resolved_params.get("body", "")
    
    if actual_body == expected_body:
        print("🎉 SUCCESS: Valid node references still work!")
        return True
    else:
        print(f"❌ FAILED: Valid references not working. Expected: '{expected_body}', Got: '{actual_body}'")
        return False

async def main():
    """Run all tests"""
    test1 = await test_javascript_code_handling()
    test2 = await test_valid_references()
    
    if test1 and test2:
        print("\n🎉 All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)