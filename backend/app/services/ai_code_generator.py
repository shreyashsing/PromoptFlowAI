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
    
    async def generate_professional_code(
        self,
        user_prompt: str,
        language: str = "javascript",
        mode: str = "runOnceForAllItems",
        context: Optional[Dict[str, Any]] = None,
        previous_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate professional-grade code similar to Pipedream/Zapier quality.
        """
        if not self._client:
            return self._generate_professional_fallback(user_prompt, language, mode)
        
        try:
            # Analyze the prompt for professional code generation
            intent = await self._analyze_professional_intent(user_prompt, context, previous_data)
            
            # Generate professional code structure
            code = await self._generate_professional_code_structure(
                user_prompt, language, mode, intent, previous_data
            )
            
            return {
                "code": code,
                "language": language,
                "mode": mode,
                "intent": intent,
                "confidence": 0.95,  # High confidence for professional templates
                "explanation": await self._generate_professional_explanation(code, intent),
                "style": "professional"
            }
            
        except Exception as e:
            logger.error(f"Professional code generation failed: {str(e)}")
            return self._generate_professional_fallback(user_prompt, language, mode)

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
            return self._get_code_templates(language, mode).get("basic", "")
    
    def _build_system_prompt(self, language: str, mode: str, intent: Dict[str, Any]) -> str:
        """Build context-aware system prompt for code generation."""
        
        base_prompt = f"""
You are an expert {language.title()} developer specializing in data processing workflows.

CRITICAL EXECUTION REQUIREMENTS:
- Your code will be executed in a sandboxed environment
- The code must be syntactically perfect and executable
- Always include proper error handling and null checks
- Test your logic mentally before generating

EXECUTION MODE: {mode}
- If "runOnceForAllItems": Process the entire 'items' array at once
- If "runOnceForEachItem": Process a single 'item' object

LANGUAGE SPECIFICS:
"""
        
        if language == "javascript":
            base_prompt += """
- Use modern ES6+ JavaScript syntax with professional structure
- Access data via 'items' array (all items mode) or 'item' object (each item mode)
- Use console.log() for debugging output and progress tracking
- ALWAYS return a value - the last expression will be the result
- For all items mode: return an array of objects with 'json' property
- For each item mode: return a single object with 'json' property
- Use array methods like map(), filter(), reduce() for data processing
- Handle edge cases gracefully with proper validation
- Include helpful comments explaining the logic
- Structure code like professional platforms (Pipedream, Zapier, etc.)

PROFESSIONAL CODE STRUCTURE:
All items mode - Clean, robust processing:
```javascript
// Validate input data
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

console.log(`Processing ${items.length} items...`);

// Process all items with error handling
return items.map((item, index) => {
  try {
    // Extract data safely
    const data = item.json || {};
    
    // Your processing logic here
    const processedData = {
      ...data,
      processed: true,
      processedAt: new Date().toISOString(),
      itemIndex: index
    };
    
    console.log(`Processed item ${index + 1}/${items.length}`);
    
    return {
      json: processedData
    };
  } catch (error) {
    console.log(`Error processing item ${index + 1}: ${error.message}`);
    return {
      json: {
        error: error.message,
        originalData: item.json || {},
        itemIndex: index
      }
    };
  }
});
```

Each item mode - Professional single item processing:
```javascript
// Validate input item
if (!item || typeof item !== 'object') {
  console.log('Warning: Invalid item provided');
  return {
    json: {
      error: 'Invalid input item',
      received: typeof item
    }
  };
}

const data = item.json || {};
console.log('Processing item:', Object.keys(data));

try {
  // Your processing logic here
  const result = {
    ...data,
    processed: true,
    processedAt: new Date().toISOString()
  };
  
  console.log('Item processed successfully');
  
  return {
    json: result
  };
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      originalData: data
    }
  };
}
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
        
        # Check if code already has proper safety checks
        has_array_check = "Array.isArray" in code or "!Array.isArray" in code
        has_item_check = "!item" in code or "item &&" in code
        has_try_catch = "try {" in code or "try{" in code
        
        # Add safety checks based on mode
        if mode == "runOnceForAllItems" and not has_array_check:
            safety_check = """// Safety check for items array
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

"""
            code = safety_check + code
        elif mode == "runOnceForEachItem" and not has_item_check:
            safety_check = """// Safety check for item
if (!item || !item.json) {
  console.log('Warning: item or item.json is missing');
  return {
    json: {
      error: 'Invalid input item'
    }
  };
}

"""
            code = safety_check + code
        
        # Add error handling wrapper if not present and complex operations detected
        if not has_try_catch and any(keyword in code for keyword in ["JSON.parse", "parseInt", "parseFloat", "new Date", ".map(", ".filter(", ".reduce("]):
            fallback_return = "[]" if mode == "runOnceForAllItems" else "{ json: { error: 'Code execution failed' } }"
            code = f"""try {{
{self._indent_code(code, 2)}
}} catch (error) {{
  console.log('Error in code execution:', error.message);
  return {fallback_return};
}}"""
        
        # Ensure code ends with return statement if it doesn't already
        if not re.search(r'\breturn\b', code):
            if mode == "runOnceForAllItems":
                code += "\n\n// Fallback return\nreturn [];"
            else:
                code += "\n\n// Fallback return\nreturn { json: {} };"
        
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
        
        code = templates.get(template_key, templates.get("basic", "// No template available"))
        
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
                    "basic": """// Process all items with safety checks
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

return items.map(item => {
  try {
    return {
      json: {
        ...item.json,
        processed: true
      }
    };
  } catch (error) {
    console.log('Error processing item:', error.message);
    return {
      json: {
        error: error.message,
        original: item.json || {}
      }
    };
  }
});""",
                    "transform": """// Transform all items with safety checks
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

return items.map(item => {
  try {
    return {
      json: {
        ...item.json,
        processed: true,
        timestamp: new Date().toISOString()
      }
    };
  } catch (error) {
    console.log('Error processing item:', error.message);
    return {
      json: {
        error: error.message,
        original: item.json || {}
      }
    };
  }
});""",
                    "filter": """// Filter items based on condition with safety checks
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

return items.filter(item => {
  try {
    // Add your condition here
    return item.json && item.json.status === 'active';
  } catch (error) {
    console.log('Error filtering item:', error.message);
    return false;
  }
});""",
                    "aggregate": """// Aggregate data with safety checks
if (!Array.isArray(items)) {
  console.log('Warning: items is not an array, converting to empty array');
  items = [];
}

try {
  const total = items.reduce((sum, item) => {
    const value = item.json && typeof item.json.value === 'number' ? item.json.value : 0;
    return sum + value;
  }, 0);
  
  return [{
    json: {
      total: total,
      count: items.length,
      average: items.length > 0 ? total / items.length : 0
    }
  }];
} catch (error) {
  console.log('Error aggregating data:', error.message);
  return [{
    json: {
      error: error.message,
      total: 0,
      count: 0,
      average: 0
    }
  }];
}"""
                }
            else:  # runOnceForEachItem
                return {
                    "basic": """// Process single item with safety checks
if (!item || !item.json) {
  console.log('Warning: item or item.json is missing');
  return {
    json: {
      error: 'Invalid input item'
    }
  };
}

try {
  return {
    json: {
      ...item.json,
      processed: true
    }
  };
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      original: item.json || {}
    }
  };
}""",
                    "transform": """// Transform single item with safety checks
if (!item || !item.json) {
  console.log('Warning: item or item.json is missing');
  return {
    json: {
      error: 'Invalid input item'
    }
  };
}

try {
  return {
    json: {
      ...item.json,
      processed: true,
      timestamp: new Date().toISOString()
    }
  };
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      original: item.json || {}
    }
  };
}""",
                    "filter": """// Process item conditionally with safety checks
if (!item || !item.json) {
  console.log('Warning: item or item.json is missing');
  return null;
}

try {
  if (item.json.status === 'active') {
    return {
      json: {
        ...item.json,
        processed: true
      }
    };
  }
  return null;
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      original: item.json || {}
    }
  };
}""",
                    "aggregate": """// Process single item with safety checks
if (!item || !item.json) {
  console.log('Warning: item or item.json is missing');
  return {
    json: {
      error: 'Invalid input item'
    }
  };
}

try {
  const value = typeof item.json.value === 'number' ? item.json.value : 0;
  return {
    json: {
      ...item.json,
      processed: true,
      value_doubled: value * 2
    }
  };
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      original: item.json || {}
    }
  };
}"""
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

    async def _analyze_professional_intent(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]], 
        previous_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze intent for professional code generation."""
        
        # Enhanced intent analysis for professional code
        prompt_lower = prompt.lower()
        
        # Detect data operations
        operations = []
        if any(word in prompt_lower for word in ["extract", "parse", "get", "retrieve"]):
            operations.append("extract")
        if any(word in prompt_lower for word in ["transform", "convert", "format", "clean"]):
            operations.append("transform")
        if any(word in prompt_lower for word in ["filter", "select", "where", "condition"]):
            operations.append("filter")
        if any(word in prompt_lower for word in ["validate", "check", "verify", "ensure"]):
            operations.append("validate")
        if any(word in prompt_lower for word in ["aggregate", "sum", "count", "calculate"]):
            operations.append("aggregate")
        
        # Detect data types
        data_types = []
        if any(word in prompt_lower for word in ["title", "content", "text", "string"]):
            data_types.append("text")
        if any(word in prompt_lower for word in ["number", "count", "value", "amount"]):
            data_types.append("numeric")
        if any(word in prompt_lower for word in ["date", "time", "timestamp"]):
            data_types.append("temporal")
        if any(word in prompt_lower for word in ["array", "list", "collection"]):
            data_types.append("array")
        if any(word in prompt_lower for word in ["object", "json", "structure"]):
            data_types.append("object")
        
        # Analyze previous data structure if available
        data_structure = {}
        if previous_data and len(previous_data) > 0:
            sample = previous_data[0].get("json", {})
            data_structure = {
                "fields": list(sample.keys()),
                "sample_values": {k: type(v).__name__ for k, v in sample.items()}
            }
        
        return {
            "operations": operations or ["process"],
            "data_types": data_types or ["object"],
            "complexity": "professional",
            "data_structure": data_structure,
            "confidence": 0.9
        }

    async def _generate_professional_code_structure(
        self,
        prompt: str,
        language: str,
        mode: str,
        intent: Dict[str, Any],
        previous_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Generate professional code structure."""
        
        if language == "javascript":
            return self._generate_professional_javascript(prompt, mode, intent, previous_data)
        else:
            return self._generate_professional_python(prompt, mode, intent, previous_data)

    def _generate_professional_javascript(
        self,
        prompt: str,
        mode: str,
        intent: Dict[str, Any],
        previous_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Generate professional JavaScript code."""
        
        operations = intent.get("operations", ["process"])
        data_structure = intent.get("data_structure", {})
        
        if mode == "runOnceForAllItems":
            return f"""// {prompt}
// Professional data processing with comprehensive error handling

// Validate and prepare input data
if (!Array.isArray(items)) {{
  console.log('Warning: Expected array of items, received:', typeof items);
  items = [];
}}

console.log(`Starting processing of ${{items.length}} items...`);

// Process all items with detailed logging and error handling
const results = items.map((item, index) => {{
  try {{
    // Validate item structure
    if (!item || typeof item !== 'object' || !item.json) {{
      console.log(`Warning: Invalid item structure at index ${{index}}`);
      return {{
        json: {{
          error: 'Invalid item structure',
          itemIndex: index,
          received: typeof item
        }}
      }};
    }}
    
    const data = item.json;
    console.log(`Processing item ${{index + 1}}/${{items.length}}:`, Object.keys(data));
    
    // Main processing logic
    {self._generate_processing_logic(operations, data_structure)}
    
    console.log(`Successfully processed item ${{index + 1}}`);
    
    return {{
      json: processedData
    }};
    
  }} catch (error) {{
    console.log(`Error processing item ${{index + 1}}: ${{error.message}}`);
    return {{
      json: {{
        error: error.message,
        itemIndex: index,
        originalData: item.json || {{}},
        stack: error.stack
      }}
    }};
  }}
}});

console.log(`Processing complete. Successfully processed ${{results.filter(r => !r.json.error).length}}/${{items.length}} items`);

return results;"""
        else:  # runOnceForEachItem
            return f"""// {prompt}
// Professional single item processing

// Validate input item
if (!item || typeof item !== 'object') {{
  console.log('Error: Invalid item provided:', typeof item);
  return {{
    json: {{
      error: 'Invalid input item',
      received: typeof item
    }}
  }};
}}

if (!item.json) {{
  console.log('Warning: Item missing json property');
  return {{
    json: {{
      error: 'Item missing json property',
      itemStructure: Object.keys(item)
    }}
  }};
}}

const data = item.json;
console.log('Processing item with fields:', Object.keys(data));

try {{
  // Main processing logic
  {self._generate_processing_logic(operations, data_structure)}
  
  console.log('Item processed successfully');
  
  return {{
    json: processedData
  }};
  
}} catch (error) {{
  console.log('Error processing item:', error.message);
  return {{
    json: {{
      error: error.message,
      originalData: data,
      stack: error.stack
    }}
  }};
}}"""

    def _generate_processing_logic(self, operations: List[str], data_structure: Dict[str, Any]) -> str:
        """Generate the main processing logic based on operations."""
        
        logic_parts = []
        
        # Start with data extraction/validation
        logic_parts.append("""
    // Extract and validate data fields
    const processedData = {
      ...data,
      processedAt: new Date().toISOString(),
      processingOperations: """ + str(operations) + """
    };""")
        
        # Add operation-specific logic
        if "extract" in operations:
            logic_parts.append("""
    
    // Extract specific fields
    if (data.title) processedData.extractedTitle = String(data.title).trim();
    if (data.content) processedData.extractedContent = String(data.content).trim();""")
        
        if "transform" in operations:
            logic_parts.append("""
    
    // Transform data
    Object.keys(data).forEach(key => {
      if (typeof data[key] === 'string') {
        processedData[key + '_cleaned'] = data[key].trim().replace(/\\s+/g, ' ');
      }
    });""")
        
        if "validate" in operations:
            logic_parts.append("""
    
    // Validate data
    processedData.validationResults = {
      hasTitle: !!data.title,
      hasContent: !!data.content,
      isValid: !!data.title && !!data.content
    };""")
        
        if "aggregate" in operations:
            logic_parts.append("""
    
    // Aggregate calculations
    processedData.metrics = {
      fieldCount: Object.keys(data).length,
      textLength: Object.values(data).filter(v => typeof v === 'string').reduce((sum, str) => sum + str.length, 0)
    };""")
        
        return "".join(logic_parts)

    def _generate_professional_fallback(self, prompt: str, language: str, mode: str) -> Dict[str, Any]:
        """Generate professional fallback code when AI is not available."""
        
        templates = self._get_professional_templates(language, mode)
        
        # Determine template based on prompt
        if any(word in prompt.lower() for word in ["extract", "parse", "clean"]):
            template_key = "extract_transform"
        elif any(word in prompt.lower() for word in ["filter", "select"]):
            template_key = "filter"
        elif any(word in prompt.lower() for word in ["aggregate", "calculate"]):
            template_key = "aggregate"
        else:
            template_key = "professional_basic"
        
        code = templates.get(template_key, templates["professional_basic"])
        
        return {
            "code": code,
            "language": language,
            "mode": mode,
            "intent": {"operation": template_key, "confidence": 0.8},
            "confidence": 0.8,
            "explanation": f"Generated professional {template_key} code template.",
            "style": "professional"
        }

    def _get_professional_templates(self, language: str, mode: str) -> Dict[str, str]:
        """Get professional code templates similar to Pipedream quality."""
        
        if language == "javascript":
            if mode == "runOnceForAllItems":
                return {
                    "professional_basic": """// Professional data processing with comprehensive error handling

// Validate and prepare input data
if (!Array.isArray(items)) {
  console.log('Warning: Expected array of items, received:', typeof items);
  items = [];
}

console.log(`Starting processing of ${items.length} items...`);

// Process all items with detailed logging and error handling
const results = items.map((item, index) => {
  try {
    // Validate item structure
    if (!item || typeof item !== 'object' || !item.json) {
      console.log(`Warning: Invalid item structure at index ${index}`);
      return {
        json: {
          error: 'Invalid item structure',
          itemIndex: index,
          received: typeof item
        }
      };
    }
    
    const data = item.json;
    console.log(`Processing item ${index + 1}/${items.length}:`, Object.keys(data));
    
    // Main processing logic
    const processedData = {
      ...data,
      processed: true,
      processedAt: new Date().toISOString(),
      itemIndex: index
    };
    
    console.log(`Successfully processed item ${index + 1}`);
    
    return {
      json: processedData
    };
    
  } catch (error) {
    console.log(`Error processing item ${index + 1}: ${error.message}`);
    return {
      json: {
        error: error.message,
        itemIndex: index,
        originalData: item.json || {},
        stack: error.stack
      }
    };
  }
});

console.log(`Processing complete. Successfully processed ${results.filter(r => !r.json.error).length}/${items.length} items`);

return results;""",
                    "extract_transform": """// Professional data extraction and transformation

// Validate and prepare input data
if (!Array.isArray(items)) {
  console.log('Warning: Expected array of items, received:', typeof items);
  items = [];
}

console.log(`Starting extraction and transformation of ${items.length} items...`);

// Helper function to clean text
const cleanText = (text) => {
  if (typeof text !== 'string') return '';
  return text.trim().replace(/\\s+/g, ' ').replace(/(\\r?\\n){2,}/g, '\\n');
};

// Process all items with comprehensive extraction
const results = items.map((item, index) => {
  try {
    // Validate item structure
    if (!item || typeof item !== 'object' || !item.json) {
      console.log(`Warning: Invalid item structure at index ${index}`);
      return {
        json: {
          error: 'Invalid item structure',
          itemIndex: index
        }
      };
    }
    
    const data = item.json;
    console.log(`Extracting from item ${index + 1}/${items.length}:`, Object.keys(data));
    
    // Extract and transform data
    const extractedData = {
      // Preserve original data
      ...data,
      
      // Add extraction metadata
      extractedAt: new Date().toISOString(),
      itemIndex: index,
      
      // Clean text fields
      title: cleanText(data.title),
      content: cleanText(data.content),
      
      // Handle citations
      citations: Array.isArray(data.citation) 
        ? data.citation.map(cleanText).filter(Boolean)
        : typeof data.citation === 'string' 
          ? [cleanText(data.citation)].filter(Boolean)
          : [],
      
      // Preserve original ID if present
      originalId: data.id || data.originalId || null
    };
    
    console.log(`Successfully extracted from item ${index + 1}`);
    
    return {
      json: extractedData
    };
    
  } catch (error) {
    console.log(`Error extracting from item ${index + 1}: ${error.message}`);
    return {
      json: {
        error: error.message,
        itemIndex: index,
        originalData: item.json || {}
      }
    };
  }
});

console.log(`Extraction complete. Successfully processed ${results.filter(r => !r.json.error).length}/${items.length} items`);

return results;"""
                }
            else:  # runOnceForEachItem
                return {
                    "professional_basic": """// Professional single item processing

// Validate input item
if (!item || typeof item !== 'object') {
  console.log('Error: Invalid item provided:', typeof item);
  return {
    json: {
      error: 'Invalid input item',
      received: typeof item
    }
  };
}

if (!item.json) {
  console.log('Warning: Item missing json property');
  return {
    json: {
      error: 'Item missing json property',
      itemStructure: Object.keys(item)
    }
  };
}

const data = item.json;
console.log('Processing item with fields:', Object.keys(data));

try {
  // Main processing logic
  const processedData = {
    ...data,
    processed: true,
    processedAt: new Date().toISOString()
  };
  
  console.log('Item processed successfully');
  
  return {
    json: processedData
  };
  
} catch (error) {
  console.log('Error processing item:', error.message);
  return {
    json: {
      error: error.message,
      originalData: data,
      stack: error.stack
    }
  };
}"""
                }
        
        return {}

    async def _generate_professional_explanation(self, code: str, intent: Dict[str, Any]) -> str:
        """Generate explanation for professional code."""
        
        operations = intent.get("operations", ["process"])
        
        explanation = f"Generated professional code that performs {', '.join(operations)} operations with:"
        explanation += "\n• Comprehensive input validation and error handling"
        explanation += "\n• Detailed logging for debugging and monitoring"
        explanation += "\n• Structured error responses with context"
        explanation += "\n• Professional code organization and comments"
        explanation += "\n• Robust data processing patterns"
        
        return explanation


# Global instance
_ai_code_generator: Optional[AICodeGenerator] = None


async def get_ai_code_generator() -> AICodeGenerator:
    """Get or create the global AI code generator instance."""
    global _ai_code_generator
    
    if _ai_code_generator is None:
        _ai_code_generator = AICodeGenerator()
        await _ai_code_generator.initialize()
    
    return _ai_code_generator