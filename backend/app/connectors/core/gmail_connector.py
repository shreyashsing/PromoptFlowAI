"""
Gmail Connector - OAuth-based email operations with full n8n feature parity.
"""
import json
import base64
import re
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import httpx

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException
from app.core.error_utils import handle_connector_errors, handle_external_api_errors


class GmailConnector(BaseConnector):
    """
    Gmail Connector for email operations using OAuth authentication.
    
    Supports sending emails, reading emails, searching, and managing labels
    through the Gmail API.
    """
    
    def _get_connector_name(self) -> str:
        return "gmail_connector"
    
    def _get_category(self) -> str:
        return "communication"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Gmail connector."""
        return {
            "action": "send",
            "to": "user@example.com",
            "subject": "Test Email",
            "body": "This is a test email sent via Gmail connector."
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Gmail-specific example prompts."""
        return [
            "Send an email to john@example.com about the meeting tomorrow",
            "Find all unread emails from my manager",
            "Search for emails with 'invoice' in the subject",
            "Mark all emails from newsletter@company.com as read",
            "Get the latest 20 emails from my inbox",
            "Reply to the email about project updates",
            "Create a draft email for the team announcement"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Gmail-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Gmail-specific parameter inference
        if "send" in prompt_lower or "email" in prompt_lower:
            suggestions["action"] = "send"
            
            # Extract email addresses
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, user_prompt)
            if emails:
                suggestions["to"] = emails[0] if len(emails) == 1 else ",".join(emails)
        
        elif "search" in prompt_lower or "find" in prompt_lower:
            suggestions["action"] = "search"
            
            # Convert natural language to Gmail query
            if "unread" in prompt_lower:
                suggestions["query"] = "is:unread"
            elif "from" in prompt_lower:
                # Extract sender info
                from_match = re.search(r'from\s+([^\s]+)', prompt_lower)
                if from_match:
                    suggestions["query"] = f"from:{from_match.group(1)}"
            elif "subject" in prompt_lower:
                # Extract subject keywords
                subject_match = re.search(r'subject[:\s]+["\']?([^"\']+)["\']?', prompt_lower)
                if subject_match:
                    suggestions["query"] = f"subject:{subject_match.group(1)}"
        
        elif "list" in prompt_lower or "get" in prompt_lower:
            suggestions["action"] = "list"
            
            # Extract number of results
            import re
            number_match = re.search(r'(\d+)', user_prompt)
            if number_match:
                suggestions["max_results"] = int(number_match.group(1))
        
        elif "mark" in prompt_lower and "read" in prompt_lower:
            suggestions["action"] = "mark_as_read"
        
        elif "delete" in prompt_lower:
            suggestions["action"] = "delete"
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Gmail action to perform",
                    "enum": [
                        # Message operations
                        "send", "reply", "read", "search", "list", "delete", 
                        "mark_as_read", "mark_as_unread", "add_labels", "remove_labels",
                        # Draft operations
                        "create_draft", "get_draft", "delete_draft", "list_drafts",
                        # Label operations
                        "get_labels", "create_label", "delete_label", "get_label",
                        # Thread operations
                        "get_thread", "list_threads", "delete_thread", "trash_thread", 
                        "untrash_thread", "add_thread_labels", "remove_thread_labels"
                    ],
                    "default": "send"
                },
                # Send email parameters
                "to": {
                    "type": ["string", "array"],
                    "description": "Recipient email address(es)"
                },
                "cc": {
                    "type": ["string", "array"],
                    "description": "CC recipient email address(es)"
                },
                "bcc": {
                    "type": ["string", "array"],
                    "description": "BCC recipient email address(es)"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML email body content"
                },
                "attachments": {
                    "type": "array",
                    "description": "Email attachments",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {"type": "string", "description": "Base64 encoded content"},
                            "mime_type": {"type": "string"}
                        },
                        "required": ["filename", "content"]
                    }
                },
                # Read/search parameters
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:example@gmail.com is:unread')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 500
                },
                "include_spam_trash": {
                    "type": "boolean",
                    "description": "Include spam and trash in search results",
                    "default": False
                },
                # Specific message operations
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID for specific operations"
                },
                "label_ids": {
                    "type": "array",
                    "description": "Label IDs to apply or filter by",
                    "items": {"type": "string"}
                },
                # Label operations
                "label_name": {
                    "type": "string",
                    "description": "Name for label operations"
                },
                "label_color": {
                    "type": "string",
                    "description": "Color for label creation",
                    "enum": ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink", "brown", "gray"]
                },
                # Thread operations
                "thread_id": {
                    "type": "string",
                    "description": "Gmail thread ID for thread operations"
                },
                # Draft operations
                "draft_id": {
                    "type": "string",
                    "description": "Gmail draft ID for draft operations"
                },
                # Reply operations
                "reply_to": {
                    "type": "string",
                    "description": "Reply-To email address"
                },
                "sender_name": {
                    "type": "string",
                    "description": "Sender name for outgoing emails"
                },
                # Advanced options
                "format": {
                    "type": "string",
                    "description": "Response format for message/draft retrieval",
                    "enum": ["full", "metadata", "minimal", "raw"],
                    "default": "full"
                },
                "simple": {
                    "type": "boolean",
                    "description": "Return simplified response format",
                    "default": False
                },
                "return_all": {
                    "type": "boolean",
                    "description": "Return all results (ignore limit)",
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 500
                }
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                # Message operations
                {
                    "if": {"properties": {"action": {"const": "send"}}},
                    "then": {"required": ["to", "subject"]}
                },
                {
                    "if": {"properties": {"action": {"const": "reply"}}},
                    "then": {"required": ["message_id", "body"]}
                },
                {
                    "if": {"properties": {"action": {"const": "search"}}},
                    "then": {"required": ["query"]}
                },
                {
                    "if": {"properties": {"action": {"const": "read"}}},
                    "then": {"required": ["message_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete"}}},
                    "then": {"required": ["message_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "mark_as_read"}}},
                    "then": {"required": ["message_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "mark_as_unread"}}},
                    "then": {"required": ["message_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "add_labels"}}},
                    "then": {"required": ["message_id", "label_ids"]}
                },
                {
                    "if": {"properties": {"action": {"const": "remove_labels"}}},
                    "then": {"required": ["message_id", "label_ids"]}
                },
                # Draft operations
                {
                    "if": {"properties": {"action": {"const": "create_draft"}}},
                    "then": {"required": ["subject"]}
                },
                {
                    "if": {"properties": {"action": {"const": "get_draft"}}},
                    "then": {"required": ["draft_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete_draft"}}},
                    "then": {"required": ["draft_id"]}
                },
                # Label operations
                {
                    "if": {"properties": {"action": {"const": "create_label"}}},
                    "then": {"required": ["label_name"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete_label"}}},
                    "then": {"required": ["label_ids"]}
                },
                {
                    "if": {"properties": {"action": {"const": "get_label"}}},
                    "then": {"required": ["label_ids"]}
                },
                # Thread operations
                {
                    "if": {"properties": {"action": {"const": "get_thread"}}},
                    "then": {"required": ["thread_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete_thread"}}},
                    "then": {"required": ["thread_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "trash_thread"}}},
                    "then": {"required": ["thread_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "untrash_thread"}}},
                    "then": {"required": ["thread_id"]}
                },
                {
                    "if": {"properties": {"action": {"const": "add_thread_labels"}}},
                    "then": {"required": ["thread_id", "label_ids"]}
                },
                {
                    "if": {"properties": {"action": {"const": "remove_thread_labels"}}},
                    "then": {"required": ["thread_id", "label_ids"]}
                }
            ]
        }
    
    @handle_connector_errors("Gmail")
    @handle_external_api_errors("Gmail API", retryable=True)
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute Gmail operation with the provided parameters.
        
        Args:
            params: Gmail operation parameters
            context: Execution context with OAuth tokens
            
        Returns:
            ConnectorResult with operation result or error
        """
        try:
            action = params["action"]
            access_token = context.auth_tokens.get("access_token")
            
            if not access_token:
                raise AuthenticationException("Gmail access token not found")
            
            # Route to appropriate action handler
            # Message operations
            if action == "send":
                result = await self._send_email(params, access_token)
            elif action == "reply":
                result = await self._reply_to_email(params, access_token)
            elif action == "read":
                result = await self._read_email(params, access_token)
            elif action == "search":
                result = await self._search_emails(params, access_token)
            elif action == "list":
                result = await self._list_emails(params, access_token)
            elif action == "delete":
                result = await self._delete_email(params, access_token)
            elif action == "mark_as_read":
                result = await self._mark_as_read(params, access_token)
            elif action == "mark_as_unread":
                result = await self._mark_as_unread(params, access_token)
            elif action == "add_labels":
                result = await self._add_labels_to_message(params, access_token)
            elif action == "remove_labels":
                result = await self._remove_labels_from_message(params, access_token)
            # Draft operations
            elif action == "create_draft":
                result = await self._create_draft(params, access_token)
            elif action == "get_draft":
                result = await self._get_draft(params, access_token)
            elif action == "delete_draft":
                result = await self._delete_draft(params, access_token)
            elif action == "list_drafts":
                result = await self._list_drafts(params, access_token)
            # Label operations
            elif action == "get_labels":
                result = await self._get_labels(access_token)
            elif action == "create_label":
                result = await self._create_label(params, access_token)
            elif action == "delete_label":
                result = await self._delete_label(params, access_token)
            elif action == "get_label":
                result = await self._get_label(params, access_token)
            # Thread operations
            elif action == "get_thread":
                result = await self._get_thread(params, access_token)
            elif action == "list_threads":
                result = await self._list_threads(params, access_token)
            elif action == "delete_thread":
                result = await self._delete_thread(params, access_token)
            elif action == "trash_thread":
                result = await self._trash_thread(params, access_token)
            elif action == "untrash_thread":
                result = await self._untrash_thread(params, access_token)
            elif action == "add_thread_labels":
                result = await self._add_labels_to_thread(params, access_token)
            elif action == "remove_thread_labels":
                result = await self._remove_labels_from_thread(params, access_token)
            else:
                raise ConnectorException(f"Unsupported Gmail action: {action}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "action": action,
                    "gmail_api_version": "v1"
                }
            )
            
        except AuthenticationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Gmail operation failed: {str(e)}",
                metadata={"action": params.get("action", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get OAuth authentication requirements for Gmail.
        
        Returns:
            AuthRequirements for Gmail OAuth
        """
        return AuthRequirements(
            type=AuthType.OAUTH2,
            fields={
                "access_token": "OAuth access token for Gmail API",
                "refresh_token": "OAuth refresh token for token renewal"
            },
            oauth_scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.labels"
            ],
            instructions="Gmail connector requires OAuth authentication with Google. "
                        "You'll need to authorize access to your Gmail account."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test Gmail API connection with provided OAuth tokens.
        
        Args:
            auth_tokens: OAuth tokens
            
        Returns:
            True if connection successful
        """
        try:
            access_token = auth_tokens.get("access_token")
            if not access_token:
                return False
            
            # Test connection by getting user profile
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def _send_email(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Send an email through Gmail API."""
        # Prepare recipients
        to_addresses = self._normalize_addresses(params["to"])
        cc_addresses = self._normalize_addresses(params.get("cc", []))
        bcc_addresses = self._normalize_addresses(params.get("bcc", []))
        
        # Create email message
        msg = MIMEMultipart('alternative') if params.get("html_body") else MIMEText(params.get("body", ""))
        
        if isinstance(msg, MIMEMultipart):
            # Add plain text part
            if params.get("body"):
                msg.attach(MIMEText(params["body"], 'plain'))
            
            # Add HTML part
            if params.get("html_body"):
                msg.attach(MIMEText(params["html_body"], 'html'))
        
        # Set headers
        msg['To'] = ', '.join(to_addresses)
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
        msg['Subject'] = params["subject"]
        
        # Add attachments
        if params.get("attachments"):
            # Convert to multipart if not already
            if not isinstance(msg, MIMEMultipart):
                original_msg = msg
                msg = MIMEMultipart()
                msg.attach(original_msg)
                msg['To'] = ', '.join(to_addresses)
                if cc_addresses:
                    msg['Cc'] = ', '.join(cc_addresses)
                msg['Subject'] = params["subject"]
            
            for attachment in params["attachments"]:
                await self._add_attachment(msg, attachment)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        # Send via Gmail API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"raw": raw_message}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to send email: {response.text}")
            
            result = response.json()
            return {
                "message_id": result["id"],
                "thread_id": result["threadId"],
                "status": "sent",
                "recipients": {
                    "to": to_addresses,
                    "cc": cc_addresses,
                    "bcc": bcc_addresses
                }
            }
    
    async def _read_email(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Read a specific email by message ID."""
        message_id = params["message_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to read email: {response.text}")
            
            message = response.json()
            return await self._parse_message(message)
    
    async def _search_emails(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Search emails using Gmail query syntax."""
        query = params["query"]
        max_results = params.get("max_results", 10)
        include_spam_trash = params.get("include_spam_trash", False)
        
        # Search for messages
        search_params = {
            "q": query,
            "maxResults": max_results
        }
        if not include_spam_trash:
            search_params["includeSpamTrash"] = False
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=search_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to search emails: {response.text}")
            
            search_result = response.json()
            messages = search_result.get("messages", [])
            
            # Get full message details for each result
            detailed_messages = []
            for msg in messages[:max_results]:  # Limit results
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if msg_response.status_code == 200:
                    detailed_messages.append(await self._parse_message(msg_response.json()))
            
            return {
                "query": query,
                "total_results": search_result.get("resultSizeEstimate", 0),
                "returned_results": len(detailed_messages),
                "messages": detailed_messages
            }
    
    async def _list_emails(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """List recent emails."""
        max_results = params.get("max_results", 10)
        label_ids = params.get("label_ids", [])
        
        list_params = {
            "maxResults": max_results
        }
        if label_ids:
            list_params["labelIds"] = label_ids
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=list_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to list emails: {response.text}")
            
            result = response.json()
            messages = result.get("messages", [])
            
            # Get details for each message
            detailed_messages = []
            for msg in messages:
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if msg_response.status_code == 200:
                    detailed_messages.append(await self._parse_message(msg_response.json()))
            
            return {
                "total_messages": len(detailed_messages),
                "messages": detailed_messages
            }
    
    async def _get_labels(self, access_token: str) -> Dict[str, Any]:
        """Get all Gmail labels."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get labels: {response.text}")
            
            result = response.json()
            return {
                "labels": result.get("labels", [])
            }
    
    async def _create_label(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create a new Gmail label."""
        label_name = params["label_name"]
        label_color = params.get("label_color")
        
        label_data = {
            "name": label_name,
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow"
        }
        
        if label_color:
            # Map color names to Gmail color IDs
            color_map = {
                "red": "#d93025", "orange": "#f57c00", "yellow": "#f9ab00",
                "green": "#0f9d58", "teal": "#00acc1", "blue": "#4285f4",
                "purple": "#9c27b0", "pink": "#e91e63", "brown": "#8d6e63", "gray": "#5f6368"
            }
            if label_color in color_map:
                label_data["color"] = {
                    "textColor": "#ffffff",
                    "backgroundColor": color_map[label_color]
                }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=label_data
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to create label: {response.text}")
            
            return response.json()
    
    async def _delete_email(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete an email by message ID."""
        message_id = params["message_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 204:
                raise ConnectorException(f"Failed to delete email: {response.text}")
            
            return {
                "message_id": message_id,
                "status": "deleted"
            }
    
    async def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into standardized format."""
        headers = {}
        for header in message.get("payload", {}).get("headers", []):
            headers[header["name"].lower()] = header["value"]
        
        # Extract body
        body = ""
        html_body = ""
        
        payload = message.get("payload", {})
        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    body = self._decode_body(part.get("body", {}).get("data", ""))
                elif part.get("mimeType") == "text/html":
                    html_body = self._decode_body(part.get("body", {}).get("data", ""))
        else:
            # Single part message
            if payload.get("mimeType") == "text/plain":
                body = self._decode_body(payload.get("body", {}).get("data", ""))
            elif payload.get("mimeType") == "text/html":
                html_body = self._decode_body(payload.get("body", {}).get("data", ""))
        
        return {
            "id": message["id"],
            "thread_id": message["threadId"],
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "date": headers.get("date", ""),
            "body": body,
            "html_body": html_body,
            "labels": message.get("labelIds", []),
            "snippet": message.get("snippet", ""),
            "size_estimate": message.get("sizeEstimate", 0)
        }
    
    def _decode_body(self, data: str) -> str:
        """Decode base64url encoded message body."""
        if not data:
            return ""
        
        try:
            # Add padding if needed
            padding = 4 - len(data) % 4
            if padding != 4:
                data += '=' * padding
            
            # Replace URL-safe characters
            data = data.replace('-', '+').replace('_', '/')
            
            return base64.b64decode(data).decode('utf-8')
        except Exception:
            return data  # Return as-is if decoding fails
    
    def _normalize_addresses(self, addresses) -> List[str]:
        """Normalize email addresses to list format."""
        if isinstance(addresses, str):
            return [addr.strip() for addr in addresses.split(',')]
        elif isinstance(addresses, list):
            return [str(addr).strip() for addr in addresses]
        else:
            return []
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]) -> None:
        """Add attachment to email message."""
        filename = attachment["filename"]
        content = attachment["content"]
        mime_type = attachment.get("mime_type", "application/octet-stream")
        
        # Decode base64 content
        try:
            file_data = base64.b64decode(content)
        except Exception:
            raise ConnectorException(f"Invalid base64 content for attachment: {filename}")
        
        # Create attachment part
        part = MIMEBase(*mime_type.split('/'))
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}'
        )
        
        msg.attach(part)
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Gmail operations."""
        return {
            # Send email example
            "send_email": {
                "action": "send",
                "to": "recipient@example.com",
                "subject": "Hello from PromptFlow AI",
                "body": "This is a test email sent through the Gmail connector.",
                "html_body": "<h1>Hello!</h1><p>This is a <b>test email</b> sent through the Gmail connector.</p>",
                "sender_name": "PromptFlow AI"
            },
            # Reply to email example
            "reply_email": {
                "action": "reply",
                "message_id": "message_id_here",
                "body": "Thank you for your email. This is my reply.",
                "sender_name": "PromptFlow AI"
            },
            # Search emails example
            "search_emails": {
                "action": "search",
                "query": "from:example@gmail.com is:unread",
                "max_results": 10
            },
            # Create draft example
            "create_draft": {
                "action": "create_draft",
                "to": "recipient@example.com",
                "subject": "Draft Email",
                "body": "This is a draft email.",
                "sender_name": "PromptFlow AI"
            },
            # Get thread example
            "get_thread": {
                "action": "get_thread",
                "thread_id": "thread_id_here",
                "simple": True
            },
            # Mark as read example
            "mark_read": {
                "action": "mark_as_read",
                "message_id": "message_id_here"
            }
        }
    
    # ==================== NEW METHODS FROM N8N IMPLEMENTATION ====================
    
    async def _reply_to_email(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Reply to an email message."""
        message_id = params["message_id"]
        
        # First get the original message to extract thread info
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": "From,To,Cc,Subject,References,Message-ID"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get original message: {response.text}")
            
            original_message = response.json()
            payload = original_message.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            
            # Extract original sender for reply-to
            original_from = headers.get("from", "")
            original_subject = headers.get("subject", "")
            references = headers.get("references", "")
            message_id_header = headers.get("message-id", "")
            
            # Prepare reply recipients
            to_addresses = self._normalize_addresses(params.get("to", [original_from]))
            cc_addresses = self._normalize_addresses(params.get("cc", []))
            bcc_addresses = self._normalize_addresses(params.get("bcc", []))
            
            # Create reply message
            msg = MIMEMultipart('alternative') if params.get("html_body") else MIMEText(params.get("body", ""))
            
            if isinstance(msg, MIMEMultipart):
                if params.get("body"):
                    msg.attach(MIMEText(params["body"], 'plain'))
                if params.get("html_body"):
                    msg.attach(MIMEText(params["html_body"], 'html'))
            
            # Set headers for reply
            msg['To'] = ', '.join(to_addresses)
            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)
            
            # Handle subject - add "Re:" if not already present
            reply_subject = original_subject
            if not reply_subject.lower().startswith("re:"):
                reply_subject = f"Re: {reply_subject}"
            msg['Subject'] = reply_subject
            
            # Set reply headers
            msg['In-Reply-To'] = message_id_header
            if references:
                msg['References'] = f"{references} {message_id_header}"
            else:
                msg['References'] = message_id_header
            
            # Add sender name if provided
            if params.get("sender_name"):
                profile_response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    email_address = profile.get("emailAddress", "")
                    msg['From'] = f"{params['sender_name']} <{email_address}>"
            
            # Add attachments if provided
            if params.get("attachments"):
                if not isinstance(msg, MIMEMultipart):
                    original_msg = msg
                    msg = MIMEMultipart()
                    msg.attach(original_msg)
                    # Re-set headers
                    msg['To'] = ', '.join(to_addresses)
                    if cc_addresses:
                        msg['Cc'] = ', '.join(cc_addresses)
                    msg['Subject'] = reply_subject
                    msg['In-Reply-To'] = message_id_header
                    msg['References'] = references
                
                for attachment in params["attachments"]:
                    await self._add_attachment(msg, attachment)
            
            # Encode and send reply
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            send_response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "raw": raw_message,
                    "threadId": original_message["threadId"]
                }
            )
            
            if send_response.status_code != 200:
                raise ConnectorException(f"Failed to send reply: {send_response.text}")
            
            result = send_response.json()
            return {
                "message_id": result["id"],
                "thread_id": result["threadId"],
                "status": "sent",
                "reply_to": original_from,
                "subject": reply_subject
            }
    
    async def _mark_as_read(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Mark a message as read."""
        message_id = params["message_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"removeLabelIds": ["UNREAD"]}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to mark as read: {response.text}")
            
            return {
                "message_id": message_id,
                "status": "marked_as_read"
            }
    
    async def _mark_as_unread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Mark a message as unread."""
        message_id = params["message_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"addLabelIds": ["UNREAD"]}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to mark as unread: {response.text}")
            
            return {
                "message_id": message_id,
                "status": "marked_as_unread"
            }
    
    async def _add_labels_to_message(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Add labels to a message."""
        message_id = params["message_id"]
        label_ids = params["label_ids"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"addLabelIds": label_ids}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to add labels: {response.text}")
            
            return {
                "message_id": message_id,
                "added_labels": label_ids,
                "status": "labels_added"
            }
    
    async def _remove_labels_from_message(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Remove labels from a message."""
        message_id = params["message_id"]
        label_ids = params["label_ids"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"removeLabelIds": label_ids}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to remove labels: {response.text}")
            
            return {
                "message_id": message_id,
                "removed_labels": label_ids,
                "status": "labels_removed"
            }
    
    # ==================== DRAFT OPERATIONS ====================
    
    async def _create_draft(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create a draft email."""
        # Prepare recipients
        to_addresses = self._normalize_addresses(params.get("to", []))
        cc_addresses = self._normalize_addresses(params.get("cc", []))
        bcc_addresses = self._normalize_addresses(params.get("bcc", []))
        
        # Create draft message
        msg = MIMEMultipart('alternative') if params.get("html_body") else MIMEText(params.get("body", ""))
        
        if isinstance(msg, MIMEMultipart):
            if params.get("body"):
                msg.attach(MIMEText(params["body"], 'plain'))
            if params.get("html_body"):
                msg.attach(MIMEText(params["html_body"], 'html'))
        
        # Set headers
        if to_addresses:
            msg['To'] = ', '.join(to_addresses)
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
        msg['Subject'] = params.get("subject", "")
        
        # Add sender name if provided
        if params.get("sender_name"):
            async with httpx.AsyncClient() as client:
                profile_response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    email_address = profile.get("emailAddress", "")
                    msg['From'] = f"{params['sender_name']} <{email_address}>"
        
        # Add reply-to if provided
        if params.get("reply_to"):
            msg['Reply-To'] = params["reply_to"]
        
        # Add attachments
        if params.get("attachments"):
            if not isinstance(msg, MIMEMultipart):
                original_msg = msg
                msg = MIMEMultipart()
                msg.attach(original_msg)
                # Re-set headers
                if to_addresses:
                    msg['To'] = ', '.join(to_addresses)
                if cc_addresses:
                    msg['Cc'] = ', '.join(cc_addresses)
                msg['Subject'] = params.get("subject", "")
            
            for attachment in params["attachments"]:
                await self._add_attachment(msg, attachment)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        # Create draft
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "message": {
                        "raw": raw_message,
                        "threadId": params.get("thread_id")
                    }
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to create draft: {response.text}")
            
            result = response.json()
            return {
                "draft_id": result["id"],
                "message_id": result["message"]["id"],
                "thread_id": result["message"].get("threadId"),
                "status": "draft_created"
            }
    
    async def _get_draft(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get a specific draft by ID."""
        draft_id = params["draft_id"]
        format_type = params.get("format", "full")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "raw" if format_type == "full" else format_type}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get draft: {response.text}")
            
            draft = response.json()
            
            if format_type == "full":
                # Parse the raw message
                parsed = await self._parse_message(draft["message"])
                parsed["draft_id"] = draft["id"]
                parsed["message_id"] = draft["message"]["id"]
                return parsed
            else:
                return draft
    
    async def _delete_draft(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete a draft by ID."""
        draft_id = params["draft_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 204:
                raise ConnectorException(f"Failed to delete draft: {response.text}")
            
            return {
                "draft_id": draft_id,
                "status": "deleted"
            }
    
    async def _list_drafts(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """List drafts."""
        return_all = params.get("return_all", False)
        limit = params.get("limit", 10)
        
        list_params = {}
        if not return_all:
            list_params["maxResults"] = limit
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
                headers={"Authorization": f"Bearer {access_token}"},
                params=list_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to list drafts: {response.text}")
            
            result = response.json()
            drafts = result.get("drafts", [])
            
            # Get details for each draft if requested
            if params.get("simple", False):
                return {
                    "total_drafts": len(drafts),
                    "drafts": drafts
                }
            else:
                detailed_drafts = []
                for draft in drafts:
                    draft_response = await client.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft['id']}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"format": "raw"}
                    )
                    if draft_response.status_code == 200:
                        draft_data = draft_response.json()
                        parsed = await self._parse_message(draft_data["message"])
                        parsed["draft_id"] = draft_data["id"]
                        parsed["message_id"] = draft_data["message"]["id"]
                        detailed_drafts.append(parsed)
                
                return {
                    "total_drafts": len(detailed_drafts),
                    "drafts": detailed_drafts
                }
    
    # ==================== LABEL OPERATIONS ====================
    
    async def _delete_label(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete a label by ID."""
        label_ids = params["label_ids"]
        if isinstance(label_ids, str):
            label_ids = [label_ids]
        
        results = []
        async with httpx.AsyncClient() as client:
            for label_id in label_ids:
                response = await client.delete(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/labels/{label_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 204:
                    raise ConnectorException(f"Failed to delete label {label_id}: {response.text}")
                
                results.append({
                    "label_id": label_id,
                    "status": "deleted"
                })
        
        return {
            "deleted_labels": results,
            "status": "success"
        }
    
    async def _get_label(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get a specific label by ID."""
        label_ids = params["label_ids"]
        if isinstance(label_ids, str):
            label_ids = [label_ids]
        
        results = []
        async with httpx.AsyncClient() as client:
            for label_id in label_ids:
                response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/labels/{label_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    raise ConnectorException(f"Failed to get label {label_id}: {response.text}")
                
                results.append(response.json())
        
        return {
            "labels": results
        }
    
    # ==================== THREAD OPERATIONS ====================
    
    async def _get_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get a thread by ID."""
        thread_id = params["thread_id"]
        simple = params.get("simple", False)
        
        thread_params = {}
        if simple:
            thread_params["format"] = "metadata"
            thread_params["metadataHeaders"] = "From,To,Cc,Bcc,Subject"
        else:
            thread_params["format"] = "full"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=thread_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get thread: {response.text}")
            
            thread = response.json()
            
            if simple:
                # Simplify the response
                simplified_messages = []
                for message in thread.get("messages", []):
                    simplified = await self._simplify_message(message)
                    simplified_messages.append(simplified)
                
                return {
                    "thread_id": thread["id"],
                    "message_count": len(simplified_messages),
                    "messages": simplified_messages
                }
            else:
                return thread
    
    async def _list_threads(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """List threads."""
        return_all = params.get("return_all", False)
        limit = params.get("limit", 10)
        query = params.get("query", "")
        
        list_params = {}
        if query:
            list_params["q"] = query
        if not return_all:
            list_params["maxResults"] = limit
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/threads",
                headers={"Authorization": f"Bearer {access_token}"},
                params=list_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to list threads: {response.text}")
            
            result = response.json()
            threads = result.get("threads", [])
            
            return {
                "total_threads": len(threads),
                "threads": threads
            }
    
    async def _delete_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete a thread."""
        thread_id = params["thread_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 204:
                raise ConnectorException(f"Failed to delete thread: {response.text}")
            
            return {
                "thread_id": thread_id,
                "status": "deleted"
            }
    
    async def _trash_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Move a thread to trash."""
        thread_id = params["thread_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/trash",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to trash thread: {response.text}")
            
            return {
                "thread_id": thread_id,
                "status": "trashed"
            }
    
    async def _untrash_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Remove a thread from trash."""
        thread_id = params["thread_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/untrash",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to untrash thread: {response.text}")
            
            return {
                "thread_id": thread_id,
                "status": "untrashed"
            }
    
    async def _add_labels_to_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Add labels to a thread."""
        thread_id = params["thread_id"]
        label_ids = params["label_ids"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"addLabelIds": label_ids}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to add labels to thread: {response.text}")
            
            return {
                "thread_id": thread_id,
                "added_labels": label_ids,
                "status": "labels_added"
            }
    
    async def _remove_labels_from_thread(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Remove labels from a thread."""
        thread_id = params["thread_id"]
        label_ids = params["label_ids"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/modify",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"removeLabelIds": label_ids}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to remove labels from thread: {response.text}")
            
            return {
                "thread_id": thread_id,
                "removed_labels": label_ids,
                "status": "labels_removed"
            }
    
    # ==================== HELPER METHODS ====================
    
    async def _simplify_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify a message for easier consumption."""
        headers = {}
        for header in message.get("payload", {}).get("headers", []):
            headers[header["name"].lower()] = header["value"]
        
        return {
            "id": message["id"],
            "thread_id": message["threadId"],
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "bcc": headers.get("bcc", ""),
            "date": headers.get("date", ""),
            "snippet": message.get("snippet", ""),
            "labels": message.get("labelIds", [])
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for Gmail connector."""
        return {
            "action": "Gmail operation - supports messages, drafts, labels, and threads",
            "to": "Recipient email address(es) - single address or comma-separated list",
            "subject": "Email subject line",
            "body": "Plain text email content",
            "html_body": "HTML formatted email content (optional)",
            "query": "Gmail search query (e.g., 'from:sender@example.com is:unread')",
            "message_id": "Gmail message ID for message operations",
            "thread_id": "Gmail thread ID for thread operations",
            "draft_id": "Gmail draft ID for draft operations",
            "label_ids": "Label ID(s) for label operations",
            "label_name": "Name for new label creation",
            "sender_name": "Display name for sender",
            "reply_to": "Reply-To email address",
            "format": "Response format: full, metadata, minimal, raw",
            "simple": "Return simplified response format (true/false)",
            "return_all": "Return all results ignoring limit (true/false)",
            "limit": "Maximum number of results to return (1-500)"
        }