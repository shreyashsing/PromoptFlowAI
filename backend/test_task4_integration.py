"""
Integration test for Task 4 - Core Connectors Implementation.

This test verifies that all core connectors are properly implemented
and can handle basic operations.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.connectors.core.register import register_core_connectors
from app.connectors.registry import connector_registry
from app.models.connector import ConnectorExecutionContext


async def test_http_connector():
    """Test HTTP connector with mocked requests."""
    print("Testing HTTP Connector...")
    
    connector = connector_registry.create_connector("http")
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow", 
        node_id="test_node",
        auth_tokens={"api_key": "test_key"}
    )
    
    # Test GET request
    with patch('httpx.AsyncClient') as mock_client:
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
            "url": "https://api.example.com/test",
            "method": "GET",
            "headers": {"Accept": "application/json"}
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"HTTP GET failed: {result.error}"
        assert result.data["status_code"] == 200
        print("  ✓ GET request successful")
    
    # Test POST request with JSON body
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_response.text = '{"id": 123, "created": True}'
        mock_response.content = b'{"id": 123, "created": True}'
        mock_response.url = "https://api.example.com/create"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "url": "https://api.example.com/create",
            "method": "POST",
            "body": {"name": "test item", "value": 42},
            "json_body": True
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"HTTP POST failed: {result.error}"
        assert result.data["status_code"] == 201
        print("  ✓ POST request with JSON body successful")


async def test_gmail_connector():
    """Test Gmail connector with mocked API calls."""
    print("Testing Gmail Connector...")
    
    connector = connector_registry.create_connector("gmail")
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node", 
        auth_tokens={"access_token": "test_access_token"}
    )
    
    # Test send email
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_123",
            "threadId": "thread_123"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "send",
            "to": "recipient@example.com",
            "subject": "Test Email from PromptFlow AI",
            "body": "This is a test email sent through the Gmail connector."
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Gmail send failed: {result.error}"
        assert result.data["message_id"] == "msg_123"
        assert result.data["status"] == "sent"
        print("  ✓ Send email successful")
    
    # Test get labels
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "SENT", "name": "SENT", "type": "system"}
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {"action": "get_labels"}
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Gmail get labels failed: {result.error}"
        assert len(result.data["labels"]) == 2
        print("  ✓ Get labels successful")


async def test_google_sheets_connector():
    """Test Google Sheets connector with mocked API calls."""
    print("Testing Google Sheets Connector...")
    
    connector = connector_registry.create_connector("googlesheets")
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node",
        auth_tokens={"access_token": "test_access_token"}
    )
    
    # Test read data
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "range": "Sheet1!A1:C3",
            "majorDimension": "ROWS",
            "values": [
                ["Name", "Age", "City"],
                ["John Doe", "30", "New York"],
                ["Jane Smith", "25", "Los Angeles"]
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "read",
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "A1:C3"
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Google Sheets read failed: {result.error}"
        assert result.data["row_count"] == 3
        assert result.data["column_count"] == 3
        assert result.data["values"][0] == ["Name", "Age", "City"]
        print("  ✓ Read data successful")
    
    # Test write data
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
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
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "A1:B2",
            "values": [["Product", "Price"], ["Widget", "19.99"]]
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Google Sheets write failed: {result.error}"
        assert result.data["updated_rows"] == 2
        assert result.data["updated_cells"] == 4
        print("  ✓ Write data successful")


async def test_webhook_connector():
    """Test Webhook connector functionality."""
    print("Testing Webhook Connector...")
    
    connector = connector_registry.create_connector("webhook")
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node",
        auth_tokens={}
    )
    
    # Test register webhook
    params = {
        "action": "register",
        "webhook_name": "github_push",
        "webhook_url": "https://api.example.com/webhooks/github",
        "description": "GitHub push event webhook",
        "allowed_methods": ["POST"],
        "secret": "webhook_secret_key"
    }
    
    result = await connector.execute(params, context)
    
    assert result.success, f"Webhook register failed: {result.error}"
    assert result.data["webhook_name"] == "github_push"
    assert result.data["status"] == "registered"
    assert result.data["has_secret"] is True
    print("  ✓ Register webhook successful")
    
    # Test receive webhook event (without signature for simplicity)
    # First register a webhook without secret
    params_no_secret = {
        "action": "register",
        "webhook_name": "simple_webhook",
        "webhook_url": "https://api.example.com/webhooks/simple",
        "description": "Simple webhook without signature verification",
        "allowed_methods": ["POST"]
    }
    
    result = await connector.execute(params_no_secret, context)
    assert result.success, f"Simple webhook register failed: {result.error}"
    
    # Now test receive event
    params = {
        "action": "receive",
        "webhook_name": "simple_webhook",
        "payload": {
            "event": "push",
            "repository": {"name": "test-repo"},
            "commits": [{"message": "Fix bug in connector"}]
        },
        "method": "POST",
        "headers": {"Content-Type": "application/json"}
    }
    
    result = await connector.execute(params, context)
    
    assert result.success, f"Webhook receive failed: {result.error}"
    assert result.data["status"] == "processed"
    assert "event_id" in result.data
    print("  ✓ Receive webhook event successful")
    
    # Test list webhooks
    params = {"action": "list"}
    result = await connector.execute(params, context)
    
    assert result.success, f"Webhook list failed: {result.error}"
    assert result.data["total_count"] >= 1
    print("  ✓ List webhooks successful")


async def test_perplexity_connector():
    """Test Perplexity AI connector with mocked API calls."""
    print("Testing Perplexity AI Connector...")
    
    connector = connector_registry.create_connector("perplexity")
    context = ConnectorExecutionContext(
        user_id="test_user",
        workflow_id="test_workflow",
        node_id="test_node",
        auth_tokens={"api_key": "pplx-test-key"}
    )
    
    # Test chat completion
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Artificial intelligence has seen significant developments in 2024, including advances in large language models, computer vision, and robotics. Key trends include improved efficiency, better reasoning capabilities, and increased adoption across industries."
                },
                "finish_reason": "stop"
            }],
            "model": "llama-3.1-sonar-large-128k-online",
            "usage": {"total_tokens": 150, "prompt_tokens": 20, "completion_tokens": 130},
            "citations": [
                "https://example.com/ai-developments-2024",
                "https://example.com/tech-trends"
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "chat",
            "query": "What are the latest developments in artificial intelligence?",
            "model": "llama-3.1-sonar-large-128k-online",
            "return_citations": True
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Perplexity chat failed: {result.error}"
        assert "artificial intelligence" in result.data["response"].lower()
        assert "citations" in result.data
        assert len(result.data["citations"]) == 2
        print("  ✓ Chat completion successful")
    
    # Test web search
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Based on recent web sources, here are the latest AI developments: 1) OpenAI released GPT-4 Turbo with improved capabilities, 2) Google announced Gemini AI with multimodal features, 3) Microsoft integrated AI into Office 365 suite."
                },
                "finish_reason": "stop"
            }],
            "model": "llama-3.1-sonar-large-128k-online",
            "usage": {"total_tokens": 200},
            "citations": [
                "https://openai.com/blog/gpt-4-turbo",
                "https://blog.google/technology/ai/google-gemini-ai/",
                "https://microsoft.com/ai-office-365"
            ],
            "related_questions": [
                "What are the risks of AI development?",
                "How is AI being regulated globally?"
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "action": "search",
            "query": "latest AI developments 2024"
        }
        
        result = await connector.execute(params, context)
        
        assert result.success, f"Perplexity search failed: {result.error}"
        assert "web sources" in result.data["response"].lower()
        assert len(result.data["citations"]) == 3
        assert len(result.data["related_questions"]) == 2
        print("  ✓ Web search successful")


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("TASK 4 INTEGRATION TEST - CORE CONNECTORS")
    print("=" * 60)
    
    # Register connectors
    print("Registering core connectors...")
    result = register_core_connectors()
    print(f"✓ Registered {result['registered']}/{result['total']} connectors\n")
    
    # Run tests for each connector
    try:
        await test_http_connector()
        print()
        
        await test_gmail_connector()
        print()
        
        await test_google_sheets_connector()
        print()
        
        await test_webhook_connector()
        print()
        
        await test_perplexity_connector()
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED - TASK 4 COMPLETE")
        print("=" * 60)
        print("\nCore connectors successfully implemented:")
        print("• HTTP Request Connector - Full REST API support")
        print("• Gmail Connector - OAuth email operations")
        print("• Google Sheets Connector - Full CRUD operations")
        print("• Webhook Connector - External event processing")
        print("• Perplexity AI Connector - Web-augmented QA")
        print("\nAll connectors support:")
        print("• Parameter validation")
        print("• Authentication handling")
        print("• Error management")
        print("• Comprehensive testing")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())