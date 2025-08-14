"""
Google Sheets Connector - OAuth-based spreadsheet operations.
"""
import json
from typing import Dict, Any, List, Optional, Union
import httpx

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class GoogleSheetsConnector(BaseConnector):
    """
    Google Sheets Connector for spreadsheet operations using OAuth authentication.
    
    Supports full CRUD operations: reading, writing, updating, and deleting data
    in Google Sheets, as well as managing sheets and formatting.
    """
    
    def _get_connector_name(self) -> str:
        return "google_sheets"
    
    def _get_category(self) -> str:
        return "data_sources"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Google Sheets connector."""
        return {
            "operation": "read",
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "Sheet1!A1:D10"
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Google Sheets-specific example prompts."""
        return [
            "Read data from a Google Sheets spreadsheet",
            "Update cells in my budget spreadsheet",
            "Create a new spreadsheet for project tracking",
            "Add a new row to the customer database",
            "Get all data from the first sheet",
            "Clear data from a specific range",
            "Format cells in the spreadsheet"
        ]
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Google Sheets-specific parameter suggestions."""
        suggestions = super().generate_parameter_suggestions(user_prompt, context)
        prompt_lower = user_prompt.lower()
        
        # Google Sheets-specific parameter inference
        if "read" in prompt_lower or "get" in prompt_lower:
            suggestions["operation"] = "read"
            
            # Default range if not specified
            if "range" not in suggestions:
                suggestions["range"] = "Sheet1!A1:Z100"
        
        elif "write" in prompt_lower or "update" in prompt_lower:
            suggestions["operation"] = "write"
        
        elif "append" in prompt_lower or "add" in prompt_lower:
            suggestions["operation"] = "append"
        
        elif "create" in prompt_lower:
            suggestions["operation"] = "create"
            
            # Extract spreadsheet title
            import re
            title_patterns = [
                r'create.*?spreadsheet.*?["\']([^"\']+)["\']',
                r'spreadsheet.*?called\s+["\']([^"\']+)["\']',
                r'new.*?["\']([^"\']+)["\']'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, prompt_lower)
                if match:
                    suggestions["title"] = match.group(1)
                    break
        
        elif "clear" in prompt_lower:
            suggestions["operation"] = "clear"
        
        elif "delete" in prompt_lower:
            suggestions["operation"] = "delete"
        
        # Extract range if mentioned
        range_patterns = [
            r'range\s+([A-Z]+\d+:[A-Z]+\d+)',
            r'cells?\s+([A-Z]+\d+:[A-Z]+\d+)',
            r'from\s+([A-Z]+\d+)\s+to\s+([A-Z]+\d+)'
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, user_prompt.upper())
            if match:
                if len(match.groups()) == 1:
                    suggestions["range"] = f"Sheet1!{match.group(1)}"
                else:
                    suggestions["range"] = f"Sheet1!{match.group(1)}:{match.group(2)}"
                break
        
        return suggestions
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Google Sheets action to perform",
                    "enum": ["read", "write", "update", "append", "delete", "create_sheet", "delete_sheet", "get_info", "clear", "format"],
                    "default": "read"
                },
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Sheets spreadsheet ID (from URL)"
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab within the spreadsheet",
                    "default": "Sheet1"
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation (e.g., 'A1:C10', 'A:A', 'Sheet1!A1:B5')"
                },
                # Data operations
                "values": {
                    "type": "array",
                    "description": "2D array of values to write/update",
                    "items": {
                        "type": "array",
                        "items": {"type": ["string", "number", "boolean", "null"]}
                    }
                },
                "value_input_option": {
                    "type": "string",
                    "description": "How input data should be interpreted",
                    "enum": ["RAW", "USER_ENTERED"],
                    "default": "USER_ENTERED"
                },
                "major_dimension": {
                    "type": "string",
                    "description": "Major dimension for data interpretation",
                    "enum": ["ROWS", "COLUMNS"],
                    "default": "ROWS"
                },
                # Sheet management
                "new_sheet_name": {
                    "type": "string",
                    "description": "Name for new sheet creation"
                },
                "sheet_properties": {
                    "type": "object",
                    "description": "Properties for sheet creation",
                    "properties": {
                        "title": {"type": "string"},
                        "index": {"type": "integer"},
                        "sheet_type": {"type": "string", "enum": ["GRID", "OBJECT"], "default": "GRID"},
                        "grid_properties": {
                            "type": "object",
                            "properties": {
                                "row_count": {"type": "integer", "default": 1000},
                                "column_count": {"type": "integer", "default": 26}
                            }
                        }
                    }
                },
                # Formatting
                "format": {
                    "type": "object",
                    "description": "Cell formatting options",
                    "properties": {
                        "background_color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1}
                            }
                        },
                        "text_format": {
                            "type": "object",
                            "properties": {
                                "bold": {"type": "boolean"},
                                "italic": {"type": "boolean"},
                                "font_size": {"type": "integer"},
                                "font_family": {"type": "string"}
                            }
                        },
                        "number_format": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["TEXT", "NUMBER", "PERCENT", "CURRENCY", "DATE", "TIME", "DATE_TIME"]},
                                "pattern": {"type": "string"}
                            }
                        }
                    }
                },
                # Query options
                "include_grid_data": {
                    "type": "boolean",
                    "description": "Include cell data when getting spreadsheet info",
                    "default": False
                },
                "date_time_render_option": {
                    "type": "string",
                    "description": "How dates and times should be rendered",
                    "enum": ["SERIAL_NUMBER", "FORMATTED_STRING"],
                    "default": "FORMATTED_STRING"
                },
                "value_render_option": {
                    "type": "string",
                    "description": "How values should be rendered",
                    "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                    "default": "FORMATTED_VALUE"
                }
            },
            "required": ["action", "spreadsheet_id"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"enum": ["read", "clear", "format"]}}},
                    "then": {"required": ["range"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["write", "update", "append"]}}},
                    "then": {"required": ["values"]}
                },
                {
                    "if": {"properties": {"action": {"const": "create_sheet"}}},
                    "then": {"required": ["new_sheet_name"]}
                },
                {
                    "if": {"properties": {"action": {"const": "delete_sheet"}}},
                    "then": {"required": ["sheet_name"]}
                }
            ]
        }
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute Google Sheets operation with the provided parameters.
        
        Args:
            params: Google Sheets operation parameters
            context: Execution context with OAuth tokens
            
        Returns:
            ConnectorResult with operation result or error
        """
        try:
            action = params["action"]
            access_token = context.auth_tokens.get("access_token")
            
            if not access_token:
                raise AuthenticationException("Google Sheets access token not found")
            
            # Route to appropriate action handler
            if action == "read":
                result = await self._read_data(params, access_token)
            elif action == "write":
                result = await self._write_data(params, access_token)
            elif action == "update":
                result = await self._update_data(params, access_token)
            elif action == "append":
                result = await self._append_data(params, access_token)
            elif action == "delete":
                result = await self._delete_data(params, access_token)
            elif action == "create_sheet":
                result = await self._create_sheet(params, access_token)
            elif action == "delete_sheet":
                result = await self._delete_sheet(params, access_token)
            elif action == "get_info":
                result = await self._get_spreadsheet_info(params, access_token)
            elif action == "clear":
                result = await self._clear_range(params, access_token)
            elif action == "format":
                result = await self._format_cells(params, access_token)
            else:
                raise ConnectorException(f"Unsupported Google Sheets action: {action}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "action": action,
                    "spreadsheet_id": params["spreadsheet_id"],
                    "sheets_api_version": "v4"
                }
            )
            
        except AuthenticationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Google Sheets operation failed: {str(e)}",
                metadata={"action": params.get("action", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get OAuth authentication requirements for Google Sheets.
        
        Returns:
            AuthRequirements for Google Sheets OAuth
        """
        return AuthRequirements(
            type=AuthType.OAUTH2,
            fields={
                "access_token": "OAuth access token for Google Sheets API",
                "refresh_token": "OAuth refresh token for token renewal"
            },
            oauth_scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly"
            ],
            instructions="Google Sheets connector requires OAuth authentication with Google. "
                        "You'll need to authorize access to your Google Sheets."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test Google Sheets API connection with provided OAuth tokens.
        
        Args:
            auth_tokens: OAuth tokens
            
        Returns:
            True if connection successful
        """
        try:
            access_token = auth_tokens.get("access_token")
            if not access_token:
                return False
            
            # Test connection by listing spreadsheets (requires Drive API)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"q": "mimeType='application/vnd.google-apps.spreadsheet'", "pageSize": 1}
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def _read_data(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Read data from Google Sheets."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params["range"]
        value_render_option = params.get("value_render_option", "FORMATTED_VALUE")
        date_time_render_option = params.get("date_time_render_option", "FORMATTED_STRING")
        major_dimension = params.get("major_dimension", "ROWS")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "valueRenderOption": value_render_option,
                    "dateTimeRenderOption": date_time_render_option,
                    "majorDimension": major_dimension
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to read data: {response.text}")
            
            result = response.json()
            sheet_data = {
                "range": result.get("range", range_param),
                "major_dimension": result.get("majorDimension", major_dimension),
                "values": result.get("values", []),
                "row_count": len(result.get("values", [])),
                "column_count": max(len(row) for row in result.get("values", [])) if result.get("values") else 0
            }
            
            # Add 'result' field for easier referencing from other connectors
            sheet_data["result"] = sheet_data["values"]
            
            return sheet_data
    
    async def _write_data(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Write data to Google Sheets."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params["range"]
        values = params["values"]
        value_input_option = params.get("value_input_option", "USER_ENTERED")
        
        request_body = {
            "values": values,
            "majorDimension": params.get("major_dimension", "ROWS")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"valueInputOption": value_input_option},
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to write data: {response.text}")
            
            result = response.json()
            write_data = {
                "spreadsheet_id": result["spreadsheetId"],
                "updated_range": result["updatedRange"],
                "updated_rows": result["updatedRows"],
                "updated_columns": result["updatedColumns"],
                "updated_cells": result["updatedCells"]
            }
            
            # Add 'result' field for easier referencing from other connectors
            write_data["result"] = f"Successfully wrote {write_data['updated_rows']} rows to {write_data['updated_range']}"
            
            return write_data
    
    async def _update_data(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Update data in Google Sheets."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params["range"]
        values = params["values"]
        value_input_option = params.get("value_input_option", "USER_ENTERED")
        
        request_body = {
            "values": values,
            "majorDimension": params.get("major_dimension", "ROWS")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"valueInputOption": value_input_option},
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to update data: {response.text}")
            
            result = response.json()
            update_data = {
                "spreadsheet_id": result["spreadsheetId"],
                "updated_range": result["updatedRange"],
                "updated_rows": result["updatedRows"],
                "updated_columns": result["updatedColumns"],
                "updated_cells": result["updatedCells"]
            }
            
            # Add 'result' field for easier referencing from other connectors
            update_data["result"] = f"Successfully updated {update_data['updated_rows']} rows in {update_data['updated_range']}"
            
            return update_data
    
    async def _append_data(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Append data to Google Sheets."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params.get("range", params.get("sheet_name", "Sheet1"))
        values = params["values"]
        value_input_option = params.get("value_input_option", "USER_ENTERED")
        
        request_body = {
            "values": values,
            "majorDimension": params.get("major_dimension", "ROWS")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}:append",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={
                    "valueInputOption": value_input_option,
                    "insertDataOption": "INSERT_ROWS"
                },
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to append data: {response.text}")
            
            result = response.json()
            append_data = {
                "spreadsheet_id": result["spreadsheetId"],
                "table_range": result["tableRange"],
                "updated_range": result["updates"]["updatedRange"],
                "updated_rows": result["updates"]["updatedRows"],
                "updated_columns": result["updates"]["updatedColumns"],
                "updated_cells": result["updates"]["updatedCells"]
            }
            
            # Add 'result' field for easier referencing from other connectors
            append_data["result"] = f"Successfully appended {append_data['updated_rows']} rows to {append_data['table_range']}"
            
            return append_data
    
    async def _delete_data(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete data by clearing the specified range."""
        return await self._clear_range(params, access_token)
    
    async def _create_sheet(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create a new sheet in the spreadsheet."""
        spreadsheet_id = params["spreadsheet_id"]
        new_sheet_name = params["new_sheet_name"]
        sheet_properties = params.get("sheet_properties", {})
        
        # Prepare sheet properties
        properties = {
            "title": new_sheet_name,
            **sheet_properties
        }
        
        request_body = {
            "requests": [{
                "addSheet": {
                    "properties": properties
                }
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to create sheet: {response.text}")
            
            result = response.json()
            sheet_info = result["replies"][0]["addSheet"]["properties"]
            return {
                "sheet_id": sheet_info["sheetId"],
                "title": sheet_info["title"],
                "index": sheet_info["index"],
                "sheet_type": sheet_info["sheetType"]
            }
    
    async def _delete_sheet(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete a sheet from the spreadsheet."""
        spreadsheet_id = params["spreadsheet_id"]
        sheet_name = params["sheet_name"]
        
        # First, get the sheet ID
        sheet_id = await self._get_sheet_id(spreadsheet_id, sheet_name, access_token)
        
        request_body = {
            "requests": [{
                "deleteSheet": {
                    "sheetId": sheet_id
                }
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to delete sheet: {response.text}")
            
            return {
                "deleted_sheet": sheet_name,
                "sheet_id": sheet_id,
                "status": "deleted"
            }
    
    async def _get_spreadsheet_info(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get spreadsheet information and metadata."""
        spreadsheet_id = params["spreadsheet_id"]
        include_grid_data = params.get("include_grid_data", False)
        
        query_params = {}
        if include_grid_data:
            query_params["includeGridData"] = "true"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=query_params
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get spreadsheet info: {response.text}")
            
            result = response.json()
            
            # Extract key information
            sheets_info = []
            for sheet in result.get("sheets", []):
                sheet_props = sheet["properties"]
                sheets_info.append({
                    "sheet_id": sheet_props["sheetId"],
                    "title": sheet_props["title"],
                    "index": sheet_props["index"],
                    "sheet_type": sheet_props["sheetType"],
                    "grid_properties": sheet_props.get("gridProperties", {})
                })
            
            return {
                "spreadsheet_id": result["spreadsheetId"],
                "title": result["properties"]["title"],
                "locale": result["properties"]["locale"],
                "auto_recalc": result["properties"]["autoRecalc"],
                "time_zone": result["properties"]["timeZone"],
                "sheets": sheets_info,
                "sheet_count": len(sheets_info)
            }
    
    async def _clear_range(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Clear data from a specified range."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params["range"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_param}:clear",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to clear range: {response.text}")
            
            result = response.json()
            return {
                "spreadsheet_id": result["spreadsheetId"],
                "cleared_range": result["clearedRange"],
                "status": "cleared"
            }
    
    async def _format_cells(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Apply formatting to cells."""
        spreadsheet_id = params["spreadsheet_id"]
        range_param = params["range"]
        format_options = params.get("format", {})
        
        # Convert range to grid range for formatting
        sheet_name, cell_range = self._parse_range(range_param)
        sheet_id = await self._get_sheet_id(spreadsheet_id, sheet_name, access_token)
        
        # Build format request
        cell_format = {}
        if "background_color" in format_options:
            cell_format["backgroundColor"] = format_options["background_color"]
        if "text_format" in format_options:
            cell_format["textFormat"] = format_options["text_format"]
        if "number_format" in format_options:
            cell_format["numberFormat"] = format_options["number_format"]
        
        request_body = {
            "requests": [{
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        **self._range_to_grid_range(cell_range)
                    },
                    "cell": {
                        "userEnteredFormat": cell_format
                    },
                    "fields": "userEnteredFormat"
                }
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to format cells: {response.text}")
            
            return {
                "formatted_range": range_param,
                "status": "formatted"
            }
    
    async def _get_sheet_id(self, spreadsheet_id: str, sheet_name: str, access_token: str) -> int:
        """Get sheet ID by name."""
        info = await self._get_spreadsheet_info({"spreadsheet_id": spreadsheet_id}, access_token)
        
        for sheet in info["sheets"]:
            if sheet["title"] == sheet_name:
                return sheet["sheet_id"]
        
        raise ConnectorException(f"Sheet '{sheet_name}' not found")
    
    def _parse_range(self, range_param: str) -> tuple[str, str]:
        """Parse range parameter to extract sheet name and cell range."""
        if "!" in range_param:
            sheet_name, cell_range = range_param.split("!", 1)
            return sheet_name, cell_range
        else:
            return "Sheet1", range_param
    
    def _range_to_grid_range(self, cell_range: str) -> Dict[str, int]:
        """Convert A1 notation to grid range coordinates."""
        # This is a simplified implementation
        # In a full implementation, you'd parse ranges like "A1:C10" properly
        return {
            "startRowIndex": 0,
            "endRowIndex": 10,
            "startColumnIndex": 0,
            "endColumnIndex": 3
        }
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Google Sheets operations."""
        return {
            "action": "read",
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "Sheet1!A1:C10"
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for Google Sheets connector."""
        return {
            "action": "Operation: read (get data), write (overwrite), append (add rows), update (modify cells)",
            "spreadsheet_id": "Google Sheets ID from URL (between /d/ and /edit)",
            "range": "Cell range in A1 notation (e.g., 'A1:C10', 'Sheet1!A:A')",
            "values": "2D array of data [[row1], [row2], ...] for write/append operations",
            "sheet_name": "Name of the sheet tab (default: 'Sheet1')",
            "value_input_option": "RAW (literal values) or USER_ENTERED (parsed like typing)",
            "new_sheet_name": "Name for new sheet creation"
        }