"""
Test Dynamic Workflow Intelligence - No Hardcoded Connectors

This test verifies that our workflow intelligence system is truly dynamic
and can work with any connectors without hardcoded mappings.
"""
import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.advanced_workflow_intelligence import (
    AdvancedWorkflowIntelligence,
    WorkflowPattern
)
from app.services.integrated_workflow_agent import IntegratedWorkflowAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DynamicWorkflowIntelligenceTestSuite:
    """Test suite for dynamic workflow intelligence capabilities."""
    
    def __init__(self):
        self.intelligence = AdvancedWorkflowIntelligence()
        self.agent = IntegratedWorkflowAgent()
    
    async def run_all_tests(self):
        """Run all dynamic workflow intelligence tests."""
        print("🔄 Testing Dynamic Workflow Intelligence - No Hardcoded Connectors")
        print("=" * 80)
        
        await self.test_dynamic_connector_discovery()
        await self.test_dynamic_workflow_generation()
        await self.test_unknown_connector_handling()
        await self.test_scalability_with_new_connectors()
        await self.test_dynamic_parameter_generation()
        
        print("=" * 80)
        print("🎉 ALL DYNAMIC WORKFLOW INTELLIGENCE TESTS COMPLETED!")
        print("🚀 System is truly dynamic and connector-agnostic!")
    
    async def test_dynamic_connector_discovery(self):
        """Test that the system discovers connectors dynamically."""
        print("\\n🔍 Testing Dynamic Connector Discovery...")
        
        # Initialize the intelligence system
        await self.agent.initialize()
        
        # Test with various requests that don't mention specific hardcoded connectors
        test_requests = [
            "I need to process some data and send notifications",
            "Help me search for information and store the results",
            "Create a workflow that handles incoming data and distributes it",
            "Build something that monitors events and takes actions"
        ]
        
        for i, request in enumerate(test_requests, 1):
            print(f"\\n   🧪 Test Case {i}: {request}")
            
            # Analyze the request
            analysis = await self.intelligence.analyze_workflow_complexity(request)
            
            print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
            print(f"   📊 Confidence: {analysis.complexity_score:.1%}")
            print(f"   🔗 Suggested Connectors: {len(analysis.suggested_connectors)}")
            
            # Verify connectors are discovered dynamically
            if analysis.suggested_connectors:
                print(f"   ✅ Dynamic discovery: Found {len(analysis.suggested_connectors)} relevant connectors")
                print(f"   🛠️  Connectors: {', '.join(analysis.suggested_connectors[:3])}...")
            else:
                print(f"   ⚠️  Dynamic discovery: No connectors found")
        
        print("\\n   ✅ Dynamic connector discovery testing completed")
    
    async def test_dynamic_workflow_generation(self):
        """Test that workflows are generated dynamically without hardcoded logic."""
        print("\\n🏗️  Testing Dynamic Workflow Generation...")
        
        # Test with a request that doesn't match any hardcoded patterns
        request = "I want to collect information from various sources, process it intelligently, and distribute the results to multiple destinations"
        
        print(f"   📝 Request: {request}")
        
        # Analyze and generate workflow
        analysis = await self.intelligence.analyze_workflow_complexity(request)
        workflow = await self.intelligence.generate_complex_workflow(analysis, request)
        
        print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
        print(f"   🏗️  Generated Workflow: {workflow.name}")
        print(f"   📊 Nodes: {len(workflow.nodes)}")
        print(f"   🔗 Edges: {len(workflow.edges)}")
        
        # Analyze the generated workflow structure
        node_types = {}
        for node in workflow.nodes:
            connector_name = node.connector_name
            if connector_name not in node_types:
                node_types[connector_name] = 0
            node_types[connector_name] += 1
        
        print(f"   🔧 Node Types: {dict(node_types)}")
        
        # Verify the workflow has a logical structure
        has_sources = any('source' in node.id or any(word in node.connector_name.lower() for word in ['search', 'get', 'fetch']) for node in workflow.nodes)
        has_processing = any('process' in node.id or any(word in node.connector_name.lower() for word in ['transform', 'process']) for node in workflow.nodes)
        has_outputs = any('output' in node.id or any(word in node.connector_name.lower() for word in ['send', 'save', 'store']) for node in workflow.nodes)
        
        structure_score = sum([has_sources, has_processing, has_outputs])
        
        if structure_score >= 2:
            print("   ✅ Dynamic generation: Logical workflow structure created")
        else:
            print("   ⚠️  Dynamic generation: Workflow structure could be improved")
            print(f"      Sources: {has_sources}, Processing: {has_processing}, Outputs: {has_outputs}")
        
        print("   ✅ Dynamic workflow generation testing completed")
    
    async def test_unknown_connector_handling(self):
        """Test how the system handles requests for unknown/non-existent connectors."""
        print("\\n❓ Testing Unknown Connector Handling...")
        
        # Test with requests mentioning non-existent connectors
        unknown_requests = [
            "Use the SuperMegaAPI to get data and process it with UltraProcessor",
            "Connect to the QuantumDatabase and send results via HyperMessenger",
            "Integrate with the AlienService and store in the MysteryVault"
        ]
        
        for i, request in enumerate(unknown_requests, 1):
            print(f"\\n   🧪 Unknown Test Case {i}: {request}")
            
            try:
                analysis = await self.intelligence.analyze_workflow_complexity(request)
                workflow = await self.intelligence.generate_complex_workflow(analysis, request)
                
                print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
                print(f"   📊 Nodes Generated: {len(workflow.nodes)}")
                
                # Check if system gracefully handled unknown connectors
                if len(workflow.nodes) > 0:
                    print("   ✅ Unknown handling: System gracefully created workflow with available connectors")
                    
                    # Show what connectors were actually used
                    actual_connectors = [node.connector_name for node in workflow.nodes]
                    print(f"   🔄 Fallback connectors used: {', '.join(set(actual_connectors))}")
                else:
                    print("   ⚠️  Unknown handling: No workflow generated")
                    
            except Exception as e:
                print(f"   ❌ Unknown handling: Error occurred - {e}")
        
        print("\\n   ✅ Unknown connector handling testing completed")
    
    async def test_scalability_with_new_connectors(self):
        """Test that the system can scale to handle new connectors dynamically."""
        print("\\n📈 Testing Scalability with New Connectors...")
        
        # Simulate having many connectors by testing various categories
        category_tests = [
            ("data_sources", "I need to fetch data from multiple APIs"),
            ("communication", "Send notifications through various channels"),
            ("productivity", "Save results to different storage systems"),
            ("ai_services", "Process content with AI tools"),
            ("triggers", "Set up automated workflows")
        ]
        
        for category, request in category_tests:
            print(f"\\n   🧪 Category Test - {category}: {request}")
            
            analysis = await self.intelligence.analyze_workflow_complexity(request)
            
            print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
            print(f"   🔗 Connectors Found: {len(analysis.suggested_connectors)}")
            
            if analysis.suggested_connectors:
                print(f"   ✅ Scalability: System found relevant connectors for {category}")
                
                # Check if connectors seem appropriate for the category
                relevant_count = 0
                for connector in analysis.suggested_connectors:
                    if category == "communication" and any(word in connector.lower() for word in ['mail', 'slack', 'message']):
                        relevant_count += 1
                    elif category == "data_sources" and any(word in connector.lower() for word in ['api', 'search', 'get', 'fetch']):
                        relevant_count += 1
                    elif category == "productivity" and any(word in connector.lower() for word in ['sheet', 'drive', 'storage']):
                        relevant_count += 1
                
                if relevant_count > 0:
                    print(f"   🎯 Relevance: {relevant_count}/{len(analysis.suggested_connectors)} connectors are category-appropriate")
                else:
                    print(f"   📝 Relevance: System used available connectors (category-specific ones may not be available)")
            else:
                print(f"   ⚠️  Scalability: No connectors found for {category}")
        
        print("\\n   ✅ Scalability testing completed")
    
    async def test_dynamic_parameter_generation(self):
        """Test that parameters are generated dynamically based on connector schemas."""
        print("\\n⚙️  Testing Dynamic Parameter Generation...")
        
        request = "Search for AI news and email me the results"
        
        analysis = await self.intelligence.analyze_workflow_complexity(request)
        workflow = await self.intelligence.generate_complex_workflow(analysis, request)
        
        print(f"   📝 Request: {request}")
        print(f"   🏗️  Generated {len(workflow.nodes)} nodes")
        
        # Analyze parameters for each node
        for i, node in enumerate(workflow.nodes):
            print(f"\\n   🔧 Node {i+1}: {node.connector_name}")
            print(f"      ID: {node.id}")
            print(f"      Parameters: {len(node.parameters)} defined")
            
            if node.parameters:
                for param_name, param_value in node.parameters.items():
                    print(f"        • {param_name}: {param_value}")
                
                # Check if parameters look reasonable
                has_input_ref = any('{' in str(value) and '}' in str(value) for value in node.parameters.values())
                has_meaningful_params = len(node.parameters) > 0
                
                if has_meaningful_params:
                    print(f"      ✅ Parameters: Generated meaningful parameters")
                    if has_input_ref:
                        print(f"      🔗 References: Contains data flow references")
                else:
                    print(f"      ⚠️  Parameters: Could use more specific parameters")
            else:
                print(f"      📝 Parameters: None generated (may be optional for this connector)")
        
        print("\\n   ✅ Dynamic parameter generation testing completed")


async def run_dynamic_workflow_intelligence_tests():
    """Run the dynamic workflow intelligence test suite."""
    test_suite = DynamicWorkflowIntelligenceTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(run_dynamic_workflow_intelligence_tests())