#!/usr/bin/env python3
"""
Test to reproduce and fix the Gmail duplicate email issue.
The issue: Gmail connector returns only 1 email but parameter resolution
tries to access indices [0], [1], [2], resulting in the same email being
repeated 3 times in Google Sheets.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.connectors.core.gmail_connector import GmailConnector
from app.models.connector import ConnectorExecutionContext
from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator


async def test_gmail_duplicate_issue():
    """Test the Gmail duplicate email issue."""
    print("=== Testing Gmail Duplicate Email Issue ===")
    
    # Mock Gmail API response with only 1 email
    mock_gmail_response = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"}
        ]
    }
    
    # Mock detailed message response
    mock_message_detail = {
        "id": "msg1",
        "threadId": "thread1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Social Media Update"},
                {"name": "From", "value": "social@example.com"},
                {"name": "Date", "value": "2024-01-15T10:00:00Z"},
                {"name": "To", "value": "user@example.com"}
            ],
            "body": {"data": "VGhpcyBpcyBhIHNvY2lhbCBtZWRpYSB1cGRhdGU="}  # Base64 encoded
        },
        "snippet": "This is a social media update",
        "labelIds": ["CATEGORY_SOCIAL", "UNREAD"],
        "sizeEstimate": 1024
    }
    
    # Test Gmail connector execution
    gmail_connector = GmailConnector()
    context = ConnectorExecutionContext(
        user_id="test_user",
        auth_tokens={"access_token": "test_token"}
    )
    
    # Mock the HTTP requests
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_gmail_response
        
        mock_detail_response = AsyncMock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = mock_message_detail
        
        mock_client.return_value.__aenter__.return_value.get.side_effect = [
            mock_response,  # First call for list
            mock_detail_response  # Second call for details
        ]
        
        # Execute Gmail connector with request for 3 unread emails
        params = {
            "action": "search",
            "query": "is:unread in:inbox",  # Should search inbox, not social
            "max_results": 3
        }
        
        result = await gmail_connector.execute(params, context)
        
        print(f"Gmail connector success: {result.success}")
        print(f"Gmail connector data: {json.dumps(result.data, indent=2)}")
        
        # Check if we got the expected structure
        if result.success and result.data:
            messages = result.data.get("messages", [])
            print(f"Number of messages returned: {len(messages)}")
            
            # This is the problem - we only get 1 message but try to access [0], [1], [2]
            if len(messages) == 1:
                print("❌ ISSUE CONFIRMED: Only 1 message returned but workflow expects 3")
                print("This will cause the same message to be repeated 3 times")
                
                # Show what happens when we try to access indices
                for i in range(3):
                    try:
                        msg = messages[i] if i < len(messages) else messages[0]  # This is the bug
                        print(f"Index [{i}]: {msg.get('subject', 'No subject')}")
                    except IndexError:
                        print(f"Index [{i}]: IndexError - would use fallback")


async def test_gmail_query_issue():
    """Test if the Gmail query is causing the social category issue."""
    print("\n=== Testing Gmail Query Issue ===")
    
    gmail_connector = GmailConnector()
    
    # Test different query variations
    queries = [
        "is:unread",  # All unread (might include social)
        "is:unread in:inbox",  # Only inbox unread
        "is:unread -in:social",  # Exclude social category
        "is:unread in:primary"  # Only primary category
    ]
    
    for query in queries:
        print(f"\nTesting query: '{query}'")
        
        # Mock response for each query
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate different responses based on query
            if "social" in query or query == "is:unread":
                # Social category response
                mock_response_data = {
                    "messages": [{"id": "social1", "threadId": "thread1"}],
                    "resultSizeEstimate": 1
                }
                category = "SOCIAL"
            else:
                # Inbox/primary response with multiple emails
                mock_response_data = {
                    "messages": [
                        {"id": "inbox1", "threadId": "thread1"},
                        {"id": "inbox2", "threadId": "thread2"},
                        {"id": "inbox3", "threadId": "thread3"}
                    ],
                    "resultSizeEstimate": 3
                }
                category = "INBOX"
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            # Mock message details
            mock_detail_responses = []
            for i, msg in enumerate(mock_response_data["messages"]):
                detail_response = AsyncMock()
                detail_response.status_code = 200
                detail_response.json.return_value = {
                    "id": msg["id"],
                    "threadId": msg["threadId"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": f"{category} Email {i+1}"},
                            {"name": "From", "value": f"sender{i+1}@example.com"},
                            {"name": "Date", "value": "2024-01-15T10:00:00Z"}
                        ]
                    },
                    "snippet": f"This is {category.lower()} email {i+1}",
                    "labelIds": [f"CATEGORY_{category}", "UNREAD"]
                }
                mock_detail_responses.append(detail_response)
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                mock_response
            ] + mock_detail_responses
            
            # Test the query
            context = ConnectorExecutionContext(
                user_id="test_user",
                auth_tokens={"access_token": "test_token"}
            )
            
            params = {
                "action": "search",
                "query": query,
                "max_results": 3
            }
            
            result = await gmail_connector.execute(params, context)
            
            if result.success:
                messages = result.data.get("messages", [])
                print(f"  Results: {len(messages)} messages")
                for i, msg in enumerate(messages):
                    print(f"    [{i}] {msg.get('subject', 'No subject')}")
            else:
                print(f"  Error: {result.error}")


async def test_parameter_resolution_fix():
    """Test the parameter resolution with proper array handling."""
    print("\n=== Testing Parameter Resolution Fix ===")
    
    # Mock Gmail result with only 1 message
    gmail_result = {
        "messages": [
            {
                "subject": "Social Media Update",
                "from": "social@example.com", 
                "snippet": "This is a social media update",
                "date": "2024-01-15T10:00:00Z"
            }
        ]
    }
    
    # Test current parameter resolution (broken)
    template_values = [
        "{gmail_connector.result[0].subject}",
        "{gmail_connector.result[0].from}",
        "{gmail_connector.result[0].snippet}",
        "{gmail_connector.result[1].subject}",  # This will fail or repeat
        "{gmail_connector.result[1].from}",
        "{gmail_connector.result[1].snippet}",
        "{gmail_connector.result[2].subject}",  # This will fail or repeat
        "{gmail_connector.result[2].from}",
        "{gmail_connector.result[2].snippet}"
    ]
    
    print("Current template values:")
    for i, template in enumerate(template_values):
        print(f"  {i}: {template}")
    
    # Simulate what happens with current resolution
    print("\nCurrent resolution result (broken):")
    messages = gmail_result["messages"]
    for i, template in enumerate(template_values):
        try:
            # Extract index from template like [1] or [2]
            import re
            match = re.search(r'\[(\d+)\]', template)
            if match:
                index = int(match.group(1))
                field = template.split('.')[-1].rstrip('}')
                
                # Current broken logic - always use index 0 if out of bounds
                if index < len(messages):
                    value = messages[index].get(field, "")
                else:
                    value = messages[0].get(field, "")  # This causes duplication
                
                print(f"  {i}: {value}")
        except Exception as e:
            print(f"  {i}: Error - {e}")


if __name__ == "__main__":
    asyncio.run(test_gmail_duplicate_issue())
    asyncio.run(test_gmail_query_issue())
    asyncio.run(test_parameter_resolution_fix())