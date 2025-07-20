"""
Comprehensive tests for core connectors.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json
import base64
from datetime import datetime

from app.connectors.core import (
    HttpConnector, 
    GmailConnector, 
    GoogleSheetsConnector, 
    WebhookConnector, 
    PerplexityConnector
)
from app.models.connector import ConnectorExecutionContext
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class TestHttpConnector:
    """Test cases for HTTP Connector."""
    
    @pytest.fixture
    def http_connector(self):
        return HttpConnector()
    
    @pytest.fixture
    def execution_context(self):
        return ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node",
            auth_tokens={"api_key": "test_key"}
        )
    
    def test_connector_properties(self, http_connector):
        """Test basic connector properties."""
        assert http_connector.name == "http"
        assert http_connector.category == "data_sources"
        assert "url" in http_connector.schema["properties"]
        assert "method" in http_connector.schema["properties"]
    
    async def test_parameter_validation(self, http_connector):
        """Test parameter validation."""
        # Valid parameters
        valid_params = {"url": "https://api.example.com"}
        assert await http_connector.validate_params(valid_params)
        
        # Missing required parameter
        with pytest.raises(ValidationException):
            await http_connector.validate_params({})
    
    async def test_auth_requirements(self, http_connector):
        """Test authentication requirements."""
        auth_req = await http_connector.get_auth_requirements()
        assert auth_req.type.value == "none"
        assert "api_key" in auth_req.fields
    
    @patch('httpx.AsyncClient')
    async def test_successful_get_request(self, mock_client, http_connector, execution_context):
        """Test successful GET request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"message": "success"}
        mock_response.text = '{"message": "success"}'
        mock_response.content = b'{"message": "success"}'
        mock_response.url = "https://api.example.com"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "url": "https://api.example.com",
            "method": "GET"
        }
        
        result = await http_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["status_code"] == 200
        assert result.data["body"]["message"] == "success"
    
    @patch('httpx.AsyncClient')
    async def test_post_request_with_json_body(self, mock_client, http_connector, execution_context):
        """Test POST request with JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"id": 123}
        mock_response.text = '{"id": 123}'
        mock_response.content = b'{"id": 123}'
        mock_response.url = "https://api.example.com"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "url": "https://api.example.com/create",
            "method": "POST",
            "body": {"name": "test", "value": 42},
            "json_body": True
        }
        
        result = await http_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["status_code"] == 201
        
        # Verify the request was made with JSON content
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args[1]["content"] == '{"name":"test","value":42}'
    
    async def test_invalid_url(self, http_connector, execution_context):
        """Test handling of invalid URL."""
        params = {"url": "not-a-valid-url"}
        
        result = await http_connector.execute(params, execution_context)
        
        assert not result.success
        assert "Invalid URL format" in result.error
    
    def test_example_params(self, http_connector):
        """Test example parameters."""
        examples = http_connector.get_example_params()
        assert "url" in examples
        assert "method" in examples
        assert examples["method"] == "GET"
    
    def test_parameter_hints(self, http_connector):
        """Test parameter hints."""
        hints = http_connector.get_parameter_hints()
        assert "url" in hints
        assert "method" in hints
        assert "timeout" in hints


class TestGmailConnector:
    """Test cases for Gmail Connector."""
    
    @pytest.fixture
    def gmail_connector(self):
        return GmailConnector()
    
    @pytest.fixture
    def execution_context(self):
        return ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow", 
            node_id="test_node",
            auth_tokens={"access_token": "test_access_token"}
        )
    
    def test_connector_properties(self, gmail_connector):
        """Test basic connector properties."""
        assert gmail_connector.name == "gmail"
        assert gmail_connector.category == "communication"
        assert "action" in gmail_connector.schema["properties"]
    
    async def test_auth_requirements(self, gmail_connector):
        """Test OAuth authentication requirements."""
        auth_req = await gmail_connector.get_auth_requirements()
        assert auth_req.type.value == "oauth"
        assert "access_token" in auth_req.fields
        assert len(auth_req.oauth_scopes) > 0
    
    @patch('httpx.AsyncClient')
    async def test_send_email(self, mock_client, gmail_connector, execution_context):
        """Test sending email."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg123",
            "threadId": "thread123"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "send",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "body": "This is a test email."
        }
        
        result = await gmail_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["message_id"] == "msg123"
        assert result.data["status"] == "sent"
    
    @patch('httpx.AsyncClient')
    async def test_read_email(self, mock_client, gmail_connector, execution_context):
        """Test reading email."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg123",
            "threadId": "thread123",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"}
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Test message body").decode()}
            },
            "snippet": "Test message body"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "read",
            "message_id": "msg123"
        }
        
        result = await gmail_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["id"] == "msg123"
        assert result.data["subject"] == "Test Subject"
        assert result.data["from"] == "sender@example.com"
    
    async def test_missing_access_token(self, gmail_connector):
        """Test handling missing access token."""
        context = ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node",
            auth_tokens={}
        )
        
        params = {"action": "send", "to": "test@example.com", "subject": "Test"}
        
        result = await gmail_connector.execute(params, context)
        
        assert not result.success
        assert "access token not found" in result.error.lower()


class TestGoogleSheetsConnector:
    """Test cases for Google Sheets Connector."""
    
    @pytest.fixture
    def sheets_connector(self):
        return GoogleSheetsConnector()
    
    @pytest.fixture
    def execution_context(self):
        return ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node", 
            auth_tokens={"access_token": "test_access_token"}
        )
    
    def test_connector_properties(self, sheets_connector):
        """Test basic connector properties."""
        assert sheets_connector.name == "googlesheets"
        assert sheets_connector.category == "data_sources"
        assert "action" in sheets_connector.schema["properties"]
        assert "spreadsheet_id" in sheets_connector.schema["properties"]
    
    async def test_auth_requirements(self, sheets_connector):
        """Test OAuth authentication requirements."""
        auth_req = await sheets_connector.get_auth_requirements()
        assert auth_req.type.value == "oauth"
        assert "access_token" in auth_req.fields
        assert "spreadsheets" in str(auth_req.oauth_scopes)
    
    @patch('httpx.AsyncClient')
    async def test_read_data(self, mock_client, sheets_connector, execution_context):
        """Test reading data from Google Sheets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "range": "Sheet1!A1:C3",
            "majorDimension": "ROWS",
            "values": [
                ["Name", "Age", "City"],
                ["John", "30", "New York"],
                ["Jane", "25", "Los Angeles"]
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "read",
            "spreadsheet_id": "test_sheet_id",
            "range": "A1:C3"
        }
        
        result = await sheets_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["row_count"] == 3
        assert result.data["column_count"] == 3
        assert result.data["values"][0] == ["Name", "Age", "City"]
    
    @patch('httpx.AsyncClient')
    async def test_write_data(self, mock_client, sheets_connector, execution_context):
        """Test writing data to Google Sheets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "spreadsheetId": "test_sheet_id",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.put.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "write",
            "spreadsheet_id": "test_sheet_id",
            "range": "A1:B2",
            "values": [["Name", "Age"], ["John", "30"]]
        }
        
        result = await sheets_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["updated_rows"] == 2
        assert result.data["updated_cells"] == 4


class TestWebhookConnector:
    """Test cases for Webhook Connector."""
    
    @pytest.fixture
    def webhook_connector(self):
        return WebhookConnector()
    
    @pytest.fixture
    def execution_context(self):
        return ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node",
            auth_tokens={}
        )
    
    def test_connector_properties(self, webhook_connector):
        """Test basic connector properties."""
        assert webhook_connector.name == "webhook"
        assert webhook_connector.category == "triggers"
        assert "action" in webhook_connector.schema["properties"]
    
    async def test_auth_requirements(self, webhook_connector):
        """Test authentication requirements."""
        auth_req = await webhook_connector.get_auth_requirements()
        assert auth_req.type.value == "none"
        assert "secret" in auth_req.fields
    
    async def test_register_webhook(self, webhook_connector, execution_context):
        """Test webhook registration."""
        params = {
            "action": "register",
            "webhook_name": "test_webhook",
            "webhook_url": "https://api.example.com/webhook",
            "description": "Test webhook",
            "secret": "test_secret"
        }
        
        result = await webhook_connector.execute(params, execution_context)
        
        assert result.success
        assert result.data["webhook_name"] == "test_webhook"
        assert result.data["status"] == "registered"
        assert result.data["has_secret"] is True
    
    async def test_receive_webhook(self, webhook_connector, execution_context):
        """Test webhook event processing."""
        # First register a webhook
        register_params = {
            "action": "register",
            "webhook_name": "test_webhook",
            "webhook_url": "https://api.example.com/webhook"
        }
        await webhook_connector.execute(register_params, execution_context)
        
        # Then receive an event
        receive_params = {
            "action": "receive",
            "webhook_name": "test_webhook",
            "payload": {"event": "test", "data": {"message": "Hello"}},
            "method": "POST",
            "headers": {"Content-Type": "application/json"}
        }
        
        result = await webhook_connector.execute(receive_params, execution_context)
        
        assert result.success
        assert result.data["status"] == "processed"
        assert "event_id" in result.data
    
    async def test_list_webhooks(self, webhook_connector, execution_context):
        """Test listing webhooks."""
        # Register a webhook first
        register_params = {
            "action": "register",
            "webhook_name": "test_webhook",
            "webhook_url": "https://api.example.com/webhook"
        }
        await webhook_connector.execute(register_params, execution_context)
        
        # List webhooks
        list_params = {"action": "list"}
        result = await webhook_connector.execute(list_params, execution_context)
        
        assert result.success
        assert result.data["total_count"] == 1
        assert result.data["webhooks"][0]["name"] == "test_webhook"
    
    async def test_webhook_filters(self, webhook_connector, execution_context):
        """Test webhook event filtering."""
        # Register webhook with filters
        register_params = {
            "action": "register",
            "webhook_name": "filtered_webhook",
            "webhook_url": "https://api.example.com/webhook",
            "filters": [
                {"field": "event", "operator": "equals", "value": "important"}
            ]
        }
        await webhook_connector.execute(register_params, execution_context)
        
        # Send event that should be filtered out
        receive_params = {
            "action": "receive",
            "webhook_name": "filtered_webhook",
            "payload": {"event": "unimportant", "data": {"message": "Hello"}},
            "method": "POST"
        }
        
        result = await webhook_connector.execute(receive_params, execution_context)
        
        assert result.success
        assert result.data["status"] == "filtered"


class TestPerplexityConnector:
    """Test cases for Perplexity AI Connector."""
    
    @pytest.fixture
    def perplexity_connector(self):
        return PerplexityConnector()
    
    @pytest.fixture
    def execution_context(self):
        return ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node",
            auth_tokens={"api_key": "pplx-test-key"}
        )
    
    def test_connector_properties(self, perplexity_connector):
        """Test basic connector properties."""
        assert perplexity_connector.name == "perplexity"
        assert perplexity_connector.category == "ai_services"
        assert "action" in perplexity_connector.schema["properties"]
        assert "query" in perplexity_connector.schema["properties"]
    
    async def test_auth_requirements(self, perplexity_connector):
        """Test API key authentication requirements."""
        auth_req = await perplexity_connector.get_auth_requirements()
        assert auth_req.type.value == "api_key"
        assert "api_key" in auth_req.fields
    
    @patch('httpx.AsyncClient')
    async def test_chat_completion(self, mock_client, perplexity_connector, execution_context):
        """Test chat completion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Artificial intelligence is rapidly evolving..."
                },
                "finish_reason": "stop"
            }],
            "model": "llama-3.1-sonar-large-128k-online",
            "usage": {"total_tokens": 150},
            "citations": ["https://example.com/ai-news"]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "chat",
            "query": "What are the latest developments in AI?",
            "return_citations": True
        }
        
        result = await perplexity_connector.execute(params, execution_context)
        
        assert result.success
        assert "Artificial intelligence" in result.data["response"]
        assert "citations" in result.data
        assert result.data["model"] == "llama-3.1-sonar-large-128k-online"
    
    @patch('httpx.AsyncClient')
    async def test_web_search(self, mock_client, perplexity_connector, execution_context):
        """Test web search functionality."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Based on recent web sources, here's what I found about AI..."
                },
                "finish_reason": "stop"
            }],
            "model": "llama-3.1-sonar-large-128k-online",
            "usage": {"total_tokens": 200},
            "citations": ["https://example.com/ai-news", "https://example.com/tech-blog"],
            "related_questions": ["What are the risks of AI?", "How is AI being regulated?"]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_client_instance
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "search",
            "query": "latest AI developments 2024"
        }
        
        result = await perplexity_connector.execute(params, execution_context)
        
        assert result.success
        assert "web sources" in result.data["response"]
        assert len(result.data["citations"]) == 2
        assert len(result.data["related_questions"]) == 2
    
    async def test_missing_api_key(self, perplexity_connector):
        """Test handling missing API key."""
        context = ConnectorExecutionContext(
            user_id="test_user",
            workflow_id="test_workflow",
            node_id="test_node",
            auth_tokens={}
        )
        
        params = {"action": "chat", "query": "Test query"}
        
        result = await perplexity_connector.execute(params, context)
        
        assert not result.success
        assert "api key not found" in result.error.lower()
    
    def test_example_params(self, perplexity_connector):
        """Test example parameters."""
        examples = perplexity_connector.get_example_params()
        assert "action" in examples
        assert "query" in examples
        assert examples["action"] == "chat"
    
    def test_parameter_hints(self, perplexity_connector):
        """Test parameter hints."""
        hints = perplexity_connector.get_parameter_hints()
        assert "action" in hints
        assert "query" in hints
        assert "model" in hints


# Integration tests
class TestConnectorIntegration:
    """Integration tests for connector interactions."""
    
    async def test_connector_registry_integration(self):
        """Test that all connectors can be registered and instantiated."""
        from app.connectors.registry import connector_registry
        
        # Register all core connectors
        connector_registry.register(HttpConnector)
        connector_registry.register(GmailConnector)
        connector_registry.register(GoogleSheetsConnector)
        connector_registry.register(WebhookConnector)
        connector_registry.register(PerplexityConnector)
        
        # Verify all connectors are registered
        connectors = connector_registry.list_connectors()
        assert "http" in connectors
        assert "gmail" in connectors
        assert "googlesheets" in connectors
        assert "webhook" in connectors
        assert "perplexity" in connectors
        
        # Test instantiation
        for connector_name in connectors:
            connector = connector_registry.create_connector(connector_name)
            assert connector is not None
            assert connector.name == connector_name
    
    async def test_connector_metadata_generation(self):
        """Test that connector metadata is properly generated."""
        from app.connectors.registry import connector_registry
        
        connector_registry.register(HttpConnector)
        metadata = connector_registry.get_metadata("http")
        
        assert metadata.name == "http"
        assert metadata.category == "data_sources"
        assert metadata.parameter_schema is not None
        assert "url" in metadata.parameter_schema["properties"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])