"""
Advanced Workflow Intelligence for Complex n8n-Style Workflows

This module enhances our AI agent's ability to build sophisticated workflows
with patterns like fan-out/fan-in, conditional branching, and data merging.
"""
import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, NodePosition

logger = logging.getLogger(__name__)


class WorkflowPattern(Enum):
    """Complex workflow patterns that can be detected and generated."""
    LINEAR = "linear"                    # A → B → C
    SIMPLE_PARALLEL = "simple_parallel"  # A → [B, C] → D
    FAN_OUT_FAN_IN = "fan_out_fan_in"   # A → [B, C, D] → [E, F, G] → H
    CONDITIONAL_BRANCH = "conditional"   # A → B → {C or D} → E
    SCHEDULED_PIPELINE = "scheduled"     # Schedule → A → B → C
    MULTI_SOURCE_MERGE = "multi_merge"   # [A, B, C] → Transform → Merge → Output
    DATA_PIPELINE = "data_pipeline"      # Extract → Transform → Load pattern


@dataclass
class WorkflowPatternAnalysis:
    """Analysis result of workflow pattern detection."""
    primary_pattern: WorkflowPattern
    complexity_score: float
    estimated_nodes: int
    parallel_branches: int
    merge_points: int
    data_transformations: int
    suggested_connectors: List[str]
    reasoning: str


@dataclass
class ConnectorGroup:
    """Group of related connectors that work well together."""
    name: str
    connectors: List[str]
    common_use_cases: List[str]
    data_formats: List[str]


