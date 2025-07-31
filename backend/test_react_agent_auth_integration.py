"""
Test ReAct Agent Authentication Integration.

This test verifies that the ReAct agent properly integrates with the existing
JWT authentication middleware and implements secure tool execution with user credentials.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.react_agent_service import ReactAgentService
from app.services.auth_context_manager import AuthContextManager
from app.models.base import AuthType
from app.core.exceptions import AuthenticationException


class TestReactAgentAuthIntegration:
    """Test ReAct agent authentication integration."""
    
    @pytest.fixture
    def react_service(self):
        """Create a ReAct agent service for testing."""
        service = ReactAgentService()
        # Mock the initialization to avoid external dependencies
        service._initialized = True
        service.react_agent = Mock()
        service.llm = Mock()
        return service
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data from JWT token."""
        return {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "user_metadata": {
                "full_name": "Test User",
                "preferences": {}
            },
            "permissions": ["read", "write"],
            "roles": ["user"]
        }
    
    @pytest.mark.asyncio
    async def test_create_user_session(self, react_service, mock_user_data):
        """Test creating user session from JWT authentication data."""
        # Test session creation
        session_id = await react_service.create_user_session(mock_user_data)
        
        # Verify session was created
        assert session_id is not None
        assert session_id in react_service.user_sessions
        
        # Verify session data
        session_data = react_service.user_sessions[session_id]
        assert session_data["user_id"] == mock_user_data["user_id"]
        assert session_data["email"] == mock_user_data["email"]
        assert session_data["user_metadata"] == mock_user_data["user_metadata"]
        assert session_data["permissions"] == mock_user_data["permissions"]
    
    @pytest.mark.asyncio
    async def test_validate_session_access(self, react_service, mock_user_data):
        """Test session-based access control."""
        # Create session
        session_id = await react_service.create_user_session(mock_user_data)
        user_id = mock_user_data["user_id"]
        
        # Test valid access
        assert await react_service.validate_session_access(session_id, user_id) == True
        
        # Test invalid access (different user)
        assert await react_service.validate_session_access(session_id, "different-user") == False
        
        # Test non-existent session
        assert await react_service.validate_session_access("non-existent", user_id) == False
    
    @pytest.mark.asyncio
    async def test_extract_user_context(self, react_service, mock_user_data):
        """Test user context extraction from JWT tokens."""
        context = react_service._extract_user_context(mock_user_data)
        
        assert context["user_id"] == mock_user_data["user_id"]
        assert context["email"] == mock_user_data["email"]
        assert context["user_metadata"] == mock_user_data["user_metadata"]
        assert context["permissions"] == mock_user_data["permissions"]
        assert context["roles"] == mock_user_data["roles"]
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, react_service, mock_user_data):
        """Test cleanup of expired sessions."""
        # Create session
        session_id = await react_service.create_user_session(mock_user_data)
        
        # Manually set session as expired
        react_service.user_sessions[session_id]["last_activity"] = datetime.utcnow() - timedelta(hours=25)
        
        # Run cleanup
        cleaned_count = await react_service.cleanup_expired_sessions()
        
        # Verify session was cleaned up
        assert cleaned_count == 1
        assert session_id not in react_service.user_sessions
    
    @pytest.mark.asyncio
    async def test_refresh_session_tokens(self, react_service, mock_user_data):
        """Test OAuth token refresh for long-running conversations."""
        # Create session
        session_id = await react_service.create_user_session(mock_user_data)
        
        # Mock tool registry and auth context manager
        react_service.tool_registry = Mock()
        react_service.tool_registry.get_tool_metadata = AsyncMock(return_value=[
            {
                "name": "gmail_connector",
                "auth_requirements": {"type": "oauth2"}
            }
        ])
        
        react_service.auth_context_manager = Mock()
        react_service.auth_context_manager.get_connector_auth_tokens = AsyncMock(return_value={
            "access_token": "old_token",
            "refresh_token": "refresh_token"
        })
        react_service.auth_context_manager.refresh_token_if_needed = AsyncMock(return_value={
            "access_token": "new_token",
            "refresh_token": "refresh_token"
        })
        
        # Test token refresh
        result = await react_service.refresh_session_tokens(session_id)
        
        # Verify refresh was attempted
        assert result == True
        react_service.auth_context_manager.refresh_token_if_needed.assert_called_once()


