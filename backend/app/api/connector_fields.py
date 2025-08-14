"""
Dynamic Connector Fields API - Fetch real-time data for connector field dropdowns.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import logging

from app.core.auth import get_current_user
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connector-fields", tags=["connector-fields"])


class FieldDataRequest(BaseModel):
    connector_name: str
    field_name: str
    context: Optional[Dict[str, Any]] = None


class FieldOption(BaseModel):
    value: str
    label: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FieldDataResponse(BaseModel):
    success: bool
    options: List[FieldOption]
    error: Optional[str] = None
    cached: bool = False


@router.post("/fetch", response_model=FieldDataResponse)
async def fetch_field_data(
    request: FieldDataRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """Fetch dynamic field data for connector dropdowns."""
    try:
        # Get user's authentication tokens
        token_service = await get_auth_token_service(db)
        user_id = current_user["user_id"]
        
        # Route to appropriate field data fetcher
        if request.connector_name == "gmail_connector":
            return await _fetch_gmail_field_data(request, user_id, token_service)
        elif request.connector_name == "notion":
            return await _fetch_notion_field_data(request, user_id, token_service)
        elif request.connector_name == "google_sheets":
            return await _fetch_google_sheets_field_data(request, user_id, token_service)
        elif request.connector_name == "google_drive":
            return await _fetch_google_drive_field_data(request, user_id, token_service)
        elif request.connector_name == "youtube":
            return await _fetch_youtube_field_data(request, user_id, token_service)
        elif request.connector_name == "airtable":
            return await _fetch_airtable_field_data(request, user_id, token_service)
        elif request.connector_name == "perplexity":
            return await _fetch_perplexity_field_data(request, user_id, token_service)
        elif request.connector_name == "google_translate":
            # Google Translate doesn't have dynamic fields (just language codes)
            return FieldDataResponse(
                success=False,
                options=[],
                error="Google Translate uses static language codes, no dynamic fields available"
            )
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic fields not supported for {request.connector_name}"
            )
            
    except Exception as e:
        logger.error(f"Failed to fetch field data: {str(e)}")
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Failed to fetch field data: {str(e)}"
        )


async def _fetch_gmail_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Gmail-specific field data."""
    try:
        # Get OAuth token
        oauth_token = await token_service.get_token(user_id, "gmail_connector", AuthType.OAUTH2)
        if not oauth_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Gmail authentication required"
            )
        
        access_token = oauth_token["token_data"]["access_token"]
        
        if request.field_name == "label_ids":
            return await _fetch_gmail_labels(access_token)
        elif request.field_name == "message_id":
            return await _fetch_gmail_messages(access_token, request.context)
        elif request.field_name == "thread_id":
            return await _fetch_gmail_threads(access_token, request.context)
        elif request.field_name == "draft_id":
            return await _fetch_gmail_drafts(access_token)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Gmail field data fetch failed: {str(e)}"
        )