class AdvancedWorkflowIntelligence:
    """
    Enhanced workflow intelligence for building complex n8n-style workflows.
    
    Capabilities:
    - Pattern recognition for complex workflows
    - Intelligent connector grouping and selection
    - Data flow optimization
    - Merge strategy planning
    """
    
    def __init__(self):
        self.connector_groups = {}  # Will be populated dynamically
        self.workflow_templates = self._initialize_workflow_templates()
        self._connector_registry_cache = None
        
    async def _get_dynamic_connector_groups(self) -> Dict[str, ConnectorGroup]:
        """Get connector groups dynamically from the actual connector registry."""
        try:
            from app.connectors.registry import connector_registry
            from app.services.tool_registry import ToolRegistry
            
            # Get all available connectors
            tool_registry = ToolRegistry()
            await tool_registry.initialize()
            tools_metadata = await tool_registry.get_tool_metadata()
            
            # Group connectors by category dynamically
            groups = {}
            category_mapping = {}
            
            for tool in tools_metadata:
                category = tool.get("category", "other").lower()
                connector_name = tool.get("name", "unknown")
                description = tool.get("description", "")
                
                # Create category group if it doesn't exist
                if category not in category_mapping:
                    category_mapping[category] = {
                        'connectors': [],
                        'use_cases': set(),
                        'data_formats': set()
                    }
                
                category_mapping[category]['connectors'].append(connector_name)
                
                # Extract use cases from description
                if description:
                    desc_lower = description.lower()
                    if any(word in desc_lower for word in ['analytics', 'data', 'metrics']):
                        category_mapping[category]['use_cases'].add('data analysis')
                    if any(word in desc_lower for word in ['send', 'notify', 'email']):
                        category_mapping[category]['use_cases'].add('notifications')
                    if any(word in desc_lower for word in ['search', 'find', 'get']):
                        category_mapping[category]['use_cases'].add('data retrieval')
                    if any(word in desc_lower for word in ['save', 'store', 'write']):
                        category_mapping[category]['use_cases'].add('data storage')
                
                # Infer data formats
                category_mapping[category]['data_formats'].update(['json', 'text'])  # Common formats
            
            # Convert to ConnectorGroup objects
            for category, data in category_mapping.items():
                group_name = category.replace('_', ' ').title()
                groups[category] = ConnectorGroup(
                    name=group_name,
                    connectors=data['connectors'],
                    common_use_cases=list(data['use_cases']) or ['general purpose'],
                    data_formats=list(data['data_formats']) or ['json']
                )
            
            return groups
            
        except Exception as e:
            logger.warning(f"Could not get dynamic connector groups: {e}")
            # Return empty groups - system will work without them
            return {}
    
    def _initialize_workflow_templates(self) -> Dict[WorkflowPattern, Dict[str, Any]]:
        """Initialize workflow templates for different patterns."""
        return {
            WorkflowPattern.FAN_OUT_FAN_IN: {
                'description': 'Multiple parallel processes that merge results',
                'min_nodes': 5,
                'typical_structure': 'trigger → [sources] → [processors] → merge → output',
                'use_cases': ['multi-source analytics', 'data aggregation', 'parallel processing']
            },
            WorkflowPattern.MULTI_SOURCE_MERGE: {
                'description': 'Collect from multiple sources and merge',
                'min_nodes': 4,
                'typical_structure': '[sources] → [transform] → merge → [outputs]',
                'use_cases': ['social media analytics', 'multi-platform reporting', 'data consolidation']
            },
            WorkflowPattern.SCHEDULED_PIPELINE: {
                'description': 'Time-triggered workflow execution',
                'min_nodes': 3,
                'typical_structure': 'schedule → process → output',
                'use_cases': ['daily reports', 'weekly analytics', 'automated monitoring']
            }
        }
    
    async def analyze_workflow_complexity(self, user_request: str) -> WorkflowPatternAnalysis:
        """
        Analyze user request to determine workflow complexity and pattern.
        
        Args:
            user_request: Natural language description of desired workflow
            
        Returns:
            WorkflowPatternAnalysis with detected pattern and recommendations
        """
        request_lower = user_request.lower()
        
        # Detect workflow patterns
        pattern_scores = {
            WorkflowPattern.FAN_OUT_FAN_IN: self._score_fan_out_fan_in(request_lower),
            WorkflowPattern.MULTI_SOURCE_MERGE: self._score_multi_source_merge(request_lower),
            WorkflowPattern.SCHEDULED_PIPELINE: self._score_scheduled_pipeline(request_lower),
            WorkflowPattern.CONDITIONAL_BRANCH: self._score_conditional_branch(request_lower),
            WorkflowPattern.DATA_PIPELINE: self._score_data_pipeline(request_lower),
            WorkflowPattern.SIMPLE_PARALLEL: self._score_simple_parallel(request_lower),
            WorkflowPattern.LINEAR: self._score_linear(request_lower)
        }
        
        # Select highest scoring pattern
        primary_pattern = max(pattern_scores.keys(), key=lambda k: pattern_scores[k])
        complexity_score = pattern_scores[primary_pattern]
        
        # Analyze specific aspects
        parallel_branches = self._count_parallel_branches(request_lower)
        merge_points = self._count_merge_points(request_lower)
        data_transformations = self._count_transformations(request_lower)
        estimated_nodes = self._estimate_node_count(request_lower, primary_pattern)
        
        # Suggest connectors
        suggested_connectors = await self._suggest_connectors(request_lower, primary_pattern)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            primary_pattern, complexity_score, parallel_branches, 
            merge_points, suggested_connectors
        )
        
        return WorkflowPatternAnalysis(
            primary_pattern=primary_pattern,
            complexity_score=complexity_score,
            estimated_nodes=estimated_nodes,
            parallel_branches=parallel_branches,
            merge_points=merge_points,
            data_transformations=data_transformations,
            suggested_connectors=suggested_connectors,
            reasoning=reasoning
        )
    
    def _score_fan_out_fan_in(self, request: str) -> float:
        """Score likelihood of fan-out/fan-in pattern."""
        score = 0.0
        
        # Multiple sources indicators
        multi_source_indicators = [
            'multiple', 'all platforms', 'various', 'different apis',
            'several services', 'from facebook, twitter', 'social media platforms'
        ]
        for indicator in multi_source_indicators:
            if indicator in request:
                score += 0.3
        
        # Merge/combine indicators
        merge_indicators = [
            'combine', 'merge', 'aggregate', 'consolidate', 
            'bring together', 'collect all'
        ]
        for indicator in merge_indicators:
            if indicator in request:
                score += 0.4
        
        # Multiple outputs
        multi_output_indicators = [
            'and email', 'save to sheets', 'both email and',
            'send report and save'
        ]
        for indicator in multi_output_indicators:
            if indicator in request:
                score += 0.2
        
        return min(score, 1.0)
    
    def _score_multi_source_merge(self, request: str) -> float:
        """Score likelihood of multi-source merge pattern."""
        score = 0.0
        
        # Count social media platforms mentioned
        platforms = ['facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'tiktok']
        platform_count = sum(1 for platform in platforms if platform in request)
        if platform_count >= 2:
            score += 0.5
        if platform_count >= 3:
            score += 0.3
        
        # Analytics/data collection indicators
        analytics_indicators = ['analytics', 'metrics', 'data', 'stats', 'performance']
        for indicator in analytics_indicators:
            if indicator in request:
                score += 0.1
        
        # Merge indicators
        if any(word in request for word in ['merge', 'combine', 'consolidate']):
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_scheduled_pipeline(self, request: str) -> float:
        """Score likelihood of scheduled pipeline pattern."""
        score = 0.0
        
        # Time-based indicators
        schedule_indicators = [
            'daily', 'weekly', 'monthly', 'every day', 'every week',
            'schedule', 'automated', 'regularly', 'periodically'
        ]
        for indicator in schedule_indicators:
            if indicator in request:
                score += 0.4
        
        # Report generation indicators
        report_indicators = ['report', 'summary', 'digest', 'update']
        for indicator in report_indicators:
            if indicator in request:
                score += 0.2
        
        return min(score, 1.0)
    
    def _score_conditional_branch(self, request: str) -> float:
        """Score likelihood of conditional branching pattern."""
        score = 0.0
        
        # Conditional indicators
        conditional_indicators = [
            'if', 'when', 'depending on', 'based on', 'condition',
            'only if', 'unless', 'in case'
        ]
        for indicator in conditional_indicators:
            if indicator in request:
                score += 0.4
        
        return min(score, 1.0)
    
    def _score_data_pipeline(self, request: str) -> float:
        """Score likelihood of data pipeline pattern."""
        score = 0.0
        
        # ETL indicators
        etl_indicators = [
            'extract', 'transform', 'load', 'process', 'clean',
            'format', 'convert', 'parse'
        ]
        for indicator in etl_indicators:
            if indicator in request:
                score += 0.3
        
        return min(score, 1.0)
    
    def _score_simple_parallel(self, request: str) -> float:
        """Score likelihood of simple parallel pattern."""
        score = 0.0
        
        # Simple parallel indicators (2 outputs)
        if 'and' in request and ('email' in request or 'save' in request):
            score += 0.5
        
        # Two distinct actions
        action_count = sum(1 for action in ['email', 'save', 'send', 'store', 'notify'] if action in request)
        if action_count == 2:
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_linear(self, request: str) -> float:
        """Score likelihood of linear pattern (fallback)."""
        # Linear is the default/fallback pattern
        return 0.1
    
    def _count_parallel_branches(self, request: str) -> int:
        """Count potential parallel branches in the request."""
        # Count social media platforms
        platforms = ['facebook', 'twitter', 'linkedin', 'instagram', 'youtube']
        platform_count = sum(1 for platform in platforms if platform in request)
        
        # Count output destinations
        outputs = ['email', 'sheets', 'slack', 'save', 'store', 'notify']
        output_count = sum(1 for output in outputs if output in request)
        
        return max(platform_count, output_count, 1)
    
    def _count_merge_points(self, request: str) -> int:
        """Count potential merge points in the request."""
        merge_indicators = ['combine', 'merge', 'aggregate', 'consolidate']
        return sum(1 for indicator in merge_indicators if indicator in request)
    
    def _count_transformations(self, request: str) -> int:
        """Count potential data transformations."""
        transform_indicators = ['format', 'transform', 'convert', 'process', 'clean', 'summarize']
        return sum(1 for indicator in transform_indicators if indicator in request)
    
    def _estimate_node_count(self, request: str, pattern: WorkflowPattern) -> int:
        """Estimate number of nodes needed for the workflow."""
        base_counts = {
            WorkflowPattern.LINEAR: 3,
            WorkflowPattern.SIMPLE_PARALLEL: 4,
            WorkflowPattern.FAN_OUT_FAN_IN: 7,
            WorkflowPattern.MULTI_SOURCE_MERGE: 6,
            WorkflowPattern.SCHEDULED_PIPELINE: 4,
            WorkflowPattern.CONDITIONAL_BRANCH: 5,
            WorkflowPattern.DATA_PIPELINE: 5
        }
        
        base_count = base_counts.get(pattern, 3)
        
        # Adjust based on complexity indicators
        platforms = ['facebook', 'twitter', 'linkedin', 'instagram']
        platform_count = sum(1 for platform in platforms if platform in request)
        
        outputs = ['email', 'sheets', 'slack', 'save']
        output_count = sum(1 for output in outputs if output in request)
        
        # Add nodes for each additional platform/output
        additional_nodes = max(0, platform_count - 1) + max(0, output_count - 1)
        
        return base_count + additional_nodes
    
    async def _suggest_connectors(self, request: str, pattern: WorkflowPattern) -> List[str]:
        """Suggest appropriate connectors based on request and pattern dynamically."""
        suggested = []
        
        try:
            # Get dynamic connector groups
            connector_groups = await self._get_dynamic_connector_groups()
            
            # Get all available connectors from tool registry
            from app.services.tool_registry import ToolRegistry
            tool_registry = ToolRegistry()
            await tool_registry.initialize()
            tools_metadata = await tool_registry.get_tool_metadata()
            
            # Score connectors based on relevance to request
            connector_scores = {}
            
            for tool in tools_metadata:
                connector_name = tool.get("name", "")
                description = tool.get("description", "").lower()
                category = tool.get("category", "").lower()
                
                score = 0.0
                
                # Direct name matching
                connector_keywords = connector_name.replace('_', ' ').split()
                for keyword in connector_keywords:
                    if keyword.lower() in request.lower():
                        score += 0.5
                
                # Description matching
                request_words = request.lower().split()
                for word in request_words:
                    if word in description:
                        score += 0.3
                
                # Category relevance
                if any(word in request.lower() for word in [
                    'email', 'send', 'notify'
                ]) and category == 'communication':
                    score += 0.4
                elif any(word in request.lower() for word in [
                    'search', 'find', 'get', 'fetch'
                ]) and category in ['data_sources', 'apis']:
                    score += 0.4
                elif any(word in request.lower() for word in [
                    'save', 'store', 'sheet', 'database'
                ]) and category in ['productivity', 'data_sources']:
                    score += 0.4
                elif any(word in request.lower() for word in [
                    'schedule', 'weekly', 'daily', 'trigger'
                ]) and category == 'triggers':
                    score += 0.4
                
                # Pattern-specific scoring
                if pattern == WorkflowPattern.MULTI_SOURCE_MERGE:
                    if any(word in connector_name.lower() for word in ['analytics', 'api', 'data']):
                        score += 0.3
                elif pattern == WorkflowPattern.SCHEDULED_PIPELINE:
                    if any(word in connector_name.lower() for word in ['schedule', 'trigger', 'webhook']):
                        score += 0.5
                
                if score > 0:
                    connector_scores[connector_name] = score
            
            # Sort by score and get top suggestions
            sorted_connectors = sorted(connector_scores.items(), key=lambda x: x[1], reverse=True)
            suggested = [name for name, score in sorted_connectors[:8]]
            
            # Add pattern-specific virtual connectors if needed
            if pattern in [WorkflowPattern.FAN_OUT_FAN_IN, WorkflowPattern.MULTI_SOURCE_MERGE]:
                # Look for actual merge/transform connectors instead of hardcoded ones
                merge_connectors = [name for name, _ in sorted_connectors 
                                  if any(word in name.lower() for word in ['merge', 'combine', 'transform'])]
                if merge_connectors and merge_connectors[0] not in suggested:
                    suggested.append(merge_connectors[0])
            
            if pattern == WorkflowPattern.SCHEDULED_PIPELINE:
                # Look for actual scheduler/trigger connectors
                trigger_connectors = [name for name, _ in sorted_connectors 
                                    if any(word in name.lower() for word in ['schedule', 'trigger', 'webhook'])]
                if trigger_connectors and trigger_connectors[0] not in suggested:
                    suggested.insert(0, trigger_connectors[0])
            
            return suggested[:8]  # Limit to top 8 suggestions
            
        except Exception as e:
            logger.warning(f"Error in dynamic connector suggestion: {e}")
            # Fallback to simple keyword matching
            return self._fallback_connector_suggestion(request, pattern)
    
    def _fallback_connector_suggestion(self, request: str, pattern: WorkflowPattern) -> List[str]:
        """Fallback connector suggestion when dynamic method fails."""
        suggested = []
        
        # Simple keyword-based suggestions
        request_lower = request.lower()
        
        if 'email' in request_lower or 'gmail' in request_lower:
            suggested.append('gmail_connector')
        if 'sheets' in request_lower or 'spreadsheet' in request_lower:
            suggested.append('google_sheets')
        if 'search' in request_lower:
            suggested.append('perplexity_search')
        if 'slack' in request_lower:
            suggested.append('slack')
        if 'webhook' in request_lower:
            suggested.append('webhook')
        if 'http' in request_lower or 'api' in request_lower:
            suggested.append('http_request')
        
        return suggested[:5]
    
    def _generate_reasoning(self, pattern: WorkflowPattern, score: float, 
                          branches: int, merges: int, connectors: List[str]) -> str:
        """Generate human-readable reasoning for the analysis."""
        reasoning_parts = []
        
        # Pattern explanation
        pattern_descriptions = {
            WorkflowPattern.FAN_OUT_FAN_IN: f"Detected fan-out/fan-in pattern with {branches} parallel branches and {merges} merge points",
            WorkflowPattern.MULTI_SOURCE_MERGE: f"Detected multi-source merge pattern with {branches} data sources",
            WorkflowPattern.SCHEDULED_PIPELINE: "Detected scheduled pipeline pattern for automated execution",
            WorkflowPattern.SIMPLE_PARALLEL: f"Detected simple parallel pattern with {branches} parallel outputs",
            WorkflowPattern.LINEAR: "Detected linear workflow pattern"
        }
        
        reasoning_parts.append(pattern_descriptions.get(pattern, f"Detected {pattern.value} pattern"))
        
        # Confidence explanation
        if score > 0.7:
            reasoning_parts.append("High confidence based on clear pattern indicators")
        elif score > 0.4:
            reasoning_parts.append("Medium confidence based on partial pattern match")
        else:
            reasoning_parts.append("Low confidence, using fallback pattern")
        
        # Connector reasoning
        if connectors:
            reasoning_parts.append(f"Suggested connectors: {', '.join(connectors[:3])}{'...' if len(connectors) > 3 else ''}")
        
        return ". ".join(reasoning_parts) + "."
    
    async def generate_complex_workflow(self, analysis: WorkflowPatternAnalysis, 
                                      user_request: str) -> WorkflowPlan:
        """
        Generate a complex workflow based on pattern analysis.
        
        Args:
            analysis: Result from analyze_workflow_complexity
            user_request: Original user request
            
        Returns:
            WorkflowPlan with complex structure
        """
        if analysis.primary_pattern == WorkflowPattern.MULTI_SOURCE_MERGE:
            return await self._generate_multi_source_merge_workflow(analysis, user_request)
        elif analysis.primary_pattern == WorkflowPattern.FAN_OUT_FAN_IN:
            return await self._generate_fan_out_fan_in_workflow(analysis, user_request)
        elif analysis.primary_pattern == WorkflowPattern.SCHEDULED_PIPELINE:
            return await self._generate_scheduled_pipeline_workflow(analysis, user_request)
        else:
            # Fallback to simpler workflow generation
            return await self._generate_simple_workflow(analysis, user_request)
    
    async def _generate_multi_source_merge_workflow(self, analysis: WorkflowPatternAnalysis, 
                                                   request: str) -> WorkflowPlan:
        """Generate multi-source merge workflow dynamically based on available connectors."""
        nodes = []
        edges = []
        
        try:
            # Get available connectors dynamically
            from app.services.tool_registry import ToolRegistry
            tool_registry = ToolRegistry()
            await tool_registry.initialize()
            tools_metadata = await tool_registry.get_tool_metadata()
            
            # Categorize available connectors
            data_sources = []
            processors = []
            outputs = []
            
            for tool in tools_metadata:
                connector_name = tool.get("name", "")
                category = tool.get("category", "").lower()
                description = tool.get("description", "").lower()
                
                # Determine if this connector is relevant to the request
                request_lower = request.lower()
                is_relevant = False
                
                # Check if connector name or description matches request keywords
                connector_keywords = connector_name.replace('_', ' ').split()
                for keyword in connector_keywords:
                    if keyword.lower() in request_lower:
                        is_relevant = True
                        break
                
                if not is_relevant:
                    for word in request_lower.split():
                        if word in description:
                            is_relevant = True
                            break
                
                if is_relevant:
                    # Categorize the connector
                    if category in ['data_sources', 'apis'] or any(word in description for word in ['get', 'fetch', 'search', 'analytics']):
                        data_sources.append(connector_name)
                    elif category in ['ai_services'] or any(word in description for word in ['transform', 'process', 'format']):
                        processors.append(connector_name)
                    elif category in ['communication', 'productivity'] or any(word in description for word in ['send', 'save', 'store']):
                        outputs.append(connector_name)
            
            # Use suggested connectors as fallback
            if not data_sources:
                data_sources = [c for c in analysis.suggested_connectors if any(word in c.lower() for word in ['search', 'get', 'api', 'analytics'])]
            if not processors:
                processors = [c for c in analysis.suggested_connectors if any(word in c.lower() for word in ['transform', 'process', 'format'])]
            if not outputs:
                outputs = [c for c in analysis.suggested_connectors if any(word in c.lower() for word in ['email', 'save', 'sheet', 'store'])]
            
            # Ensure we have at least some connectors
            if not data_sources:
                data_sources = ['http_request']  # Generic fallback
            if not processors:
                processors = ['text_summarizer']  # Generic fallback
            if not outputs:
                outputs = ['gmail_connector']  # Generic fallback
            
            # Create source nodes (parallel data collection)
            source_nodes = []
            for i, connector_name in enumerate(data_sources[:analysis.parallel_branches]):
                node = WorkflowNode(
                    id=f"source_{i}",
                    connector_name=connector_name,
                    parameters=await self._generate_dynamic_parameters(connector_name, "source", request),
                    position=NodePosition(x=100, y=100 + i * 120)
                )
                nodes.append(node)
                source_nodes.append(node)
            
            # Create processing nodes (parallel data processing)
            process_nodes = []
            for i, source_node in enumerate(source_nodes):
                processor_name = processors[i % len(processors)]  # Cycle through available processors
                node = WorkflowNode(
                    id=f"process_{i}",
                    connector_name=processor_name,
                    parameters=await self._generate_dynamic_parameters(processor_name, "processor", request, source_node.id),
                    position=NodePosition(x=300, y=100 + i * 120)
                )
                nodes.append(node)
                process_nodes.append(node)
                
                # Connect source to processor
                edges.append(WorkflowEdge(
                    id=f"edge_source_{i}",
                    source=source_node.id,
                    target=node.id
                ))
            
            # Create merge node if we have multiple sources
            if len(process_nodes) > 1:
                merge_connector = next((c for c in analysis.suggested_connectors if 'merge' in c.lower()), 
                                     processors[0])  # Use first processor as merge fallback
                
                merge_node = WorkflowNode(
                    id="merge_data",
                    connector_name=merge_connector,
                    parameters=await self._generate_dynamic_parameters(merge_connector, "merge", request),
                    position=NodePosition(x=500, y=100 + len(process_nodes) * 60)
                )
                nodes.append(merge_node)
                
                # Connect all processors to merge
                for process_node in process_nodes:
                    edges.append(WorkflowEdge(
                        id=f"edge_merge_{process_node.id}",
                        source=process_node.id,
                        target="merge_data"
                    ))
                
                last_node_id = "merge_data"
            else:
                last_node_id = process_nodes[0].id if process_nodes else source_nodes[0].id
            
            # Create output nodes (parallel outputs)
            output_y = 100 + len(process_nodes) * 60
            for i, output_connector in enumerate(outputs[:2]):  # Limit to 2 outputs
                node = WorkflowNode(
                    id=f"output_{i}",
                    connector_name=output_connector,
                    parameters=await self._generate_dynamic_parameters(output_connector, "output", request),
                    position=NodePosition(x=700, y=output_y + i * 80 - 40)
                )
                nodes.append(node)
                
                # Connect to last processing node
                edges.append(WorkflowEdge(
                    id=f"edge_output_{i}",
                    source=last_node_id,
                    target=node.id
                ))
            
            return WorkflowPlan(
                id=str(uuid4()),
                user_id="system",
                name="Dynamic Multi-Source Workflow",
                description=f"Dynamically generated workflow with {len(data_sources)} sources, processing, and {len(outputs)} outputs",
                nodes=nodes,
                edges=edges
            )
            
        except Exception as e:
            logger.error(f"Error generating dynamic multi-source workflow: {e}")
            return await self._generate_simple_workflow(analysis, request)
    
    async def _generate_dynamic_parameters(self, connector_name: str, role: str, request: str, source_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate parameters dynamically based on connector and role."""
        try:
            # Get connector metadata
            from app.services.tool_registry import ToolRegistry
            tool_registry = ToolRegistry()
            await tool_registry.initialize()
            tools_metadata = await tool_registry.get_tool_metadata()
            
            connector_metadata = next(
                (tool for tool in tools_metadata if tool.get("name") == connector_name),
                None
            )
            
            parameters = {}
            
            if connector_metadata and "parameters" in connector_metadata:
                # Use actual connector parameters
                param_schema = connector_metadata["parameters"]
                if isinstance(param_schema, dict):
                    for param_name, param_info in param_schema.items():
                        # Generate appropriate values based on role and request
                        if role == "source":
                            if param_name in ["query", "search", "term"]:
                                parameters[param_name] = self._extract_search_term(request)
                            elif param_name in ["limit", "count", "max_results"]:
                                parameters[param_name] = 10
                        elif role == "processor":
                            if param_name in ["input", "data", "text"]:
                                parameters[param_name] = f"{{{source_id}.result}}" if source_id else "{input}"
                            elif param_name in ["format", "output_format"]:
                                parameters[param_name] = "json"
                        elif role == "output":
                            if param_name in ["to", "recipient", "email"]:
                                parameters[param_name] = "{user.email}"
                            elif param_name in ["subject", "title"]:
                                parameters[param_name] = "Workflow Results"
                            elif param_name in ["body", "content", "message"]:
                                parameters[param_name] = "{result}"
                            elif param_name in ["data", "content"]:
                                parameters[param_name] = "{result}"
            
            # Fallback generic parameters
            if not parameters:
                if role == "source":
                    parameters = {"query": self._extract_search_term(request)}
                elif role == "processor":
                    parameters = {"input": f"{{{source_id}.result}}" if source_id else "{input}"}
                elif role == "output":
                    parameters = {"data": "{result}"}
                elif role == "merge":
                    parameters = {"inputs": ["{result}"]}
            
            return parameters
            
        except Exception as e:
            logger.warning(f"Error generating dynamic parameters for {connector_name}: {e}")
            return {"input": "{result}"}
    
    def _extract_search_term(self, request: str) -> str:
        """Extract search term from user request."""
        # Simple extraction - can be enhanced with NLP
        request_lower = request.lower()
        
        # Look for quoted terms
        import re
        quoted_terms = re.findall(r'"([^"]*)"', request)
        if quoted_terms:
            return quoted_terms[0]
        
        # Look for common search patterns
        search_patterns = [
            r'search for (.+?)(?:\s+and|\s+then|$)',
            r'find (.+?)(?:\s+and|\s+then|$)',
            r'get (.+?)(?:\s+and|\s+then|$)',
            r'collect (.+?)(?:\s+and|\s+then|$)'
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, request_lower)
            if match:
                return match.group(1).strip()
        
        # Fallback to first few words
        words = request.split()[:3]
        return " ".join(words)
        
        # Create merge node
        merge_node = WorkflowNode(
            id="merge_data",
            connector_name="data_merger",
            parameters={
                "inputs": [f"{{format_{platform}.result}}" for platform, _ in platforms],
                "merge_strategy": "combine_arrays",
                "group_by": "date"
            },
            position=NodePosition(x=500, y=100 + len(platforms) * 60)
        )
        nodes.append(merge_node)
        
        # Create output nodes (parallel outputs)
        output_y = 100 + len(platforms) * 60
        
        # Google Sheets output
        if 'sheets' in request.lower() or 'spreadsheet' in request.lower():
            sheets_node = WorkflowNode(
                id="save_to_sheets",
                connector_name="google_sheets",
                parameters={
                    "spreadsheet_name": "Social Media Analytics",
                    "worksheet": "Weekly Report",
                    "data": "{merge_data.result}",
                    "append": True
                },
                position=NodePosition(x=700, y=output_y - 60)
            )
            nodes.append(sheets_node)
        
        # Email output
        if 'email' in request.lower() or 'report' in request.lower():
            email_node = WorkflowNode(
                id="send_email_report",
                connector_name="gmail",
                parameters={
                    "to": "{user.email}",
                    "subject": "Social Media Analytics Report",
                    "body": "Weekly social media report attached.\\n\\nSummary: {merge_data.summary}",
                    "attachment_data": "{merge_data.result}"
                },
                position=NodePosition(x=700, y=output_y + 60)
            )
            nodes.append(email_node)
        
        # Create edges
        # Source to format connections
        for platform, _ in platforms:
            edges.append(WorkflowEdge(
                id=f"edge_get_to_format_{platform}",
                source=f"get_{platform}",
                target=f"format_{platform}"
            ))
        
        # Format to merge connections
        for platform, _ in platforms:
            edges.append(WorkflowEdge(
                id=f"edge_format_to_merge_{platform}",
                source=f"format_{platform}",
                target="merge_data"
            ))
        
        # Merge to outputs
        for node in nodes:
            if node.id.startswith('save_') or node.id.startswith('send_'):
                edges.append(WorkflowEdge(
                    id=f"edge_merge_to_{node.id}",
                    source="merge_data",
                    target=node.id
                ))
        
        return WorkflowPlan(
            id=str(uuid4()),
            user_id="system",
            name="Multi-Source Analytics Workflow",
            description=f"Complex workflow with {len(platforms)} data sources, formatting, merging, and multiple outputs",
            nodes=nodes,
            edges=edges
        )
    
    async def _generate_fan_out_fan_in_workflow(self, analysis: WorkflowPatternAnalysis, 
                                              request: str) -> WorkflowPlan:
        """Generate fan-out/fan-in workflow pattern."""
        # Similar to multi-source but with more complex branching
        return await self._generate_multi_source_merge_workflow(analysis, request)
    
    async def _generate_scheduled_pipeline_workflow(self, analysis: WorkflowPatternAnalysis, 
                                                   request: str) -> WorkflowPlan:
        """Generate scheduled pipeline workflow."""
        nodes = []
        edges = []
        
        # Extract schedule from request
        schedule_params = {"schedule": "weekly"}  # Default
        if 'daily' in request.lower():
            schedule_params["schedule"] = "daily"
        elif 'monthly' in request.lower():
            schedule_params["schedule"] = "monthly"
        
        # Create trigger node
        trigger_node = WorkflowNode(
            id="schedule_trigger",
            connector_name="scheduler",
            parameters=schedule_params,
            position=NodePosition(x=50, y=200)
        )
        nodes.append(trigger_node)
        
        # Generate the rest of the workflow
        base_workflow = await self._generate_multi_source_merge_workflow(analysis, request)
        
        # Adjust positions and add trigger connections
        for node in base_workflow.nodes:
            node.position.x += 150  # Shift right to make room for trigger
            nodes.append(node)
        
        # Connect trigger to first nodes
        first_nodes = [node for node in base_workflow.nodes if node.id.startswith('get_')]
        for node in first_nodes:
            edges.append(WorkflowEdge(
                id=f"trigger_to_{node.id}",
                source="schedule_trigger",
                target=node.id
            ))
        
        # Add existing edges
        edges.extend(base_workflow.edges)
        
        return WorkflowPlan(
            id=str(uuid4()),
            user_id="system",
            name="Scheduled Analytics Pipeline",
            description=f"Scheduled workflow with {analysis.estimated_nodes} nodes",
            nodes=nodes,
            edges=edges
        )
    
    async def _generate_simple_workflow(self, analysis: WorkflowPatternAnalysis, 
                                       request: str) -> WorkflowPlan:
        """Generate simple workflow as fallback."""
        nodes = []
        edges = []
        
        # Create basic 3-node workflow
        search_node = WorkflowNode(
            id="search",
            connector_name="perplexity_search",
            parameters={"query": "AI news"},
            position=NodePosition(x=100, y=200)
        )
        
        process_node = WorkflowNode(
            id="process",
            connector_name="text_summarizer",
            parameters={"text": "{search.result}"},
            position=NodePosition(x=300, y=200)
        )
        
        output_node = WorkflowNode(
            id="output",
            connector_name="gmail",
            parameters={
                "to": "{user.email}",
                "subject": "AI News Summary",
                "body": "{process.result}"
            },
            position=NodePosition(x=500, y=200)
        )
        
        nodes = [search_node, process_node, output_node]
        edges = [
            WorkflowEdge(id="edge1", source="search", target="process"),
            WorkflowEdge(id="edge2", source="process", target="output")
        ]
        
        return WorkflowPlan(
            id=str(uuid4()),
            user_id="system",
            name="Simple Workflow",
            description="Basic linear workflow",
            nodes=nodes,
            edges=edges
        )


# Global instance for use across the application
advanced_workflow_intelligence = AdvancedWorkflowIntelligence()