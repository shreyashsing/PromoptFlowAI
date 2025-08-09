"""
AI Code Generator for Code Connector
Intelligently generates JavaScript and Python code based on user prompts and workflow context.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from openai import AsyncAzureOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class AICodeGenerator:
    """
    AI-powered code generation service for the Code connector.
    Generates contextually appropriate JavaScript and Python code.
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
            logger.info("AI Code Generator initialized successfully")
        else:
            logger.warning("Azure OpenAI not configured - AI code generation disabled")
    
    async def generate_code(
        self, 
        user_prompt: str, 
        language: str = "javascript",
        mode: str = "runOnceForAllItems",
        context: Optional[Dict[str, Any]] = None,
        previous_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate code based on user prompt and context.
        
        Args:
            user_prompt: Natural language description of what the code should do
            language: "javascript" or "python"
            mode: "runOnceForAllItems" or "runOnceForEachItem"
            context: Additional context about the workflow
            previous_data: Sample of previous workflow data for context
            
        Returns:
            Dictionary with generated code and metadata
        """
        if not self._client:
            return self._fallback_code_generation(user_prompt, language, mode)
        
        try:
            # Analyze the prompt to understand intent
            intent = await self._analyze_intent(user_prompt, context)
            
            # Generate appropriate code
            code = await self._generate_code_with_ai(
                user_prompt, language, mode, intent, previous_data
            )
            
            # Validate and enhance the generated code
            enhanced_code = await self._enhance_code(code, language, mode, intent)
            
            return {
                "code": enhanced_code,
                "language": language,
                "mode": mode,
                "intent": intent,
                "confidence": 0.9,  # AI-generated code confidence
                "explanation": await self._generate_explanation(enhanced_code, intent)
            }
            
        except Exception as e:
            logger.error(f"AI code generation failed: {str(e)}")
            return self._fallback_code_generation(user_prompt, language, mode)
    
    async def _analyze_intent(self, prompt: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user prompt to understand the coding intent."""
        
        system_prompt = """
You are an expert code analyst. Analyze the user's request and identify:
1. Primary operation (transform, filter, aggregate, validate, etc.)
2. Data manipulation type (array operations, object manipulation, calculations, etc.)
3. Required libraries or functions
4. Input/output expectations
5. Complexity level (simple, intermediate, advanced)

Return a JSON object with your analysis.
"""
        
        user_message = f"""
Analyze this coding request:
"{prompt}"

Context: {json.dumps(context) if context else "No additional context"}

Provide analysis in JSON format.
"""
        
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return self._fallback_intent_analysis(prompt)
    
    async def _generate_code_with_ai(
        self, 
        prompt: str, 
        language: str, 
        mode: str, 
        intent: Dict[str, Any],
        previous_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Generate code using AI based on analyzed intent."""
        
        # Build context-aware system prompt
        system_prompt = self._build_system_prompt(language, mode, intent)
        
        # Build user prompt with examples and context
        user_message = self._build_user_prompt(prompt, language, mode, previous_data)
        
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.4,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"AI code generation failed: {str(e)}")
            return self._fallback_code_templates(prompt, language, mode)
    
    def _build_system_prompt(self, language: str, mode: str, intent: Dict[str, Any]) -> str:
        """Build context-aware system prompt for code generation."""
        
        base_prompt = f"""
You are an expert {language.title()} developer specializing in data processing workflows.

EXECUTION MODE: {mode}
- If "runOnceForAllItems": Process the entire 'items' array at once
- If "runOnceForEachItem": Process a single 'item' object

LANGUAGE SPECIFICS:
"""
        
        if language == "javascript":
            base_prompt += """
- Use modern ES6+ JavaScript syntax
- Access data via 'items' array (all items mode) or 'item' object (each item mode)
- Use console.log() for debugging output
- Return the result directly (no explicit return statement needed in function wrapper)
- For all items mode: return an array of objects with 'json' property
- For each item mode: return a single object with 'json' property
- Use array methods like map(), filter(), reduce() for data processing
- Handle edge cases (null, undefined, empty arrays)

EXAMPLES:
All items mode:
```javascript
// Transform all items
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString()
  }
}));
```

Each item mode:
```javascript
// Process single item
return {
  json: {
    ...item.json,
    processed: true,
    category: item.json.age >= 18 ? 'adult' : 'minor'
  }
};
```
"""
        else:  # Python
            base_prompt += """
- Use Python 3.x syntax
- Access data via 'items' list (all items mode) or 'item' dict (each item mode)
- Use print() for debugging output
- Set 'result' variable with your output
- For all items mode: result should be a list of dicts with 'json' key
- For each item mode: result should be a single dict with 'json' key
- Use list comprehensions and built-in functions for data processing
- Handle edge cases (None, empty lists, missing keys)

EXAMPLES:
All items mode:
```python
# Transform all items
result = []
for item in items:
    new_item = {
        "json": {
            **item["json"],
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
    }
    result.append(new_item)
```

Each item mode:
```python
# Process single item
result = {
    "json": {
        **item["json"],
        "processed": True,
        "category": "adult" if item["json"]["age"] >= 18 else "minor"
    }
}
```
"""
        
        base_prompt += f"""

INTENT ANALYSIS: {json.dumps(intent)}

REQUIREMENTS:
1. Write clean, readable code
2. Handle edge cases gracefully
3. Include helpful comments
4. Follow the execution mode requirements
5. Ensure proper data structure format
6. Add console.log/print statements for debugging when helpful

Generate ONLY the code, no explanations or markdown formatting.
"""
        
        return base_prompt
    
    def _build_user_prompt(
        self, 
        prompt: str, 
        language: str, 
        mode: str, 
        previous_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build user prompt with context and examples."""
        
        user_message = f"Generate {language} code for: {prompt}\n\n"
        
        if previous_data:
            user_message += f"Sample input data structure:\n{json.dumps(previous_data[:2], indent=2)}\n\n"
        
        user_message += f"Execution mode: {mode}\n"
        user_message += "Generate the code now:"
        
        return user_message
    
    async def _enhance_code(self, code: str, language: str, mode: str, intent: Dict[str, Any]) -> str:
        """Enhance generated code with additional safety and optimization."""
        
        # Remove any markdown formatting
        code = re.sub(r'```(?:javascript|python)?\n?', '', code)
        code = re.sub(r'\n?```', '', code)
        code = code.strip()
        
        # Add safety checks and optimizations
        if language == "javascript":
            code = self._enhance_javascript_code(code, mode)
        else:
            code = self._enhance_python_code(code, mode)
        
        return code
    
    def _enhance_javascript_code(self, code: str, mode: str) -> str:
        """Add safety checks and optimizations to JavaScript code."""
        
        # Add null/undefined checks if not present
        if mode == "runOnceForAllItems" and "items" in code and "Array.isArray" not in code:
            safety_check = "// Safety check for items array\nif (!Array.isArray(items)) items = [];\n\n"
            code = safety_check + code
        
        # Add error handling wrapper if complex operations detected
        if any(keyword in code for keyword in ["JSON.parse", "parseInt", "parseFloat", "new Date"]):
            code = f"""try {{
{self._indent_code(code, 2)}
}} catch (error) {{
  console.log('Error in code execution:', error.message);
  return {mode == 'runOnceForAllItems' and '[]' or 'null'};
}}"""
        
        return code
    
    def _enhance_python_code(self, code: str, mode: str) -> str:
        """Add safety checks and optimizations to Python code."""
        
        # Add imports if needed
        imports_needed = []
        if "datetime" in code and "import datetime" not in code:
            imports_needed.append("from datetime import datetime")
        if "json" in code and "import json" not in code:
            imports_needed.append("import json")
        
        if imports_needed:
            code = "\n".join(imports_needed) + "\n\n" + code
        
        # Add safety check for items
        if mode == "runOnceForAllItems" and "items" in code:
            safety_check = "# Safety check for items list\nif not isinstance(items, list):\n    items = []\n\n"
            code = safety_check + code
        
        return code
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces."""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))
    
    async def _generate_explanation(self, code: str, intent: Dict[str, Any]) -> str:
        """Generate human-readable explanation of the generated code."""
        
        if not self._client:
            return "Generated code based on your request."
        
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system", 
                        "content": "Explain this code in simple terms, focusing on what it does and why."
                    },
                    {
                        "role": "user", 
                        "content": f"Explain this code:\n\n{code}\n\nIntent: {json.dumps(intent)}"
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Code explanation generation failed: {str(e)}")
            return "Generated code to process your data as requested."
    
    def _fallback_code_generation(self, prompt: str, language: str, mode: str) -> Dict[str, Any]:
        """Fallback code generation when AI is not available."""
        
        # Simple template-based generation
        templates = self._get_code_templates(language, mode)
        
        # Basic intent detection
        if any(word in prompt.lower() for word in ["transform", "change", "modify", "update"]):
            template_key = "transform"
        elif any(word in prompt.lower() for word in ["filter", "select", "where", "condition"]):
            template_key = "filter"
        elif any(word in prompt.lower() for word in ["count", "sum", "total", "aggregate"]):
            template_key = "aggregate"
        else:
            template_key = "basic"
        
        code = templates.get(template_key, templates["basic"])
        
        return {
            "code": code,
            "language": language,
            "mode": mode,
            "intent": {"operation": template_key, "confidence": 0.6},
            "confidence": 0.6,
            "explanation": f"Generated {template_key} code template based on your request."
        }
    
    def _get_code_templates(self, language: str, mode: str) -> Dict[str, str]:
        """Get code templates for fallback generation."""
        
        if language == "javascript":
            if mode == "runOnceForAllItems":
                return {
                    "basic": """// Process all items
return items.map(item => ({
  json: {
    ...item.json,
    processed: true
  }
}));""",
                    "transform": """// Transform all items
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString()
  }
}));""",
                    "filter": """// Filter items based on condition
