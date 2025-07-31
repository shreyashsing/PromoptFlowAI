"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import secrets
import httpx
from urllib.parse import urlencode
from app.core.auth import get_auth_service, get_current_user, AuthService
from app.core.config import settings
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service, AuthTokenService
from app.models.database import CreateAuthTokenRequest, UpdateUserProfileRequest
from app.models.base import AuthType
from supabase import Client

router = APIRouter(prefix="/auth", tags=["authentication"])


class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


@router.post("/signup", response_model=AuthResponse)
async def sign_up(
    request: SignUpRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Sign up a new user."""
    try:
        user_metadata = {}
        if request.full_name:
            user_metadata["full_name"] = request.full_name
        
        result = await auth_service.sign_up(
            email=request.email,
            password=request.password,
            user_metadata=user_metadata
        )
        
        if not result.get("session"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sign up failed - no session created"
            )
        
        session = result["session"]
        user = result["user"]
        
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {}
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign up failed: {str(e)}"
        )


@router.post("/signin", response_model=AuthResponse)
async def sign_in(
    request: SignInRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Sign in an existing user."""
    try:
        result = await auth_service.sign_in(
            email=request.email,
            password=request.password
        )
        
        if not result.get("session"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        session = result["session"]
        user = result["user"]
        
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {}
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token."""
    try:
        result = await auth_service.refresh_token(request.refresh_token)
        
        session = result["session"]
        user = result["user"]
        
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {}
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/signout")
async def sign_out(
    current_user: Dict[str, Any] = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Sign out current user."""
    try:
        # Note: In a real implementation, you'd need to pass the actual token
        # For now, we'll just return success
        return {"message": "Signed out successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign out failed"
        )


@router.get("/me")
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user profile."""
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "profile": current_user["profile"]
    }


@router.put("/me")
async def update_user_profile(
    request: UpdateUserProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """Update current user profile."""
    try:
        user_id = current_user["user_id"]
        
        # Prepare update data
        update_data = {}
        if request.full_name is not None:
            update_data["full_name"] = request.full_name
        if request.avatar_url is not None:
            update_data["avatar_url"] = request.avatar_url
        if request.preferences is not None:
            update_data["preferences"] = request.preferences
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update in database
        result = db.table('users').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "Profile updated successfully", "profile": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


# Token management endpoints
@router.post("/tokens")
async def store_auth_token(
    request: CreateAuthTokenRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """Store an authentication token for a connector."""
    try:
        token_service = await get_auth_token_service(db)
        user_id = current_user["user_id"]
        
        token_record = await token_service.store_token(user_id, request)
        
        return {
            "message": "Token stored successfully",
            "token_id": token_record.id,
            "connector_name": token_record.connector_name,
            "token_type": token_record.token_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store token: {str(e)}"
        )


@router.get("/tokens")
async def list_auth_tokens(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """List all authentication tokens for current user."""
    try:
        token_service = await get_auth_token_service(db)
        user_id = current_user["user_id"]
        
        tokens = await token_service.list_user_tokens(user_id)
        
        return {"tokens": tokens}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tokens: {str(e)}"
        )


@router.delete("/tokens/{connector_name}/{token_type}")
async def delete_auth_token(
    connector_name: str,
    token_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """Delete an authentication token."""
    try:
        from app.models.base import AuthType
        
        token_service = await get_auth_token_service(db)
        user_id = current_user["user_id"]
        
        # Validate token type
        try:
            auth_type = AuthType(token_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid token type: {token_type}"
            )
        
        success = await token_service.deactivate_token(user_id, connector_name, auth_type)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        return {"message": "Token deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete token: {str(e)}"
        )


# OAuth endpoints
class OAuthInitiateRequest(BaseModel):
    connector_name: str
    redirect_uri: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    connector_name: str



@router.post("/oauth/initiate")
async def initiate_oauth(
    request: OAuthInitiateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Initiate OAuth flow for a connector via POST request."""
    return await initiate_oauth_impl(request, current_user)


async def initiate_oauth_impl(
    request: OAuthInitiateRequest,
    current_user: Dict[str, Any]
):
    """Implementation of OAuth initiation logic."""
    try:
        if request.connector_name in ["gmail_connector", "google_sheets"]:
            # Google OAuth configuration (works for both Gmail and Sheets)
            client_id = settings.GMAIL_CLIENT_ID
            if not client_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth not configured - missing GMAIL_CLIENT_ID"
                )
            redirect_uri = request.redirect_uri or "http://localhost:3000/auth/oauth/callback"
            
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Define scopes based on connector
            if request.connector_name == "gmail_connector":
                scopes = [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/gmail.labels"
                ]
            elif request.connector_name == "google_sheets":
                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.file"
                ]
            
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
                "state": state
            })
            
            return {
                "authorization_url": auth_url,
                "state": state,
                "redirect_uri": redirect_uri
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth not supported for connector: {request.connector_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )


@router.post("/oauth/callback")
async def oauth_callback(
    request: OAuthCallbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Client = Depends(get_database)
):
    """Handle OAuth callback and exchange code for tokens."""
    try:
        if request.connector_name in ["gmail_connector", "google_sheets"]:
            # Google OAuth token exchange (works for both Gmail and Sheets)
            client_id = settings.GMAIL_CLIENT_ID
            client_secret = settings.GMAIL_CLIENT_SECRET
            
            if not client_id or not client_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth not configured - missing credentials"
                )
            
            redirect_uri = "http://localhost:3000/auth/oauth/callback"
            
            # Exchange authorization code for tokens
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": request.code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri
                    }
                )
                
                if token_response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to exchange authorization code for tokens"
                    )
                
                tokens = token_response.json()
                
                # Store tokens in database
                token_service = await get_auth_token_service(db)
                user_id = current_user["user_id"]
                
                # First, deactivate any existing tokens for this connector
                await token_service.deactivate_token(user_id, request.connector_name, AuthType.OAUTH2)
                
                # Prepare combined token data (both access and refresh tokens in one record)
                token_data = {
                    "access_token": tokens["access_token"],
                    "token_type": tokens.get("token_type", "Bearer"),
                    "expires_in": str(tokens.get("expires_in")) if tokens.get("expires_in") is not None else None,
                    "scope": tokens.get("scope")
                }
                
                # Add refresh token if available
                if "refresh_token" in tokens:
                    token_data["refresh_token"] = tokens["refresh_token"]
                
                # Store combined token data in single call
                combined_token_request = CreateAuthTokenRequest(
                    connector_name=request.connector_name,
                    token_type=AuthType.OAUTH2,
                    token_data=token_data
                )
                
                await token_service.store_token(user_id, combined_token_request)
                
                return {
                    "message": "OAuth authentication successful",
                    "connector_name": request.connector_name,
                    "scopes": tokens.get("scope", "").split(" ") if tokens.get("scope") else []
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth callback not supported for connector: {request.connector_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )