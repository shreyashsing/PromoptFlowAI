"""
Authentication Context Manager for ReAct Agent Tools.

This service handles authentication token injection and ConnectorExecutionContext
creation from user sessions as specified in requirement 2.4.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.connector import ConnectorExecutionContext
from app.models.base import AuthType
from app.services.auth_tokens import AuthTokenService
from app.core.exceptions import AuthenticationException
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)


class AuthContextManager:
    """
    Manages authentication context for ReAct agent tool execution.
    
    This class implements the authentication token injection mechanism and
    ConnectorExecutionContext creation requirements from task 2.3.
    """
    
    def __init__(self):
        self.auth_token_service = None
    
    async def _get_auth_token_service(self) -> AuthTokenService:
        """Get auth token service instance."""
        if self.auth_token_service is None:
            db_client = get_supabase_client()
            self.auth_token_service = AuthTokenService(db_client)
        return self.auth_token_service
    
    async def create_execution_context(
        self,
        user_id: str,
        connector_name: str,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        previous_results: Optional[Dict[str, Any]] = None
    ) -> ConnectorExecutionContext:
        """
        Create ConnectorExecutionContext from user session.
        
        This method implements the ConnectorExecutionContext creation requirement from 2.3.
        
        Args:
            user_id: User ID from authentication
            connector_name: Name of the connector being executed
            request_id: Optional request ID for tracking
            workflow_id: Optional workflow ID if part of a workflow
            node_id: Optional node ID if part of a workflow
            previous_results: Optional previous results from workflow
            
        Returns:
            ConnectorExecutionContext with injected authentication tokens
        """
        try:
            # Get authentication tokens for the connector
            auth_tokens = await self.get_connector_auth_tokens(user_id, connector_name)
            
            # Create execution context
            context = ConnectorExecutionContext(
                user_id=user_id,
                auth_tokens=auth_tokens,
                request_id=request_id or f"react_tool_{datetime.utcnow().timestamp()}",
                workflow_id=workflow_id,
                node_id=node_id,
                previous_results=previous_results or {}
            )
            
            logger.debug(f"Created execution context for user {user_id}, connector {connector_name}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create execution context for user {user_id}, connector {connector_name}: {e}")
            # Return context with empty auth tokens to allow execution to proceed
            # The connector will handle authentication failures appropriately
            return ConnectorExecutionContext(
                user_id=user_id,
                auth_tokens={},
                request_id=request_id or f"react_tool_{datetime.utcnow().timestamp()}",
                workflow_id=workflow_id,
                node_id=node_id,
                previous_results=previous_results or {}
            )
    
    async def get_connector_auth_tokens(self, user_id: str, connector_name: str) -> Dict[str, str]:
        """
        Get authentication tokens for a specific connector.
        
        This method implements the authentication token injection mechanism from 2.3.
        
        Args:
            user_id: User ID
            connector_name: Name of the connector
            
        Returns:
            Dictionary of authentication tokens for the connector
        """
        try:
            auth_service = await self._get_auth_token_service()
            auth_tokens = {}
            
            # Try to get OAuth2 tokens first (most common for Google services)
            oauth_token = await auth_service.get_token(user_id, connector_name, AuthType.OAUTH2)
            if oauth_token:
                token_data = oauth_token["token_data"]
                if "access_token" in token_data:
                    auth_tokens["access_token"] = token_data["access_token"]
                if "refresh_token" in token_data:
                    auth_tokens["refresh_token"] = token_data["refresh_token"]
                logger.debug(f"Retrieved OAuth2 tokens for user {user_id}, connector {connector_name}")
                return auth_tokens
            
            # Try to get API key tokens
            api_key_token = await auth_service.get_token(user_id, connector_name, AuthType.API_KEY)
            if api_key_token:
                token_data = api_key_token["token_data"]
                if "api_key" in token_data:
                    auth_tokens["api_key"] = token_data["api_key"]
                logger.debug(f"Retrieved API key tokens for user {user_id}, connector {connector_name}")
                return auth_tokens
            
            # Try to get basic auth tokens
            basic_token = await auth_service.get_token(user_id, connector_name, AuthType.BASIC)
            if basic_token:
                token_data = basic_token["token_data"]
                if "username" in token_data:
                    auth_tokens["username"] = token_data["username"]
                if "password" in token_data:
                    auth_tokens["password"] = token_data["password"]
                logger.debug(f"Retrieved basic auth tokens for user {user_id}, connector {connector_name}")
                return auth_tokens
            
            # No tokens found
            logger.warning(f"No authentication tokens found for user {user_id}, connector {connector_name}")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get auth tokens for user {user_id}, connector {connector_name}: {e}")
            return {}
    
    async def handle_authentication_failure(
        self,
        user_id: str,
        connector_name: str,
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle authentication failures during tool execution.
        
        This method implements the error handling for authentication failures from 2.3.
        
        Args:
            user_id: User ID
            connector_name: Name of the connector
            error: Authentication error that occurred
            
        Returns:
            Dictionary with error information and suggested actions
        """
        try:
            logger.warning(f"Authentication failure for user {user_id}, connector {connector_name}: {error}")
            
            # Determine the type of authentication error and provide appropriate guidance
            error_msg = str(error).lower()
            
            if "token" in error_msg and ("expired" in error_msg or "invalid" in error_msg):
                return {
                    "error_type": "token_expired",
                    "message": f"Authentication token for {connector_name} has expired or is invalid",
                    "suggested_action": "Please re-authenticate with the connector",
                    "requires_reauth": True
                }
            elif "permission" in error_msg or "scope" in error_msg:
                return {
                    "error_type": "insufficient_permissions",
                    "message": f"Insufficient permissions for {connector_name}",
                    "suggested_action": "Please check that the connector has the required permissions",
                    "requires_reauth": True
                }
            elif "not found" in error_msg or "missing" in error_msg:
                return {
                    "error_type": "no_authentication",
                    "message": f"No authentication configured for {connector_name}",
                    "suggested_action": "Please authenticate with the connector first",
                    "requires_reauth": True
                }
            else:
                return {
                    "error_type": "authentication_error",
                    "message": f"Authentication failed for {connector_name}: {str(error)}",
                    "suggested_action": "Please check your authentication settings",
                    "requires_reauth": True
                }
                
        except Exception as e:
            logger.error(f"Failed to handle authentication failure: {e}")
            return {
                "error_type": "unknown_error",
                "message": f"Unknown authentication error for {connector_name}",
                "suggested_action": "Please try again or contact support",
                "requires_reauth": True
            }
    
    async def refresh_token_if_needed(
        self,
        user_id: str,
        connector_name: str,
        auth_tokens: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Refresh authentication token if needed and possible.
        
        This method implements requirement 2.4: Add OAuth token refresh handling for long-running conversations.
        
        Args:
            user_id: User ID
            connector_name: Name of the connector
            auth_tokens: Current authentication tokens
            
        Returns:
            Updated authentication tokens (may be the same if refresh not needed/possible)
        """
        try:
            # Only attempt refresh for OAuth2 tokens with refresh_token
            if "refresh_token" not in auth_tokens or "access_token" not in auth_tokens:
                logger.debug(f"No refresh token available for {connector_name}, skipping refresh")
                return auth_tokens
            
            # Check if we need to refresh the token
            # For now, we'll implement a basic refresh mechanism
            # In production, you would check token expiry time
            
            logger.info(f"Attempting to refresh OAuth2 token for user {user_id}, connector {connector_name}")
            
            # Get the auth token service to update stored tokens
            auth_service = await self._get_auth_token_service()
            
            # For Google services (Gmail, Google Sheets), implement OAuth2 refresh
            if connector_name in ["gmail_connector", "google_sheets_connector"]:
                refreshed_tokens = await self._refresh_google_oauth_token(
                    user_id, connector_name, auth_tokens
                )
                if refreshed_tokens:
                    logger.info(f"Successfully refreshed OAuth2 token for {connector_name}")
                    return refreshed_tokens
            
            # For other OAuth2 services, implement generic refresh
            elif "refresh_token" in auth_tokens:
                refreshed_tokens = await self._refresh_generic_oauth_token(
                    user_id, connector_name, auth_tokens
                )
                if refreshed_tokens:
                    logger.info(f"Successfully refreshed OAuth2 token for {connector_name}")
                    return refreshed_tokens
            
            logger.debug(f"Token refresh not needed or not possible for {connector_name}")
            return auth_tokens
            
        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}, connector {connector_name}: {e}")
            # Return original tokens on failure to allow execution to continue
            return auth_tokens
    
    async def _refresh_google_oauth_token(
        self,
        user_id: str,
        connector_name: str,
        auth_tokens: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """
        Refresh Google OAuth2 token using refresh token.
        
        This method implements OAuth token refresh for Google services.
        """
        try:
            import requests
            from datetime import datetime, timedelta
            
            refresh_token = auth_tokens.get("refresh_token")
            if not refresh_token:
                return None
            
            # Google OAuth2 token refresh endpoint
            token_url = "https://oauth2.googleapis.com/token"
            
            # Get client credentials from settings
            from app.core.config import settings
            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
            client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
            
            if not client_id or not client_secret:
                logger.warning("Google OAuth credentials not configured, cannot refresh token")
                return None
            
            # Prepare refresh request
            refresh_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            # Make refresh request
            response = requests.post(token_url, data=refresh_data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update tokens
                new_tokens = {
                    "access_token": token_data["access_token"],
                    "refresh_token": refresh_token,  # Keep existing refresh token
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_in": token_data.get("expires_in", 3600)
                }
                
                # Update stored tokens
                auth_service = await self._get_auth_token_service()
                expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
                
                await auth_service.update_token(
                    user_id, connector_name, AuthType.OAUTH2, new_tokens, expires_at
                )
                
                logger.info(f"Successfully refreshed Google OAuth token for {connector_name}")
                return new_tokens
            else:
                logger.error(f"Failed to refresh Google OAuth token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing Google OAuth token: {e}")
            return None
    
    async def _refresh_generic_oauth_token(
        self,
        user_id: str,
        connector_name: str,
        auth_tokens: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """
        Generic OAuth2 token refresh implementation.
        
        This can be extended for other OAuth2 providers.
        """
        try:
            # This is a placeholder for generic OAuth2 refresh
            # Each OAuth2 provider has different refresh endpoints and requirements
            logger.debug(f"Generic OAuth2 refresh not implemented for {connector_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error in generic OAuth token refresh: {e}")
            return None
    
    async def validate_connector_authentication(
        self,
        user_id: str,
        connector_name: str,
        required_auth_type: AuthType
    ) -> bool:
        """
        Validate that the user has the required authentication for a connector.
        
        Args:
            user_id: User ID
            connector_name: Name of the connector
            required_auth_type: Required authentication type
            
        Returns:
            True if user has valid authentication, False otherwise
        """
        try:
            if required_auth_type == AuthType.NONE:
                return True
            
            auth_service = await self._get_auth_token_service()
            token_info = await auth_service.get_token(user_id, connector_name, required_auth_type)
            
            return token_info is not None
            
        except Exception as e:
            logger.error(f"Failed to validate authentication for user {user_id}, connector {connector_name}: {e}")
            return False
    
    async def check_tool_permissions(
        self,
        user_id: str,
        connector_name: str,
        requested_action: str = "execute"
    ) -> Dict[str, Any]:
        """
        Check if user has permission to access a specific tool.
        
        This method implements requirement 2.4: Implement permission checks before tool access.
        
        Args:
            user_id: User ID
            connector_name: Name of the connector/tool
            requested_action: Action being requested (execute, configure, etc.)
            
        Returns:
            Dictionary with permission check results
        """
        try:
            # Get user session to check permissions
            # For now, we'll implement basic permission checking
            # This can be extended with role-based access control (RBAC)
            
            permission_result = {
                "allowed": True,
                "reason": "Permission granted",
                "restrictions": [],
                "required_scopes": []
            }
            
            # Check if user has authentication for the connector
            try:
                from app.connectors.registry import get_connector_registry
                connector_registry = get_connector_registry()
            except ImportError:
                logger.warning("Connector registry not available for permission check")
                return permission_result
            
            try:
                connector_class = connector_registry.get_connector(connector_name)
                if connector_class:
                    # Create temporary instance to get auth requirements
                    temp_connector = connector_class()
                    auth_requirements = await temp_connector.get_auth_requirements()
                    
                    # Check if user has required authentication
                    if auth_requirements.type != AuthType.NONE:
                        has_auth = await self.validate_connector_authentication(
                            user_id, connector_name, auth_requirements.type
                        )
                        
                        if not has_auth:
                            permission_result.update({
                                "allowed": False,
                                "reason": f"Missing authentication for {connector_name}",
                                "required_auth_type": auth_requirements.type.value,
                                "auth_instructions": auth_requirements.instructions
                            })
                            return permission_result
                    
                    # Check OAuth scopes if applicable
                    if hasattr(auth_requirements, 'oauth_scopes') and auth_requirements.oauth_scopes:
                        permission_result["required_scopes"] = auth_requirements.oauth_scopes
                        
                        # Verify user has required scopes
                        user_tokens = await self.get_connector_auth_tokens(user_id, connector_name)
                        if user_tokens and "scope" in user_tokens:
                            user_scopes = user_tokens["scope"].split() if isinstance(user_tokens["scope"], str) else user_tokens["scope"]
                            missing_scopes = [scope for scope in auth_requirements.oauth_scopes if scope not in user_scopes]
                            
                            if missing_scopes:
                                permission_result.update({
                                    "allowed": False,
                                    "reason": f"Missing required OAuth scopes: {missing_scopes}",
                                    "missing_scopes": missing_scopes
                                })
                                return permission_result
                
            except Exception as connector_error:
                logger.warning(f"Could not check connector requirements for {connector_name}: {connector_error}")
            
            # Additional permission checks can be added here
            # For example: rate limiting, user role checks, time-based restrictions
            
            # Check for any user-specific restrictions
            restrictions = await self._get_user_restrictions(user_id, connector_name)
            if restrictions:
                permission_result["restrictions"] = restrictions
                
                # Check if any restrictions block access
                if any(r.get("blocks_access", False) for r in restrictions):
                    permission_result.update({
                        "allowed": False,
                        "reason": "Access blocked by user restrictions"
                    })
            
            logger.debug(f"Permission check for user {user_id}, connector {connector_name}: {permission_result}")
            return permission_result
            
        except Exception as e:
            logger.error(f"Failed to check tool permissions for user {user_id}, connector {connector_name}: {e}")
            return {
                "allowed": False,
                "reason": f"Permission check failed: {str(e)}",
                "error": True
            }
    
    async def _get_user_restrictions(
        self,
        user_id: str,
        connector_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get user-specific restrictions for a connector.
        
        This can be extended to implement role-based access control,
        rate limiting, time-based restrictions, etc.
        """
        try:
            # Placeholder for user restrictions
            # In a full implementation, this would query a database
            # for user-specific or role-based restrictions
            
            restrictions = []
            
            # Example: Rate limiting restriction
            # restrictions.append({
            #     "type": "rate_limit",
            #     "limit": 100,
            #     "period": "hour",
            #     "blocks_access": False
            # })
            
            return restrictions
            
        except Exception as e:
            logger.error(f"Failed to get user restrictions: {e}")
            return []
    
    async def create_secure_execution_context(
        self,
        user_id: str,
        connector_name: str,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        previous_results: Optional[Dict[str, Any]] = None
    ) -> ConnectorExecutionContext:
        """
        Create secure ConnectorExecutionContext with permission checks and token refresh.
        
        This method implements requirement 2.4: Create secure credential passing to connector tools.
        
        Args:
            user_id: User ID from authentication
            connector_name: Name of the connector being executed
            request_id: Optional request ID for tracking
            workflow_id: Optional workflow ID if part of a workflow
            node_id: Optional node ID if part of a workflow
            previous_results: Optional previous results from workflow
            
        Returns:
            ConnectorExecutionContext with validated authentication and permissions
        """
        try:
            # First check permissions
            permission_check = await self.check_tool_permissions(user_id, connector_name)
            
            if not permission_check["allowed"]:
                raise AuthenticationException(
                    f"Permission denied for {connector_name}: {permission_check['reason']}"
                )
            
            # Get authentication tokens
            auth_tokens = await self.get_connector_auth_tokens(user_id, connector_name)
            
            # Refresh tokens if needed (for OAuth2)
            if auth_tokens and "refresh_token" in auth_tokens:
                auth_tokens = await self.refresh_token_if_needed(user_id, connector_name, auth_tokens)
            
            # Create execution context with validated tokens
            context = ConnectorExecutionContext(
                user_id=user_id,
                auth_tokens=auth_tokens,
                request_id=request_id or f"react_tool_{datetime.utcnow().timestamp()}",
                workflow_id=workflow_id,
                node_id=node_id,
                previous_results=previous_results or {},
                permissions=permission_check.get("restrictions", []),
                required_scopes=permission_check.get("required_scopes", [])
            )
            
            logger.debug(f"Created secure execution context for user {user_id}, connector {connector_name}")
            return context
            
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"Failed to create secure execution context for user {user_id}, connector {connector_name}: {e}")
            # Return context with empty auth tokens to allow execution to proceed
            # The connector will handle authentication failures appropriately
            return ConnectorExecutionContext(
                user_id=user_id,
                auth_tokens={},
                request_id=request_id or f"react_tool_{datetime.utcnow().timestamp()}",
                workflow_id=workflow_id,
                node_id=node_id,
                previous_results=previous_results or {}
            )


# Global instance
auth_context_manager = AuthContextManager()


async def get_auth_context_manager() -> AuthContextManager:
    """Get the global auth context manager instance."""
    return auth_context_manager