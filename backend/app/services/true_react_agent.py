"""
True ReAct Agent - Dynamic reasoning and acting with connectors.
No hardcoded logic, pure reasoning-based connector selection.
"""
import json
import logging
import re
import uuid
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI

from app.core.config import settings
from app.services.tool_registry import ToolRegistry

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
        
    async def initialize(self):
        """Initialize the ReAct agent with tool registry and AI client."""
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        await self.tool_registry.initialize()
        
        # Initialize AI client
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self._client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            logger.info("True ReAct agent initialized successfully")
        else:
            logger.warning("Azure OpenAI not configured, agent will use fallback reasoning")
    
    async def determine_if_workflow_needed(self, request: str) -> bool:
        """
        Determine if the user request actually needs a workflow or is just conversational.
        """
        request_lower = request.lower().strip()
        
        # Common greetings and conversational patterns
        greetings = [
            "hi", "hello", "hey", "hii", "hiii", "hiiii",
            "good morning", "good afternoon", "good evening",
            "what's up", "whats up", "how are you", "sup"
        ]
        
        # Simple conversational responses
        simple_responses = [
            "thanks", "thank you", "ok", "okay", "yes", "no",
            "cool", "nice", "great", "awesome", "lol", "haha"
        ]
        
        # Check if it's just a greeting
        if request_lower in greetings:
            return False
        
        # Check if it's a simple response
        if request_lower in simple_responses:
            return False
        
        # Check if it's very short and doesn't contain action words
        action_words = [
            "send", "email", "search", "find", "create", "make", "build",
            "get", "fetch", "download", "upload", "process", "analyze",
            "summarize", "write", "generate", "automate", "schedule",
            "connect", "integrate", "sync", "update", "delete", "add"
        ]
        
        # If request is very short (< 3 words) and has no action words, likely conversational
        words = request_lower.split()
        if len(words) < 3 and not any(action in request_lower for action in action_words):
            return False
        
        # If it contains action words, likely needs a workflow
        if any(action in request_lower for action in action_words):
            return True
        
        # If it's a single word and not an action word, probably conversational
        if len(words) == 1 and request_lower not in action_words:
            return False
        
        # If it mentions specific tools/services AND has enough context, likely needs a workflow
        service_words = [
            "gmail", "google", "sheets", "slack", "webhook",
            "api", "database", "file", "document", "spreadsheet"
        ]
        
        # Only consider service words if the request has more context (more than just the service name)
        if any(service in request_lower for service in service_words) and len(words) > 1:
            return True
        
        # Special case for "email" - only if it's part of a longer request
        if "email" in request_lower and len(words) > 1:
            return True
        
        # If we get here and it's still very short, probably conversational
        if len(request_lower) < 10:
            return False
        
        # Default to needing workflow for longer, more complex requests
        return True
    
    async def process_user_request(self, request: str, user_id: str) -> Dict[str, Any]:
        """
        Process user request using true ReAct methodology.
        Returns real-time updates and final workflow.
        """
        try:
            # Step 0: Determine if this request actually needs a workflow
            logger.info(f"🤔 Starting ReAct analysis for: {request}")
            needs_workflow = await self.determine_if_workflow_needed(request)
            
            if not needs_workflow:
                logger.info("💬 Request is conversational/greeting - no workflow needed")
                return {
                    "success": False,
                    "error": "no_workflow_needed",
                    "message": "This appears to be a greeting or conversational message. I can help you create workflows for specific tasks like sending emails, searching for information, or processing data. What would you like to automate?",
                    "reasoning_trace": ["Request analyzed as conversational - no actionable workflow intent detected"],
                    "is_conversational": True
                }
            
            # Step 1: Initial analysis of what's needed
            initial_analysis = await self.reason_about_requirements(request)
            
            # Check if we found any actionable intent
            if not initial_analysis.get("required_steps") and not initial_analysis.get("suggested_connectors"):
                logger.info("🚫 No actionable workflow steps identified")
                return {
                    "success": False,
                    "error": "no_actionable_intent",
                    "message": "I couldn't identify specific actions to automate from your request. Could you be more specific about what you'd like me to help you with? For example: 'Send an email', 'Search for information', or 'Process data'.",
                    "reasoning_trace": self.get_reasoning_trace(),
                    "is_conversational": True
                }
            
            # Step 2: Iterative ReAct loop - build workflow step by step
            workflow_steps = []
            step_number = 1
            
            while not await self.is_workflow_complete(initial_analysis, workflow_steps):
                logger.info(f"🔄 ReAct Step {step_number}: Reasoning about next action")
                
                # REASON: What do I need to do next?
                next_action = await self.reason_next_step(initial_analysis, workflow_steps, request)
                
                if not next_action:
                    logger.info("✅ ReAct agent determined workflow is complete")
                    break
                
                # ACT: Find and configure the right connector
                logger.info(f"⚡ Acting on: {next_action.get('action_type', 'unknown')}")
                connector_result = await self.act_on_connector(next_action, workflow_steps, request)
                
                if connector_result:
                    workflow_steps.append(connector_result)
                    logger.info(f"✅ Completed step {step_number}: {connector_result['connector_name']}")
                
                step_number += 1
                
                # Safety limit
                if step_number > 10:
                    logger.warning("ReAct agent hit step limit, completing workflow")
                    break
            
            # Check if we actually created any workflow steps
            if not workflow_steps:
                logger.info("🚫 No workflow steps were created")
                return {
                    "success": False,
                    "error": "no_workflow_created",
                    "message": "I wasn't able to create a workflow from your request. Could you provide more specific details about what you'd like to automate?",
                    "reasoning_trace": self.get_reasoning_trace(),
                    "is_conversational": True
                }
            
            # Step 3: Build final workflow
            final_workflow = await self.build_final_workflow(workflow_steps, request)
            
            return {
                "success": True,
                "workflow": final_workflow,
                "reasoning_trace": self.get_reasoning_trace(),
                "steps_completed": len(workflow_steps)
            }
            
        except Exception as e:
            logger.error(f"Error in ReAct agent processing: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.get_reasoning_trace()
            }
    
    async def reason_about_requirements(self, request: str) -> Dict[str, Any]:
        """Initial reasoning about what the user wants to accomplish."""
        
        # Get available connectors
        available_connectors = await self.tool_registry.get_tool_metadata()
        
        # Format connector list for reasoning
        connector_list = self._format_connector_list(available_connectors)
        
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
    
    async def reason_next_step(self, initial_analysis: Dict[str, Any], current_steps: List[Dict[str, Any]], original_request: str) -> Optional[Dict[str, Any]]:
        """Reason about what the next step should be."""
        
        if not current_steps:
            # First step - what do we need to start with?
            reasoning_prompt = f"""
            Based on my initial analysis, I need to start building the workflow.
            
            ORIGINAL REQUEST: "{original_request}"
            INITIAL ANALYSIS: {initial_analysis.get('reasoning', '')}
            
            Available connectors: perplexity_search, text_summarizer, gmail_connector, google_sheets, http_request, webhook
            
            What should be the FIRST step in this workflow?
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "connector_name": "exact_connector_name_from_list_above",
                "action_type": "search|process|output",
                "purpose": "what this step accomplishes",
                "reasoning": "why this connector is needed"
            }}
            """
        else:
            # Subsequent steps - what comes next?
            completed_steps = [f"Step {i+1}: {step['connector_name']} - {step['purpose']}" for i, step in enumerate(current_steps)]
            
            reasoning_prompt = f"""
            I've completed these steps so far:
            {chr(10).join(completed_steps)}
            
            ORIGINAL REQUEST: "{original_request}"
            
            Available connectors: perplexity_search, text_summarizer, gmail_connector, google_sheets, http_request, webhook
            
            What should be the NEXT step to complete this workflow?
            
            RESPOND WITH VALID JSON ONLY:
            {{
                "connector_name": "exact_connector_name_from_list_above_or_null_if_complete",
                "action_type": "search|process|output|complete",
                "purpose": "what this step accomplishes",
                "reasoning": "why this connector is needed or why workflow is complete"
            }}
            
            If workflow is complete, use: {{"connector_name": null, "action_type": "complete", "purpose": "workflow complete", "reasoning": "all steps done"}}
            """
        
        if self._client:
            next_step = await self._ai_reason(reasoning_prompt)
            # If AI reasoning failed or returned fallback, use our logic
            if next_step.get("action_type") == "fallback" or not next_step.get("connector_name"):
                logger.info("AI reasoning failed or incomplete, using fallback logic")
                next_step = await self._fallback_next_step(current_steps, original_request)
        else:
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
        """Determine if the workflow is complete."""
        if not steps:
            return False
        
        # Simple heuristic: if we have an output connector (email, sheets, etc.), we're likely done
        output_connectors = ["gmail_connector", "google_sheets", "slack_messenger", "webhook"]
        has_output = any(step["connector_name"] in output_connectors for step in steps)
        
        return has_output and len(steps) >= 2  # At least input + output
    
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
    
    # Helper methods
    
    def _format_connector_list(self, connectors: List[Dict[str, Any]]) -> str:
        """Format connector list for AI reasoning."""
        formatted = []
        for connector in connectors:
            formatted.append(f"- {connector['name']}: {connector.get('description', 'No description')}")
        return "\n".join(formatted)
    
    async def _ai_reason(self, prompt: str) -> Dict[str, Any]:
        """Use AI to reason about the prompt."""
        try:
            messages = [
                {"role": "system", "content": "You are a ReAct agent that reasons step by step about workflow automation. You MUST respond with valid JSON only. No explanations, no markdown, just pure JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse as JSON, fallback to text reasoning
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning(f"AI returned non-JSON response: {content[:200]}...")
                # If AI fails to return JSON, fall back to our logic
                return {"reasoning": content, "action_type": "fallback"}
                
        except Exception as e:
            logger.error(f"AI reasoning failed: {e}")
            return {"reasoning": "AI reasoning unavailable", "action_type": "fallback"}
    
    async def _fallback_reason(self, request: str, connectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback reasoning when AI is not available."""
        return {
            "reasoning": f"Analyzing request: {request}. Available connectors: {len(connectors)}",
            "goal": "Build workflow step by step",
            "approach": "Use available connectors to fulfill user request"
        }
    
    async def _fallback_next_step(self, current_steps: List[Dict[str, Any]], request: str) -> Dict[str, Any]:
        """Intelligent fallback for determining next step based on request analysis."""
        request_lower = request.lower()
        
        if not current_steps:
            # First step - what kind of input do we need?
            if any(keyword in request_lower for keyword in ["search", "find", "blogs", "perplexity"]):
                return {
                    "action_type": "search",
                    "connector_name": "perplexity_search",
                    "purpose": "Search for information based on user request",
                    "user_request": request
                }
            elif any(keyword in request_lower for keyword in ["email", "send", "mail"]):
                return {
                    "action_type": "communication",
                    "connector_name": "gmail_connector", 
                    "purpose": "Send email as requested",
                    "user_request": request
                }
            else:
                # Default to search if unclear
                return {
                    "action_type": "search",
                    "connector_name": "perplexity_search",
                    "purpose": "Gather information for the request",
                    "user_request": request
                }
        
        elif len(current_steps) == 1:
            # Second step - do we need processing?
            if any(keyword in request_lower for keyword in ["summarize", "summary", "combine"]):
                return {
                    "action_type": "process",
                    "connector_name": "text_summarizer",
                    "purpose": "Summarize and process the retrieved information",
                    "user_request": request
                }
            elif any(keyword in request_lower for keyword in ["email", "send", "mail"]):
                return {
                    "action_type": "output",
                    "connector_name": "gmail_connector",
                    "purpose": "Send the results via email",
                    "user_request": request
                }
            else:
                return None  # Complete with one step
        
        elif len(current_steps) == 2:
            # Third step - output
            if any(keyword in request_lower for keyword in ["email", "send", "mail", "gmail"]):
                return {
                    "action_type": "output",
                    "connector_name": "gmail_connector",
                    "purpose": "Send the processed results via email",
                    "user_request": request
                }
            else:
                return None  # Complete
        
        else:
            return None  # Complete - workflow is done
    
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
                    # Reference the most relevant previous step
                    if 'body' in param_name.lower() or 'content' in param_name.lower():
                        # For body/content, prefer summarizer or text processing steps
                        for step in reversed(current_steps):
                            if any(keyword in step['connector_name'] for keyword in ['summariz', 'text', 'process']):
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