async def _fetch_gmail_labels(access_token: str) -> FieldDataResponse:
    """Fetch Gmail labels."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/labels",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Gmail labels"
            )
        
        data = response.json()
        labels = data.get("labels", [])
        
        options = []
        for label in labels:
            # Skip system labels that are not user-friendly
            if label["id"] in ["CHAT", "SENT", "INBOX", "IMPORTANT", "TRASH", "DRAFT", "SPAM"]:
                continue
                
            options.append(FieldOption(
                value=label["id"],
                label=label["name"],
                description=f"Type: {label.get('type', 'user')}",
                metadata={
                    "type": label.get("type"),
                    "messages_total": label.get("messagesTotal", 0),
                    "messages_unread": label.get("messagesUnread", 0)
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_gmail_messages(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch recent Gmail messages."""
    async with httpx.AsyncClient() as client:
        # Get recent messages
        params = {"maxResults": 20}
        if context and context.get("query"):
            params["q"] = context["query"]
            
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Gmail messages"
            )
        
        data = response.json()
        messages = data.get("messages", [])
        
        options = []
        # Get details for first 10 messages
        for msg in messages[:10]:
            msg_response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]}
            )
            
            if msg_response.status_code == 200:
                msg_data = msg_response.json()
                headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                
                subject = headers.get("Subject", "No Subject")[:50]
                from_addr = headers.get("From", "Unknown")[:30]
                
                options.append(FieldOption(
                    value=msg["id"],
                    label=f"{subject} - {from_addr}",
                    description=headers.get("Date", ""),
                    metadata={
                        "thread_id": msg_data.get("threadId"),
                        "snippet": msg_data.get("snippet", "")[:100]
                    }
                ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_gmail_threads(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch Gmail threads."""
    async with httpx.AsyncClient() as client:
        params = {"maxResults": 15}
        if context and context.get("query"):
            params["q"] = context["query"]
            
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/threads",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Gmail threads"
            )
        
        data = response.json()
        threads = data.get("threads", [])
        
        options = []
        for thread in threads[:10]:
            # Get thread details
            thread_response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "From"]}
            )
            
            if thread_response.status_code == 200:
                thread_data = thread_response.json()
                messages = thread_data.get("messages", [])
                if messages:
                    first_msg = messages[0]
                    headers = {h["name"]: h["value"] for h in first_msg.get("payload", {}).get("headers", [])}
                    
                    subject = headers.get("Subject", "No Subject")[:50]
                    from_addr = headers.get("From", "Unknown")[:30]
                    
                    options.append(FieldOption(
                        value=thread["id"],
                        label=f"{subject} - {from_addr}",
                        description=f"{len(messages)} messages",
                        metadata={
                            "message_count": len(messages),
                            "snippet": first_msg.get("snippet", "")[:100]
                        }
                    ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_gmail_drafts(access_token: str) -> FieldDataResponse:
    """Fetch Gmail drafts."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": 20}
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Gmail drafts"
            )
        
        data = response.json()
        drafts = data.get("drafts", [])
        
        options = []
        for draft in drafts[:15]:
            # Get draft details
            draft_response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "To"]}
            )
            
            if draft_response.status_code == 200:
                draft_data = draft_response.json()
                message = draft_data.get("message", {})
                headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
                
                subject = headers.get("Subject", "No Subject")[:50]
                to_addr = headers.get("To", "No Recipient")[:30]
                
                options.append(FieldOption(
                    value=draft["id"],
                    label=f"{subject} → {to_addr}",
                    description="Draft",
                    metadata={
                        "message_id": message.get("id"),
                        "snippet": message.get("snippet", "")[:100]
                    }
                ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_notion_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Notion-specific field data."""
    try:
        # Get API key token
        api_token = await token_service.get_token(user_id, "notion", AuthType.API_KEY)
        if not api_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Notion authentication required"
            )
        
        api_key = api_token["token_data"]["api_key"]
        
        if request.field_name == "database_id":
            return await _fetch_notion_databases(api_key)
        elif request.field_name == "page_id":
            return await _fetch_notion_pages(api_key, request.context)
        elif request.field_name == "user_id":
            return await _fetch_notion_users(api_key)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Notion field data fetch failed: {str(e)}"
        )


async def _fetch_notion_databases(api_key: str) -> FieldDataResponse:
    """Fetch Notion databases."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.notion.com/v1/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            },
            json={
                "filter": {"property": "object", "value": "database"},
                "page_size": 50
            }
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Notion databases"
            )
        
        data = response.json()
        databases = data.get("results", [])
        
        options = []
        for db in databases:
            title = ""
            if db.get("title"):
                title = "".join([t.get("plain_text", "") for t in db["title"]])
            
            options.append(FieldOption(
                value=db["id"],
                label=title or "Untitled Database",
                description=f"Created: {db.get('created_time', '')[:10]}",
                metadata={
                    "url": db.get("url"),
                    "properties_count": len(db.get("properties", {}))
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_notion_pages(api_key: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch Notion pages."""
    async with httpx.AsyncClient() as client:
        search_data = {
            "filter": {"property": "object", "value": "page"},
            "page_size": 50
        }
        
        if context and context.get("query"):
            search_data["query"] = context["query"]
        
        response = await client.post(
            "https://api.notion.com/v1/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            },
            json=search_data
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Notion pages"
            )
        
        data = response.json()
        pages = data.get("results", [])
        
        options = []
        for page in pages:
            title = ""
            if page.get("properties"):
                # Find title property
                for prop_name, prop_data in page["properties"].items():
                    if prop_data.get("type") == "title" and prop_data.get("title"):
                        title = "".join([t.get("plain_text", "") for t in prop_data["title"]])
                        break
            
            options.append(FieldOption(
                value=page["id"],
                label=title or "Untitled Page",
                description=f"Created: {page.get('created_time', '')[:10]}",
                metadata={
                    "url": page.get("url"),
                    "parent_type": page.get("parent", {}).get("type")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_notion_users(api_key: str) -> FieldDataResponse:
    """Fetch Notion users."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.notion.com/v1/users",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28"
            }
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Notion users"
            )
        
        data = response.json()
        users = data.get("results", [])
        
        options = []
        for user in users:
            name = user.get("name", "Unknown User")
            user_type = user.get("type", "person")
            
            options.append(FieldOption(
                value=user["id"],
                label=name,
                description=f"Type: {user_type}",
                metadata={
                    "type": user_type,
                    "avatar_url": user.get("avatar_url")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_google_sheets_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Google Sheets-specific field data."""
    try:
        # Get OAuth token
        oauth_token = await token_service.get_token(user_id, "google_sheets", AuthType.OAUTH2)
        if not oauth_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Google Sheets authentication required"
            )
        
        access_token = oauth_token["token_data"]["access_token"]
        
        if request.field_name == "spreadsheet_id":
            return await _fetch_google_spreadsheets(access_token)
        elif request.field_name == "sheet_name":
            return await _fetch_google_sheet_names(access_token, request.context)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Google Sheets field data fetch failed: {str(e)}"
        )


async def _fetch_google_spreadsheets(access_token: str) -> FieldDataResponse:
    """Fetch Google Spreadsheets from Drive."""
    async with httpx.AsyncClient() as client:
        try:
            # First, test token validity
            logger.info("Testing Google Drive API access...")
            test_response = await client.get(
                "https://www.googleapis.com/drive/v3/about",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "user"}
            )
            
            if test_response.status_code != 200:
                logger.error(f"Google Drive API access test failed: {test_response.status_code} - {test_response.text}")
                return FieldDataResponse(
                    success=False,
                    options=[],
                    error=f"Google Drive API access denied: {test_response.status_code}"
                )
            
            # Now fetch spreadsheets
            logger.info("Fetching Google Spreadsheets from Drive API...")
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": "mimeType='application/vnd.google-apps.spreadsheet'",
                    "pageSize": 50,
                    "fields": "files(id,name,createdTime,modifiedTime)"
                }
            )
            
            logger.info(f"Google Drive API response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Failed to fetch Google Spreadsheets: {response.status_code} - {error_text}")
                return FieldDataResponse(
                    success=False,
                    options=[],
                    error=f"Failed to fetch Google Spreadsheets: {response.status_code} - {error_text}"
                )
            
            data = response.json()
            files = data.get("files", [])
            logger.info(f"Found {len(files)} Google Spreadsheets")
            
            # If no files found, let's check if user has any files at all
            if len(files) == 0:
                logger.info("No spreadsheets found, checking for any files...")
                all_files_response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "pageSize": 5,
                        "fields": "files(id,name,mimeType)"
                    }
                )
                
                if all_files_response.status_code == 200:
                    all_files_data = all_files_response.json()
                    all_files = all_files_data.get("files", [])
                    logger.info(f"User has {len(all_files)} total files in Drive")
                    
                    if len(all_files) == 0:
                        return FieldDataResponse(
                            success=True,
                            options=[],
                            error="No files found in Google Drive. Please create some Google Sheets first."
                        )
                    else:
                        return FieldDataResponse(
                            success=True,
                            options=[],
                            error="No Google Sheets found in your Drive. Please create some Google Sheets first."
                        )
            
            options = []
            for file in files:
                options.append(FieldOption(
                    value=file["id"],
                    label=file["name"],
                    description=f"Modified: {file.get('modifiedTime', '')[:10]}",
                    metadata={
                        "created_time": file.get("createdTime"),
                        "modified_time": file.get("modifiedTime")
                    }
                ))
            
            return FieldDataResponse(
                success=True,
                options=options
            )
            
        except Exception as e:
            logger.error(f"Exception in _fetch_google_spreadsheets: {str(e)}")
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Error fetching Google Spreadsheets: {str(e)}"
            )


async def _fetch_google_sheet_names(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch sheet names from a specific spreadsheet."""
    if not context or not context.get("spreadsheet_id"):
        return FieldDataResponse(
            success=False,
            options=[],
            error="Spreadsheet ID required to fetch sheet names"
        )
    
    spreadsheet_id = context["spreadsheet_id"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "sheets(properties(sheetId,title,gridProperties))"}
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch sheet names"
            )
        
        data = response.json()
        sheets = data.get("sheets", [])
        
        options = []
        for sheet in sheets:
            props = sheet.get("properties", {})
            grid_props = props.get("gridProperties", {})
            
            options.append(FieldOption(
                value=props.get("title", ""),
                label=props.get("title", "Untitled Sheet"),
                description=f"Rows: {grid_props.get('rowCount', 0)}, Cols: {grid_props.get('columnCount', 0)}",
                metadata={
                    "sheet_id": props.get("sheetId"),
                    "row_count": grid_props.get("rowCount"),
                    "column_count": grid_props.get("columnCount")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_airtable_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Airtable-specific field data."""
    try:
        # Get API key token
        api_token = await token_service.get_token(user_id, "airtable", AuthType.API_KEY)
        if not api_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Airtable authentication required"
            )
        
        api_key = api_token["token_data"]["api_key"]
        
        if request.field_name == "base_id":
            return await _fetch_airtable_bases(api_key)
        elif request.field_name == "table_name":
            return await _fetch_airtable_tables(api_key, request.context)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Airtable field data fetch failed: {str(e)}"
        )


async def _fetch_airtable_bases(api_key: str) -> FieldDataResponse:
    """Fetch Airtable bases."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.airtable.com/v0/meta/bases",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Airtable bases"
            )
        
        data = response.json()
        bases = data.get("bases", [])
        
        options = []
        for base in bases:
            options.append(FieldOption(
                value=base["id"],
                label=base["name"],
                description=f"Permission: {base.get('permissionLevel', 'unknown')}",
                metadata={
                    "permission_level": base.get("permissionLevel")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_airtable_tables(api_key: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch Airtable tables from a specific base."""
    if not context or not context.get("base_id"):
        return FieldDataResponse(
            success=False,
            options=[],
            error="Base ID required to fetch tables"
        )
    
    base_id = context["base_id"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Airtable tables"
            )
        
        data = response.json()
        tables = data.get("tables", [])
        
        options = []
        for table in tables:
            options.append(FieldOption(
                value=table["name"],
                label=table["name"],
                description=f"Fields: {len(table.get('fields', []))}",
                metadata={
                    "table_id": table.get("id"),
                    "field_count": len(table.get("fields", []))
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_google_drive_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Google Drive-specific field data."""
    try:
        # Get OAuth token
        oauth_token = await token_service.get_token(user_id, "google_drive", AuthType.OAUTH2)
        if not oauth_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Google Drive authentication required"
            )
        
        access_token = oauth_token["token_data"]["access_token"]
        
        if request.field_name == "file_id":
            return await _fetch_google_drive_files(access_token, request.context)
        elif request.field_name == "folder_id":
            return await _fetch_google_drive_folders(access_token, request.context)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Google Drive field data fetch failed: {str(e)}"
        )


async def _fetch_google_drive_files(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch Google Drive files."""
    async with httpx.AsyncClient() as client:
        params = {
            "pageSize": 50,
            "fields": "files(id,name,mimeType,createdTime,modifiedTime,size)"
        }
        
        # Add query filter if provided
        if context and context.get("query"):
            params["q"] = context["query"]
        elif context and context.get("mime_type"):
            params["q"] = f"mimeType='{context['mime_type']}'"
        else:
            # Default: exclude folders and show recent files
            params["q"] = "mimeType != 'application/vnd.google-apps.folder'"
            
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Google Drive files"
            )
        
        data = response.json()
        files = data.get("files", [])
        
        options = []
        for file in files:
            # Format file size
            size_str = ""
            if file.get("size"):
                size_bytes = int(file["size"])
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes // 1024} KB"
                else:
                    size_str = f"{size_bytes // (1024 * 1024)} MB"
            
            # Get file type from mime type
            mime_type = file.get("mimeType", "")
            file_type = "File"
            if "google-apps" in mime_type:
                if "document" in mime_type:
                    file_type = "Google Doc"
                elif "spreadsheet" in mime_type:
                    file_type = "Google Sheet"
                elif "presentation" in mime_type:
                    file_type = "Google Slides"
                elif "folder" in mime_type:
                    file_type = "Folder"
            
            options.append(FieldOption(
                value=file["id"],
                label=file["name"],
                description=f"{file_type} • {size_str}" if size_str else file_type,
                metadata={
                    "mime_type": mime_type,
                    "created_time": file.get("createdTime"),
                    "modified_time": file.get("modifiedTime"),
                    "size": file.get("size")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_google_drive_folders(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch Google Drive folders."""
    async with httpx.AsyncClient() as client:
        params = {
            "q": "mimeType='application/vnd.google-apps.folder'",
            "pageSize": 50,
            "fields": "files(id,name,createdTime,modifiedTime)"
        }
        
        if context and context.get("query"):
            params["q"] += f" and name contains '{context['query']}'"
            
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch Google Drive folders"
            )
        
        data = response.json()
        folders = data.get("files", [])
        
        options = []
        for folder in folders:
            options.append(FieldOption(
                value=folder["id"],
                label=folder["name"],
                description=f"Modified: {folder.get('modifiedTime', '')[:10]}",
                metadata={
                    "created_time": folder.get("createdTime"),
                    "modified_time": folder.get("modifiedTime")
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_youtube_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch YouTube-specific field data."""
    try:
        # Get OAuth token
        oauth_token = await token_service.get_token(user_id, "youtube", AuthType.OAUTH2)
        if not oauth_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="YouTube authentication required"
            )
        
        access_token = oauth_token["token_data"]["access_token"]
        
        if request.field_name == "video_id":
            return await _fetch_youtube_videos(access_token, request.context)
        elif request.field_name == "playlist_id":
            return await _fetch_youtube_playlists(access_token, request.context)
        elif request.field_name == "channel_id":
            return await _fetch_youtube_channels(access_token, request.context)
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"YouTube field data fetch failed: {str(e)}"
        )


async def _fetch_youtube_videos(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch YouTube videos from user's channel."""
    async with httpx.AsyncClient() as client:
        # First get the user's channel
        channel_response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "part": "id,snippet",
                "mine": "true"
            }
        )
        
        if channel_response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch YouTube channel"
            )
        
        channel_data = channel_response.json()
        if not channel_data.get("items"):
            return FieldDataResponse(
                success=False,
                options=[],
                error="No YouTube channel found"
            )
        
        channel_id = channel_data["items"][0]["id"]
        
        # Get videos from the channel
        params = {
            "part": "id,snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": 25
        }
        
        if context and context.get("query"):
            params["q"] = context["query"]
        
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch YouTube videos"
            )
        
        data = response.json()
        videos = data.get("items", [])
        
        options = []
        for video in videos:
            if video["id"]["kind"] == "youtube#video":
                snippet = video["snippet"]
                options.append(FieldOption(
                    value=video["id"]["videoId"],
                    label=snippet["title"],
                    description=f"Published: {snippet.get('publishedAt', '')[:10]}",
                    metadata={
                        "channel_title": snippet.get("channelTitle"),
                        "published_at": snippet.get("publishedAt"),
                        "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url")
                    }
                ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_youtube_playlists(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch YouTube playlists."""
    async with httpx.AsyncClient() as client:
        params = {
            "part": "id,snippet,contentDetails",
            "mine": "true",
            "maxResults": 25
        }
        
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code != 200:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Failed to fetch YouTube playlists"
            )
        
        data = response.json()
        playlists = data.get("items", [])
        
        options = []
        for playlist in playlists:
            snippet = playlist["snippet"]
            content_details = playlist.get("contentDetails", {})
            
            options.append(FieldOption(
                value=playlist["id"],
                label=snippet["title"],
                description=f"{content_details.get('itemCount', 0)} videos",
                metadata={
                    "channel_title": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "item_count": content_details.get("itemCount", 0)
                }
            ))
        
        return FieldDataResponse(
            success=True,
            options=options
        )


async def _fetch_youtube_channels(access_token: str, context: Optional[Dict[str, Any]]) -> FieldDataResponse:
    """Fetch YouTube channels (user's own channel + subscriptions)."""
    async with httpx.AsyncClient() as client:
        options = []
        
        try:
            # First, get the user's own channel
            my_channel_response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "id,snippet,statistics",
                    "mine": "true"
                }
            )
            
            if my_channel_response.status_code == 200:
                my_channel_data = my_channel_response.json()
                my_channels = my_channel_data.get("items", [])
                
                for channel in my_channels:
                    snippet = channel.get("snippet", {})
                    statistics = channel.get("statistics", {})
                    
                    options.append(FieldOption(
                        value=channel["id"],
                        label=f"{snippet.get('title', 'My Channel')} (My Channel)",
                        description=f"Subscribers: {statistics.get('subscriberCount', 'N/A')}",
                        metadata={
                            "is_own_channel": True,
                            "published_at": snippet.get("publishedAt"),
                            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                            "subscriber_count": statistics.get("subscriberCount"),
                            "video_count": statistics.get("videoCount")
                        }
                    ))
            
            # Then try to get subscriptions (this might fail if user hasn't granted permission)
            try:
                subscriptions_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/subscriptions",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "part": "snippet",
                        "mine": "true",
                        "maxResults": 25
                    }
                )
                
                if subscriptions_response.status_code == 200:
                    subscriptions_data = subscriptions_response.json()
                    subscriptions = subscriptions_data.get("items", [])
                    
                    for sub in subscriptions:
                        snippet = sub.get("snippet", {})
                        resource_id = snippet.get("resourceId", {})
                        
                        if resource_id.get("kind") == "youtube#channel":
                            # Don't add if it's already in the list (user's own channel)
                            channel_id = resource_id["channelId"]
                            if not any(opt.value == channel_id for opt in options):
                                options.append(FieldOption(
                                    value=channel_id,
                                    label=snippet.get("title", "Unknown Channel"),
                                    description=snippet.get("description", "")[:100] if snippet.get("description") else "Subscribed channel",
                                    metadata={
                                        "is_own_channel": False,
                                        "published_at": snippet.get("publishedAt"),
                                        "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url")
                                    }
                                ))
                else:
                    # Subscriptions API failed, but that's okay - we still have the user's own channel
                    logger.warning(f"Failed to fetch YouTube subscriptions: {subscriptions_response.status_code}")
                    
            except Exception as e:
                # Subscriptions might not be available due to permissions, but that's okay
                logger.warning(f"Could not fetch YouTube subscriptions: {str(e)}")
            
            # If we have no options at all, return an error
            if not options:
                return FieldDataResponse(
                    success=False,
                    options=[],
                    error="No YouTube channels found. Please make sure you have a YouTube channel."
                )
            
            return FieldDataResponse(
                success=True,
                options=options
            )
            
        except Exception as e:
            logger.error(f"Error fetching YouTube channels: {str(e)}")
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Failed to fetch YouTube channels: {str(e)}"
            )


async def _fetch_perplexity_field_data(
    request: FieldDataRequest,
    user_id: str,
    token_service
) -> FieldDataResponse:
    """Fetch Perplexity-specific field data."""
    try:
        # Get API key token
        api_token = await token_service.get_token(user_id, "perplexity", AuthType.API_KEY)
        if not api_token:
            return FieldDataResponse(
                success=False,
                options=[],
                error="Perplexity authentication required"
            )
        
        # Perplexity doesn't have dynamic fields like databases or files
        # But we can provide model options
        if request.field_name == "model":
            return await _fetch_perplexity_models()
        else:
            return FieldDataResponse(
                success=False,
                options=[],
                error=f"Dynamic data not available for field: {request.field_name}"
            )
            
    except Exception as e:
        return FieldDataResponse(
            success=False,
            options=[],
            error=f"Perplexity field data fetch failed: {str(e)}"
        )


async def _fetch_perplexity_models() -> FieldDataResponse:
    """Fetch available Perplexity models."""
    # Static list of Perplexity models (they don't have a models API endpoint)
    models = [
        {
            "value": "llama-3.1-sonar-small-128k-online",
            "label": "Llama 3.1 Sonar Small (Online)",
            "description": "Fast online model with web search"
        },
        {
            "value": "llama-3.1-sonar-large-128k-online", 
            "label": "Llama 3.1 Sonar Large (Online)",
            "description": "Powerful online model with web search"
        },
        {
            "value": "llama-3.1-sonar-huge-128k-online",
            "label": "Llama 3.1 Sonar Huge (Online)", 
            "description": "Most capable online model with web search"
        },
        {
            "value": "llama-3.1-8b-instruct",
            "label": "Llama 3.1 8B Instruct",
            "description": "Fast offline model"
        },
        {
            "value": "llama-3.1-70b-instruct",
            "label": "Llama 3.1 70B Instruct",
            "description": "Powerful offline model"
        }
    ]
    
    options = []
    for model in models:
        options.append(FieldOption(
            value=model["value"],
            label=model["label"],
            description=model["description"],
            metadata={"type": "online" if "online" in model["value"] else "offline"}
        ))
    
    return FieldDataResponse(
        success=True,
        options=options
    )