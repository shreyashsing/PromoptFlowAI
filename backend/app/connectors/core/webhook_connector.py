"""
Webhook Connector - For receiving and processing external events.
"""
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, ValidationException


class WebhookConnector(BaseConnector):
    """
    Webhook Connector for receiving external events and data.
    
    Supports webhook registration, payload validation, signature verification,
    and event processing with filtering and transformation capabilities.
    """
    
    def __init__(self):
        super().__init__()
        self._webhook_store = {}  # In-memory store for demo (use database in production)
    
    def _get_category(self) -> str:
        return "triggers"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Webhook connector."""
        return {
            "action": "register",
            "webhook_url": "https://your-app.com/webhook",
            "events": ["user.created", "order.completed"]
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Webhook-specific example prompts."""
        return [
            "Register a webhook to receive user events",
            "Set up webhook for order notifications",
            "Receive webhook data from external service",
            "List all registered webhooks",
            "Delete a webhook endpoint",
            "Test webhook connectivity",
            "Process incoming webhook payload"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Webhook-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Webhook action inference
        if "register" in prompt_lower or "create" in prompt_lower or "setup" in prompt_lower:
            suggestions["action"] = "register"
        elif "receive" in prompt_lower or "process" in prompt_lower:
            suggestions["action"] = "receive"
        elif "list" in prompt_lower or "show" in prompt_lower:
            suggestions["action"] = "list"
        elif "delete" in prompt_lower or "remove" in prompt_lower:
            suggestions["action"] = "delete"
        elif "test" in prompt_lower:
            suggestions["action"] = "test"
        
        # Extract webhook URL
        import re
        url_patterns = [
            r'https?://[^\s]+',
            r'webhook.*?url\s+(https?://[^\s]+)',
            r'endpoint\s+(https?://[^\s]+)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, user_prompt)
            if match:
                suggestions["webhook_url"] = match.group(1) if len(match.groups()) > 0 else match.group(0)
                break
        
        # Extract event types
        event_patterns = [
            r'for\s+([a-z_\.]+)\s+events?',
            r'events?\s+([a-z_\.]+)',
            r'when\s+([a-z_\.]+)'
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                event_type = match.group(1)
                suggestions["events"] = [event_type]
                break
        
        # Common event types based on keywords
        if "user" in prompt_lower:
            suggestions["events"] = ["user.created", "user.updated", "user.deleted"]
        elif "order" in prompt_lower:
            suggestions["events"] = ["order.created", "order.completed", "order.cancelled"]
        elif "payment" in prompt_lower:
            suggestions["events"] = ["payment.succeeded", "payment.failed"]
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Webhook action to perform",
                    "enum": ["register", "receive", "list", "delete", "test"],
                    "default": "receive"
                },
                # Webhook registration
                "webhook_name": {
                    "type": "string",
                    "description": "Unique name for the webhook"
                },
                "webhook_url": {
                    "type": "string",
                    "description": "URL endpoint for the webhook",
                    "format": "uri"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the webhook purpose"
                },
                "allowed_methods": {
                    "type": "array",
                    "description": "HTTP methods allowed for this webhook",
                    "items": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                    "default": ["POST"]
                },
                # Security settings
                "secret": {
                    "type": "string",
                    "description": "Secret key for signature verification"
                },
                "signature_header": {
                    "type": "string",
                    "description": "Header name containing the signature",
                    "default": "X-Hub-Signature-256"
                },
                "signature_algorithm": {
                    "type": "string",
                    "description": "Algorithm for signature verification",
                    "enum": ["sha1", "sha256", "md5"],
                    "default": "sha256"
                },
                # Event processing
                "payload": {
                    "type": ["object", "string"],
                    "description": "Webhook payload data"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers from webhook request",
                    "additionalProperties": {"type": "string"}
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method used for the webhook request"
                },
                "query_params": {
                    "type": "object",
                    "description": "Query parameters from webhook request",
                    "additionalProperties": {"type": "string"}
                },
                # Filtering and transformation
                "filters": {
                    "type": "array",
                    "description": "Filters to apply to webhook events",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string", "description": "JSON path to field"},
                            "operator": {"type": "string", "enum": ["equals", "contains", "starts_with", "ends_with", "regex", "exists"]},
                            "value": {"type": ["string", "number", "boolean"], "description": "Value to compare against"}
                        },
                        "required": ["field", "operator"]
                    }
                },
                "transformations": {
                    "type": "array",
                    "description": "Transformations to apply to webhook data",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["extract", "rename", "format", "calculate"]},
                            "source": {"type": "string", "description": "Source field path"},
                            "target": {"type": "string", "description": "Target field name"},
                            "format": {"type": "string", "description": "Format string for transformation"}
                        },
                        "required": ["type", "source"]
                    }
                },
                # Response settings
                "response_status": {
                    "type": "integer",
                    "description": "HTTP status code to return",
                    "default": 200,
                    "minimum": 100,
                    "maximum": 599
                },
                "response_body": {
                    "type": ["object", "string"],
                    "description": "Response body to return"
                },
                "response_headers": {
                    "type": "object",
                    "description": "Response headers to return",
                    "additionalProperties": {"type": "string"}
                },
                # Event storage
                "store_events": {
                    "type": "boolean",
                    "description": "Whether to store received events",
                    "default": True
                },
                "max_stored_events": {
                    "type": "integer",
                    "description": "Maximum number of events to store",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 10000
                },
                "event_retention_days": {
                    "type": "integer",
                    "description": "Number of days to retain events",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 365
                }
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"const": "register"}}},
                    "then": {"required": ["webhook_name", "webhook_url"]}
                },
                {
                    "if": {"properties": {"action": {"const": "receive"}}},
                    "then": {"required": ["webhook_name", "payload"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete"}}},
                    "then": {"required": ["webhook_name"]}
                }
            ]
        }
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute webhook operation with the provided parameters.
        
        Args:
            params: Webhook operation parameters
            context: Execution context
            
        Returns:
            ConnectorResult with operation result or error
        """
        try:
            action = params["action"]
            
            # Route to appropriate action handler
            if action == "register":
                result = await self._register_webhook(params, context)
            elif action == "receive":
                result = await self._receive_webhook(params, context)
            elif action == "list":
                result = await self._list_webhooks(params, context)
            elif action == "delete":
                result = await self._delete_webhook(params, context)
            elif action == "test":
                result = await self._test_webhook(params, context)
            else:
                raise ConnectorException(f"Unsupported webhook action: {action}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "action": action,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Webhook operation failed: {str(e)}",
                metadata={"action": params.get("action", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for webhooks.
        
        Returns:
            AuthRequirements (optional authentication)
        """
        return AuthRequirements(
            type=AuthType.NONE,  # Webhooks can use optional signature verification
            fields={
                "secret": "Secret key for webhook signature verification (optional)",
                "api_key": "API key for webhook authentication (optional)"
            },
            instructions="Webhooks support optional signature verification using a secret key. "
                        "This ensures the webhook payload hasn't been tampered with."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test webhook connection (always returns True as webhooks are passive).
        
        Args:
            auth_tokens: Authentication tokens
            
        Returns:
            True (webhooks don't require active connection testing)
        """
        return True
    
    async def _register_webhook(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """Register a new webhook endpoint."""
        webhook_name = params["webhook_name"]
        webhook_url = params["webhook_url"]
        description = params.get("description", "")
        allowed_methods = params.get("allowed_methods", ["POST"])
        secret = params.get("secret")
        
        # Check if webhook already exists
        if webhook_name in self._webhook_store:
            raise ConnectorException(f"Webhook '{webhook_name}' already exists")
        
        # Create webhook configuration
        webhook_config = {
            "name": webhook_name,
            "url": webhook_url,
            "description": description,
            "allowed_methods": allowed_methods,
            "secret": secret,
            "signature_header": params.get("signature_header", "X-Hub-Signature-256"),
            "signature_algorithm": params.get("signature_algorithm", "sha256"),
            "filters": params.get("filters", []),
            "transformations": params.get("transformations", []),
            "store_events": params.get("store_events", True),
            "max_stored_events": params.get("max_stored_events", 1000),
            "event_retention_days": params.get("event_retention_days", 30),
            "created_at": datetime.utcnow().isoformat(),
            "user_id": context.user_id,
            "events": [],  # Store received events
            "stats": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "last_request": None
            }
        }
        
        # Store webhook configuration
        self._webhook_store[webhook_name] = webhook_config
        
        return {
            "webhook_name": webhook_name,
            "webhook_url": webhook_url,
            "webhook_id": webhook_name,  # Using name as ID for simplicity
            "status": "registered",
            "endpoint": f"/webhooks/{webhook_name}",  # Hypothetical endpoint
            "allowed_methods": allowed_methods,
            "has_secret": bool(secret)
        }
    
    async def _receive_webhook(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """Process a received webhook event."""
        webhook_name = params["webhook_name"]
        payload = params["payload"]
        headers = params.get("headers", {})
        method = params.get("method", "POST")
        query_params = params.get("query_params", {})
        
        # Get webhook configuration
        if webhook_name not in self._webhook_store:
            raise ConnectorException(f"Webhook '{webhook_name}' not found")
        
        webhook_config = self._webhook_store[webhook_name]
        
        # Verify method is allowed
        if method not in webhook_config["allowed_methods"]:
            raise ConnectorException(f"Method {method} not allowed for webhook '{webhook_name}'")
        
        # Verify signature if secret is configured
        if webhook_config["secret"]:
            await self._verify_signature(payload, headers, webhook_config)
        
        # Apply filters
        if webhook_config["filters"]:
            if not await self._apply_filters(payload, webhook_config["filters"]):
                return {
                    "webhook_name": webhook_name,
                    "status": "filtered",
                    "message": "Event filtered out by webhook filters"
                }
        
        # Apply transformations
        processed_payload = await self._apply_transformations(payload, webhook_config["transformations"])
        
        # Create event record
        event = {
            "id": f"{webhook_name}_{datetime.utcnow().timestamp()}",
            "webhook_name": webhook_name,
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "headers": headers,
            "query_params": query_params,
            "original_payload": payload,
            "processed_payload": processed_payload,
            "user_id": context.user_id
        }
        
        # Store event if configured
        if webhook_config["store_events"]:
            await self._store_event(webhook_name, event)
        
        # Update statistics
        webhook_config["stats"]["total_requests"] += 1
        webhook_config["stats"]["successful_requests"] += 1
        webhook_config["stats"]["last_request"] = datetime.utcnow().isoformat()
        
        # Prepare response
        response = {
            "webhook_name": webhook_name,
            "event_id": event["id"],
            "status": "processed",
            "processed_payload": processed_payload,
            "timestamp": event["timestamp"]
        }
        
        # Add custom response if configured
        if params.get("response_body"):
            response["custom_response"] = {
                "status": params.get("response_status", 200),
                "body": params.get("response_body"),
                "headers": params.get("response_headers", {})
            }
        
        return response
    
    async def _list_webhooks(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """List all registered webhooks for the user."""
        user_webhooks = []
        
        for webhook_name, config in self._webhook_store.items():
            if config["user_id"] == context.user_id:
                user_webhooks.append({
                    "name": webhook_name,
                    "url": config["url"],
                    "description": config["description"],
                    "allowed_methods": config["allowed_methods"],
                    "has_secret": bool(config["secret"]),
                    "created_at": config["created_at"],
                    "stats": config["stats"],
                    "event_count": len(config["events"])
                })
        
        return {
            "webhooks": user_webhooks,
            "total_count": len(user_webhooks)
        }
    
    async def _delete_webhook(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """Delete a webhook registration."""
        webhook_name = params["webhook_name"]
        
        if webhook_name not in self._webhook_store:
            raise ConnectorException(f"Webhook '{webhook_name}' not found")
        
        webhook_config = self._webhook_store[webhook_name]
        
        # Verify ownership
        if webhook_config["user_id"] != context.user_id:
            raise ConnectorException(f"Access denied to webhook '{webhook_name}'")
        
        # Delete webhook
        del self._webhook_store[webhook_name]
        
        return {
            "webhook_name": webhook_name,
            "status": "deleted",
            "events_deleted": len(webhook_config["events"])
        }
    
    async def _test_webhook(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """Test a webhook with sample data."""
        webhook_name = params.get("webhook_name")
        
        if not webhook_name:
            # Generate test webhook configuration
            test_payload = {
                "event": "test",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"message": "This is a test webhook event"}
            }
            
            return {
                "status": "test_generated",
                "test_payload": test_payload,
                "instructions": "Use this payload to test your webhook endpoint"
            }
        
        # Test existing webhook
        if webhook_name not in self._webhook_store:
            raise ConnectorException(f"Webhook '{webhook_name}' not found")
        
        webhook_config = self._webhook_store[webhook_name]
        
        # Create test event
        test_params = {
            "action": "receive",
            "webhook_name": webhook_name,
            "payload": {
                "event": "test",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"message": "Test event for webhook validation"}
            },
            "method": "POST",
            "headers": {"Content-Type": "application/json"}
        }
        
        # Process test event
        result = await self._receive_webhook(test_params, context)
        
        return {
            "webhook_name": webhook_name,
            "test_status": "completed",
            "test_result": result
        }
    
    async def _verify_signature(self, payload: Any, headers: Dict[str, str], webhook_config: Dict[str, Any]) -> None:
        """Verify webhook signature."""
        signature_header = webhook_config["signature_header"]
        secret = webhook_config["secret"]
        algorithm = webhook_config["signature_algorithm"]
        
        if signature_header not in headers:
            raise ConnectorException(f"Missing signature header: {signature_header}")
        
        received_signature = headers[signature_header]
        
        # Prepare payload for signature verification
        if isinstance(payload, dict):
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        else:
            payload_bytes = str(payload).encode('utf-8')
        
        # Calculate expected signature
        if algorithm == "sha256":
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            expected_signature = f"sha256={expected_signature}"
        elif algorithm == "sha1":
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha1
            ).hexdigest()
            expected_signature = f"sha1={expected_signature}"
        else:
            raise ConnectorException(f"Unsupported signature algorithm: {algorithm}")
        
        # Compare signatures
        if not hmac.compare_digest(received_signature, expected_signature):
            raise ConnectorException("Invalid webhook signature")
    
    async def _apply_filters(self, payload: Any, filters: List[Dict[str, Any]]) -> bool:
        """Apply filters to webhook payload."""
        for filter_config in filters:
            field = filter_config["field"]
            operator = filter_config["operator"]
            value = filter_config.get("value")
            
            # Extract field value from payload
            field_value = self._extract_field_value(payload, field)
            
            # Apply filter
            if not self._evaluate_filter(field_value, operator, value):
                return False
        
        return True
    
    async def _apply_transformations(self, payload: Any, transformations: List[Dict[str, Any]]) -> Any:
        """Apply transformations to webhook payload."""
        if not transformations:
            return payload
        
        # Start with original payload
        result = payload.copy() if isinstance(payload, dict) else payload
        
        for transform in transformations:
            transform_type = transform["type"]
            source = transform["source"]
            target = transform.get("target", source)
            
            if transform_type == "extract":
                # Extract specific field
                value = self._extract_field_value(payload, source)
                if isinstance(result, dict):
                    result[target] = value
            
            elif transform_type == "rename":
                # Rename field
                if isinstance(result, dict) and source in result:
                    result[target] = result.pop(source)
            
            elif transform_type == "format":
                # Format field value
                value = self._extract_field_value(result, source)
                format_string = transform.get("format", "{}")
                if isinstance(result, dict):
                    result[target] = format_string.format(value)
        
        return result
    
    def _extract_field_value(self, data: Any, field_path: str) -> Any:
        """Extract field value using dot notation path."""
        if not field_path:
            return data
        
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        
        return current
    
    def _evaluate_filter(self, field_value: Any, operator: str, expected_value: Any) -> bool:
        """Evaluate filter condition."""
        if operator == "exists":
            return field_value is not None
        
        if field_value is None:
            return False
        
        if operator == "equals":
            return field_value == expected_value
        elif operator == "contains":
            return str(expected_value) in str(field_value)
        elif operator == "starts_with":
            return str(field_value).startswith(str(expected_value))
        elif operator == "ends_with":
            return str(field_value).endswith(str(expected_value))
        elif operator == "regex":
            import re
            return bool(re.search(str(expected_value), str(field_value)))
        
        return False
    
    async def _store_event(self, webhook_name: str, event: Dict[str, Any]) -> None:
        """Store webhook event."""
        webhook_config = self._webhook_store[webhook_name]
        
        # Add event to storage
        webhook_config["events"].append(event)
        
        # Enforce max events limit
        max_events = webhook_config["max_stored_events"]
        if len(webhook_config["events"]) > max_events:
            webhook_config["events"] = webhook_config["events"][-max_events:]
        
        # Clean up old events based on retention policy
        retention_days = webhook_config["event_retention_days"]
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        webhook_config["events"] = [
            e for e in webhook_config["events"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff_date
        ]
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for webhook operations."""
        return {
            "action": "register",
            "webhook_name": "github_push",
            "webhook_url": "https://api.example.com/webhooks/github",
            "description": "GitHub push event webhook",
            "allowed_methods": ["POST"],
            "secret": "your-webhook-secret-key"
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for webhook connector."""
        return {
            "action": "Operation: register (create webhook), receive (process event), list (show webhooks), delete (remove)",
            "webhook_name": "Unique identifier for the webhook",
            "webhook_url": "URL endpoint where webhook events will be sent",
            "payload": "Event data received from external service",
            "secret": "Secret key for signature verification (recommended for security)",
            "filters": "Conditions to filter which events should be processed",
            "transformations": "Data transformations to apply to incoming events"
        }