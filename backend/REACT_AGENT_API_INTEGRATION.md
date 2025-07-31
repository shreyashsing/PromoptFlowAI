# ReAct Agent API Integration

## Overview

The new ReAct agent has been successfully integrated with the existing API at `http://localhost:8000/api/v1/agent`. The integration provides both backward compatibility with the existing agent system and new endpoints specifically for the ReAct agent capabilities.

## New API Endpoints

### 1. ReAct Chat Endpoint
**POST** `/api/v1/agent/react-chat`

Process messages using the new ReAct agent with reasoning capabilities.

**Request:**
```json
{
  "message": "Hello, can you help me understand what tools you have available?",
  "session_id": "your-session-id"
}
```

**Response:**
```json
{
  "response": "Agent's response message",
  "session_id": "your-session-id",
  "reasoning_trace": [
    {
      "step_number": 1,
      "step_type": "thought",
      "content": "I need to check what tools are available...",
      "timestamp": "2025-01-27T..."
    }
  ],
  "tool_calls": [
    {
      "id": "call_1",
      "tool_name": "http_request",
      "parameters": {...},
      "status": "completed"
    }
  ],
  "status": "completed",
  "processing_time_ms": 1500,
  "iterations_used": 3,
  "metadata": {...}
}
```

### 2. ReAct Streaming Chat Endpoint
**POST** `/api/v1/agent/react-chat-stream`

Stream the ReAct agent's reasoning process in real-time.

**Request:** Same as above

**Response:** Server-Sent Events stream with chunks like:
```
data: {"type": "content", "content": "I'm thinking about...", "session_id": "..."}
data: {"type": "tool_call", "tool_call": {...}, "session_id": "..."}
data: {"type": "complete", "session_id": "...", "tool_calls": [...]}
```

### 3. ReAct Agent Status
**GET** `/api/v1/agent/react-status`

Get the health status and capabilities of the ReAct agent.

**Response:**
```json
{
  "health": {
    "status": "healthy",
    "initialized": true,
    "tools_available": 6,
    "llm_configured": true,
    "agent_ready": true
  },
  "tools": [
    {
      "name": "http_request",
      "description": "Make HTTP requests...",
      "parameters": {...}
    }
  ],
  "capabilities": {
    "reasoning": true,
    "tool_usage": true,
    "conversation_memory": true,
    "streaming": true
  }
}
```

### 4. ReAct Conversation History
**GET** `/api/v1/agent/react-conversations/{session_id}`

Get detailed conversation history with reasoning traces.

## Key Features

### 1. **Intelligent Reasoning**
- Step-by-step reasoning process using ReAct methodology
- Detailed reasoning traces showing the agent's thought process
- Iterative problem-solving with tool usage

### 2. **Tool Integration**
- Automatic discovery of existing connectors as tools
- Support for HTTP requests, Gmail, Google Sheets, Webhooks, etc.
- Real-time tool execution with status tracking

### 3. **Conversation Memory**
- Persistent conversation sessions across requests
- Context-aware responses based on conversation history
- Separate database tables for ReAct conversations

### 4. **Streaming Support**
- Real-time streaming of agent responses
- Live updates of reasoning steps and tool calls
- Better user experience for long-running requests

### 5. **Fallback Handling**
- Graceful degradation when Azure OpenAI is not configured
- Informative error messages and status reporting
- Backward compatibility with existing agent system

## Database Schema

The integration includes new database tables:
- `react_conversations` - Main conversation sessions
- `react_conversation_messages` - Individual messages
- `react_tool_executions` - Tool execution tracking
- `react_reasoning_traces` - Detailed reasoning steps

## Configuration Requirements

### Required Environment Variables:
```env
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Optional Dependencies:
- `langchain-openai` - For Azure OpenAI integration
- `langgraph` - For ReAct agent functionality

## Testing

### 1. **Python Test Script**
```bash
python test_react_api_simple.py
```

### 2. **Curl Test Script**
```bash
bash test_react_api_curl.sh
```

### 3. **Interactive API Documentation**
Visit: `http://localhost:8000/docs`

### 4. **Manual Testing**
```bash
# Start the server
uvicorn app.main:app --reload

# Test the endpoint
curl -X POST "http://localhost:8000/api/v1/agent/react-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What tools do you have available?",
    "session_id": "test-123"
  }'
```

## Error Handling

The integration includes comprehensive error handling:
- **Configuration Errors**: Graceful fallback when Azure OpenAI is not configured
- **Tool Errors**: Individual tool failures don't crash the entire request
- **Network Errors**: Proper timeout and retry mechanisms
- **Authentication Errors**: Clear error messages for auth issues

## Backward Compatibility

The existing `/chat-agent` endpoint remains unchanged, ensuring:
- Existing frontend integrations continue to work
- Gradual migration path to the new ReAct agent
- Side-by-side comparison of agent capabilities

## Next Steps

1. **Configure Azure OpenAI** credentials for full functionality
2. **Install missing dependencies** (`langchain-openai`)
3. **Test the endpoints** using the provided test scripts
4. **Update frontend** to use the new ReAct endpoints
5. **Monitor performance** and adjust configuration as needed

## Troubleshooting

### Common Issues:

1. **"ReAct agent not fully configured"**
   - Solution: Set Azure OpenAI environment variables

2. **"langchain_openai not found"**
   - Solution: `pip install langchain-openai`

3. **"LangGraph not available"**
   - Solution: `pip install langgraph`

4. **Authentication errors**
   - Solution: Ensure proper user authentication headers

5. **Tool execution failures**
   - Solution: Check connector configurations and credentials