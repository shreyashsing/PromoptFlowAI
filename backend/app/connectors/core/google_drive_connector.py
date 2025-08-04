"""
Google Drive Connector - OAuth-based file and folder operations.
"""
import json
import base64
from typing import Dict, Any, List, Optional, Union
import httpx
from urllib.parse import quote

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException, ValidationException


class GoogleDriveConnector(BaseConnector):
    """
    Google Drive Connector for file and folder operations using OAuth authentication.
    
    Supports comprehensive file operations: upload, download, create, delete, move, copy,
    share, search, and folder management with Google Drive API v3.
    """
    
    def _get_connector_name(self) -> str:
        return "google_drive"
    
    def _get_category(self) -> str:
        return "data_sources"
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Google Drive action to perform",
                    "enum": [
                        "upload", "download", "create_folder", "delete", "move", "copy", 
                        "share", "search", "get_info", "list_files", "create_from_text",
                        "update_file", "get_permissions", "update_permissions"
                    ],
                    "default": "list_files"
                },
                # File/Folder identification
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file or folder ID"
                },
                "file_name": {
                    "type": "string",
                    "description": "Name for the file or folder"
                },
                "parent_folder_id": {
                    "type": "string",
                    "description": "Parent folder ID (use 'root' for root directory)",
                    "default": "root"
                },
                # File content operations
                "file_content": {
                    "type": "string",
                    "description": "Base64 encoded file content for upload operations"
                },
                "text_content": {
                    "type": "string",
                    "description": "Text content for creating text files"
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type of the file",
                    "default": "application/octet-stream"
                },
                # Search and listing
                "query": {
                    "type": "string",
                    "description": "Search query using Google Drive search syntax"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                },
                "order_by": {
                    "type": "string",
                    "description": "Sort order for results (field name optionally followed by 'desc')",
                    "default": "modifiedTime desc"
                },
                # File operations
                "new_parent_id": {
                    "type": "string",
                    "description": "New parent folder ID for move operations"
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for copy or rename operations"
                },
                # Sharing and permissions
                "share_type": {
                    "type": "string",
                    "description": "Type of sharing permission",
                    "enum": ["user", "group", "domain", "anyone"],
                    "default": "anyone"
                },
                "share_role": {
                    "type": "string",
                    "description": "Role for sharing",
                    "enum": ["owner", "organizer", "fileOrganizer", "writer", "commenter", "reader"],
                    "default": "reader"
                },
                "share_email": {
                    "type": "string",
                    "description": "Email address for user/group sharing"
                },
                "share_domain": {
                    "type": "string",
                    "description": "Domain for domain sharing"
                },
                "send_notification": {
                    "type": "boolean",
                    "description": "Send notification email when sharing",
                    "default": True
                },
                "share_message": {
                    "type": "string",
                    "description": "Custom message for sharing notification"
                },
                # File properties
                "description": {
                    "type": "string",
                    "description": "File description"
                },
                "starred": {
                    "type": "boolean",
                    "description": "Whether to star the file"
                },
                # Download options
                "export_format": {
                    "type": "string",
                    "description": "Export format for Google Workspace files",
                    "enum": [
                        "application/pdf", "text/html", "text/plain", "application/rtf",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.oasis.opendocument.text", "text/csv",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.oasis.opendocument.spreadsheet",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "application/vnd.oasis.opendocument.presentation", "image/jpeg", "image/png", "image/svg+xml"
                    ]
                },
                # Advanced options
                "include_items_from_all_drives": {
                    "type": "boolean",
                    "description": "Include items from all drives (shared drives)",
                    "default": True
                },
                "supports_all_drives": {
                    "type": "boolean",
                    "description": "Support all drives in operations",
                    "default": True
                },
                "fields": {
                    "type": "string",
                    "description": "Specific fields to return (comma-separated)",
                    "default": "id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink"
                },
                "convert_to_google_docs": {
                    "type": "boolean",
                    "description": "Convert uploaded files to Google Docs format when possible",
                    "default": False
                }
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"enum": ["download", "delete", "get_info", "share", "get_permissions", "update_permissions"]}}},
                    "then": {"required": ["file_id"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["upload"]}}},
                    "then": {"required": ["file_name", "file_content"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["create_from_text"]}}},
                    "then": {"required": ["file_name", "text_content"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["create_folder"]}}},
                    "then": {"required": ["file_name"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["move"]}}},
                    "then": {"required": ["file_id", "new_parent_id"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["copy"]}}},
                    "then": {"required": ["file_id", "new_name"]}
                },
                {
                    "if": {"properties": {"action": {"enum": ["search"]}}},
                    "then": {"required": ["query"]}
                },
                {
                    "if": {"properties": {"action": {"const": "share"}, "share_type": {"enum": ["user", "group"]}}},
                    "then": {"required": ["share_email"]}
                },
                {
                    "if": {"properties": {"action": {"const": "share"}, "share_type": {"const": "domain"}}},
                    "then": {"required": ["share_domain"]}
                }
            ]
        }
    
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute Google Drive operation with the provided parameters.
        
        Args:
            params: Google Drive operation parameters
            context: Execution context with OAuth tokens
            
        Returns:
            ConnectorResult with operation result or error
        """
        try:
            action = params["action"]
            access_token = context.auth_tokens.get("access_token")
            
            if not access_token:
                raise AuthenticationException("Google Drive access token not found")
            
            # Route to appropriate action handler
            if action == "upload":
                result = await self._upload_file(params, access_token)
            elif action == "download":
                result = await self._download_file(params, access_token)
            elif action == "create_folder":
                result = await self._create_folder(params, access_token)
            elif action == "delete":
                result = await self._delete_file(params, access_token)
            elif action == "move":
                result = await self._move_file(params, access_token)
            elif action == "copy":
                result = await self._copy_file(params, access_token)
            elif action == "share":
                result = await self._share_file(params, access_token)
            elif action == "search":
                result = await self._search_files(params, access_token)
            elif action == "get_info":
                result = await self._get_file_info(params, access_token)
            elif action == "list_files":
                result = await self._list_files(params, access_token)
            elif action == "create_from_text":
                result = await self._create_from_text(params, access_token)
            elif action == "update_file":
                result = await self._update_file(params, access_token)
            elif action == "get_permissions":
                result = await self._get_permissions(params, access_token)
            elif action == "update_permissions":
                result = await self._update_permissions(params, access_token)
            else:
                raise ConnectorException(f"Unsupported Google Drive action: {action}")
            
            return ConnectorResult(
                success=True,
                data=result,
                metadata={
                    "action": action,
                    "drive_api_version": "v3",
                    "file_id": params.get("file_id")
                }
            )
            
        except AuthenticationException:
            raise
        except Exception as e:
            return ConnectorResult(
                success=False,
                data=None,
                error=f"Google Drive operation failed: {str(e)}",
                metadata={"action": params.get("action", "unknown")}
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get OAuth authentication requirements for Google Drive.
        
        Returns:
            AuthRequirements for Google Drive OAuth
        """
        return AuthRequirements(
            type=AuthType.OAUTH2,
            fields={
                "access_token": "OAuth access token for Google Drive API",
                "refresh_token": "OAuth refresh token for token renewal"
            },
            oauth_scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file"
            ],
            instructions="Google Drive connector requires OAuth authentication with Google. "
                        "You'll need to authorize access to your Google Drive files and folders."
        )
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test Google Drive API connection with provided OAuth tokens.
        
        Args:
            auth_tokens: OAuth tokens
            
        Returns:
            True if connection successful
        """
        try:
            access_token = auth_tokens.get("access_token")
            if not access_token:
                return False
            
            # Test connection by getting user info
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/about",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"fields": "user"}
                )
                return response.status_code == 200
                
        except Exception:
            return False    

    async def _upload_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Upload a file to Google Drive."""
        file_name = params["file_name"]
        file_content = params["file_content"]
        parent_folder_id = params.get("parent_folder_id", "root")
        mime_type = params.get("mime_type", "application/octet-stream")
        description = params.get("description", "")
        convert_to_google_docs = params.get("convert_to_google_docs", False)
        
        # Decode base64 content
        try:
            content_bytes = base64.b64decode(file_content)
        except Exception as e:
            raise ConnectorException(f"Invalid base64 file content: {str(e)}")
        
        # Prepare metadata
        metadata = {
            "name": file_name,
            "parents": [parent_folder_id] if parent_folder_id != "root" else None
        }
        
        if description:
            metadata["description"] = description
        
        # Use resumable upload for larger files
        if len(content_bytes) > 5 * 1024 * 1024:  # 5MB threshold
            return await self._resumable_upload(metadata, content_bytes, mime_type, access_token, convert_to_google_docs)
        else:
            return await self._simple_upload(metadata, content_bytes, mime_type, access_token, convert_to_google_docs)
    
    async def _simple_upload(self, metadata: Dict[str, Any], content_bytes: bytes, mime_type: str, access_token: str, convert_to_google_docs: bool) -> Dict[str, Any]:
        """Simple upload for smaller files."""
        # Multipart upload
        boundary = "upload_boundary_123456789"
        
        # Build multipart body
        body_parts = [
            f'--{boundary}',
            'Content-Type: application/json; charset=UTF-8',
            '',
            json.dumps(metadata),
            f'--{boundary}',
            f'Content-Type: {mime_type}',
            '',
        ]
        
        body_text = '\r\n'.join(body_parts) + '\r\n'
        body_bytes = body_text.encode('utf-8') + content_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')
        
        params = {
            "uploadType": "multipart",
            "supportsAllDrives": "true"
        }
        
        if convert_to_google_docs:
            # Try to convert to appropriate Google format
            if mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword", "text/plain"]:
                params["convert"] = "true"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}"
                },
                params=params,
                content=body_bytes
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to upload file: {response.text}")
            
            result = response.json()
            return {
                "file_id": result["id"],
                "name": result["name"],
                "mime_type": result["mimeType"],
                "size": result.get("size"),
                "web_view_link": result.get("webViewLink"),
                "web_content_link": result.get("webContentLink"),
                "created_time": result.get("createdTime"),
                "result": f"Successfully uploaded file '{result['name']}' with ID {result['id']}"
            }
    
    async def _resumable_upload(self, metadata: Dict[str, Any], content_bytes: bytes, mime_type: str, access_token: str, convert_to_google_docs: bool) -> Dict[str, Any]:
        """Resumable upload for larger files."""
        # Start resumable upload session
        params = {
            "uploadType": "resumable",
            "supportsAllDrives": "true"
        }
        
        if convert_to_google_docs:
            params["convert"] = "true"
        
        async with httpx.AsyncClient() as client:
            # Initiate upload
            init_response = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": mime_type,
                    "X-Upload-Content-Length": str(len(content_bytes))
                },
                params=params,
                json=metadata
            )
            
            if init_response.status_code != 200:
                raise ConnectorException(f"Failed to initiate upload: {init_response.text}")
            
            upload_url = init_response.headers.get("Location")
            if not upload_url:
                raise ConnectorException("No upload URL received")
            
            # Upload content in chunks
            chunk_size = 256 * 1024  # 256KB chunks
            total_size = len(content_bytes)
            
            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk = content_bytes[start:end]
                
                upload_response = await client.put(
                    upload_url,
                    headers={
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end-1}/{total_size}"
                    },
                    content=chunk
                )
                
                if upload_response.status_code == 200:
                    # Upload complete
                    result = upload_response.json()
                    return {
                        "file_id": result["id"],
                        "name": result["name"],
                        "mime_type": result["mimeType"],
                        "size": result.get("size"),
                        "web_view_link": result.get("webViewLink"),
                        "web_content_link": result.get("webContentLink"),
                        "created_time": result.get("createdTime"),
                        "result": f"Successfully uploaded file '{result['name']}' with ID {result['id']}"
                    }
                elif upload_response.status_code != 308:
                    # 308 means continue, anything else is an error
                    raise ConnectorException(f"Upload failed: {upload_response.text}")
            
            raise ConnectorException("Upload completed but no final response received")
    
    async def _download_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Download a file from Google Drive."""
        file_id = params["file_id"]
        export_format = params.get("export_format")
        
        # First get file info to determine if it's a Google Workspace file
        file_info = await self._get_file_info({"file_id": file_id}, access_token)
        mime_type = file_info["mime_type"]
        
        async with httpx.AsyncClient() as client:
            if mime_type.startswith("application/vnd.google-apps."):
                # Google Workspace file - needs export
                if not export_format:
                    # Determine default export format based on file type
                    if "document" in mime_type:
                        export_format = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif "spreadsheet" in mime_type:
                        export_format = "text/csv"
                    elif "presentation" in mime_type:
                        export_format = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    elif "drawing" in mime_type:
                        export_format = "image/png"
                    else:
                        export_format = "application/pdf"
                
                response = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"mimeType": export_format}
                )
            else:
                # Regular file - direct download
                response = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"alt": "media", "supportsAllDrives": "true"}
                )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to download file: {response.text}")
            
            # Encode content as base64
            content_base64 = base64.b64encode(response.content).decode('utf-8')
            
            return {
                "file_id": file_id,
                "name": file_info["name"],
                "mime_type": export_format if export_format else mime_type,
                "size": len(response.content),
                "content": content_base64,
                "result": f"Successfully downloaded file '{file_info['name']}'"
            }
    
    async def _create_folder(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create a new folder in Google Drive."""
        folder_name = params["file_name"]
        parent_folder_id = params.get("parent_folder_id", "root")
        description = params.get("description", "")
        
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id] if parent_folder_id != "root" else None
        }
        
        if description:
            metadata["description"] = description
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.googleapis.com/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"supportsAllDrives": "true"},
                json=metadata
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to create folder: {response.text}")
            
            result = response.json()
            return {
                "folder_id": result["id"],
                "name": result["name"],
                "mime_type": result["mimeType"],
                "web_view_link": result.get("webViewLink"),
                "created_time": result.get("createdTime"),
                "result": f"Successfully created folder '{result['name']}' with ID {result['id']}"
            }
    
    async def _delete_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Delete a file or folder from Google Drive."""
        file_id = params["file_id"]
        
        # Get file info before deletion
        file_info = await self._get_file_info({"file_id": file_id}, access_token)
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"supportsAllDrives": "true"}
            )
            
            if response.status_code != 204:
                raise ConnectorException(f"Failed to delete file: {response.text}")
            
            return {
                "deleted_file_id": file_id,
                "deleted_name": file_info["name"],
                "status": "deleted",
                "result": f"Successfully deleted '{file_info['name']}'"
            }
    
    async def _move_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Move a file to a different folder."""
        file_id = params["file_id"]
        new_parent_id = params["new_parent_id"]
        
        # Get current parents
        file_info = await self._get_file_info({"file_id": file_id, "fields": "parents,name"}, access_token)
        current_parents = file_info.get("parents", [])
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "addParents": new_parent_id,
                    "removeParents": ",".join(current_parents),
                    "supportsAllDrives": "true"
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to move file: {response.text}")
            
            result = response.json()
            return {
                "file_id": result["id"],
                "name": result["name"],
                "new_parents": result.get("parents", []),
                "result": f"Successfully moved '{result['name']}' to new location"
            }
    
    async def _copy_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Copy a file in Google Drive."""
        file_id = params["file_id"]
        new_name = params["new_name"]
        parent_folder_id = params.get("parent_folder_id")
        
        metadata = {"name": new_name}
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/copy",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"supportsAllDrives": "true"},
                json=metadata
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to copy file: {response.text}")
            
            result = response.json()
            return {
                "new_file_id": result["id"],
                "name": result["name"],
                "mime_type": result["mimeType"],
                "web_view_link": result.get("webViewLink"),
                "created_time": result.get("createdTime"),
                "result": f"Successfully copied file as '{result['name']}' with ID {result['id']}"
            }
    
    async def _share_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Share a file or folder with specified permissions."""
        file_id = params["file_id"]
        share_type = params["share_type"]
        share_role = params["share_role"]
        share_email = params.get("share_email")
        share_domain = params.get("share_domain")
        send_notification = params.get("send_notification", True)
        share_message = params.get("share_message")
        
        permission = {
            "type": share_type,
            "role": share_role
        }
        
        if share_type in ["user", "group"] and share_email:
            permission["emailAddress"] = share_email
        elif share_type == "domain" and share_domain:
            permission["domain"] = share_domain
        
        request_params = {
            "supportsAllDrives": "true",
            "sendNotificationEmail": str(send_notification).lower()
        }
        
        if share_message:
            request_params["emailMessage"] = share_message
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params=request_params,
                json=permission
            )
            
            if response.status_code not in [200, 201]:
                raise ConnectorException(f"Failed to share file: {response.text}")
            
            result = response.json()
            return {
                "permission_id": result["id"],
                "type": result["type"],
                "role": result["role"],
                "email_address": result.get("emailAddress"),
                "domain": result.get("domain"),
                "result": f"Successfully shared file with {share_type} as {share_role}"
            }
    
    async def _search_files(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Search for files in Google Drive."""
        query = params["query"]
        max_results = params.get("max_results", 100)
        order_by = params.get("order_by", "modifiedTime desc")
        fields = params.get("fields", "id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink")
        include_all_drives = params.get("include_items_from_all_drives", True)
        
        search_params = {
            "q": query,
            "pageSize": min(max_results, 1000),
            "orderBy": order_by,
            "fields": f"files({fields}),nextPageToken",
            "includeItemsFromAllDrives": str(include_all_drives).lower(),
            "supportsAllDrives": "true"
        }
        
        all_files = []
        next_page_token = None
        
        async with httpx.AsyncClient() as client:
            while len(all_files) < max_results:
                if next_page_token:
                    search_params["pageToken"] = next_page_token
                
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=search_params
                )
                
                if response.status_code != 200:
                    raise ConnectorException(f"Failed to search files: {response.text}")
                
                result = response.json()
                files = result.get("files", [])
                all_files.extend(files)
                
                next_page_token = result.get("nextPageToken")
                if not next_page_token or len(all_files) >= max_results:
                    break
        
        # Limit to requested number of results
        all_files = all_files[:max_results]
        
        return {
            "query": query,
            "total_found": len(all_files),
            "files": all_files,
            "result": f"Found {len(all_files)} files matching query: {query}"
        }
    
    async def _get_file_info(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get detailed information about a file or folder."""
        file_id = params["file_id"]
        fields = params.get("fields", "id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink,description,starred,owners,permissions")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "fields": fields,
                    "supportsAllDrives": "true"
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get file info: {response.text}")
            
            result = response.json()
            
            # Add computed fields
            file_info = dict(result)
            file_info["is_folder"] = result.get("mimeType") == "application/vnd.google-apps.folder"
            file_info["is_google_workspace"] = result.get("mimeType", "").startswith("application/vnd.google-apps.")
            file_info["result"] = f"Retrieved info for '{result.get('name', 'Unknown')}'"
            
            return file_info
    
    async def _list_files(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """List files in a folder or root directory."""
        parent_folder_id = params.get("parent_folder_id", "root")
        max_results = params.get("max_results", 100)
        order_by = params.get("order_by", "modifiedTime desc")
        fields = params.get("fields", "id,name,mimeType,size,createdTime,modifiedTime,webViewLink")
        include_all_drives = params.get("include_items_from_all_drives", True)
        
        # Build query to list files in specific folder
        query = f"'{parent_folder_id}' in parents and trashed = false"
        
        list_params = {
            "q": query,
            "pageSize": min(max_results, 1000),
            "orderBy": order_by,
            "fields": f"files({fields}),nextPageToken",
            "includeItemsFromAllDrives": str(include_all_drives).lower(),
            "supportsAllDrives": "true"
        }
        
        all_files = []
        next_page_token = None
        
        async with httpx.AsyncClient() as client:
            while len(all_files) < max_results:
                if next_page_token:
                    list_params["pageToken"] = next_page_token
                
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=list_params
                )
                
                if response.status_code != 200:
                    raise ConnectorException(f"Failed to list files: {response.text}")
                
                result = response.json()
                files = result.get("files", [])
                all_files.extend(files)
                
                next_page_token = result.get("nextPageToken")
                if not next_page_token or len(all_files) >= max_results:
                    break
        
        # Limit to requested number of results
        all_files = all_files[:max_results]
        
        # Separate folders and files
        folders = [f for f in all_files if f.get("mimeType") == "application/vnd.google-apps.folder"]
        files = [f for f in all_files if f.get("mimeType") != "application/vnd.google-apps.folder"]
        
        return {
            "parent_folder_id": parent_folder_id,
            "total_items": len(all_files),
            "folder_count": len(folders),
            "file_count": len(files),
            "folders": folders,
            "files": files,
            "all_items": all_files,
            "result": f"Listed {len(all_files)} items from folder {parent_folder_id}"
        }
    
    async def _create_from_text(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create a text file from provided content."""
        file_name = params["file_name"]
        text_content = params["text_content"]
        parent_folder_id = params.get("parent_folder_id", "root")
        mime_type = params.get("mime_type", "text/plain")
        description = params.get("description", "")
        
        # Convert text to base64 for upload
        content_bytes = text_content.encode('utf-8')
        file_content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # Use the upload method
        upload_params = {
            "file_name": file_name,
            "file_content": file_content_base64,
            "parent_folder_id": parent_folder_id,
            "mime_type": mime_type,
            "description": description
        }
        
        return await self._upload_file(upload_params, access_token)
    
    async def _update_file(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Update file metadata or content."""
        file_id = params["file_id"]
        new_name = params.get("new_name")
        description = params.get("description")
        starred = params.get("starred")
        file_content = params.get("file_content")
        mime_type = params.get("mime_type")
        
        # Prepare metadata updates
        metadata = {}
        if new_name:
            metadata["name"] = new_name
        if description is not None:
            metadata["description"] = description
        if starred is not None:
            metadata["starred"] = starred
        
        if file_content:
            # Update with new content (resumable upload)
            content_bytes = base64.b64decode(file_content)
            return await self._update_file_content(file_id, metadata, content_bytes, mime_type, access_token)
        else:
            # Update only metadata
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    params={"supportsAllDrives": "true"},
                    json=metadata
                )
                
                if response.status_code != 200:
                    raise ConnectorException(f"Failed to update file: {response.text}")
                
                result = response.json()
                return {
                    "file_id": result["id"],
                    "name": result["name"],
                    "modified_time": result.get("modifiedTime"),
                    "result": f"Successfully updated file '{result['name']}'"
                }
    
    async def _update_file_content(self, file_id: str, metadata: Dict[str, Any], content_bytes: bytes, mime_type: str, access_token: str) -> Dict[str, Any]:
        """Update file content using resumable upload."""
        # Start resumable upload session for update
        async with httpx.AsyncClient() as client:
            init_response = await client.patch(
                f"https://www.googleapis.com/upload/drive/v3/files/{file_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": mime_type or "application/octet-stream",
                    "X-Upload-Content-Length": str(len(content_bytes))
                },
                params={
                    "uploadType": "resumable",
                    "supportsAllDrives": "true"
                },
                json=metadata
            )
            
            if init_response.status_code != 200:
                raise ConnectorException(f"Failed to initiate content update: {init_response.text}")
            
            upload_url = init_response.headers.get("Location")
            if not upload_url:
                raise ConnectorException("No upload URL received for content update")
            
            # Upload new content
            upload_response = await client.put(
                upload_url,
                headers={
                    "Content-Length": str(len(content_bytes))
                },
                content=content_bytes
            )
            
            if upload_response.status_code != 200:
                raise ConnectorException(f"Failed to update file content: {upload_response.text}")
            
            result = upload_response.json()
            return {
                "file_id": result["id"],
                "name": result["name"],
                "mime_type": result["mimeType"],
                "size": result.get("size"),
                "modified_time": result.get("modifiedTime"),
                "result": f"Successfully updated content for '{result['name']}'"
            }
    
    async def _get_permissions(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Get permissions for a file or folder."""
        file_id = params["file_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "supportsAllDrives": "true",
                    "fields": "permissions(id,type,role,emailAddress,domain,displayName)"
                }
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to get permissions: {response.text}")
            
            result = response.json()
            permissions = result.get("permissions", [])
            
            return {
                "file_id": file_id,
                "permission_count": len(permissions),
                "permissions": permissions,
                "result": f"Retrieved {len(permissions)} permissions for file"
            }
    
    async def _update_permissions(self, params: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Update existing permissions for a file or folder."""
        file_id = params["file_id"]
        permission_id = params.get("permission_id")
        new_role = params.get("share_role")
        
        if not permission_id or not new_role:
            raise ConnectorException("permission_id and share_role are required for updating permissions")
        
        permission_update = {"role": new_role}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions/{permission_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"supportsAllDrives": "true"},
                json=permission_update
            )
            
            if response.status_code != 200:
                raise ConnectorException(f"Failed to update permission: {response.text}")
            
            result = response.json()
            return {
                "permission_id": result["id"],
                "type": result["type"],
                "role": result["role"],
                "email_address": result.get("emailAddress"),
                "result": f"Successfully updated permission to {new_role}"
            }
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Google Drive operations."""
        return {
            "action": "list_files",
            "parent_folder_id": "root",
            "max_results": 50
        }
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """Get parameter hints for Google Drive connector."""
        return {
            "action": "Operation: upload, download, create_folder, delete, move, copy, share, search, list_files, etc.",
            "file_id": "Google Drive file or folder ID (from URL or API response)",
            "file_name": "Name for the file or folder",
            "parent_folder_id": "Parent folder ID ('root' for root directory)",
            "file_content": "Base64 encoded file content for upload operations",
            "text_content": "Plain text content for creating text files",
            "query": "Search query using Google Drive syntax (e.g., 'name contains \"report\"')",
            "share_type": "Sharing type: user, group, domain, or anyone",
            "share_role": "Permission level: owner, writer, commenter, or reader",
            "share_email": "Email address for user/group sharing",
            "export_format": "Export format for Google Workspace files (PDF, DOCX, etc.)"
        }