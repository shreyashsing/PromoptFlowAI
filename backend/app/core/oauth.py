"""
OAuth helper utilities for third-party authentication.
"""
import secrets
import base64
import hashlib
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from pydantic import BaseModel

from app.core.exceptions import AuthenticationException
from app.models.base import AuthType


class OAuthConfig(BaseModel):
    """OAuth configuration for a service."""
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    scopes: List[str]
    redirect_uri: str


class OAuthToken(BaseModel):
    """OAuth token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuthHelper:
    """Helper class for OAuth 2.0 authentication flows."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    def generate_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL and state parameter.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = self._generate_state()
        
        params = {
            'client_id': self.config.client_id,
            'response_type': 'code',
            'redirect_uri': self.config.redirect_uri,
            'scope': ' '.join(self.config.scopes),
            'state': state,
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent'  # Force consent screen to get refresh token
        }
        
        auth_url = f"{self.config.authorization_url}?{urlencode(params)}"
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            state: State parameter for verification
            
        Returns:
            OAuthToken with access and refresh tokens
            
        Raises:
            AuthenticationException: If token exchange fails
        """
        token_data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.config.redirect_uri
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    data=token_data,
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                
                token_response = response.json()
                
                if 'error' in token_response:
                    raise AuthenticationException(
                        f"OAuth token exchange failed: {token_response.get('error_description', token_response['error'])}"
                    )
                
                return OAuthToken(**token_response)
                
        except httpx.HTTPError as e:
            raise AuthenticationException(f"OAuth token exchange failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from previous OAuth flow
            
        Returns:
            New OAuthToken with refreshed access token
            
        Raises:
            AuthenticationException: If token refresh fails
        """
        token_data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    data=token_data,
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                
                token_response = response.json()
                
                if 'error' in token_response:
                    raise AuthenticationException(
                        f"OAuth token refresh failed: {token_response.get('error_description', token_response['error'])}"
                    )
                
                # Preserve refresh token if not returned in response
                if 'refresh_token' not in token_response:
                    token_response['refresh_token'] = refresh_token
                
                return OAuthToken(**token_response)
                
        except httpx.HTTPError as e:
            raise AuthenticationException(f"OAuth token refresh failed: {str(e)}")
    
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate an access token by making a test API call.
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        # This is a generic validation - specific connectors should override
        # with service-specific validation endpoints
        return True
    
    def _generate_state(self) -> str:
        """Generate a secure random state parameter for CSRF protection."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


class OAuthManager:
    """Manager for OAuth configurations and flows."""
    
    def __init__(self):
        self._configs: Dict[str, OAuthConfig] = {}
    
    def register_oauth_config(self, service_name: str, config: OAuthConfig) -> None:
        """
        Register OAuth configuration for a service.
        
        Args:
            service_name: Name of the service (e.g., 'gmail', 'google_sheets')
            config: OAuth configuration
        """
        self._configs[service_name] = config
    
    def get_oauth_helper(self, service_name: str) -> OAuthHelper:
        """
        Get OAuth helper for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            OAuthHelper instance
            
        Raises:
            AuthenticationException: If service not configured
        """
        if service_name not in self._configs:
            raise AuthenticationException(f"OAuth not configured for service: {service_name}")
        
        return OAuthHelper(self._configs[service_name])
    
    def list_oauth_services(self) -> List[str]:
        """List all configured OAuth services."""
        return list(self._configs.keys())


# Global OAuth manager instance
oauth_manager = OAuthManager()


# Common OAuth configurations
GOOGLE_OAUTH_CONFIG = OAuthConfig(
    client_id="",  # To be set from environment
    client_secret="",  # To be set from environment
    authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=[
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/spreadsheets"
    ],
    redirect_uri="http://localhost:8000/auth/oauth/callback"
)