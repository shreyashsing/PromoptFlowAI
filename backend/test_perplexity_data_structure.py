#!/usr/bin/env python3
"""
Test to understand what data structure Perplexity returns
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.workflow_graph import WorkflowGraph
from app.models.base import WorkflowNode

async def test_perplexity_data_processing():
    """Test how the code node processes Perplexity data"""
    
    print("🧪 Testing Perplexity data processing...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Add a perplexity node
    perplexity_node = WorkflowNode(
        id="perplexity_search-0",
        connector_name="perplexity_search",
        parameters={"query": "AI blog posts"},
        position={"x": 100, "y": 100}
    )
    graph.add_node(perplexity_node)
    
    # Simulate different types of Perplexity responses
    test_cases = [
        {
            "name": "Typical Perplexity Response",
            "data": {
                "response": "Here are some AI blog posts: 1. Understanding Machine Learning 2. Deep Learning Basics 3. AI Ethics",
                "citations": [
                    {"title": "ML Blog", "url": "https://example.com/ml"},
                    {"title": "DL Blog", "url": "https://example.com/dl"}
                ]
            }
        },
        {
            "name": "Simple String Response",
            "data": "AI blog posts: Machine Learning fundamentals, Neural Networks, Computer Vision"
        },
        {
            "name": "Array of Blog Objects",
            "data": {
                "results": [
                    {"title": "AI Blog 1", "content": "Content about AI", "url": "https://blog1.com"},
                    {"title": "AI Blog 2", "content": "More AI content", "url": "https://blog2.com"}
                ]
            }
        },
        {
            "name": "Empty Response",
            "data": {}
        }
    ]
    
    # The JavaScript code from your workflow
    js_code = """
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
  
  // Try other string properties
  for (let key in blog) {
    if (typeof blog[key] === 'string' && blog[key].length > 50) {
      return blog[key];
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
  
  // If no array found, try to extract from main response
  if (blogContents.length === 0) {
    // Check if there's a response field with content
    if (inputData.response && typeof inputData.response === 'string' && inputData.response.length > 0) {
      blogContents.push(inputData.response);
      blogCount = 1;
    }
    // Check if the whole inputData is a string
    else if (typeof inputData === 'string' && inputData.length > 0) {
      blogContents.push(inputData);
      blogCount = 1;
    }
  }
}

// If inputData is a string, treat as single blog content
if (typeof inputData === 'string' && inputData.length > 0) {
  blogContents = [inputData];
  blogCount = 1;
}

const combinedText = blogContents.join('\\n\\n');

return {
  combinedText,
  blogCount,
  timestamp: new Date().toISOString(),
  sourceType: typeof inputData,
  originalKeys: Object.keys(inputData || {}),
  debugInfo: {
    inputDataType: typeof inputData,
    inputDataKeys: inputData ? Object.keys(inputData) : [],
    foundArrays: inputData ? Object.keys(inputData).filter(key => Array.isArray(inputData[key])) : []
  }
};
"""
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['name']}")
        
        # Simulate perplexity node completion
        perplexity_context = graph.node_contexts["perplexity_search-0"]
        perplexity_context.output_data = {"main": test_case["data"]}
        perplexity_context.transition_to(NodeState.SUCCESS, "Search completed")
        
        # Create a code node
        code_node = WorkflowNode(
            id="code-1",
            connector_name="code",
            parameters={"code": js_code},
            position={"x": 300, "y": 100}
        )
        
        # Add to graph if not already there
        if "code-1" not in graph.nodes:
            graph.add_node(code_node)
            graph.add_connection("perplexity_search-0", "code-1", "main", "main")
        
        # Create context for code node
        code_context = graph.node_contexts["code-1"]
        code_context.workflow_graph = graph
        
        # Prepare input data
        input_data = graph.prepare_node_input("code-1")
        print(f"   Input data: {input_data}")
        
        # Resolve parameters (this will include the JavaScript code)
        resolved_params = await resolver.resolve_parameters(code_node, input_data, code_context)
        
        # The resolved code would be executed by the code connector
        # For testing, let's just show what the input would be
        print(f"   Expected result: blogCount > 0 if content found")
        
        # Simulate what the code would return based on the input
        if isinstance(test_case["data"], dict):
            if "results" in test_case["data"] and isinstance(test_case["data"]["results"], list):
                expected_count = len([item for item in test_case["data"]["results"] if isinstance(item, dict) and any(field in item for field in ["content", "body", "text"])])
                print(f"   Expected blogCount: {expected_count}")
            elif "response" in test_case["data"]:
                print(f"   Expected blogCount: 1 (from response field)")
            else:
                print(f"   Expected blogCount: 0 (no recognizable content)")
        elif isinstance(test_case["data"], str):
            print(f"   Expected blogCount: 1 (string input)")
        else:
            print(f"   Expected blogCount: 0 (no content)")

if __name__ == "__main__":
    asyncio.run(test_perplexity_data_processing())