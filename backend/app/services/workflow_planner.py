"""
Dynamic Workflow Planner Agent - Intelligent Tool Chaining

This module implements a truly dynamic planner agent that:
1. Leverages your existing unified workflow orchestrator and tool registry
2. Uses AI to analyze connector capabilities dynamically (no hardcoding)
3. Creates intelligent workflow sequences based on connector metadata
4. Integrates with your existing WorkflowGraph and execution systems
"""
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from openai import AsyncAzureOpenAI

from app.core.config import settings
from app.services.tool_registry import ToolRegistry, get_tool_registry
from app.services.unified_workflow_orchestrator import ConnectorIntelligence, WorkflowIntelligence
from app.connectors.registry import get_connector_registry
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge

logger = logging.getLogger(__name__)


class PlanState(Enum):
    """States in the planning state machine."""
    ANALYZING = "analyzing"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    MODIFYING = "modifying"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    """Represents a single step in a workflow plan."""
    id: str
    connector_name: str
    action_description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    expected_output: str = ""
    estimated_duration: float = 5.0


@dataclass
class WorkflowPlanSequence:
    """Represents a complete workflow plan sequence."""
    id: str
    user_request: str
    steps: List[PlanStep]
    state: PlanState = PlanState.ANALYZING
    created_at: datetime = field(default_factory=datetime.utcnow)
    user_id: str = ""
    approval_required: bool = True
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_sequence_description(self) -> str:
        """Get human-readable sequence description."""
        if not self.steps:
            return "No steps planned"
        
        sequence_parts = []
        for step in self.steps:
            sequence_parts.append(step.action_description)
        
        return " ➝ ".join(sequence_parts)
    
    def to_workflow_plan(self) -> WorkflowPlan:
        """Convert to WorkflowPlan for execution."""
        nodes = []
        edges = []
        
        for i, step in enumerate(self.steps):
            node = WorkflowNode(
                id=step.id,
                connector_name=step.connector_name,
                parameters=step.parameters,
                dependencies=step.dependencies
            )
            nodes.append(node)
            
            # Create edges based on dependencies
            for dep_id in step.dependencies:
                edge = WorkflowEdge(
                    id=f"{dep_id}-{step.id}",
                    source=dep_id,
                    target=step.id
                )
                edges.append(edge)
        
        return WorkflowPlan(
            id=self.id,
            user_id=self.user_id,
            nodes=nodes,
            edges=edges,
            created_at=self.created_at
        )


