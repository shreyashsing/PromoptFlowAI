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
    TECHNICAL_QUESTION = "technical_question"  # New: Questions about how connectors/steps work
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
            
            # If either analysis detected technical_question with good confidence, prefer it
            elif (rule_result.intent == ConversationIntent.TECHNICAL_QUESTION and 
                  rule_result.confidence > 0.7):
                return IntentAnalysis(
                    rule_result.intent,
                    0.8,
                    f"Rule-based analysis detected clear technical question. Trusting over conflicting AI analysis.",
                    rule_result.extracted_info
                )
            elif (ai_result.intent == ConversationIntent.TECHNICAL_QUESTION and 
                  ai_result.confidence > 0.7):
                return IntentAnalysis(
                    ai_result.intent,
                    0.8,
                    f"AI analysis detected clear technical question. Trusting over conflicting rule-based analysis.",
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
        
        # Check for workflow creation patterns FIRST (before technical questions)
        # This prevents workflow creation requests from being misclassified as technical questions
        workflow_creation_patterns = [
            r'\b(generate|create|build|make)\b.*\b(template|response|automation|workflow|system|agent)\b',
            r'\b(automate|automation)\b.*\b(responses?|inquiries|questions|customer|support)\b',
            r'\b(template|response template)\b.*\b(addressing|for|about)\b',
            r'\b(goal|task|objective)\b.*:.*\b(automate|generate|create|build)\b',
            r'\b(desired output|expected response|output)\b.*:.*\b(template|response)\b',
            r'\bresponse\s+template\b.*\b(placeholders?|variables?|customer)\b',
            r'\bcustomer\s+(service|support|inquiries|questions)\b.*\b(template|automation|responses?)\b',
            r'\b(skincare|product)\s+(features?|benefits?|ingredients?)\b.*\b(template|response|automation)\b'
        ]
        
        has_workflow_creation_pattern = any(re.search(pattern, message_lower) for pattern in workflow_creation_patterns)
        
        if has_workflow_creation_pattern:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.9,
                "User is requesting workflow creation for template generation or automation",
                {"workflow_type": "template_generation"}
            )

        # Check for technical questions AFTER workflow creation patterns
        # This prevents technical questions from being misclassified as workflow questions
        technical_question_patterns = [
            r'\bhow\s+(is|are|does|do)\b.*\b(processing|processed|working|works|storing|stored|sending|sent|passing|passed)\b',
            r'\bwhat\s+(is|are|does|do)\b.*\b(connector|step|parameter)\b',
            r'\bhow\s+(does|do|is|are)\b.*\b(youtube|gmail|sheets|drive|notion|perplexity|summarizer|translate)\b.*\b(work|process|extract|connect)\b',
            r'\bwhat\s+(data|information)\b.*\b(stored|processed|extracted|passed|sent|received)\b.*\b(connector|step|workflow)\b',
            r'\bhow\s+.*\b(data flow|data flows|content flows|information flows)\b',
            r'\bwhat\s+.*\b(parameters|configuration|settings|options)\b.*\b(used|needed|required)\b.*\b(connector|step)\b',
            r'\bhow\s+.*\b(extracted|data)\b.*\b(from|to)\b.*\b(youtube|gmail|sheets|drive|notion)\b.*\b(connector|step)\b',
            r'\bwhat\s+.*\b(format|structure|type)\b.*\b(data|output|input)\b.*\b(connector|step|workflow)\b',
            r'\bhow\s+.*\b(connector|step|tool)\b.*\b(communicates?|connects?|integrates?)\b',
            r'\bwhat\s+.*\b(api|endpoint|method|function)\b.*\b(called|used|invoked)\b.*\b(connector|step)\b'
        ]
        
        connector_names = [
            'youtube', 'gmail', 'sheets', 'drive', 'notion', 'perplexity', 
            'summarizer', 'translate', 'airtable', 'webhook', 'http'
        ]
        
        has_technical_pattern = any(re.search(pattern, message_lower) for pattern in technical_question_patterns)
        mentions_connector = any(connector in message_lower for connector in connector_names)
        
        # More specific technical question detection - must have both connector mention AND technical context
        is_technical_question = (
            has_technical_pattern or 
            (mentions_connector and 
             any(word in message_lower for word in ['how', 'what']) and
             any(tech_word in message_lower for tech_word in ['processing', 'data flow', 'extract', 'api', 'parameter', 'configuration']) and
             not any(creation_word in message_lower for creation_word in ['generate', 'create', 'build', 'automate', 'template']))
        )
        
        if is_technical_question:
            return IntentAnalysis(
                ConversationIntent.TECHNICAL_QUESTION,
                0.85,
                "User is asking a technical question about how connectors or workflow steps work",
                {"question_type": "technical", "mentioned_connectors": [c for c in connector_names if c in message_lower]}
            )

        # Check context after technical questions
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
        
        # Check for agent/AI assistant specifications FIRST (before help requests)
        # This prevents "capabilities" in agent specs from being misclassified as help requests
        agent_specification_patterns = [
            r'\byou\s+are\b.*\bai\b',
            r'\byou\s+are\b.*\bassistant\b',
            r'\byou\s+are\b.*\bagent\b',
            r'\bintelligent\b.*\bassistant\b',
            r'\bresearch\b.*\bassistant\b',
            r'\bcapabilities\b.*:',
            r'\bunderstand\s+content\b',
            r'\bcite\b.*\bwrite\b',
            r'\bresearch\s+tools\b',
            r'\busability\s+features\b',
            r'\bresponse\s+behavior\b',
            r'\blimitations\b.*:',
            r'\bworld-class\b.*\bassistant\b',
            r'\btrusted\s+by\b.*\bresearchers\b'
        ]
        
        has_agent_specification = any(re.search(pattern, message_lower) for pattern in agent_specification_patterns)
        
        # Check for detailed specifications (long, structured requests)
        is_detailed_spec = len(user_message) > 500 and any([
            "capabilities" in message_lower,
            "features" in message_lower,
            "behavior" in message_lower,
            "limitations" in message_lower,
            user_message.count('\n') > 5,  # Multi-line structured request
            user_message.count(':') > 3    # Structured with colons (like specifications)
        ])
        
        if has_agent_specification or is_detailed_spec:
            return IntentAnalysis(
                ConversationIntent.WORKFLOW_CREATION,
                0.9,
                "User is providing detailed agent/assistant specification for workflow creation"
            )

        # Help requests (moved after agent specification check)
        help_keywords = [
            'help', 'how to', 'what can you do', 'what do you do',
            'capabilities', 'features', 'commands', 'options'
        ]
        # Only trigger help request if it's NOT an agent specification
        if any(keyword in message_lower for keyword in help_keywords) and not has_agent_specification and not is_detailed_spec:
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
            'collect', 'gather', 'retrieve', 'compile', 'extract',
            'template', 'response', 'automation'
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
            r'\bgenerate\b.*\b(template|response)\b',
            r'\b(template|response)\b.*\b(customer|inquiry|question)\b',
            r'\bcustomer\s+(service|support|inquiries)\b.*\b(automate|template|response)\b',
            r'\b(automate|automation)\b.*\b(responses?|inquiries|customer)\b',
            r'\bresponse\s+template\b.*\b(addressing|for|about)\b',
            r'\btemplate\b.*\b(placeholders?|variables?|customer name)\b',
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

            INTENT CATEGORIES:
            1. WORKFLOW_CREATION - User wants to create a workflow/automation/agent
               ✅ Use if: 
               - Describes an agent, assistant, or automation system
               - Provides detailed capabilities or requirements
               - Mentions specific tools, integrations, or workflows
               - Describes what they want to build or create
               - Uses phrases like "I want to create", "build an agent", "automate", etc.
               - Provides comprehensive specifications or requirements
               
            2. WORKFLOW_QUESTION - User is asking about an existing workflow
               ✅ Use if: References "this workflow", "current workflow", or asks about workflow status
               
            3. WORKFLOW_MODIFICATION - User wants to modify an existing workflow
               ✅ Use if: Says "change", "modify", "update" with reference to existing workflow
               
            4. TECHNICAL_QUESTION - User is asking how connectors/steps work technically
               ✅ Use if: 
               - Asks "how does [connector] work", "what data is processed", "how is content extracted"
               - Questions about data flow, processing, storage, parameters
               - Technical questions about specific connectors (YouTube, Gmail, etc.)
               - Questions about how data moves between workflow steps
               
            5. APPROVAL_RESPONSE - User is approving/rejecting a proposed plan
               ✅ Use if: Says "approve", "looks good", "proceed", "yes" in response to a plan
               
            6. HELP_REQUEST - User wants general help or guidance
               ✅ Use if: Simple questions, requests for information, general guidance
               
            7. CONVERSATIONAL - General chat, greetings, simple responses
               ✅ Use if: "hi", "thanks", "ok", casual conversation
               
            8. GREETING - User is greeting the assistant
               ✅ Use if: "hello", "hi", "good morning", etc.
               
            9. UNKNOWN - Intent is genuinely unclear after careful analysis

            ANALYSIS FRAMEWORK:
            1. Does the user describe an agent, system, or automation they want to build? → WORKFLOW_CREATION
            2. Do they provide detailed specifications or capabilities? → WORKFLOW_CREATION
            3. Are they asking about an existing workflow? → WORKFLOW_QUESTION  
            4. Are they greeting or being conversational? → GREETING/CONVERSATIONAL
            5. Are they asking for general help? → HELP_REQUEST
            6. Still unclear? → UNKNOWN

            EXAMPLES:
            - "Create a workflow to summarize my emails daily" → WORKFLOW_CREATION (specific task)
            - "You are Clara AI, an intelligent research assistant..." → WORKFLOW_CREATION (agent specification)
            - "Build an AI agent that can process documents and generate citations" → WORKFLOW_CREATION (agent description)
            - "I want to create an automation that monitors websites and sends alerts" → WORKFLOW_CREATION (clear automation)
            - "Monitor competitive websites for changes" → WORKFLOW_CREATION (clear action and target)
            - "How does YouTube connector extract content?" → TECHNICAL_QUESTION (technical inquiry)
            - "What data is the text summarizer processing?" → TECHNICAL_QUESTION (data flow question)
            - "How is extracted content from youtube processing?" → TECHNICAL_QUESTION (processing question)
            - "What parameters does Gmail connector use?" → TECHNICAL_QUESTION (parameter question)
            - "How does data flow from YouTube to text summarizer?" → TECHNICAL_QUESTION (data flow)
            - "What format does the YouTube connector output?" → TECHNICAL_QUESTION (output format)
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

            Respond with valid JSON only. Keep reasoning concise and on one line:
            {{
                "intent": "INTENT_CATEGORY",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation of your analysis (keep this short and on one line)",
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
            
            # Clean up common JSON formatting issues
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # Try to extract JSON if it's embedded in other text
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            try:
                result_json = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed for AI response: {e}")
                logger.warning(f"Raw response: {result_text[:500]}...")
                
                # Try to fix common JSON issues and parse again
                try:
                    # Fix unescaped newlines in strings
                    fixed_text = result_text.replace('\n', '\\n').replace('\r', '\\r')
                    # Fix unescaped quotes
                    fixed_text = re.sub(r'(?<!\\)"(?=\s*[^:,}\]])', '\\"', fixed_text)
                    result_json = json.loads(fixed_text)
                    logger.info("Successfully parsed JSON after fixing formatting issues")
                except json.JSONDecodeError as e2:
                    logger.warning(f"JSON parsing failed even after fixes: {e2}")
                    # Return None to fall back to rule-based analysis
                    return None
            
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
        
        elif intent == ConversationIntent.TECHNICAL_QUESTION:
            return await self._generate_technical_explanation(user_message, context)
        
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

    async def _generate_technical_explanation(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate detailed technical explanations about connectors, data flow, and processing.
        This addresses the user's need for specific technical information about how workflows operate.
        """
        message_lower = user_message.lower()
        
        # Use AI to intelligently analyze and explain any connector
        return await self._generate_intelligent_connector_explanation(user_message)
        

        
        # Handle data flow questions
        if any(phrase in message_lower for phrase in ["data flow", "how data", "content flow", "information flow"]):
            return """## Workflow Data Flow

**Data flows between connectors in a structured pipeline:**

1. **Source Connector** (e.g., YouTube, Gmail) extracts raw data
2. **Processing Connector** (e.g., Text Summarizer) transforms the data
3. **Destination Connector** (e.g., Notion, Sheets) stores the results

**Data Format:**
- Each connector outputs structured JSON data
- Common fields: content, metadata, timestamp, source_info
- Data is automatically passed between connected steps
- Error handling preserves data integrity

**Example Flow:**
YouTube → Text Summarizer → Notion
1. YouTube extracts video transcript and metadata
2. Text Summarizer processes the transcript into key points
3. Notion creates a new page with the summary and metadata"""
        
        # Handle general processing questions
        if any(word in message_lower for word in ["processing", "process", "work", "works"]):
            return """## How Workflow Processing Works

**Execution Flow:**
1. **Trigger**: Workflow starts (manual, scheduled, or webhook)
2. **Authentication**: Connectors authenticate with their services
3. **Data Extraction**: Source connectors fetch data from external services
4. **Processing**: Transform, filter, or analyze the extracted data
5. **Output**: Send processed data to destination services

**Data Handling:**
- All data is processed in JSON format for consistency
- Each step validates input and handles errors gracefully
- Large datasets are processed in chunks to manage memory
- Sensitive data is encrypted in transit and at rest

**Error Management:**
- Failed steps are retried automatically
- Detailed logs help troubleshoot issues
- Partial failures don't stop the entire workflow"""
        
        # Fallback for unrecognized technical questions
        return """I'd be happy to explain the technical details! Could you be more specific about what you'd like to know?

**I can explain:**
- How specific connectors work (YouTube, Gmail, Sheets, etc.)
- Data flow between workflow steps
- Processing and transformation details
- Parameters and configuration options
- Authentication and security

**Example questions:**
- "How does the YouTube connector extract video content?"
- "What data format does Gmail connector output?"
- "How does data flow from YouTube to Text Summarizer?"
- "What parameters does the Notion connector use?"

What specific aspect would you like me to explain in detail?"""

    async def _generate_intelligent_connector_explanation(self, user_message: str) -> str:
        """
        Generate intelligent explanations for ANY connector using AI analysis.
        This scales to unlimited connectors without hardcoding anything.
        """
        if not self._client:
            return self._generate_fallback_technical_response(user_message)
        
        try:
            # Get available connectors dynamically
            available_connectors = await self._get_all_available_connectors()
            
            # Create comprehensive AI prompt for intelligent analysis
            prompt = f"""
            You are an expert technical documentation specialist for workflow automation connectors. 
            Your job is to provide comprehensive, accurate technical explanations about how connectors work.

            USER QUESTION: "{user_message}"

            AVAILABLE CONNECTORS IN SYSTEM:
            {self._format_connector_list_for_ai(available_connectors)}

            INSTRUCTIONS:
            1. Analyze the user's question to identify which connector(s) they're asking about
            2. Determine what aspect they want to know (data extraction, processing, parameters, data flow, etc.)
            3. Provide a detailed, technical explanation that covers:
               - How the connector works internally
               - What data it extracts/processes
               - Data formats and structures
               - Authentication methods
               - API interactions
               - Processing steps
               - Integration with other connectors
               - Common use cases and applications

            TECHNICAL DEPTH REQUIREMENTS:
            - Be specific about APIs, data formats, and technical processes
            - Explain authentication mechanisms (OAuth 2.0, API keys, etc.)
            - Detail data transformation and processing steps
            - Describe error handling and retry logic
            - Explain how data flows between connectors
            - Include relevant technical specifications

            RESPONSE FORMAT:
            Structure your response with clear headings and detailed explanations.
            Use technical language appropriate for developers and system architects.
            Provide concrete examples and specific implementation details.

            If the user asks about data flow between connectors, explain the complete pipeline.
            If they ask about specific parameters, detail the configuration options.
            If they ask about processing, explain the step-by-step technical workflow.

            Generate a comprehensive technical explanation that directly answers their question.
            """
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"AI connector explanation failed: {e}")
            return self._generate_fallback_technical_response(user_message)

    async def _get_all_available_connectors(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive information about all available connectors.
        This provides the AI with context about the entire system.
        """
        try:
            from app.services.tool_registry import get_tool_registry
            
            tool_registry = await get_tool_registry()
            available_tools = await tool_registry.get_available_tools()
            
            connectors = []
            
            # Handle different tool registry formats
            if isinstance(available_tools, list):
                for tool in available_tools:
                    if hasattr(tool, 'name'):
                        connectors.append({
                            'name': tool.name,
                            'description': getattr(tool, 'description', 'Workflow connector'),
                            'type': getattr(tool, 'type', 'connector'),
                            'category': getattr(tool, 'category', 'general')
                        })
                    elif isinstance(tool, dict):
                        connectors.append({
                            'name': tool.get('name', 'unknown'),
                            'description': tool.get('description', 'Workflow connector'),
                            'type': tool.get('type', 'connector'),
                            'category': tool.get('category', 'general')
                        })
            elif isinstance(available_tools, dict):
                for name, tool in available_tools.items():
                    if hasattr(tool, 'description'):
                        connectors.append({
                            'name': name,
                            'description': tool.description,
                            'type': getattr(tool, 'type', 'connector'),
                            'category': getattr(tool, 'category', 'general')
                        })
                    else:
                        connectors.append({
                            'name': name,
                            'description': 'Workflow connector',
                            'type': 'connector',
                            'category': 'general'
                        })
            
            return connectors
            
        except Exception as e:
            logger.warning(f"Failed to get available connectors: {e}")
            # Return basic connector list as fallback
            return [
                {'name': 'youtube', 'description': 'YouTube video and channel data extraction', 'category': 'media'},
                {'name': 'gmail', 'description': 'Gmail email management and automation', 'category': 'communication'},
                {'name': 'google_sheets', 'description': 'Google Sheets data manipulation', 'category': 'data'},
                {'name': 'google_drive', 'description': 'Google Drive file management', 'category': 'storage'},
                {'name': 'notion', 'description': 'Notion workspace and database management', 'category': 'productivity'},
                {'name': 'airtable', 'description': 'Airtable database operations', 'category': 'data'},
                {'name': 'perplexity_search', 'description': 'AI-powered search and research', 'category': 'ai'},
                {'name': 'text_summarizer', 'description': 'AI text summarization and analysis', 'category': 'ai'},
                {'name': 'google_translate', 'description': 'Language translation services', 'category': 'ai'},
                {'name': 'webhook', 'description': 'HTTP webhook integration', 'category': 'integration'},
                {'name': 'http_request', 'description': 'HTTP API requests and responses', 'category': 'integration'},
                {'name': 'code_connector', 'description': 'Custom code execution', 'category': 'development'}
            ]

    def _format_connector_list_for_ai(self, connectors: List[Dict[str, Any]]) -> str:
        """Format connector list for AI analysis."""
        if not connectors:
            return "No connectors available"
        
        formatted = []
        for connector in connectors:
            name = connector.get('name', 'unknown')
            description = connector.get('description', 'No description')
            category = connector.get('category', 'general')
            formatted.append(f"- {name} ({category}): {description}")
        
        return "\n".join(formatted)

    def _generate_fallback_technical_response(self, user_message: str) -> str:
        """
        Generate a technical response when AI is not available.
        This still provides useful information without hardcoding specific connectors.
        """
        message_lower = user_message.lower()
        
        # Extract connector name from message
        connector_name = None
        for word in message_lower.split():
            if word in ['youtube', 'gmail', 'sheets', 'drive', 'notion', 'airtable', 
                       'perplexity', 'summarizer', 'translate', 'webhook', 'http']:
                connector_name = word
                break
        
        if connector_name:
            display_name = connector_name.replace('_', ' ').title()
            
            if any(word in message_lower for word in ["extract", "extraction", "data", "content"]):
                return f"""## {display_name} Connector - Technical Data Extraction

**Data Extraction Process:**
The {display_name} connector uses standard API integration patterns to extract data from its source service. It handles authentication, makes structured API calls, and processes the returned data into a standardized format.

**Technical Implementation:**
- **Authentication**: Secure connection using OAuth 2.0 or API key authentication
- **API Communication**: RESTful API calls with proper error handling and rate limiting
- **Data Processing**: Raw API responses are parsed, validated, and transformed
- **Output Format**: Structured JSON data with consistent field naming and types

**Data Flow:**
1. Authentication and connection establishment
2. API request with specified parameters
3. Response processing and data validation
4. Data transformation to standard format
5. Output preparation for downstream connectors

**Integration:**
The connector outputs standardized JSON data that can be consumed by any downstream connector in your workflow, enabling seamless data flow and processing."""
            
            elif any(word in message_lower for word in ["process", "processing", "work", "flow"]):
                return f"""## {display_name} Connector - Processing Workflow

**Step-by-Step Processing:**
1. **Initialization**: Connector loads configuration and validates parameters
2. **Authentication**: Establishes secure connection to the service
3. **Data Retrieval**: Makes API calls to fetch requested data
4. **Processing**: Transforms and validates the retrieved data
5. **Output Generation**: Formats data for downstream connectors

**Technical Architecture:**
- **Error Handling**: Comprehensive error detection and recovery mechanisms
- **Rate Limiting**: Respects API limits and implements backoff strategies
- **Data Validation**: Ensures data integrity and format consistency
- **Logging**: Detailed operation logs for debugging and monitoring

**Performance Optimization:**
- Efficient API usage with batch operations where possible
- Caching mechanisms to reduce redundant API calls
- Asynchronous processing for improved throughput
- Memory management for large data sets"""
            
            else:
                return f"""## {display_name} Connector - Technical Overview

**Functionality:**
This connector provides integration with {display_name} services, enabling automated data exchange and workflow automation.

**Technical Capabilities:**
- **Data Access**: Secure access to service APIs and data sources
- **Authentication**: Industry-standard security protocols
- **Data Processing**: Intelligent data transformation and formatting
- **Integration**: Seamless connectivity with other workflow components

**Architecture:**
- **Modular Design**: Clean separation of concerns for maintainability
- **Scalable Processing**: Handles varying data volumes efficiently
- **Error Resilience**: Robust error handling and recovery mechanisms
- **Monitoring**: Comprehensive logging and performance metrics

**Use Cases:**
- Automated data synchronization
- Workflow trigger and response handling
- Data transformation and enrichment
- Integration with external systems and services

**Configuration:**
The connector supports flexible configuration options to customize behavior, authentication methods, and data processing parameters according to your specific requirements."""
        
        # Generic technical response for unrecognized connectors
        return """## Connector Technical Architecture

**How Workflow Connectors Work:**

**Core Processing Pipeline:**
1. **Authentication & Authorization**: Secure connection establishment
2. **Parameter Configuration**: Dynamic parameter handling and validation
3. **Data Acquisition**: API calls, file processing, or service integration
4. **Data Transformation**: Format conversion and standardization
5. **Output Generation**: Structured data for downstream processing

**Technical Standards:**
- **Security**: OAuth 2.0, API keys, encrypted connections
- **Data Format**: Standardized JSON with consistent schemas
- **Error Handling**: Comprehensive exception management and retry logic
- **Performance**: Optimized for throughput and resource efficiency

**Integration Patterns:**
- **Input Processing**: Handles various data sources and formats
- **Transformation Logic**: Converts data between different schemas
- **Output Standardization**: Ensures compatibility with downstream connectors
- **State Management**: Maintains processing context and error states

**Scalability Features:**
- **Batch Processing**: Efficient handling of large data sets
- **Async Operations**: Non-blocking processing for improved performance
- **Resource Management**: Optimized memory and CPU usage
- **Monitoring**: Real-time performance and health metrics

For specific connector details, please specify which connector you're interested in learning about."""

    async def _get_dynamic_connector_info(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically get connector information from the tool registry.
        This scales to any number of connectors without hardcoding.
        """
        try:
            # Import here to avoid circular imports
            from app.services.tool_registry import get_tool_registry
            
            # Get tool registry (this contains all connector metadata)
            tool_registry = await get_tool_registry()
            
            # Get all available tools/connectors
            available_tools = await tool_registry.get_available_tools()
            logger.info(f"Available tools type: {type(available_tools)}, count: {len(available_tools) if hasattr(available_tools, '__len__') else 'unknown'}")
            
            # Find mentioned connector in the user message
            message_lower = user_message.lower()
            mentioned_connector = None
            
            # Handle different tool registry formats
            if isinstance(available_tools, dict):
                # If tools are returned as a dictionary
                for tool_name, tool_obj in available_tools.items():
                    if (tool_name.lower() in message_lower or 
                        tool_name.lower().replace('_', ' ') in message_lower or
                        tool_name.lower().replace('_', '') in message_lower):
                        mentioned_connector = tool_obj
                        break
            elif isinstance(available_tools, list):
                # If tools are returned as a list
                for tool in available_tools:
                    if hasattr(tool, 'name'):
                        tool_name = tool.name.lower()
                        # Check various name formats
                        if (tool_name in message_lower or 
                            tool_name.replace('_', ' ') in message_lower or
                            tool_name.replace('_', '') in message_lower):
                            mentioned_connector = tool
                            break
                    elif isinstance(tool, dict) and 'name' in tool:
                        tool_name = tool['name'].lower()
                        if (tool_name in message_lower or 
                            tool_name.replace('_', ' ') in message_lower or
                            tool_name.replace('_', '') in message_lower):
                            mentioned_connector = tool
                            break
            
            if mentioned_connector:
                # Get detailed metadata for this connector
                try:
                    tool_metadata = await tool_registry.get_tool_metadata()
                    # Handle both dict and list formats
                    if isinstance(tool_metadata, dict):
                        connector_metadata = tool_metadata.get(mentioned_connector.name, {})
                    elif isinstance(tool_metadata, list):
                        # Find metadata by name in list
                        connector_metadata = {}
                        for metadata in tool_metadata:
                            if isinstance(metadata, dict) and metadata.get('name') == mentioned_connector.name:
                                connector_metadata = metadata
                                break
                    else:
                        connector_metadata = {}
                except Exception as e:
                    logger.warning(f"Failed to get tool metadata: {e}")
                    connector_metadata = {}
                
                # Handle both object and dict formats for mentioned_connector
                if hasattr(mentioned_connector, 'name'):
                    # Object format
                    connector_name = mentioned_connector.name
                    connector_description = getattr(mentioned_connector, 'description', 'Connector for workflow automation')
                    connector_parameters = getattr(mentioned_connector, 'parameters', {})
                elif isinstance(mentioned_connector, dict):
                    # Dict format
                    connector_name = mentioned_connector.get('name', 'unknown')
                    connector_description = mentioned_connector.get('description', 'Connector for workflow automation')
                    connector_parameters = mentioned_connector.get('parameters', {})
                else:
                    # Fallback
                    connector_name = str(mentioned_connector)
                    connector_description = 'Connector for workflow automation'
                    connector_parameters = {}
                
                return {
                    "name": connector_name,
                    "display_name": connector_name.replace('_', ' ').title(),
                    "description": connector_description,
                    "metadata": connector_metadata,
                    "parameters": connector_parameters,
                    "tool_object": mentioned_connector
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get dynamic connector info: {e}")
            return None

    async def _generate_dynamic_connector_explanation(
        self, 
        connector_info: Dict[str, Any], 
        user_message: str
    ) -> str:
        """
        Generate technical explanation using AI and dynamic connector metadata.
        This approach scales to any number of connectors.
        """
        if not self._client:
            return self._generate_fallback_connector_explanation(connector_info, user_message)
        
        try:
            # Create AI prompt with connector metadata
            prompt = f"""
            You are a technical documentation expert. Generate a detailed, accurate explanation about how this connector works.
            
            CONNECTOR INFORMATION:
            - Name: {connector_info['name']}
            - Description: {connector_info['description']}
            - Metadata: {json.dumps(connector_info.get('metadata', {}), indent=2)}
            
            USER QUESTION: "{user_message}"
            
            INSTRUCTIONS:
            1. Focus on the specific aspect the user is asking about (extraction, processing, data flow, parameters, etc.)
            2. Be technical but clear - assume the user wants detailed information
            3. Include specific details about data formats, APIs, authentication, and processing steps
            4. Use the connector metadata to provide accurate information
            5. Structure the response with clear headings and bullet points
            6. If asking about data flow, explain how data moves between this connector and others
            
            Generate a comprehensive technical explanation that directly answers the user's question.
            """
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"AI explanation generation failed: {e}")
            return self._generate_fallback_connector_explanation(connector_info, user_message)

    def _generate_fallback_connector_explanation(
        self, 
        connector_info: Dict[str, Any], 
        user_message: str
    ) -> str:
        """
        Generate a fallback explanation when AI is not available.
        Uses connector metadata to create structured responses.
        """
        name = connector_info['display_name']
        description = connector_info['description']
        metadata = connector_info.get('metadata', {})
        
        # Determine what aspect the user is asking about
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["extract", "extraction", "extracting", "content", "data"]):
            return f"""## {name} Connector - Data Extraction

**Overview:**
{description}

**Data Extraction Process:**
{metadata.get('data_extraction', 'This connector extracts data from its source service using standard API calls.')}

**Data Format:**
{metadata.get('data_format', 'Data is returned in structured JSON format with relevant fields and metadata.')}

**Authentication:**
{metadata.get('authentication', 'Uses standard OAuth 2.0 or API key authentication.')}"""
        
        elif any(word in message_lower for word in ["process", "processing", "work", "works", "flow"]):
            return f"""## How {name} Connector Works

**Overview:**
{description}

**Processing Steps:**
1. Authentication with the service
2. Data retrieval using API calls
3. Data formatting and validation
4. Output preparation for downstream connectors

**Technical Details:**
{metadata.get('processing_details', 'The connector handles API communication, data transformation, and error management.')}

**Data Flow:**
Input → Processing → Structured Output → Next Connector"""
        
        elif any(word in message_lower for word in ["parameter", "parameters", "config", "configuration", "setting"]):
            parameters = connector_info.get('parameters', {})
            param_list = []
            
            if isinstance(parameters, dict):
                for param_name, param_info in parameters.items():
                    if isinstance(param_info, dict):
                        param_list.append(f"- **{param_name}**: {param_info.get('description', 'Configuration parameter')}")
                    else:
                        param_list.append(f"- **{param_name}**: {param_info}")
            
            param_text = "\n".join(param_list) if param_list else "Parameters are configured through the connector interface."
            
            return f"""## {name} Connector Parameters

**Overview:**
{description}

**Configuration Parameters:**
{param_text}

**Setup:**
Configure these parameters in the connector modal to customize how the connector operates."""
        
        else:
            return f"""## {name} Connector Technical Details

**Overview:**
{description}

**Key Features:**
- Connects to {name.lower()} service
- Handles authentication and API communication
- Processes and formats data for workflow integration
- Supports standard workflow operations

**Usage:**
This connector can be used in workflows to integrate with {name.lower()} services. Configure the required parameters and connect it to other workflow steps.

**Need more specific information?** Ask about:
- Data extraction process
- Processing workflow
- Configuration parameters
- Data formats and outputs"""

    def _generate_basic_connector_explanation(self, connector_name: str, user_message: str) -> str:
        """
        Generate a basic explanation when dynamic lookup fails.
        This provides useful information even without full connector metadata.
        """
        message_lower = user_message.lower()
        display_name = connector_name.replace('_', ' ').title()
        
        # Basic connector information
        connector_basics = {
            'youtube': {
                'description': 'Extracts video metadata, transcripts, and channel information from YouTube',
                'data_format': 'JSON with video_id, title, description, transcript, view_count, etc.',
                'processing': 'Uses YouTube Data API v3 with OAuth 2.0 authentication',
                'use_cases': 'Content analysis, research, transcript extraction, video monitoring'
            },
            'gmail': {
                'description': 'Accesses and manages Gmail emails, including reading, sending, and organizing',
                'data_format': 'JSON with message_id, subject, sender, body, attachments, labels',
                'processing': 'Uses Gmail API with OAuth 2.0, handles MIME content and attachments',
                'use_cases': 'Email automation, filtering, notifications, data extraction'
            },
            'google_sheets': {
                'description': 'Reads and writes data to Google Sheets spreadsheets',
                'data_format': 'Structured data as 2D arrays with cell values and formatting',
                'processing': 'Uses Google Sheets API v4 with OAuth 2.0 authentication',
                'use_cases': 'Data storage, reporting, calculations, collaborative data management'
            },
            'sheets': {
                'description': 'Reads and writes data to Google Sheets spreadsheets',
                'data_format': 'Structured data as 2D arrays with cell values and formatting',
                'processing': 'Uses Google Sheets API v4 with OAuth 2.0 authentication',
                'use_cases': 'Data storage, reporting, calculations, collaborative data management'
            },
            'notion': {
                'description': 'Creates and manages pages and databases in Notion workspaces',
                'data_format': 'JSON with page properties, content blocks, and database entries',
                'processing': 'Uses Notion API with API key authentication',
                'use_cases': 'Knowledge management, project tracking, documentation, databases'
            },
            'text_summarizer': {
                'description': 'Generates concise summaries from text content using AI models',
                'data_format': 'JSON with original_text, summary, key_points, word_count',
                'processing': 'Uses NLP models to analyze and condense text content',
                'use_cases': 'Content summarization, key point extraction, document processing'
            },
            'summarizer': {
                'description': 'Generates concise summaries from text content using AI models',
                'data_format': 'JSON with original_text, summary, key_points, word_count',
                'processing': 'Uses NLP models to analyze and condense text content',
                'use_cases': 'Content summarization, key point extraction, document processing'
            },
            'perplexity': {
                'description': 'Performs AI-powered search and research across web sources',
                'data_format': 'JSON with search results, sources, citations, and answers',
                'processing': 'Uses Perplexity API for intelligent search and fact-checking',
                'use_cases': 'Research, fact-checking, information gathering, Q&A'
            }
        }
        
        connector_info = connector_basics.get(connector_name, {
            'description': f'Handles {display_name} integration and data processing',
            'data_format': 'Structured JSON data with relevant fields and metadata',
            'processing': 'Standard API integration with authentication and data transformation',
            'use_cases': 'Workflow automation and data integration'
        })
        
        # Determine what aspect the user is asking about
        if any(word in message_lower for word in ["extract", "extraction", "extracting", "content", "data"]):
            return f"""## {display_name} Connector - Data Extraction

**How it works:**
{connector_info['description']}

**Data Extraction Process:**
{connector_info['processing']}

**Output Format:**
{connector_info['data_format']}

**Common Use Cases:**
{connector_info['use_cases']}

**Data Flow:**
The {display_name} connector extracts data from its source, formats it into structured JSON, and passes it to the next step in your workflow. Each connector handles authentication, API communication, and data transformation automatically."""
        
        elif any(word in message_lower for word in ["process", "processing", "work", "works", "flow"]):
            return f"""## How {display_name} Connector Processing Works

**Overview:**
{connector_info['description']}

**Processing Steps:**
1. **Authentication** - Securely connects to the {display_name} service
2. **Data Retrieval** - {connector_info['processing']}
3. **Data Formatting** - Converts raw data to structured format
4. **Output Preparation** - Formats data for downstream connectors

**Data Flow Between Connectors:**
{display_name} → Structured JSON Data → Next Connector

**Output Format:**
{connector_info['data_format']}

**Integration:**
This connector integrates seamlessly with other workflow steps, automatically handling data transformation and error management."""
        
        elif any(word in message_lower for word in ["parameter", "parameters", "config", "configuration", "setting"]):
            return f"""## {display_name} Connector Configuration

**Overview:**
{connector_info['description']}

**Key Configuration Areas:**
- **Authentication**: Secure connection setup (OAuth 2.0, API keys, etc.)
- **Data Selection**: Choose what data to extract or process
- **Output Format**: Configure how data is structured and formatted
- **Processing Options**: Customize behavior and filtering

**Setup Process:**
1. Configure authentication credentials
2. Set data selection parameters
3. Choose output format options
4. Test the connection

**Data Processing:**
{connector_info['processing']}

**Use Cases:**
{connector_info['use_cases']}"""
        
        else:
            return f"""## {display_name} Connector Technical Overview

**What it does:**
{connector_info['description']}

**How it works:**
{connector_info['processing']}

**Data Format:**
{connector_info['data_format']}

**Common Applications:**
{connector_info['use_cases']}

**Integration:**
- Connects seamlessly with other workflow connectors
- Handles authentication and API communication automatically
- Transforms data into standardized formats
- Provides error handling and retry logic

**Want more specific details?** Ask about:
- "How does {connector_name} extract data?"
- "What parameters does {connector_name} use?"
- "How does data flow from {connector_name} to other connectors?"
- "What format does {connector_name} output?"
"""


# Global instance
_conversation_handler: Optional[IntelligentConversationHandler] = None

async def get_conversation_handler() -> IntelligentConversationHandler:
    """Get the global conversation handler instance."""
    global _conversation_handler
    if _conversation_handler is None:
        _conversation_handler = IntelligentConversationHandler()
        await _conversation_handler.initialize()
    return _conversation_handler