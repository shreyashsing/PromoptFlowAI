"""
Authentication utilities using Supabase Auth.
"""
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.core.database import get_database
from app.models.database import UserProfile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data."""
        try:
            # Supabase handles JWT verification internally
            user_response = self.db.auth.get_user(token)
            
            if not user_response.user:
                raise AuthenticationError("Invalid token")
            
            return {
                "user_id": user_response.user.id,
                "email": user_response.user.email,
                "user_metadata": user_response.user.user_metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AuthenticationError("Token verification failed")
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from database."""
        try:
            result = self.db.table('users').select('*').eq('id', user_id).execute()
            
            if not result.data:
                return None
            
            user_data = result.data[0]
            return UserProfile(**user_data)
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None
    
    async def create_or_update_user_profile(self, user_data: Dict[str, Any]) -> UserProfile:
        """Create or update user profile in database."""
        try:
            profile_data = {
                "id": user_data["user_id"],
                "email": user_data["email"],
                "full_name": user_data.get("user_metadata", {}).get("full_name"),
                "avatar_url": user_data.get("user_metadata", {}).get("avatar_url"),
                "preferences": user_data.get("user_metadata", {}).get("preferences", {})
            }
            
            # First check if the user profile exists
            existing = self.db.table('users').select('id').eq('id', user_data["user_id"]).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing profile
                result = self.db.table('users').update(profile_data).eq('id', user_data["user_id"]).execute()
            else:
                # Insert new profile
                result = self.db.table('users').insert(profile_data).execute()
            
            if not result.data:
                raise Exception("Failed to create/update user profile")
            
            return UserProfile(**result.data[0])
            
        except Exception as e:
            logger.error(f"Failed to create/update user profile: {e}")
            # Return a fallback profile to prevent authentication failures
            now = datetime.now()
            return UserProfile(
                id=user_data["user_id"],
                email=user_data["email"],
                full_name=user_data.get("user_metadata", {}).get("full_name"),
                avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
                preferences=user_data.get("user_metadata", {}).get("preferences", {}),
                created_at=now,
                updated_at=now
            )
    
    async def sign_up(self, email: str, password: str, user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sign up a new user."""
        try:
            response = self.db.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata or {}
                }
            })
            
            if response.user:
                # Create user profile in our database
                user_data = {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": user_metadata or {}
                }
                await self.create_or_update_user_profile(user_data)
            
            return {
                "user": response.user,
                "session": response.session
            }
            
        except Exception as e:
            logger.error(f"Sign up failed: {e}")
            raise AuthenticationError(f"Sign up failed: {str(e)}")
    
    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in an existing user."""
        try:
            response = self.db.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Update user profile if needed
                user_data = {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {}
                }
                await self.create_or_update_user_profile(user_data)
            
            return {
                "user": response.user,
                "session": response.session
            }
            
        except Exception as e:
            logger.error(f"Sign in failed: {e}")
            raise AuthenticationError(f"Sign in failed: {str(e)}")
    
    async def sign_out(self, token: str) -> bool:
        """Sign out user and invalidate session."""
        try:
            self.db.auth.sign_out()
            return True
            
        except Exception as e:
            logger.error(f"Sign out failed: {e}")
            return False
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            response = self.db.auth.refresh_session(refresh_token)
            
            return {
                "session": response.session,
                "user": response.user
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {str(e)}")


async def get_auth_service(db: Client = Depends(get_database)) -> AuthService:
    """Dependency to get authentication service."""
    return AuthService(db)


async def get_current_user(authorization: str = Header(...)) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token.
    Supports both real Supabase JWT tokens and development token.
    """
    try:
        logger.info(f"Authentication attempt with header: {authorization[:20]}...")
        
        if not authorization.startswith("Bearer "):
            logger.warning("Invalid authorization header format")
            raise AuthenticationError("Invalid authorization header")
        
        token = authorization.split(" ")[1]
        logger.info(f"Extracted token: {token[:20]}...")
        
        # Handle development token
        if token == "dev-test-token":
            logger.info("Using development token")
            user_data = {
                "user_id": "00000000-0000-0000-0000-000000000001",
                "email": "dev@test.com",
                "user_metadata": {}
            }
            
            # Ensure development user exists in database
            from app.core.database import get_supabase_client
            db_client = get_supabase_client()
            auth_service = AuthService(db_client)
            try:
                await auth_service.create_or_update_user_profile(user_data)
                logger.info("Created development user profile: 00000000-0000-0000-0000-000000000001")
            except Exception as e:
                logger.error(f"Failed to create/update user profile: {e}")
                # Continue anyway for development
            
            return user_data
        
        # Handle real Supabase JWT token
        logger.info("Attempting to verify real Supabase JWT token")
        from app.core.database import get_supabase_client
        db_client = get_supabase_client()
        auth_service = AuthService(db_client)
        user_data = await auth_service.verify_token(token)
        logger.info(f"Successfully verified JWT for user: {user_data.get('user_id', 'UNKNOWN')}")
        
        return user_data
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[Dict[str, Any]]:
    """Dependency to get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, auth_service)
    except HTTPException:
        return None