"""
True ReAct Agent - Dynamic reasoning and acting with connectors.
No hardcoded logic, pure reasoning-based connector selection.
"""
import json
import logging
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI

from app.core.config import settings
from app.services.tool_registry import ToolRegistry
from app.services.workflow_planner import WorkflowPlannerAgent, PlanStep, WorkflowPlanSequence
from app.services.output_formatter import format_connector_output

logger = logging.getLogger(__name__)


class TrueReActAgent:
    """
    A true ReAct agent that dynamically reasons about connectors and builds workflows step-by-step.
    Inspired by String Alpha's iterative reasoning approach.
    """
    
    def __init__(self):
        self.tool_registry: Optional[ToolRegistry] = None
        self._client: Optional[AsyncAzureOpenAI] = None
        self.current_reasoning = ""
        self.workflow_steps = []
        self.planner_agent: Optional[WorkflowPlannerAgent] = None
        
    async def initialize(self, auth_context: Optional[Dict[str, str]] = None):
        """Initialize the ReAct agent with enhanced tool registry and AI client."""
        # Initialize enhanced tool registry (combines validation + AI features)
        from app.services.tool_registry import get_tool_registry
        self.tool_registry = await get_tool_registry(auth_context)
        
        # Dynamic tool loader is now integrated into the enhanced tool registry
        
        # Initialize AI client
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self._client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            logger.info("True ReAct agent initialized successfully with dynamic tool loader")
        else:
            logger.warning("Azure OpenAI not configured, agent will use fallback reasoning")
        
        # Initialize enhanced planner agent
        self.planner_agent = WorkflowPlannerAgent()
        await self.planner_agent.initialize(auth_context)
        logger.info("Enhanced planner agent integrated successfully")
    
    async def analyze_user_intent(self, request: str, session_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user intent using the intelligent conversation handler.
        """
        from app.services.intelligent_conversation_handler import get_conversation_handler
        
        conversation_handler = await get_conversation_handler()
        intent_analysis = await conversation_handler.analyze_intent(request, session_context)
        
        return {
            "intent": intent_analysis.intent.value,
            "confidence": intent_analysis.confidence,
            "reasoning": intent_analysis.reasoning,
            "extracted_info": intent_analysis.extracted_info,
            "needs_workflow": intent_analysis.intent.value == "workflow_creation"
        }
    
    async def process_user_request(self, request: str, user_id: str, session_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process user request using conversational workflow planning methodology.
        
        New Flow:
        1. Check if this is a response to a previous plan (approval/modification)
        2. If not, analyze request and create comprehensive plan using Tool Registry
        3. Present plan to user for approval/modification
        4. Execute approved plan task by task with reasoning
        5. Assemble final workflow
        """
        try:
            logger.info(f"🤔 Starting conversational workflow planning for: {request}")
            
            # Step 0: Check if this is a plan approval/modification response
            if session_context and session_context.get("awaiting_approval"):
                logger.info("🔄 Detected plan approval/modification response")
                return await self.handle_user_response(request, user_id, session_context.get("current_plan", {}))
            
            # Step 0.5: Check if this is a post-execution workflow modification request
            if session_context and session_context.get("executed_workflow"):
                logger.info("🔧 Detected post-execution workflow modification request")
                return await self.handle_workflow_modification(request, user_id, session_context)
            
            # Step 1: Check if this is an approval keyword without context
            approval_keywords = ['approve', 'approved', 'looks good', 'proceed', 'yes', 'ok', 'correct']
            if request.lower().strip() in approval_keywords:
                logger.info("⚠️  Approval keyword detected but no plan context available")
                return {
                    "success": False,
                    "error": "no_plan_context",
                    "message": "It looks like you're trying to approve a plan, but I don't have a current plan to approve. Please start by describing what workflow you'd like me to create.",
                    "reasoning_trace": ["Approval keyword detected without plan context"],
                    "is_conversational": True
                }
            
            # Step 2: Analyze user intent using intelligent conversation handler
            intent_analysis = await self.analyze_user_intent(request, session_context)
            
            logger.info(f"🧠 Intent analysis: {intent_analysis['intent']} (confidence: {intent_analysis['confidence']})")
            
            # Handle different intents appropriately
            if intent_analysis["intent"] in ["conversational", "greeting", "help_request", "workflow_question"]:
                from app.services.intelligent_conversation_handler import get_conversation_handler, ConversationIntent
                
                conversation_handler = await get_conversation_handler()
                intent_enum = ConversationIntent(intent_analysis["intent"])
                
                # Add extracted info to context for better response generation
                enhanced_context = session_context.copy() if session_context else {}
                enhanced_context["extracted_info"] = intent_analysis.get("extracted_info", {})
                
                response_message = await conversation_handler.generate_conversational_response(
                    intent_enum, request, enhanced_context
                )
                
                logger.info(f"💬 Conversational response generated for intent: {intent_analysis['intent']}")
                return {
                    "success": True,
                    "phase": "conversational",
                    "message": response_message,
                    "reasoning_trace": [f"Intent: {intent_analysis['intent']} - {intent_analysis['reasoning']}"],
                    "is_conversational": True,
                    "intent_analysis": intent_analysis
                }
            
            elif intent_analysis["intent"] == "approval_response":
                logger.info("✅ User is responding to a plan approval request")
                # This should be handled by the plan approval logic above
                return {
                    "success": False,
                    "error": "no_plan_context",
                    "message": "It looks like you're trying to approve a plan, but I don't have a current plan to approve. Please start by describing what workflow you'd like me to create.",
                    "reasoning_trace": ["Approval response detected but no plan context available"],
                    "is_conversational": True
                }
            
            elif not intent_analysis["needs_workflow"]:
                logger.info(f"💬 Request doesn't need workflow: {intent_analysis['intent']}")
                return {
                    "success": False,
                    "error": "no_workflow_needed",
                    "message": "I understand you're looking for help. Could you please describe what kind of workflow or automation you'd like me to create for you?",
                    "reasoning_trace": [f"Intent analysis: {intent_analysis['reasoning']}"],
                    "is_conversational": True,
                    "intent_analysis": intent_analysis
                }
            
            # Step 3: Validate workflow requirements before creating plan
            validation_result = await self._validate_workflow_requirements(request, intent_analysis)
            
            if not validation_result["is_valid"]:
                # Requirements are insufficient - ask for clarification
                from app.services.intelligent_conversation_handler import get_conversation_handler, ConversationIntent
                
                conversation_handler = await get_conversation_handler()
                clarification_response = await conversation_handler.generate_conversational_response(
                    ConversationIntent.HELP_REQUEST, request, {
                        "extracted_info": {
                            "needs_clarification": True,
                            "validation_issues": validation_result["issues"]
                        }
                    }
                )
                
                logger.info("❓ Workflow requirements insufficient - requesting clarification")
                return {
                    "success": True,
                    "phase": "conversational",
                    "message": clarification_response,
                    "reasoning_trace": [f"Validation failed: {validation_result['reason']}"],
                    "is_conversational": True,
                    "needs_clarification": True
                }
            
            # Step 4: Create comprehensive plan using Tool Registry
            logger.info("📋 Creating comprehensive workflow plan...")
            workflow_response = await self._create_comprehensive_plan(request, user_id)
            
            # _create_comprehensive_plan now returns a full response, so we can return it directly
            if workflow_response.get("success"):
                # Present plan to user for approval
                plan = workflow_response.get("plan", {})
                if plan:
                    await self._present_plan_to_user(plan, user_id)
                return workflow_response
            else:
                # If planning failed, return the error response
                return workflow_response
            
        except Exception as e:
            logger.error(f"Error in ReAct agent processing: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def reason_about_requirements(self, request: str) -> Dict[str, Any]:
        """Initial reasoning about what the user wants to accomplish."""
        
        # Get enhanced connector metadata from enhanced tool registry
        try:
            # Use enhanced tool registry's AI-powered tool selection
            relevant_tools = await self.tool_registry.get_tools_for_prompt(request, max_tools=15)
            available_connectors = relevant_tools
        except Exception as e:
            logger.warning(f"Failed to get AI-enhanced tools, falling back to basic metadata: {str(e)}")
            # Fallback to basic tool metadata
            available_connectors = await self.tool_registry.get_tool_metadata()
        
        # Format connector list for reasoning with enhanced metadata
        connector_list = self._format_enhanced_connector_list(available_connectors)
        
        reasoning_prompt = f"""
        I need to analyze this user request like String Alpha does - identify the apps and components required.
        
        USER REQUEST: "{request}"
        
        AVAILABLE CONNECTORS:
        {connector_list}
        
        Let me think step by step:
        1. What does the user want to accomplish?
        2. What sequence of actions is needed?
        3. Which connectors can help achieve each step?
        
        Respond with JSON containing:
        {{
            "reasoning": "My analysis of what the user wants...",
            "goal": "Main objective",
            "required_steps": ["step1", "step2", "step3"],
            "suggested_connectors": ["connector1", "connector2"]
        }}
        """
        
        if self._client:
            analysis = await self._ai_reason(reasoning_prompt)
        else:
            analysis = await self._fallback_reason(request, available_connectors)
        
        self.current_reasoning = analysis.get("reasoning", "")
        return analysis
    
    async def _validate_workflow_requirements(self, request: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that we have sufficient information to create a meaningful workflow.
        This prevents creating generic or incorrect workflows based on vague requests.
        """
        extracted_info = intent_analysis.get("extracted_info", {})
        
        # If we have high confidence from intent analysis, trust it
        confidence = intent_analysis.get("confidence", 0.0)
        if confidence >= 0.8:
            # High confidence means the intent detection was clear, proceed with workflow creation
            return {
                "is_valid": True,
                "reason": "High confidence intent detection indicates clear workflow request",
                "confidence": confidence
            }
        
        # Check specificity level (only if provided by AI analysis)
        specificity = extracted_info.get("specificity_level", "medium")  # Default to medium instead of low
        if specificity == "low" and confidence < 0.7:
            return {
                "is_valid": False,
                "reason": "Request lacks specific details about what to automate",
                "issues": ["vague_requirements"],
                "suggestions": ["Ask what specific task to automate", "Ask which tools to use", "Ask about desired outcome"]
            }
        
        # Check for mentioned tools or clear actions
        mentioned_tools = extracted_info.get("mentioned_tools", [])
        action_words = extracted_info.get("action_words", [])
        
        # Check if the request has clear actionable intent even without explicit tools
        clear_action_patterns = [
            r'\bmonitor\b.*\bwebsites?\b',
            r'\btrack\b.*\bchanges?\b',
            r'\bwatch\b.*\bfor\b',
            r'\bnotify\b.*\bwhen\b',
            r'\bsummarize\b.*\bemail',
            r'\bsync\b.*\bdata\b',
            r'\bbackup\b.*\bfiles?\b',
            r'\bgenerate\b.*\breports?\b',
            r'\bbuild\b.*\bautomation\b',
            r'\bsend\b.*\b(message|email)\b.*@',
            r'\bprocess\b.*\bdata\b',
            r'\bdata\s+processing\b',
            r'\bfind\b.*\bblog.*\band\s+send\b',
            r'\bsearch\b.*\band\s+email\b',
            r'\bget\b.*\band\s+send\s+to\b',
            r'\bfind\b.*\btop\s+\d+\b.*\band\s+send\b',
            r'\bsearch\b.*\btop\s+\d+\b.*\band\s+email\b'
        ]
        
        has_clear_action = any(re.search(pattern, request.lower()) for pattern in clear_action_patterns)
        
        # Check for email addresses (strong indicator of clear intent)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        has_email = bool(re.search(email_pattern, request))
        
        # If request has clear action pattern or email, it's likely valid
        if has_clear_action or has_email:
            return {
                "is_valid": True,
                "reason": "Request contains clear action patterns or specific destinations",
                "has_clear_action": has_clear_action,
                "has_email": has_email
            }
        
        if not mentioned_tools and not action_words and not has_clear_action:
            return {
                "is_valid": False,
                "reason": "No specific tools or actions mentioned",
                "issues": ["no_tools_specified", "no_actions_specified"],
                "suggestions": ["Ask which tools to connect", "Ask what actions to perform"]
            }
        
        # Check clarity assessment (only if provided by AI analysis)
        clarity = extracted_info.get("clarity_assessment", "clear")  # Default to clear instead of ambiguous
        if clarity == "ambiguous" and confidence < 0.7:
            return {
                "is_valid": False,
                "reason": "Request is ambiguous and could be misinterpreted",
                "issues": ["ambiguous_request"],
                "suggestions": ["Ask for clarification", "Provide examples", "Ask specific questions"]
            }
        
        # Additional validation: Check for potentially sensitive operations
        sensitive_keywords = ["delete", "remove", "destroy", "wipe", "clear", "reset"]
        if any(keyword in request.lower() for keyword in sensitive_keywords):
            return {
                "is_valid": False,
                "reason": "Request involves potentially sensitive operations that need explicit confirmation",
                "issues": ["sensitive_operations"],
                "suggestions": ["Ask for explicit confirmation", "Clarify scope of operation", "Confirm safety measures"]
            }
        
        # Validation passed
        return {
            "is_valid": True,
            "reason": "Request has sufficient detail and clarity",
            "confidence": intent_analysis.get("confidence", 0.7)
        }
    
    async def reason_next_step(self, initial_analysis: Dict[str, Any], current_steps: List[Dict[str, Any]], original_request: str) -> Optional[Dict[str, Any]]:
        """Reason about what the next step should be."""
        
        # Get enhanced connector metadata for next step reasoning
        try:
            # Use enhanced tool registry for context-aware tool selection
            context_prompt = f"{original_request} Current progress: {[step.get('action', '') for step in current_steps]}"
            relevant_tools = await self.tool_registry.get_tools_for_prompt(context_prompt, max_tools=10)
            available_connectors = relevant_tools
        except Exception as e:
            logger.warning(f"Failed to get context-aware tools: {str(e)}")
            # Fallback to basic tool metadata
            available_connectors = await self.tool_registry.get_tool_metadata()
        
        connector_names = [connector["name"] for connector in available_connectors]
        connector_list = ", ".join(connector_names)
        
        # Create enhanced connector descriptions
        connector_info = self._format_enhanced_connector_list(available_connectors)
        
        if not current_steps:
            # First step - what do we need to start with?
            reasoning_prompt = f"""
            WORKFLOW PLANNING - FIRST STEP SELECTION
            
            USER REQUEST: "{original_request}"
            INITIAL ANALYSIS: {initial_analysis.get('reasoning', '')}
            
            AVAILABLE CONNECTORS:
            {connector_info}
            
            TASK: Analyze the user's request and select the most appropriate connector for the FIRST step.
            
            Consider:
            1. What is the primary input/data source needed for this request?
            2. What type of action should happen first (data gathering, processing, communication)?
            3. Which connector's capabilities best match the initial requirement?
            4. What would be the logical starting point for this workflow?
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "connector_name": "exact_connector_name_from_available_list",
                "action_type": "search|process|output|communication|storage",
                "purpose": "clear description of what this first step accomplishes",
                "reasoning": "detailed explanation of why this connector is the optimal choice"
            }}
            """
        else:
            # Subsequent steps - what comes next?
            completed_steps = [f"Step {i+1}: {step['connector_name']} - {step['purpose']}" for i, step in enumerate(current_steps)]
            
            reasoning_prompt = f"""
            WORKFLOW PLANNING - NEXT STEP SELECTION
            
            ORIGINAL USER REQUEST: "{original_request}"
            
            COMPLETED STEPS:
            {chr(10).join(completed_steps)}
            
            AVAILABLE UNUSED CONNECTORS:
            {connector_info}
            
            TASK: Analyze what has been accomplished and determine the next logical step.
            
            Consider:
            1. What parts of the original request are still unfulfilled?
            2. What would be the most logical next action in this workflow sequence?
            3. Which available connector best serves that next requirement?
            4. Is there any data transformation, storage, or communication still needed?
            5. Are all user requirements fully satisfied, or is more work needed?
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "connector_name": "exact_connector_name_from_available_list_or_null_if_complete",
                "action_type": "search|process|output|communication|storage|complete",
                "purpose": "clear description of what this step accomplishes",
                "reasoning": "detailed explanation of why this is the next logical step"
            }}
            
            If ALL requirements from the original request are satisfied, use:
            {{"connector_name": null, "action_type": "complete", "purpose": "workflow complete", "reasoning": "all user requirements have been fully addressed"}}
            """
        
        if self._client:
            next_step = await self._ai_reason(reasoning_prompt)
            
            # Validate AI response with improved error handling
            if next_step and isinstance(next_step, dict):
                connector_name = next_step.get("connector_name")
                
                if connector_name:
                    # Check if the suggested connector exists and hasn't been used
                    available_names = [c["name"] for c in available_connectors]
                    used_names = [step['connector_name'] for step in current_steps]
                    
                    if (connector_name in available_names and connector_name not in used_names):
                        # Valid AI suggestion
                        logger.info(f"✅ AI suggested valid connector: {connector_name}")
                        return next_step
                    else:
                        logger.warning(f"AI suggested invalid/used connector: {connector_name}")
                        logger.info(f"Available: {available_names}")
                        logger.info(f"Used: {used_names}")
                elif connector_name is None and next_step.get("action_type") == "complete":
                    # AI determined workflow is complete
                    logger.info("🎯 AI determined workflow is complete")
                    return None
                elif next_step.get("action_type") == "fallback":
                    # AI explicitly requested fallback
                    logger.info("AI requested fallback reasoning")
                else:
                    logger.warning(f"AI response missing connector_name: {next_step}")
            else:
                logger.warning(f"Invalid AI response format: {type(next_step)} - {next_step}")
            
            # AI reasoning failed or was invalid, use intelligent fallback
            logger.info("Using intelligent fallback reasoning")
            next_step = await self._fallback_next_step(current_steps, original_request)
        else:
            # No AI client available, use fallback
            next_step = await self._fallback_next_step(current_steps, original_request)
        
        return next_step
    
    async def act_on_connector(self, action: Dict[str, Any], current_steps: List[Dict[str, Any]], original_request: str = "") -> Optional[Dict[str, Any]]:
        """Act on the reasoned action by configuring the appropriate connector."""
        
        connector_name = action.get("connector_name")
        if not connector_name or connector_name is None:
            if action.get("action_type") == "complete":
                logger.info("Workflow marked as complete by reasoning")
                return None
            logger.warning("No connector specified in action")
            return None
        
        # Get connector metadata
        available_connectors = await self.tool_registry.get_tool_metadata()
        connector_info = next((c for c in available_connectors if c["name"] == connector_name), None)
        
        if not connector_info:
            logger.warning(f"Connector {connector_name} not found in registry")
            return None
        
        # Add the original user request to the action for parameter extraction
        action_with_request = {**action, "user_request": original_request}
        
        # Configure connector parameters based on reasoning
        parameters = await self._configure_connector_parameters(
            connector_info, action_with_request, current_steps
        )
        
        # Determine dependencies
        dependencies = self._determine_step_dependencies(current_steps)
        
        return {
            "connector_name": connector_name,
            "purpose": action.get("purpose", f"Process using {connector_name}"),
            "parameters": parameters,
            "dependencies": dependencies,
            "step_number": len(current_steps) + 1
        }
    
    async def is_workflow_complete(self, analysis: Dict[str, Any], steps: List[Dict[str, Any]]) -> bool:
        """
        Intelligently determine if the workflow is complete using AI reasoning.
        This scales to any number of connectors and complex workflows.
        """
        if not steps:
            return False
        
        # Use AI to determine completion based on original request and current steps
        original_request = analysis.get('original_request', '')
        
        # Get available tools from Tool Registry dynamically
        available_tools = []
        tool_descriptions = {}
        
        try:
            if hasattr(self, 'tool_registry') and self.tool_registry:
                # Get all available tools and their metadata
                tools = await self.tool_registry.get_available_tools()
                for tool in tools:
                    tool_name = tool.name
                    available_tools.append(tool_name)
                    tool_descriptions[tool_name] = tool.description
                    
                # Also get metadata for better descriptions
                if hasattr(self.tool_registry, 'tool_metadata'):
                    for tool_name, metadata in self.tool_registry.tool_metadata.items():
                        if tool_name in tool_descriptions:
                            tool_descriptions[tool_name] = metadata.get('description', tool_descriptions[tool_name])
        except Exception as e:
            logger.warning(f"Could not get tools from registry: {e}")
            # Fallback to basic tool list if registry fails
            available_tools = ['perplexity_search', 'text_summarizer', 'youtube', 'google_drive', 'google_sheets', 'airtable', 'gmail_connector', 'notion']
        
        # Get completed connectors
        completed_connectors = [step['connector_name'] for step in steps]
        
        # Create dynamic tool list for AI analysis
        available_tools_list = "\n".join([
            f"- {tool}: {tool_descriptions.get(tool, 'Available connector')}" 
            for tool in available_tools
        ])
        
        # Extract explicit requirements from the user request
        request_lower = original_request.lower()
        explicit_requirements = []
        
        # Parse specific platform/service mentions
        platform_requirements = {
            'perplexity': 'perplexity_search',
            'youtube': 'youtube', 
            'google docs': 'google_drive',
            'drive': 'google_drive',
            'google sheets': 'google_sheets',
            'sheets': 'google_sheets',
            'airtable': 'airtable',
            'email': 'gmail_connector',
            'gmail': 'gmail_connector',
            'notion': 'notion'
        }
        
        for platform, connector in platform_requirements.items():
            if platform in request_lower:
                explicit_requirements.append(f"{connector} (for {platform})")
        
        # Check which requirements are satisfied
        satisfied_requirements = []
        missing_requirements = []
        
        for req in explicit_requirements:
            connector_name = req.split(' (')[0]
            if connector_name in completed_connectors:
                satisfied_requirements.append(req)
            else:
                missing_requirements.append(req)
        
        completion_prompt = f"""
        ORIGINAL USER REQUEST: "{original_request}"
        
        EXPLICIT REQUIREMENTS DETECTED:
        {chr(10).join([f"✅ {req}" for req in explicit_requirements])}
        
        REQUIREMENT SATISFACTION CHECK:
        Satisfied: {chr(10).join([f"✅ {req}" for req in satisfied_requirements]) if satisfied_requirements else "None"}
        Missing: {chr(10).join([f"❌ {req}" for req in missing_requirements]) if missing_requirements else "None"}
        
        WORKFLOW STEPS COMPLETED SO FAR ({len(steps)} steps):
        {chr(10).join([f"{i+1}. {step['connector_name']}: {step.get('purpose', 'No purpose')}" for i, step in enumerate(steps)])}
        
        COMPLETION ANALYSIS:
        
        CRITICAL RULE: If ANY requirement shows "❌ Missing" above, the workflow is INCOMPLETE.
        
        Requirements Found: {len(explicit_requirements)}
        Requirements Satisfied: {len(satisfied_requirements)}
        Requirements Missing: {len(missing_requirements)}
        
        RESPOND WITH EXACTLY THIS JSON FORMAT:
        {{"status": "COMPLETE", "reasoning": "All {len(explicit_requirements)} requirements satisfied"}} if ALL requirements are satisfied
        {{"status": "INCOMPLETE", "reasoning": "Missing {len(missing_requirements)} requirements: {', '.join([req.split(' (')[0] for req in missing_requirements])}"}} if ANY requirements are missing
        
        Be extremely strict - if even ONE requirement is missing, respond with INCOMPLETE.
        """
        
        try:
            if self._client:
                response = await self._ai_reason(completion_prompt)
                
                # Robust response parsing to handle different formats
                completion_status = None
                
                if isinstance(response, dict):
                    # Check for different possible response structures
                    if 'status' in response:
                        completion_status = response['status'].strip().upper()
                    elif 'content' in response:
                        content = response['content'].strip()
                        # Try to parse content as JSON first
                        try:
                            parsed_content = json.loads(content)
                            if isinstance(parsed_content, dict) and 'status' in parsed_content:
                                completion_status = parsed_content['status'].strip().upper()
                            else:
                                # Content might be plain text
                                completion_status = content.upper()
                        except json.JSONDecodeError:
                            # Content is plain text
                            completion_status = content.upper()
                    elif 'reasoning' in response:
                        # This is a fallback response, be conservative
                        completion_status = "INCOMPLETE"
                elif isinstance(response, str):
                    # Direct string response
                    try:
                        parsed_response = json.loads(response)
                        if isinstance(parsed_response, dict) and 'status' in parsed_response:
                            completion_status = parsed_response['status'].strip().upper()
                        else:
                            completion_status = response.strip().upper()
                    except json.JSONDecodeError:
                        completion_status = response.strip().upper()
                
                # INTELLIGENT OVERRIDE: Use AI reasoning to double-check completion
                if completion_status == 'COMPLETE':
                    # For complex requests, do additional validation
                    original_request = analysis.get('original_request', '').lower()
                    
                    # Count action words and complexity indicators
                    action_words = ['find', 'search', 'get', 'retrieve', 'summarize', 'process', 'analyze', 
                                  'save', 'store', 'log', 'email', 'send', 'create', 'upload', 'generate']
                    
                    action_count = sum(1 for word in action_words if word in original_request)
                    
                    # If request is complex (many actions) but few steps completed, be suspicious
                    if action_count >= 6 and len(steps) < 4:
                        logger.warning(f"🚨 Complex request ({action_count} actions) but only {len(steps)} steps - requesting AI re-analysis")
                        
                        # Ask AI to specifically justify the completion
                        justification_prompt = f"""
                        The user requested: "{analysis.get('original_request', '')}"
                        
                        Only {len(steps)} workflow steps were completed:
                        {chr(10).join([f"{i+1}. {step['connector_name']}" for i, step in enumerate(steps)])}
                        
                        You previously marked this as COMPLETE. Please justify:
                        
                        1. List every requirement from the user request
                        2. Explain how each requirement was satisfied by the completed steps
                        3. Confirm if ANY requirement is missing
                        
                        RESPOND WITH:
                        {{"status": "COMPLETE", "justification": "detailed explanation"}} if truly complete
                        {{"status": "INCOMPLETE", "missing": "what's still needed"}} if incomplete
                        """
                        
                        try:
                            justification_response = await self._ai_reason(justification_prompt)
                            if isinstance(justification_response, dict) and justification_response.get('status') == 'INCOMPLETE':
                                logger.info("🔄 AI re-analysis determined workflow is INCOMPLETE")
                                return False
                        except Exception as e:
                            logger.warning(f"AI justification failed: {e}")
                    
                    logger.info("🎯 AI determined workflow is COMPLETE")
                    return True
                        
                elif completion_status == 'INCOMPLETE':
                    logger.info("🔄 AI determined workflow is INCOMPLETE - more steps needed")
                    return False
                else:
                    logger.warning(f"AI gave unclear completion response: {completion_status}")
            
            # Intelligent fallback logic using request analysis
            original_request = analysis.get('original_request', '').lower()
            
            # Analyze request complexity dynamically
            action_indicators = ['find', 'search', 'get', 'retrieve', 'summarize', 'process', 'analyze', 
                               'save', 'store', 'log', 'email', 'send', 'create', 'upload', 'generate']
            
            platform_indicators = ['google', 'drive', 'docs', 'sheets', 'gmail', 'youtube', 'airtable', 
                                 'notion', 'perplexity', 'slack', 'discord', 'twitter', 'facebook']
            
            action_count = sum(1 for action in action_indicators if action in original_request)
            platform_count = sum(1 for platform in platform_indicators if platform in original_request)
            
            # For simple requests (few actions/platforms), fewer steps needed
            if action_count <= 3 and platform_count <= 2 and len(steps) >= 2:
                logger.info(f"Simple request detected ({action_count} actions, {platform_count} platforms) - {len(steps)} steps likely sufficient")
                return True
            
            # For complex requests, need more steps (but be more reasonable about platform count)
            if action_count >= 6 or platform_count >= 4:
                # Use action count as primary indicator, platform count as secondary
                min_steps_needed = max(action_count - 1, min(platform_count - 1, 8), 4)
                if len(steps) < min_steps_needed:
                    logger.info(f"Complex request detected ({action_count} actions, {platform_count} platforms) - need at least {min_steps_needed} steps, have {len(steps)}")
                    return False
            
            # Check if we have a reasonable workflow pattern
            connector_names = [step['connector_name'] for step in steps]
            
            # Improved pattern detection based on connector types and names
            has_input = any(any(keyword in name.lower() for keyword in ['search', 'find', 'get', 'retrieve', 'perplexity']) for name in connector_names)
            has_process = any(any(keyword in name.lower() for keyword in ['summarize', 'process', 'analyze', 'transform', 'text']) for name in connector_names)
            
            # Better output detection - include common output connectors
            output_connectors = ['drive', 'sheets', 'gmail', 'email', 'notion', 'airtable', 'slack', 'discord']
            has_output = any(
                any(keyword in name.lower() for keyword in ['save', 'store', 'send', 'create', 'upload']) or
                any(output_conn in name.lower() for output_conn in output_connectors)
                for name in connector_names
            )
            
            if has_input and has_process and has_output:
                logger.info(f"Fallback: Complete workflow pattern detected (input/process/output) with {len(steps)} steps")
                return True
            
            # Conservative fallback - continue workflow for incomplete patterns
            logger.info(f"Fallback: Workflow pattern incomplete or insufficient steps ({len(steps)}) - continuing")
            return False
            
        except Exception as e:
            logger.error(f"Error in workflow completion check: {e}")
            # Very conservative fallback - allow workflow to continue
            return False
    
    async def _create_comprehensive_plan(self, request: str, user_id: str) -> Dict[str, Any]:
        """
        Create a comprehensive workflow plan using enhanced planner agent with state machine modeling.
        This integrates advanced planning capabilities including tool chaining and sequence optimization.
        """
        try:
            logger.info("🧠 Using enhanced planner agent for comprehensive workflow planning")
            
            # Use the enhanced planner agent to create a sophisticated plan
            if self.planner_agent:
                try:
                    # Create workflow plan sequence using the advanced planner
                    plan_sequence = await self.planner_agent.create_workflow_plan(request, user_id)
                    
                    # Convert the advanced plan to the format expected by TrueReActAgent
                    enhanced_plan = await self._convert_planner_sequence_to_plan(plan_sequence)
                    
                    logger.info(f"✅ Enhanced planner created {len(enhanced_plan.get('tasks', []))} optimized tasks")
                    
                    # Wrap the enhanced plan in the expected response format
                    return {
                        "success": True,
                        "phase": "planning",
                        "plan": enhanced_plan,
                        "message": self._format_plan_presentation(enhanced_plan),
                        "reasoning_trace": self.get_reasoning_trace(),
                        "awaiting_approval": True
                    }
                    
                except Exception as e:
                    logger.warning(f"Enhanced planner failed, falling back to original method: {e}")
            
            # Fallback to original planning method if enhanced planner fails
            fallback_plan = await self._create_original_comprehensive_plan(request, user_id)
            
            # Wrap the fallback plan in the expected response format
            return {
                "success": True,
                "phase": "planning",
                "plan": fallback_plan,
                "message": self._format_plan_presentation(fallback_plan),
                "reasoning_trace": self.get_reasoning_trace(),
                "awaiting_approval": True
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive planning: {e}")
            # Final fallback
            available_tools = []
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tools = await self.tool_registry.get_available_tools()
                available_tools = [tool.name for tool in tools]
            
            final_fallback_plan = await self._create_fallback_plan(request, available_tools)
            
            # Wrap the final fallback plan in the expected response format
            return {
                "success": True,
                "phase": "planning",
                "plan": final_fallback_plan,
                "message": self._format_plan_presentation(final_fallback_plan),
                "reasoning_trace": self.get_reasoning_trace(),
                "awaiting_approval": True
            }
    
    async def _convert_planner_sequence_to_plan(self, plan_sequence: WorkflowPlanSequence) -> Dict[str, Any]:
        """
        Convert the enhanced planner's WorkflowPlanSequence to the format expected by TrueReActAgent.
        This bridges the advanced planner with the existing agent architecture.
        """
        tasks = []
        
        for step in plan_sequence.steps:
            task = {
                "task_number": len(tasks) + 1,
                "description": step.action_description,
                "suggested_tool": step.connector_name,
                "reasoning": f"Enhanced planner selected {step.connector_name} for optimal workflow execution",
                "inputs": ["data from previous tasks"] if step.dependencies else ["user request"],
                "outputs": [step.expected_output] if step.expected_output else ["processed data"],
                "dependencies": step.dependencies,
                "estimated_duration": step.estimated_duration,
                "parameters": step.parameters,
                "step_id": step.id
            }
            tasks.append(task)
        
        return {
            "summary": f"Enhanced workflow plan: {plan_sequence.get_sequence_description()}",
            "tasks": tasks,
            "data_flow": "Optimized sequence with intelligent tool chaining and dependency resolution",
            "estimated_steps": len(tasks),
            "original_request": plan_sequence.user_request,
            "user_id": plan_sequence.user_id,
            "created_at": plan_sequence.created_at.isoformat(),
            "plan_id": plan_sequence.id,
            "sequence_description": plan_sequence.get_sequence_description(),
            "enhanced_planning": True
        }
    
    async def _create_original_comprehensive_plan(self, request: str, user_id: str) -> Dict[str, Any]:
        """
        Original comprehensive planning method as fallback.
        """
        try:
            # Get available tools from Tool Registry
            available_tools = []
            tool_metadata = {}
            
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tools = await self.tool_registry.get_available_tools()
                for tool in tools:
                    available_tools.append(tool.name)
                    tool_metadata[tool.name] = {
                        'name': tool.name,
                        'description': tool.description,
                        'metadata': getattr(self.tool_registry, 'tool_metadata', {}).get(tool.name, {})
                    }
            
            # Create planning prompt using available tools
            planning_prompt = f"""
            USER REQUEST: "{request}"
            
            AVAILABLE TOOLS:
            {chr(10).join([f"- {name}: {tool_metadata[name]['description']}" for name in available_tools])}
            
            TASK: Create a comprehensive workflow plan to fulfill the user's request.
            
            ANALYSIS PROCESS:
            1. Break down the user request into logical tasks/steps
            2. For each task, identify which available tool(s) would be most suitable
            3. Consider data flow between tasks (outputs feeding into inputs)
            4. If you need to combine, transform, or process data between steps, use "code" as the suggested_tool
            5. Ensure all aspects of the user request are covered
            6. AVOID DUPLICATE TASKS - don't create multiple similar search/retrieval tasks
            7. OPTIMIZE FOR EFFICIENCY - use the minimum number of steps needed
            
            IMPORTANT GUIDELINES:
            - For data transformation/combination steps that require custom logic, always use "code" as the suggested_tool name
            - perplexity_search can provide both search results AND content in one step - don't create separate retrieval tasks
            - Avoid creating multiple perplexity_search tasks unless they serve different purposes
            - Focus on the essential workflow steps only
            
            DYNAMIC CONNECTOR ANALYSIS:
            - Analyze each connector's description and category to understand its capabilities
            - Use "code" connector for any data transformation, extraction, or combining tasks
            - Avoid creating duplicate tasks that serve the same purpose
            - Consider the data flow: what each connector produces and what the next connector needs
            
            RESPOND WITH THIS JSON FORMAT:
            {{
                "summary": "Brief description of what this workflow will accomplish",
                "tasks": [
                    {{
                        "task_number": 1,
                        "description": "What this task does",
                        "suggested_tool": "tool_name_or_code",
                        "reasoning": "Why this tool is suitable",
                        "inputs": ["what data this task needs"],
                        "outputs": ["what data this task produces"]
                    }}
                ],
                "data_flow": "How data flows between tasks",
                "estimated_steps": "number of steps"
            }}
            
            OPTIMIZE FOR EFFICIENCY - Use the minimum steps needed to accomplish the goal.
            """
            
            # Enhance the prompt with dynamic connector analysis
            enhanced_prompt = await self._add_dynamic_connector_insights(planning_prompt, available_tools, tool_metadata)
            
            # Get AI analysis
            if self._client:
                ai_response = await self._ai_reason(enhanced_prompt)
                
                if isinstance(ai_response, dict):
                    plan = ai_response
                elif isinstance(ai_response, str):
                    try:
                        plan = json.loads(ai_response)
                    except:
                        # Fallback to basic plan
                        plan = await self._create_fallback_plan(request, available_tools)
                else:
                    plan = await self._create_fallback_plan(request, available_tools)
            else:
                # No AI available, create fallback plan
                plan = await self._create_fallback_plan(request, available_tools)
            
            # Enhance plan with tool metadata
            for task in plan.get('tasks', []):
                tool_name = task.get('suggested_tool')
                if tool_name in tool_metadata:
                    task['tool_metadata'] = tool_metadata[tool_name]['metadata']
            
            plan['original_request'] = request
            plan['user_id'] = user_id
            plan['created_at'] = datetime.now().isoformat()
            
            return plan
            
        except Exception as e:
            logger.error(f"Error creating original comprehensive plan: {e}")
            return await self._create_fallback_plan(request, available_tools)
    
    async def _add_dynamic_connector_insights(self, base_prompt: str, available_tools: List[str], tool_metadata: Dict[str, Any]) -> str:
        """
        Dynamically analyze available connectors and add insights to the planning prompt.
        This replaces hardcoded connector knowledge with dynamic analysis.
        """
        try:
            # Categorize connectors by their capabilities
            search_connectors = []
            data_connectors = []
            ai_connectors = []
            communication_connectors = []
            transformation_connectors = []
            
            for tool_name in available_tools:
                if tool_name not in tool_metadata:
                    continue
                    
                metadata = tool_metadata[tool_name]
                description = metadata.get('description', '').lower()
                category = metadata.get('category', '').lower()
                
                # Dynamically categorize based on description and category
                if any(keyword in description for keyword in ['search', 'find', 'query', 'lookup']):
                    search_connectors.append(tool_name)
                elif any(keyword in description for keyword in ['summarize', 'analyze', 'process', 'ai', 'llm']):
                    ai_connectors.append(tool_name)
                elif any(keyword in description for keyword in ['email', 'send', 'message', 'notify', 'communication']):
                    communication_connectors.append(tool_name)
                elif any(keyword in description for keyword in ['data', 'database', 'storage', 'sheet', 'drive']):
                    data_connectors.append(tool_name)
                elif tool_name == 'code':
                    transformation_connectors.append(tool_name)
            
            # Build dynamic insights
            insights = []
            
            if search_connectors:
                insights.append(f"SEARCH CONNECTORS: {', '.join(search_connectors)} - Use for finding/retrieving information")
            
            if ai_connectors:
                insights.append(f"AI PROCESSING CONNECTORS: {', '.join(ai_connectors)} - Use for analysis, summarization, or AI processing")
            
            if communication_connectors:
                insights.append(f"COMMUNICATION CONNECTORS: {', '.join(communication_connectors)} - Use for sending/sharing results")
            
            if data_connectors:
                insights.append(f"DATA CONNECTORS: {', '.join(data_connectors)} - Use for storing or retrieving structured data")
            
            if transformation_connectors:
                insights.append(f"TRANSFORMATION CONNECTORS: {', '.join(transformation_connectors)} - Use for custom data processing, combining, or transformation")
            
            # Add insights to the prompt
            if insights:
                dynamic_insights = "\n            DYNAMIC CONNECTOR ANALYSIS:\n            " + "\n            ".join(insights)
                return base_prompt.replace("DYNAMIC CONNECTOR ANALYSIS:", f"DYNAMIC CONNECTOR ANALYSIS:{dynamic_insights}")
            
            return base_prompt
            
        except Exception as e:
            logger.error(f"Error adding dynamic connector insights: {e}")
            return base_prompt
    
    async def _create_fallback_plan(self, request: str, available_tools: List[str]) -> Dict[str, Any]:
        """
        Create a basic fallback plan when AI analysis fails.
        """
        # Simple keyword-based task identification
        request_lower = request.lower()
        tasks = []
        task_num = 1
        
        # Look for common patterns and match to available tools
        if any(word in request_lower for word in ['find', 'search', 'get']) and 'perplexity_search' in available_tools:
            tasks.append({
                "task_number": task_num,
                "description": "Search for information",
                "suggested_tool": "perplexity_search",
                "reasoning": "Request contains search-related keywords",
                "inputs": ["search query"],
                "outputs": ["search results"]
            })
            task_num += 1
        
        if any(word in request_lower for word in ['summarize', 'summary']) and 'text_summarizer' in available_tools:
            tasks.append({
                "task_number": task_num,
                "description": "Summarize content",
                "suggested_tool": "text_summarizer",
                "reasoning": "Request mentions summarization",
                "inputs": ["text to summarize"],
                "outputs": ["summary"]
            })
            task_num += 1
        
        # Add more tools based on keywords
        tool_keywords = {
            'youtube': ['youtube', 'video'],
            'google_drive': ['google docs', 'drive', 'save'],
            'google_sheets': ['sheets', 'spreadsheet', 'log'],
            'airtable': ['airtable', 'database'],
            'gmail_connector': ['email', 'gmail', 'send'],
            'notion': ['notion', 'page', 'document']
        }
        
        for tool_name, keywords in tool_keywords.items():
            if tool_name in available_tools and any(keyword in request_lower for keyword in keywords):
                tasks.append({
                    "task_number": task_num,
                    "description": f"Use {tool_name.replace('_', ' ')}",
                    "suggested_tool": tool_name,
                    "reasoning": f"Request mentions {tool_name.replace('_', ' ')} related keywords",
                    "inputs": ["data from previous tasks"],
                    "outputs": ["processed data"]
                })
                task_num += 1
        
        return {
            "summary": f"Workflow to handle: {request[:100]}...",
            "tasks": tasks,
            "data_flow": "Sequential execution with data passing between tasks",
            "estimated_steps": len(tasks)
        }
    
    async def _present_plan_to_user(self, plan: Dict[str, Any], user_id: str) -> None:
        """
        Present the workflow plan to the user via UI updates.
        """
        try:
            if hasattr(self, 'ui_manager') and self.ui_manager:
                plan_message = self._format_plan_presentation(plan)
                # Use the correct UI manager method to send plan updates
                await self.ui_manager.update_reasoning(user_id, plan_message, "plan_presentation")
                logger.info(f"📋 Presented refined plan to user {user_id}")
        except Exception as e:
            logger.error(f"Error presenting plan to user: {e}")
    
    def _format_plan_presentation(self, plan: Dict[str, Any]) -> str:
        """
        Format the workflow plan for user presentation with enhanced visualization.
        """
        message = f"📋 **Enhanced Workflow Plan**\n\n"
        
        # Show sequence visualization if available
        if plan.get('sequence_description'):
            message += f"**Sequence:** {plan['sequence_description']}\n\n"
        
        message += f"**Summary:** {plan.get('summary', 'Workflow automation')}\n\n"
        
        # Enhanced planning indicator
        if plan.get('enhanced_planning'):
            message += "🧠 **Enhanced AI Planning:** This plan uses advanced tool chaining and state machine modeling\n\n"
        
        message += f"**Planned Tasks ({len(plan.get('tasks', []))}):**\n"
        
        for task in plan.get('tasks', []):
            message += f"{task['task_number']}. **{task['description']}**\n"
            message += f"   - Tool: {task['suggested_tool']}\n"
            message += f"   - Purpose: {task['reasoning']}\n"
            
            # Show dependencies if available
            if task.get('dependencies'):
                message += f"   - Dependencies: {', '.join(task['dependencies'])}\n"
            
            # Show estimated duration if available
            if task.get('estimated_duration'):
                message += f"   - Duration: ~{task['estimated_duration']}s\n"
            
            message += "\n"
        
        message += f"**Data Flow:** {plan.get('data_flow', 'Sequential processing')}\n\n"
        
        # Show total estimated time if available
        total_duration = sum(task.get('estimated_duration', 5) for task in plan.get('tasks', []))
        if total_duration:
            message += f"**Estimated Total Time:** ~{total_duration}s\n\n"
        
        message += "**Please review this plan and respond with:**\n"
        message += "- 'approve' or 'looks good' to proceed\n"
        message += "- Describe any changes you'd like to make\n"
        
        return message
    
    async def handle_user_response(self, response: str, user_id: str, current_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user response to plan approval or modification requests with intelligent intent detection.
        """
        try:
            logger.info(f"🧠 Analyzing user response: '{response}'")
            
            # Use AI to intelligently determine user intent
            intent = await self._analyze_user_intent(response, current_plan)
            
            if intent["action"] == "approve":
                logger.info("✅ User approved the plan - proceeding with execution")
                return await self._execute_approved_enhanced_plan(current_plan, user_id)
            
            elif intent["action"] == "modify":
                logger.info(f"🔄 User requested changes: {intent['reasoning']}")
                refined_plan = await self._refine_plan_with_changes(current_plan, response, user_id)
                
                # Present refined plan
                await self._present_plan_to_user(refined_plan, user_id)
                
                return {
                    "success": True,
                    "phase": "planning",
                    "plan": refined_plan,
                    "message": self._format_plan_presentation(refined_plan),
                    "reasoning_trace": self.get_reasoning_trace(),
                    "awaiting_approval": True
                }
            
            elif intent["action"] == "clarify":
                logger.info(f"❓ User needs clarification: {intent['reasoning']}")
                return {
                    "success": True,
                    "phase": "planning",
                    "plan": current_plan,
                    "message": f"I understand you have questions about the plan. {intent['response']} Please let me know if you'd like to approve the current plan or make specific changes.",
                    "reasoning_trace": self.get_reasoning_trace(),
                    "awaiting_approval": True
                }
            
            else:
                # Fallback for unclear responses
                return {
                    "success": True,
                    "phase": "planning",
                    "plan": current_plan,
                    "message": "I'm not sure about your response. Please reply with 'approve' to proceed with the current plan, or describe what changes you'd like to make.",
                    "reasoning_trace": self.get_reasoning_trace(),
                    "awaiting_approval": True
                }
                
        except Exception as e:
            logger.error(f"❌ Error handling user response: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def handle_workflow_modification(self, request: str, user_id: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle post-execution workflow modification requests.
        This allows users to modify workflows even after they've been executed.
        """
        try:
            logger.info(f"🔧 Processing workflow modification request: {request}")
            
            executed_workflow = session_context.get("executed_workflow", {})
            original_plan = session_context.get("original_plan", {})
            
            if not executed_workflow:
                logger.warning("⚠️ No executed workflow found in session context")
                return {
                    "success": False,
                    "error": "no_executed_workflow",
                    "message": "I don't see an executed workflow to modify. Please create a workflow first.",
                    "reasoning_trace": self.get_reasoning_trace()
                }
            
            # Analyze the modification request using AI
            modification_analysis = await self._analyze_modification_request(request, executed_workflow, original_plan)
            
            if not modification_analysis.get("is_modification"):
                # This might be a new workflow request, not a modification
                logger.info("🆕 Request doesn't seem to be a workflow modification, checking if it needs a workflow")
                
                # Check if this is actually a conversational message using intelligent handler
                intent_analysis = await self.analyze_user_intent(request, session_context)
                
                if not intent_analysis["needs_workflow"]:
                    # Handle conversational requests using intelligent conversation handler
                    from app.services.intelligent_conversation_handler import get_conversation_handler, ConversationIntent
                    
                    conversation_handler = await get_conversation_handler()
                    intent_enum = ConversationIntent(intent_analysis["intent"])
                    
                    # Add extracted info to context for better response generation
                    enhanced_context = session_context.copy() if session_context else {}
                    enhanced_context["extracted_info"] = intent_analysis.get("extracted_info", {})
                    
                    response_message = await conversation_handler.generate_conversational_response(
                        intent_enum, request, enhanced_context
                    )
                    
                    logger.info(f"💬 Conversational response generated for intent: {intent_analysis['intent']}")
                    return {
                        "success": True,
                        "phase": "conversational",
                        "message": response_message,
                        "reasoning_trace": [f"Intent: {intent_analysis['intent']} - {intent_analysis['reasoning']}"],
                        "is_conversational": True,
                        "intent_analysis": intent_analysis
                    }
                
                # If it needs a workflow, create a comprehensive plan
                logger.info("🔧 Creating new workflow plan")
                return await self._create_comprehensive_plan(request, user_id)
            
            # Apply the modification automatically (no approval needed for post-execution changes)
            logger.info(f"🔍 Modification analysis result: {modification_analysis}")
            logger.info(f"🔍 Changes to apply: {modification_analysis.get('changes', [])}")
            
            modified_workflow = await self._apply_workflow_modification(
                executed_workflow, 
                original_plan,
                modification_analysis, 
                user_id
            )
            
            # Present the changes to the user
            change_summary = self._format_modification_summary(modification_analysis, modified_workflow)
            
            result = {
                "success": True,
                "phase": "modified",  # Use "modified" instead of "completed" to indicate this is a modification
                "message": change_summary,
                "workflow": modified_workflow,
                "reasoning_trace": self.get_reasoning_trace(),
                "modification_applied": True,
                "changes": modification_analysis.get("changes", [])
            }
            
            logger.info(f"🎉 Workflow modification completed successfully")
            logger.info(f"📋 Returning result with keys: {list(result.keys())}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error handling workflow modification: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def _analyze_user_intent(self, user_response: str, current_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to intelligently analyze user intent for plan responses.
        This replaces simple keyword matching with sophisticated natural language understanding.
        """
        try:
            # Create a comprehensive prompt for intent analysis
            intent_analysis_prompt = f"""
            TASK: Analyze the user's response to determine their intent regarding a workflow plan.
            
            USER RESPONSE: "{user_response}"
            
            CURRENT PLAN SUMMARY:
            - Tasks: {len(current_plan.get('tasks', []))} steps
            - Connectors: {', '.join([task.get('connector_name', 'unknown') for task in current_plan.get('tasks', [])])}
            
            INTENT ANALYSIS INSTRUCTIONS:
            Analyze the user's response and determine their primary intent. Consider:
            
            1. APPROVAL INTENT - User wants to proceed with the current plan:
               - Words like: "approve", "yes", "ok", "proceed", "looks good", "correct", "go ahead"
               - Phrases like: "that's perfect", "execute it", "run it", "do it"
               
            2. MODIFICATION INTENT - User wants to change the plan:
               - Words like: "modify", "change", "different", "instead", "add", "remove", "replace"
               - Specific requests: "remove X", "add Y", "change X to Y", "don't include Z"
               - Conditional statements: "but without X", "except for Y"
               
            3. CLARIFICATION INTENT - User has questions or needs more info:
               - Words like: "what", "how", "why", "explain", "clarify", "tell me more"
               - Questions about the plan or process
            
            CRITICAL RULES:
            - If the response contains BOTH approval and modification language, prioritize MODIFICATION
            - Look for specific change requests (remove, add, replace specific items)
            - Consider the overall context and tone of the message
            - Be very careful with ambiguous responses
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "action": "approve|modify|clarify|unclear",
                "confidence": 0.0-1.0,
                "reasoning": "detailed explanation of why you chose this intent",
                "specific_changes": ["list of specific changes requested if action is modify"],
                "response": "helpful response if clarification is needed"
            }}
            """
            
            if self._client:
                # Use AI for sophisticated intent analysis
                intent_result = await self._ai_reason(intent_analysis_prompt)
                
                if isinstance(intent_result, dict) and "action" in intent_result:
                    logger.info(f"🧠 AI Intent Analysis: {intent_result['action']} (confidence: {intent_result.get('confidence', 'unknown')})")
                    logger.info(f"🧠 AI Reasoning: {intent_result.get('reasoning', 'No reasoning provided')}")
                    return intent_result
                else:
                    logger.warning(f"AI intent analysis returned invalid format: {intent_result}")
            
            # Fallback to enhanced pattern matching if AI fails
            return await self._fallback_intent_analysis(user_response)
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            return await self._fallback_intent_analysis(user_response)
    
    async def _fallback_intent_analysis(self, user_response: str) -> Dict[str, Any]:
        """
        Enhanced fallback intent analysis with better pattern matching.
        """
        response_lower = user_response.lower().strip()
        
        # Enhanced modification detection
        modification_patterns = [
            r'\b(remove|delete|exclude|skip|without|drop)\b.*\b(webhook|connector|step|task)\b',
            r'\b(add|include|insert|append)\b.*\b(connector|step|task)\b',
            r'\b(change|modify|replace|swap|substitute)\b',
            r'\b(instead of|rather than|but not|except for)\b',
            r'\b(don\'t|do not|avoid|omit)\b.*\b(webhook|connector|step|task)\b'
        ]
        
        # Check for specific modification patterns
        import re
        for pattern in modification_patterns:
            if re.search(pattern, response_lower):
                return {
                    "action": "modify",
                    "confidence": 0.8,
                    "reasoning": f"Detected modification pattern: {pattern}",
                    "specific_changes": [user_response]
                }
        
        # Enhanced approval detection (only if no modification detected)
        approval_patterns = [
            r'^\s*(approve|yes|ok|proceed|correct|good|perfect)\s*$',
            r'\b(looks good|go ahead|execute|run it|do it)\b'
        ]
        
        for pattern in approval_patterns:
            if re.search(pattern, response_lower):
                return {
                    "action": "approve",
                    "confidence": 0.9,
                    "reasoning": f"Detected approval pattern: {pattern}"
                }
        
        # Question/clarification detection
        if any(word in response_lower for word in ['what', 'how', 'why', 'explain', '?']):
            return {
                "action": "clarify",
                "confidence": 0.7,
                "reasoning": "Detected question or request for clarification",
                "response": "I can explain more about the workflow plan."
            }
        
        # Default to unclear
        return {
            "action": "unclear",
            "confidence": 0.3,
            "reasoning": "Could not determine clear intent from user response"
        }
    
    async def _refine_plan_with_changes(self, current_plan: Dict[str, Any], user_feedback: str, user_id: str) -> Dict[str, Any]:
        """
        Refine the workflow plan based on user feedback.
        """
        try:
            logger.info(f"🔄 Starting plan refinement for user {user_id}")
            logger.info(f"📝 User feedback: {user_feedback}")
            
            # Get available tools for refinement
            available_tools = []
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tools = await self.tool_registry.get_available_tools()
                available_tools = [tool.name for tool in tools]
                logger.info(f"🔧 Available tools: {available_tools}")
            
            refinement_prompt = f"""
            ORIGINAL REQUEST: "{current_plan.get('original_request', '')}"
            
            CURRENT PLAN:
            {json.dumps(current_plan, indent=2)}
            
            USER FEEDBACK: "{user_feedback}"
            
            AVAILABLE TOOLS: {', '.join(available_tools)}
            
            TASK: Refine the workflow plan based on the user's feedback.
            
            CRITICAL INSTRUCTIONS:
            1. CAREFULLY analyze what the user wants to change
            2. If user says "remove webhook" or "remove the webhook", you MUST completely remove ALL tasks that use the "webhook" tool
            3. If user says "remove [tool_name]", completely remove ALL tasks using that specific tool
            4. Keep all other tasks that don't use the removed tool
            5. Update the data_flow to reflect the removed tasks
            6. Update estimated_steps to match the new number of tasks
            7. Update the summary to reflect the changes
            
            EXAMPLE: If user says "remove webhook", and current plan has 3 tasks where task 1 uses "webhook", 
            then the refined plan should only have tasks 2 and 3, with updated task numbers.
            
            RESPOND WITH THE SAME JSON FORMAT AS THE ORIGINAL PLAN:
            {{
                "summary": "Updated description reflecting the changes",
                "tasks": [only tasks that don't use the removed tool],
                "data_flow": "Updated data flow without removed components",
                "estimated_steps": "updated number matching task count"
            }}
            """
            
            if self._client:
                logger.info("🤖 Using AI for plan refinement")
                ai_response = await self._ai_reason(refinement_prompt)
                
                logger.info(f"🤖 AI response type: {type(ai_response)}")
                if isinstance(ai_response, dict):
                    logger.info(f"🤖 AI response keys: {list(ai_response.keys())}")
                
                if isinstance(ai_response, dict) and 'tasks' in ai_response:
                    refined_plan = ai_response
                    original_task_count = len(current_plan.get('tasks', []))
                    refined_task_count = len(refined_plan.get('tasks', []))
                    logger.info(f"✅ AI successfully refined the plan: {original_task_count} -> {refined_task_count} tasks")
                    
                    # Log which tools are in the refined plan
                    refined_tools = [task.get('suggested_tool') for task in refined_plan.get('tasks', [])]
                    logger.info(f"🔧 Refined plan tools: {refined_tools}")
                    
                elif isinstance(ai_response, str):
                    try:
                        refined_plan = json.loads(ai_response)
                        logger.info("✅ AI response parsed as JSON")
                    except Exception as e:
                        logger.warning(f"⚠️ AI response was not valid JSON: {e}, using fallback")
                        refined_plan = await self._simple_plan_refinement(current_plan, user_feedback, available_tools)
                else:
                    logger.warning(f"⚠️ AI response was not in expected format: {ai_response}, using fallback")
                    refined_plan = await self._simple_plan_refinement(current_plan, user_feedback, available_tools)
            else:
                logger.info("🔧 Using simple fallback refinement (no AI client)")
                refined_plan = await self._simple_plan_refinement(current_plan, user_feedback, available_tools)
            
            # Preserve metadata
            refined_plan['original_request'] = current_plan.get('original_request')
            refined_plan['user_id'] = user_id
            refined_plan['refined_at'] = datetime.now().isoformat()
            refined_plan['user_feedback'] = user_feedback
            
            logger.info(f"✅ Plan refinement completed. Tasks: {len(current_plan.get('tasks', []))} -> {len(refined_plan.get('tasks', []))}")
            return refined_plan
            
        except Exception as e:
            logger.error(f"❌ Error refining plan: {e}")
            return current_plan  # Return original plan if refinement fails
    
    async def _execute_approved_enhanced_plan(self, plan: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Execute the approved workflow plan using enhanced orchestration with state machine modeling.
        This method leverages the advanced workflow orchestrator for optimal execution.
        """
        try:
            logger.info(f"🚀 Executing enhanced plan with {len(plan.get('tasks', []))} tasks")
            
            # For now, use the original execution method which is working well
            # TODO: Fix advanced orchestrator signature mismatch
            return await self._execute_approved_plan_original(plan, user_id)
                
        except Exception as e:
            logger.error(f"Error executing enhanced plan: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def _execute_with_advanced_orchestrator(self, plan: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Execute plan using the advanced workflow orchestrator with state machine modeling.
        """
        try:
            logger.info("🧠 Using advanced workflow orchestrator for enhanced execution")
            
            # Get the planner's workflow plan if available
            if self.planner_agent and plan.get('plan_id'):
                workflow_plan = await self.planner_agent.get_approved_workflow_plan(plan['plan_id'])
                
                if workflow_plan:
                    # Use the unified workflow orchestrator
                    from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
                    orchestrator = UnifiedWorkflowOrchestrator()
                    
                    execution_result = await orchestrator.execute_workflow(
                        workflow_plan, 
                        user_id, 
                        auth_context={}
                    )
                    
                    # Mark plan as completed in planner
                    await self.planner_agent.mark_plan_completed(
                        plan['plan_id'], 
                        success=(execution_result.status.value == "completed")
                    )
                    
                    return {
                        "success": True,
                        "phase": "completed",
                        "execution_id": execution_result.execution_id,
                        "status": execution_result.status.value,
                        "workflow": execution_result.final_output,
                        "sequence_executed": plan.get('sequence_description', ''),
                        "enhanced_execution": True,
                        "reasoning_trace": self.get_reasoning_trace(),
                        "original_plan": plan
                    }
            
            # Fallback if advanced orchestrator fails
            logger.warning("Advanced orchestrator unavailable, falling back to original execution")
            return await self._execute_approved_plan_original(plan, user_id)
            
        except Exception as e:
            logger.error(f"Advanced orchestrator execution failed: {e}")
            return await self._execute_approved_plan_original(plan, user_id)
    
    async def _execute_approved_plan_original(self, plan: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Original execution method as fallback.
        """
        try:
            logger.info(f"🚀 Executing approved plan with {len(plan.get('tasks', []))} tasks")
            
            workflow_steps = []
            
            for task in plan.get('tasks', []):
                logger.info(f"⚡ Executing Task {task['task_number']}: {task['description']}")
                
                # Reason about this specific task
                task_result = await self._execute_planned_task(task, workflow_steps, plan)
                
                if task_result:
                    workflow_steps.append(task_result)
                    logger.info(f"✅ Completed Task {task['task_number']}: {task_result['connector_name']}")
                else:
                    logger.warning(f"❌ Task {task['task_number']} failed - continuing with next task")
            
            # Build final workflow
            final_workflow = await self.build_final_workflow(workflow_steps, plan.get('original_request', ''))
            
            return {
                "success": True,
                "phase": "completed",
                "workflow": final_workflow,
                "steps_completed": len(workflow_steps),
                "reasoning_trace": self.get_reasoning_trace(),
                "original_plan": plan
            }
            
        except Exception as e:
            logger.error(f"Error executing approved plan: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def _execute_planned_task(self, task: Dict[str, Any], previous_steps: List[Dict[str, Any]], plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single planned task with reasoning and parameter configuration.
        """
        try:
            tool_name = task.get('suggested_tool')
            
            if not tool_name:
                logger.warning(f"No tool specified for task: {task}")
                return None
            
            # Handle Code connector for data processing tasks
            if tool_name == 'code':
                logger.info(f"🔧 Configuring Code connector for data transformation: {task.get('description', 'Data processing')}")
                
                # Generate appropriate code based on the task description
                code_parameters = await self._generate_code_parameters(task, previous_steps, plan)
                
                step_result = {
                    "connector_name": "code",
                    "parameters": code_parameters,
                    "purpose": task.get('description', 'Code execution for data processing'),
                    "task_number": task.get('task_number'),
                    "reasoning": task.get('reasoning', 'Custom code execution for data transformation'),
                    "dependencies": self._extract_dependencies(code_parameters, previous_steps),
                    "step_number": len(previous_steps) + 1
                }
                
                return step_result
            
            # Create reasoning context for this task
            reasoning_context = {
                "task": task,
                "previous_steps": previous_steps,
                "original_request": plan.get('original_request', ''),
                "overall_plan": plan
            }
            
            # Configure parameters for this specific task
            logger.info(f"🤖 AI-configuring parameters for {tool_name} (Task {task['task_number']})")
            parameters = await self._configure_task_parameters(tool_name, reasoning_context)
            
            if not parameters:
                logger.warning(f"Failed to configure parameters for {tool_name}")
                return None
            
            # Create step result
            step_result = {
                "connector_name": tool_name,
                "parameters": parameters,
                "purpose": task.get('description', 'Planned task execution'),
                "task_number": task.get('task_number'),
                "reasoning": task.get('reasoning', ''),
                "dependencies": self._extract_dependencies(parameters, previous_steps),
                "step_number": len(previous_steps) + 1
            }
            
            return step_result
            
        except Exception as e:
            logger.error(f"Error executing planned task: {e}")
            return None
    
    async def _generate_ai_code_with_context(self, task: Dict[str, Any], previous_steps: List[Dict[str, Any]], plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate AI code using the enhanced Code connector AI generator with intelligent decision making."""
        try:
            from app.connectors.core.code_connector import CodeConnector
            from app.services.intelligent_code_decision import get_intelligent_code_decision
            
            # First, intelligently decide if code generation is actually needed
            decision_system = await get_intelligent_code_decision()
            
            user_request = task.get('description', '') or task.get('action', '')
            available_connectors = await self._get_available_connector_names()
            
            # Analyze if code is truly needed
            decision = await decision_system.should_generate_code(
                user_request, 
                available_connectors,
                {"task": task, "previous_steps": previous_steps, "plan": plan}
            )
            
            logger.info(f"Code generation decision: {decision}")
            
            # If code is not needed, return None to let other connectors handle it
            if not decision.get("needs_code", False):
                logger.info(f"Code generation not needed: {decision.get('reasoning')}")
                logger.info(f"Alternative connectors suggested: {decision.get('alternative_connectors')}")
                return None
            
            # If code is needed and confidence is high enough, generate it
            if decision.get("confidence", 0) < 0.6:
                logger.warning(f"Low confidence for code generation: {decision.get('confidence')}")
                return None
            
            # Create a Code connector instance
            code_connector = CodeConnector()
            
            # Build context from task and previous steps
            context = {
                "task": task,
                "previous_steps": previous_steps,
                "plan": plan,
                "workflow_context": True,
                "decision_analysis": decision
            }
            
            # Extract previous results for context
            if previous_steps:
                latest_step = previous_steps[-1]
                if "result" in latest_step:
                    context["previous_results"] = {"items": [latest_step["result"]]}
            
            # Generate AI-powered code
            ai_params = await code_connector.generate_ai_code(user_request, context)
            
            # Validate the generated code
            if ai_params.get("code"):
                validation = await decision_system.validate_generated_code(
                    ai_params["code"],
                    user_request,
                    ai_params.get("language", "javascript")
                )
                
                # If code doesn't address the request well, don't use it
                if not validation.get("addresses_request", False):
                    logger.warning(f"Generated code doesn't address request well: {validation}")
                    return None
                
                # Add validation results to metadata
                ai_params["_validation"] = validation
            
            # Add Code connector specific parameters
            ai_params.update({
                "timeout": 30,
                "safe_mode": True,
                "return_console_output": True,
                "_decision_reasoning": decision.get("reasoning"),
                "_code_complexity": decision.get("code_complexity"),
                "_risk_assessment": decision.get("risk_assessment")
            })
            
            logger.info(f"Generated AI code for task: {task.get('description', '')}")
            logger.info(f"AI confidence: {ai_params.get('_ai_confidence', 'unknown')}")
            logger.info(f"Decision confidence: {decision.get('confidence')}")
            
            return ai_params
            
        except Exception as e:
            logger.error(f"AI code generation failed: {str(e)}")
            return None
    
    async def _get_available_connector_names(self) -> List[str]:
        """Get list of available connector names."""
        try:
            if self.tool_registry:
                tools = await self.tool_registry.get_tool_metadata()
                return [tool.name for tool in tools]
            return []
        except Exception as e:
            logger.error(f"Failed to get connector names: {str(e)}")
            return ["gmail", "google_sheets", "google_drive", "notion", "airtable", "http", "perplexity"]
    
    async def _generate_code_parameters(self, task: Dict[str, Any], previous_steps: List[Dict[str, Any]], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate appropriate code parameters for data transformation tasks using AI reasoning."""
        try:
            task_description = task.get('description', '').lower()
            
            # Use enhanced AI code generator for Code connector
            if self._client:
                ai_code_result = await self._generate_ai_code_with_context(task, previous_steps, plan)
                if ai_code_result:
                    return ai_code_result
            
            # Use AI to generate custom code if available (fallback)
            if self._client:
                custom_code = await self._ai_generate_code(task, previous_steps, plan)
                if custom_code:
                    return custom_code
            
            # Fallback to pattern-based code generation
            if 'combine' in task_description or 'merge' in task_description:
                # Code for combining multiple items with robust data structure handling
                code = """// Combine multiple items into a single text block
// CRITICAL: Extract actual data from the main wrapper
let actualData = inputData.main || inputData;

// First, inspect the input data structure
console.log('Input data structure:', typeof actualData, Object.keys(actualData || {}));

let items = [];
let combinedText = '';

// Try to find array data in various possible structures
if (Array.isArray(actualData)) {
    items = actualData;
} else if (actualData && typeof actualData === 'object') {
    // Look for common array property names
    const possibleArrays = ['items', 'posts', 'results', 'data', 'content', 'blogs', 'articles'];
    for (const prop of possibleArrays) {
        if (Array.isArray(actualData[prop])) {
            items = actualData[prop];
            break;
        }
    }
    
    // If no array found, try to extract values
    if (items.length === 0) {
        const values = Object.values(actualData);
        for (const value of values) {
            if (Array.isArray(value)) {
                items = value;
                break;
            }
        }
    }
    
    // If still no array, treat the object itself as a single item
    if (items.length === 0) {
        items = [actualData];
    }
} else {
    // Handle primitive types
    items = [actualData];
}

// Process each item
items.forEach((item, index) => {
    if (item && typeof item === 'object') {
        // Try common text properties
        const title = item.title || item.name || item.subject || item.heading || `Item ${index + 1}`;
        const content = item.content || item.text || item.body || item.description || item.summary || JSON.stringify(item);
        
        combinedText += `${title}\\n`;
        combinedText += `${content}\\n\\n`;
    } else if (typeof item === 'string') {
        combinedText += `${item}\\n\\n`;
    } else {
        combinedText += `${JSON.stringify(item)}\\n\\n`;
    }
});

return {
    combined_text: combinedText.trim(),
    total_items: items.length,
    processed_at: new Date().toISOString(),
    input_structure: typeof actualData,
    found_items: items.length > 0
};"""
            
            elif 'transform' in task_description or 'process' in task_description:
                # Generic data transformation code
                code = """// Transform and process input data
// CRITICAL: Extract actual data from the main wrapper
let actualData = inputData.main || inputData;
const data = actualData;
let result = {};

// Process the data based on its structure
if (Array.isArray(data)) {
    result = {
        processed_items: data.map((item, index) => ({
            index: index + 1,
            data: item,
            processed: true
        })),
        total_count: data.length
    };
} else if (typeof data === 'object') {
    result = {
        ...data,
        processed: true,
        processed_at: new Date().toISOString()
    };
} else {
    result = {
        original_data: data,
        processed: true,
        processed_at: new Date().toISOString()
    };
}

return result;"""
            
            else:
                # Default passthrough with processing metadata
                code = """// Process input data and add metadata
// CRITICAL: Extract actual data from the main wrapper
let actualData = inputData.main || inputData;
const data = actualData;

return {
    data: data,
    processed: true,
    processed_at: new Date().toISOString(),
    step_info: 'Data processed by Code connector'
};"""
            
            # Validate and fix the fallback code as well
            validated_code = await self._validate_and_fix_javascript(code)
            
            return {
                "language": "javascript",
                "code": validated_code,
                "input_data": {},  # Will be populated with actual data during execution
                "timeout": 30,
                "safe_mode": True
            }
            
        except Exception as e:
            logger.error(f"Error generating code parameters: {e}")
            # Fallback to simple passthrough code
            fallback_code = "let actualData = inputData.main || inputData; return actualData;"
            validated_fallback = await self._validate_and_fix_javascript(fallback_code)
            
            return {
                "language": "javascript", 
                "code": validated_fallback,
                "input_data": {},
                "timeout": 30,
                "safe_mode": True
            }
    
    async def _ai_generate_code(self, task: Dict[str, Any], previous_steps: List[Dict[str, Any]], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to generate custom code for the specific task context."""
        try:
            # Get context about previous steps
            previous_context = ""
            if previous_steps:
                previous_context = "Previous workflow steps:\n"
                for i, step in enumerate(previous_steps, 1):
                    previous_context += f"{i}. {step.get('connector_name', 'Unknown')}: {step.get('purpose', 'No description')}\n"
            
            # Create AI prompt for code generation
            code_prompt = f"""
            TASK: Generate JavaScript code for a workflow data transformation step.
            
            TASK DESCRIPTION: {task.get('description', 'Process data')}
            TASK REASONING: {task.get('reasoning', 'Data transformation needed')}
            
            {previous_context}
            
            CONTEXT: This code will receive data from the previous step via 'inputData' variable.
            The code should process this data and return the result for the next step.
            
            CRITICAL DATA STRUCTURE: The inputData is wrapped in a 'main' key like this:
            inputData = {{ main: {{ actualData }} }}
            
            You MUST extract the actual data first:
            let actualData = inputData.main || inputData;
            
            GENERAL DATA PROCESSING: When processing data from any connector:
            - Inspect the actualData structure to understand what fields are available
            - Extract the relevant content based on the task requirements
            - Handle different data formats (objects, arrays, strings) gracefully
            - Focus on extracting meaningful content rather than metadata
            
            REQUIREMENTS:
            1. Use JavaScript (ES6+)
            2. ALWAYS extract actual data: let actualData = inputData.main || inputData;
            3. Work with actualData, not inputData directly
            4. Return a JavaScript object with the processed result
            5. Handle different data structures gracefully (arrays, objects, strings)
            6. Add helpful metadata like timestamps, counts, etc.
            7. IMPORTANT: Don't assume specific property names - inspect the data structure first
            
            EXAMPLE PATTERNS:
            - Extract data: let actualData = inputData.main || inputData;
            - Combining multiple items: First check what properties exist in actualData, then iterate
            - Data transformation: Inspect actualData structure, then modify/add fields
            - Text processing: Handle both string and object inputs from actualData
            
            CRITICAL: Always start with: let actualData = inputData.main || inputData;
            Then inspect the actualData structure before accessing properties.
            Use defensive programming - check if properties exist before using them.
            
            Generate ONLY the JavaScript code (no explanations, no markdown):
            """
            
            response = await self._ai_reason(code_prompt)
            
            # Handle both JSON and raw text responses
            generated_code = None
            if isinstance(response, dict):
                if 'content' in response:
                    generated_code = response['content'].strip()
                elif 'code' in response:
                    generated_code = response['code'].strip()
            elif isinstance(response, str):
                generated_code = response.strip()
            
            if generated_code:
                # Clean up the code (remove markdown formatting if present)
                if generated_code.startswith('```javascript'):
                    generated_code = generated_code.replace('```javascript', '').replace('```', '').strip()
                elif generated_code.startswith('```'):
                    generated_code = generated_code.replace('```', '').strip()
                
                # Validate and auto-correct the JavaScript code
                validated_code = await self._validate_and_fix_javascript(generated_code)
                
                # Validate that it looks like JavaScript code
                if validated_code and ('inputData' in validated_code or 'return' in validated_code):
                    return {
                        "language": "javascript",
                        "code": validated_code,
                        "input_data": {},
                        "timeout": 30,
                        "safe_mode": True
                    }
            
            return None  # Fall back to pattern-based generation
            
        except Exception as e:
            logger.error(f"AI code generation failed: {e}")
            return None  # Fall back to pattern-based generation
    
    async def _validate_and_fix_javascript(self, code: str) -> str:
        """
        Validate JavaScript code and automatically fix common syntax errors.
        This implements intelligent code correction similar to Cursor/Kiro AI.
        """
        try:
            # First, try basic syntax validation and auto-fixes
            fixed_code = await self._apply_common_js_fixes(code)
            
            # If we have AI available, use it for more sophisticated fixes
            if self._client:
                validated_code = await self._ai_validate_and_fix_code(fixed_code)
                if validated_code:
                    return validated_code
            
            return fixed_code
            
        except Exception as e:
            logger.error(f"Code validation failed: {e}")
            return code  # Return original code if validation fails
    
    async def _apply_common_js_fixes(self, code: str) -> str:
        """Apply common JavaScript syntax fixes."""
        fixed_code = code
        
        # Fix 1: If code uses 'await' but function isn't async, wrap in async function
        if 'await ' in fixed_code and 'async ' not in fixed_code:
            logger.info("🔧 Auto-fixing: Adding async wrapper for await usage")
            # Wrap the entire code in an async function
            fixed_code = f"""(async function() {{
{fixed_code}
}})();"""
        
        # Fix 2: Ensure proper return statement structure
        if 'return' not in fixed_code and not fixed_code.strip().endswith(';'):
            # If no return statement, assume the last expression should be returned
            lines = fixed_code.strip().split('\n')
            if lines and not lines[-1].strip().startswith('return'):
                last_line = lines[-1].strip()
                if last_line and not last_line.endswith(';'):
                    lines[-1] = f"return {last_line};"
                    fixed_code = '\n'.join(lines)
        
        # Fix 3: Handle common variable declaration issues
        fixed_code = fixed_code.replace('let actualData = inputData.main || inputData;', 
                                      'let actualData = (inputData && inputData.main) ? inputData.main : inputData;')
        
        # Fix 4: Ensure proper error handling for external API calls
        if 'fetch(' in fixed_code and 'try' not in fixed_code:
            logger.info("🔧 Auto-fixing: Adding error handling for fetch calls")
            # This is a more complex fix that would require parsing, so we'll handle it in AI validation
        
        return fixed_code
    
    async def _ai_validate_and_fix_code(self, code: str) -> str:
        """Use AI to validate and fix JavaScript code syntax errors."""
        try:
            validation_prompt = f"""
TASK: Validate and fix JavaScript code syntax errors.

ORIGINAL CODE:
```javascript
{code}
```

REQUIREMENTS:
1. Fix any syntax errors (missing async, improper await usage, etc.)
2. Ensure the code is valid JavaScript that can run in Node.js
3. Maintain the original functionality and logic
4. Add proper error handling for external API calls
5. Ensure variables are properly declared
6. Make sure the code handles the inputData structure correctly

COMMON ISSUES TO FIX:
- Using 'await' without 'async' function
- Missing variable declarations
- Improper error handling
- Syntax errors in loops or conditionals

Return ONLY the corrected JavaScript code (no explanations, no markdown):
"""
            
            response = await self._ai_reason(validation_prompt)
            
            if isinstance(response, dict) and 'content' in response:
                fixed_code = response['content'].strip()
            elif isinstance(response, str):
                fixed_code = response.strip()
            else:
                return code
            
            # Clean up any markdown formatting
            if fixed_code.startswith('```javascript'):
                fixed_code = fixed_code.replace('```javascript', '').replace('```', '').strip()
            elif fixed_code.startswith('```'):
                fixed_code = fixed_code.replace('```', '').strip()
            
            # Basic validation - ensure it still contains key elements
            if 'inputData' in fixed_code or 'return' in fixed_code:
                logger.info("🎉 AI successfully validated and fixed JavaScript code")
                return fixed_code
            else:
                logger.warning("AI validation removed essential code elements, using original")
                return code
                
        except Exception as e:
            logger.error(f"AI code validation failed: {e}")
            return code
    
    async def build_final_workflow(self, steps: List[Dict[str, Any]], request: str) -> Dict[str, Any]:
        """Build the final workflow from the completed steps."""
        
        return {
            "id": str(uuid.uuid4()),
            "name": f"ReAct Workflow - {request[:50]}...",
            "description": f"Dynamically created workflow: {request}",
            "steps": steps,
            "total_steps": len(steps),
            "created_by": "TrueReActAgent"
        }
    
    def get_reasoning_trace(self) -> List[str]:
        """Get the trace of reasoning steps for debugging/transparency."""
        return [self.current_reasoning]
    
    def _format_enhanced_connector_list(self, connectors: List[Dict[str, Any]]) -> str:
        """Format connectors with enhanced metadata for AI reasoning."""
        formatted_connectors = []
        
        for connector in connectors:
            name = connector.get("name", "")
            description = connector.get("description", "")
            category = connector.get("category", "")
            capabilities = connector.get("capabilities", [])
            use_cases = connector.get("use_cases", [])
            examples = connector.get("examples", [])
            relevance_score = connector.get("relevance_score", 0)
            
            # Build rich description
            parts = [f"**{name}**"]
            
            if category:
                parts.append(f"Category: {category}")
            
            if relevance_score > 0:
                parts.append(f"Relevance: {relevance_score}/10")
            
            if capabilities:
                parts.append(f"Capabilities: {', '.join(capabilities)}")
            
            if description:
                # Truncate long descriptions
                desc = description[:200] + "..." if len(description) > 200 else description
                parts.append(f"Description: {desc}")
            
            if use_cases:
                parts.append(f"Use Cases: {', '.join(use_cases[:3])}")
            
            if examples:
                parts.append(f"Examples: {'; '.join(examples[:2])}")
            
            formatted_connectors.append("\n  ".join(parts))
        
        return "\n\n".join(formatted_connectors)
    
    async def _analyze_connector_semantic_fit(self, connector: Dict[str, Any], user_intent: str, context: str = "") -> float:
        """
        Analyze how well a connector semantically fits the user's intent.
        Returns a score from 0.0 to 1.0 indicating relevance.
        This enables intelligent connector selection without hardcoding.
        """
        try:
            if not self._client:
                return 0.5  # Neutral score if no AI available
            
            semantic_prompt = f"""
            USER INTENT: "{user_intent}"
            CONTEXT: {context}
            
            CONNECTOR ANALYSIS:
            Name: {connector.get('name', '')}
            Category: {connector.get('category', '')}
            Description: {connector.get('description', '')}
            Capabilities: {connector.get('capabilities', [])}
            
            TASK: Rate how well this connector matches the user's intent and context.
            
            Consider:
            1. Does the connector's purpose align with what the user wants?
            2. Are the connector's capabilities relevant to the user's needs?
            3. Does the connector fit logically in the current workflow context?
            4. Would using this connector move the workflow closer to fulfilling the user's request?
            
            RESPOND WITH ONLY A NUMBER between 0.0 and 1.0:
            - 0.0 = Completely irrelevant
            - 0.5 = Somewhat relevant
            - 1.0 = Perfect match
            """
            
            response = await self._ai_reason(semantic_prompt)
            score_text = response.get('content', '0.5').strip()
            
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))  # Clamp to valid range
            except ValueError:
                return 0.5  # Default if parsing fails
                
        except Exception as e:
            logger.error(f"Error in semantic fit analysis: {e}")
            return 0.5
    
    # Helper methods
    
    def _format_connector_list(self, connectors: List[Dict[str, Any]]) -> str:
        """Format connector list for AI reasoning."""
        formatted = []
        for connector in connectors:
            formatted.append(f"- {connector['name']}: {connector.get('description', 'No description')}")
        return "\n".join(formatted)
    
    async def _ai_reason(self, prompt: str) -> Dict[str, Any]:
        """Use AI to reason about the prompt with improved error handling."""
        try:
            messages = [
                {"role": "system", "content": "You are a ReAct agent that reasons step by step about workflow automation. You MUST respond with valid JSON only. No explanations, no markdown, just pure JSON. Always follow the exact JSON format requested in the prompt."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up common AI response issues
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Try to parse as JSON first
            try:
                parsed_json = json.loads(content)
                return parsed_json
            except json.JSONDecodeError:
                logger.warning(f"AI returned non-JSON response: {content[:200]}...")
                
                # Try to extract JSON from the response if it's embedded
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json.loads(json_match.group())
                        logger.info("Successfully extracted JSON from AI response")
                        return extracted_json
                    except json.JSONDecodeError:
                        pass
                
                # If all JSON parsing fails, return structured fallback
                return {"content": content, "action_type": "fallback", "reasoning": "AI response was not valid JSON"}
                
        except Exception as e:
            logger.error(f"AI reasoning failed: {e}")
            return {"reasoning": "AI reasoning unavailable", "action_type": "fallback", "error": str(e)}
    
    async def _fallback_reason(self, request: str, connectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback reasoning when AI is not available."""
        return {
            "reasoning": f"Analyzing request: {request}. Available connectors: {len(connectors)}",
            "goal": "Build workflow step by step",
            "approach": "Use available connectors to fulfill user request"
        }
    
    async def _fallback_next_step(self, current_steps: List[Dict[str, Any]], request: str) -> Dict[str, Any]:
        """
        Intelligent AI-driven fallback for determining next step.
        This method scales to hundreds of connectors without hardcoding.
        """
        try:
            # Get all available connectors dynamically
            available_connectors = await self.tool_registry.get_tool_metadata()
            used_connectors = [step['connector_name'] for step in current_steps]
            
            # Filter out already used connectors
            unused_connectors = [
                connector for connector in available_connectors 
                if connector['name'] not in used_connectors
            ]
            
            if not unused_connectors:
                return None  # No more connectors available
            
            # Create detailed connector information for AI reasoning
            connector_info = []
            for connector in unused_connectors:
                info = f"- {connector['name']}: {connector.get('description', 'No description')}"
                if connector.get('category'):
                    info += f" (Category: {connector['category']})"
                if connector.get('capabilities'):
                    info += f" - Capabilities: {', '.join(connector['capabilities'])}"
                connector_info.append(info)
            
            # Create context about completed steps
            completed_context = ""
            if current_steps:
                completed_context = "Steps completed so far:\n"
                for i, step in enumerate(current_steps, 1):
                    completed_context += f"{i}. {step['connector_name']}: {step.get('purpose', 'No purpose')}\n"
            
            # AI-driven next step selection
            fallback_prompt = f"""
            ORIGINAL USER REQUEST: "{request}"
            
            {completed_context}
            
            Available unused connectors:
            {chr(10).join(connector_info)}
            
            TASK: Analyze the original request and determine what the next logical step should be.
            
            Consider:
            1. What parts of the original request haven't been addressed yet?
            2. What would be the most logical next action in this workflow?
            3. Which connector would best serve that next action?
            4. Is the workflow actually complete, or are there still requirements to fulfill?
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "connector_name": "exact_connector_name_from_available_list_or_null_if_complete",
                "action_type": "search|process|output|storage|communication|complete",
                "purpose": "clear description of what this step accomplishes",
                "reasoning": "why this connector is the best choice for the next step"
            }}
            
            If the workflow is complete and no more steps are needed, use:
            {{"connector_name": null, "action_type": "complete", "purpose": "workflow complete", "reasoning": "all requirements fulfilled"}}
            """
            
            # Use AI reasoning if available
            if self._client:
                response = await self._ai_reason(fallback_prompt)
                
                # Validate the AI response
                if (response.get('connector_name') and 
                    response['connector_name'] in [c['name'] for c in unused_connectors]):
                    return {
                        "action_type": response.get('action_type', 'process'),
                        "connector_name": response['connector_name'],
                        "purpose": response.get('purpose', 'AI-determined next step'),
                        "user_request": request,
                        "reasoning": response.get('reasoning', 'AI-selected connector')
                    }
                elif response.get('connector_name') is None:
                    # AI determined workflow is complete
                    return None
            
            # Ultimate fallback: return None (workflow complete)
            logger.warning("Fallback reasoning failed, marking workflow as complete")
            return None
            
        except Exception as e:
            logger.error(f"Error in fallback next step: {e}")
            return None
    
    async def _configure_connector_parameters(self, connector_info: Dict[str, Any], action: Dict[str, Any], current_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Intelligently configure parameters for ANY connector using AI reasoning.
        This scales to hundreds of connectors without hardcoding each one.
        """
        schema = connector_info.get("parameter_schema", {})
        properties = schema.get("properties", {})
        connector_name = connector_info.get("name", "")
        user_request = action.get("user_request", "")
        
        logger.info(f"🤖 AI-configuring parameters for {connector_name}")
        logger.info(f"📝 User request being processed: '{user_request}'")
        
        # Use AI to intelligently extract parameters if available
        if self._client:
            parameters = await self._ai_configure_parameters(
                connector_name, connector_info, user_request, current_steps
            )
        else:
            # Fallback to pattern-based extraction
            parameters = await self._pattern_based_parameter_extraction(
                connector_name, properties, user_request, current_steps
            )
        
        logger.info(f"✅ AI-configured parameters for {connector_name}: {parameters}")
        return parameters
    
    async def _ai_configure_parameters(self, connector_name: str, connector_info: Dict[str, Any], user_request: str, current_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use AI to intelligently configure connector parameters.
        This works for ANY connector by understanding the schema and user intent.
        """
        try:
            schema = connector_info.get("parameter_schema", {})
            properties = schema.get("properties", {})
            description = connector_info.get("description", "")
            
            # Build context about previous steps
            previous_steps_context = ""
            if current_steps:
                previous_steps_context = "Previous workflow steps:\n"
                for i, step in enumerate(current_steps, 1):
                    previous_steps_context += f"{i}. {step['connector_name']}: {step.get('purpose', 'No description')}\n"
            
            # Create AI prompt for parameter extraction
            prompt = f"""
            I need to configure parameters for the "{connector_name}" connector based on a user's request.
            
            CONNECTOR INFO:
            Name: {connector_name}
            Description: {description}
            
            PARAMETER SCHEMA:
            {json.dumps(properties, indent=2)}
            
            USER REQUEST:
            "{user_request}"
            
            {previous_steps_context}
            
            TASK: Extract and configure the connector parameters from the user request. 
            
            RULES:
            1. CAREFULLY extract specific values mentioned in the user request:
               - Email addresses (like shreyashbarca10@gmail.com) → use for "to", "recipient", "email" fields
               - URLs, search terms, file names, etc.
               - Numbers, dates, and other specific data
            2. For data flow parameters (like "text", "content", "input"), reference previous steps using format: "{{connector_name.result}}" where connector_name is the actual name
            3. Set appropriate default values for optional parameters
            4. If a parameter isn't mentioned in the request, use intelligent defaults based on context
            5. For action/method parameters, choose the most appropriate option from available enum values
            6. ALWAYS include required parameters - check the schema for required fields
            
            EXAMPLES OF DATA FLOW REFERENCES:
            - If previous step was "perplexity_search", use: "{{perplexity_search.result}}"
            - If previous step was "text_summarizer", use: "{{text_summarizer.result}}"
            
            EXAMPLES OF PARAMETER EXTRACTION:
            - User says "send to john@example.com" → "to": "john@example.com"
            - User says "search for Python tutorials" → "query": "Python tutorials"
            - User says "summarize the content" → "text": "{{previous_step.result}}"
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "parameter_name": "extracted_or_default_value",
                "another_parameter": "value"
            }}
            """
            
            response = await self._ai_reason(prompt)
            logger.info(f"🧠 AI response for {connector_name}: {response}")
            
            # If AI returned valid JSON parameters, use them
            if isinstance(response, dict) and any(key in properties for key in response.keys()):
                logger.info(f"✅ Using AI-extracted parameters for {connector_name}")
                return response
            else:
                logger.warning(f"❌ AI parameter extraction failed for {connector_name}, falling back to pattern-based")
                logger.warning(f"AI response type: {type(response)}, content: {response}")
                return await self._pattern_based_parameter_extraction(connector_name, properties, user_request, current_steps)
                
        except Exception as e:
            logger.error(f"AI parameter configuration failed: {e}")
            return await self._pattern_based_parameter_extraction(connector_name, properties, user_request, current_steps)
    
    async def _pattern_based_parameter_extraction(self, connector_name: str, properties: Dict[str, Any], user_request: str, current_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback pattern-based parameter extraction that works for any connector.
        Uses intelligent pattern matching and schema analysis.
        """
        parameters = {}
        
        # Common patterns that work across all connectors
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'url': r'https?://[^\s]+',
            'phone': r'\+?[\d\s\-\(\)]{10,}',
            'number': r'\b\d+\b',
            'quoted_text': r'"([^"]*)"',
            'parenthetical': r'\(([^)]*)\)'
        }
        
        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string")
            param_enum = param_def.get("enum", [])
            param_default = param_def.get("default")
            param_description = param_def.get("description", "").lower()
            
            # Smart parameter extraction based on parameter name and type
            value = None
            
            # 1. Email parameters
            if any(keyword in param_name.lower() for keyword in ['email', 'to', 'from', 'recipient']):
                email_match = re.search(patterns['email'], user_request)
                if email_match:
                    value = email_match.group()
                    logger.info(f"📧 Extracted email '{value}' for parameter '{param_name}'")
            
            # 2. URL parameters
            elif any(keyword in param_name.lower() for keyword in ['url', 'endpoint', 'link', 'href']):
                url_match = re.search(patterns['url'], user_request)
                if url_match:
                    value = url_match.group()
            
            # 3. Query/search parameters
            elif any(keyword in param_name.lower() for keyword in ['query', 'search', 'term', 'keyword']):
                # Extract search intent from user request
                if 'find' in user_request.lower() or 'search' in user_request.lower():
                    # Try to extract what they want to search for
                    search_patterns = [
                        r'find\s+(.+?)(?:\s+using|\s+with|\s+via|$)',
                        r'search\s+for\s+(.+?)(?:\s+using|\s+with|\s+via|$)',
                        r'get\s+(.+?)(?:\s+from|\s+using|$)'
                    ]
                    for pattern in search_patterns:
                        match = re.search(pattern, user_request, re.IGNORECASE)
                        if match:
                            value = match.group(1).strip()
                            logger.info(f"🔍 Extracted search query '{value}' for parameter '{param_name}'")
                            break
                    if not value:
                        value = user_request  # Fallback to full request
                        logger.info(f"🔍 Using full request as search query for parameter '{param_name}'")
            
            # 4. Action/method parameters with enum values
            elif param_enum and param_name.lower() in ['action', 'method', 'operation', 'type']:
                # Find the most relevant action based on user request
                request_lower = user_request.lower()
                action_keywords = {
                    'send': ['send', 'email', 'mail', 'deliver'],
                    'get': ['get', 'fetch', 'retrieve', 'read', 'find'],
                    'post': ['post', 'create', 'add', 'insert'],
                    'put': ['put', 'update', 'modify', 'change'],
                    'delete': ['delete', 'remove', 'clear'],
                    'search': ['search', 'find', 'query', 'look'],
                    'list': ['list', 'show', 'display'],
                    'write': ['write', 'save', 'store'],
                    'read': ['read', 'get', 'fetch']
                }
                
                for enum_value in param_enum:
                    enum_lower = enum_value.lower()
                    if enum_lower in request_lower:
                        value = enum_value
                        break
                    # Check action keywords
                    for action, keywords in action_keywords.items():
                        if action == enum_lower and any(kw in request_lower for kw in keywords):
                            value = enum_value
                            break
                    if value:
                        break
                
                # Default to first enum value if nothing matches
                if not value and param_enum:
                    value = param_enum[0]
            
            # 5. Content/text parameters (data flow)
            elif any(keyword in param_name.lower() for keyword in ['content', 'text', 'body', 'data', 'input']):
                if current_steps:
                    # Reference the most relevant previous step with intelligent field selection
                    if 'body' in param_name.lower() or 'content' in param_name.lower():
                        # For body/content, prefer summarizer or text processing steps
                        for step in reversed(current_steps):
                            if any(keyword in step['connector_name'] for keyword in ['summariz', 'text', 'process']):
                                value = f"{{{{{step['connector_name']}.result}}}}"
                                break
                        if not value:
                            value = f"{{{{{current_steps[-1]['connector_name']}.result}}}}"
                    elif param_name.lower() == 'text' and 'summariz' in connector_name.lower():
                        # Dynamic handling for any summarizer connector - it needs actual text content
                        # Look for code nodes that might have processed text content
                        for step in reversed(current_steps):
                            if step['connector_name'] == 'code':
                                # Try common text field names from code processing
                                possible_fields = ['combinedText', 'processedText', 'content', 'text', 'result']
                                # Use the most likely field for text content
                                value = f"{{{{{step['connector_name']}.combinedText}}}}"
                                break
                            elif any(keyword in step['connector_name'] for keyword in ['summariz', 'text', 'process']):
                                value = f"{{{{{step['connector_name']}.result}}}}"
                                break
                        if not value:
                            value = f"{{{{{current_steps[-1]['connector_name']}.result}}}}"
                    else:
                        # For other content parameters, use previous step
                        value = f"{{{{{current_steps[-1]['connector_name']}.result}}}}"
            
            # 6. Subject/title parameters
            elif any(keyword in param_name.lower() for keyword in ['subject', 'title', 'name', 'label']):
                # Extract quoted text or generate intelligent subject
                quoted_match = re.search(patterns['quoted_text'], user_request)
                if quoted_match:
                    value = quoted_match.group(1)
                else:
                    # Generate intelligent subject based on context
                    if 'email' in user_request.lower() or 'mail' in user_request.lower():
                        if 'summary' in user_request.lower():
                            value = "Summary Report"
                        elif 'blog' in user_request.lower():
                            value = "Blog Summary"
                        else:
                            value = "Workflow Results"
                    else:
                        value = "Automated Workflow"
            
            # 7. Number parameters
            elif param_type in ['number', 'integer']:
                number_match = re.search(patterns['number'], user_request)
                if number_match:
                    value = int(number_match.group())
                elif param_default is not None:
                    value = param_default
                else:
                    # Intelligent defaults based on parameter name
                    if 'max' in param_name.lower() or 'limit' in param_name.lower():
                        value = 10
                    elif 'timeout' in param_name.lower():
                        value = 30
                    else:
                        value = 1
            
            # 8. Boolean parameters
            elif param_type == 'boolean':
                # Look for boolean indicators in request
                if any(word in user_request.lower() for word in ['enable', 'yes', 'true', 'on']):
                    value = True
                elif any(word in user_request.lower() for word in ['disable', 'no', 'false', 'off']):
                    value = False
                elif param_default is not None:
                    value = param_default
                else:
                    value = False
            
            # 9. Use default value if available
            elif param_default is not None:
                value = param_default
            
            # 10. Intelligent defaults based on parameter name patterns
            elif not value:
                name_lower = param_name.lower()
                if 'timeout' in name_lower:
                    value = 30
                elif 'max' in name_lower or 'limit' in name_lower:
                    value = 10
                elif 'format' in name_lower:
                    value = 'json'
                elif 'method' in name_lower and param_enum:
                    value = param_enum[0]
            
            # Set the parameter if we found a value and it makes sense
            if value is not None:
                # Only set parameters that are relevant to the current action or are required
                should_set = True
                
                # For Gmail connector, only set relevant parameters based on action
                if connector_name == "gmail_connector":
                    action = parameters.get("action", "send")
                    if action == "send":
                        # Only set send-related parameters
                        relevant_params = ["action", "to", "cc", "bcc", "subject", "body", "html_body", "attachments"]
                        should_set = param_name in relevant_params
                    elif action in ["read", "search", "list"]:
                        # Only set read-related parameters
                        relevant_params = ["action", "query", "max_results", "include_spam_trash", "label_ids"]
                        should_set = param_name in relevant_params
                    elif action in ["get_labels", "create_label"]:
                        # Only set label-related parameters
                        relevant_params = ["action", "label_name", "label_color"]
                        should_set = param_name in relevant_params
                
                if should_set:
                    parameters[param_name] = value
                    logger.info(f"✅ Set parameter '{param_name}' = '{value}'")
        
        return parameters
    

    
    def _determine_step_dependencies(self, current_steps: List[Dict[str, Any]]) -> List[str]:
        """Determine dependencies for the current step."""
        if not current_steps:
            return []
        
        # Simple dependency: depend on the previous step
        return [current_steps[-1]["connector_name"]]
    
    async def _configure_task_parameters(self, tool_name: str, reasoning_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure parameters for a specific task using AI reasoning with enhanced metadata.
        """
        try:
            task = reasoning_context.get('task', {})
            previous_steps = reasoning_context.get('previous_steps', [])
            original_request = reasoning_context.get('original_request', '')
            
            # Get enhanced tool metadata from enhanced tool registry
            tool_schema = {}
            parameter_hints = {}
            example_params = {}
            
            try:
                # Get AI-generated parameter suggestions from enhanced registry
                example_params = await self.tool_registry.generate_parameter_suggestions(tool_name, original_request, reasoning_context)
                
                # Get tool metadata including schema and hints
                tool_metadata = await self.tool_registry.get_tool_metadata_by_name(tool_name)
                if tool_metadata:
                    tool_schema = tool_metadata.get('parameter_schema', {})
                    parameter_hints = tool_metadata.get('ai_parameter_hints', tool_metadata.get('parameter_hints', {}))
                
            except Exception as e:
                logger.warning(f"Failed to get enhanced metadata for {tool_name}: {str(e)}")
                
                # Fallback to basic tool registry metadata
                if hasattr(self.tool_registry, 'tool_metadata'):
                    tool_metadata = self.tool_registry.tool_metadata.get(tool_name, {})
                    tool_schema = tool_metadata.get('parameter_schema', {})
            
            # Create enhanced parameter configuration prompt with AI suggestions
            parameter_prompt = f"""
            TASK CONTEXT:
            - Task: {task.get('description', '')}
            - Tool: {tool_name}
            - Task Number: {task.get('task_number', 1)}
            - Original Request: "{original_request}"
            
            PREVIOUS STEPS COMPLETED:
            {chr(10).join([f"{i+1}. {step['connector_name']}: {step.get('purpose', '')}" for i, step in enumerate(previous_steps)])}
            
            TOOL SCHEMA:
            {json.dumps(tool_schema, indent=2) if tool_schema else "No schema available"}
            
            AI-GENERATED PARAMETER SUGGESTIONS:
            {json.dumps(example_params, indent=2) if example_params else "No suggestions available"}
            
            PARAMETER HINTS:
            {chr(10).join([f"- {param}: {hint}" for param, hint in parameter_hints.items()]) if parameter_hints else "No hints available"}
            
            TASK: Configure the parameters for {tool_name} to accomplish: {task.get('description', '')}
            
            INSTRUCTIONS:
            1. Start with the AI-generated parameter suggestions as a base
            2. Analyze what this task needs to accomplish
            3. Consider data from previous steps (use {{step_name.result}} format for references)
            4. Use the parameter hints to understand what each parameter does
            3. Fill in all required parameters based on the original request
            4. Use appropriate values that align with the user's intent
            
            RESPOND WITH ONLY A JSON OBJECT containing the parameter values:
            {{
                "parameter_name": "value",
                "another_parameter": "{{previous_step.result}}"
            }}
            
            Be precise and ensure parameters align with the task requirements.
            """
            
            if self._client:
                ai_response = await self._ai_reason(parameter_prompt)
                
                if isinstance(ai_response, dict):
                    return ai_response
                elif isinstance(ai_response, str):
                    try:
                        return json.loads(ai_response)
                    except:
                        return self._create_fallback_parameters(tool_name, task, original_request)
                else:
                    return self._create_fallback_parameters(tool_name, task, original_request)
            else:
                return self._create_fallback_parameters(tool_name, task, original_request)
                
        except Exception as e:
            logger.error(f"Error configuring task parameters: {e}")
            return self._create_fallback_parameters(tool_name, task, original_request)
    
    def _create_fallback_parameters(self, tool_name: str, task: Dict[str, Any], original_request: str) -> Dict[str, Any]:
        """
        Create basic fallback parameters when AI configuration fails.
        """
        # Basic parameter templates for common tools
        fallback_params = {
            'perplexity_search': {
                'action': 'search',
                'query': original_request[:100],
                'model': 'sonar',
                'max_tokens': 1000
            },
            'text_summarizer': {
                'text': '{perplexity_search.result}',
                'max_length': 100,
                'style': 'detailed'
            },
            'youtube': {
                'resource': 'video',
                'operation': 'video_getAll',
                'query': '{text_summarizer.result}',
                'maxResults': 3
            },
            'google_drive': {
                'action': 'create_from_text',
                'file_name': 'Workflow Result',
                'text_content': '{text_summarizer.result}'
            },
            'google_sheets': {
                'action': 'append',
                'values': [['Timestamp', 'Data'], ['{now}', '{text_summarizer.result}']]
            },
            'gmail_connector': {
                'action': 'send',
                'to': 'user@example.com',
                'subject': 'Workflow Result',
                'body': '{text_summarizer.result}'
            }
        }
        
        return fallback_params.get(tool_name, {'action': 'default'})
    
    def _extract_dependencies(self, parameters: Dict[str, Any], previous_steps: List[Dict[str, Any]]) -> List[str]:
        """
        Extract dependencies from parameter values that reference previous steps.
        """
        dependencies = []
        param_str = json.dumps(parameters)
        
        for step in previous_steps:
            step_name = step.get('connector_name', '')
            if f"{{{step_name}." in param_str:
                dependencies.append(step_name)
        
        return dependencies
    
    async def _simple_plan_refinement(self, current_plan: Dict[str, Any], user_feedback: str, available_tools: List[str]) -> Dict[str, Any]:
        """
        Simple plan refinement when AI is not available.
        """
        logger.info(f"🔧 Using simple plan refinement fallback")
        feedback_lower = user_feedback.lower()
        refined_plan = current_plan.copy()
        
        # If user wants to add something
        if 'add' in feedback_lower:
            for tool in available_tools:
                if tool.replace('_', ' ') in feedback_lower:
                    new_task = {
                        "task_number": len(refined_plan.get('tasks', [])) + 1,
                        "description": f"Use {tool.replace('_', ' ')}",
                        "suggested_tool": tool,
                        "reasoning": f"User requested to add {tool}",
                        "inputs": ["data from previous tasks"],
                        "outputs": ["processed data"]
                    }
                    refined_plan.setdefault('tasks', []).append(new_task)
        
        # If user wants to remove something
        elif 'remove' in feedback_lower:
            logger.info(f"🗑️ Detected removal request in feedback: {user_feedback}")
            tasks = refined_plan.get('tasks', [])
            refined_tasks = []
            removed_tools = []
            
            for task in tasks:
                tool_name = task.get('suggested_tool', '')
                tool_display_name = tool_name.replace('_', ' ')
                
                # Check if this tool should be removed
                should_remove = False
                if 'webhook' in feedback_lower and tool_name == 'webhook':
                    should_remove = True
                    removed_tools.append(tool_name)
                elif tool_name in feedback_lower or tool_display_name in feedback_lower:
                    should_remove = True
                    removed_tools.append(tool_name)
                
                if not should_remove:
                    # Renumber the task
                    task_copy = task.copy()
                    task_copy['task_number'] = len(refined_tasks) + 1
                    refined_tasks.append(task_copy)
                else:
                    logger.info(f"🗑️ Removing task: {task.get('description')} (tool: {tool_name})")
            
            refined_plan['tasks'] = refined_tasks
            refined_plan['estimated_steps'] = str(len(refined_tasks))
            
            # Update summary to reflect removal
            if removed_tools:
                removed_tools_str = ', '.join(removed_tools)
                original_summary = refined_plan.get('summary', '')
                refined_plan['summary'] = f"{original_summary} (removed: {removed_tools_str})"
            
            logger.info(f"🔧 Fallback refinement: {len(tasks)} -> {len(refined_tasks)} tasks")
        
        return refined_plan
    
    async def _analyze_modification_request(self, request: str, executed_workflow: Dict[str, Any], original_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user request to determine if it's a workflow modification and what changes are needed.
        """
        try:
            logger.info(f"🧠 Analyzing modification request: {request}")
            
            # Get available tools for replacement suggestions
            available_tools = []
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tools = await self.tool_registry.get_available_tools()
                available_tools = [tool.name for tool in tools]
            
            analysis_prompt = f"""
            EXECUTED WORKFLOW:
            {json.dumps(executed_workflow, indent=2)}
            
            ORIGINAL PLAN:
            {json.dumps(original_plan, indent=2)}
            
            USER MODIFICATION REQUEST: "{request}"
            
            AVAILABLE TOOLS: {', '.join(available_tools)}
            
            TASK: Analyze if this is a workflow modification request and determine what changes are needed.
            
            INSTRUCTIONS:
            1. Determine if the user wants to modify the existing workflow
            2. If yes, identify which specific tasks/connectors need to be changed
            3. For replacements, suggest replacement connectors from available tools
            4. For removals, identify which connectors to remove
            5. Provide reasoning for the changes
            
            RESPOND WITH JSON:
            {{
                "is_modification": true/false,
                "confidence": 0.0-1.0,
                "reasoning": "explanation of analysis",
                "changes": [
                    {{
                        "type": "replace_connector|remove_connector",
                        "task_number": 1,
                        "current_connector": "perplexity_search",
                        "new_connector": "openai_connector",
                        "reason": "User requested OpenAI instead of Perplexity"
                    }}
                ],
                "modification_type": "connector_replacement|connector_removal|parameter_change|task_addition"
            }}
            """
            
            if self._client:
                ai_response = await self._ai_reason(analysis_prompt)
                
                if isinstance(ai_response, dict) and 'is_modification' in ai_response:
                    logger.info(f"🧠 Modification analysis: {ai_response.get('reasoning', 'No reasoning provided')}")
                    return ai_response
                else:
                    logger.warning("⚠️ AI analysis failed, using fallback")
                    return await self._fallback_modification_analysis(request, executed_workflow)
            else:
                return await self._fallback_modification_analysis(request, executed_workflow)
                
        except Exception as e:
            logger.error(f"❌ Error analyzing modification request: {e}")
            return await self._fallback_modification_analysis(request, executed_workflow)
    
    async def _fallback_modification_analysis(self, request: str, executed_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback analysis when AI is not available.
        """
        logger.info("🔧 Using fallback modification analysis")
        
        request_lower = request.lower()
        workflow_steps = executed_workflow.get("steps", [])
        
        # Check for common modification patterns
        modification_keywords = ['replace', 'change', 'use', 'instead', 'switch', 'modify', 'remove', 'delete', 'exclude']
        is_modification = any(keyword in request_lower for keyword in modification_keywords)
        
        if not is_modification:
            return {
                "is_modification": False,
                "confidence": 0.2,
                "reasoning": "No clear modification keywords detected",
                "changes": []
            }
        
        # Check if this is a removal request
        removal_keywords = ['remove', 'delete', 'exclude', 'drop']
        is_removal = any(keyword in request_lower for keyword in removal_keywords)
        
        # Try to identify connector changes
        changes = []
        for i, step in enumerate(workflow_steps):
            connector_name = step.get("connector_name", "")
            connector_display = connector_name.replace("_", " ")
            
            if connector_name.lower() in request_lower or connector_display.lower() in request_lower:
                if is_removal:
                    # This connector should be removed
                    changes.append({
                        "type": "remove_connector",
                        "task_number": i + 1,
                        "current_connector": connector_name,
                        "reason": f"User requested to remove {connector_name}"
                    })
                else:
                    # This connector might need to be replaced
                    changes.append({
                        "type": "replace_connector",
                        "task_number": i + 1,
                        "current_connector": connector_name,
                        "new_connector": "to_be_determined",
                        "reason": f"User mentioned {connector_name} in modification request"
                    })
        
        modification_type = "connector_removal" if is_removal else "connector_replacement"
        
        return {
            "is_modification": True,
            "confidence": 0.7,
            "reasoning": f"Detected modification keywords and connector references. Type: {modification_type}",
            "changes": changes,
            "modification_type": modification_type
        }
    
    async def _apply_workflow_modification(self, executed_workflow: Dict[str, Any], original_plan: Dict[str, Any], modification_analysis: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Apply the requested modifications to the workflow.
        """
        try:
            logger.info(f"🔧 Applying workflow modifications")
            logger.info(f"🔍 Number of changes to apply: {len(modification_analysis.get('changes', []))}")
            
            modified_workflow = executed_workflow.copy()
            changes_applied = []
            
            for i, change in enumerate(modification_analysis.get("changes", [])):
                logger.info(f"🔍 Processing change {i+1}: {change}")
                if change["type"] == "replace_connector":
                    result = await self._replace_connector_in_workflow(
                        modified_workflow, 
                        change, 
                        user_id
                    )
                    if result["success"]:
                        changes_applied.append(result["change_description"])
                        logger.info(f"✅ Applied change: {result['change_description']}")
                    else:
                        logger.warning(f"⚠️ Failed to apply change: {result.get('error', 'Unknown error')}")
                elif change["type"] == "remove_connector":
                    # Handle connector removal
                    result = await self._remove_connector_from_workflow(
                        modified_workflow, 
                        change, 
                        user_id
                    )
                    if result["success"]:
                        changes_applied.append(result["change_description"])
                        logger.info(f"✅ Applied change: {result['change_description']}")
                    else:
                        logger.warning(f"⚠️ Failed to apply change: {result.get('error', 'Unknown error')}")
                elif change["type"] == "parameter_change":
                    # Handle parameter changes
                    result = await self._modify_connector_parameters(
                        modified_workflow, 
                        change, 
                        user_id
                    )
                    if result["success"]:
                        changes_applied.append(result["change_description"])
                        logger.info(f"✅ Applied change: {result['change_description']}")
                    else:
                        logger.warning(f"⚠️ Failed to apply change: {result.get('error', 'Unknown error')}")
                elif change["type"] == "task_addition":
                    # Handle task addition
                    result = await self._add_task_to_workflow(
                        modified_workflow, 
                        change, 
                        user_id
                    )
                    if result["success"]:
                        changes_applied.append(result["change_description"])
                        logger.info(f"✅ Applied change: {result['change_description']}")
                    else:
                        logger.warning(f"⚠️ Failed to apply change: {result.get('error', 'Unknown error')}")
                else:
                    logger.warning(f"⚠️ Unknown change type: {change.get('type', 'unknown')}")
            
            # Apply intelligent dependency resolution after all changes
            if changes_applied:
                logger.info("🧠 Applying intelligent dependency resolution")
                dependency_changes = await self._resolve_workflow_dependencies(modified_workflow, modification_analysis)
                changes_applied.extend(dependency_changes)
            
            # Update workflow metadata
            modified_workflow["modified_at"] = datetime.now().isoformat()
            modified_workflow["modification_history"] = modified_workflow.get("modification_history", [])
            modified_workflow["modification_history"].append({
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "changes": changes_applied,
                "original_request": modification_analysis.get("original_request", "")
            })
            
            return modified_workflow
            
        except Exception as e:
            logger.error(f"❌ Error applying workflow modification: {e}")
            return executed_workflow  # Return original if modification fails
    
    async def _replace_connector_in_workflow(self, workflow: Dict[str, Any], change: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Replace a specific connector in the workflow.
        """
        try:
            current_connector = change["current_connector"]
            new_connector = change.get("new_connector", "")
            
            # If new connector is not specified, try to find a suitable replacement
            if new_connector == "to_be_determined":
                new_connector = await self._find_suitable_replacement(current_connector)
            
            if not new_connector:
                return {
                    "success": False,
                    "error": f"Could not find suitable replacement for {current_connector}"
                }
            
            # Update workflow steps
            steps = workflow.get("steps", [])
            updated_steps = []
            
            for step in steps:
                if step.get("connector_name") == current_connector:
                    # Replace the connector
                    updated_step = step.copy()
                    updated_step["connector_name"] = new_connector
                    updated_step["modified"] = True
                    updated_step["modification_reason"] = change.get("reason", "User requested change")
                    
                    # Update step description if needed
                    old_description = updated_step.get("description", "")
                    updated_step["description"] = old_description.replace(
                        current_connector.replace("_", " ").title(),
                        new_connector.replace("_", " ").title()
                    )
                    
                    updated_steps.append(updated_step)
                    logger.info(f"🔄 Replaced {current_connector} with {new_connector} in step")
                else:
                    updated_steps.append(step)
            
            workflow["steps"] = updated_steps
            
            return {
                "success": True,
                "change_description": f"Replaced {current_connector} with {new_connector}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error replacing connector: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _remove_connector_from_workflow(self, workflow: Dict[str, Any], change: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Remove a specific connector from the workflow.
        """
        try:
            connector_to_remove = change["current_connector"]
            
            # Update workflow steps by removing the specified connector
            steps = workflow.get("steps", [])
            updated_steps = []
            removed_step_number = None
            
            for step in steps:
                if step.get("connector_name") == connector_to_remove:
                    # Mark this step for removal
                    removed_step_number = step.get("step_number")
                    logger.info(f"🗑️ Removing step {removed_step_number}: {step.get('description', 'Unknown step')} ({connector_to_remove})")
                else:
                    # Keep this step but renumber if necessary
                    updated_step = step.copy()
                    if removed_step_number and step.get("step_number", 0) > removed_step_number:
                        updated_step["step_number"] = step.get("step_number", 0) - 1
                    updated_steps.append(updated_step)
            
            workflow["steps"] = updated_steps
            
            return {
                "success": True,
                "change_description": f"Removed {connector_to_remove} from workflow"
            }
            
        except Exception as e:
            logger.error(f"❌ Error removing connector: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _modify_connector_parameters(self, workflow: Dict[str, Any], change: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Modify parameters of a specific connector in the workflow.
        """
        try:
            connector_name = change["current_connector"]
            task_number = change.get("task_number")
            reason = change.get("reason", "User requested parameter modification")
            
            logger.info(f"🔧 Modifying parameters for {connector_name} (task #{task_number})")
            
            # Find the step to modify
            steps = workflow.get("steps", [])
            target_step = None
            
            for step in steps:
                if (step.get("connector_name") == connector_name and 
                    (not task_number or step.get("task_number") == task_number or step.get("step_number") == task_number)):
                    target_step = step
                    break
            
            if not target_step:
                return {
                    "success": False,
                    "error": f"Could not find step with connector {connector_name}"
                }
            
            # Use AI to intelligently modify parameters based on the user's request
            parameter_modifications = await self._ai_modify_parameters(
                target_step, 
                reason, 
                workflow
            )
            
            if parameter_modifications:
                # Apply the parameter modifications
                original_parameters = target_step.get("parameters", {}).copy()
                updated_parameters = original_parameters.copy()
                updated_parameters.update(parameter_modifications)
                
                target_step["parameters"] = updated_parameters
                target_step["parameter_modified"] = True
                target_step["parameter_modification_reason"] = reason
                target_step["original_parameters"] = original_parameters
                
                # Log the changes
                changes_made = []
                for key, new_value in parameter_modifications.items():
                    old_value = original_parameters.get(key, "not set")
                    changes_made.append(f"{key}: {old_value} → {new_value}")
                    logger.info(f"🔄 Updated parameter {key}: {old_value} → {new_value}")
                
                return {
                    "success": True,
                    "change_description": f"Modified {connector_name} parameters: {', '.join(changes_made)}"
                }
            else:
                # Fallback: apply basic parameter fixes
                fallback_changes = self._apply_fallback_parameter_fixes(target_step, reason)
                if fallback_changes:
                    target_step["parameter_modified"] = True
                    target_step["parameter_modification_reason"] = reason
                    
                    return {
                        "success": True,
                        "change_description": f"Applied fallback parameter fixes to {connector_name}: {fallback_changes}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Could not determine appropriate parameter modifications for {connector_name}"
                    }
            
        except Exception as e:
            logger.error(f"❌ Error modifying connector parameters: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _ai_modify_parameters(self, step: Dict[str, Any], reason: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to intelligently modify connector parameters based on user feedback.
        """
        try:
            connector_name = step.get("connector_name", "")
            current_parameters = step.get("parameters", {})
            
            logger.info(f"🤖 Using AI to modify parameters for {connector_name}")
            
            # Create AI prompt for parameter modification
            parameter_prompt = f"""
            CONNECTOR PARAMETER MODIFICATION REQUEST:
            
            CONNECTOR: {connector_name}
            CURRENT PARAMETERS: {json.dumps(current_parameters, indent=2)}
            USER ISSUE/REQUEST: "{reason}"
            
            FULL WORKFLOW CONTEXT:
            {json.dumps(workflow, indent=2)}
            
            TASK: Analyze the user's issue and suggest specific parameter modifications to resolve it.
            
            COMMON ISSUES AND SOLUTIONS:
            - "cannot see email body" → ensure html_body is properly formatted, add plain_text fallback
            - "data not showing" → check data formatting, add proper encoding
            - "connection failed" → verify authentication parameters, add retry logic
            - "output format wrong" → adjust output_format, content_type parameters
            
            RESPOND WITH JSON containing only the parameters that need to be changed:
            {{
                "parameter_name": "new_value",
                "another_parameter": "another_new_value"
            }}
            
            If no changes are needed, respond with empty object: {{}}
            """
            
            if self._client:
                ai_response = await self._ai_reason(parameter_prompt)
                
                if isinstance(ai_response, dict):
                    # Filter out any non-parameter fields
                    parameter_changes = {}
                    for key, value in ai_response.items():
                        if key not in ["reasoning", "action_type", "error", "content"]:
                            parameter_changes[key] = value
                    
                    if parameter_changes:
                        logger.info(f"🤖 AI suggested parameter changes: {parameter_changes}")
                        return parameter_changes
                    else:
                        logger.info("🤖 AI determined no parameter changes needed")
                        return {}
                else:
                    logger.warning("⚠️ AI parameter modification failed")
                    return {}
            else:
                logger.info("🔧 No AI client available for parameter modification")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error in AI parameter modification: {e}")
            return {}
    
    def _apply_fallback_parameter_fixes(self, step: Dict[str, Any], reason: str) -> str:
        """
        Apply basic parameter fixes when AI is not available.
        """
        try:
            connector_name = step.get("connector_name", "")
            current_parameters = step.get("parameters", {})
            reason_lower = reason.lower()
            
            applied_fixes = []
            
            # Gmail-specific fixes
            if connector_name == "gmail_connector":
                if "email body" in reason_lower or "cannot see" in reason_lower:
                    # Ensure email body is visible
                    if "html_body" in current_parameters:
                        # Add plain text fallback
                        current_parameters["include_plain_text"] = True
                        applied_fixes.append("added plain text fallback")
                    
                    if "format" not in current_parameters:
                        current_parameters["format"] = "both"  # HTML and plain text
                        applied_fixes.append("set format to both HTML and plain text")
            
            # General data visibility fixes
            if "cannot see" in reason_lower or "not showing" in reason_lower:
                if "output_format" in current_parameters:
                    current_parameters["output_format"] = "detailed"
                    applied_fixes.append("changed output format to detailed")
                
                if "include_metadata" not in current_parameters:
                    current_parameters["include_metadata"] = True
                    applied_fixes.append("enabled metadata inclusion")
            
            # Connection/authentication fixes
            if "failed" in reason_lower or "error" in reason_lower:
                if "retry_count" not in current_parameters:
                    current_parameters["retry_count"] = 3
                    applied_fixes.append("added retry logic")
                
                if "timeout" not in current_parameters:
                    current_parameters["timeout"] = 30
                    applied_fixes.append("increased timeout")
            
            return ", ".join(applied_fixes) if applied_fixes else ""
            
        except Exception as e:
            logger.error(f"❌ Error applying fallback parameter fixes: {e}")
            return ""
    
    async def _find_suitable_replacement(self, current_connector: str) -> str:
        """
        Find a suitable replacement connector based on functionality.
        """
        try:
            # Define connector replacement mappings based on functionality
            replacement_map = {
                "perplexity_search": "text_summarizer",  # AI search/reasoning (using available connector)
                "text_summarizer": "perplexity_search",  # AI search/reasoning
                "google_sheets": "airtable",              # Spreadsheet/database
                "airtable": "google_sheets",              # Spreadsheet/database
                "notion": "google_drive",                 # Document storage
                "google_drive": "notion",                 # Document storage
                "gmail_connector": "webhook",             # Communication
                "webhook": "gmail_connector",             # Communication
            }
            
            # Get available tools
            available_tools = []
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tools = await self.tool_registry.get_available_tools()
                available_tools = [tool.name for tool in tools]
            
            # Try direct mapping first
            suggested_replacement = replacement_map.get(current_connector)
            if suggested_replacement and suggested_replacement in available_tools:
                return suggested_replacement
            
            # If no direct mapping, try to find similar functionality
            connector_categories = {
                "ai_services": ["perplexity_search", "text_summarizer"],
                "data_sources": ["google_sheets", "airtable", "google_drive"],
                "communication": ["gmail_connector", "webhook"],
                "productivity": ["notion"],
                "social_media": ["youtube"]
            }
            
            # Find category of current connector
            current_category = None
            for category, connectors in connector_categories.items():
                if current_connector in connectors:
                    current_category = category
                    break
            
            if current_category:
                # Find another connector in the same category
                for connector in connector_categories[current_category]:
                    if connector != current_connector and connector in available_tools:
                        return connector
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding replacement connector: {e}")
            return None
    
    async def _add_task_to_workflow(self, workflow: Dict[str, Any], change: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Add a new task to the workflow.
        """
        try:
            connector_name = change.get("new_connector")
            task_number = change.get("task_number", 1)
            reason = change.get("reason", "User requested task addition")
            
            if not connector_name:
                return {
                    "success": False,
                    "error": "No connector specified for task addition"
                }
            
            # Get connector info from tool registry
            connector_info = None
            
            if hasattr(self, 'tool_registry') and self.tool_registry:
                tool_metadata = await self.tool_registry.get_tool_metadata_by_name(connector_name)
                if tool_metadata:
                    connector_info = tool_metadata
            
            if not connector_info:
                return {
                    "success": False,
                    "error": f"Connector {connector_name} not found in tool registry"
                }
            
            # Generate parameters for the new task using AI/pattern-based extraction first,
            # leveraging the user's modification reason text for better accuracy.
            try:
                parameters = {}

                # Prefer intelligent configuration using the connector schema and the reason text
                try:
                    current_steps = workflow.get("steps", [])
                    parameters = await self._configure_connector_parameters(
                        connector_info,
                        {"user_request": reason},
                        current_steps,
                    )
                except Exception as _cfg_err:
                    logger.warning(
                        f"⚠️ Intelligent parameter configuration failed for {connector_name}: {_cfg_err}"
                    )
                    parameters = {}

                # If intelligent configuration produced nothing, fall back to the planner-based generation
                if not parameters:
                    if hasattr(self, 'workflow_planner') and self.workflow_planner:
                        # Create a simple task description for parameter generation
                        task_description = f"Add {connector_name.replace('_', ' ')} task: {reason}"

                        # Generate parameters using the workflow planner's AI capabilities
                        parameters = await self._generate_task_parameters(
                            connector_name, task_description, workflow
                        )
                    else:
                        parameters = self._get_default_parameters(connector_name)

                # As a final guard, if key intent parameters like 'query' are still missing for
                # search-type connectors, seed them from the reason text.
                if connector_name == "perplexity_search" and (
                    "query" not in parameters or not parameters.get("query")
                ):
                    parameters["query"] = reason

            except Exception as e:
                logger.warning(
                    f"⚠️ Could not generate parameters for {connector_name}, using defaults: {e}"
                )
                parameters = self._get_default_parameters(connector_name)
            
            # Create the new step
            new_step = {
                "task_number": task_number,
                "connector_name": connector_name,
                "parameters": parameters,
                "purpose": reason,
                "reasoning": f"Added {connector_name} as requested by user"
            }
            
            # Insert the step at the specified position
            steps = workflow.get("steps", [])
            
            # Adjust task numbers for existing steps
            for step in steps:
                if step.get("task_number", 0) >= task_number:
                    step["task_number"] = step.get("task_number", 0) + 1
            
            # Insert the new step
            if task_number <= 1:
                steps.insert(0, new_step)
            elif task_number > len(steps):
                steps.append(new_step)
            else:
                steps.insert(task_number - 1, new_step)
            
            workflow["steps"] = steps
            workflow["total_steps"] = len(steps)
            
            return {
                "success": True,
                "change_description": f"Added {connector_name.replace('_', ' ')} task at position {task_number}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding task to workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_default_parameters(self, connector_name: str) -> Dict[str, Any]:
        """
        Get default parameters for a connector.
        """
        defaults = {
            "perplexity_search": {
                "query": "search query",
                "max_results": 5
            },
            "gmail_connector": {
                "to": "recipient@example.com",
                "subject": "Email subject",
                "body": "Email body"
            },
            "google_sheets": {
                "spreadsheet_id": "",
                "range": "A1:Z100",
                "operation": "read"
            }
        }
        
        return defaults.get(connector_name, {})
    
    async def _generate_task_parameters(self, connector_name: str, task_description: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate appropriate parameters for a task using AI.
        """
        try:
            # Use the workflow planner's AI to generate parameters
            if hasattr(self, 'workflow_planner') and self.workflow_planner:
                # Create a simple workflow request for parameter generation
                simple_request = f"Create a {connector_name} task: {task_description}"
                
                # Use the planner to generate a single-step workflow
                plan_result = await self.workflow_planner.create_workflow_plan(simple_request, "temp_user")
                
                if plan_result.get("success") and plan_result.get("workflow", {}).get("steps"):
                    first_step = plan_result["workflow"]["steps"][0]
                    if first_step.get("connector_name") == connector_name:
                        return first_step.get("parameters", {})
            
            # Fallback to defaults
            return self._get_default_parameters(connector_name)
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating AI parameters: {e}")
            return self._get_default_parameters(connector_name)
    
    def _format_modification_summary(self, modification_analysis: Dict[str, Any], modified_workflow: Dict[str, Any]) -> str:
        """
        Format a summary of the modifications applied to the workflow.
        """
        try:
            changes = modification_analysis.get("changes", [])
            
            if not changes:
                return "✅ I've analyzed your request, but no specific changes were needed."
            
            summary_parts = [
                "✅ **Workflow Modified Successfully!**\n",
                "Here's what I changed:\n"
            ]
            
            for i, change in enumerate(changes, 1):
                if change["type"] == "replace_connector":
                    current = change["current_connector"].replace("_", " ").title()
                    new = change.get("new_connector", "Unknown").replace("_", " ").title()
                    reason = change.get("reason", "User requested change")
                    
                    summary_parts.append(f"{i}. **Replaced {current} with {new}**")
                    summary_parts.append(f"   - Reason: {reason}")
                    summary_parts.append(f"   - Task #{change.get('task_number', 'Unknown')} updated\n")
                
                elif change["type"] == "task_addition":
                    connector = change.get("new_connector", "Unknown").replace("_", " ").title()
                    reason = change.get("reason", "User requested addition")
                    task_num = change.get("task_number", "Unknown")
                    
                    summary_parts.append(f"{i}. **Added {connector} Task**")
                    summary_parts.append(f"   - Reason: {reason}")
                    summary_parts.append(f"   - Position: Task #{task_num}\n")
                
                elif change["type"] == "parameter_change":
                    connector = change.get("current_connector", "Unknown").replace("_", " ").title()
                    reason = change.get("reason", "User requested parameter update")
                    task_num = change.get("task_number", "Unknown")
                    
                    summary_parts.append(f"{i}. **Updated {connector} Parameters**")
                    summary_parts.append(f"   - Reason: {reason}")
                    summary_parts.append(f"   - Task #{task_num} modified\n")
                
                elif change["type"] == "remove_connector":
                    connector = change.get("current_connector", "Unknown").replace("_", " ").title()
                    reason = change.get("reason", "User requested removal")
                    
                    summary_parts.append(f"{i}. **Removed {connector}**")
                    summary_parts.append(f"   - Reason: {reason}\n")
            
            summary_parts.append("\n🚀 **Your workflow is ready to use with these changes!**")
            summary_parts.append("\nThe modifications have been applied automatically. You can continue using your workflow or request additional changes.")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ Error formatting modification summary: {e}")
            return "✅ Workflow modifications have been applied successfully!"
    
    async def _resolve_workflow_dependencies(self, workflow: Dict[str, Any], modification_analysis: Dict[str, Any]) -> List[str]:
        """
        Intelligently resolve workflow dependencies after modifications.
        This makes the AI agent human-like by understanding workflow context and data flow.
        """
        try:
            logger.info("🧠 Starting intelligent dependency resolution")
            
            dependency_changes = []
            steps = workflow.get("steps", [])
            
            # Analyze what was changed to understand impact
            removed_connectors = []
            replaced_connectors = {}
            
            for change in modification_analysis.get("changes", []):
                if change["type"] == "remove_connector":
                    removed_connectors.append(change["current_connector"])
                elif change["type"] == "replace_connector":
                    replaced_connectors[change["current_connector"]] = change.get("new_connector")
            
            # For each step, check if it depends on removed/replaced connectors
            for step in steps:
                step_modified = False
                original_parameters = step.get("parameters", {})
                updated_parameters = original_parameters.copy()
                
                # Check each parameter for dependencies
                for param_key, param_value in original_parameters.items():
                    if isinstance(param_value, str):
                        # Look for dependency references like "{connector_name.output}"
                        updated_value = await self._resolve_parameter_dependencies(
                            param_value, 
                            removed_connectors, 
                            replaced_connectors, 
                            steps
                        )
                        
                        if updated_value != param_value:
                            updated_parameters[param_key] = updated_value
                            step_modified = True
                            logger.info(f"🔄 Updated parameter {param_key}: {param_value} → {updated_value}")
                
                # Update step if parameters were modified
                if step_modified:
                    step["parameters"] = updated_parameters
                    step["dependency_resolved"] = True
                    step["dependency_resolution_reason"] = "Parameters updated due to workflow modifications"
                    
                    connector_name = step.get("connector_name", "unknown")
                    dependency_changes.append(f"Updated {connector_name} parameters to resolve dependencies")
            
            # Apply AI-powered intelligent dependency resolution
            if removed_connectors or replaced_connectors:
                ai_dependency_changes = await self._ai_resolve_complex_dependencies(
                    workflow, removed_connectors, replaced_connectors
                )
                dependency_changes.extend(ai_dependency_changes)
            
            logger.info(f"🧠 Dependency resolution completed. Applied {len(dependency_changes)} dependency fixes")
            return dependency_changes
            
        except Exception as e:
            logger.error(f"❌ Error in dependency resolution: {e}")
            return []
    
    async def _resolve_parameter_dependencies(self, param_value: str, removed_connectors: List[str], replaced_connectors: Dict[str, str], steps: List[Dict[str, Any]]) -> str:
        """
        Resolve parameter dependencies by updating references to removed/replaced connectors.
        """
        try:
            updated_value = param_value
            
            # Handle removed connectors - find alternative data sources
            for removed_connector in removed_connectors:
                dependency_pattern = f"{{{removed_connector}."
                if dependency_pattern in updated_value:
                    # Find an alternative connector that can provide similar data
                    alternative_connector = self._find_alternative_data_source(removed_connector, steps)
                    if alternative_connector:
                        updated_value = updated_value.replace(
                            f"{{{removed_connector}.", 
                            f"{{{alternative_connector}."
                        )
                        logger.info(f"🔄 Redirected dependency from {removed_connector} to {alternative_connector}")
            
            # Handle replaced connectors
            for old_connector, new_connector in replaced_connectors.items():
                dependency_pattern = f"{{{old_connector}."
                if dependency_pattern in updated_value:
                    updated_value = updated_value.replace(
                        f"{{{old_connector}.", 
                        f"{{{new_connector}."
                    )
                    logger.info(f"🔄 Updated dependency from {old_connector} to {new_connector}")
            
            return updated_value
            
        except Exception as e:
            logger.error(f"❌ Error resolving parameter dependencies: {e}")
            return param_value
    
    def _find_alternative_data_source(self, removed_connector: str, steps: List[Dict[str, Any]]) -> str:
        """
        Find an alternative connector that can provide similar data to the removed one.
        """
        try:
            # Get the step that was removed to understand what it provided
            removed_step = None
            for step in steps:
                if step.get("connector_name") == removed_connector:
                    removed_step = step
                    break
            
            if not removed_step:
                # Look for the most recent step that could provide data
                if steps:
                    return steps[-1].get("connector_name", "")
                return ""
            
            # Analyze what the removed connector was supposed to output
            removed_outputs = removed_step.get("outputs", [])
            removed_purpose = removed_step.get("purpose", "").lower()
            
            # Find a step that comes before the removed one and could provide similar data
            alternative_candidates = []
            
            for step in steps:
                step_connector = step.get("connector_name", "")
                step_outputs = step.get("outputs", [])
                step_purpose = step.get("purpose", "").lower()
                
                if step_connector != removed_connector:
                    # Score based on output similarity and purpose similarity
                    score = 0
                    
                    # Check output similarity
                    for output in step_outputs:
                        if any(removed_output in output or output in removed_output for removed_output in removed_outputs):
                            score += 2
                    
                    # Check purpose similarity
                    if any(word in step_purpose for word in removed_purpose.split() if len(word) > 3):
                        score += 1
                    
                    if score > 0:
                        alternative_candidates.append((step_connector, score))
            
            # Return the best alternative
            if alternative_candidates:
                alternative_candidates.sort(key=lambda x: x[1], reverse=True)
                best_alternative = alternative_candidates[0][0]
                logger.info(f"🎯 Found best alternative for {removed_connector}: {best_alternative}")
                return best_alternative
            
            # Fallback: return the first available step
            if steps:
                fallback = steps[0].get("connector_name", "")
                logger.info(f"🔄 Using fallback alternative for {removed_connector}: {fallback}")
                return fallback
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ Error finding alternative data source: {e}")
            return ""
    
    async def _ai_resolve_complex_dependencies(self, workflow: Dict[str, Any], removed_connectors: List[str], replaced_connectors: Dict[str, str]) -> List[str]:
        """
        Use AI to resolve complex workflow dependencies that require understanding of data flow and context.
        """
        try:
            if not removed_connectors and not replaced_connectors:
                return []
            
            logger.info("🤖 Using AI for complex dependency resolution")
            
            # Create a comprehensive prompt for AI dependency resolution
            dependency_prompt = f"""
            WORKFLOW ANALYSIS FOR DEPENDENCY RESOLUTION:
            
            CURRENT WORKFLOW:
            {json.dumps(workflow, indent=2)}
            
            MODIFICATIONS MADE:
            - Removed connectors: {removed_connectors}
            - Replaced connectors: {replaced_connectors}
            
            TASK: Analyze the workflow and identify additional changes needed to maintain data flow integrity.
            
            INSTRUCTIONS:
            1. Identify steps that depend on removed/replaced connectors
            2. Suggest parameter updates to maintain workflow functionality
            3. Identify any logical gaps in the data flow
            4. Recommend additional modifications to ensure workflow coherence
            
            RESPOND WITH JSON:
            {{
                "dependency_issues": [
                    {{
                        "step_number": 3,
                        "connector_name": "text_summarizer",
                        "issue": "References removed http_request connector",
                        "suggested_fix": "Update input parameter to use perplexity_search output instead",
                        "new_parameter_value": "{{perplexity_search.blog_content}}"
                    }}
                ],
                "workflow_improvements": [
                    {{
                        "description": "Merge perplexity search and summarization for better flow",
                        "reasoning": "Without HTTP request, perplexity can provide content directly to summarizer"
                    }}
                ]
            }}
            """
            
            if self._client:
                ai_response = await self._ai_reason(dependency_prompt)
                
                if isinstance(ai_response, dict) and 'dependency_issues' in ai_response:
                    return await self._apply_ai_dependency_fixes(workflow, ai_response)
                else:
                    logger.warning("⚠️ AI dependency resolution failed, using basic fixes")
                    return []
            else:
                logger.info("🔧 No AI client available for complex dependency resolution")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in AI dependency resolution: {e}")
            return []
    
    async def _apply_ai_dependency_fixes(self, workflow: Dict[str, Any], ai_response: Dict[str, Any]) -> List[str]:
        """
        Apply the dependency fixes suggested by AI.
        """
        try:
            applied_fixes = []
            steps = workflow.get("steps", [])
            
            # Apply dependency issue fixes
            for issue in ai_response.get("dependency_issues", []):
                step_number = issue.get("step_number")
                connector_name = issue.get("connector_name")
                suggested_fix = issue.get("suggested_fix")
                new_parameter_value = issue.get("new_parameter_value")
                
                # Find the step to fix
                for step in steps:
                    if (step.get("step_number") == step_number or 
                        step.get("connector_name") == connector_name):
                        
                        # Apply the parameter fix
                        if new_parameter_value:
                            # Extract parameter key from the issue description
                            parameters = step.get("parameters", {})
                            
                            # Try to identify which parameter to update
                            for param_key, param_value in parameters.items():
                                if isinstance(param_value, str) and "{" in param_value:
                                    # This looks like a dependency parameter
                                    parameters[param_key] = new_parameter_value
                                    step["parameters"] = parameters
                                    step["ai_dependency_fix"] = True
                                    step["ai_fix_reason"] = suggested_fix
                                    
                                    applied_fixes.append(f"AI fixed {connector_name}: {suggested_fix}")
                                    logger.info(f"🤖 Applied AI fix to {connector_name}: {suggested_fix}")
                                    break
                        break
            
            # Log workflow improvements for future reference
            for improvement in ai_response.get("workflow_improvements", []):
                logger.info(f"💡 AI workflow improvement suggestion: {improvement.get('description')} - {improvement.get('reasoning')}")
            
            return applied_fixes
            
        except Exception as e:
            logger.error(f"❌ Error applying AI dependency fixes: {e}")
            return []