class WorkflowPlannerAgent:
    """
    Dynamic planner agent that leverages your existing architecture.
    
    Integrates with:
    - ConnectorIntelligence for dynamic connector analysis
    - WorkflowIntelligence for optimization
    - Tool Registry for connector discovery
    - Unified Workflow Orchestrator for execution
    """
    
    def __init__(self):
        self.tool_registry: Optional[ToolRegistry] = None
        self._client: Optional[AsyncAzureOpenAI] = None
        self.active_plans: Dict[str, WorkflowPlanSequence] = {}
        self.connector_intelligence: Optional[ConnectorIntelligence] = None
        self.workflow_intelligence: Optional[WorkflowIntelligence] = None
        self.connector_registry = None
        
    async def initialize(self, auth_context: Optional[Dict[str, str]] = None):
        """Initialize the planner agent with your existing systems."""
        # Initialize tool registry
        self.tool_registry = await get_tool_registry(auth_context)
        
        # Initialize connector intelligence from unified orchestrator
        self.connector_intelligence = ConnectorIntelligence()
        self.workflow_intelligence = WorkflowIntelligence(self.connector_intelligence)
        
        # Get connector registry
        self.connector_registry = get_connector_registry()
        
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self._client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            logger.info("Workflow Planner Agent initialized successfully")
        else:
            logger.warning("Azure OpenAI not configured, planner will use fallback logic")
    
    async def create_workflow_plan(self, user_request: str, user_id: str) -> WorkflowPlanSequence:
        """
        Create a comprehensive workflow plan from user request.
        
        Args:
            user_request: The user's natural language request
            user_id: User identifier
            
        Returns:
            WorkflowPlanSequence with planned steps
        """
        plan_id = str(uuid.uuid4())
        
        # Create initial plan
        plan = WorkflowPlanSequence(
            id=plan_id,
            user_request=user_request,
            steps=[],
            user_id=user_id,
            state=PlanState.ANALYZING
        )
        
        self.active_plans[plan_id] = plan
        
        try:
            # Step 1: Analyze user request
            logger.info(f"🔍 Analyzing user request: {user_request}")
            analysis = await self._analyze_user_request(user_request)
            
            # Step 2: Create step sequence
            logger.info("📋 Creating workflow step sequence")
            plan.state = PlanState.PLANNING
            steps = await self._create_step_sequence(analysis, user_request)
            plan.steps = steps
            
            # Step 3: Validate and optimize plan
            logger.info("✅ Validating and optimizing plan")
            await self._validate_and_optimize_plan(plan)
            
            # Step 4: Set to awaiting approval
            plan.state = PlanState.AWAITING_APPROVAL
            logger.info(f"📝 Plan created with {len(steps)} steps: {plan.get_sequence_description()}")
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create workflow plan: {e}")
            plan.state = PlanState.FAILED
            raise
    
    async def _analyze_user_request(self, user_request: str) -> Dict[str, Any]:
        """Dynamically analyze user request using connector intelligence."""
        
        # Get all available connectors dynamically
        connector_names = self.connector_registry.list_connectors()
        
        # Build dynamic connector analysis using ConnectorIntelligence
        connector_profiles = {}
        for connector_name in connector_names:
            try:
                profile = await self.connector_intelligence.analyze_connector(connector_name)
                connector_profiles[connector_name] = profile
            except Exception as e:
                logger.warning(f"Failed to analyze connector {connector_name}: {e}")
        
        # Create dynamic analysis prompt based on actual connector capabilities
        connector_descriptions = []
        for name, profile in connector_profiles.items():
            category = profile.get('category', 'unknown')
            description = f"- {name} ({category}): {profile.get('description', 'No description')}"
            connector_descriptions.append(description)
        
        analysis_prompt = f"""
        Analyze this user request to create an intelligent workflow plan.
        
        USER REQUEST: "{user_request}"
        
        AVAILABLE CONNECTORS (dynamically discovered):
        {chr(10).join(connector_descriptions)}
        
        Analyze the request and identify:
        1. What is the user trying to accomplish?
        2. Which connectors would be most suitable for each step?
        3. What is the logical sequence of operations?
        4. Are there any data transformations needed between steps?
        
        Consider connector categories:
        - data_sources: For retrieving/searching information
        - ai_services: For processing, analyzing, summarizing content
        - communication: For sending emails, notifications
        - productivity: For saving to documents, databases
        - utility: For custom processing, transformations
        
        Respond with JSON:
        {{
            "primary_goal": "Main objective of the workflow",
            "required_connectors": ["connector1", "connector2", "connector3"],
            "workflow_sequence": [
                {{"step": 1, "connector": "connector_name", "purpose": "what this step does"}},
                {{"step": 2, "connector": "connector_name", "purpose": "what this step does"}}
            ],
            "complexity": "simple|moderate|complex",
            "estimated_steps": 3
        }}
        """
        
        if self._client:
            try:
                response = await self._client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": "You are a workflow analysis expert. Use only the available connectors listed. Respond only with valid JSON."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content.strip()
                analysis_result = json.loads(content)
                
                # Validate that suggested connectors actually exist
                suggested_connectors = analysis_result.get('required_connectors', [])
                valid_connectors = [c for c in suggested_connectors if c in connector_names]
                analysis_result['required_connectors'] = valid_connectors
                
                logger.info(f"🧠 Dynamic AI Analysis Result: {analysis_result}")
                return analysis_result
                
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")
        
        # Fallback analysis using connector intelligence
        return await self._dynamic_fallback_analysis(user_request, connector_profiles)
    
    async def _dynamic_fallback_analysis(self, user_request: str, connector_profiles: Dict[str, Dict]) -> Dict[str, Any]:
        """Dynamic fallback analysis using connector intelligence."""
        request_lower = user_request.lower()
        
        # Dynamically categorize connectors based on their actual profiles
        data_connectors = []
        ai_connectors = []
        communication_connectors = []
        productivity_connectors = []
        utility_connectors = []
        
        for name, profile in connector_profiles.items():
            category = profile.get('category', 'unknown')
            if category == 'data_sources':
                data_connectors.append(name)
            elif category == 'ai_services':
                ai_connectors.append(name)
            elif category == 'communication':
                communication_connectors.append(name)
            elif category == 'productivity':
                productivity_connectors.append(name)
            elif category == 'utility':
                utility_connectors.append(name)
        
        # Build workflow sequence dynamically
        workflow_sequence = []
        step_num = 1
        
        # Step 1: Data acquisition
        if any(word in request_lower for word in ['search', 'find', 'get', 'lookup']):
            # Choose best data connector based on request content
            chosen_connector = None
            if 'youtube' in request_lower and 'youtube' in data_connectors:
                chosen_connector = 'youtube'
            elif any(word in request_lower for word in ['news', 'information', 'trends']) and 'perplexity_search' in data_connectors:
                chosen_connector = 'perplexity_search'
            elif data_connectors:
                chosen_connector = data_connectors[0]  # Default to first available
            
            if chosen_connector:
                workflow_sequence.append({
                    "step": step_num,
                    "connector": chosen_connector,
                    "purpose": f"Retrieve data using {chosen_connector}"
                })
                step_num += 1
        
        # Step 2: Processing
        if any(word in request_lower for word in ['summarize', 'analyze', 'process', 'combine']) and ai_connectors:
            chosen_connector = ai_connectors[0]  # Use first available AI service
            workflow_sequence.append({
                "step": step_num,
                "connector": chosen_connector,
                "purpose": f"Process data using {chosen_connector}"
            })
            step_num += 1
        
        # Step 3: Output/Communication
        if any(word in request_lower for word in ['email', 'send', 'notify']) and communication_connectors:
            chosen_connector = communication_connectors[0]
            workflow_sequence.append({
                "step": step_num,
                "connector": chosen_connector,
                "purpose": f"Send results using {chosen_connector}"
            })
            step_num += 1
        elif any(word in request_lower for word in ['save', 'store', 'notion', 'sheets']) and productivity_connectors:
            chosen_connector = productivity_connectors[0]
            workflow_sequence.append({
                "step": step_num,
                "connector": chosen_connector,
                "purpose": f"Save results using {chosen_connector}"
            })
            step_num += 1
        
        required_connectors = [step["connector"] for step in workflow_sequence]
        
        return {
            "primary_goal": f"Dynamic workflow: {user_request[:100]}...",
            "required_connectors": required_connectors,
            "workflow_sequence": workflow_sequence,
            "complexity": "complex" if len(workflow_sequence) > 2 else "moderate",
            "estimated_steps": len(workflow_sequence)
        }
    
    async def _create_step_sequence(self, analysis: Dict[str, Any], user_request: str) -> List[PlanStep]:
        """Create step sequence using dynamic connector intelligence."""
        
        steps = []
        workflow_sequence = analysis.get('workflow_sequence', [])
        
        if not workflow_sequence:
            # Check if the analysis explicitly indicates no workflow is needed
            estimated_steps = analysis.get('estimated_steps', 0)
            primary_goal = analysis.get('primary_goal', '').lower()
            
            # Don't create fallback steps for greetings or when analysis shows 0 steps
            if (estimated_steps == 0 or 
                'greeting' in primary_goal or 
                'no actionable workflow' in primary_goal or
                'no workflow' in primary_goal):
                logger.info("🚫 Analysis indicates no workflow needed - returning empty steps")
                return steps
            
            # Only create fallback for unclear but potentially actionable requests
            connector_names = self.connector_registry.list_connectors()
            if connector_names:
                step = PlanStep(
                    id="step-1",
                    connector_name=connector_names[0],
                    action_description=f"Process request using {connector_names[0]}",
                    parameters=await self._generate_dynamic_parameters(connector_names[0], user_request),
                    dependencies=[],
                    expected_output="Processed results",
                    estimated_duration=5.0
                )
                steps.append(step)
            return steps
        
        # Create steps based on AI-analyzed workflow sequence
        for seq_step in workflow_sequence:
            connector_name = seq_step.get('connector')
            step_num = seq_step.get('step', len(steps) + 1)
            purpose = seq_step.get('purpose', f'Process using {connector_name}')
            
            # Validate connector exists
            if connector_name not in self.connector_registry.list_connectors():
                logger.warning(f"Connector {connector_name} not found, skipping step")
                continue
            
            # Determine dependencies (steps depend on previous steps)
            dependencies = []
            if step_num > 1:
                dependencies = [f"step-{step_num - 1}"]
            
            step = PlanStep(
                id=f"step-{step_num}",
                connector_name=connector_name,
                action_description=purpose,
                parameters=await self._generate_dynamic_parameters(connector_name, user_request),
                dependencies=dependencies,
                expected_output=f"Output from {connector_name}",
                estimated_duration=await self._estimate_connector_duration(connector_name)
            )
            steps.append(step)
        
        return steps
    
    async def _generate_dynamic_parameters(self, connector_name: str, user_request: str) -> Dict[str, Any]:
        """Generate parameters dynamically using connector intelligence."""
        try:
            # Get connector profile from intelligence system
            profile = await self.connector_intelligence.analyze_connector(connector_name)
            
            # Use connector's input schema if available
            input_schema = profile.get('input_schema', {})
            if input_schema:
                # Generate parameters based on schema
                parameters = {}
                for param_name, param_info in input_schema.items():
                    if param_name == 'query' or 'query' in param_name.lower():
                        parameters[param_name] = user_request
                    elif param_name == 'text' or 'text' in param_name.lower():
                        parameters[param_name] = "{previous_step.result}"
                    elif param_name == 'input' or 'input' in param_name.lower():
                        parameters[param_name] = "{previous_step.result}"
                    else:
                        # Use default value if available
                        parameters[param_name] = param_info.get('default', '')
                
                return parameters
            
            # Fallback: generate based on connector category
            category = profile.get('category', 'unknown')
            
            if category == 'data_sources':
                return {"query": user_request}
            elif category == 'ai_services':
                return {"text": "{previous_step.result}"}
            elif category == 'communication':
                return {
                    "subject": f"Workflow Result: {user_request[:50]}",
                    "content": "{previous_step.result}"
                }
            elif category == 'productivity':
                return {
                    "title": f"Workflow Result: {user_request[:50]}",
                    "content": "{previous_step.result}"
                }
            else:
                return {"input": "{previous_step.result}"}
                
        except Exception as e:
            logger.warning(f"Failed to generate dynamic parameters for {connector_name}: {e}")
            return {"input": user_request}
    
    async def _estimate_connector_duration(self, connector_name: str) -> float:
        """Estimate execution duration using connector intelligence."""
        try:
            profile = await self.connector_intelligence.analyze_connector(connector_name)
            return profile.get('avg_execution_time', 5.0)
        except Exception as e:
            logger.warning(f"Failed to estimate duration for {connector_name}: {e}")
            return 5.0
    
    async def _validate_and_optimize_plan(self, plan: WorkflowPlanSequence):
        """Validate and optimize the workflow plan."""
        
        # Check for missing dependencies
        step_ids = {step.id for step in plan.steps}
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    logger.warning(f"Step {step.id} has invalid dependency: {dep_id}")
        
        # Optimize parameter references
        for i, step in enumerate(plan.steps):
            if i > 0 and not step.dependencies:
                # Add dependency on previous step if none specified
                step.dependencies = [plan.steps[i-1].id]
        
        # Estimate total duration
        total_duration = sum(step.estimated_duration for step in plan.steps)
        logger.info(f"Plan estimated duration: {total_duration:.1f} seconds")
    
    async def get_plan_for_approval(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get plan formatted for user approval."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return None
        
        return {
            "plan_id": plan_id,
            "user_request": plan.user_request,
            "sequence_description": plan.get_sequence_description(),
            "steps": [
                {
                    "step_number": i + 1,
                    "action": step.action_description,
                    "connector": step.connector_name,
                    "dependencies": step.dependencies,
                    "estimated_duration": step.estimated_duration
                }
                for i, step in enumerate(plan.steps)
            ],
            "total_steps": len(plan.steps),
            "estimated_duration": sum(step.estimated_duration for step in plan.steps),
            "state": plan.state.value
        }
    
    async def approve_plan(self, plan_id: str) -> bool:
        """Approve a plan for execution."""
        plan = self.active_plans.get(plan_id)
        if not plan or plan.state != PlanState.AWAITING_APPROVAL:
            return False
        
        plan.state = PlanState.APPROVED
        logger.info(f"Plan {plan_id} approved for execution")
        return True
    
    async def modify_plan(self, plan_id: str, modifications: Dict[str, Any]) -> bool:
        """Modify a plan based on user feedback."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return False
        
        plan.state = PlanState.MODIFYING
        plan.modifications.append({
            "timestamp": datetime.utcnow().isoformat(),
            "modifications": modifications
        })
        
        # Apply modifications (simplified implementation)
        if "remove_step" in modifications:
            step_to_remove = modifications["remove_step"]
            plan.steps = [step for step in plan.steps if step.id != step_to_remove]
        
        if "add_step" in modifications:
            # Add new step logic here
            pass
        
        if "modify_parameters" in modifications:
            # Modify step parameters logic here
            pass
        
        plan.state = PlanState.AWAITING_APPROVAL
        logger.info(f"Plan {plan_id} modified and awaiting re-approval")
        return True
    
    async def get_approved_workflow_plan(self, plan_id: str) -> Optional[WorkflowPlan]:
        """Get approved plan as WorkflowPlan for execution."""
        plan = self.active_plans.get(plan_id)
        if not plan or plan.state != PlanState.APPROVED:
            return None
        
        plan.state = PlanState.EXECUTING
        return plan.to_workflow_plan()
    
    async def mark_plan_completed(self, plan_id: str, success: bool = True):
        """Mark a plan as completed or failed."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
        
        plan.state = PlanState.COMPLETED if success else PlanState.FAILED
        logger.info(f"Plan {plan_id} marked as {'completed' if success else 'failed'}")
    
    def get_plan_state(self, plan_id: str) -> Optional[PlanState]:
        """Get current state of a plan."""
        plan = self.active_plans.get(plan_id)
        return plan.state if plan else None


# Global planner instance
_planner_instance: Optional[WorkflowPlannerAgent] = None

async def get_workflow_planner(auth_context: Optional[Dict[str, str]] = None) -> WorkflowPlannerAgent:
    """Get or create the global workflow planner instance."""
    global _planner_instance
    
    if _planner_instance is None:
        _planner_instance = WorkflowPlannerAgent()
        await _planner_instance.initialize(auth_context)
    
    return _planner_instance