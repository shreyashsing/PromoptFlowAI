"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.core.auth import get_auth_service, get_current_user, AuthService
from app.core.database import get_database
from app.services.auth_tokens import get_auth_token_service, AuthTokenService
from app.models.database import CreateAuthTokenRequest, UpdateUserProfileRequest
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