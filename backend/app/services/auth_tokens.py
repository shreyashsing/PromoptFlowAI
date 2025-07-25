"""
Service for managing user authentication tokens.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from supabase import Client
from app.core.encryption import get_encryption_service
from app.models.database import AuthTokenDB, CreateAuthTokenRequest
from app.models.base import AuthType
import logging

logger = logging.getLogger(__name__)


class AuthTokenService:
    """Service for managing encrypted authentication tokens."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
        self.encryption = get_encryption_service()
    
    async def store_token(self, user_id: str, request: CreateAuthTokenRequest) -> AuthTokenDB:
        """Store an encrypted authentication token."""
        try:
            # Encrypt the token data
            encrypted_token = self.encryption.encrypt_token(request.token_data)
            
            # Prepare token metadata (non-sensitive info)
            token_metadata = {
                "created_by": "user",
                "token_hint": self._create_token_hint(request.token_data),
                "scopes": request.token_data.get("scopes", []) if request.token_type == AuthType.OAUTH2 else []
            }
            
            # Store in database
            token_data = {
                "user_id": user_id,
                "connector_name": request.connector_name,
                "token_type": request.token_type.value,
                "encrypted_token": encrypted_token,
                "token_metadata": token_metadata,
                "expires_at": request.expires_at.isoformat() if request.expires_at else None,
                "is_active": True
            }
            
            result = self.db.table('auth_tokens').upsert(
                token_data,
                on_conflict="user_id,connector_name,token_type"
            ).execute()
            
            if not result.data:
                raise Exception("Failed to store token")
            
            return AuthTokenDB(**result.data[0])
            
        except Exception as e:
            logger.error(f"Failed to store auth token: {e}")
            raise
    
    async def get_token(self, user_id: str, connector_name: str, token_type: AuthType) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt an authentication token."""
        try:
            result = self.db.table('auth_tokens').select('*').eq('user_id', user_id).eq('connector_name', connector_name).eq('token_type', token_type.value).eq('is_active', True).execute()
            
            if not result.data:
                return None
            
            token_record = result.data[0]
            
            # Check if token is expired
            if token_record.get('expires_at'):
                expires_at = datetime.fromisoformat(token_record['expires_at'].replace('Z', '+00:00'))
                if expires_at < datetime.utcnow():
                    logger.warning(f"Token expired for user {user_id}, connector {connector_name}")
                    await self.deactivate_token(user_id, connector_name, token_type)
                    return None
            
            # Decrypt token data
            decrypted_data = self.encryption.decrypt_token(token_record['encrypted_token'])
            
            return {
                "token_data": decrypted_data,
                "metadata": token_record.get('token_metadata', {}),
                "expires_at": token_record.get('expires_at')
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve auth token: {e}")
            return None
    
    async def update_token(self, user_id: str, connector_name: str, token_type: AuthType, new_token_data: Dict[str, Any], expires_at: Optional[datetime] = None) -> bool:
        """Update an existing authentication token."""
        try:
            # Encrypt the new token data
            encrypted_token = self.encryption.encrypt_token(new_token_data)
            
            # Update token metadata
            token_metadata = {
                "updated_by": "system",
                "token_hint": self._create_token_hint(new_token_data),
                "scopes": new_token_data.get("scopes", []) if token_type == AuthType.OAUTH2 else []
            }
            
            update_data = {
                "encrypted_token": encrypted_token,
                "token_metadata": token_metadata,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.db.table('auth_tokens').update(update_data).eq('user_id', user_id).eq('connector_name', connector_name).eq('token_type', token_type.value).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update auth token: {e}")
            return False
    
    async def deactivate_token(self, user_id: str, connector_name: str, token_type: AuthType) -> bool:
        """Deactivate an authentication token."""
        try:
            result = self.db.table('auth_tokens').update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('connector_name', connector_name).eq('token_type', token_type.value).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to deactivate auth token: {e}")
            return False
    
    async def list_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """List all active tokens for a user (without decrypting)."""
        try:
            result = self.db.table('auth_tokens').select('id, connector_name, token_type, token_metadata, expires_at, created_at').eq('user_id', user_id).eq('is_active', True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to list user tokens: {e}")
            return []
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens (background task)."""
        try:
            current_time = datetime.utcnow().isoformat()
            
            result = self.db.table('auth_tokens').update({
                "is_active": False,
                "updated_at": current_time
            }).lt('expires_at', current_time).eq('is_active', True).execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {count} expired tokens")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0
    
    def _create_token_hint(self, token_data: Dict[str, Any]) -> str:
        """Create a hint for the token (last 4 characters or similar)."""
        if "access_token" in token_data:
            token = token_data["access_token"]
        elif "api_key" in token_data:
            token = token_data["api_key"]
        elif "token" in token_data:
            token = token_data["token"]
        else:
            return "****"
        
        if len(token) > 8:
            return f"****{token[-4:]}"
        else:
            return "****"


async def get_auth_token_service(db: Client) -> AuthTokenService:
    """Get auth token service instance."""
    return AuthTokenService(db)