"""
Gmail Connector - OAuth-based email operations.
"""
import json
import base64
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


class GmailConnector(BaseConnector):
    """
    Gmail Connector for email operations using OAuth authentication.
    
    Supports sending emails, reading emails, searching, and managing labels
    through the Gmail API.
    """
    
    def _get_category(self) -> str:
        return "communication"
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Gmail action to perform",
                    "enum": ["send", "read", "search", "list", "get_labels", "create_label", "delete"],
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
                }
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"const": "send"}}},
                    "then": {"required": ["to", "subject"]}
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
                    "if": {"properties": {"action": {"const": "create_label"}}},
                    "then": {"required": ["label_name"]}
                }
            ]
        }
    
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
            if action == "send":
                result = await self._send_email(params, access_token)
            elif action == "read":
                result = await self._read_email(params, access_token)
            elif action == "search":
                result = await self._search_emails(params, access_token)
            elif action == "list":
                result = await self._list_emails(params, access_token)
            elif action == "get_labels":
                result = await self._get_labels(access_token)
            elif action == "create_label":
                result = await self._create_label(params, access_token)
            elif action == "delete":
                result = await self._delete_email(params, access_token)
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
            "action": "send",
            "to": "recipient@example.com",
            "subject": "Hello from PromptFlow AI",
            "body": "This is a test email sent through the Gmail connector.",
            "html_body": "<h1>Hello!</h1><p>This is a <b>test email</b> sent through the Gmail connector.</p>"
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for Gmail connector."""
        return {
            "action": "Gmail operation: send (email), read (specific message), search (query emails), list (recent emails)",
            "to": "Recipient email address(es) - single address or comma-separated list",
            "subject": "Email subject line",
            "body": "Plain text email content",
            "html_body": "HTML formatted email content (optional)",
            "query": "Gmail search query (e.g., 'from:sender@example.com is:unread')",
            "message_id": "Gmail message ID for read/delete operations",
            "max_results": "Maximum number of emails to return (1-500)",
            "label_name": "Name for new label creation"
        }