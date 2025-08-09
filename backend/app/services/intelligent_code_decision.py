"""
Intelligent Code Decision System
Prevents hallucination and ensures code generation is only used when truly needed.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from openai import AsyncAzureOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class IntelligentCodeDecision:
    """
    AI-powered decision system that determines when code generation is actually needed
    and prevents unnecessary code injection into workflows.
    """
    
    def __init__(self):
        self._client: Optional[AsyncAzureOpenAI] = None
        
    async def initialize(self):
        """Initialize the AI client."""
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self._client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            logger.info("Intelligent Code Decision system initialized")
        else:
            logger.warning("Azure OpenAI not configured - using rule-based decisions")
    
    async def should_generate_code(
        self, 
        user_request: str, 
        available_connectors: List[str],
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Intelligently decide if code generation is needed or if existing connectors can handle the task.
        
        Returns:
            {
                "needs_code": bool,
                "confidence": float,
                "reasoning": str,
                "alternative_connectors": List[str],
                "code_complexity": str,
                "risk_assessment": str
            }
        """
        
        # First, check if existing connectors can handle the request
        connector_analysis = await self._analyze_connector_coverage(user_request, available_connectors)
        
        if connector_analysis["coverage_score"] > 0.8:
            return {
                "needs_code": False,
                "confidence": connector_analysis["coverage_score"],
                "reasoning": f"Existing connectors can handle this: {', '.join(connector_analysis['suitable_connectors'])}",
                "alternative_connectors": connector_analysis["suitable_connectors"],
                "code_complexity": "none",
                "risk_assessment": "low"
            }
        
        # If connectors can't handle it, analyze if code is truly needed
        if self._client:
            return await self._ai_analyze_code_necessity(user_request, available_connectors, workflow_context)
        else:
            return await self._rule_based_code_analysis(user_request, available_connectors)
    
    async def _analyze_connector_coverage(self, request: str, connectors: List[str]) -> Dict[str, Any]:
        """Analyze how well existing connectors can cover the user's request."""
        
        # Define connector capabilities
        connector_capabilities = {
            "gmail": ["email", "send", "receive", "compose", "reply", "forward"],
            "google_sheets": ["spreadsheet", "data", "rows", "columns", "calculate", "formula"],
            "google_drive": ["files", "upload", "download", "share", "folder", "document"],
            "notion": ["notes", "database", "pages", "blocks", "workspace"],
            "airtable": ["database", "records", "tables", "fields", "base"],
            "youtube": ["videos", "channels", "playlists", "upload", "search"],
            "http": ["api", "request", "get", "post", "webhook", "rest"],
            "webhook": ["trigger", "receive", "event", "notification"],
            "perplexity": ["search", "ai", "query", "research", "information"],
            "text_summarizer": ["summarize", "text", "content", "extract"],
            "google_translate": ["translate", "language", "convert", "localize"]
        }
        
        request_lower = request.lower()
        suitable_connectors = []
        coverage_scores = []
        
        for connector in connectors:
            if connector in connector_capabilities:
                capabilities = connector_capabilities[connector]
                matches = sum(1 for cap in capabilities if cap in request_lower)
                coverage_score = matches / len(capabilities) if capabilities else 0
                
                if coverage_score > 0.2:  # At least 20% capability match
                    suitable_connectors.append(connector)
                    coverage_scores.append(coverage_score)
        
        overall_coverage = max(coverage_scores) if coverage_scores else 0
        
        return {
            "coverage_score": overall_coverage,
            "suitable_connectors": suitable_connectors,
            "analysis": f"Found {len(suitable_connectors)} suitable connectors with max coverage {overall_coverage:.2f}"
        }
    
    async def _ai_analyze_code_necessity(
        self, 
        request: str, 
        connectors: List[str], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use AI to analyze if code generation is truly necessary."""
        
        system_prompt = """
You are an expert workflow analyst. Your job is to prevent unnecessary code generation by determining if existing connectors can handle a user's request.

CRITICAL RULES:
1. Code generation should ONLY be used when existing connectors cannot handle the task
2. Prefer existing connectors over custom code whenever possible
3. Code is needed for: complex data transformations, custom business logic, mathematical calculations, data validation rules
4. Code is NOT needed for: simple API calls, basic data retrieval, standard operations that connectors handle

Analyze the request and return JSON with your decision.
"""
        
        user_message = f"""
USER REQUEST: "{request}"

AVAILABLE CONNECTORS: {', '.join(connectors)}

CONTEXT: {json.dumps(context) if context else "No additional context"}

Determine if code generation is truly necessary or if existing connectors can handle this.

Return JSON:
{{
    "needs_code": boolean,
    "confidence": float (0-1),
    "reasoning": "detailed explanation",
    "alternative_connectors": ["list", "of", "suitable", "connectors"],
    "code_complexity": "none|simple|intermediate|advanced",
    "risk_assessment": "low|medium|high"
}}
"""
        
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,  # Low temperature for consistent decisions
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"AI code necessity analysis failed: {str(e)}")
            return await self._rule_based_code_analysis(request, connectors)
    
    async def _rule_based_code_analysis(self, request: str, connectors: List[str]) -> Dict[str, Any]:
        """Fallback rule-based analysis when AI is not available."""
        
        request_lower = request.lower()
        
        # Patterns that definitely need code
        code_needed_patterns = [
            r"transform.*data",
            r"calculate.*formula",
            r"custom.*logic",
            r"validate.*rules",
            r"complex.*processing",
            r"mathematical.*operation",
            r"algorithm",
            r"parse.*format",
            r"convert.*structure"
        ]
        
        # Patterns that can be handled by connectors
        connector_patterns = [
            r"send.*email",
            r"get.*data",
            r"create.*record",
            r"update.*field",
            r"search.*information",
            r"upload.*file",
            r"download.*document",
            r"translate.*text",
            r"summarize.*content"
        ]
        
        needs_code = False
        confidence = 0.6  # Medium confidence for rule-based
        reasoning = "Rule-based analysis: "
        
        # Check if code is needed
        for pattern in code_needed_patterns:
            if re.search(pattern, request_lower):
                needs_code = True
                reasoning += f"Detected pattern requiring code: {pattern}. "
                break
        
        # Check if connectors can handle it
        if not needs_code:
            for pattern in connector_patterns:
                if re.search(pattern, request_lower):
                    reasoning += f"Can be handled by existing connectors: {pattern}. "
                    break
            else:
                # No clear pattern, lean towards code if it's complex
                if len(request.split()) > 10:  # Complex request
                    needs_code = True
                    reasoning += "Complex request may need custom code. "
        
        return {
            "needs_code": needs_code,
            "confidence": confidence,
            "reasoning": reasoning,
            "alternative_connectors": self._suggest_connectors(request_lower, connectors),
            "code_complexity": "intermediate" if needs_code else "none",
            "risk_assessment": "medium" if needs_code else "low"
        }
    
    def _suggest_connectors(self, request_lower: str, available_connectors: List[str]) -> List[str]:
        """Suggest alternative connectors based on request keywords."""
        
        suggestions = []
        
        if any(word in request_lower for word in ["email", "send", "compose"]):
            if "gmail" in available_connectors:
                suggestions.append("gmail")
        
        if any(word in request_lower for word in ["spreadsheet", "data", "calculate"]):
            if "google_sheets" in available_connectors:
                suggestions.append("google_sheets")
        
        if any(word in request_lower for word in ["file", "document", "upload"]):
            if "google_drive" in available_connectors:
                suggestions.append("google_drive")
        
        if any(word in request_lower for word in ["search", "information", "research"]):
            if "perplexity" in available_connectors:
                suggestions.append("perplexity")
        
        if any(word in request_lower for word in ["translate", "language"]):
            if "google_translate" in available_connectors:
                suggestions.append("google_translate")
        
        return suggestions
    
    async def validate_generated_code(
        self, 
        code: str, 
        original_request: str, 
        language: str
    ) -> Dict[str, Any]:
        """Validate that generated code actually addresses the original request."""
        
        if not self._client:
            return self._rule_based_code_validation(code, original_request)
        
        system_prompt = """
You are a code reviewer. Validate that the generated code actually addresses the user's original request.

Check for:
1. Code relevance to the request
2. Potential security issues
3. Code quality and efficiency
4. Whether simpler alternatives exist

Return validation results in JSON format.
"""
        
        user_message = f"""
ORIGINAL REQUEST: "{original_request}"

GENERATED CODE ({language}):
```{language}
{code}
```

Validate this code and return JSON:
{{
    "is_relevant": boolean,
    "addresses_request": boolean,
    "security_score": float (0-1),
    "quality_score": float (0-1),
    "simpler_alternative": "description or null",
    "issues": ["list", "of", "issues"],
    "recommendations": ["list", "of", "improvements"]
}}
"""
        
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Code validation failed: {str(e)}")
            return self._rule_based_code_validation(code, original_request)
    
    def _rule_based_code_validation(self, code: str, request: str) -> Dict[str, Any]:
        """Rule-based code validation fallback."""
        
        issues = []
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__",
            r"subprocess",
            r"os\.system",
            r"require\s*\(\s*['\"]child_process['\"]"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                issues.append(f"Potentially dangerous pattern: {pattern}")
        
        # Basic relevance check
        request_words = set(request.lower().split())
        code_words = set(re.findall(r'\w+', code.lower()))
        relevance = len(request_words & code_words) / len(request_words) if request_words else 0
        
        return {
            "is_relevant": relevance > 0.2,
            "addresses_request": relevance > 0.3,
            "security_score": 0.8 if not issues else 0.4,
            "quality_score": 0.7,  # Default medium quality
            "simpler_alternative": None,
            "issues": issues,
            "recommendations": ["Review code for security", "Test thoroughly"]
        }


# Global instance
_intelligent_code_decision: Optional[IntelligentCodeDecision] = None


async def get_intelligent_code_decision() -> IntelligentCodeDecision:
    """Get or create the global intelligent code decision instance."""
    global _intelligent_code_decision
    
    if _intelligent_code_decision is None:
        _intelligent_code_decision = IntelligentCodeDecision()
        await _intelligent_code_decision.initialize()
    
    return _intelligent_code_decision