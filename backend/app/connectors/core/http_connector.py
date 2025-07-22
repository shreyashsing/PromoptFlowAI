"""
HTTP Request Connector - Production implementation with full REST support.
"""
import asyncio
import json
from typing import Dict, Any, Optional, Union
import httpx
from urllib.parse import urljoin, urlparse

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, ValidationException
from app.core.error_utils import handle_connector_errors, handle_external_api_errors


class HttpConnector(BaseConnector):
    """
    HTTP Request Connector for making REST API calls.
    
    Supports all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    with comprehensive authentication, headers, query parameters, and error handling.
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
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers to include in the request",
                    "additionalProperties": {"type": "string"},
                    "default": {}
                },
                "query_params": {
                    "type": "object", 
                    "description": "Query parameters to append to the URL",
                    "additionalProperties": {"type": ["string", "number", "boolean"]},
                    "default": {}
                },
                "body": {
                    "type": ["object", "string", "array", "null"],
                    "description": "Request body (for POST, PUT, PATCH methods)"
                },
                "json_body": {
                    "type": "boolean",
                    "description": "Whether to automatically serialize body as JSON",
                    "default": True
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
                },
                "verify_ssl": {
                    "type": "boolean",
                    "description": "Whether to verify SSL certificates",
                    "default": True
                },
                "max_retries": {
                    "type": "integer",
                    "description": "Maximum number of retry attempts for failed requests",
                    "default": 3,
                    "minimum": 0,
                    "maximum": 10
                },
                "retry_delay": {
                    "type": "number",
                    "description": "Delay between retry attempts in seconds",
                    "default": 1.0,
                    "minimum": 0.1,
                    "maximum": 60.0
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    
    @handle_connector_errors("HTTP")
    @handle_external_api_errors("HTTP Request", retryable=True)
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
            # Extract and validate parameters
            url = params["url"]
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {}).copy()
            query_params = params.get("query_params", {})
            body = params.get("body")
            json_body = params.get("json_body", True)
            timeout = params.get("timeout", 30)
            follow_redirects = params.get("follow_redirects", True)
            verify_ssl = params.get("verify_ssl", True)
            max_retries = params.get("max_retries", 3)
            retry_delay = params.get("retry_delay", 1.0)
            
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValidationException("Invalid URL format")
            
            # Add authentication headers if available
            auth_headers = await self._prepare_auth_headers(context.auth_tokens)
            headers.update(auth_headers)
            
            # Prepare request body
            prepared_body = await self._prepare_body(body, json_body, headers)
            
            # Execute request with retry logic
            response_data = await self._execute_request_with_retry(
                url=url,
                method=method,
                headers=headers,
                query_params=query_params,
                body=prepared_body,
                timeout=timeout,
                follow_redirects=follow_redirects,
                verify_ssl=verify_ssl,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            
            return ConnectorResult(
                success=True,
                data=response_data,
                metadata={
                    "url": url,
                    "method": method,
                    "status_code": response_data.get("status_code"),
                    "response_time": response_data.get("response_time"),
                    "content_type": response_data.get("headers", {}).get("content-type"),
                    "content_length": len(str(response_data.get("body", "")))
                }
            )
            
        except ValidationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"HTTP request failed: {str(e)}",
                metadata={"url": params.get("url", "unknown"), "method": params.get("method", "GET")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for HTTP requests.
        
        Returns:
            AuthRequirements supporting multiple auth types
        """
        return AuthRequirements(
            type=AuthType.NONE,  # HTTP connector supports optional auth
            fields={
                "api_key": "API key for authentication (optional)",
                "auth_header": "Header name for API key (optional, default: Authorization)",
                "auth_prefix": "Prefix for auth header value (optional, default: Bearer)",
                "username": "Username for basic authentication (optional)",
                "password": "Password for basic authentication (optional)"
            },
            instructions="Provide authentication credentials if the endpoint requires them. "
                        "Supports API key authentication (via Authorization header) or "
                        "HTTP Basic authentication (username/password)."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test connection with provided authentication.
        
        Args:
            auth_tokens: Authentication tokens
            
        Returns:
            True if connection test passes
        """
        # For HTTP connector, we can't test without a specific URL
        # Just validate that auth tokens are properly formatted
        if "api_key" in auth_tokens and auth_tokens["api_key"]:
            return True
        if "username" in auth_tokens and "password" in auth_tokens:
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
        
        # API Key authentication
        if "api_key" in auth_tokens and auth_tokens["api_key"]:
            auth_header = auth_tokens.get("auth_header", "Authorization")
            auth_prefix = auth_tokens.get("auth_prefix", "Bearer")
            api_key = auth_tokens["api_key"]
            
            if auth_prefix:
                headers[auth_header] = f"{auth_prefix} {api_key}"
            else:
                headers[auth_header] = api_key
        
        # Basic authentication
        elif "username" in auth_tokens and "password" in auth_tokens:
            import base64
            credentials = f"{auth_tokens['username']}:{auth_tokens['password']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        
        return headers
    
    async def _prepare_body(
        self, 
        body: Any, 
        json_body: bool, 
        headers: Dict[str, str]
    ) -> Optional[Union[str, bytes]]:
        """
        Prepare request body based on content type and parameters.
        
        Args:
            body: Raw body data
            json_body: Whether to serialize as JSON
            headers: Request headers (may be modified)
            
        Returns:
            Prepared body data
        """
        if body is None:
            return None
        
        # If body is already a string or bytes, return as-is
        if isinstance(body, (str, bytes)):
            return body
        
        # Handle JSON serialization
        if json_body and isinstance(body, (dict, list)):
            headers.setdefault("Content-Type", "application/json")
            return json.dumps(body, ensure_ascii=False)
        
        # Handle form data
        if isinstance(body, dict) and not json_body:
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            from urllib.parse import urlencode
            return urlencode(body)
        
        # Default: convert to string
        return str(body)
    
    async def _execute_request_with_retry(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        query_params: Dict[str, Any],
        body: Optional[Union[str, bytes]],
        timeout: float,
        follow_redirects: bool,
        verify_ssl: bool,
        max_retries: int,
        retry_delay: float
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic.
        
        Args:
            url: Request URL
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            body: Request body
            timeout: Request timeout
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries
            
        Returns:
            Response data dictionary
            
        Raises:
            ConnectorException: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                    verify=verify_ssl
                ) as client:
                    
                    # Record start time
                    import time
                    start_time = time.time()
                    
                    # Make the request
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=query_params,
                        content=body
                    )
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Parse response
                    response_data = await self._parse_response(response, response_time)
                    
                    # Check if we should retry based on status code
                    if response.status_code >= 500 and attempt < max_retries:
                        last_error = ConnectorException(f"Server error: {response.status_code}")
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    
                    return response_data
                    
            except httpx.TimeoutException as e:
                last_error = ConnectorException(f"Request timeout: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                    
            except httpx.RequestError as e:
                last_error = ConnectorException(f"Request error: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                    
            except Exception as e:
                last_error = ConnectorException(f"Unexpected error: {str(e)}")
                break  # Don't retry unexpected errors
        
        # All retries failed
        raise last_error or ConnectorException("Request failed after all retry attempts")
    
    async def _parse_response(self, response: httpx.Response, response_time: float) -> Dict[str, Any]:
        """
        Parse HTTP response into standardized format.
        
        Args:
            response: httpx Response object
            response_time: Time taken for the request
            
        Returns:
            Parsed response data
        """
        # Get response headers
        response_headers = dict(response.headers)
        
        # Parse response body
        content_type = response_headers.get("content-type", "").lower()
        
        try:
            if "application/json" in content_type:
                body = response.json()
            elif "text/" in content_type or "application/xml" in content_type:
                body = response.text
            else:
                # For binary content, return base64 encoded data
                import base64
                body = {
                    "content_type": content_type,
                    "data": base64.b64encode(response.content).decode(),
                    "size": len(response.content)
                }
        except Exception:
            # Fallback to text if parsing fails
            body = response.text
        
        return {
            "status_code": response.status_code,
            "headers": response_headers,
            "body": body,
            "response_time": response_time,
            "url": str(response.url),
            "is_success": 200 <= response.status_code < 300,
            "is_redirect": 300 <= response.status_code < 400,
            "is_client_error": 400 <= response.status_code < 500,
            "is_server_error": response.status_code >= 500
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
            "query_params": {
                "limit": 10,
                "offset": 0
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
            "method": "HTTP method: GET for retrieving, POST for creating, PUT for updating, DELETE for removing",
            "headers": "Key-value pairs for HTTP headers (Accept, Content-Type, Authorization, etc.)",
            "query_params": "URL query parameters as key-value pairs",
            "body": "Request payload for POST/PUT/PATCH requests (JSON object, string, or array)",
            "json_body": "Automatically serialize body as JSON and set Content-Type header",
            "timeout": "Maximum time to wait for response (1-300 seconds)",
            "follow_redirects": "Whether to automatically follow HTTP redirects",
            "verify_ssl": "Whether to verify SSL certificates (disable only for testing)",
            "max_retries": "Number of retry attempts for failed requests (0-10)",
            "retry_delay": "Base delay between retries in seconds (exponential backoff applied)"
        }