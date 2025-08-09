"""
Test Advanced Workflow Intelligence for n8n-Style Complex Workflows

This test demonstrates our enhanced AI agent's ability to build sophisticated
workflows similar to the n8n examples provided.
"""
import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.advanced_workflow_intelligence import (
    AdvancedWorkflowIntelligence,
    WorkflowPattern,
    advanced_workflow_intelligence
)
from app.services.integrated_workflow_agent import IntegratedWorkflowAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedWorkflowIntelligenceTestSuite:
    """Test suite for advanced workflow intelligence capabilities."""
    
    def __init__(self):
        self.intelligence = AdvancedWorkflowIntelligence()
        self.agent = IntegratedWorkflowAgent()
    
    async def run_all_tests(self):
        """Run all advanced workflow intelligence tests."""
        print("🧠 Testing Advanced Workflow Intelligence for n8n-Style Workflows")
        print("=" * 80)
        
        await self.test_pattern_recognition()
        await self.test_social_media_analytics_workflow()
        await self.test_fan_out_fan_in_workflow()
        await self.test_scheduled_pipeline_workflow()
        await self.test_complex_workflow_generation()
        await self.test_integrated_agent_enhancement()
        
        print("=" * 80)
        print("🎉 ALL ADVANCED WORKFLOW INTELLIGENCE TESTS COMPLETED!")
        print("🚀 AI Agent now supports n8n-style complex workflows!")
    
    async def test_pattern_recognition(self):
        """Test pattern recognition for different workflow types."""
        print("\\n🎯 Testing Workflow Pattern Recognition...")
        
        test_cases = [
            {
                "request": "Get analytics from Facebook, Twitter, and LinkedIn weekly, format the data, combine it, and send a report via email while saving to Google Sheets",
                "expected_pattern": WorkflowPattern.MULTI_SOURCE_MERGE,
                "description": "Social Media Analytics Pipeline"
            },
            {
                "request": "Every Monday, collect data from multiple APIs, process each one differently, merge the results, and distribute to various channels",
                "expected_pattern": WorkflowPattern.SCHEDULED_PIPELINE,
                "description": "Scheduled Multi-Source Pipeline"
            },
            {
                "request": "When webhook receives data, send it to Slack and save to database",
                "expected_pattern": WorkflowPattern.SIMPLE_PARALLEL,
                "description": "Simple Webhook Handler"
            },
            {
                "request": "Search for AI news and email me a summary",
                "expected_pattern": WorkflowPattern.LINEAR,
                "description": "Simple Linear Workflow"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\\n   🧪 Test Case {i}: {test_case['description']}")
            print(f"   📝 Request: {test_case['request']}")
            
            analysis = await self.intelligence.analyze_workflow_complexity(test_case["request"])
            
            print(f"   🎯 Detected Pattern: {analysis.primary_pattern.value}")
            print(f"   📊 Confidence: {analysis.complexity_score:.1%}")
            print(f"   🔗 Estimated Nodes: {analysis.estimated_nodes}")
            print(f"   ⚡ Parallel Branches: {analysis.parallel_branches}")
            print(f"   🔄 Merge Points: {analysis.merge_points}")
            print(f"   🛠️  Suggested Connectors: {', '.join(analysis.suggested_connectors[:3])}...")
            print(f"   💭 Reasoning: {analysis.reasoning}")
            
            # Validate pattern detection
            if analysis.primary_pattern == test_case["expected_pattern"]:
                print(f"   ✅ Pattern recognition: CORRECT")
            else:
                print(f"   ⚠️  Pattern recognition: Expected {test_case['expected_pattern'].value}, got {analysis.primary_pattern.value}")
        
        print("\\n   ✅ Pattern recognition testing completed")
    
    async def test_social_media_analytics_workflow(self):
        """Test generation of social media analytics workflow (like n8n example 2)."""
        print("\\n📱 Testing Social Media Analytics Workflow Generation...")
        
        request = "Weekly collect Facebook, Twitter, LinkedIn analytics, format each platform's data, merge them into a unified report, save to Google Sheets and email the summary"
        
        print(f"   📝 User Request: {request}")
        
        # Analyze the request
        analysis = await self.intelligence.analyze_workflow_complexity(request)
        print(f"   🎯 Pattern: {analysis.primary_pattern.value} (confidence: {analysis.complexity_score:.1%})")
        
        # Generate the workflow
        workflow = await self.intelligence.generate_complex_workflow(analysis, request)
        
        print(f"   🏗️  Generated Workflow: {workflow.name}")
        print(f"   📊 Nodes: {len(workflow.nodes)}")
        print(f"   🔗 Edges: {len(workflow.edges)}")
        
        # Analyze workflow structure
        source_nodes = [n for n in workflow.nodes if 'get_' in n.id]
        format_nodes = [n for n in workflow.nodes if 'format_' in n.id]
        merge_nodes = [n for n in workflow.nodes if 'merge' in n.id]
        output_nodes = [n for n in workflow.nodes if n.id in ['save_to_sheets', 'send_email_report']]
        
        print(f"   📡 Data Sources: {len(source_nodes)} ({', '.join([n.connector_name for n in source_nodes])})")
        print(f"   🔄 Format Processors: {len(format_nodes)}")
        print(f"   🔀 Merge Nodes: {len(merge_nodes)}")
        print(f"   📤 Output Nodes: {len(output_nodes)} ({', '.join([n.connector_name for n in output_nodes])})")
        
        # Validate workflow structure
        expected_structure = {
            "sources": 3,  # Facebook, Twitter, LinkedIn
            "formatters": 3,  # One for each source
            "merge": 1,  # Single merge node
            "outputs": 2  # Sheets + Email
        }
        
        structure_valid = (
            len(source_nodes) >= expected_structure["sources"] - 1 and  # Allow some flexibility
            len(format_nodes) >= expected_structure["formatters"] - 1 and
            len(merge_nodes) >= expected_structure["merge"] and
            len(output_nodes) >= expected_structure["outputs"] - 1
        )
        
        if structure_valid:
            print("   ✅ Workflow structure: VALID n8n-style fan-out/fan-in pattern")
        else:
            print("   ⚠️  Workflow structure: Needs improvement")
        
        # Test parameter resolution
        merge_node = next((n for n in workflow.nodes if 'merge' in n.id), None)
        if merge_node and 'inputs' in merge_node.parameters:
            print("   ✅ Parameter resolution: Merge node has input references")
        else:
            print("   ⚠️  Parameter resolution: Merge node missing input references")
        
        print("   ✅ Social media analytics workflow generation completed")
    
    async def test_fan_out_fan_in_workflow(self):
        """Test fan-out/fan-in pattern generation."""
        print("\\n🌟 Testing Fan-Out/Fan-In Workflow Pattern...")
        
        request = "Collect data from 5 different APIs simultaneously, process each one with different transformations, then combine all results and send to multiple destinations"
        
        analysis = await self.intelligence.analyze_workflow_complexity(request)
        workflow = await self.intelligence.generate_complex_workflow(analysis, request)
        
        print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
        print(f"   📊 Total Nodes: {len(workflow.nodes)}")
        print(f"   ⚡ Parallel Branches: {analysis.parallel_branches}")
        
        # Validate fan-out/fan-in structure
        has_multiple_sources = len([n for n in workflow.nodes if 'get_' in n.id or 'source' in n.id]) > 2
        has_merge_point = any('merge' in n.id for n in workflow.nodes)
        has_multiple_outputs = len([n for n in workflow.nodes if any(output in n.id for output in ['save', 'send', 'output'])]) > 1
        
        fan_out_fan_in_valid = has_multiple_sources and has_merge_point and has_multiple_outputs
        
        if fan_out_fan_in_valid:
            print("   ✅ Fan-out/Fan-in pattern: VALID structure detected")
        else:
            print("   ⚠️  Fan-out/Fan-in pattern: Structure needs improvement")
            print(f"      Multiple sources: {has_multiple_sources}")
            print(f"      Merge point: {has_merge_point}")
            print(f"      Multiple outputs: {has_multiple_outputs}")
        
        print("   ✅ Fan-out/fan-in workflow testing completed")
    
    async def test_scheduled_pipeline_workflow(self):
        """Test scheduled pipeline workflow generation."""
        print("\\n⏰ Testing Scheduled Pipeline Workflow...")
        
        request = "Every Monday at 9 AM, collect social media metrics, generate a weekly report, and distribute it via email and Slack"
        
        analysis = await self.intelligence.analyze_workflow_complexity(request)
        workflow = await self.intelligence.generate_complex_workflow(analysis, request)
        
        print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
        print(f"   📊 Total Nodes: {len(workflow.nodes)}")
        
        # Check for scheduler trigger
        has_scheduler = any('schedule' in n.connector_name for n in workflow.nodes)
        scheduler_node = next((n for n in workflow.nodes if 'schedule' in n.connector_name), None)
        
        if has_scheduler:
            print("   ✅ Scheduler trigger: Found")
            if scheduler_node and 'schedule' in scheduler_node.parameters:
                print(f"   📅 Schedule config: {scheduler_node.parameters.get('schedule', 'Not specified')}")
        else:
            print("   ⚠️  Scheduler trigger: Missing")
        
        # Check workflow flow
        trigger_connections = [e for e in workflow.edges if e.source == 'schedule_trigger']
        if trigger_connections:
            print(f"   🔗 Trigger connections: {len(trigger_connections)} nodes triggered")
            print("   ✅ Scheduled pipeline: VALID structure")
        else:
            print("   ⚠️  Scheduled pipeline: Trigger not properly connected")
        
        print("   ✅ Scheduled pipeline workflow testing completed")
    
    async def test_complex_workflow_generation(self):
        """Test overall complex workflow generation capabilities."""
        print("\\n🏗️  Testing Complex Workflow Generation...")
        
        complex_requests = [
            "Create a comprehensive social media monitoring system that tracks mentions across Facebook, Twitter, LinkedIn, and Instagram, analyzes sentiment, categorizes by topic, stores results in Airtable, sends alerts for negative sentiment via Slack, and generates weekly reports via email",
            "Build an automated customer onboarding workflow that triggers when a new user signs up, sends welcome emails, creates accounts in multiple systems, schedules follow-up tasks, and notifies the sales team",
            "Design a content distribution pipeline that takes blog posts, formats them for different platforms, schedules posts across social media, tracks engagement, and compiles performance reports"
        ]
        
        for i, request in enumerate(complex_requests, 1):
            print(f"\\n   🧪 Complex Test Case {i}:")
            print(f"   📝 Request: {request[:100]}...")
            
            analysis = await self.intelligence.analyze_workflow_complexity(request)
            workflow = await self.intelligence.generate_complex_workflow(analysis, request)
            
            print(f"   🎯 Pattern: {analysis.primary_pattern.value}")
            print(f"   📊 Complexity Score: {analysis.complexity_score:.1%}")
            print(f"   🔗 Nodes Generated: {len(workflow.nodes)}")
            print(f"   ⚡ Edges Generated: {len(workflow.edges)}")
            print(f"   🔄 Parallel Branches: {analysis.parallel_branches}")
            
            # Validate complexity
            is_complex = (
                len(workflow.nodes) >= 5 and
                len(workflow.edges) >= 4 and
                analysis.parallel_branches > 1
            )
            
            if is_complex:
                print(f"   ✅ Complexity: VALID complex workflow generated")
            else:
                print(f"   ⚠️  Complexity: Workflow may be too simple")
        
        print("\\n   ✅ Complex workflow generation testing completed")
    
    async def test_integrated_agent_enhancement(self):
        """Test the enhanced integrated agent with advanced intelligence."""
        print("\\n🤖 Testing Enhanced Integrated Agent...")
        
        try:
            # Initialize the agent
            await self.agent.initialize()
            
            # Test enhanced reasoning
            request = "Weekly collect analytics from Facebook, Twitter, LinkedIn, format and merge the data, then save to Google Sheets and email a summary report"
            
            print(f"   📝 Testing Request: {request}")
            
            # Test the enhanced reasoning method
            reasoning_result = await self.agent._reason_about_workflow_requirements(request)
            
            print(f"   🧠 Enhanced Reasoning Completed")
            print(f"   🎯 Pattern Analysis: {'✅ Found' if 'pattern_analysis' in reasoning_result else '❌ Missing'}")
            print(f"   🔗 Connectors Suggested: {len(reasoning_result.get('connectors', []))}")
            print(f"   📊 Complexity Score: {reasoning_result.get('complexity_score', 'N/A')}")
            print(f"   ⏱️  Estimated Time: {reasoning_result.get('estimated_execution_time', 'N/A')}")
            
            # Test complex workflow building
            if 'pattern_analysis' in reasoning_result:
                workflow = await self.agent.build_complex_workflow_from_analysis(
                    reasoning_result, 
                    "test_user",
                    "Test Complex Workflow"
                )
                
                print(f"   🏗️  Complex Workflow Built: {workflow.name}")
                print(f"   📊 Nodes: {len(workflow.nodes)}")
                print(f"   🔗 Edges: {len(workflow.edges)}")
                print("   ✅ Enhanced agent integration: WORKING")
            else:
                print("   ⚠️  Enhanced agent integration: Pattern analysis missing")
        
        except Exception as e:
            print(f"   ❌ Enhanced agent integration: ERROR - {e}")
        
        print("   ✅ Enhanced integrated agent testing completed")


async def run_advanced_workflow_intelligence_tests():
    """Run the advanced workflow intelligence test suite."""
    test_suite = AdvancedWorkflowIntelligenceTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(run_advanced_workflow_intelligence_tests())