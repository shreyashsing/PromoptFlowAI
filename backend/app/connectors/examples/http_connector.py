"""
HTTP Request Connector - Example implementation using the base connector framework.
"""
import asyncio
from typing import Dict, Any, Optional
import json

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException


class HttpConnector(BaseConnector):
    """
    HTTP Request Connector for making REST API calls.
    
    Supports GET, POST, PUT, DELETE methods with headers, authentication,
    and request/response handling.
    """
    
    def _get_category(self) -> str:
        return "data_sources"
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to make the HTTP request to",
                    "format": "uri"
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method to use",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers to include in the request",
                    "additionalProperties": {"type": "string"}
                },
                "body": {
                    "type": ["object", "string", "null"],
                    "description": "Request body (for POST, PUT, PATCH methods)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300
                },
                "follow_redirects": {
                    "type": "boolean",
                    "description": "Whether to follow HTTP redirects",
                    "default": True
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute HTTP request with the provided parameters.
        
        Args:
            params: HTTP request parameters
            context: Execution context with auth tokens
            
        Returns:
            ConnectorResult with response data or error
        """
        try:
            # Extract parameters
            url = params["url"]
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {})
            body = params.get("body")
            timeout = params.get("timeout", 30)
            follow_redirects = params.get("follow_redirects", True)
            
            # Add authentication headers if available
            auth_headers = await self._prepare_auth_headers(context.auth_tokens)
            headers.update(auth_headers)
            
            # Prepare request body
            if body and isinstance(body, dict):
                body = json.dumps(body)
                headers.setdefault("Content-Type", "application/json")
            
            # Simulate HTTP request (in real implementation, use httpx or similar)
            response_data = await self._simulate_http_request(
                url, method, headers, body, timeout, follow_redirects
            )
            
            return ConnectorResult(
                success=True,
                data=response_data,
                metadata={
                    "url": url,
                    "method": method,
                    "status_code": response_data.get("status_code", 200),
                    "response_time": response_data.get("response_time", 0.1)
                }
            )
            
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"HTTP request failed: {str(e)}",
                metadata={"url": params.get("url", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for HTTP requests.
        
        Returns:
            AuthRequirements supporting API key or no auth
        """
        return AuthRequirements(
            type=AuthType.NONE,  # HTTP connector supports optional auth
            fields={
                "api_key": "API key for authentication (optional)",
                "auth_header": "Header name for API key (optional, default: Authorization)"
            },
            instructions="Provide API key if the endpoint requires authentication. "
                        "The key will be sent in the Authorization header by default."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test connection with provided authentication.
        
        Args:
            auth_tokens: Authentication tokens
            
        Returns:
            True if connection test passes
        """
        # In a real implementation, this would make a test request
        # For now, just validate that required auth fields are present
        if "api_key" in auth_tokens and auth_tokens["api_key"]:
            return True
        return True  # Allow no-auth requests
    
    async def _prepare_auth_headers(self, auth_tokens: Dict[str, str]) -> Dict[str, str]:
        """
        Prepare authentication headers from tokens.
        
        Args:
            auth_tokens: Authentication tokens
            
        Returns:
            Dictionary of headers to add to the request
        """
        headers = {}
        
        if "api_key" in auth_tokens and auth_tokens["api_key"]:
            auth_header = auth_tokens.get("auth_header", "Authorization")
            api_key = auth_tokens["api_key"]
            
            # Handle different auth header formats
            if auth_header.lower() == "authorization":
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                headers[auth_header] = api_key
        
        return headers
    
    async def _simulate_http_request(
        self, 
        url: str, 
        method: str, 
        headers: Dict[str, str], 
        body: Optional[str],
        timeout: float,
        follow_redirects: bool
    ) -> Dict[str, Any]:
        """
        Simulate HTTP request for testing purposes.
        In a real implementation, this would use httpx or similar library.
        
        Args:
            url: Request URL
            method: HTTP method
            headers: Request headers
            body: Request body
            timeout: Request timeout
            follow_redirects: Whether to follow redirects
            
        Returns:
            Simulated response data
        """
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate different responses based on URL
        if "error" in url.lower():
            raise ConnectorException("Simulated HTTP error")
        
        return {
            "status_code": 200,
            "headers": {
                "content-type": "application/json",
                "server": "test-server"
            },
            "body": {
                "message": f"Successful {method} request to {url}",
                "received_headers": dict(headers),
                "received_body": body
            },
            "response_time": 0.1
        }
    
    def get_example_params(self) -> Dict[str, Any]:
        """
        Get example parameters for this connector.
        
        Returns:
            Dictionary with example parameter values
        """
        return {
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {
                "Accept": "application/json",
                "User-Agent": "PromptFlow-AI/1.0"
            },
            "timeout": 30
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """
        Get human-readable hints for connector parameters.
        
        Returns:
            Dictionary mapping parameter names to description hints
        """
        return {
            "url": "Full URL including protocol (https://api.example.com/endpoint)",
            "method": "HTTP method: GET for retrieving data, POST for creating, PUT for updating",
            "headers": "Key-value pairs for HTTP headers (e.g., Accept, Content-Type)",
            "body": "Request payload for POST/PUT requests (JSON object or string)",
            "timeout": "Maximum time to wait for response (1-300 seconds)"
        }