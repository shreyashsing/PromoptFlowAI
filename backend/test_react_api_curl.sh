#!/bin/bash

# Test script for ReAct Agent API endpoints
# Make sure the server is running: uvicorn app.main:app --reload

BASE_URL="http://localhost:8000/api/v1/agent"

echo "Testing ReAct Agent API Endpoints..."
echo "===================================="

# Test 1: Get ReAct agent status
echo -e "\n1. Testing ReAct Agent Status:"
echo "GET $BASE_URL/react-status"
curl -X GET "$BASE_URL/react-status" \
  -H "Content-Type: application/json" \
  -w "\nStatus Code: %{http_code}\n" \
  2>/dev/null | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

# Test 2: Test ReAct chat endpoint
echo -e "\n2. Testing ReAct Chat Endpoint:"
echo "POST $BASE_URL/react-chat"
curl -X POST "$BASE_URL/react-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me understand what tools you have available?",
    "session_id": "test-session-curl-123"
  }' \
  -w "\nStatus Code: %{http_code}\n" \
  2>/dev/null | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

# Test 3: Test conversation history
echo -e "\n3. Testing Conversation History:"
echo "GET $BASE_URL/react-conversations/test-session-curl-123"
curl -X GET "$BASE_URL/react-conversations/test-session-curl-123" \
  -H "Content-Type: application/json" \
  -w "\nStatus Code: %{http_code}\n" \
  2>/dev/null | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

echo -e "\n===================================="
echo "Test completed!"
echo -e "\nTo run these tests:"
echo "1. Make sure the server is running: uvicorn app.main:app --reload"
echo "2. Run this script: bash test_react_api_curl.sh"
echo "3. Or visit the interactive docs: http://localhost:8000/docs"