return items.filter(item => {
  // Add your condition here
  return item.json.status === 'active';
});""",
                    "aggregate": """// Aggregate data
const total = items.reduce((sum, item) => sum + (item.json.value || 0), 0);
return [{
  json: {
    total: total,
    count: items.length,
    average: total / items.length
  }
}];"""
                }
            else:  # runOnceForEachItem
                return {
                    "basic": """// Process single item
return {
  json: {
    ...item.json,
    processed: true
  }
};""",
                    "transform": """// Transform single item
return {
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString()
  }
};""",
                    "filter": """// Process item conditionally
if (item.json.status === 'active') {
  return {
    json: {
      ...item.json,
      processed: true
    }
  };
}
return null;""",
                    "aggregate": """// Process single item
return {
  json: {
    ...item.json,
    processed: true,
    value_doubled: (item.json.value || 0) * 2
  }
};"""
                }
        else:  # Python
            if mode == "runOnceForAllItems":
                return {
                    "basic": """# Process all items
result = []
for item in items:
    new_item = {
        "json": {
            **item["json"],
            "processed": True
        }
    }
    result.append(new_item)""",
                    "transform": """# Transform all items
from datetime import datetime

result = []
for item in items:
    new_item = {
        "json": {
            **item["json"],
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
    }
    result.append(new_item)""",
                    "filter": """# Filter items based on condition
result = []
for item in items:
    if item["json"].get("status") == "active":
        result.append(item)""",
                    "aggregate": """# Aggregate data
total = sum(item["json"].get("value", 0) for item in items)
result = [{
    "json": {
        "total": total,
        "count": len(items),
        "average": total / len(items) if items else 0
    }
}]"""
                }
            else:  # runOnceForEachItem
                return {
                    "basic": """# Process single item
result = {
    "json": {
        **item["json"],
        "processed": True
    }
}""",
                    "transform": """# Transform single item
from datetime import datetime

result = {
    "json": {
        **item["json"],
        "processed": True,
        "timestamp": datetime.now().isoformat()
    }
}""",
                    "filter": """# Process item conditionally
if item["json"].get("status") == "active":
    result = {
        "json": {
            **item["json"],
            "processed": True
        }
    }
else:
    result = None""",
                    "aggregate": """# Process single item
result = {
    "json": {
        **item["json"],
        "processed": True,
        "value_doubled": item["json"].get("value", 0) * 2
    }
}"""
                }
    
    def _fallback_intent_analysis(self, prompt: str) -> Dict[str, Any]:
        """Fallback intent analysis when AI is not available."""
        
        prompt_lower = prompt.lower()
        
        # Basic keyword-based analysis
        if any(word in prompt_lower for word in ["transform", "change", "modify", "convert"]):
            operation = "transform"
        elif any(word in prompt_lower for word in ["filter", "select", "where", "find"]):
            operation = "filter"
        elif any(word in prompt_lower for word in ["count", "sum", "total", "calculate"]):
            operation = "aggregate"
        elif any(word in prompt_lower for word in ["validate", "check", "verify"]):
            operation = "validate"
        else:
            operation = "process"
        
        return {
            "operation": operation,
            "complexity": "intermediate",
            "data_type": "object_manipulation",
            "confidence": 0.6
        }


# Global instance
_ai_code_generator: Optional[AICodeGenerator] = None


async def get_ai_code_generator() -> AICodeGenerator:
    """Get or create the global AI code generator instance."""
    global _ai_code_generator
    
    if _ai_code_generator is None:
        _ai_code_generator = AICodeGenerator()
        await _ai_code_generator.initialize()
    
    return _ai_code_generator