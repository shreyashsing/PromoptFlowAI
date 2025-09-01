"""
Perplexity AI Connector - Real-time web-augmented QA and grounded search.
"""
import json
from typing import Dict, Any, List, Optional
import httpx

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class PerplexityConnector(BaseConnector):
    """
    Perplexity AI Connector for real-time web search, blog discovery, and content analysis.
    
    Provides access to Perplexity's AI models with real-time web search capabilities for finding
    recent blog posts, articles, news, and web content. Perfect for discovering the latest blogs
    from companies like Google, analyzing web content, and getting up-to-date information with
    citation support and various model options for different use cases.
    """
    
    def _get_connector_name(self) -> str:
        return "perplexity_search"
    
    def _get_category(self) -> str:
        return "ai_services"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Perplexity connector."""
        return {
            "action": "search",
            "query": "latest AI developments 2024",
            "model": "llama-3.1-sonar-small-128k-online"
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Perplexity-specific example prompts."""
        return [
            "Search for the latest AI news and developments",
            "Find recent blog posts about machine learning",
            "Get current information about cryptocurrency trends",
            "Search for company announcements from Google",
            "Find recent articles about climate change",
            "Get up-to-date information about stock market",
            "Search for latest technology breakthroughs"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Perplexity-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Default action is search
        suggestions["action"] = "search"
        
        # Use the user prompt as the search query
        suggestions["query"] = user_prompt
        
        # Model selection based on query complexity
        if len(user_prompt) > 100 or "complex" in prompt_lower or "detailed" in prompt_lower:
            suggestions["model"] = "llama-3.1-sonar-large-128k-online"
        else:
            suggestions["model"] = "llama-3.1-sonar-small-128k-online"
        
        # Extract specific search terms
        import re
        search_patterns = [
            r'search.*?for\s+(.+)',
            r'find.*?about\s+(.+)',
            r'get.*?information.*?about\s+(.+)',
            r'latest.*?(.+)'
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                search_term = match.group(1).strip()
                # Clean up the search term
                search_term = re.sub(r'\s+(and|or|from|in|about)\s+.*$', '', search_term)
                suggestions["query"] = search_term
                break
        
        # Add time-based modifiers for recent information
        if any(word in prompt_lower for word in ["latest", "recent", "current", "new", "today", "2024"]):
            current_query = suggestions.get("query", user_prompt)
            if "2024" not in current_query:
                suggestions["query"] = f"{current_query} 2024"
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Perplexity AI action to perform",
                    "enum": ["chat", "search", "summarize", "analyze"],
                    "default": "chat"
                },
                # Core parameters
                "query": {
                    "type": "string",
                    "description": "Question or search query for Perplexity AI"
                },
                "messages": {
                    "type": ["array", "string"],
                    "description": "Conversation messages for chat completion (array or JSON string)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                            "content": {"type": "string"}
                        },
                        "required": ["role", "content"]
                    }
                },
                # Model configuration
                "model": {
                    "type": "string",
                    "description": "Perplexity model to use",
                    "enum": [
                        "sonar",
                        "llama-3.1-sonar-small-128k-online",
                        "llama-3.1-sonar-large-128k-online",
                        "llama-3.1-sonar-huge-128k-online",
                        "llama-3.1-sonar-small-128k-chat",
                        "llama-3.1-sonar-large-128k-chat",
                        "llama-3.1-sonar-huge-128k-chat"
                    ],
                    "default": "sonar"
                },
                # Generation parameters
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum number of tokens to generate",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 4000
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0.0 to 2.0)",
                    "default": 0.2,
                    "minimum": 0.0,
                    "maximum": 2.0
                },
                "top_p": {
                    "type": "number",
                    "description": "Nucleus sampling parameter",
                    "default": 0.9,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "top_k": {
                    "type": "integer",
                    "description": "Top-k sampling parameter",
                    "default": 0,
                    "minimum": 0,
                    "maximum": 2048
                },
                "frequency_penalty": {
                    "type": "number",
                    "description": "Frequency penalty (-2.0 to 2.0)",
                    "default": 1.0,
                    "minimum": -2.0,
                    "maximum": 2.0
                },
                "presence_penalty": {
                    "type": "number",
                    "description": "Presence penalty (-2.0 to 2.0)",
                    "default": 0.0,
                    "minimum": -2.0,
                    "maximum": 2.0
                },
                # Search and citation parameters
                "return_citations": {
                    "type": "boolean",
                    "description": "Whether to return source citations",
                    "default": True
                },
                "return_images": {
                    "type": "boolean",
                    "description": "Whether to return related images",
                    "default": False
                },
                "return_related_questions": {
                    "type": "boolean",
                    "description": "Whether to return related questions",
                    "default": False
                },
                "search_domain_filter": {
                    "type": ["array", "string"],
                    "description": "Domains to include/exclude in search (array or comma-separated string)",
                    "items": {"type": "string"}
                },
                "search_recency_filter": {
                    "type": "string",
                    "description": "Recency filter for search results",
                    "enum": ["month", "week", "day", "hour"],
                    "default": "month"
                },
                # Content processing
                "content": {
                    "type": "string",
                    "description": "Content to analyze or summarize"
                },
                "content_url": {
                    "type": "string",
                    "description": "URL of content to analyze",
                    "format": "uri"
                },
                "summary_length": {
                    "type": "string",
                    "description": "Desired summary length",
                    "enum": ["short", "medium", "long"],
                    "default": "medium"
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform",
                    "enum": ["sentiment", "topics", "entities", "summary", "key_points"],
                    "default": "summary"
                },
                # System prompt
                "system_prompt": {
                    "type": "string",
                    "description": "System prompt to guide the AI's behavior"
                },
                # Streaming parameter (ignored but allowed for compatibility)
                "stream": {
                    "type": "boolean",
                    "description": "Enable streaming response (not supported, parameter ignored)",
                    "default": False
                }
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"enum": ["chat", "search"]}}},
                    "then": {
                        "anyOf": [
                            {"required": ["query"]},
                            {"required": ["messages"]}
                        ]
                    }
                },
                {
                    "if": {"properties": {"action": {"enum": ["summarize", "analyze"]}}},
                    "then": {
                        "anyOf": [
                            {"required": ["content"]},
                            {"required": ["content_url"]}
                        ]
                    }
                }
            ]
        }
    
    def _validate_and_fix_model(self, model: str) -> str:
        """
        Validate and fix model parameter to use current valid models.
        
        Args:
            model: The model name to validate
            
        Returns:
            Valid model name
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Use single model name to avoid API issues
        valid_models = ["sonar"]
        
        logger.info(f"Validating Perplexity model: {model}")
        
        # If model is valid, return as-is
        if model in valid_models:
            logger.info(f"Model {model} is valid, using as-is")
            return model
            
        # Map all models to single "sonar" model
        mapped_model = "sonar"
        logger.info(f"Model {model} mapped to {mapped_model}")
        return mapped_model

    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters with normalization for array parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid
            
        Raises:
            ValidationException: If parameters are invalid
        """
        # Normalize array parameters before validation
        normalized_params = self._normalize_array_parameters(params)
        
        # Use the parent validation with normalized parameters
        return await super().validate_params(normalized_params)

    def _normalize_array_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize parameters that can be either strings or arrays.
        
        Args:
            params: Raw parameters
            
        Returns:
            Normalized parameters with proper array formats
        """
        normalized = params.copy()
        
        # Convert search_domain_filter from string to array if needed
        if "search_domain_filter" in normalized:
            domain_filter = normalized["search_domain_filter"]
            if isinstance(domain_filter, str):
                if domain_filter.strip():
                    # Split by comma and clean up whitespace
                    normalized["search_domain_filter"] = [
                        domain.strip() for domain in domain_filter.split(",") 
                        if domain.strip()
                    ]
                else:
                    # Empty string becomes empty array
                    normalized["search_domain_filter"] = []
        
        # Convert messages from string to array if needed
        if "messages" in normalized:
            messages = normalized["messages"]
            if isinstance(messages, str):
                if messages.strip():
                    # Try to parse as JSON array
                    try:
                        import json
                        parsed_messages = json.loads(messages)
                        if isinstance(parsed_messages, list):
                            normalized["messages"] = parsed_messages
                        else:
                            # If it's not a list, create a simple user message
                            normalized["messages"] = [{"role": "user", "content": messages}]
                    except json.JSONDecodeError:
                        # If JSON parsing fails, create a simple user message
                        normalized["messages"] = [{"role": "user", "content": messages}]
                else:
                    # Empty string becomes empty array
                    normalized["messages"] = []
        
        return normalized

    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute Perplexity AI operation with the provided parameters.
        
        Args:
            params: Perplexity AI operation parameters
            context: Execution context with API key
            
        Returns:
            ConnectorResult with AI response or error
        """
        try:
            action = params["action"]
            api_key = context.auth_tokens.get("api_key")
            
            if not api_key:
                raise AuthenticationException("Perplexity AI API key not found")
            
            # Normalize array parameters
            params = self._normalize_array_parameters(params)
            
            # Validate and fix model parameter
            original_model = params.get("model", "sonar")
            validated_model = self._validate_and_fix_model(original_model)
            params["model"] = validated_model
            
            # Route to appropriate action handler
            if action == "chat":
                result = await self._chat_completion(params, api_key)
            elif action == "search":
                result = await self._web_search(params, api_key)
            elif action == "summarize":
                result = await self._summarize_content(params, api_key)
            elif action == "analyze":
                result = await self._analyze_content(params, api_key)
            else:
                raise ConnectorException(f"Unsupported Perplexity AI action: {action}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "action": action,
                    "model": validated_model,
                    "original_model": original_model if original_model != validated_model else None,
                    "provider": "perplexity"
                }
            )
            
        except AuthenticationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Perplexity AI operation failed: {str(e)}",
                metadata={"action": params.get("action", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for Perplexity AI.
        
        Returns:
            AuthRequirements for Perplexity AI API key
        """
        return AuthRequirements(
            type=AuthType.API_KEY,
            fields={
                "api_key": "Perplexity AI API key"
            },
            instructions="Get your Perplexity AI API key from https://www.perplexity.ai/settings/api. "
                        "The API key should start with 'pplx-'."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test Perplexity AI API connection with provided API key.
        
        Args:
            auth_tokens: API key tokens
            
        Returns:
            True if connection successful
        """
        try:
            api_key = auth_tokens.get("api_key")
            if not api_key:
                return False
            
            # Test with a simple chat completion
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10
                    },
                    timeout=30.0
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def _chat_completion(self, params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Perform chat completion with Perplexity AI."""
        # Prepare messages
        if "messages" in params:
            messages = params["messages"]
        else:
            # Convert query to messages format
            messages = []
            if params.get("system_prompt"):
                messages.append({"role": "system", "content": params["system_prompt"]})
            messages.append({"role": "user", "content": params["query"]})
        
        # Prepare request payload
        request_data = {
            "model": params.get("model", "sonar"),
            "messages": messages,
            "max_tokens": params.get("max_tokens", 1000),
            "temperature": params.get("temperature", 0.2),
            "top_p": params.get("top_p", 0.9),
            "return_citations": params.get("return_citations", True),
            "return_images": params.get("return_images", False),
            "return_related_questions": params.get("return_related_questions", False),
            "frequency_penalty": params.get("frequency_penalty", 1.0),
            "presence_penalty": params.get("presence_penalty", 0.0)
        }
        
        # Add optional parameters
        if params.get("top_k", 0) > 0:
            request_data["top_k"] = params["top_k"]
        
        if params.get("search_domain_filter"):
            request_data["search_domain_filter"] = params["search_domain_filter"]
        
        if params.get("search_recency_filter"):
            request_data["search_recency_filter"] = params["search_recency_filter"]
        
        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_data,
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Perplexity API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract and format response
            choice = result["choices"][0]
            message = choice["message"]
            
            formatted_result = {
                "response": message["content"],
                "model": result["model"],
                "usage": result.get("usage", {}),
                "finish_reason": choice.get("finish_reason")
            }
            
            # Add citations if available
            if "citations" in result:
                formatted_result["citations"] = result["citations"]
            
            # Add related questions if available
            if "related_questions" in result:
                formatted_result["related_questions"] = result["related_questions"]
            
            # Add images if available
            if "images" in result:
                formatted_result["images"] = result["images"]
            
            return formatted_result
    
    async def _web_search(self, params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Perform web search with Perplexity AI."""
        query = params.get("query") or params.get("messages", [{}])[-1].get("content", "")
        
        # Use sonar model for web search
        model = params.get("model", "sonar")
        
        # Prepare search-optimized request
        messages = [
            {"role": "system", "content": "You are a helpful assistant that provides accurate, up-to-date information with proper citations."},
            {"role": "user", "content": f"Search for and provide comprehensive information about: {query}"}
        ]
        
        search_params = {
            **params,
            "messages": messages,
            "model": model,
            "return_citations": True,
            "return_related_questions": True
        }
        
        return await self._chat_completion(search_params, api_key)
    
    async def _summarize_content(self, params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Summarize content using Perplexity AI."""
        content = params.get("content")
        content_url = params.get("content_url")
        summary_length = params.get("summary_length", "medium")
        
        if not content and not content_url:
            raise ConnectorException("Either 'content' or 'content_url' must be provided for summarization")
        
        # Prepare summarization prompt
        length_instructions = {
            "short": "Provide a brief, concise summary in 2-3 sentences.",
            "medium": "Provide a comprehensive summary in 1-2 paragraphs.",
            "long": "Provide a detailed summary with key points and important details."
        }
        
        if content_url:
            prompt = f"Please summarize the content from this URL: {content_url}\n\n{length_instructions[summary_length]}"
        else:
            prompt = f"Please summarize the following content:\n\n{content}\n\n{length_instructions[summary_length]}"
        
        messages = [
            {"role": "system", "content": "You are an expert at creating clear, accurate summaries of content."},
            {"role": "user", "content": prompt}
        ]
        
        summary_params = {
            **params,
            "messages": messages,
            "model": params.get("model", "sonar"),
            "temperature": 0.1  # Lower temperature for more consistent summaries
        }
        
        result = await self._chat_completion(summary_params, api_key)
        
        # Add summary metadata
        result["summary_type"] = summary_length
        result["source_type"] = "url" if content_url else "text"
        if content_url:
            result["source_url"] = content_url
        
        return result
    
    async def _analyze_content(self, params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Analyze content using Perplexity AI."""
        content = params.get("content")
        content_url = params.get("content_url")
        analysis_type = params.get("analysis_type", "summary")
        
        if not content and not content_url:
            raise ConnectorException("Either 'content' or 'content_url' must be provided for analysis")
        
        # Prepare analysis prompts
        analysis_prompts = {
            "sentiment": "Analyze the sentiment of this content. Provide the overall sentiment (positive, negative, neutral) and explain the reasoning.",
            "topics": "Identify and list the main topics and themes discussed in this content.",
            "entities": "Extract and categorize the key entities (people, organizations, locations, dates, etc.) mentioned in this content.",
            "summary": "Provide a comprehensive analysis and summary of this content, including key points and insights.",
            "key_points": "Extract and list the key points, main arguments, and important takeaways from this content."
        }
        
        if content_url:
            prompt = f"Please analyze the content from this URL: {content_url}\n\n{analysis_prompts[analysis_type]}"
        else:
            prompt = f"Please analyze the following content:\n\n{content}\n\n{analysis_prompts[analysis_type]}"
        
        messages = [
            {"role": "system", "content": "You are an expert content analyst who provides thorough, structured analysis."},
            {"role": "user", "content": prompt}
        ]
        
        analysis_params = {
            **params,
            "messages": messages,
            "model": params.get("model", "sonar"),
            "temperature": 0.2
        }
        
        result = await self._chat_completion(analysis_params, api_key)
        
        # Add analysis metadata
        result["analysis_type"] = analysis_type
        result["source_type"] = "url" if content_url else "text"
        if content_url:
            result["source_url"] = content_url
        
        return result
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Perplexity AI operations."""
        return {
            "action": "chat",
            "query": "What are the latest developments in artificial intelligence?",
            "model": "sonar",
            "max_tokens": 1000,
            "temperature": 0.2,
            "return_citations": True,
            "return_related_questions": True
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for Perplexity AI connector."""
        return {
            "action": "Operation: chat (Q&A), search (web search), summarize (content summary), analyze (content analysis)",
            "query": "Question or search query for the AI",
            "model": "AI model to use - 'online' models have web access, 'chat' models are faster",
            "max_tokens": "Maximum response length (1-4000 tokens)",
            "temperature": "Response creativity (0.0=focused, 2.0=creative)",
            "return_citations": "Include source citations in response (recommended: true)",
            "content": "Text content to summarize or analyze",
            "content_url": "URL of content to process",
            "summary_length": "Summary detail level: short, medium, or long"
        }