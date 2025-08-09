#!/usr/bin/env python3
"""
Test to verify the Gmail duplicate email fix.
This test ensures:
1. Gmail connector searches inbox instead of social category
2. Parameter resolution handles missing array indices gracefully
3. No duplicate emails appear in Google Sheets
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.connectors.core.gmail_connector import GmailConnector
from app.models.connector import ConnectorExecutionContext
from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator


async def test_gmail_query_enhancement():
    """Test that Gmail queries are enhanced to prioritize inbox."""
    print("=== Testing Gmail Query Enhancement ===")
    
    gmail_connector = GmailConnector()
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={"access_token": "test_token"}
    )
    
    # Mock multiple inbox emails
    mock_inbox_messages = [
        {"id": "inbox1", "threadId": "thread1"},
        {"id": "inbox2", "threadId": "thread2"},
        {"id": "inbox3", "threadId": "thread3"}
    ]
    
    mock_inbox_response = {
        "messages": mock_inbox_messages,
        "resultSizeEstimate": 3
    }
    
    # Mock detailed message responses
    mock_message_details = []
    for i, msg in enumerate(mock_inbox_messages):
        detail = {
            "id": msg["id"],
            "threadId": msg["threadId"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Inbox Email {i+1}"},
                    {"name": "From", "value": f"sender{i+1}@company.com"},
                    {"name": "Date", "value": f"2024-01-{15+i}T10:00:00Z"},
                    {"name": "To", "value": "user@example.com"}
                ],
                "body": {"data": "VGhpcyBpcyBhbiBlbWFpbA=="}  # Base64 "This is an email"
            },
            "snippet": f"This is inbox email {i+1}",
            "labelIds": ["INBOX", "UNREAD"],
            "sizeEstimate": 1024
        }
        mock_message_details.append(detail)
    
    with patch('httpx.AsyncClient') as mock_client:
        # Mock the list response
        mock_list_response = AsyncMock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = mock_inbox_response
        
        # Mock the detail responses
        mock_detail_responses = []
        for detail in mock_message_details:
            detail_response = AsyncMock()
            detail_response.status_code = 200
            detail_response.json.return_value = detail
            mock_detail_responses.append(detail_response)
        
        mock_client.return_value.__aenter__.return_value.get.side_effect = [
            mock_list_response
        ] + mock_detail_responses
        
        # Test search with unread query (should be enhanced to include inbox)
        params = {
            "action": "search",
            "query": "is:unread",  # This should be enhanced to "is:unread in:inbox"
            "max_results": 3
        }
        
        result = await gmail_connector.execute(params, context)
        
        print(f"Gmail connector success: {result.success}")
        if result.success:
            messages = result.data.get("messages", [])
            print(f"Number of messages returned: {len(messages)}")
            print(f"Enhanced query used: {result.data.get('query', 'N/A')}")
            
            # Verify we got 3 different emails
            subjects = [msg.get('subject', '') for msg in messages]
            print(f"Email subjects: {subjects}")
            
            if len(set(subjects)) == 3:
                print("✅ SUCCESS: Got 3 different emails from inbox")
            else:
                print("❌ FAILED: Still getting duplicate emails")
        else:
            print(f"❌ FAILED: {result.error}")


async def test_parameter_resolution_fix():
    """Test that parameter resolution handles missing array indices gracefully."""
    print("\n=== Testing Parameter Resolution Fix ===")
    
    # Create a mock workflow orchestrator
    orchestrator = UnifiedWorkflowOrchestrator()
    
    # Mock Gmail result with only 1 email (the problematic case)
    gmail_result = {
        "messages": [
            {
                "subject": "Important Email",
                "sender": "boss@company.com",
                "snippet": "This is an important email",
                "date": "2024-01-15T10:00:00Z"
            }
        ]
    }
    
    # Test parameter resolution for indices [0], [1], [2]
    test_cases = [
        ("gmail_connector.result.messages[0].subject", "Important Email"),
        ("gmail_connector.result.messages[0].sender", "boss@company.com"),
        ("gmail_connector.result.messages[0].snippet", "This is an important email"),
        ("gmail_connector.result.messages[1].subject", ""),  # Should return empty string
        ("gmail_connector.result.messages[1].sender", ""),   # Should return empty string
        ("gmail_connector.result.messages[1].snippet", ""),  # Should return empty string
        ("gmail_connector.result.messages[2].subject", ""),  # Should return empty string
        ("gmail_connector.result.messages[2].sender", ""),   # Should return empty string
        ("gmail_connector.result.messages[2].snippet", "")   # Should return empty string
    ]
    
    print("Testing parameter resolution:")
    for field_path, expected in test_cases:
        try:
            # Mock the node data structure
            node_data = {
                "result": gmail_result
            }
            
            # Test the complex field path resolution
            result = await orchestrator._resolve_complex_field_path(
                field_path.replace("gmail_connector.result.", ""),
                node_data,
                {}
            )
            
            print(f"  {field_path}: '{result}' (expected: '{expected}')")
            
            if result == expected:
                print("    ✅ PASS")
            else:
                print(f"    ❌ FAIL - got '{result}', expected '{expected}'")
                
        except Exception as e:
            print(f"  {field_path}: ERROR - {e}")


async def test_google_sheets_integration():
    """Test the complete Gmail to Google Sheets flow."""
    print("\n=== Testing Gmail to Google Sheets Integration ===")
    
    # Simulate the workflow with proper parameter resolution
    gmail_result = {
        "messages": [
            {
                "subject": "Email 1",
                "sender": "sender1@example.com",
                "snippet": "First email content"
            },
            {
                "subject": "Email 2", 
                "sender": "sender2@example.com",
                "snippet": "Second email content"
            }
            # Note: Only 2 emails, but template expects 3
        ]
    }
    
    # Template values that would be sent to Google Sheets
    template_values = [
        "{gmail_connector.result.messages[0].subject}",
        "{gmail_connector.result.messages[0].sender}",
        "{gmail_connector.result.messages[0].snippet}",
        "{gmail_connector.result.messages[1].subject}",
        "{gmail_connector.result.messages[1].sender}",
        "{gmail_connector.result.messages[1].snippet}",
        "{gmail_connector.result.messages[2].subject}",  # This should be empty
        "{gmail_connector.result.messages[2].sender}",   # This should be empty
        "{gmail_connector.result.messages[2].snippet}"   # This should be empty
    ]
    
    orchestrator = UnifiedWorkflowOrchestrator()
    
    # Resolve each template value
    resolved_values = []
    for template in template_values:
        # Extract the field path
        field_path = template.replace("{gmail_connector.result.", "").replace("}", "")
        
        node_data = {"result": gmail_result}
        resolved = await orchestrator._resolve_complex_field_path(field_path, node_data, {})
        resolved_values.append(resolved)
    
    print("Resolved values for Google Sheets:")
    for i, value in enumerate(resolved_values):
        print(f"  [{i}]: '{value}'")
    
    # Check for duplicates
    non_empty_values = [v for v in resolved_values if v != ""]
    unique_values = set(non_empty_values)
    
    if len(non_empty_values) == len(unique_values):
        print("✅ SUCCESS: No duplicate values found")
    else:
        print("❌ FAILED: Duplicate values detected")
        
    # Verify the pattern: first 6 should have values, last 3 should be empty
    expected_pattern = [
        "Email 1", "sender1@example.com", "First email content",
        "Email 2", "sender2@example.com", "Second email content", 
        "", "", ""
    ]
    
    if resolved_values == expected_pattern:
        print("✅ SUCCESS: Values match expected pattern")
    else:
        print("❌ FAILED: Values don't match expected pattern")
        print(f"Expected: {expected_pattern}")
        print(f"Got:      {resolved_values}")


if __name__ == "__main__":
    asyncio.run(test_gmail_query_enhancement())
    asyncio.run(test_parameter_resolution_fix())
    asyncio.run(test_google_sheets_integration())