#!/usr/bin/env python3
"""
Test that workflows with JavaScript code don't generate reference warnings
"""
import asyncio
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge

# Set up logging to capture warnings
logging.basicConfig(level=logging.WARNING)

async def test_workflow_with_javascript():
    """Test workflow execution with JavaScript code that contains braces"""
    
    print("🧪 Testing workflow with JavaScript code...")
    
    # Create a workflow similar to the one causing issues
    workflow = WorkflowPlan(
        id="test-js-workflow",
        user_id="test-user",
        name="JavaScript Code Test",
        description="Test workflow with JavaScript code containing braces",
        nodes=[
            WorkflowNode(
                id="perplexity_search-0",
                connector_name="perplexity_search",
                parameters={
                    "query": "AI blog posts",
                    "model": "sonar"
                },
                position={"x": 100, "y": 100}
            ),
            WorkflowNode(
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
            ),
            WorkflowNode(
                id="gmail_connector-2",
                connector_name="gmail_connector",
                parameters={
                    "to": "test@example.com",
                    "subject": "Blog Analysis Results",
                    "body": "Found {code.blogCount} blog posts. Combined text: {code.combinedText}"
                },
                position={"x": 500, "y": 100}
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge-1",
                source="perplexity_search-0",
                target="code-1"
            ),
            WorkflowEdge(
                id="edge-2",
                source="code-1",
                target="gmail_connector-2"
            )
        ]
    )
    
    # Capture log messages
    log_messages = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            if "Referenced node" in record.getMessage() and "not found in input data" in record.getMessage():
                log_messages.append(record.getMessage())
    
    # Add log capture handler
    logger = logging.getLogger("app.services.unified_workflow_orchestrator")
    handler = LogCapture()
    logger.addHandler(handler)
    
    try:
        # Execute the workflow (this will likely fail due to missing connectors, but we're testing reference resolution)
        orchestrator = UnifiedWorkflowOrchestrator()
        
        # Test just the parameter resolution part
        graph = await orchestrator._build_intelligent_graph(workflow)
        parameter_resolver = orchestrator.parameter_resolver
        
        # Test code node parameter resolution
        code_node = graph.nodes["code-1"]
        code_context = graph.node_contexts["code-1"]
        code_context.workflow_graph = graph
        
        # Mock some input data
        input_data = {"main": {"results": "Some search results"}}
        
        # Resolve parameters
        resolved_params = await parameter_resolver.resolve_parameters(code_node, input_data, code_context)
        
        print(f"✅ Parameter resolution completed")
        print(f"   Code parameter length: {len(resolved_params.get('code', ''))}")
        
        # Check for warnings about JavaScript code being treated as references
        javascript_warnings = [msg for msg in log_messages if any(js_keyword in msg for js_keyword in [
            "let blogContents", "function extractContent", "typeof blog", "for (let", "if (typeof"
        ])]
        
        if javascript_warnings:
            print("❌ FAILED: JavaScript code was incorrectly treated as node references")
            for warning in javascript_warnings[:3]:  # Show first 3 warnings
                print(f"   Warning: {warning[:100]}...")
            return False
        else:
            print("🎉 SUCCESS: No warnings about JavaScript code being treated as references!")
            
            # Test that valid references still work
            gmail_node = graph.nodes["gmail_connector-2"]
            gmail_context = graph.node_contexts["gmail_connector-2"]
            gmail_context.workflow_graph = graph
            
            # Mock code node completion
            code_context.output_data = {"main": {"blogCount": 5, "combinedText": "Sample blog content"}}
            code_context.transition_to(code_context.state.__class__.SUCCESS, "Code executed")
            graph.mark_node_completed("code-1", {"main": {"blogCount": 5, "combinedText": "Sample blog content"}})
            
            # Prepare input for gmail node
            gmail_input = graph.prepare_node_input("gmail_connector-2")
            gmail_resolved = await parameter_resolver.resolve_parameters(gmail_node, gmail_input, gmail_context)
            
            expected_body = "Found 5 blog posts. Combined text: Sample blog content"
            actual_body = gmail_resolved.get("body", "")
            
            if actual_body == expected_body:
                print("🎉 SUCCESS: Valid node references still work correctly!")
                return True
            else:
                print(f"❌ FAILED: Valid references not working. Expected: '{expected_body}', Got: '{actual_body}'")
                return False
        
    finally:
        logger.removeHandler(handler)

if __name__ == "__main__":
    success = asyncio.run(test_workflow_with_javascript())
    sys.exit(0 if success else 1)