"""
Notion Connector - API-based workspace and content management operations.
"""
import json
import re
from typing import Dict, Any, List, Optional, Union
import httpx
from datetime import datetime

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class NotionConnector(BaseConnector):
    """
    Notion Connector for workspace and content management using API authentication.
    
    Supports comprehensive operations: blocks, databases, pages, users, and database pages
    with full CRUD operations using Notion API v1.
    """
    
    def _get_connector_name(self) -> str:
        return "notion"
    
    def _get_category(self) -> str:
        return "productivity"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Notion connector."""
        return {
            "resource": "page",
            "operation": "create_page",
            "title": "New Project Plan",
            "content": "This is the content of the new page."
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Notion-specific example prompts."""
        return [
            "Create a new page in Notion with project details",
            "Get all pages from my Notion workspace",
            "Search for pages about 'marketing strategy'",
            "Update the project timeline page",
            "Create a database entry for the new client",
            "Get all users in my Notion workspace",
            "Add content blocks to the meeting notes page"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Notion-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Notion-specific parameter inference
        if "create" in prompt_lower:
            if "page" in prompt_lower:
                suggestions.update({
                    "resource": "page",
                    "operation": "create_page"
                })
            elif "database" in prompt_lower:
                suggestions.update({
                    "resource": "database_page",
                    "operation": "create_database_page"
                })
        
        elif "get" in prompt_lower or "fetch" in prompt_lower:
            if "page" in prompt_lower:
                suggestions.update({
                    "resource": "page",
                    "operation": "get_page"
                })
            elif "database" in prompt_lower:
                suggestions.update({
                    "resource": "database",
                    "operation": "get_database"
                })
            elif "user" in prompt_lower:
                suggestions.update({
                    "resource": "user",
                    "operation": "get_all_users"
                })
        
        elif "search" in prompt_lower:
            if "page" in prompt_lower:
                suggestions.update({
                    "resource": "page",
                    "operation": "search_pages"
                })
            elif "database" in prompt_lower:
                suggestions.update({
                    "resource": "database",
                    "operation": "search_databases"
                })
        
        elif "update" in prompt_lower:
            if "page" in prompt_lower:
                suggestions.update({
                    "resource": "database_page",
                    "operation": "update_database_page"
                })
        
        elif "add" in prompt_lower and "block" in prompt_lower:
            suggestions.update({
                "resource": "block",
                "operation": "append_block"
            })
        
        # Extract title from prompt
        import re
        title_patterns = [
            r'titled?\s+["\']([^"\']+)["\']',
            r'called\s+["\']([^"\']+)["\']',
            r'named\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                suggestions["title"] = match.group(1)
                break
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Notion resource to operate on",
                    "enum": ["block", "database", "database_page", "page", "user"],
                    "default": "page"
                },
                "operation": {
                    "type": "string",
                    "description": "Operation to perform on the resource",
                    "enum": [
                        # Block operations
                        "append_block", "get_block_children",
                        # Database operations  
                        "get_database", "get_all_databases", "search_databases",
                        # Database Page operations
                        "create_database_page", "get_database_page", "get_all_database_pages", "update_database_page",
                        # Page operations
                        "create_page", "get_page", "search_pages", "archive_page",
                        # User operations
                        "get_user", "get_all_users"
                    ],
                    "default": "get_page"
                },
                
                # Common identifiers
                "page_id": {
                    "type": "string",
                    "description": "Notion page ID (32-character UUID with or without dashes)"
                },
                "block_id": {
                    "type": "string", 
                    "description": "Notion block ID (32-character UUID with or without dashes)"
                },
                "database_id": {
                    "type": "string",
                    "description": "Notion database ID (32-character UUID with or without dashes)"
                },
                "user_id": {
                    "type": "string",
                    "description": "Notion user ID"
                },
                
                # Page creation/update
                "title": {
                    "type": "string",
                    "description": "Title for the page"
                },
                "parent_page_id": {
                    "type": "string",
                    "description": "Parent page ID for creating child pages"
                },
                "parent_database_id": {
                    "type": "string", 
                    "description": "Parent database ID for creating database pages"
                },
                
                # Content and blocks
                "content": {
                    "type": "string",
                    "description": "Text content to add as blocks"
                },
                "blocks": {
                    "type": "array",
                    "description": "Array of block objects to append",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "toggle", "code", "quote"]
                            },
                            "content": {
                                "type": "string",
                                "description": "Text content of the block"
                            }
                        }
                    }
                },
                
                # Database properties
                "properties": {
                    "type": "object",
                    "description": "Database page properties as key-value pairs",
                    "additionalProperties": True
                },
                
                # Search and filtering
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "filter": {
                    "type": "object",
                    "description": "Filter object for database queries",
                    "additionalProperties": True
                },
                "sorts": {
                    "type": "array",
                    "description": "Array of sort objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "property": {"type": "string"},
                            "direction": {"type": "string", "enum": ["ascending", "descending"]}
                        }
                    }
                },
                
                # Pagination and limits
                "page_size": {
                    "type": "integer",
                    "description": "Number of results per page",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 100
                },
                "start_cursor": {
                    "type": "string",
                    "description": "Cursor for pagination"
                },
                "return_all": {
                    "type": "boolean",
                    "description": "Return all results (ignore pagination)",
                    "default": False
                },
                
                # Options
                "simple_output": {
                    "type": "boolean",
                    "description": "Return simplified output format",
                    "default": False
                },
                "include_nested_blocks": {
                    "type": "boolean",
                    "description": "Include nested blocks in block operations",
                    "default": False
                },
                
                # Page/Block options
                "icon_type": {
                    "type": "string",
                    "description": "Type of icon (emoji or external)",
                    "enum": ["emoji", "external"]
                },
                "icon_value": {
                    "type": "string",
                    "description": "Icon emoji or external URL"
                },
                "cover_url": {
                    "type": "string",
                    "description": "Cover image URL"
                }
            },
            "required": ["resource", "operation"],
            "additionalProperties": False
        }
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """Notion uses API key authentication."""
        return AuthRequirements(
            type=AuthType.API_KEY,
            fields={"api_key": "Notion integration token"},
            instructions="Notion API requires an integration token. Create an integration at https://www.notion.so/my-integrations"
        )
    
    def _normalize_id(self, notion_id: str) -> str:
        """Normalize Notion ID by removing dashes and validating format."""
        if not notion_id:
            raise ValidationException("Notion ID cannot be empty")
        
        # Remove dashes and validate
        clean_id = notion_id.replace("-", "")
        if len(clean_id) != 32 or not re.match(r'^[a-f0-9]{32}$', clean_id, re.IGNORECASE):
            raise ValidationException(f"Invalid Notion ID format: {notion_id}")
        
        return clean_id
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract Notion ID from URL."""
        # Pattern for Notion URLs
        patterns = [
            r'notion\.so/.*?([a-f0-9]{32})',
            r'notion\.so/.*?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return self._normalize_id(match.group(1))
        
        raise ValidationException(f"Could not extract Notion ID from URL: {url}")
    
    def _get_notion_id(self, id_value: str) -> str:
        """Get normalized Notion ID from various formats."""
        if not id_value:
            raise ValidationException("ID value is required")
        
        # If it looks like a URL, extract ID
        if "notion.so" in id_value:
            return self._extract_id_from_url(id_value)
        
        # Otherwise normalize as direct ID
        return self._normalize_id(id_value)
    
    def _format_blocks(self, blocks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format blocks for Notion API."""
        formatted_blocks = []
        
        for block in blocks_data:
            block_type = block.get("type", "paragraph")
            content = block.get("content", "")
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote"]:
                formatted_block = {
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": content}
                            }
                        ]
                    }
                }
            elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                formatted_block = {
                    "object": "block", 
                    "type": block_type,
                    block_type: {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": content}
                            }
                        ]
                    }
                }
            elif block_type == "to_do":
                formatted_block = {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [
                            {
                                "type": "text", 
                                "text": {"content": content}
                            }
                        ],
                        "checked": False
                    }
                }
            elif block_type == "code":
                formatted_block = {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": content}
                            }
                        ],
                        "language": "plain text"
                    }
                }
            else:
                # Default to paragraph
                formatted_block = {
                    "object": "block",
                    "type": "paragraph", 
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": content}
                            }
                        ]
                    }
                }
            
            formatted_blocks.append(formatted_block)
        
        return formatted_blocks
    
    def _create_text_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Create paragraph blocks from text content."""
        if not content:
            return []
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        blocks = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                blocks.append({
                    "type": "paragraph",
                    "content": paragraph.strip()
                })
        
        return self._format_blocks(blocks)
    
    async def _make_notion_request(
        self, 
        method: str, 
        endpoint: str, 
        context: ConnectorExecutionContext,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Notion API."""
        api_key = context.auth_tokens.get("api_key")
        if not api_key:
            raise AuthenticationException("Notion API key is required")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        url = f"https://api.notion.com/v1{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise AuthenticationException("Invalid Notion API key")
                elif response.status_code == 404:
                    raise ConnectorException("Notion resource not found")
                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("message", f"HTTP {response.status_code}")
                    raise ConnectorException(f"Notion API error: {error_message}")
                
                return response.json()
                
            except httpx.TimeoutException:
                raise ConnectorException("Request to Notion API timed out")
            except httpx.RequestError as e:
                raise ConnectorException(f"Failed to connect to Notion API: {str(e)}")
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Execute Notion operations."""
        try:
            resource = params.get("resource", "page")
            operation = params.get("operation", "get_page")
            
            # Route to appropriate handler
            if resource == "block":
                return await self._handle_block_operations(params, context)
            elif resource == "database":
                return await self._handle_database_operations(params, context)
            elif resource == "database_page":
                return await self._handle_database_page_operations(params, context)
            elif resource == "page":
                return await self._handle_page_operations(params, context)
            elif resource == "user":
                return await self._handle_user_operations(params, context)
            else:
                raise ValidationException(f"Unsupported resource: {resource}")
                
        except (ValidationException, AuthenticationException, ConnectorException):
            raise
        except Exception as e:
            raise ConnectorException(f"Unexpected error in Notion connector: {str(e)}")    

    async def _handle_block_operations(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Handle block-related operations."""
        operation = params.get("operation")
        
        if operation == "append_block":
            block_id = self._get_notion_id(params.get("block_id", ""))
            
            # Prepare blocks to append
            blocks_to_append = []
            
            # Handle content parameter (simple text)
            if params.get("content"):
                blocks_to_append.extend(self._create_text_blocks(params["content"]))
            
            # Handle blocks parameter (structured blocks)
            if params.get("blocks"):
                blocks_to_append.extend(self._format_blocks(params["blocks"]))
            
            if not blocks_to_append:
                raise ValidationException("Either 'content' or 'blocks' parameter is required")
            
            data = {"children": blocks_to_append}
            result = await self._make_notion_request("PATCH", f"/blocks/{block_id}/children", context, data)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Successfully appended {len(blocks_to_append)} blocks"
            )
        
        elif operation == "get_block_children":
            block_id = self._get_notion_id(params.get("block_id", ""))
            
            query_params = {}
            if params.get("page_size"):
                query_params["page_size"] = params["page_size"]
            if params.get("start_cursor"):
                query_params["start_cursor"] = params["start_cursor"]
            
            result = await self._make_notion_request("GET", f"/blocks/{block_id}/children", context, params=query_params)
            
            # Handle nested blocks if requested
            if params.get("include_nested_blocks", False):
                result = await self._get_nested_blocks(result, context)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved children for block {block_id}"
            )
        
        else:
            raise ValidationException(f"Unsupported block operation: {operation}")
    
    async def _handle_database_operations(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Handle database-related operations."""
        operation = params.get("operation")
        
        if operation == "get_database":
            database_id = self._get_notion_id(params.get("database_id", ""))
            result = await self._make_notion_request("GET", f"/databases/{database_id}", context)
            
            if params.get("simple_output", False):
                result = self._simplify_database_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved database {database_id}"
            )
        
        elif operation == "get_all_databases":
            data = {"filter": {"property": "object", "value": "database"}}
            
            if params.get("page_size"):
                data["page_size"] = params["page_size"]
            
            if params.get("return_all", False):
                result = await self._get_all_paginated_results("/search", context, data)
            else:
                result = await self._make_notion_request("POST", "/search", context, data)
                result = result.get("results", [])
            
            if params.get("simple_output", False):
                result = [self._simplify_database_output(db) for db in result]
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved {len(result)} databases"
            )
        
        elif operation == "search_databases":
            data = {
                "filter": {"property": "object", "value": "database"}
            }
            
            if params.get("query"):
                data["query"] = params["query"]
            
            if params.get("sorts"):
                data["sort"] = params["sorts"]
            
            if params.get("page_size"):
                data["page_size"] = params["page_size"]
            
            if params.get("return_all", False):
                result = await self._get_all_paginated_results("/search", context, data)
            else:
                result = await self._make_notion_request("POST", "/search", context, data)
                result = result.get("results", [])
            
            if params.get("simple_output", False):
                result = [self._simplify_database_output(db) for db in result]
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Found {len(result)} databases matching search"
            )
        
        else:
            raise ValidationException(f"Unsupported database operation: {operation}")
    
    async def _handle_database_page_operations(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Handle database page operations."""
        operation = params.get("operation")
        
        if operation == "create_database_page":
            database_id = self._get_notion_id(params.get("database_id", ""))
            
            # Get database schema to find title property
            database = await self._make_notion_request("GET", f"/databases/{database_id}", context)
            title_property = self._find_title_property(database.get("properties", {}))
            
            data = {
                "parent": {"database_id": database_id},
                "properties": {}
            }
            
            # Set title if provided
            if params.get("title") and title_property:
                data["properties"][title_property] = {
                    "title": [{"text": {"content": params["title"]}}]
                }
            
            # Set other properties
            if params.get("properties"):
                data["properties"].update(self._format_database_properties(params["properties"]))
            
            # Add content blocks
            if params.get("content"):
                data["children"] = self._create_text_blocks(params["content"])
            elif params.get("blocks"):
                data["children"] = self._format_blocks(params["blocks"])
            
            # Add icon if specified
            if params.get("icon_value"):
                if params.get("icon_type") == "external":
                    data["icon"] = {"external": {"url": params["icon_value"]}}
                else:
                    data["icon"] = {"emoji": params["icon_value"]}
            
            result = await self._make_notion_request("POST", "/pages", context, data)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message="Successfully created database page"
            )
        
        elif operation == "get_database_page":
            page_id = self._get_notion_id(params.get("page_id", ""))
            result = await self._make_notion_request("GET", f"/pages/{page_id}", context)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved database page {page_id}"
            )
        
        elif operation == "get_all_database_pages":
            database_id = self._get_notion_id(params.get("database_id", ""))
            
            data = {}
            
            # Add filter if provided
            if params.get("filter"):
                data["filter"] = params["filter"]
            
            # Add sorts if provided
            if params.get("sorts"):
                data["sorts"] = params["sorts"]
            
            # Add page size
            if params.get("page_size"):
                data["page_size"] = params["page_size"]
            
            if params.get("return_all", False):
                result = await self._get_all_paginated_results(f"/databases/{database_id}/query", context, data)
            else:
                result = await self._make_notion_request("POST", f"/databases/{database_id}/query", context, data)
                result = result.get("results", [])
            
            if params.get("simple_output", False):
                result = [self._simplify_page_output(page) for page in result]
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved {len(result)} pages from database"
            )
        
        elif operation == "update_database_page":
            page_id = self._get_notion_id(params.get("page_id", ""))
            
            data = {"properties": {}}
            
            # Update properties
            if params.get("properties"):
                data["properties"] = self._format_database_properties(params["properties"])
            
            # Update icon if specified
            if params.get("icon_value"):
                if params.get("icon_type") == "external":
                    data["icon"] = {"type": "external", "external": {"url": params["icon_value"]}}
                else:
                    data["icon"] = {"type": "emoji", "emoji": params["icon_value"]}
            
            result = await self._make_notion_request("PATCH", f"/pages/{page_id}", context, data)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Successfully updated database page {page_id}"
            )
        
        else:
            raise ValidationException(f"Unsupported database page operation: {operation}")
    
    async def _handle_page_operations(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Handle page operations."""
        operation = params.get("operation")
        
        if operation == "create_page":
            data = {
                "parent": {},
                "properties": {}
            }
            
            # Set parent
            if params.get("parent_page_id"):
                data["parent"]["page_id"] = self._get_notion_id(params["parent_page_id"])
            elif params.get("parent_database_id"):
                data["parent"]["database_id"] = self._get_notion_id(params["parent_database_id"])
            else:
                raise ValidationException("Either parent_page_id or parent_database_id is required")
            
            # Set title
            if params.get("title"):
                data["properties"]["title"] = {
                    "title": [{"text": {"content": params["title"]}}]
                }
            
            # Add content blocks
            if params.get("content"):
                data["children"] = self._create_text_blocks(params["content"])
            elif params.get("blocks"):
                data["children"] = self._format_blocks(params["blocks"])
            
            # Add icon if specified
            if params.get("icon_value"):
                if params.get("icon_type") == "external":
                    data["icon"] = {"external": {"url": params["icon_value"]}}
                else:
                    data["icon"] = {"emoji": params["icon_value"]}
            
            result = await self._make_notion_request("POST", "/pages", context, data)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message="Successfully created page"
            )
        
        elif operation == "get_page":
            page_id = self._get_notion_id(params.get("page_id", ""))
            result = await self._make_notion_request("GET", f"/pages/{page_id}", context)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved page {page_id}"
            )
        
        elif operation == "search_pages":
            data = {}
            
            if params.get("query"):
                data["query"] = params["query"]
            
            if params.get("filter"):
                data["filter"] = params["filter"]
            
            if params.get("sorts"):
                data["sort"] = params["sorts"]
            
            if params.get("page_size"):
                data["page_size"] = params["page_size"]
            
            if params.get("return_all", False):
                result = await self._get_all_paginated_results("/search", context, data)
            else:
                result = await self._make_notion_request("POST", "/search", context, data)
                result = result.get("results", [])
            
            if params.get("simple_output", False):
                result = [self._simplify_page_output(page) for page in result]
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Found {len(result)} pages matching search"
            )
        
        elif operation == "archive_page":
            page_id = self._get_notion_id(params.get("page_id", ""))
            data = {"archived": True}
            result = await self._make_notion_request("PATCH", f"/pages/{page_id}", context, data)
            
            if params.get("simple_output", False):
                result = self._simplify_page_output(result)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Successfully archived page {page_id}"
            )
        
        else:
            raise ValidationException(f"Unsupported page operation: {operation}")
    
    async def _handle_user_operations(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Handle user operations."""
        operation = params.get("operation")
        
        if operation == "get_user":
            user_id = params.get("user_id", "")
            if not user_id:
                raise ValidationException("user_id is required")
            
            result = await self._make_notion_request("GET", f"/users/{user_id}", context)
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved user {user_id}"
            )
        
        elif operation == "get_all_users":
            query_params = {}
            if params.get("page_size"):
                query_params["page_size"] = params["page_size"]
            if params.get("start_cursor"):
                query_params["start_cursor"] = params["start_cursor"]
            
            if params.get("return_all", False):
                result = await self._get_all_paginated_results("/users", context, method="GET")
            else:
                result = await self._make_notion_request("GET", "/users", context, params=query_params)
                result = result.get("results", [])
            
            return ConnectorResult(
                success=True,
                data=result,
                message=f"Retrieved {len(result)} users"
            )
        
        else:
            raise ValidationException(f"Unsupported user operation: {operation}")
    
    async def _get_all_paginated_results(
        self, 
        endpoint: str, 
        context: ConnectorExecutionContext, 
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST"
    ) -> List[Dict[str, Any]]:
        """Get all results from paginated endpoint."""
        all_results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            if method == "POST":
                request_data = data.copy() if data else {}
                if start_cursor:
                    request_data["start_cursor"] = start_cursor
                response = await self._make_notion_request("POST", endpoint, context, request_data)
            else:
                params = {"start_cursor": start_cursor} if start_cursor else {}
                response = await self._make_notion_request("GET", endpoint, context, params=params)
            
            results = response.get("results", [])
            all_results.extend(results)
            
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return all_results
    
    async def _get_nested_blocks(self, blocks_response: Dict[str, Any], context: ConnectorExecutionContext) -> Dict[str, Any]:
        """Recursively get nested blocks."""
        results = blocks_response.get("results", [])
        
        for block in results:
            if block.get("has_children", False):
                block_id = block["id"]
                children_response = await self._make_notion_request("GET", f"/blocks/{block_id}/children", context)
                block["children"] = await self._get_nested_blocks(children_response, context)
        
        return blocks_response
    
    def _find_title_property(self, properties: Dict[str, Any]) -> Optional[str]:
        """Find the title property in database schema."""
        for prop_name, prop_config in properties.items():
            if prop_config.get("type") == "title":
                return prop_name
        return None
    
    def _format_database_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Format properties for database page operations."""
        formatted_props = {}
        
        for prop_name, prop_value in properties.items():
            # Simple text properties
            if isinstance(prop_value, str):
                formatted_props[prop_name] = {
                    "rich_text": [{"text": {"content": prop_value}}]
                }
            # Number properties
            elif isinstance(prop_value, (int, float)):
                formatted_props[prop_name] = {"number": prop_value}
            # Boolean properties (checkbox)
            elif isinstance(prop_value, bool):
                formatted_props[prop_name] = {"checkbox": prop_value}
            # Date properties
            elif isinstance(prop_value, dict) and "start" in prop_value:
                formatted_props[prop_name] = {"date": prop_value}
            # Select properties
            elif isinstance(prop_value, dict) and "name" in prop_value:
                formatted_props[prop_name] = {"select": prop_value}
            # Multi-select properties
            elif isinstance(prop_value, list):
                formatted_props[prop_name] = {"multi_select": prop_value}
            else:
                # Default to rich text
                formatted_props[prop_name] = {
                    "rich_text": [{"text": {"content": str(prop_value)}}]
                }
        
        return formatted_props
    
    def _simplify_database_output(self, database: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify database output for easier consumption."""
        return {
            "id": database.get("id"),
            "title": self._extract_title_from_properties(database.get("properties", {})),
            "description": database.get("description", []),
            "created_time": database.get("created_time"),
            "last_edited_time": database.get("last_edited_time"),
            "properties": database.get("properties", {}),
            "url": database.get("url")
        }
    
    def _simplify_page_output(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify page output for easier consumption."""
        return {
            "id": page.get("id"),
            "title": self._extract_title_from_properties(page.get("properties", {})),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "archived": page.get("archived", False),
            "properties": page.get("properties", {}),
            "parent": page.get("parent", {}),
            "url": page.get("url"),
            "icon": page.get("icon"),
            "cover": page.get("cover")
        }
    
    def _extract_title_from_properties(self, properties: Dict[str, Any]) -> str:
        """Extract title text from properties."""
        for prop_name, prop_config in properties.items():
            if prop_config.get("type") == "title":
                title_array = prop_config.get("title", [])
                if title_array:
                    return "".join([item.get("text", {}).get("content", "") for item in title_array])
        return ""