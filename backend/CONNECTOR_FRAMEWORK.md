# Connector Framework Documentation

## Overview

The PromptFlow AI Connector Framework provides a standardized way to create, register, and execute integrations with external services and APIs. The framework ensures consistency, type safety, and proper error handling across all connectors.

## Architecture

### Core Components

1. **BaseConnector** - Abstract base class defining the standard interface
2. **ConnectorRegistry** - Registration and discovery system for connectors
3. **ConnectorResultHandler** - Result processing and error management
4. **OAuthHelper** - OAuth 2.0 authentication utilities

### Key Features

- **Type Safety**: Pydantic models for all data structures
- **Parameter Validation**: JSON schema validation for connector inputs
- **Error Handling**: Comprehensive error management with retry logic
- **Authentication**: Support for multiple auth types (API key, OAuth2, Basic)
- **Result Processing**: Standardized result handling and transformation
- **Metadata Management**: Rich metadata for RAG-based connector discovery

## Creating a New Connector

### Step 1: Inherit from BaseConnector

```python
from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType

class MyConnector(BaseConnector):
    def _get_category(self) -> str:
        return "data_sources"  # or "communication", "ai_services", etc.
    
    def _define_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of parameter"
                }
            },
            "required": ["param1"]
        }
    
    async def execute(self, params: dict, context: ConnectorExecutionContext) -> ConnectorResult:
        # Implement your connector logic here
        return ConnectorResult(
            success=True,
            data={"result": "success"},
            metadata={"connector": self.name}
        )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        return AuthRequirements(
            type=AuthType.API_KEY,
            fields={"api_key": "Your API key"},
            instructions="Get your API key from the service dashboard"
        )
```

### Step 2: Register the Connector

```python
from app.connectors.registry import connector_registry

# Register your connector
connector_registry.register(MyConnector)
```

### Step 3: Use the Connector

```python
# Create execution context
context = ConnectorExecutionContext(
    user_id="user123",
    workflow_id="workflow456",
    node_id="node789",
    auth_tokens={"api_key": "your_api_key"}
)

# Get connector instance
connector = connector_registry.create_connector("my")

# Execute with parameters
result = await connector.execute({"param1": "value"}, context)
```

## Authentication Types

### No Authentication
```python
AuthRequirements(type=AuthType.NONE)
```

### API Key Authentication
```python
AuthRequirements(
    type=AuthType.API_KEY,
    fields={"api_key": "Your API key"},
    instructions="Get your API key from the service dashboard"
)
```

### OAuth 2.0 Authentication
```python
AuthRequirements(
    type=AuthType.OAUTH2,
    fields={"client_id": "OAuth client ID", "client_secret": "OAuth client secret"},
    oauth_scopes=["read", "write"],
    instructions="Configure OAuth app in the service settings"
)
```

### Basic Authentication
```python
AuthRequirements(
    type=AuthType.BASIC,
    fields={"username": "Username", "password": "Password"},
    instructions="Use your service account credentials"
)
```

## Error Handling

### Built-in Retry Logic

The framework provides automatic retry with exponential backoff:

```python
result = await connector.execute_with_retry(
    params={"param1": "value"},
    context=context,
    max_retries=3,
    retry_delay=1.0
)
```

### Custom Error Handling

```python
from app.core.exceptions import ConnectorException, ValidationException

async def execute(self, params: dict, context: ConnectorExecutionContext) -> ConnectorResult:
    try:
        # Your connector logic
        return ConnectorResult(success=True, data=result_data)
    except ValidationException as e:
        # Don't retry validation errors
        raise e
    except Exception as e:
        # Will be retried automatically
        raise ConnectorException(f"Service error: {str(e)}")
```

## Result Processing

### Creating Results

```python
from app.connectors.result_handler import result_handler

# Success result
success = result_handler.create_success_result(
    data={"key": "value"},
    message="Operation completed successfully"
)

# Error result
error = result_handler.create_error_result(
    error="Something went wrong",
    severity=ResultSeverity.HIGH
)

# Warning result (success with warnings)
warning = result_handler.create_warning_result(
    data={"key": "value"},
    warning="Operation completed with warnings"
)

# Partial result (some data despite errors)
partial = result_handler.create_partial_result(
    data={"partial": "data"},
    error="Could not retrieve all data"
)
```

### Merging Results

```python
# Merge multiple connector results
results = [result1, result2, result3]
merged = result_handler.merge_results(results)
```

### Transforming Results

```python
# Transform result data
transformed = result_handler.transform_result_data(
    result, 
    lambda data: {"transformed": data}
)
```

## OAuth Integration

### Setting up OAuth

```python
from app.core.oauth import oauth_manager, OAuthConfig

# Configure OAuth for a service
config = OAuthConfig(
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_url="https://service.com/oauth/authorize",
    token_url="https://service.com/oauth/token",
    scopes=["read", "write"],
    redirect_uri="http://localhost:8000/auth/callback"
)

oauth_manager.register_oauth_config("my_service", config)
```

### Using OAuth in Connectors

```python
async def execute(self, params: dict, context: ConnectorExecutionContext) -> ConnectorResult:
    # OAuth tokens are automatically available in context.auth_tokens
    access_token = context.auth_tokens.get("access_token")
    
    # Use the token in your API calls
    headers = {"Authorization": f"Bearer {access_token}"}
    # ... make API request
```

## Best Practices

### 1. Parameter Validation
- Always define comprehensive JSON schemas
- Include helpful descriptions for all parameters
- Use appropriate data types and constraints

### 2. Error Handling
- Use specific exception types for different error categories
- Provide clear, actionable error messages
- Don't retry authentication or validation errors

### 3. Authentication
- Support multiple authentication methods when possible
- Provide clear instructions for obtaining credentials
- Test authentication in the `test_connection` method

### 4. Result Processing
- Always return structured data in results
- Include relevant metadata for debugging and monitoring
- Use appropriate result types (success, error, warning, partial)

### 5. Documentation
- Provide example parameters and usage hints
- Document any special requirements or limitations
- Include troubleshooting information

## Testing Connectors

### Unit Testing

```python
import pytest
from app.models.connector import ConnectorExecutionContext

@pytest.mark.asyncio
async def test_my_connector():
    connector = MyConnector()
    
    # Test parameter validation
    valid_params = {"param1": "test_value"}
    assert await connector.validate_params(valid_params)
    
    # Test execution
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow", 
        node_id="test_node"
    )
    
    result = await connector.execute(valid_params, context)
    assert result.success
    assert "result" in result.data
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_connector_with_registry():
    from app.connectors.registry import ConnectorRegistry
    
    registry = ConnectorRegistry()
    registry.register(MyConnector)
    
    connector = registry.create_connector("my")
    # ... test connector functionality
```

## Connector Categories

- **data_sources**: HTTP requests, databases, file systems
- **communication**: Email, Slack, SMS, webhooks
- **ai_services**: OpenAI, summarization, text processing
- **logic**: Conditional branches, data transformation
- **control**: Error handling, workflow control

## Framework Extension Points

### Custom Result Handlers

```python
class CustomResultHandler(ConnectorResultHandler):
    def create_custom_result(self, data, custom_field):
        return ConnectorResult(
            success=True,
            data=data,
            metadata={"custom_field": custom_field}
        )
```

### Custom Authentication

```python
class CustomAuthConnector(BaseConnector):
    async def validate_auth(self, auth_tokens: dict) -> bool:
        # Custom authentication logic
        return await self.custom_auth_check(auth_tokens)
```

This framework provides a solid foundation for building reliable, maintainable connectors that integrate seamlessly with the PromptFlow AI platform.