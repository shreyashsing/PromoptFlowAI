"""
Code Connector - Execute JavaScript and Python code with sandboxing and validation.
"""
import json
import re
import subprocess
import tempfile
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


logger = logging.getLogger(__name__)


class CodeExecutionError(ConnectorException):
    """Custom exception for code execution errors."""
    
    def __init__(self, message: str, line_number: Optional[int] = None, item_index: Optional[int] = None):
        self.line_number = line_number
        self.item_index = item_index
        
        # Format error message with context
        if line_number and item_index is not None:
            message = f"{message} [line {line_number}, for item {item_index}]"
        elif line_number:
            message = f"{message} [line {line_number}]"
        elif item_index is not None:
            message = f"{message} [item {item_index}]"
            
        super().__init__(message)


class CodeValidationError(ValidationException):
    """Custom exception for code validation errors."""
    pass


class CodeConnector(BaseConnector):
    """
    Code Connector for executing JavaScript and Python code with proper sandboxing.
    
    Supports both 'Run Once for All Items' and 'Run Once for Each Item' modes
    with comprehensive error handling and validation.
    """
    
    def _get_connector_name(self) -> str:
        return "code"
    
    def _get_category(self) -> str:
        return "development"
    
    def _define_schema(self) -> Dict[str, Any]:
        """Define the JSON schema for Code connector parameters."""
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["runOnceForAllItems", "runOnceForEachItem"],
                    "default": "runOnceForAllItems",
                    "description": "Execution mode: run once for all items or once per item"
                },
                "language": {
                    "type": "string", 
                    "enum": ["javascript", "python"],
                    "default": "javascript",
                    "description": "Programming language to execute"
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute (JavaScript or Python)",
                    "minLength": 1
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300,
                    "description": "Execution timeout in seconds"
                },
                "safe_mode": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable safe mode with restricted operations"
                },
                "allow_network": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow network operations (requires safe_mode=False)"
                },
                "allow_file_system": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow file system operations (requires safe_mode=False)"
                },
                "max_memory_mb": {
                    "type": "integer",
                    "default": 128,
                    "minimum": 16,
                    "maximum": 1024,
                    "description": "Maximum memory usage in MB"
                },
                "return_console_output": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include console output in results"
                }
            },
            "required": ["code", "language"],
            "additionalProperties": False
        }
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """Code connector doesn't require authentication."""
        return AuthRequirements(
            type=AuthType.NONE,
            fields={}
        )
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Code connector."""
        return {
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "code": "return items.map(item => ({ json: { ...item.json, processed: true } }));",
            "timeout": 30,
            "safe_mode": True
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Code-specific example prompts."""
        return [
            "Execute JavaScript code to transform data",
            "Run Python script to process items",
            "Transform JSON data using custom code",
            "Execute code to filter and modify items",
            "Run custom logic on workflow data",
            "Process data with JavaScript functions",
            "Execute Python data analysis code"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Code-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Language detection
        if any(word in prompt_lower for word in ["javascript", "js", "node"]):
            suggestions["language"] = "javascript"
        elif any(word in prompt_lower for word in ["python", "py", "pandas", "numpy"]):
            suggestions["language"] = "python"
        
        # Mode detection
        if any(word in prompt_lower for word in ["each", "every", "per item", "individual"]):
            suggestions["mode"] = "runOnceForEachItem"
        else:
            suggestions["mode"] = "runOnceForAllItems"
        
        # Safety detection
        if any(word in prompt_lower for word in ["network", "http", "api", "request"]):
            suggestions["allow_network"] = True
            suggestions["safe_mode"] = False
        
        if any(word in prompt_lower for word in ["file", "read", "write", "save"]):
            suggestions["allow_file_system"] = True
            suggestions["safe_mode"] = False
        
        return suggestions
    
    async def generate_ai_code(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate AI-powered code based on user prompt and context.
        This is the main method the AI agent will call to generate code.
        """
        try:
            from app.services.ai_code_generator import get_ai_code_generator
            
            # Get basic parameter suggestions first
            suggestions = self.generate_parameter_suggestions(user_prompt, context)
            
            # Extract previous workflow data for context
            previous_data = None
            if context and "previous_results" in context:
                previous_data = context["previous_results"].get("items", [])
            
            # Generate AI code using professional templates
            ai_generator = await get_ai_code_generator()
            code_result = await ai_generator.generate_professional_code(
                user_prompt=user_prompt,
                language=suggestions.get("language", "javascript"),
                mode=suggestions.get("mode", "runOnceForAllItems"),
                context=context,
                previous_data=previous_data
            )
            
            # Merge AI-generated code with parameter suggestions
            final_params = {
                **suggestions,
                "code": code_result["code"],
                "_ai_generated": True,
                "_ai_confidence": code_result["confidence"],
                "_ai_explanation": code_result["explanation"],
                "_ai_intent": code_result["intent"]
            }
            
            return final_params
            
        except Exception as e:
            logger.error(f"AI code generation failed: {str(e)}")
            # Fallback to basic parameter suggestions
            return self.generate_parameter_suggestions(user_prompt, context)
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Execute code with proper sandboxing and validation."""
        try:
            # Extract parameters
            language = params.get("language", "javascript")
            mode = params.get("mode", "runOnceForAllItems")
            code = params.get("code", "")
            timeout = params.get("timeout", 30)
            safe_mode = params.get("safe_mode", True)
            allow_network = params.get("allow_network", False)
            allow_file_system = params.get("allow_file_system", False)
            max_memory_mb = params.get("max_memory_mb", 128)
            return_console_output = params.get("return_console_output", True)
            
            # Validate code
            await self._validate_code(code, language, safe_mode, allow_network, allow_file_system)
            
            # Get input items from context
            input_items = context.previous_results.get("items", [{"json": {}}]) if context.previous_results else [{"json": {}}]
            
            # Execute based on mode
            if mode == "runOnceForAllItems":
                result = await self._execute_for_all_items(
                    code, language, input_items, timeout, safe_mode, 
                    allow_network, allow_file_system, max_memory_mb, return_console_output
                )
            else:  # runOnceForEachItem
                result = await self._execute_for_each_item(
                    code, language, input_items, timeout, safe_mode,
                    allow_network, allow_file_system, max_memory_mb, return_console_output
                )
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "language": language,
                    "mode": mode,
                    "items_processed": len(input_items),
                    "execution_time": result.get("execution_time", 0),
                    "safe_mode": safe_mode
                }
            )
            
        except Exception as e:
            logger.error(f"Code execution failed: {str(e)}")
            return ConnectorResult(
                success=False,
                error=str(e),
                data=None
            )
    
    async def _validate_code(self, code: str, language: str, safe_mode: bool, 
                           allow_network: bool, allow_file_system: bool) -> None:
        """Validate code for security and syntax issues."""
        if not code or not code.strip():
            raise CodeValidationError("Code cannot be empty")
        
        # Check for dangerous operations in safe mode
        if safe_mode:
            dangerous_patterns = {
                "javascript": [
                    r"require\s*\(\s*['\"]fs['\"]",
                    r"require\s*\(\s*['\"]child_process['\"]",
                    r"require\s*\(\s*['\"]os['\"]",
                    r"require\s*\(\s*['\"]process['\"]",
                    r"eval\s*\(",
                    r"Function\s*\(",
                    r"setTimeout\s*\(",
                    r"setInterval\s*\(",
                ],
                "python": [
                    r"import\s+os",
                    r"import\s+subprocess",
                    r"import\s+sys",
                    r"from\s+os\s+import",
                    r"from\s+subprocess\s+import",
                    r"exec\s*\(",
                    r"eval\s*\(",
                    r"__import__\s*\(",
                    r"open\s*\(",
                ]
            }
            
            if not allow_network:
                dangerous_patterns["javascript"].extend([
                    r"require\s*\(\s*['\"]http['\"]",
                    r"require\s*\(\s*['\"]https['\"]",
                    r"require\s*\(\s*['\"]net['\"]",
                    r"fetch\s*\(",
                    r"XMLHttpRequest",
                ])
                dangerous_patterns["python"].extend([
                    r"import\s+requests",
                    r"import\s+urllib",
                    r"import\s+http",
                    r"from\s+requests\s+import",
                    r"from\s+urllib\s+import",
                ])
            
            if not allow_file_system:
                dangerous_patterns["javascript"].extend([
                    r"require\s*\(\s*['\"]fs['\"]",
                    r"require\s*\(\s*['\"]path['\"]",
                ])
                dangerous_patterns["python"].extend([
                    r"open\s*\(",
                    r"file\s*\(",
                ])
            
            patterns = dangerous_patterns.get(language, [])
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    raise CodeValidationError(f"Dangerous operation detected: {pattern}")
        
        # Basic syntax validation
        if language == "javascript":
            await self._validate_javascript_syntax(code)
        elif language == "python":
            await self._validate_python_syntax(code)
    
    async def _validate_javascript_syntax(self, code: str) -> None:
        """Validate JavaScript syntax."""
        # Basic bracket matching
        brackets = {"(": ")", "[": "]", "{": "}"}
        stack = []
        
        for char in code:
            if char in brackets:
                stack.append(brackets[char])
            elif char in brackets.values():
                if not stack or stack.pop() != char:
                    raise CodeValidationError("JavaScript syntax error: Mismatched brackets")
        
        if stack:
            raise CodeValidationError("JavaScript syntax error: Unclosed brackets")
    
    async def _validate_python_syntax(self, code: str) -> None:
        """Validate Python syntax."""
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            raise CodeValidationError(f"Python syntax error: {e.msg} at line {e.lineno}")
    
    async def _execute_for_all_items(self, code: str, language: str, items: List[Dict[str, Any]], 
                                   timeout: int, safe_mode: bool, allow_network: bool, 
                                   allow_file_system: bool, max_memory_mb: int, 
                                   return_console_output: bool) -> Dict[str, Any]:
        """Execute code once for all items."""
        start_time = datetime.now()
        
        if language == "javascript":
            result = await self._execute_javascript_all_items(
                code, items, timeout, safe_mode, allow_network, allow_file_system, 
                max_memory_mb, return_console_output
            )
        else:  # python
            result = await self._execute_python_all_items(
                code, items, timeout, safe_mode, allow_network, allow_file_system,
                max_memory_mb, return_console_output
            )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        result["execution_time"] = execution_time
        
        return result
    
    async def _execute_for_each_item(self, code: str, language: str, items: List[Dict[str, Any]],
                                   timeout: int, safe_mode: bool, allow_network: bool,
                                   allow_file_system: bool, max_memory_mb: int,
                                   return_console_output: bool) -> Dict[str, Any]:
        """Execute code once for each item."""
        start_time = datetime.now()
        results = []
        console_outputs = []
        
        for index, item in enumerate(items):
            try:
                if language == "javascript":
                    item_result = await self._execute_javascript_each_item(
                        code, item, index, timeout, safe_mode, allow_network, 
                        allow_file_system, max_memory_mb, return_console_output
                    )
                else:  # python
                    item_result = await self._execute_python_each_item(
                        code, item, index, timeout, safe_mode, allow_network,
                        allow_file_system, max_memory_mb, return_console_output
                    )
                
                results.append(item_result["result"])
                if return_console_output and "console_output" in item_result:
                    console_outputs.append(item_result["console_output"])
                    
            except Exception as e:
                # Handle individual item errors
                error_result = {
                    "json": {"error": str(e)},
                    "pairedItem": {"item": index}
                }
                results.append(error_result)
                if return_console_output:
                    console_outputs.append(f"Error for item {index}: {str(e)}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "items": results,
            "execution_time": execution_time
        }
        
        if return_console_output and console_outputs:
            result["console_output"] = "\n".join(console_outputs)
        
        return result
    
    async def _execute_javascript_all_items(self, code: str, items: List[Dict[str, Any]], 
                                          timeout: int, safe_mode: bool, allow_network: bool,
                                          allow_file_system: bool, max_memory_mb: int,
                                          return_console_output: bool) -> Dict[str, Any]:
        """Execute JavaScript code for all items."""
        # Prepare JavaScript execution environment
        js_code = f"""
const items = {json.dumps(items)};
const console_output = [];

// Store original console
const originalConsoleLog = console.log;

// Override console.log to capture output
console.log = (...args) => {{
    console_output.push(args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' '));
}};

// Helper functions
const $input = {{
    all: () => items,
    first: () => items[0] || null,
    last: () => items[items.length - 1] || null,
    itemMatching: (index) => items[index] || null
}};

// Execute user code
const result = (function() {{
    {code}
}})();

// Restore original console.log and output result
console.log = originalConsoleLog;

const output = JSON.stringify({{
    result: result,
    console_output: console_output.join('\\n')
}});

console.log(output);
"""
        
        try:
            # Execute JavaScript using Node.js
            result = await self._run_node_js(js_code, timeout, max_memory_mb)
            parsed_result = json.loads(result)
            
            # Validate and normalize result
            items_result = parsed_result.get("result", [])
            if not isinstance(items_result, list):
                items_result = [{"json": items_result}] if items_result is not None else []
            
            # Ensure proper item format
            normalized_items = []
            for item in items_result:
                if isinstance(item, dict) and "json" in item:
                    normalized_items.append(item)
                else:
                    normalized_items.append({"json": item})
            
            response = {"items": normalized_items}
            
            if return_console_output and parsed_result.get("console_output"):
                response["console_output"] = parsed_result["console_output"]
            
            return response
            
        except Exception as e:
            raise CodeExecutionError(f"JavaScript execution failed: {str(e)}")
    
    async def _execute_javascript_each_item(self, code: str, item: Dict[str, Any], index: int,
                                          timeout: int, safe_mode: bool, allow_network: bool,
                                          allow_file_system: bool, max_memory_mb: int,
                                          return_console_output: bool) -> Dict[str, Any]:
        """Execute JavaScript code for a single item."""
        js_code = f"""
const item = {json.dumps(item)};
const console_output = [];

// Store original console
const originalConsoleLog = console.log;

// Override console.log to capture output
console.log = (...args) => {{
    console_output.push(args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' '));
}};

// Helper functions
const $input = {{
    item: item
}};

// Execute user code
const result = (function() {{
    {code}
}})();

// Restore original console.log and output result
console.log = originalConsoleLog;

const output = JSON.stringify({{
    result: result,
    console_output: console_output.join('\\n')
}});

console.log(output);
"""
        
        try:
            result = await self._run_node_js(js_code, timeout, max_memory_mb)
            parsed_result = json.loads(result)
            
            # Validate and normalize result
            item_result = parsed_result.get("result")
            if item_result is None:
                return {"result": None}
            
            # Ensure proper item format
            if isinstance(item_result, dict) and "json" in item_result:
                normalized_result = item_result
            else:
                normalized_result = {"json": item_result}
            
            # Add paired item reference
            normalized_result["pairedItem"] = {"item": index}
            
            response = {"result": normalized_result}
            
            if return_console_output and parsed_result.get("console_output"):
                response["console_output"] = parsed_result["console_output"]
            
            return response
            
        except Exception as e:
            raise CodeExecutionError(f"JavaScript execution failed: {str(e)}", item_index=index)
    
    async def _execute_python_all_items(self, code: str, items: List[Dict[str, Any]],
                                      timeout: int, safe_mode: bool, allow_network: bool,
                                      allow_file_system: bool, max_memory_mb: int,
                                      return_console_output: bool) -> Dict[str, Any]:
        """Execute Python code for all items."""
        python_code = f"""
import json
import sys
from io import StringIO

# Capture console output
console_output = StringIO()
sys.stdout = console_output

# Input data
items = {json.dumps(items)}

# Helper functions
class InputHelper:
    @staticmethod
    def all():
        return items
    
    @staticmethod
    def first():
        return items[0] if items else None
    
    @staticmethod
    def last():
        return items[-1] if items else None
    
    @staticmethod
    def item_matching(index):
        return items[index] if 0 <= index < len(items) else None

_input = InputHelper()

# Execute user code
try:
    exec('''
{code}
''')
    
    # Get result (should be set by user code)
    result = locals().get('result', items)
    
except Exception as e:
    result = {{"error": str(e)}}

# Restore stdout and get console output
sys.stdout = sys.__stdout__
console_out = console_output.getvalue()

# Return result
print(json.dumps({{
    "result": result,
    "console_output": console_out
}}))
"""
        
        try:
            result = await self._run_python(python_code, timeout, max_memory_mb)
            parsed_result = json.loads(result)
            
            # Validate and normalize result
            items_result = parsed_result.get("result", [])
            if not isinstance(items_result, list):
                items_result = [{"json": items_result}] if items_result is not None else []
            
            # Ensure proper item format
            normalized_items = []
            for item in items_result:
                if isinstance(item, dict) and "json" in item:
                    normalized_items.append(item)
                else:
                    normalized_items.append({"json": item})
            
            response = {"items": normalized_items}
            
            if return_console_output and parsed_result.get("console_output"):
                response["console_output"] = parsed_result["console_output"]
            
            return response
            
        except Exception as e:
            raise CodeExecutionError(f"Python execution failed: {str(e)}")
    
    async def _execute_python_each_item(self, code: str, item: Dict[str, Any], index: int,
                                      timeout: int, safe_mode: bool, allow_network: bool,
                                      allow_file_system: bool, max_memory_mb: int,
                                      return_console_output: bool) -> Dict[str, Any]:
        """Execute Python code for a single item."""
        python_code = f"""
import json
import sys
from io import StringIO

# Capture console output
console_output = StringIO()
sys.stdout = console_output

# Input data
item = {json.dumps(item)}

# Helper functions
class InputHelper:
    @property
    def item(self):
        return item

_input = InputHelper()

# Execute user code
try:
    exec('''
{code}
''')
    
    # Get result (should be set by user code)
    result = locals().get('result', item)
    
except Exception as e:
    result = {{"error": str(e)}}

# Restore stdout and get console output
sys.stdout = sys.__stdout__
console_out = console_output.getvalue()

# Return result
print(json.dumps({{
    "result": result,
    "console_output": console_out
}}))
"""
        
        try:
            result = await self._run_python(python_code, timeout, max_memory_mb)
            parsed_result = json.loads(result)
            
            # Validate and normalize result
            item_result = parsed_result.get("result")
            if item_result is None:
                return {"result": None}
            
            # Ensure proper item format
            if isinstance(item_result, dict) and "json" in item_result:
                normalized_result = item_result
            else:
                normalized_result = {"json": item_result}
            
            # Add paired item reference
            normalized_result["pairedItem"] = {"item": index}
            
            response = {"result": normalized_result}
            
            if return_console_output and parsed_result.get("console_output"):
                response["console_output"] = parsed_result["console_output"]
            
            return response
            
        except Exception as e:
            raise CodeExecutionError(f"Python execution failed: {str(e)}", item_index=index)
    
    async def _run_node_js(self, code: str, timeout: int, max_memory_mb: int) -> str:
        """Run JavaScript code using Node.js."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run Node.js with memory and timeout limits
            process = await asyncio.create_subprocess_exec(
                'node',
                '--max-old-space-size=' + str(max_memory_mb),
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                    raise CodeExecutionError(f"Node.js execution failed: {error_msg}")
                
                output = stdout.decode('utf-8').strip()
                if not output:
                    raise CodeExecutionError("JavaScript execution produced no output")
                
                return output
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise CodeExecutionError(f"JavaScript execution timed out after {timeout} seconds")
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _run_python(self, code: str, timeout: int, max_memory_mb: int) -> str:
        """Run Python code with restrictions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run Python with timeout
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                    raise CodeExecutionError(f"Python execution failed: {error_msg}")
                
                return stdout.decode('utf-8').strip()
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise CodeExecutionError(f"Python execution timed out after {timeout} seconds")
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def get_capabilities(self) -> List[str]:
        """Get Code connector capabilities."""
        return [
            "code_execution",
            "data_transformation", 
            "javascript",
            "python",
            "custom_logic",
            "data_processing"
        ]
    
    def get_use_cases(self) -> List[Dict[str, Any]]:
        """Get Code connector use cases."""
        return [
            {
                "title": "Data Transformation",
                "description": "Transform and manipulate data using custom JavaScript or Python code",
                "category": "data_processing",
                "complexity": "intermediate",
                "example_prompts": [
                    "Transform JSON data with custom logic",
                    "Process items using JavaScript functions"
                ]
            },
            {
                "title": "Custom Business Logic",
                "description": "Implement custom business rules and calculations",
                "category": "business_logic",
                "complexity": "advanced",
                "example_prompts": [
                    "Calculate custom metrics using Python",
                    "Apply business rules to workflow data"
                ]
            },
            {
                "title": "Data Filtering",
                "description": "Filter and validate data using custom conditions",
                "category": "data_processing", 
                "complexity": "simple",
                "example_prompts": [
                    "Filter items based on custom criteria",
                    "Validate data using custom rules"
                ]
            },
            {
                "title": "API Response Processing",
                "description": "Process and format API responses with custom code",
                "category": "integration",
                "complexity": "intermediate",
                "example_prompts": [
                    "Format API response data",
                    "Extract specific fields from API results"
                ]
            }
        ]