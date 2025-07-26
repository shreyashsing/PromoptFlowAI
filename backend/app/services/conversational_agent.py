"""
Conversational Agent System for PromptFlow AI.
Handles prompt parsing, intent recognition, dialogue management, and workflow planning.
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_database
from app.core.exceptions import AgentError, PlanningError
from app.core.error_utils import handle_external_api_errors, log_function_performance, handle_database_errors
from app.models.conversation import (
    ConversationContext, 
    ChatMessage, 
    PlanModificationRequest,
    PlanConfirmationRequest
)
from app.models.base import (
    WorkflowPlan, 
    WorkflowNode, 
    WorkflowEdge, 
    NodePosition,
    ConversationState,
    WorkflowStatus,
    Trigger
)
from app.models.connector import ConnectorMetadata
from app.services.rag import RAGRetriever

logger = logging.getLogger(__name__)


class IntentRecognitionResult(BaseModel):
    """Result of intent recognition analysis."""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    requires_clarification: bool
    clarification_questions: List[str]


class WorkflowPlanningResult(BaseModel):
    """Result of workflow planning process."""
    plan: WorkflowPlan
    selected_connectors: List[ConnectorMetadata]
    reasoning: str
    confidence: float


class ConversationalAgent:
    """
    Main conversational agent for interactive workflow planning.
    Handles prompt parsing, intent recognition, and dialogue management.
    """
    
    def __init__(self, rag_retriever: RAGRetriever):
        self.rag_retriever = rag_retriever
        self._client: Optional[AsyncAzureOpenAI] = None
        self._initialized = False
        
        # System prompts for different phases
        self.intent_recognition_prompt = self._load_intent_recognition_prompt()
        self.planning_prompt = self._load_planning_prompt()
    
    async def initialize(self) -> None:
        """Initialize the Azure OpenAI client."""
        if self._initialized:
            return
            
        try:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            self._initialized = True
            logger.info("Conversational agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversational agent: {e}")
            raise AgentError(f"Failed to initialize agent: {e}")
    
    @handle_external_api_errors("Azure OpenAI", retryable=True)
    @log_function_performance("process_initial_prompt")
    async def process_initial_prompt(
        self, 
        prompt: str, 
        user_id: str,
        session_id: Optional[str] = None
    ) -> Tuple[ConversationContext, str]:
        """
        Process initial user prompt and start conversation.
        
        Args:
            prompt: User's natural language prompt
            user_id: ID of the user
            session_id: Optional existing session ID
            
        Returns:
            Tuple of (ConversationContext, response_message)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create or get conversation context
            if not session_id:
                session_id = str(uuid.uuid4())
            
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                state=ConversationState.INITIAL
            )
            
            # Add user message to context
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=prompt
            )
            context.messages.append(user_message)
            
            # Recognize intent and analyze prompt
            intent_result = await self._recognize_intent(prompt, context)
            
            # Generate response based on actual intent
            if intent_result.requires_clarification:
                response = await self._handle_clarification_needed(intent_result, context)
                context.state = ConversationState.PLANNING
            elif intent_result.intent == "workflow_creation":
                # Only proceed to workflow planning for actual workflow creation requests
                planning_result = await self._generate_workflow_plan(prompt, context)
                response = await self._present_workflow_plan(planning_result, context)
                context.current_plan = planning_result.plan
                context.state = ConversationState.CONFIRMING
            elif intent_result.intent == "troubleshooting":
                response = await self._handle_troubleshooting_request(prompt, context)
                # Keep the current state, don't change it
            elif intent_result.intent == "question":
                response = await self._handle_general_question(prompt, context)
                # Keep the current state
            elif intent_result.intent == "conversation_management":
                response = await self._handle_conversation_management(prompt, context)
                # Keep the current state
            elif intent_result.intent == "execution_request":
                response = await self._handle_execution_request(prompt, context)
                # Keep the current state
            elif intent_result.intent == "workflow_modification":
                response = await self._handle_workflow_modification_request(prompt, context)
                # Keep the current state
            else:
                # Fallback for unclear intents
                response = await self._handle_unclear_request(prompt, context)
                context.state = ConversationState.PLANNING
            
            # Add assistant response to context
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=response
            )
            context.messages.append(assistant_message)
            
            # Save conversation context
            await self._save_conversation_context(context)
            
            logger.info(f"Processed initial prompt for session {session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to process initial prompt: {e}")
            raise AgentError(f"Failed to process prompt: {e}")
    
    @handle_external_api_errors("Azure OpenAI", retryable=True)
    @log_function_performance("handle_conversation_turn")
    async def handle_conversation_turn(
        self, 
        message: str, 
        session_id: str
    ) -> Tuple[ConversationContext, str]:
        """
        Handle a conversation turn in an existing session.
        
        Args:
            message: User's message
            session_id: Session ID
            
        Returns:
            Tuple of (updated_context, response_message)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Load conversation context
            context = await self._load_conversation_context(session_id)
            if not context:
                raise AgentError(f"Session {session_id} not found")
            
            # Add user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=message
            )
            context.messages.append(user_message)
            
            # Handle based on current conversation state
            if context.state == ConversationState.PLANNING:
                response = await self._handle_planning_conversation(message, context)
            elif context.state == ConversationState.CONFIRMING:
                response = await self._handle_confirmation_conversation(message, context)
            elif context.state in [ConversationState.APPROVED, ConversationState.EXECUTING, ConversationState.INITIAL]:
                # Check if user wants to start a new workflow
                response = await self._handle_post_workflow_conversation(message, context)
            else:
                response = "I'm not sure how to help with that. Could you please start over with a new workflow request?"
            
            # Add assistant response
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=response
            )
            context.messages.append(assistant_message)
            
            # Update timestamp
            context.updated_at = datetime.utcnow()
            
            # Save updated context
            await self._save_conversation_context(context)
            
            logger.info(f"Handled conversation turn for session {session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to handle conversation turn: {e}")
            raise AgentError(f"Failed to handle conversation: {e}")
    
    async def modify_workflow_plan(
        self, 
        request: PlanModificationRequest
    ) -> Tuple[WorkflowPlan, str]:
        """
        Modify an existing workflow plan based on user request.
        
        Args:
            request: Plan modification request
            
        Returns:
            Tuple of (modified_plan, explanation)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Load conversation context
            context = await self._load_conversation_context(request.session_id)
            if not context:
                raise AgentError(f"Session {request.session_id} not found")
            
            # Generate modified plan
            modified_plan = await self._apply_plan_modifications(
                request.modification, 
                request.current_plan, 
                context
            )
            
            # Generate explanation of changes
            explanation = await self._explain_plan_changes(
                request.current_plan, 
                modified_plan, 
                request.modification
            )
            
            # Update context
            context.current_plan = modified_plan
            context.updated_at = datetime.utcnow()
            await self._save_conversation_context(context)
            
            logger.info(f"Modified workflow plan for session {request.session_id}")
            return modified_plan, explanation
            
        except Exception as e:
            logger.error(f"Failed to modify workflow plan: {e}")
            raise PlanningError(f"Failed to modify plan: {e}")
    
    async def confirm_workflow_plan(
        self, 
        request: PlanConfirmationRequest
    ) -> Tuple[ConversationContext, str]:
        """
        Handle workflow plan confirmation.
        
        Args:
            request: Plan confirmation request
            
        Returns:
            Tuple of (updated_context, response_message)
        """
        try:
            # Load conversation context
            context = await self._load_conversation_context(request.session_id)
            if not context:
                raise AgentError(f"Session {request.session_id} not found")
            
            if request.approved:
                # Mark plan as approved and ready for execution
                request.plan.status = WorkflowStatus.ACTIVE
                context.current_plan = request.plan
                context.state = ConversationState.APPROVED
                
                response = (
                    f"Great! I've approved your workflow plan '{request.plan.name}'. "
                    f"The workflow is now ready for execution. You can run it manually "
                    f"or set up triggers for automatic execution."
                )
                
                # Save the approved plan to database
                await self._save_workflow_plan(request.plan)
                
                # Workflow is ready for manual execution
                response += f"\n\n✅ **Workflow Ready!**\n"
                response += f"Configure authentication for each connector, then click 'Execute' to run the workflow."
                
                return response
            else:
                # Plan rejected, return to planning state
                context.state = ConversationState.PLANNING
                response = (
                    "No problem! Let me know what changes you'd like to make to the workflow plan, "
                    "or provide additional details about what you're trying to accomplish."
                )
            
            # Update context
            context.updated_at = datetime.utcnow()
            await self._save_conversation_context(context)
            
            logger.info(f"Handled plan confirmation for session {request.session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to handle plan confirmation: {e}")
            raise AgentError(f"Failed to confirm plan: {e}")
    
    # Private helper methods
    
    async def _recognize_intent(
        self, 
        prompt: str, 
        context: ConversationContext
    ) -> IntentRecognitionResult:
        """Recognize user intent with enhanced flexibility and context awareness."""
        try:
            messages = [
                {
                    "role": "system", 
                    "content": f"""
                    You are analyzing user prompts for workflow automation intent.
                    Be precise in distinguishing between different types of user messages.
                    
                    Respond with JSON containing:
                    - intent: "workflow_creation" | "troubleshooting" | "conversation_management" | "question" | "execution_request" | "workflow_modification"
                    - confidence: 0-1 
                    - entities: extracted information (services, actions, data, etc.)
                    - requires_clarification: true only if genuinely unclear or missing critical info
                    - clarification_questions: specific questions only if truly needed
                    
                    Intent guidelines (BE STRICT):
                    - workflow_creation: ONLY when user explicitly wants to CREATE/BUILD a NEW workflow with specific automation goals
                      Examples: "create a workflow that...", "build automation for...", "I need a workflow to..."
                    
                    - troubleshooting: User reporting issues, asking for retries, or seeking support
                      Examples: "try again", "there was an issue", "fix this", "something went wrong", "error occurred"
                    
                    - conversation_management: Simple responses, confirmations, greetings
                      Examples: "okay", "thanks", "yes", "no", "hello", "got it"
                    
                    - question: User asking about capabilities, how things work, or seeking information
                      Examples: "how does this work?", "what can you do?", "explain this"
                    
                    - execution_request: User wants to run/execute an existing workflow
                      Examples: "run the workflow", "execute this", "start the automation"
                      
                    - workflow_modification: User wants to change an existing workflow
                      Examples: "change the email", "modify the step", "update the workflow"
                    
                    CRITICAL: If the message doesn't contain clear workflow creation language with specific automation goals, DO NOT classify as workflow_creation.
                    
                    Extract useful entities only when relevant to the actual intent.
                    """
                },
                {"role": "user", "content": prompt}
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse the structured response
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
            return IntentRecognitionResult(**result_data)
            
        except Exception as e:
            logger.error(f"Failed to recognize intent: {e}")
            # Return flexible default result that doesn't require clarification
            return IntentRecognitionResult(
                intent="workflow_creation",
                confidence=0.7,
                entities={"user_request": prompt},
                requires_clarification=False,
                clarification_questions=[]
            )
    
    @handle_external_api_errors("Azure OpenAI", retryable=True)
    @log_function_performance("generate_workflow_plan")
    async def _generate_workflow_plan(
        self, 
        prompt: str, 
        context: ConversationContext
    ) -> WorkflowPlanningResult:
        """Generate a workflow plan based on user prompt."""
        try:
            # Retrieve relevant connectors using RAG
            connectors = await self.rag_retriever.retrieve_connectors(
                query=prompt,
                limit=15,
                similarity_threshold=0.3
            )
            
            if not connectors:
                raise PlanningError("No suitable connectors found for the requested workflow")
            
            # Prepare connector information for the LLM
            connector_info = []
            for conn in connectors:
                connector_info.append({
                    "name": conn.name,
                    "description": conn.description,
                    "category": conn.category,
                    "parameters": conn.parameter_schema,
                    "auth_type": conn.auth_type.value
                })
            
            # Create planning messages
            messages = [
                {"role": "system", "content": self.planning_prompt},
                {
                    "role": "user", 
                    "content": f"""
                    User Request: {prompt}
                    
                    Available Connectors:
                    {json.dumps(connector_info, indent=2)}
                    
                    CRITICAL PARAMETER REQUIREMENTS:
                    You MUST populate ALL required parameters for each connector based on the user's request. Do NOT leave parameters empty or use placeholders.
                    
                    EXACT PARAMETER REQUIREMENTS (DO NOT DEVIATE):
                    
                    IMPORTANT: Use the exact parameter schemas provided for each connector. Each connector has specific required parameters that MUST be included.
                    
                    PARAMETER CHAINING:
                    Use {{previous_connector_name.result}} to chain outputs between connectors.
                    
                    WORKFLOW STRUCTURE:
                    {{
                        "name": "Workflow Name",
                        "description": "Workflow description", 
                        "nodes": [
                            {{
                                "connector_name": "connector_name_from_available_list",
                                "parameters": {{
                                    // Use the exact parameter names and types from the connector's schema
                                    // Include ALL required parameters
                                    // Use appropriate default values from the schema
                                }},
                                "dependencies": ["previous_connector_name"] // if this node depends on another
                            }}
                        ]
                    }}
                    
                    CRITICAL: 
                    - Use ONLY connectors from the Available Connectors list
                    - Check each connector's parameter_schema for required fields
                    - Use appropriate default values from the schema
                    - Reference previous node outputs using {{connector_name.result}} syntax for data flow
                    
                    Generate a complete workflow plan with ALL parameters properly filled based on the user's specific request.
                    """
                }
            ]
            
            # Use function calling to generate structured workflow plan
            functions = [self._get_workflow_planning_function()]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                functions=functions,
                function_call={"name": "generate_workflow_plan"},
                temperature=0.2,
                max_tokens=2000
            )
            
            # Parse function call result
            function_call = response.choices[0].message.function_call
            plan_data = json.loads(function_call.arguments)
            
            # Debug: Log the generated plan data
            logger.info(f"AI generated workflow plan: {json.dumps(plan_data, indent=2)}")
            
            # Validate and fix parameters with contextual reasoning
            plan_data = await self._validate_and_fix_parameters_with_context(plan_data, prompt)
            
            # Create WorkflowPlan object
            workflow_plan = self._create_workflow_plan_from_data(
                plan_data, 
                context.user_id
            )
            
            # Filter connectors to only those used in the plan
            used_connector_names = {node.connector_name for node in workflow_plan.nodes}
            selected_connectors = [
                conn for conn in connectors 
                if conn.name in used_connector_names
            ]
            
            return WorkflowPlanningResult(
                plan=workflow_plan,
                selected_connectors=selected_connectors,
                reasoning=plan_data.get("reasoning", ""),
                confidence=plan_data.get("confidence", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate workflow plan: {e}")
            raise PlanningError(f"Failed to generate workflow plan: {e}")
    
    async def _handle_clarification_needed(
        self, 
        intent_result: IntentRecognitionResult, 
        context: ConversationContext
    ) -> str:
        """Handle cases where clarification is needed from the user."""
        questions = intent_result.clarification_questions
        
        response = (
            "I'd like to help you create a workflow, but I need a bit more information. "
            "Could you help me understand:\n\n"
        )
        
        for i, question in enumerate(questions, 1):
            response += f"{i}. {question}\n"
        
        response += (
            "\nOnce I have these details, I'll be able to create a detailed workflow plan for you."
        )
        
        return response
    
    async def _present_workflow_plan(
        self, 
        planning_result: WorkflowPlanningResult, 
        context: ConversationContext
    ) -> str:
        """Present the generated workflow plan to the user."""
        plan = planning_result.plan
        
        response = f"I've created a workflow plan called '{plan.name}' for you:\n\n"
        response += f"**Description:** {plan.description}\n\n"
        response += "**Workflow Steps:**\n"
        
        # Sort nodes by dependencies to show logical flow
        sorted_nodes = self._sort_nodes_by_dependencies(plan.nodes)
        
        for i, node in enumerate(sorted_nodes, 1):
            connector = next(
                (c for c in planning_result.selected_connectors if c.name == node.connector_name),
                None
            )
            
            if connector:
                response += f"{i}. **{connector.name.replace('_', ' ').title()}**\n"
                response += f"   - {connector.description}\n"
                
                if node.parameters:
                    response += f"   - Parameters: {self._format_parameters(node.parameters)}\n"
                
                response += "\n"
        
        if plan.triggers:
            response += "**Triggers:**\n"
            for trigger in plan.triggers:
                response += f"- {trigger.type}: {self._format_trigger_config(trigger.config)}\n"
            response += "\n"
        
        response += f"**Reasoning:** {planning_result.reasoning}\n\n"
        response += (
            "Does this workflow plan look good to you? You can:\n"
            "- Approve it by saying 'yes' or 'approve'\n"
            "- Request changes by describing what you'd like modified\n"
            "- Ask questions about any part of the plan"
        )
        
        return response
    
    async def _handle_planning_conversation(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle conversation during the planning phase with enhanced flexibility."""
        try:
            # Use AI to understand user intent instead of rigid keyword matching
            intent_analysis = await self._analyze_planning_intent(message, context)
            
            if intent_analysis["action"] == "create_workflow":
                # Generate new workflow plan with accumulated context
                full_prompt = self._build_full_prompt_from_context(context)
                planning_result = await self._generate_workflow_plan(full_prompt, context)
                
                context.current_plan = planning_result.plan
                context.state = ConversationState.CONFIRMING
                
                return await self._present_workflow_plan(planning_result, context)
                
            elif intent_analysis["action"] == "provide_more_info":
                # User is providing additional information
                acknowledgment = await self._generate_acknowledgment_response(message, intent_analysis)
                return acknowledgment
                
            elif intent_analysis["action"] == "ask_question":
                # User has questions before proceeding
                answer = await self._answer_planning_question(message, context)
                return answer
                
            elif intent_analysis["action"] == "modify_requirements":
                # User wants to change their requirements
                context.state = ConversationState.PLANNING
                return await self._handle_requirement_modification(message, context)
                
            else:
                # Generate contextual response for unclear or other intents
                return await self._generate_planning_guidance(message, intent_analysis, context)
                
        except Exception as e:
            logger.error(f"Error in planning conversation: {e}")
            return (
                "I encountered an issue while processing your request. "
                "Could you please rephrase what you'd like the workflow to do?"
            )
    
    async def _analyze_planning_intent(
        self, 
        message: str, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Analyze user intent during the planning phase."""
        try:
            conversation_summary = self._summarize_conversation_context(context)
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are analyzing user messages during workflow planning. 
                    Determine what the user wants to do next.
                    
                    Context: {conversation_summary}
                    
                    Respond with JSON containing:
                    - action: "create_workflow" | "provide_more_info" | "ask_question" | "modify_requirements" | "unclear"
                    - confidence: 0-1
                    - details: specific information extracted from their message
                    - reasoning: brief explanation of your analysis
                    
                    Actions explained:
                    - create_workflow: User wants to generate/create the workflow plan now
                    - provide_more_info: User is adding more details or requirements
                    - ask_question: User has questions about the process or capabilities
                    - modify_requirements: User wants to change previously stated requirements
                    - unclear: Message is ambiguous or off-topic
                    """
                },
                {
                    "role": "user",
                    "content": f"User message: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=600
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to analyze planning intent: {e}")
            return {
                "action": "unclear",
                "confidence": 0.0,
                "details": {},
                "reasoning": "Failed to parse user intent"
            }

    async def _generate_acknowledgment_response(
        self, 
        message: str, 
        intent_analysis: Dict[str, Any]
    ) -> str:
        """Generate intelligent acknowledgment for additional information."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """
                    The user has provided additional information about their workflow requirements.
                    Generate a natural acknowledgment that shows you understand their input
                    and guide them toward the next step.
                    
                    Be encouraging and show you're building up a complete picture of their needs.
                    """
                },
                {
                    "role": "user",
                    "content": f"User provided: {message}\nIntent analysis: {intent_analysis}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate acknowledgment: {e}")
            return "Thank you for that information. Is there anything else you'd like to add, or shall I create the workflow plan?"

    async def _answer_planning_question(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Answer questions during the planning phase."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """
                    You are helping a user understand workflow planning capabilities.
                    Answer their questions clearly and help them make informed decisions.
                    Focus on being helpful and educational.
                    """
                },
                {
                    "role": "user",
                    "content": f"User question: {message}\nContext: {self._summarize_conversation_context(context)}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            
            answer = response.choices[0].message.content
            return f"{answer}\n\nDo you have any other questions, or would you like me to create your workflow plan?"
            
        except Exception as e:
            logger.error(f"Failed to answer planning question: {e}")
            return "I'd be happy to help answer your question. Could you rephrase it so I can better understand what you're looking for?"

    async def _handle_requirement_modification(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle when user wants to modify their requirements."""
        # Update the conversation context with the modification
        modification_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=f"REQUIREMENT_UPDATE: {message}"
        )
        context.messages.append(modification_message)
        
        return "I've noted your updated requirements. Please let me know if you have any other changes, or say 'create the workflow' when you're ready for me to generate the plan."

    async def _generate_planning_guidance(
        self, 
        message: str, 
        intent_analysis: Dict[str, Any], 
        context: ConversationContext
    ) -> str:
        """Generate helpful guidance during planning phase."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are guiding a user through workflow planning. Their message was unclear or didn't fit standard patterns.
                    
                    Generate a helpful response that:
                    - Acknowledges their input
                    - Guides them toward useful next steps
                    - Offers specific examples if they seem stuck
                    - Maintains a supportive, encouraging tone
                    
                    Intent analysis: {intent_analysis}
                    """
                },
                {
                    "role": "user",
                    "content": f"User said: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.4,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate planning guidance: {e}")
            return (
                "I want to make sure I create the perfect workflow for you. "
                "Could you tell me more about what you'd like to automate or accomplish?"
            )
    
    async def _handle_confirmation_conversation(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle conversation during the confirmation phase with intelligent intent detection."""
        try:
            # Use AI to understand user intent instead of rigid keyword matching
            intent_result = await self._analyze_confirmation_intent(message, context)
            
            if intent_result["action"] == "approve":
                if context.current_plan:
                    context.current_plan.status = WorkflowStatus.ACTIVE
                    context.state = ConversationState.APPROVED
                    
                    # Save the approved plan
                    await self._save_workflow_plan(context.current_plan)
                    
                    response = (
                        f"Excellent! I've approved your workflow '{context.current_plan.name}'. "
                        f"The workflow is now active and ready for execution. "
                        f"You can run it manually or set up triggers for automatic execution."
                    )
                    
                    # Workflow is ready for manual execution
                    response += f"\n\n✅ **Workflow Ready!**\n"
                    response += f"Configure authentication for each connector, then click 'Execute' to run the workflow."
                    
                    return response
                else:
                    return "I don't have a current plan to approve. Let's start over with your workflow request."
            
            elif intent_result["action"] == "modify":
                if context.current_plan:
                    # Handle modification request with specific changes
                    try:
                        original_plan = context.current_plan
                        modified_plan = await self._apply_intelligent_modifications(
                            message, 
                            intent_result.get("specific_changes", []),
                            context.current_plan, 
                            context
                        )
                        
                        # Generate explanation of changes
                        explanation = await self._explain_plan_changes(
                            original_plan,
                            modified_plan,
                            message
                        )
                        
                        context.current_plan = modified_plan
                        
                        response = f"I've updated the workflow plan based on your request:\n\n{explanation}\n\n"
                        response += await self._present_workflow_plan(
                            WorkflowPlanningResult(
                                plan=modified_plan,
                                selected_connectors=[],  # Will be populated if needed
                                reasoning="Plan modified based on user feedback",
                                confidence=0.8
                            ),
                            context
                        )
                        
                        return response
                        
                    except Exception as e:
                        logger.error(f"Failed to modify plan: {e}")
                        return await self._generate_clarification_response(message, context)
                else:
                    return "I don't have a current plan to modify. Let's start over with your workflow request."
            
            elif intent_result["action"] == "question":
                # Handle questions about the workflow plan
                return await self._answer_workflow_question(message, context)
            
            elif intent_result["action"] == "reject":
                # Handle complete rejection
                context.state = ConversationState.PLANNING
                return (
                    "No problem! Let's start over. Please describe what you'd like your workflow to do, "
                    "and I'll create a new plan for you."
                )
            
            else:
                # Generate intelligent response based on context
                return await self._generate_contextual_response(message, intent_result, context)
                
        except Exception as e:
            logger.error(f"Error in confirmation conversation: {e}")
            return await self._generate_fallback_response(message, context)

    async def _analyze_confirmation_intent(
        self, 
        message: str, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Use AI to analyze user intent during confirmation phase."""
        try:
            current_plan_summary = ""
            if context.current_plan:
                current_plan_summary = f"""
                Current workflow plan: "{context.current_plan.name}"
                Description: {context.current_plan.description}
                Steps: {len(context.current_plan.nodes)} connectors
                """
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are analyzing user responses to a workflow plan proposal. 
                    Determine the user's intent and extract specific details.
                    
                    Context: {current_plan_summary}
                    
                    Respond with JSON containing:
                    - action: "approve" | "modify" | "question" | "reject" | "unclear"
                    - confidence: 0-1 
                    - specific_changes: array of specific modifications requested (if action is "modify")
                    - question_topic: what they're asking about (if action is "question")
                    - reasoning: brief explanation of your analysis
                    
                    Examples of modifications to detect:
                    - "remove the test message part" -> specific_changes: ["remove_test_message"]
                    - "change the email to john@example.com" -> specific_changes: ["change_email_recipient"]
                    - "use a different summary style" -> specific_changes: ["modify_summary_style"]
                    - "add more search results" -> specific_changes: ["increase_search_results"]
                    """
                },
                {
                    "role": "user", 
                    "content": f"User response: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=800
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to analyze confirmation intent: {e}")
            return {
                "action": "unclear",
                "confidence": 0.0,
                "specific_changes": [],
                "reasoning": "Failed to parse user intent"
            }

    async def _apply_intelligent_modifications(
        self, 
        original_message: str,
        specific_changes: List[str],
        current_plan: WorkflowPlan, 
        context: ConversationContext
    ) -> WorkflowPlan:
        """Apply modifications with RAG-based connector discovery and intelligent workflow restructuring."""
        try:
            # Use RAG to discover relevant connectors for the modification request
            modification_query = f"{original_message} {' '.join(specific_changes)}"
            relevant_connectors = await self.rag_retriever.retrieve_connectors(
                query=modification_query,
                limit=15,
                similarity_threshold=0.3
            )
            
            if not relevant_connectors:
                logger.warning("No relevant connectors found for modification request")
                # Fallback to existing connectors
                relevant_connectors = await self.rag_retriever.retrieve_connectors(
                    query="workflow automation",
                    limit=10,
                    similarity_threshold=0.2
                )
            
            # Prepare connector information for the LLM
            connector_info = []
            for conn in relevant_connectors:
                connector_info.append({
                    "name": conn.name,
                    "description": conn.description,
                    "category": conn.category,
                    "parameters": conn.parameter_schema,
                    "auth_type": conn.auth_type.value if hasattr(conn.auth_type, 'value') else str(conn.auth_type)
                })
            
            # Enhanced modification prompt that understands specific changes
            modification_context = f"""
            User's original request: {original_message}
            Specific changes detected: {specific_changes}
            
            Please modify the workflow plan according to these specific requirements:
            """
            
            for change in specific_changes:
                if "remove" in change.lower():
                    modification_context += f"\n- Remove or eliminate components related to: {change}"
                elif "change" in change.lower() or "modify" in change.lower():
                    modification_context += f"\n- Modify or update: {change}"
                elif "add" in change.lower():
                    modification_context += f"\n- Add or include: {change}"
                else:
                    modification_context += f"\n- Address requirement: {change}"
            
            messages = [
                {
                    "role": "system", 
                    "content": f"""
                    You are modifying an existing workflow plan based on user feedback with access to relevant connectors.
                    
                    CRITICAL RULES FOR MODIFICATION:
                    1. Use RAG-discovered connectors from the available list for new functionality
                    2. When adding connectors, intelligently determine optimal placement in the workflow
                    3. Maintain existing data flow while incorporating new connectors
                    4. For parallel operations (like saving to multiple destinations), place them at the same dependency level
                    5. For sequential operations, place them in logical order
                    
                    INTELLIGENT PLACEMENT STRATEGIES:
                    - Adding output connectors (email, sheets, notifications): Place in parallel after data preparation
                    - Adding processing connectors (summarizers, transformers): Place in sequence before outputs
                    - Adding input connectors (searches, APIs): Place early in the workflow
                    
                    WORKFLOW GRAPH LOGIC:
                    - Use dependencies array to control execution order
                    - Multiple connectors can depend on the same parent for parallel execution
                    - Ensure proper data flow using {{connector_name.result}} syntax
                    
                    {self.modification_prompt}
                    
                    Pay special attention to:
                    - Removing components when asked (don't just hide them)
                    - Changing parameters accurately
                    - Maintaining workflow logic and dependencies
                    - Preserving user's original intent while making requested changes
                    - Using appropriate connectors from the available list
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    Current Workflow Plan:
                    {json.dumps(current_plan.dict(), indent=2, default=str)}
                    
                    Available Connectors for Modification:
                    {json.dumps(connector_info, indent=2)}
                    
                    {modification_context}
                    
                    Please generate the modified workflow plan using appropriate connectors from the available list.
                    Ensure new connectors are placed optimally in the workflow graph.
                    """
                }
            ]
            
            # Use function calling for structured modification
            functions = [self._get_workflow_planning_function()]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                functions=functions,
                function_call={"name": "generate_workflow_plan"},
                temperature=0.2,
                max_tokens=2000
            )
            
            # Parse the modified plan
            function_call = response.choices[0].message.function_call
            plan_data = json.loads(function_call.arguments)
            
            # Validate and fix parameters with contextual reasoning
            plan_data = await self._validate_and_fix_parameters_with_context(plan_data, original_message)
            
            # Create modified WorkflowPlan
            modified_plan = self._create_workflow_plan_from_data(
                plan_data, 
                current_plan.user_id
            )
            
            # Preserve original ID and timestamps
            modified_plan.id = current_plan.id
            modified_plan.created_at = current_plan.created_at
            modified_plan.updated_at = datetime.utcnow()
            
            logger.info(f"Applied intelligent modifications with {len(relevant_connectors)} available connectors")
            return modified_plan
            
        except Exception as e:
            logger.error(f"Failed to apply intelligent modifications: {e}")
            raise PlanningError(f"Failed to modify plan: {e}")

    async def _answer_workflow_question(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Answer questions about the current workflow plan."""
        try:
            if not context.current_plan:
                return "I don't have a current workflow plan to discuss. Would you like to create one?"
            
            messages = [
                {
                    "role": "system",
                    "content": """
                    You are helping a user understand their workflow plan. 
                    Answer their questions clearly and provide helpful details about how the workflow works.
                    Keep answers concise but informative.
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    Workflow Plan:
                    {json.dumps(context.current_plan.dict(), indent=2, default=str)}
                    
                    User Question: {message}
                    
                    Please answer their question about this workflow.
                    """
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            return f"{answer}\n\nWould you like to approve this workflow, make changes, or ask another question?"
            
        except Exception as e:
            logger.error(f"Failed to answer workflow question: {e}")
            return "I'm having trouble understanding your question. Could you rephrase it?"

    async def _generate_contextual_response(
        self, 
        message: str, 
        intent_result: Dict[str, Any], 
        context: ConversationContext
    ) -> str:
        """Generate intelligent contextual responses instead of hardcoded patterns."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are a helpful AI assistant managing workflow creation. 
                    The user has been presented with a workflow plan and you need to respond appropriately.
                    
                    Current context:
                    - User has a workflow plan pending approval
                    - Their response was: "{message}"
                    - Intent analysis: {intent_result}
                    
                    Generate a helpful, conversational response that:
                    - Acknowledges their input
                    - Guides them toward next steps
                    - Offers specific options based on their needs
                    - Maintains a friendly, professional tone
                    
                    Avoid rigid, robotic responses. Be natural and adaptive.
                    """
                },
                {
                    "role": "user",
                    "content": f"User said: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.4,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate contextual response: {e}")
            return await self._generate_fallback_response(message, context)

    async def _generate_clarification_response(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Generate intelligent clarification requests."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """
                    The user wants to modify a workflow plan, but there was an issue processing their request.
                    Generate a helpful response that asks for clarification in a natural way.
                    Be specific about what information would help, and offer examples.
                    """
                },
                {
                    "role": "user",
                    "content": f"User modification request: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate clarification response: {e}")
            return "I'd like to help modify the workflow, but I need a bit more clarity. Could you tell me specifically what you'd like to change?"

    async def _generate_fallback_response(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Generate fallback response when other methods fail."""
        return (
            "I want to make sure I understand you correctly. Could you help me by:\n"
            "• Telling me if you'd like to approve the current workflow plan\n"
            "• Describing any specific changes you'd like to make\n"
            "• Asking any questions you have about how it works\n\n"
            "I'm here to make this workflow perfect for your needs!"
        )
    
    async def _apply_plan_modifications(
        self, 
        modification_request: str, 
        current_plan: WorkflowPlan, 
        context: ConversationContext
    ) -> WorkflowPlan:
        """Apply modifications to an existing workflow plan."""
        try:
            # Prepare modification prompt
            messages = [
                {"role": "system", "content": self.modification_prompt},
                {
                    "role": "user",
                    "content": f"""
                    Current Workflow Plan:
                    {json.dumps(current_plan.dict(), indent=2, default=str)}
                    
                    Modification Request:
                    {modification_request}
                    
                    Please modify the workflow plan according to the user's request.
                    """
                }
            ]
            
            # Use function calling for structured modification
            functions = [self._get_workflow_planning_function()]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                functions=functions,
                function_call={"name": "generate_workflow_plan"},
                temperature=0.2,
                max_tokens=2000
            )
            
            # Parse the modified plan
            function_call = response.choices[0].message.function_call
            plan_data = json.loads(function_call.arguments)
            
            # Validate and fix parameters with contextual reasoning
            plan_data = await self._validate_and_fix_parameters_with_context(plan_data, modification_request)
            
            # Create modified WorkflowPlan
            modified_plan = self._create_workflow_plan_from_data(
                plan_data, 
                current_plan.user_id
            )
            
            # Preserve original ID and timestamps
            modified_plan.id = current_plan.id
            modified_plan.created_at = current_plan.created_at
            modified_plan.updated_at = datetime.utcnow()
            
            return modified_plan
            
        except Exception as e:
            logger.error(f"Failed to apply plan modifications: {e}")
            raise PlanningError(f"Failed to modify plan: {e}")
    
    async def _explain_plan_changes(
        self, 
        original_plan: WorkflowPlan, 
        modified_plan: WorkflowPlan, 
        modification_request: str
    ) -> str:
        """Generate explanation of changes made to the plan."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant that explains changes made to workflow plans. "
                        "Provide a clear, concise explanation of what was changed and why."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                    Original Plan: {json.dumps(original_plan.dict(), indent=2, default=str)}
                    Modified Plan: {json.dumps(modified_plan.dict(), indent=2, default=str)}
                    User Request: {modification_request}
                    
                    Please explain what changes were made to the workflow plan.
                    """
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to explain plan changes: {e}")
            return "I've updated the workflow plan based on your request."    

    async def _handle_post_workflow_conversation(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle conversation after workflow completion with enhanced flexibility."""
        try:
            # Analyze user intent for post-workflow conversation
            intent_result = await self._analyze_post_workflow_intent(message, context)
            
            if intent_result["action"] == "create_new_workflow":
                # User wants to create a new workflow
                context.state = ConversationState.PLANNING
                context.current_plan = None
                
                # Reset conversation context for new workflow
                context.messages = context.messages[-2:]  # Keep recent context but start fresh
                
                # Add the new request message
                user_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    role="user",
                    content=message
                )
                context.messages.append(user_message)
                
                # Generate initial planning response
                return await self._generate_new_workflow_response(message, intent_result)
                
            elif intent_result["action"] == "execute_workflow":
                # User wants to execute the current workflow
                if context.current_plan and context.current_plan.status == WorkflowStatus.ACTIVE:
                    return (
                        f"Great! To execute your workflow '{context.current_plan.name}', "
                        f"please make sure all connectors are properly authenticated, "
                        f"then click the 'Execute' button in the interface."
                    )
                else:
                    return "You don't have an active workflow to execute. Would you like to create a new one?"
                    
            elif intent_result["action"] == "modify_existing":
                # User wants to modify the existing workflow
                if context.current_plan:
                    context.state = ConversationState.CONFIRMING
                    return await self._handle_existing_workflow_modification(message, context)
                else:
                    return "You don't have an existing workflow to modify. Would you like to create a new one?"
                    
            elif intent_result["action"] == "ask_question":
                # User has questions about workflows or the system
                return await self._answer_general_question(message, context)
                
            else:
                # Generate contextual response for unclear intents
                return await self._generate_contextual_guidance(message, intent_result, context)
                
        except Exception as e:
            logger.error(f"Error in post-workflow conversation: {e}")
            return (
                "I'm here to help! You can create a new workflow, execute an existing one, "
                "or ask me any questions about workflow automation. What would you like to do?"
            )

    async def _analyze_post_workflow_intent(
        self, 
        message: str, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Analyze user intent after workflow completion."""
        try:
            workflow_status = "No active workflow"
            if context.current_plan:
                workflow_status = f"Has workflow: '{context.current_plan.name}' (status: {context.current_plan.status})"
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are analyzing user messages after workflow creation/completion.
                    Determine what the user wants to do next.
                    
                    Current state: {workflow_status}
                    Conversation state: {context.state}
                    
                    Respond with JSON containing:
                    - action: "create_new_workflow" | "execute_workflow" | "modify_existing" | "ask_question" | "unclear"
                    - confidence: 0-1
                    - workflow_details: any workflow requirements extracted (if creating new)
                    - reasoning: brief explanation of your analysis
                    
                    Actions explained:
                    - create_new_workflow: User wants to create a completely new workflow
                    - execute_workflow: User wants to run their current workflow
                    - modify_existing: User wants to change their existing workflow
                    - ask_question: User has questions about workflows or capabilities
                    - unclear: Message is ambiguous or doesn't fit the patterns
                    """
                },
                {
                    "role": "user",
                    "content": f"User message: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=600
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to analyze post-workflow intent: {e}")
            return {
                "action": "unclear",
                "confidence": 0.0,
                "workflow_details": {},
                "reasoning": "Failed to parse user intent"
            }

    async def _generate_new_workflow_response(
        self, 
        message: str, 
        intent_result: Dict[str, Any]
    ) -> str:
        """Generate response for new workflow creation."""
        try:
            workflow_details = intent_result.get("workflow_details", {})
            
            if workflow_details and len(workflow_details) > 0:
                # User provided clear requirements
                return (
                    f"Perfect! I understand you want to create a new workflow. "
                    f"Let me analyze your requirements and generate a plan for you."
                )
            else:
                # User intent is clear but needs more details
                return (
                    "I'd be happy to help you create a new workflow! "
                    "Please describe what you'd like to automate - for example:\n"
                    "• Send emails or notifications\n"
                    "• Process data from web sources\n"
                    "• Integrate different services\n"
                    "• Schedule automated tasks\n\n"
                    "What would you like your workflow to accomplish?"
                )
                
        except Exception as e:
            logger.error(f"Failed to generate new workflow response: {e}")
            return "I'd be happy to help you create a new workflow! What would you like to automate?"

    async def _handle_existing_workflow_modification(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle modifications to existing workflow."""
        try:
            # Apply the modification using the intelligent modification system
            original_plan = context.current_plan
            intent_result = await self._analyze_confirmation_intent(message, context)
            
            if intent_result["action"] == "modify":
                modified_plan = await self._apply_intelligent_modifications(
                    message, 
                    intent_result.get("specific_changes", []),
                    context.current_plan, 
                    context
                )
                
                # Generate explanation of changes
                explanation = await self._explain_plan_changes(
                    original_plan,
                    modified_plan,
                    message
                )
                
                context.current_plan = modified_plan
                
                response = f"I've updated your existing workflow:\n\n{explanation}\n\n"
                response += await self._present_workflow_plan(
                    WorkflowPlanningResult(
                        plan=modified_plan,
                        selected_connectors=[],
                        reasoning="Existing workflow modified",
                        confidence=0.8
                    ),
                    context
                )
                
                return response
            else:
                return "I'd be happy to modify your existing workflow. Could you tell me specifically what changes you'd like to make?"
                
        except Exception as e:
            logger.error(f"Failed to handle existing workflow modification: {e}")
            return "I'd like to help modify your workflow. Could you be more specific about what changes you want to make?"

    async def _handle_general_question(self, message: str, context: ConversationContext) -> str:
        """Handle general questions about the system."""
        try:
            # Use RAG to get relevant connectors for the user's question
            relevant_connectors = await self.rag_retriever.retrieve_connectors(
                query=message,
                limit=10,
                similarity_threshold=0.3
            )
            
            # Build dynamic connector information
            if relevant_connectors:
                connector_info = "\n".join([
                    f"- {conn.name.replace('_', ' ').title()}: {conn.description}"
                    for conn in relevant_connectors
                ])
                connector_context = f"\nRelevant connectors for your question:\n{connector_info}"
            else:
                connector_context = "\nI have various connectors available for workflow automation."
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are a helpful assistant for PromptFlow AI, a workflow automation platform.
                    Answer user questions about the system's capabilities, available connectors, and how things work.
                    
                    {connector_context}
                    
                    Be helpful and informative. If they want to create a workflow, guide them to be specific about their automation goals.
                    Focus on the connectors that are most relevant to their question.
                    """
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error handling general question: {e}")
            return (
                "I'd be happy to help answer your question! "
                "PromptFlow AI helps you create automated workflows using various connectors. "
                "What specific aspect would you like to know about?"
            )

    async def _generate_contextual_guidance(
        self, 
        message: str, 
        intent_result: Dict[str, Any], 
        context: ConversationContext
    ) -> str:
        """Generate contextual guidance for unclear post-workflow messages."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are guiding a user who has completed workflow creation. Their message was unclear.
                    
                    Current context:
                    - User state: {context.state}
                    - Has workflow: {context.current_plan is not None}
                    - Intent analysis: {intent_result}
                    
                    Generate a helpful response that:
                    - Acknowledges their input
                    - Offers clear next steps they can take
                    - Provides specific examples of what they can do
                    - Maintains an encouraging, helpful tone
                    """
                },
                {
                    "role": "user",
                    "content": f"User said: {message}"
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.4,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate contextual guidance: {e}")
            return (
                "I'm here to help with your workflow automation! You can:\n"
                "• Create a new workflow by describing what you want to automate\n"
                "• Execute your current workflow if you have one ready\n"
                "• Ask questions about what's possible with workflow automation\n\n"
                "What would you like to do?"
            )

    def _serialize_workflow_plan(self, plan: WorkflowPlan) -> Dict[str, Any]:
        """Serialize WorkflowPlan to JSON-compatible dict with datetime handling."""
        plan_dict = plan.dict()
        # Convert datetime objects to ISO format strings
        if 'created_at' in plan_dict:
            plan_dict['created_at'] = plan_dict['created_at'].isoformat()
        if 'updated_at' in plan_dict:
            plan_dict['updated_at'] = plan_dict['updated_at'].isoformat()
        return plan_dict

    # Database and persistence methods
    
    @handle_database_errors("save_conversation_context")
    async def _save_conversation_context(self, context: ConversationContext) -> None:
        """Save conversation context to database."""
        try:
            db = await get_database()
            
            # Test database connection before proceeding
            try:
                # Simple test query to verify connection and permissions
                test_result = db.table('conversations').select('id').limit(1).execute()
                logger.info(f"Database connection test successful for conversation save (user: {context.user_id})")
            except Exception as test_e:
                logger.error(f"Database connection test failed: {test_e}")
                return  # Exit early if we can't even query
            
            # Ensure user exists (especially for development user)
            await self._ensure_user_exists(context.user_id, db)
            
            context_data = {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata
                    } for msg in context.messages
                ],
                "current_plan": self._serialize_workflow_plan(context.current_plan) if context.current_plan else None,
                "state": context.state.value,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat()
            }
            
            # First check if the conversation exists
            existing = db.table('conversations').select('id').eq('user_id', context.user_id).eq('session_id', context.session_id).execute()
            
            # Generate a title from the first message if available
            title = "New Conversation"
            if context.messages:
                first_message = context.messages[0].content[:50] + "..." if len(context.messages[0].content) > 50 else context.messages[0].content
                title = first_message
            
            # Create metadata from context
            metadata = {
                'state': context.state.value,
                'message_count': len(context.messages),
                'has_plan': context.current_plan is not None
            }
            
            # Prepare the full conversation data
            conversation_data = {
                'user_id': context.user_id,
                'session_id': context.session_id,
                'title': title,
                'messages': [
                    {
                        'id': msg.id,
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'metadata': msg.metadata
                    } for msg in context.messages
                ],
                'current_plan': self._serialize_workflow_plan(context.current_plan) if context.current_plan else None,
                'state': context.state.value,
                'metadata': metadata,
                'updated_at': datetime.now().isoformat()
            }
            
            if existing.data and len(existing.data) > 0:
                # Update existing conversation
                db.table('conversations').update(conversation_data).eq('user_id', context.user_id).eq('session_id', context.session_id).execute()
            else:
                # Insert new conversation
                conversation_data['created_at'] = datetime.now().isoformat()
                db.table('conversations').insert(conversation_data).execute()
            
            logger.debug(f"Saved conversation context for session {context.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation context: {e}")
            logger.error(f"Context details: user_id={context.user_id}, session_id={context.session_id}, messages_count={len(context.messages)}")
            # For debugging: Let's make this error more visible
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Don't raise error as this is not critical for functionality
    
    @handle_database_errors("load_conversation_context")
    async def _load_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Load conversation context from database."""
        try:
            db = await get_database()
            
            # Add debugging to see what's happening
            logger.info(f"Attempting to load conversation: {session_id}")
            
            result = db.table("conversations").select("*").eq("session_id", session_id).execute()
            
            logger.info(f"Load query result: found {len(result.data) if result.data else 0} conversations")
            
            if not result.data:
                # Additional debugging - try to see if conversation exists at all
                try:
                    debug_result = db.table("conversations").select("session_id, user_id").eq("session_id", session_id).execute()
                    if debug_result.data:
                        logger.warning(f"Conversation exists but not accessible: session={session_id}, user_id={debug_result.data[0].get('user_id')}")
                    else:
                        logger.info(f"Conversation truly not found: {session_id}")
                except Exception as debug_e:
                    logger.error(f"Debug query failed: {debug_e}")
                return None
            
            data = result.data[0]
            logger.info(f"Successfully loaded conversation: {session_id} for user {data.get('user_id')}")
            
            # Reconstruct messages
            messages = []
            for msg_data in data["messages"]:
                msg_data_copy = msg_data.copy()
                if isinstance(msg_data_copy["timestamp"], str):
                    msg_data_copy["timestamp"] = datetime.fromisoformat(msg_data_copy["timestamp"])
                messages.append(ChatMessage(**msg_data_copy))
            
            # Reconstruct current plan if exists
            current_plan = None
            if data["current_plan"]:
                plan_data = data["current_plan"].copy()
                # Convert datetime strings back to datetime objects
                if 'created_at' in plan_data and isinstance(plan_data['created_at'], str):
                    plan_data['created_at'] = datetime.fromisoformat(plan_data['created_at'])
                if 'updated_at' in plan_data and isinstance(plan_data['updated_at'], str):
                    plan_data['updated_at'] = datetime.fromisoformat(plan_data['updated_at'])
                current_plan = WorkflowPlan(**plan_data)
            
            return ConversationContext(
                session_id=data["session_id"],
                user_id=data["user_id"],
                messages=messages,
                current_plan=current_plan,
                state=ConversationState(data["state"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"])
            )
            
        except Exception as e:
            logger.error(f"Failed to load conversation context: {e}")
            return None
    
    async def _ensure_user_exists(self, user_id: str, db) -> None:
        """Ensure user exists in database, create if missing (especially for development user)."""
        try:
            # Check if user exists
            result = db.table('users').select('id').eq('id', user_id).execute()
            
            if not result.data:
                # User doesn't exist, create them
                if user_id == "00000000-0000-0000-0000-000000000001":
                    # Development user
                    user_data = {
                        "id": user_id,
                        "email": "dev@test.com",
                        "full_name": "Development User",
                        "avatar_url": None,
                        "preferences": {},
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    db.table('users').insert(user_data).execute()
                    logger.info(f"Created development user profile: {user_id}")
                else:
                    # Regular user - this shouldn't happen in normal flow but create basic profile
                    user_data = {
                        "id": user_id,
                        "email": f"user-{user_id}@example.com",
                        "full_name": "User",
                        "avatar_url": None,
                        "preferences": {},
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    db.table('users').insert(user_data).execute()
                    logger.warning(f"Created missing user profile: {user_id}")
                    
        except Exception as e:
            logger.warning(f"Failed to ensure user exists: {e}")
            # Don't raise error as this is not critical for functionality

    async def _save_workflow_plan(self, plan: WorkflowPlan) -> None:
        """Save workflow plan to database."""
        try:
            db = await get_database()
            
            # Ensure user exists before saving workflow
            await self._ensure_user_exists(plan.user_id, db)
            
            plan_data = {
                "id": plan.id,
                "user_id": plan.user_id,
                "name": plan.name,
                "description": plan.description,
                "nodes": [node.dict() for node in plan.nodes],
                "edges": [edge.dict() for edge in plan.edges],
                "triggers": [trigger.dict() for trigger in plan.triggers],
                "status": plan.status.value,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            }
            
            # Upsert workflow plan
            db.table("workflows").upsert(
                plan_data,
                on_conflict="id"
            ).execute()
            
            logger.info(f"Saved workflow plan: {plan.name} ({plan.id})")
            
        except Exception as e:
            logger.error(f"Failed to save workflow plan: {e}")
            raise AgentError(f"Failed to save workflow plan: {e}")
    
    # Utility methods
    
    def _create_workflow_plan_from_data(self, plan_data: Dict[str, Any], user_id: str) -> WorkflowPlan:
        """Create WorkflowPlan object from structured data."""
        # Generate unique IDs
        plan_id = str(uuid.uuid4())
        
        # Create nodes
        nodes = []
        for i, node_data in enumerate(plan_data.get("nodes", [])):
            node = WorkflowNode(
                id=str(uuid.uuid4()),
                connector_name=node_data["connector_name"],
                parameters=node_data.get("parameters", {}),
                position=NodePosition(x=i * 200, y=100),  # Simple positioning
                dependencies=node_data.get("dependencies", [])
            )
            nodes.append(node)
        
        # Create a mapping of connector names to node IDs for dependency resolution
        connector_to_node = {node.connector_name: node.id for node in nodes}
        
        # Update node dependencies to use node IDs instead of connector names
        for node in nodes:
            resolved_dependencies = []
            for dep_name in node.dependencies:
                if dep_name in connector_to_node:
                    resolved_dependencies.append(connector_to_node[dep_name])
                else:
                    logger.warning(f"Dependency '{dep_name}' not found for node {node.id}")
            node.dependencies = resolved_dependencies
        
        # Create edges based on dependencies
        edges = []
        for node in nodes:
            for dep_node_id in node.dependencies:
                edge = WorkflowEdge(
                    id=str(uuid.uuid4()),
                    source=dep_node_id,
                    target=node.id
                )
                edges.append(edge)
        
        # Create triggers if specified
        triggers = []
        for trigger_data in plan_data.get("triggers", []):
            trigger = Trigger(
                id=str(uuid.uuid4()),
                type=trigger_data["type"],
                config=trigger_data.get("config", {}),  # Use empty dict as default
                enabled=trigger_data.get("enabled", True)
            )
            triggers.append(trigger)
        
        return WorkflowPlan(
            id=plan_id,
            user_id=user_id,
            name=plan_data.get("name", "Untitled Workflow"),
            description=plan_data.get("description", ""),
            nodes=nodes,
            edges=edges,
            triggers=triggers,
            status=WorkflowStatus.DRAFT
        )
    
    def _sort_nodes_by_dependencies(self, nodes: List[WorkflowNode]) -> List[WorkflowNode]:
        """Sort nodes by their dependencies for logical display order."""
        sorted_nodes = []
        remaining_nodes = nodes.copy()
        
        while remaining_nodes:
            # Find nodes with no unresolved dependencies
            ready_nodes = []
            for node in remaining_nodes:
                resolved_deps = [n.connector_name for n in sorted_nodes]
                if all(dep in resolved_deps or dep == node.connector_name for dep in node.dependencies):
                    ready_nodes.append(node)
            
            if not ready_nodes:
                # If no nodes are ready, just take the first one to avoid infinite loop
                ready_nodes = [remaining_nodes[0]]
            
            # Add ready nodes to sorted list
            for node in ready_nodes:
                sorted_nodes.append(node)
                remaining_nodes.remove(node)
        
        return sorted_nodes
    
    def _format_parameters(self, parameters: Dict[str, Any]) -> str:
        """Format parameters for display."""
        if not parameters:
            return "None"
        
        formatted = []
        for key, value in parameters.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            formatted.append(f"{key}={value}")
        
        return ", ".join(formatted)
    
    def _format_trigger_config(self, config: Dict[str, Any]) -> str:
        """Format trigger configuration for display."""
        if config.get("type") == "schedule":
            return f"Every {config.get('interval', 'hour')}"
        elif config.get("type") == "webhook":
            return f"Webhook URL: {config.get('url', 'TBD')}"
        else:
            return str(config)
    
    def _build_full_prompt_from_context(self, context: ConversationContext) -> str:
        """Build full prompt from conversation context."""
        user_messages = [msg.content for msg in context.messages if msg.role == "user"]
        return " ".join(user_messages)
    
    async def _validate_and_fix_parameters(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix workflow parameters."""
        fixed_nodes = []
        
        for node in plan_data.get("nodes", []):
            connector_name = node.get("connector_name")
            parameters = node.get("parameters", {})
            
            try:
                # Import the connector registry to get schema
                from app.connectors.registry import get_connector_registry
                registry = get_connector_registry()
                connector_class = registry.get_connector(connector_name)
                
                if connector_class:
                    # Get the schema from the connector
                    connector_instance = connector_class()
                    schema = connector_instance._define_schema()
                    
                    # Validate and fix parameters based on schema
                    fixed_params = self._fix_parameters_from_schema(parameters, schema)
                    parameters = fixed_params
                    
                    logger.info(f"Validated parameters for {connector_name}: {parameters}")
                else:
                    logger.warning(f"Connector {connector_name} not found in registry")
                    
            except Exception as e:
                logger.error(f"Failed to validate parameters for {connector_name}: {e}")
                # Keep original parameters if validation fails
            
            # Update node with fixed parameters
            fixed_node = {**node, "parameters": parameters}
            fixed_nodes.append(fixed_node)
        
        # Update plan data with fixed nodes
        plan_data["nodes"] = fixed_nodes
        logger.info(f"Validated workflow parameters: {json.dumps(plan_data, indent=2)}")
        
        return plan_data

    async def _validate_and_fix_parameters_with_context(
        self, 
        plan_data: Dict[str, Any], 
        user_prompt: str
    ) -> Dict[str, Any]:
        """Validate and fix workflow parameters with contextual reasoning."""
        
        # First apply basic schema validation
        plan_data = await self._validate_and_fix_parameters(plan_data)
        
        # Then apply contextual reasoning to fill missing critical parameters
        enhanced_plan = await self._apply_contextual_parameter_reasoning(plan_data, user_prompt)
        
        # Final validation pass to ensure all required parameters are still valid
        final_plan = await self._validate_and_fix_parameters(enhanced_plan)
        
        logger.info(f"Applied contextual reasoning - Final workflow parameters: {json.dumps(final_plan, indent=2)}")
        
        return final_plan
    
    def _fix_parameters_from_schema(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Fix parameters based on connector schema with contextual reasoning."""
        fixed_params = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Process each property in the schema
        for param_name, param_schema in properties.items():
            param_type = param_schema.get("type")
            param_default = param_schema.get("default")
            param_enum = param_schema.get("enum")
            
            # Get the current value or use default
            current_value = parameters.get(param_name, param_default)
            
            # Validate and fix the parameter
            if param_enum and current_value not in param_enum:
                # Use first enum value if current value is invalid
                current_value = param_enum[0] if param_enum else param_default
                
            elif param_type == "integer" and isinstance(current_value, str):
                try:
                    current_value = int(current_value)
                except ValueError:
                    current_value = param_default or 0
                    
            elif param_type == "number" and isinstance(current_value, str):
                try:
                    current_value = float(current_value)
                except ValueError:
                    current_value = param_default or 0.0
                    
            elif param_type == "boolean" and not isinstance(current_value, bool):
                current_value = bool(current_value) if current_value is not None else param_default
            
            # Include parameter if it has a value or is required
            if current_value is not None or param_name in required:
                fixed_params[param_name] = current_value
        
        # Ensure all required parameters are present
        for required_param in required:
            if required_param not in fixed_params:
                param_schema = properties.get(required_param, {})
                default_value = param_schema.get("default", "")
                fixed_params[required_param] = default_value
                logger.warning(f"Added missing required parameter {required_param} with default value")
        
        return fixed_params
    
    def _get_workflow_planning_function(self) -> Dict[str, Any]:
        """Get function definition for workflow planning."""
        return {
            "name": "generate_workflow_plan",
            "description": "Generate a structured workflow plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the workflow"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the workflow does"
                    },
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "connector_name": {
                                    "type": "string",
                                    "description": "Name of the connector to use"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Parameters for the connector"
                                },
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of connector names this node depends on"
                                }
                            },
                            "required": ["connector_name", "parameters"]
                        }
                    },
                    "triggers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["schedule", "webhook"]
                                },
                                "config": {
                                    "type": "object",
                                    "description": "Trigger configuration"
                                }
                            },
                            "required": ["type", "config"]
                        }
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of the workflow design choices"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1) in the plan"
                    }
                },
                "required": ["name", "description", "nodes", "reasoning"]
            }
        }
    
    # System prompts
    
    def _load_intent_recognition_prompt(self) -> str:
        """Load system prompt for intent recognition."""
        return """
You are an AI assistant specialized in understanding user intents for workflow automation.
Your task is to analyze user prompts and determine their intent, extract relevant entities, and identify if clarification is needed.

Analyze the user's prompt and respond with a JSON object containing:
- intent: The primary intent (e.g., "workflow_creation", "data_processing", "communication_automation")
- confidence: Confidence score (0-1)
- entities: Extracted entities like services, actions, schedules, etc.
- requires_clarification: Boolean indicating if more information is needed
- clarification_questions: List of specific questions to ask if clarification is needed

Focus on identifying:
1. What the user wants to automate
2. What services/platforms they want to integrate
3. What triggers or schedules they want
4. What data transformations are needed
5. What outputs they expect

If the prompt is vague or missing critical information, set requires_clarification to true and provide specific questions.

Example response:
{
  "intent": "workflow_creation",
  "confidence": 0.8,
  "entities": {
    "services": ["gmail", "google_sheets"],
    "actions": ["send_email", "update_spreadsheet"],
    "schedule": "daily"
  },
  "requires_clarification": false,
  "clarification_questions": []
}
"""
    
    def _load_planning_prompt(self) -> str:
        """Load system prompt for workflow planning."""
        return """
You are an AI workflow planner for PromptFlow AI. Your task is to create detailed, executable workflow plans based on user requests and available connectors.

CRITICAL: Each connector node MUST include ALL required parameters from its schema. Check the "required" field in each connector's parameter schema and ensure all required parameters are provided with appropriate values.

AVAILABLE CONNECTORS (DO NOT CREATE OR HALLUCINATE ANY OTHERS):
- **perplexity_search**: Web searches, finding blogs/articles/news. ALREADY INCLUDES CITATIONS/LINKS when return_citations=true
- **text_summarizer**: Summarize text content into concise summaries
- **gmail_connector**: Send/read emails, manage Gmail 
- **google_sheets**: Google Sheets operations
- **http_request**: Make HTTP API calls
- **webhook**: Handle webhook operations

CRITICAL CONNECTOR RULES:
1. ONLY use connectors from the above list - DO NOT create blog_link_extractor, summary_combiner, or ANY other fake connectors
2. Perplexity ALREADY provides links via citations when return_citations=true - no separate link extraction needed
3. Text Summarizer can summarize the full Perplexity result (content + citations)
4. Keep workflows simple and use existing connector capabilities

CONNECTOR USAGE GUIDELINES:
- **Perplexity Search**: Perfect for "find blogs/articles". Set return_citations=true to get links automatically
- **Text Summarizer**: Summarizes any text, including Perplexity results with citations
- **Gmail Connector**: ONLY for email operations, NOT for web searches

Guidelines:
1. Analyze the user's request to understand their automation goals
2. Select ONLY from the available connectors listed above
3. Design a logical flow that accomplishes the user's objectives using existing connectors
4. **ALWAYS include ALL required parameters for each connector**
5. Use realistic parameter values based on the user's request
6. Consider dependencies between steps and data flow
7. Include appropriate error handling and validation
8. Explain your reasoning for the design choices

When creating the workflow plan:
- Use ONLY connectors from the available list above
- Check each connector's parameter schema for required fields
- Provide realistic values for all required parameters
- Use parameter references ({{previous_node.field}}) for data flow between nodes
- Ensure proper sequencing of operations
- Include necessary authentication steps where needed
- Add appropriate triggers if mentioned
- Keep the plan focused and efficient

PARAMETER GUIDELINES:
- Check each connector's parameter_schema for required fields (marked in "required" array)
- Use appropriate default values from the schema where available
- For enum parameters, use only values from the "enum" array
- Use proper data types (string, number, boolean, array, object) as specified
- Reference previous node outputs using {{connector_name.result}} syntax for data flow

EXAMPLE WORKFLOW FOR "find blogs with links":
1. perplexity_search (with return_citations=true) → Gets content + citations
2. text_summarizer (input: {{perplexity_search.result}}) → Summarizes everything including links
3. gmail_connector → Sends the summary

The workflow should be practical, executable, and aligned with the user's stated goals.
Use the generate_workflow_plan function to provide a structured response.
"""
    


    def _summarize_conversation_context(self, context: ConversationContext) -> str:
        """Create a summary of the conversation context for AI analysis."""
        if not context.messages:
            return "No previous conversation"
        
        recent_messages = context.messages[-3:]  # Last 3 messages for context
        summary = "Recent conversation:\n"
        for msg in recent_messages:
            summary += f"- {msg.role}: {msg.content[:100]}...\n"
        
        return summary

    @property
    def modification_prompt(self) -> str:
        """System prompt for workflow plan modifications."""
        return """
        You are modifying an existing workflow plan based on user feedback.

        Guidelines:
        1. Make only the changes the user specifically requested
        2. Preserve the original workflow logic and structure where possible
        3. Ensure all connectors have proper parameters
        4. Maintain data flow between connectors
        5. If removing components, ensure dependencies are handled
        6. If adding components, integrate them logically into the flow
        
        When modifying:
        - Remove components completely when asked (don't just disable)
        - Update parameters accurately based on user requests
        - Adjust connector sequences if needed
        - Preserve user's original intent while making requested changes
        
        Generate a complete, valid workflow plan with the requested modifications.
"""

    async def _apply_contextual_parameter_reasoning(
        self, 
        plan_data: Dict[str, Any], 
        user_prompt: str
    ) -> Dict[str, Any]:
        """Apply intelligent contextual reasoning to fill parameters based on user needs."""
        try:
            # Use AI to analyze the user prompt and generate contextual parameters
            messages = [
                {
                    "role": "system",
                    "content": """
                    You are an expert at analyzing user requests and filling workflow parameters intelligently.
                    
                    Your task is to examine the user's request and the current workflow plan, then fill in 
                    missing or null parameters with appropriate values based on the user's actual needs.
                    
                    CRITICAL RULES:
                    1. Extract specific details from the user's request (email addresses, search queries, etc.)
                    2. Set up proper data flow between connectors using {{connector_name.result}} syntax
                    3. Fill required parameters that make logical sense for the user's goal
                    4. Keep existing valid parameters unchanged
                    5. Always use {{connector_name.result}} for data flow - the system automatically maps to correct field names
                    6. NEVER create self-references - a connector cannot reference its own result as input
                    
                    CONNECTOR CAPABILITIES:
                    - **perplexity_search**: Provides content AND citations/links when return_citations=true (no separate link extraction needed)
                    - **text_summarizer**: Can summarize any text including Perplexity results with citations
                    - **gmail_connector**: Sends emails with proper recipients, subjects, and body content
                    - **google_sheets**: Google Sheets operations
                    - **http_request**: Makes HTTP API calls  
                    - **webhook**: Handles webhook operations
                    
                    DATA FLOW LOGIC (CRITICAL):
                    - Each connector receives input from PREVIOUS connectors in the workflow, never from itself
                    - text_summarizer's "text" parameter should reference the PREVIOUS step's output (e.g., {{perplexity_search.result}})
                    - gmail_connector's "body" parameter should reference processed text (e.g., {{text_summarizer.result}})
                    - google_sheets connector should reference appropriate previous outputs
                    
                    WORKFLOW DEPENDENCY ANALYSIS:
                    1. Identify the dependency chain from the workflow structure
                    2. For each connector, determine what PREVIOUS connector it depends on
                    3. Fill input parameters with references to those PREVIOUS connectors
                    4. Ensure no connector references itself
                    
                    PARAMETER ANALYSIS APPROACH:
                    - Analyze each connector's role in the workflow based on its name and position
                    - For search/query connectors: Extract search terms from user request, set return_citations=true for links
                    - For processing connectors: Set up input from PREVIOUS connector using {{previous_connector.result}}
                    - For output connectors (email, notifications): Use processed data from PREVIOUS steps
                    - For communication connectors: Extract recipients, subjects, and content from user request
                    
                    DATA FLOW PRINCIPLES:
                    - Chain connector outputs using {{connector_name.result}} syntax
                    - Each connector should receive appropriate input from the PREVIOUS step in the dependency chain
                    - Final output should go to user-specified destination (email, file, etc.)
                    - Perplexity results already include citations when return_citations=true
                    
                    DYNAMIC PARAMETER FILLING:
                    - Extract concrete values from user request (emails, search terms, file names, etc.)
                    - Create descriptive subjects/titles based on the workflow purpose
                    - Set appropriate styles/formats based on user preferences or context
                    - Fill required fields with sensible defaults if not specified by user
                    - For Perplexity: Always set return_citations=true when user wants links
                    
                    EXAMPLE CORRECT DATA FLOW:
                    1. perplexity_search: query="user's search terms", return_citations=true
                    2. text_summarizer: text="{{perplexity_search.result}}" (gets input from step 1)
                    3. gmail_connector: body="{{text_summarizer.result}}" (gets input from step 2)
                    
                    Respond with the complete workflow plan JSON with all parameters properly filled based on the specific user request and workflow context.
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    User Request: {user_prompt}
                    
                    Current Workflow Plan:
                    {json.dumps(plan_data, indent=2)}
                    
                    Please analyze the user's request and fill in all missing/null parameters with 
                    contextually appropriate values that fulfill the user's actual needs.
                    
                    Return the complete workflow plan with intelligent parameter values.
                    """
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.2,
                max_tokens=2500
            )
            
            # Try to parse the response as JSON
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
                else:
                    # No closing ``` found, take everything after ```json
                    response_text = response_text[start:].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
                else:
                    # No closing ``` found, take everything after ```
                    response_text = response_text[start:].strip()
            
            # Additional cleanup: remove any trailing commas and fix common JSON issues
            response_text = response_text.replace(",\n}", "\n}")  # Remove trailing commas before }
            response_text = response_text.replace(",\n]", "\n]")  # Remove trailing commas before ]
            
            try:
                enhanced_plan = json.loads(response_text)
                logger.info(f"Applied contextual reasoning to parameters")
                return enhanced_plan
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing failed: {json_error}")
                logger.error(f"Problematic JSON text: {response_text[:500]}...")
                # Return original plan if JSON parsing fails
                return plan_data
            
        except Exception as e:
            logger.error(f"Failed to apply contextual parameter reasoning: {e}")
            return plan_data  # Return original plan if reasoning fails

    # New intent handler methods
    
    async def _handle_troubleshooting_request(self, message: str, context: ConversationContext) -> str:
        """Handle troubleshooting and support requests."""
        return (
            "I understand you're experiencing an issue. I'm here to help! "
            "Could you please provide more details about what went wrong? For example:\n\n"
            "• What were you trying to do?\n"
            "• What error or unexpected behavior did you see?\n"
            "• Would you like me to help you create a new workflow or fix an existing one?\n\n"
            "I'm ready to assist you with any workflow automation challenges you're facing."
        )
    
    async def _handle_conversation_management(self, message: str, context: ConversationContext) -> str:
        """Handle simple conversation responses like 'okay', 'thanks', etc."""
        message_lower = message.lower().strip()
        
        if message_lower in ['thanks', 'thank you', 'thx']:
            return "You're welcome! Is there anything else I can help you with?"
        elif message_lower in ['okay', 'ok', 'got it', 'understood']:
            return "Great! What would you like to do next?"
        elif message_lower in ['hello', 'hi', 'hey']:
            return "Hello! I'm here to help you create workflow automations. What would you like to automate today?"
        else:
            return "I'm here to help! What would you like to do next?"
    
    async def _handle_execution_request(self, message: str, context: ConversationContext) -> str:
        """Handle requests to execute workflows."""
        if context.current_plan:
            return (
                f"I understand you want to execute the workflow '{context.current_plan.name}'. "
                "To run your workflow, please:\n\n"
                "1. Make sure all connectors are properly authenticated\n"
                "2. Click the 'Execute' button in the interface\n"
                "3. Monitor the execution status\n\n"
                "The workflow will process automatically once started."
            )
        else:
            return (
                "It looks like you don't have an active workflow to execute. "
                "Would you like me to help you create a new workflow first?"
            )
    
    async def _handle_workflow_modification_request(self, message: str, context: ConversationContext) -> str:
        """Handle requests to modify existing workflows."""
        if context.current_plan:
            return (
                f"I can help you modify the workflow '{context.current_plan.name}'. "
                "Please let me know specifically what you'd like to change, for example:\n\n"
                "• Change email addresses or recipients\n"
                "• Modify search queries or parameters\n"
                "• Add or remove steps\n"
                "• Update triggers or schedules\n\n"
                "What specific changes would you like to make?"
            )
        else:
            return (
                "I don't see an active workflow to modify. "
                "Would you like me to help you create a new workflow instead?"
            )
    
    async def _handle_unclear_request(self, message: str, context: ConversationContext) -> str:
        """Handle unclear or ambiguous requests."""
        return (
            "I'm not entirely sure what you'd like me to help you with. "
            "Here's what I can do for you:\n\n"
            "🔧 **Create workflows** - Tell me what you want to automate\n"
            "❓ **Answer questions** - Ask about my capabilities or how things work\n"
            "⚡ **Execute workflows** - Run your existing automations\n"
            "✏️ **Modify workflows** - Change existing automation flows\n\n"
            "What would you like to do today?"
        )


# Global agent instance
conversational_agent: Optional[ConversationalAgent] = None


async def get_conversational_agent() -> ConversationalAgent:
    """Dependency to get conversational agent instance."""
    global conversational_agent
    
    if not conversational_agent:
        from app.services.rag import get_rag_retriever
        rag_retriever = await get_rag_retriever()
        conversational_agent = ConversationalAgent(rag_retriever)
        await conversational_agent.initialize()
    
    return conversational_agent


async def init_conversational_agent() -> None:
    """Initialize conversational agent on startup."""
    await get_conversational_agent()