class TestAuthContextManager:
    """Test authentication context manager."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth context manager for testing."""
        return AuthContextManager()
    
    @pytest.mark.asyncio
    async def test_check_tool_permissions(self, auth_manager):
        """Test permission checks before tool access."""
        user_id = "test-user-123"
        connector_name = "test_connector"
        
        # Mock connector registry
        with patch('app.services.auth_context_manager.get_connector_registry') as mock_registry:
            mock_connector_class = Mock()
            mock_connector_instance = Mock()
            mock_connector_instance.get_auth_requirements = AsyncMock(return_value=Mock(
                type=AuthType.NONE,
                fields={},
                instructions=""
            ))
            mock_connector_class.return_value = mock_connector_instance
            
            mock_registry.return_value.get_connector.return_value = mock_connector_class
            
            # Test permission check
            result = await auth_manager.check_tool_permissions(user_id, connector_name)
            
            assert result["allowed"] == True
            assert result["reason"] == "Permission granted"
    
    @pytest.mark.asyncio
    async def test_create_secure_execution_context(self, auth_manager):
        """Test secure execution context creation."""
        user_id = "test-user-123"
        connector_name = "test_connector"
        
        # Mock permission check and token retrieval
        auth_manager.check_tool_permissions = AsyncMock(return_value={
            "allowed": True,
            "reason": "Permission granted",
            "restrictions": [],
            "required_scopes": []
        })
        auth_manager.get_connector_auth_tokens = AsyncMock(return_value={
            "access_token": "test_token"
        })
        auth_manager.refresh_token_if_needed = AsyncMock(return_value={
            "access_token": "test_token"
        })
        
        # Test context creation
        context = await auth_manager.create_secure_execution_context(
            user_id, connector_name
        )
        
        assert context.user_id == user_id
        assert context.auth_tokens == {"access_token": "test_token"}
        assert context.request_id is not None
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, auth_manager):
        """Test permission denied scenario."""
        user_id = "test-user-123"
        connector_name = "restricted_connector"
        
        # Mock permission check to deny access
        auth_manager.check_tool_permissions = AsyncMock(return_value={
            "allowed": False,
            "reason": "Access denied",
            "restrictions": []
        })
        
        # Test that permission denied raises exception
        with pytest.raises(AuthenticationException):
            await auth_manager.create_secure_execution_context(
                user_id, connector_name
            )
    
    @pytest.mark.asyncio
    async def test_oauth_token_refresh(self, auth_manager):
        """Test OAuth token refresh functionality."""
        user_id = "test-user-123"
        connector_name = "gmail_connector"
        auth_tokens = {
            "access_token": "old_token",
            "refresh_token": "refresh_token"
        }
        
        # Mock Google OAuth refresh
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_token",
                "expires_in": 3600
            }
            mock_post.return_value = mock_response
            
            # Mock settings
            with patch('app.services.auth_context_manager.settings') as mock_settings:
                mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
                mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
                
                # Mock auth token service
                auth_manager._get_auth_token_service = AsyncMock()
                mock_auth_service = Mock()
                mock_auth_service.update_token = AsyncMock()
                auth_manager._get_auth_token_service.return_value = mock_auth_service
                
                # Test token refresh
                result = await auth_manager._refresh_google_oauth_token(
                    user_id, connector_name, auth_tokens
                )
                
                assert result is not None
                assert result["access_token"] == "new_token"
                assert result["refresh_token"] == "refresh_token"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])