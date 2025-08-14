"""
Intelligent Conversation Handler - Smart Intent Detection

This module provides intelligent conversation handling that can distinguish between:
1. Workflow creation requests
2. Questions about existing workflows  
3. General conversational messages
4. Workflow modification requests
5. Help and information requests

The goal is to make the AI agent feel more natural and flexible, like Cursor AI, Kiro, or other modern AI assistants.
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from openai import AsyncAzureOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConversationIntent(Enum):
    """Different types of user intents we can detect."""
    WORKFLOW_CREATION = "workflow_creation"
    WORKFLOW_QUESTION = "workflow_question"
    WORKFLOW_MODIFICATION = "workflow_modification"
    CONVERSATIONAL = "conversational"
    HELP_REQUEST = "help_request"
    APPROVAL_RESPONSE = "approval_response"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class IntentAnalysis:
    """Result of intent analysis."""
    def __init__(
        self,
        intent: ConversationIntent,
        confidence: float,
        reasoning: str,
        extracted_info: Dict[str, Any] = None
    ):
        self.intent = intent
        self.confidence = confidence
        self.reasoning = reasoning
        self.extracted_info = extracted_info or {}


class IntelligentConversationHandler:
    """
    Intelligent conversation handler that can understand user intent
    and route to appropriate response handlers.
    """
    
    def __init__(self):
        self._client: Optional[AsyncAzureOpenAI] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the conversation handler."""
        if self._initialized:
            return
            
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self._client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            logger.info("Intelligent conversation handler initialized with AI")
        else:
            logger.warning("No AI client available, using rule-based intent detection")
        
        self._initialized = True
    
    async def analyze_intent(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """
        Analyze user message to determine intent with deep reasoning and validation.
        
        This method uses multiple layers of analysis to ensure accuracy and prevent
        misinterpretation that could lead to incorrect workflow creation.
        
        Args:
            user_message: The user's message
            context: Optional context including session state, current workflow, etc.
            
        Returns:
            IntentAnalysis with detected intent and confidence
        """
        if not self._initialized:
            await self.initialize()
        
        # Layer 1: Rule-based detection for obvious cases
        rule_based_result = self._rule_based_intent_detection(user_message, context)
        
        # Layer 2: AI-powered deep reasoning for complex cases
        ai_result = None
        if self._client:
            ai_result = await self._ai_intent_analysis(user_message, context)
        
        # Layer 3: Cross-validation and reasoning synthesis
        final_result = await self._synthesize_intent_analysis(
            user_message, context, rule_based_result, ai_result
        )
        
        return final_result
    
    async def _synthesize_intent_analysis(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]],
        rule_result: IntentAnalysis,
        ai_result: Optional[IntentAnalysis]
    ) -> IntentAnalysis:
        """
        Synthesize multiple analysis results with deep reasoning to ensure accuracy.
        This prevents hallucinations and ensures we ask clarifying questions when uncertain.
        """
        # If both analyses agree with high confidence, trust the result
        if ai_result and rule_result.intent == ai_result.intent and min(rule_result.confidence, ai_result.confidence) > 0.8:
            return IntentAnalysis(
                rule_result.intent,
                min(rule_result.confidence, ai_result.confidence),
                f"Cross-validated: {rule_result.reasoning} | {ai_result.reasoning}",
                {**rule_result.extracted_info, **ai_result.extracted_info}
            )
        
        # If analyses disagree, use intelligent conflict resolution
        if ai_result and rule_result.intent != ai_result.intent:
            # If rule-based detected workflow_creation with high confidence, trust it over AI help_request
            if (rule_result.intent == ConversationIntent.WORKFLOW_CREATION and 
                rule_result.confidence > 0.75 and 
                ai_result.intent == ConversationIntent.HELP_REQUEST):
                return IntentAnalysis(
                    rule_result.intent,
                    0.8,
                    f"Rule-based analysis detected clear workflow creation pattern. Trusting over AI uncertainty.",
                    rule_result.extracted_info
                )
            
            # If AI detected workflow_creation with high confidence, trust it over rule-based help_request
            elif (ai_result.intent == ConversationIntent.WORKFLOW_CREATION and 
                  ai_result.confidence > 0.75 and 
                  rule_result.intent == ConversationIntent.HELP_REQUEST):
                return IntentAnalysis(
                    ai_result.intent,
                    0.8,
                    f"AI analysis detected clear workflow creation intent. Trusting over rule-based uncertainty.",
                    ai_result.extracted_info
                )
            
            # For other conflicts, be conservative
            else:
                return IntentAnalysis(
                    ConversationIntent.HELP_REQUEST,
                    0.6,
                    f"Conflicting analysis detected - rule-based: {rule_result.intent.value} vs AI: {ai_result.intent.value}. Being conservative to avoid errors.",
                    {"needs_clarification": True, "conflicting_intents": [rule_result.intent.value, ai_result.intent.value]}
                )
        
        # If only rule-based analysis available (AI failed or not available), use it but be more conservative for truly low confidence
        if not ai_result:
            if rule_result.confidence < 0.6:  # Lowered threshold - only ask for clarification when really uncertain
                return IntentAnalysis(
                    ConversationIntent.HELP_REQUEST,
                    0.6,
                    f"Low confidence in intent detection: {rule_result.reasoning}. Asking for clarification to prevent errors.",
                    {"needs_clarification": True, "uncertain_intent": rule_result.intent.value}
                )
            return rule_result
        
        # Use the higher confidence result, but cap confidence to prevent overconfidence
        if ai_result.confidence > rule_result.confidence:
            return IntentAnalysis(
                ai_result.intent,
                min(ai_result.confidence, 0.85),  # Cap confidence to stay humble
                f"AI analysis preferred: {ai_result.reasoning}",
                ai_result.extracted_info
            )
        else:
            return IntentAnalysis(
                rule_result.intent,
                min(rule_result.confidence, 0.85),  # Cap confidence to stay humble
                f"Rule-based analysis preferred: {rule_result.reasoning}",
                rule_result.extracted_info
            )
    
    def _rule_based_intent_detection(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """Rule-based intent detection for obvious cases."""
        message_lower = user_message.lower().strip()
        
        # Check context first
        if context:
            # If we're awaiting approval, this is likely an approval response
            if context.get("awaiting_approval"):
                approval_keywords = [
                    'approve', 'approved', 'looks good', 'proceed', 'yes', 'ok', 
                    'correct', 'go ahead', 'continue', 'execute', 'run it'
                ]
                modification_keywords = [
                    'change', 'modify', 'update', 'edit', 'fix', 'adjust',
                    'instead', 'replace', 'use', 'different'
                ]
                
                if any(keyword in message_lower for keyword in approval_keywords):
                    return IntentAnalysis(
                        ConversationIntent.APPROVAL_RESPONSE,
                        0.9,
                        "User is approving a workflow plan",
                        {"approval_type": "approve"}
                    )
                elif any(keyword in message_lower for keyword in modification_keywords):
                    return IntentAnalysis(
                        ConversationIntent.WORKFLOW_MODIFICATION,
                        0.85,
                        "User wants to modify the workflow plan",
                        {"modification_request": user_message}
                    )
            
            # If there's an existing workflow, check for questions about it
            if context.get("current_workflow") or context.get("executed_workflow"):
                question_patterns = [
                    r'\bwhat\s+(is|are|does|did)\b',
                    r'\bhow\s+(does|did|is|are)\b',
                    r'\bwhy\s+(is|are|does|did)\b',
                    r'\bwhen\s+(does|did|will)\b',
                    r'\bwhere\s+(is|are|does|did)\b',
                    r'\bcan\s+you\s+(tell|explain|show)\b',
                    r'\bexplain\b',
                    r'\bdescribe\b',
                    r'\btell\s+me\b',
                    r'\bshow\s+me\b'
                ]
                
                workflow_references = [
                    'workflow', 'this', 'it', 'steps', 'process', 'happening',
                    'working', 'doing', 'result', 'output'
                ]
                
                has_question_pattern = any(re.search(pattern, message_lower) for pattern in question_patterns)
                has_workflow_reference = any(ref in message_lower for ref in workflow_references)
                
                if has_question_pattern and has_workflow_reference:
                    return IntentAnalysis(
                        ConversationIntent.WORKFLOW_QUESTION,
                        0.9,
                        "User is asking about the current/existing workflow",
                        {"question_type": "workflow_inquiry"}
                    )
        
        # Greeting detection - use word boundaries to avoid false positives
        greeting_patterns = [
            r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\bhii\b', r'\bhiii\b', r'\bhiiii\b',
            r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b',
            r'\bwhat\'?s up\b', r'\bhow are you\b', r'\bsup\b'
        ]
        
        # Check if message is exactly a greeting or starts with a greeting
        if (message_lower in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'] or
            any(re.search(pattern, message_lower) and len(user_message.split()) <= 3 for pattern in greeting_patterns)):
            return IntentAnalysis(
                ConversationIntent.GREETING,
                0.95,
                "User is greeting the assistant"
            )
        
        # Simple conversational responses
        simple_responses = [
            'thanks', 'thank you', 'ok', 'okay', 'yes', 'no',
            'cool', 'nice', 'great', 'awesome', 'lol', 'haha'
        ]
        if message_lower in simple_responses:
            return IntentAnalysis(
                ConversationIntent.CONVERSATIONAL,
                0.9,
                "User is making a simple conversational response"
            )
        
        # Help requests
        help_keywords = [
            'help', 'how to', 'what can you do', 'what do you do',
            'capabilities', 'features', 'commands', 'options'
        ]
        if any(keyword in message_lower for keyword in help_keywords):
            return IntentAnalysis(
                ConversationIntent.HELP_REQUEST,
                0.85,
                "User is asking for help or information about capabilities"
            )
        
        # Workflow creation detection with intelligence for vague requests
        action_words = [
            'create', 'make', 'build', 'generate', 'setup', 'set up',
            'automate', 'workflow', 'process', 'send', 'email',
            'search', 'find', 'get', 'fetch', 'download', 'upload',
            'summarize', 'analyze', 'connect', 'integrate', 'sync',
            'collect', 'gather', 'retrieve', 'compile', 'extract'
        ]
        
        service_words = [
            'gmail', 'google', 'sheets', 'drive', 'slack', 'notion',
            'airtable', 'youtube', 'webhook', 'api', 'database',
            'email', 'spreadsheet', 'document', 'blog', 'blogs',
            'website', 'websites', 'search', 'perplexity'
        ]
        
        # Detect vague workflow requests that need clarification
        vague_patterns = [
            r'\b(create|make|build|let\'?s create)\s+(a\s+)?(new\s+)?workflow\b',
            r'\b(new\s+)?workflow\b.*\b(please|now|today)\b',
            r'\b(start|begin)\s+(a\s+)?(new\s+)?workflow\b',
            r'\b(let\'?s|can we|i want to)\s+(create|make|build)\b.*\bworkflow\b'
        ]
        
        is_vague_request = any(re.search(pattern, message_lower) for pattern in vague_patterns)
        
        # Check if it's a vague request without specific details
        if is_vague_request:
            # Count specific details mentioned
            has_action = any(action in message_lower for action in action_words if action not in ['create', 'make', 'build', 'workflow'])
            has_service = any(service in message_lower for service in service_words)
            
            # If it's vague (no specific actions or services), treat as help request
            if not has_action and not has_service:
                return IntentAnalysis(
                    ConversationIntent.HELP_REQUEST,
                    0.85,
                    "User wants to create a workflow but needs guidance on what kind",
                    {"workflow_guidance_needed": True}
                )
        
        has_action = any(action in message_lower for action in action_words)
        has_service = any(service in message_lower for service in service_words)
        
        # Check for clear workflow patterns even without explicit services
        clear_workflow_patterns = [
            r'\bmonitor\b.*\bwebsites?\b.*\bchanges?\b',
            r'\btrack\b.*\bcompetitor\b',
            r'\bwatch\b.*\bfor\s+changes?\b',
            r'\bnotify\b.*\bwhen\b.*\bchanges?\b',
            r'\bsummarize\b.*\bemail',
            r'\bfind\b.*\bblog.*\band\s+send\b',
            r'\bsearch\b.*\band\s+email\b',
            r'\bget\b.*\band\s+send\s+to\b',
            r'\bfind\b.*\btop\s+\d+\b.*\band\s+send\b',
            r'\bsearch\b.*\btop\s+\d+\b.*\band\s+email\b',
            r'\bsync\b.*\bdata\b',
            r'\bbackup\b.*\bfiles?\b',
            r'\bgenerate\b.*\breports?\b',
            r'\bautomate\b.*\b(email|data|file|report)',
            r'\bsend\b.*\balert\b',
            r'\bsave\b.*\bto\b.*\b(sheet|database|drive)',
            r'\bbuild\b.*\bautomation\b.*\bfor\b',
            r'\bcreate\b.*\bautomation\b.*\bfor\b',
            r'\bset\s+up\b.*\bautomation\b',
            r'\bsend\b.*\b(message|email)\b.*\bto\b.*@',
            r'\bprocess\b.*\bdata\b',
            r'\bdata\s+processing\b',
            r'\bemail\b.*\bto\b.*@.*\.com',
            r'\bcreate\b.*\bworkflow\b.*\bsend\b.*@',
            r'\bnew\b.*\bworkflow\b.*\bsend\b.*@',
            r'\bworkflow\b.*\bsend\b.*\bmessage\b.*@',
            r'\bset\s+up\b.*\bnotification\b.*\bsystem\b',
            r'\bnotification\b.*\bsystem\b',
            r'\balert\b.*\bsystem\b',
            r'\bset\s+up\b.*\balerts?\b'
        ]
        
        has_clear_workflow_pattern = any(re.search(pattern, message_lower) for pattern in clear_workflow_patterns)
        
        # Check for email addresses (strong indicator of workflow creation)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        has_email = bool(re.search(email_pattern, user_message))
        
        # Strong workflow creation indicators (specific requests)
        if has_email and has_action:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.9,
                "User is requesting workflow creation with specific email destination"
            )
        elif has_action and has_service and len(user_message.split()) > 3:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.8,
                "User is requesting workflow creation with specific actions and services"
            )
        elif has_clear_workflow_pattern:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.85,
                "User has clear workflow intent with recognizable automation pattern"
            )
        elif has_action and len(user_message.split()) > 4 and not is_vague_request:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.7,
                "User is requesting workflow creation with action words"
            )
        
        # If message is very short and doesn't match patterns, likely conversational
        if len(user_message.split()) < 3:
            return IntentAnalysis(
                ConversationIntent.CONVERSATIONAL,
                0.6,
                "Short message without clear workflow intent"
            )
        
        # Default to unknown with low confidence
        return IntentAnalysis(
            ConversationIntent.UNKNOWN,
            0.3,
            "Could not determine clear intent from message"
        )
    
    async def _ai_intent_analysis(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """AI-powered intent analysis for complex cases."""
        try:
            # Build context information
            context_info = ""
            if context:
                if context.get("awaiting_approval"):
                    context_info += "- User was presented with a workflow plan and is awaiting approval\n"
                if context.get("current_workflow"):
                    context_info += "- There is a current workflow in the conversation\n"
                if context.get("executed_workflow"):
                    context_info += "- A workflow was recently executed\n"
                if context.get("conversation_history"):
                    recent_messages = context["conversation_history"][-3:]  # Last 3 messages
                    context_info += f"- Recent conversation: {[msg.get('content', '') for msg in recent_messages]}\n"
            
            prompt = f"""
            You are an intelligent intent analyzer for a workflow automation system. Your job is to carefully analyze user messages to determine their intent while being extremely cautious to prevent errors that could lead to incorrect workflow creation or misunderstanding.

            CRITICAL SAFETY PRINCIPLES:
            1. When in doubt, ask for clarification rather than assume
            2. Be conservative with confidence scores - overconfidence leads to errors
            3. Prefer HELP_REQUEST over WORKFLOW_CREATION when requirements are vague
            4. Consider context carefully to avoid misinterpretation

            USER MESSAGE: "{user_message}"

            CONTEXT:
            {context_info if context_info else "- No additional context"}

            INTENT CATEGORIES (in order of preference when uncertain):
            1. WORKFLOW_CREATION - User has SPECIFIC, CLEAR requirements for a workflow/automation
               ⚠️  Only use if: User specifies WHAT to automate, HOW it should work, or WHICH tools to use
               
            2. WORKFLOW_QUESTION - User is asking about an existing workflow
               ✅ Use if: References "this workflow", "current workflow", or asks about workflow status
               
            3. WORKFLOW_MODIFICATION - User wants to modify an existing workflow
               ✅ Use if: Says "change", "modify", "update" with reference to existing workflow
               
            4. APPROVAL_RESPONSE - User is approving/rejecting a proposed plan
               ✅ Use if: Says "approve", "looks good", "proceed", "yes" in response to a plan
               
            5. HELP_REQUEST - User wants help, guidance, or has vague requests (DEFAULT when uncertain)
               ✅ Use if: Vague workflow requests, general questions, needs guidance
               ✅ PREFER THIS over WORKFLOW_CREATION when requirements are unclear
               
            6. CONVERSATIONAL - General chat, greetings, simple responses
               ✅ Use if: "hi", "thanks", "ok", casual conversation
               
            7. GREETING - User is greeting the assistant
               ✅ Use if: "hello", "hi", "good morning", etc.
               
            8. UNKNOWN - Intent is genuinely unclear after careful analysis

            ANALYSIS FRAMEWORK:
            1. Does the user specify EXACTLY what they want to automate? → WORKFLOW_CREATION
            2. Are they asking about an existing workflow? → WORKFLOW_QUESTION  
            3. Are they greeting or being conversational? → GREETING/CONVERSATIONAL
            4. Are they asking for help or being vague? → HELP_REQUEST
            5. Still unclear? → HELP_REQUEST (be conservative)

            EXAMPLES:
            - "Create a workflow to summarize my emails daily" → WORKFLOW_CREATION (specific task)
            - "Monitor competitive websites for changes" → WORKFLOW_CREATION (clear action and target)
            - "Build an automation for data processing" → WORKFLOW_CREATION (clear automation request)
            - "Send test message to user@email.com" → WORKFLOW_CREATION (specific email action)
            - "Set up notifications when my competitor updates their site" → WORKFLOW_CREATION (specific automation)
            - "Track website changes and alert me" → WORKFLOW_CREATION (clear workflow intent)
            - "Process my data automatically" → WORKFLOW_CREATION (clear processing task)
            - "Set up a notification system" → WORKFLOW_CREATION (clear system setup)
            - "Create alerts for my website" → WORKFLOW_CREATION (specific alert system)
            - "Let's create a new workflow" → HELP_REQUEST (vague, needs clarification)
            - "What is this workflow doing?" → WORKFLOW_QUESTION (about existing)
            - "Hi there" → GREETING
            - "I need help with automation" → HELP_REQUEST

            Respond with JSON only. Be thoughtful and conservative:
            {{
                "intent": "INTENT_CATEGORY",
                "confidence": 0.0-1.0,
                "reasoning": "Detailed explanation of your analysis and why you chose this intent",
                "extracted_info": {{
                    "specificity_level": "high/medium/low",
                    "mentioned_tools": ["list", "of", "tools"],
                    "action_words": ["list", "of", "actions"],
                    "clarity_assessment": "clear/vague/ambiguous"
                }}
            }}
            """
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            result_json = json.loads(result_text)
            
            intent_str = result_json.get("intent", "UNKNOWN")
            try:
                intent = ConversationIntent(intent_str.lower())
            except ValueError:
                intent = ConversationIntent.UNKNOWN
            
            return IntentAnalysis(
                intent,
                float(result_json.get("confidence", 0.5)),
                result_json.get("reasoning", "AI analysis"),
                result_json.get("extracted_info", {})
            )
            
        except Exception as e:
            logger.warning(f"AI intent analysis failed: {e}")
            # Return None instead of UNKNOWN so rule-based analysis can take precedence
            return None
    
    async def generate_conversational_response(
        self,
        intent: ConversationIntent,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate thoughtful, reasoning-driven conversational responses.
        
        This method prioritizes accuracy and user safety by asking clarifying questions
        when there's any ambiguity, rather than making assumptions that could lead to errors.
        """
        
        if intent == ConversationIntent.GREETING:
            return "Hello! I'm here to help you create workflows and automate tasks. What would you like to build today?"
        
        elif intent == ConversationIntent.CONVERSATIONAL:
            if "thanks" in user_message.lower() or "thank you" in user_message.lower():
                return "You're welcome! Is there anything else I can help you with?"
            elif user_message.lower() in ["ok", "okay", "yes"]:
                return "Great! What would you like to work on next?"
            elif user_message.lower() in ["no"]:
                return "No problem! Let me know if you need help with anything else."
            else:
                return "I understand. Is there a specific workflow or automation you'd like me to help you create?"
        
        elif intent == ConversationIntent.HELP_REQUEST:
            return await self._generate_thoughtful_help_response(user_message, context)
        
        elif intent == ConversationIntent.WORKFLOW_QUESTION:
            if context and context.get("current_workflow"):
                workflow = context["current_workflow"]
                return self._explain_current_workflow(workflow)
            elif context and context.get("executed_workflow"):
                workflow = context["executed_workflow"]
                return self._explain_executed_workflow(workflow)
            else:
                return "I don't see a current workflow to explain. Would you like me to create a new workflow for you?"
        
        elif intent == ConversationIntent.UNKNOWN:
            return "I'm not sure I understand what you're looking for. Could you please clarify? I can help you create workflows, answer questions about existing workflows, or provide information about my capabilities."
        
        else:
            return "I'm here to help! What would you like to work on?"
    
    def _explain_current_workflow(self, workflow: Dict[str, Any]) -> str:
        """Explain what's happening in the current workflow."""
        if not workflow or not workflow.get("steps"):
            return "The current workflow doesn't have any steps defined yet."
        
        steps = workflow["steps"]
        explanation = f"Here's what this workflow does:\n\n"
        
        for i, step in enumerate(steps, 1):
            connector_name = step.get("connector_name", "Unknown")
            purpose = step.get("purpose", "No description available")
            
            # Make connector names more readable
            readable_name = connector_name.replace("_", " ").title()
            if "Connector" in readable_name:
                readable_name = readable_name.replace(" Connector", "")
            
            explanation += f"**Step {i}: {readable_name}**\n"
            explanation += f"   {purpose}\n\n"
        
        # Add summary
        if len(steps) == 1:
            explanation += "This is a simple single-step workflow."
        else:
            explanation += f"This workflow has {len(steps)} steps that work together to complete the automation."
        
        return explanation
    
    def _explain_executed_workflow(self, workflow: Dict[str, Any]) -> str:
        """Explain what happened in an executed workflow."""
        explanation = "Here's what the executed workflow accomplished:\n\n"
        explanation += self._explain_current_workflow(workflow)
        explanation += "\n\n✅ This workflow has been executed and should have completed its tasks."
        return explanation
    
    async def _generate_thoughtful_help_response(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a thoughtful help response that asks clarifying questions
        and provides guidance based on the specific context.
        """
        extracted_info = context.get("extracted_info", {}) if context else {}
        
        # Handle clarification requests (when we're uncertain about intent)
        if extracted_info.get("needs_clarification"):
            return await self._generate_clarification_request(user_message, extracted_info)
        
        # Handle workflow guidance requests
        if extracted_info.get("workflow_guidance_needed"):
            return await self._generate_workflow_guidance(user_message, context)
        
        # General help request
        return await self._generate_general_help_response(user_message, context)
    
    async def _generate_clarification_request(
        self,
        user_message: str,
        extracted_info: Dict[str, Any]
    ) -> str:
        """Generate a clarification request when we're uncertain about user intent."""
        
        base_message = "I want to make sure I understand exactly what you need to avoid any mistakes. "
        
        if "conflicting_intents" in extracted_info:
            intents = extracted_info["conflicting_intents"]
            return f"""{base_message}Your message could be interpreted in different ways:

🤔 **I'm seeing potential for:**
- {intents[0].replace('_', ' ').title()}
- {intents[1].replace('_', ' ').title()}

**To help you accurately, could you clarify:**
- Are you asking about an existing workflow, or do you want to create a new one?
- If creating new, what specific task do you want to automate?
- If asking about existing, which workflow are you referring to?

This helps me give you the right response and avoid any confusion."""
        
        elif "uncertain_intent" in extracted_info:
            uncertain = extracted_info["uncertain_intent"]
            return f"""{base_message}I think you might be looking for {uncertain.replace('_', ' ')}, but I want to be certain.

**Could you help me understand:**
- What exactly are you trying to accomplish?
- Are you working with an existing workflow or creating something new?
- What specific outcome are you looking for?

This way I can provide the most helpful and accurate response."""
        
        return f"""{base_message}Could you provide a bit more detail about what you're looking for? 

**For example:**
- Are you asking about something specific?
- Do you need help with a particular task?
- Are you looking to create or modify something?

The more specific you can be, the better I can assist you!"""
    
    async def _generate_workflow_guidance(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate thoughtful workflow guidance with clarifying questions."""
        
        return """I'd love to help you create a workflow! To build something that truly meets your needs, let me ask a few thoughtful questions:

🎯 **What's your main goal?**
- What task or process do you want to automate?
- What problem are you trying to solve?

📊 **What data or systems are involved?**
- Do you work with emails, spreadsheets, documents, or other tools?
- Which apps or services do you use regularly?

⏰ **When should this happen?**
- Should it run automatically on a schedule?
- Should it trigger when something specific happens?
- Or do you want to run it manually when needed?

🔍 **Here are some examples to spark ideas:**

**Email & Communication:**
- "Summarize my daily emails and send me a digest"
- "Auto-file emails from specific senders into folders"
- "Send me alerts when important emails arrive"

**Data & Organization:**
- "Sync data between my CRM and spreadsheet"
- "Backup important files to cloud storage daily"
- "Generate weekly reports from my data"

**Content & Research:**
- "Monitor competitor websites for changes"
- "Save interesting articles to my reading list"
- "Research topics and compile findings"

**What resonates with you, or what specific challenge are you facing?** The more details you share, the better I can design something perfect for your needs!"""
    
    async def _generate_general_help_response(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a general help response with thoughtful guidance."""
        
        return """I'm here to help you create powerful automated workflows! Here's what I can do:

🔧 **Workflow Creation**: Build multi-step automations that connect different tools and services
📧 **Email Automation**: Work with Gmail to manage, process, and organize your emails
📊 **Data Processing**: Connect spreadsheets, databases, and apps to sync and transform data
🔍 **Information Gathering**: Search the web, YouTube, and other sources for information
💻 **Code Execution**: Run custom scripts and process data programmatically
🔗 **API Integration**: Connect to webhooks and external services

**To get started, I need to understand your specific needs:**

❓ **What would you like to automate?**
- A repetitive task you do regularly?
- Data that needs to move between different apps?
- Notifications or alerts you want to receive?
- Information you need to gather or process?

**Examples of what I can help with:**
- "I spend too much time organizing my emails"
- "I need to sync data between my tools"
- "I want to monitor something and get notified"
- "I have files that need processing"

**What's your biggest time-consuming task that you'd love to automate?** Be as specific as possible - the more details you provide, the better I can help you build something truly useful!"""


# Global instance
_conversation_handler: Optional[IntelligentConversationHandler] = None

async def get_conversation_handler() -> IntelligentConversationHandler:
    """Get the global conversation handler instance."""
    global _conversation_handler
    if _conversation_handler is None:
        _conversation_handler = IntelligentConversationHandler()
        await _conversation_handler.initialize()
    return _conversation_handler