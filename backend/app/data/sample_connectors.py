"""
Sample connector metadata for testing and initial setup.
"""
from app.models.connector import ConnectorMetadata
from app.models.base import AuthType
from datetime import datetime


SAMPLE_CONNECTORS = [
    ConnectorMetadata(
        name="http_request",
        description="Make HTTP requests to any REST API endpoint. Supports GET, POST, PUT, DELETE methods with custom headers and authentication.",
        category="data_sources",
        parameter_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to make the request to"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                "headers": {"type": "object", "description": "Custom headers to include"},
                "body": {"type": "object", "description": "Request body for POST/PUT requests"},
                "timeout": {"type": "integer", "default": 30, "description": "Request timeout in seconds"}
            },
            "required": ["url"]
        },
        auth_type=AuthType.API_KEY,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="gmail_connector",
        description="Send and receive emails through Gmail. Supports reading inbox, sending emails, managing labels, and searching messages.",
        category="communication",
        parameter_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send", "read", "search", "label"], "description": "Action to perform"},
                "to": {"type": "string", "description": "Recipient email address (for send action)"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
                "query": {"type": "string", "description": "Search query (for search action)"},
                "max_results": {"type": "integer", "default": 10, "description": "Maximum number of results"}
            },
            "required": ["action"]
        },
        auth_type=AuthType.OAUTH2,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="google_sheets",
        description="Read and write data to Google Sheets. Supports reading ranges, writing data, creating sheets, and formatting cells.",
        category="data_sources",
        parameter_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Google Sheets spreadsheet ID"},
                "action": {"type": "string", "enum": ["read", "write", "create", "format"], "description": "Action to perform"},
                "range": {"type": "string", "description": "Cell range (e.g., 'A1:B10')"},
                "values": {"type": "array", "description": "Data to write (for write action)"},
                "sheet_name": {"type": "string", "description": "Name of the sheet tab"}
            },
            "required": ["spreadsheet_id", "action"]
        },
        auth_type=AuthType.OAUTH2,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="webhook_receiver",
        description="Receive data from external webhooks and trigger workflows. Supports JSON payload processing and custom response handling.",
        category="triggers",
        parameter_schema={
            "type": "object",
            "properties": {
                "endpoint_name": {"type": "string", "description": "Unique name for the webhook endpoint"},
                "response_type": {"type": "string", "enum": ["json", "text", "status"], "default": "json"},
                "response_data": {"type": "object", "description": "Custom response data"},
                "filters": {"type": "object", "description": "Filters to apply to incoming data"}
            },
            "required": ["endpoint_name"]
        },
        auth_type=AuthType.NONE,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="openai_completion",
        description="Generate text completions using OpenAI GPT models. Supports various models, custom prompts, and response formatting.",
        category="ai_services",
        parameter_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to send to the AI model"},
                "model": {"type": "string", "default": "gpt-4", "description": "OpenAI model to use"},
                "max_tokens": {"type": "integer", "default": 1000, "description": "Maximum tokens in response"},
                "temperature": {"type": "number", "default": 0.7, "description": "Response creativity (0-1)"},
                "system_message": {"type": "string", "description": "System message to set context"}
            },
            "required": ["prompt"]
        },
        auth_type=AuthType.API_KEY,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="perplexity_search",
        description="Search the web and get AI-powered answers using Perplexity AI. Great for research and fact-checking.",
        category="ai_services",
        parameter_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or question"},
                "model": {"type": "string", "default": "llama-3.1-sonar-small-128k-online", "description": "Perplexity model to use"},
                "max_tokens": {"type": "integer", "default": 1000, "description": "Maximum tokens in response"},
                "return_citations": {"type": "boolean", "default": True, "description": "Include source citations"}
            },
            "required": ["query"]
        },
        auth_type=AuthType.API_KEY,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="text_summarizer",
        description="Summarize long text content into concise summaries. Supports different summary lengths and styles.",
        category="ai_services",
        parameter_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content to summarize"},
                "length": {"type": "string", "enum": ["short", "medium", "long"], "default": "medium"},
                "style": {"type": "string", "enum": ["bullet_points", "paragraph", "key_insights"], "default": "paragraph"},
                "focus": {"type": "string", "description": "Specific aspect to focus on in summary"}
            },
            "required": ["text"]
        },
        auth_type=AuthType.NONE,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="slack_messenger",
        description="Send messages to Slack channels and users. Supports rich formatting, file uploads, and channel management.",
        category="communication",
        parameter_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send_message", "upload_file", "create_channel"], "description": "Action to perform"},
                "channel": {"type": "string", "description": "Channel name or ID"},
                "message": {"type": "string", "description": "Message content"},
                "user": {"type": "string", "description": "User to send direct message to"},
                "file_path": {"type": "string", "description": "Path to file to upload"},
                "thread_ts": {"type": "string", "description": "Thread timestamp for replies"}
            },
            "required": ["action"]
        },
        auth_type=AuthType.OAUTH2,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="conditional_logic",
        description="Add conditional logic to workflows. Supports if/else conditions, comparisons, and data validation.",
        category="logic",
        parameter_schema={
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "Condition to evaluate (e.g., 'value > 10')"},
                "if_true": {"type": "object", "description": "Action to take if condition is true"},
                "if_false": {"type": "object", "description": "Action to take if condition is false"},
                "variable": {"type": "string", "description": "Variable name to evaluate"},
                "operator": {"type": "string", "enum": ["==", "!=", ">", "<", ">=", "<=", "contains"], "description": "Comparison operator"},
                "value": {"type": "string", "description": "Value to compare against"}
            },
            "required": ["condition"]
        },
        auth_type=AuthType.NONE,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="data_merger",
        description="Merge and combine data from multiple sources. Supports JSON merging, array concatenation, and data transformation.",
        category="logic",
        parameter_schema={
            "type": "object",
            "properties": {
                "sources": {"type": "array", "description": "List of data sources to merge"},
                "merge_type": {"type": "string", "enum": ["deep_merge", "shallow_merge", "concatenate", "union"], "default": "deep_merge"},
                "key_field": {"type": "string", "description": "Field to use as merge key"},
                "output_format": {"type": "string", "enum": ["json", "csv", "array"], "default": "json"},
                "remove_duplicates": {"type": "boolean", "default": False, "description": "Remove duplicate entries"}
            },
            "required": ["sources"]
        },
        auth_type=AuthType.NONE,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="schedule_trigger",
        description="Schedule workflows to run at specific times or intervals. Supports cron expressions and recurring schedules.",
        category="triggers",
        parameter_schema={
            "type": "object",
            "properties": {
                "schedule_type": {"type": "string", "enum": ["once", "recurring", "cron"], "description": "Type of schedule"},
                "datetime": {"type": "string", "description": "Specific datetime for one-time execution"},
                "interval": {"type": "string", "enum": ["hourly", "daily", "weekly", "monthly"], "description": "Recurring interval"},
                "cron_expression": {"type": "string", "description": "Cron expression for complex scheduling"},
                "timezone": {"type": "string", "default": "UTC", "description": "Timezone for scheduling"}
            },
            "required": ["schedule_type"]
        },
        auth_type=AuthType.NONE,
        usage_count=0
    ),
    
    ConnectorMetadata(
        name="error_handler",
        description="Handle errors and exceptions in workflows. Supports retry logic, fallback actions, and error notifications.",
        category="control",
        parameter_schema={
            "type": "object",
            "properties": {
                "max_retries": {"type": "integer", "default": 3, "description": "Maximum number of retry attempts"},
                "retry_delay": {"type": "integer", "default": 5, "description": "Delay between retries in seconds"},
                "fallback_action": {"type": "object", "description": "Action to take if all retries fail"},
                "error_types": {"type": "array", "description": "Specific error types to handle"},
                "notify_on_error": {"type": "boolean", "default": False, "description": "Send notification on error"}
            }
        },
        auth_type=AuthType.NONE,
        usage_count=0
    )
]