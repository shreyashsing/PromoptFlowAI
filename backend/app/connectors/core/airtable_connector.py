"""
Airtable Connector - Comprehensive database operations for Airtable bases.
"""
import json
import base64
from typing import Dict, Any, List, Optional, Union
import httpx
from urllib.parse import quote, urlencode

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class AirtableConnector(BaseConnector):
    """
    Airtable Connector for comprehensive database operations.
    
    Supports record operations (create, read, update, delete, search), 
    base operations (get schema, list tables), and advanced features like
    batch operations, filtering, sorting, and field management.
    """
    
    def _get_connector_name(self) -> str:
        return "airtable"
    
    def _get_category(self) -> str:
        return "data_sources"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Airtable connector."""
        return {
            "operation": "list",
            "base_id": "appXXXXXXXXXXXXXX",
            "table_name": "Tasks",
            "max_records": 10
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Airtable-specific example prompts."""
        return [
            "Get all records from my Airtable base",
            "Create a new record in the Tasks table",
            "Update a record in my customer database",
            "Search for records with status 'Complete'",
            "Delete a record from the inventory table",
            "List all tables in my Airtable base",
            "Get records filtered by specific criteria"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Airtable-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Airtable-specific parameter inference
        if "list" in prompt_lower or "get" in prompt_lower:
            suggestions["operation"] = "list"
            
            # Extract number of records
            import re
            number_match = re.search(r'(\d+)', user_prompt)
            if number_match:
                suggestions["max_records"] = int(number_match.group(1))
        
        elif "create" in prompt_lower or "add" in prompt_lower:
            suggestions["operation"] = "create"
        
        elif "update" in prompt_lower or "modify" in prompt_lower:
            suggestions["operation"] = "update"
        
        elif "delete" in prompt_lower or "remove" in prompt_lower:
            suggestions["operation"] = "delete"
        
        elif "search" in prompt_lower or "find" in prompt_lower:
            suggestions["operation"] = "list"
            
            # Extract filter criteria
            filter_patterns = [
                r'with\s+status\s+["\']([^"\']+)["\']',
                r'where\s+([^,\.]+)',
                r'status\s+["\']([^"\']+)["\']'
            ]
            
            for pattern in filter_patterns:
                match = re.search(pattern, prompt_lower)
                if match:
                    filter_value = match.group(1)
                    suggestions["filter_by_formula"] = f"{{Status}} = '{filter_value}'"
                    break
        
        # Extract table name
        table_patterns = [
            r'table\s+["\']([^"\']+)["\']',
            r'from\s+["\']([^"\']+)["\']',
            r'in\s+the\s+([A-Za-z]+)\s+table'
        ]
        
        for pattern in table_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                suggestions["table_name"] = match.group(1)
                break
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Airtable resource to operate on",
                    "enum": ["record", "base", "table"],
                    "default": "record"
                },
                "operation": {
                    "type": "string",
                    "description": "Operation to perform on the resource",
                    "enum": [
                        # Record operations
                        "create", "get", "update", "delete", "search", "upsert",
                        # Base operations  
                        "get_schema", "list_tables",
                        # Table operations
                        "create_table", "update_table", "get_table_schema"
                    ],
                    "default": "get"
                },
                # Base identification
                "base_id": {
                    "type": "string",
                    "description": "Airtable Base ID (starts with 'app')",
                    "pattern": "^app[a-zA-Z0-9]+$"
                },
                "base_url": {
                    "type": "string",
                    "description": "Airtable Base URL (alternative to base_id)",
                    "pattern": "^https://airtable\\.com/app[a-zA-Z0-9]+.*$"
                },
                # Table identification
                "table_id": {
                    "type": "string",
                    "description": "Airtable Table ID or name"
                },
                "table_url": {
                    "type": "string",
                    "description": "Airtable Table URL (alternative to table_id)",
                    "pattern": "^https://airtable\\.com/app[a-zA-Z0-9]+/tbl[a-zA-Z0-9]+.*$"
                },
                # Record identification
                "record_id": {
                    "type": "string",
                    "description": "Airtable Record ID (starts with 'rec')",
                    "pattern": "^rec[a-zA-Z0-9]+$"
                },
                # Record data
                "fields": {
                    "type": "object",
                    "description": "Record fields as key-value pairs",
                    "additionalProperties": True
                },
                "records": {
                    "type": "array",
                    "description": "Array of records for batch operations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "fields": {"type": "object", "additionalProperties": True}
                        }
                    }
                },
                # Query and filtering
                "filter_formula": {
                    "type": "string",
                    "description": "Airtable formula for filtering records"
                },
                "view": {
                    "type": "string",
                    "description": "View name or ID to filter records"
                },
                "sort": {
                    "type": "array",
                    "description": "Sort configuration",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "direction": {"type": "string", "enum": ["asc", "desc"]}
                        },
                        "required": ["field"]
                    }
                },
                "fields_to_return": {
                    "type": "array",
                    "description": "Specific fields to return",
                    "items": {"type": "string"}
                },
                # Pagination
                "max_records": {
                    "type": "integer",
                    "description": "Maximum number of records to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of records per page",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 100
                },
                "offset": {
                    "type": "string",
                    "description": "Pagination offset token"
                },
                # Options
                "typecast": {
                    "type": "boolean",
                    "description": "Automatically cast field values to appropriate types",
                    "default": False
                },
                "return_fields_by_field_id": {
                    "type": "boolean",
                    "description": "Return field IDs instead of field names",
                    "default": False
                },
                "cell_format": {
                    "type": "string",
                    "description": "Format for returned cell values",
                    "enum": ["json", "string"],
                    "default": "json"
                },
                "time_zone": {
                    "type": "string",
                    "description": "Time zone for date/time fields",
                    "default": "UTC"
                },
                "user_locale": {
                    "type": "string",
                    "description": "User locale for formatting",
                    "default": "en"
                },
                # Upsert options
                "merge_fields": {
                    "type": "array",
                    "description": "Fields to use for matching in upsert operations",
                    "items": {"type": "string"}
                },
                # Table creation
                "table_name": {
                    "type": "string",
                    "description": "Name for new table"
                },
                "table_description": {
                    "type": "string",
                    "description": "Description for new table"
                },
                "table_fields": {
                    "type": "array",
                    "description": "Field definitions for new table",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": [
                                    "singleLineText", "email", "url", "multilineText",
                                    "number", "percent", "currency", "singleSelect",
                                    "multipleSelects", "singleCollaborator", "multipleCollaborators",
                                    "multipleRecordLinks", "date", "dateTime", "phoneNumber",
                                    "multipleAttachments", "checkbox", "formula", "createdTime",
                                    "rollup", "count", "lookup", "createdBy", "lastModifiedTime",
                                    "lastModifiedBy", "button", "rating", "richText", "duration",
                                    "autonumber", "barcode", "externalSyncSource"
                                ]
                            },
                            "description": {"type": "string"},
                            "options": {"type": "object", "additionalProperties": True}
                        },
                        "required": ["name", "type"]
                    }
                },
                # Advanced options
                "include_comment_count": {
                    "type": "boolean",
                    "description": "Include comment count in response",
                    "default": False
                },
                "include_created_time": {
                    "type": "boolean", 
                    "description": "Include created time in response",
                    "default": False
                }
            },
            "required": ["resource", "operation"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"resource": {"const": "record"}}},
                    "then": {"required": ["base_id", "table_id"]}
                },
                {
                    "if": {"properties": {"resource": {"const": "base"}}},
                    "then": {"required": ["base_id"]}
                },
                {
                    "if": {"properties": {"resource": {"const": "table"}}},
                    "then": {"required": ["base_id"]}
                },
                {
                    "if": {"properties": {"operation": {"enum": ["get", "update", "delete"]}}},
                    "then": {"required": ["record_id"]}
                },
                {
                    "if": {"properties": {"operation": {"enum": ["create", "update"]}}},
                    "then": {"required": ["fields"]}
                },
                {
                    "if": {"properties": {"operation": {"const": "upsert"}}},
                    "then": {"required": ["fields", "merge_fields"]}
                },
                {
                    "if": {"properties": {"operation": {"const": "create_table"}}},
                    "then": {"required": ["table_name", "table_fields"]}
                }
            ]
        }
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute Airtable operation with the provided parameters.
        
        Args:
            params: Airtable operation parameters
            context: Execution context with API tokens
            
        Returns:
            ConnectorResult with operation result or error
        """
        try:
            resource = params["resource"]
            operation = params["operation"]
            
            # Extract base_id from URL if provided
            base_id = self._extract_base_id(params)
            table_id = self._extract_table_id(params) if resource in ["record", "table"] else None
            
            # Get API token
            api_token = context.auth_tokens.get("api_token") or context.auth_tokens.get("access_token")
            if not api_token:
                raise AuthenticationException("Airtable API token not found")
            
            # Route to appropriate handler
            if resource == "record":
                result = await self._handle_record_operation(operation, params, base_id, table_id, api_token)
            elif resource == "base":
                result = await self._handle_base_operation(operation, params, base_id, api_token)
            elif resource == "table":
                result = await self._handle_table_operation(operation, params, base_id, table_id, api_token)
            else:
                raise ConnectorException(f"Unsupported Airtable resource: {resource}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "resource": resource,
                    "operation": operation,
                    "base_id": base_id,
                    "table_id": table_id,
                    "api_version": "v0"
                }
            )
            
        except AuthenticationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Airtable operation failed: {str(e)}",
                metadata={
                    "resource": params.get("resource", "unknown"),
                    "operation": params.get("operation", "unknown")
                }
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for Airtable.
        
        Returns:
            AuthRequirements for Airtable API token
        """
        return AuthRequirements(
            type=AuthType.API_KEY,
            fields={
                "api_token": "Airtable Personal Access Token or API Key"
            },
            instructions="Airtable connector requires a Personal Access Token. "
                        "You can create one at https://airtable.com/create/tokens. "
                        "Make sure to grant appropriate scopes for your bases and tables."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test Airtable API connection with provided token.
        
        Args:
            auth_tokens: API tokens
            
        Returns:
            True if connection successful
        """
        try:
            api_token = auth_tokens.get("api_token") or auth_tokens.get("access_token")
            if not api_token:
                return False
            
            # Test connection by listing bases (if token has meta:read scope)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.airtable.com/v0/meta/bases",
                    headers={"Authorization": f"Bearer {api_token}"}
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    def _extract_base_id(self, params: Dict[str, Any]) -> str:
        """Extract base ID from parameters or URL."""
        base_id = params.get("base_id")
        if base_id:
            return base_id
        
        base_url = params.get("base_url")
        if base_url:
            # Extract from URL like https://airtable.com/appXXXXXXXXXXXXXX/...
            import re
            match = re.search(r'airtable\.com/(app[a-zA-Z0-9]+)', base_url)
            if match:
                return match.group(1)
        
        raise ValidationException("base_id or base_url is required")
    
    def _extract_table_id(self, params: Dict[str, Any]) -> str:
        """Extract table ID from parameters or URL."""
        table_id = params.get("table_id")
        if table_id:
            return table_id
        
        table_url = params.get("table_url")
        if table_url:
            # Extract from URL like https://airtable.com/appXXX/tblXXXXXXXXXXXXXX/...
            import re
            match = re.search(r'/tbl([a-zA-Z0-9]+)', table_url)
            if match:
                return f"tbl{match.group(1)}"
        
        raise ValidationException("table_id or table_url is required")
    
    async def _handle_record_operation(self, operation: str, params: Dict[str, Any], 
                                     base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Handle record-level operations."""
        if operation == "create":
            return await self._create_record(params, base_id, table_id, api_token)
        elif operation == "get":
            return await self._get_record(params, base_id, table_id, api_token)
        elif operation == "update":
            return await self._update_record(params, base_id, table_id, api_token)
        elif operation == "delete":
            return await self._delete_record(params, base_id, table_id, api_token)
        elif operation == "search":
            return await self._search_records(params, base_id, table_id, api_token)
        elif operation == "upsert":
            return await self._upsert_record(params, base_id, table_id, api_token)
        else:
            raise ConnectorException(f"Unsupported record operation: {operation}")
    
    async def _handle_base_operation(self, operation: str, params: Dict[str, Any], 
                                   base_id: str, api_token: str) -> Dict[str, Any]:
        """Handle base-level operations."""
        if operation == "get_schema":
            return await self._get_base_schema(params, base_id, api_token)
        elif operation == "list_tables":
            return await self._list_tables(params, base_id, api_token)
        else:
            raise ConnectorException(f"Unsupported base operation: {operation}")
    
    async def _handle_table_operation(self, operation: str, params: Dict[str, Any], 
                                    base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Handle table-level operations."""
        if operation == "create_table":
            return await self._create_table(params, base_id, api_token)
        elif operation == "update_table":
            return await self._update_table(params, base_id, table_id, api_token)
        elif operation == "get_table_schema":
            return await self._get_table_schema(params, base_id, table_id, api_token)
        else:
            raise ConnectorException(f"Unsupported table operation: {operation}") 
   
    async def _create_record(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Create a new record in the specified table."""
        fields = params["fields"]
        typecast = params.get("typecast", False)
        return_fields_by_field_id = params.get("return_fields_by_field_id", False)
        
        body = {
            "fields": fields,
            "typecast": typecast,
            "returnFieldsByFieldId": return_fields_by_field_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to create record: {response.text}")
            
            result = response.json()
            return {
                "record_id": result["id"],
                "fields": result["fields"],
                "created_time": result.get("createdTime"),
                "result": f"Successfully created record with ID {result['id']}"
            }
    
    async def _get_record(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Get a specific record by ID."""
        record_id = params["record_id"]
        fields_to_return = params.get("fields_to_return", [])
        return_fields_by_field_id = params.get("return_fields_by_field_id", False)
        cell_format = params.get("cell_format", "json")
        time_zone = params.get("time_zone", "UTC")
        user_locale = params.get("user_locale", "en")
        
        query_params = {
            "returnFieldsByFieldId": str(return_fields_by_field_id).lower(),
            "cellFormat": cell_format,
            "timeZone": time_zone,
            "userLocale": user_locale
        }
        
        if fields_to_return:
            for field in fields_to_return:
                query_params[f"fields[]"] = field
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}/{record_id}",
                headers={"Authorization": f"Bearer {api_token}"},
                params=query_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get record: {response.text}")
            
            result = response.json()
            return {
                "record_id": result["id"],
                "fields": result["fields"],
                "created_time": result.get("createdTime"),
                "result": f"Successfully retrieved record {result['id']}"
            }
    
    async def _update_record(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Update an existing record."""
        record_id = params["record_id"]
        fields = params["fields"]
        typecast = params.get("typecast", False)
        return_fields_by_field_id = params.get("return_fields_by_field_id", False)
        
        body = {
            "fields": fields,
            "typecast": typecast,
            "returnFieldsByFieldId": return_fields_by_field_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}/{record_id}",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to update record: {response.text}")
            
            result = response.json()
            return {
                "record_id": result["id"],
                "fields": result["fields"],
                "created_time": result.get("createdTime"),
                "result": f"Successfully updated record {result['id']}"
            }
    
    async def _delete_record(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Delete a record by ID."""
        record_id = params["record_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}/{record_id}",
                headers={"Authorization": f"Bearer {api_token}"}
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to delete record: {response.text}")
            
            result = response.json()
            return {
                "deleted": result.get("deleted", False),
                "record_id": result.get("id", record_id),
                "result": f"Successfully deleted record {record_id}"
            }
    
    async def _search_records(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Search/list records with filtering, sorting, and pagination."""
        filter_formula = params.get("filter_formula")
        view = params.get("view")
        sort = params.get("sort", [])
        fields_to_return = params.get("fields_to_return", [])
        max_records = params.get("max_records", 100)
        page_size = params.get("page_size", 100)
        offset = params.get("offset")
        return_fields_by_field_id = params.get("return_fields_by_field_id", False)
        cell_format = params.get("cell_format", "json")
        time_zone = params.get("time_zone", "UTC")
        user_locale = params.get("user_locale", "en")
        include_comment_count = params.get("include_comment_count", False)
        
        query_params = {
            "maxRecords": str(max_records),
            "pageSize": str(page_size),
            "returnFieldsByFieldId": str(return_fields_by_field_id).lower(),
            "cellFormat": cell_format,
            "timeZone": time_zone,
            "userLocale": user_locale,
            "includeCommentCount": str(include_comment_count).lower()
        }
        
        if filter_formula:
            query_params["filterByFormula"] = filter_formula
        
        if view:
            query_params["view"] = view
        
        if fields_to_return:
            for field in fields_to_return:
                query_params[f"fields[]"] = field
        
        if sort:
            for i, sort_item in enumerate(sort):
                query_params[f"sort[{i}][field]"] = sort_item["field"]
                query_params[f"sort[{i}][direction]"] = sort_item.get("direction", "asc")
        
        if offset:
            query_params["offset"] = offset
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}",
                headers={"Authorization": f"Bearer {api_token}"},
                params=query_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to search records: {response.text}")
            
            result = response.json()
            return {
                "records": result.get("records", []),
                "offset": result.get("offset"),
                "total_records": len(result.get("records", [])),
                "result": f"Successfully retrieved {len(result.get('records', []))} records"
            }
    
    async def _upsert_record(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Create or update record based on merge fields."""
        fields = params["fields"]
        merge_fields = params["merge_fields"]
        typecast = params.get("typecast", False)
        return_fields_by_field_id = params.get("return_fields_by_field_id", False)
        
        body = {
            "records": [{"fields": fields}],
            "performUpsert": {
                "fieldsToMergeOn": merge_fields
            },
            "typecast": typecast,
            "returnFieldsByFieldId": return_fields_by_field_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.airtable.com/v0/{base_id}/{quote(table_id)}",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to upsert record: {response.text}")
            
            result = response.json()
            records = result.get("records", [])
            if records:
                record = records[0]
                return {
                    "record_id": record["id"],
                    "fields": record["fields"],
                    "created_time": record.get("createdTime"),
                    "was_created": result.get("createdRecords", []) and record["id"] in result["createdRecords"],
                    "was_updated": result.get("updatedRecords", []) and record["id"] in result["updatedRecords"],
                    "result": f"Successfully upserted record {record['id']}"
                }
            else:
                raise ConnectorException("No record returned from upsert operation")
    
    async def _get_base_schema(self, params: Dict[str, Any], base_id: str, api_token: str) -> Dict[str, Any]:
        """Get the complete schema for a base."""
        include_comment_count = params.get("include_comment_count", False)
        
        query_params = {
            "includeCommentCount": str(include_comment_count).lower()
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
                headers={"Authorization": f"Bearer {api_token}"},
                params=query_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get base schema: {response.text}")
            
            result = response.json()
            return {
                "base_id": base_id,
                "tables": result.get("tables", []),
                "total_tables": len(result.get("tables", [])),
                "result": f"Successfully retrieved schema for base {base_id}"
            }
    
    async def _list_tables(self, params: Dict[str, Any], base_id: str, api_token: str) -> Dict[str, Any]:
        """List all tables in a base."""
        schema = await self._get_base_schema(params, base_id, api_token)
        
        tables = []
        for table in schema["tables"]:
            tables.append({
                "id": table["id"],
                "name": table["name"],
                "description": table.get("description"),
                "primary_field_id": table.get("primaryFieldId"),
                "field_count": len(table.get("fields", [])),
                "view_count": len(table.get("views", []))
            })
        
        return {
            "base_id": base_id,
            "tables": tables,
            "total_tables": len(tables),
            "result": f"Successfully listed {len(tables)} tables in base {base_id}"
        }
    
    async def _create_table(self, params: Dict[str, Any], base_id: str, api_token: str) -> Dict[str, Any]:
        """Create a new table in the base."""
        table_name = params["table_name"]
        table_description = params.get("table_description", "")
        table_fields = params["table_fields"]
        
        body = {
            "name": table_name,
            "description": table_description,
            "fields": table_fields
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to create table: {response.text}")
            
            result = response.json()
            return {
                "table_id": result["id"],
                "name": result["name"],
                "description": result.get("description"),
                "fields": result.get("fields", []),
                "views": result.get("views", []),
                "result": f"Successfully created table '{result['name']}' with ID {result['id']}"
            }
    
    async def _update_table(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Update table properties."""
        table_name = params.get("table_name")
        table_description = params.get("table_description")
        
        body = {}
        if table_name:
            body["name"] = table_name
        if table_description is not None:
            body["description"] = table_description
        
        if not body:
            raise ValidationException("At least one of table_name or table_description must be provided")
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to update table: {response.text}")
            
            result = response.json()
            return {
                "table_id": result["id"],
                "name": result["name"],
                "description": result.get("description"),
                "result": f"Successfully updated table {result['id']}"
            }
    
    async def _get_table_schema(self, params: Dict[str, Any], base_id: str, table_id: str, api_token: str) -> Dict[str, Any]:
        """Get schema for a specific table."""
        include_comment_count = params.get("include_comment_count", False)
        
        query_params = {
            "includeCommentCount": str(include_comment_count).lower()
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}",
                headers={"Authorization": f"Bearer {api_token}"},
                params=query_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get table schema: {response.text}")
            
            result = response.json()
            return {
                "table_id": result["id"],
                "name": result["name"],
                "description": result.get("description"),
                "primary_field_id": result.get("primaryFieldId"),
                "fields": result.get("fields", []),
                "views": result.get("views", []),
                "field_count": len(result.get("fields", [])),
                "view_count": len(result.get("views", [])),
                "result": f"Successfully retrieved schema for table '{result['name']}'"
            }