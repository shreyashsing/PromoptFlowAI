"""
Tests for authentication system.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from app.core.auth import AuthService
from app.core.encryption import EncryptionService
from app.services.auth_tokens import AuthTokenService
from app.models.database import CreateAuthTokenRequest
from app.models.base import AuthType


class TestEncryptionService:
    """Test encryption service functionality."""
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption."""
        encryption = EncryptionService("test_secret_key_12345")
        
        token_data = {
            "access_token": "test_access_token_123",
            "refresh_token": "test_refresh_token_456",
            "expires_in": 3600
        }
        
        # Encrypt token
        encrypted = encryption.encrypt_token(token_data)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        
        # Decrypt token
        decrypted = encryption.decrypt_token(encrypted)
        assert decrypted == token_data
    
    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption."""
        encryption = EncryptionService("test_secret_key_12345")
        
        test_string = "sensitive_api_key_12345"
        
        # Encrypt string
        encrypted = encryption.encrypt_string(test_string)
        assert isinstance(encrypted, str)
        assert encrypted != test_string
        
        # Decrypt string
        decrypted = encryption.decrypt_string(encrypted)
        assert decrypted == test_string


class TestAuthTokenService:
    """Test authentication token service."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Mock database client."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table
    
    @pytest.fixture
    def auth_token_service(self, mock_db_client):
        """Create auth token service with mocked database."""
        db_client, _ = mock_db_client
        return AuthTokenService(db_client)
    
    @pytest.mark.asyncio
    async def test_store_token(self, auth_token_service, mock_db_client):
        """Test storing an authentication token."""
        _, mock_table = mock_db_client
        
        # Mock successful upsert
        mock_table.upsert.return_value.execute.return_value.data = [{
            "id": "test-token-id",
            "user_id": "test-user-id",
            "connector_name": "gmail",
            "token_type": "oauth2",
            "encrypted_token": "encrypted_data",
            "token_metadata": {"token_hint": "****123"},
            "expires_at": None,
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        
        request = CreateAuthTokenRequest(
            connector_name="gmail",
            token_type=AuthType.OAUTH2,
            token_data={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token"
            }
        )
        
        result = await auth_token_service.store_token("test-user-id", request)
        
        assert result.connector_name == "gmail"
        assert result.token_type == AuthType.OAUTH2
        assert result.is_active == True
        
        # Verify database was called
        mock_table.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_token(self, auth_token_service, mock_db_client):
        """Test retrieving an authentication token."""
        _, mock_table = mock_db_client
        
        # Mock successful select
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
            "encrypted_token": auth_token_service.encryption.encrypt_token({
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token"
            }),
            "token_metadata": {"token_hint": "****123"},
            "expires_at": None
        }]
        
        result = await auth_token_service.get_token("test-user-id", "gmail", AuthType.OAUTH2)
        
        assert result is not None
        assert result["token_data"]["access_token"] == "test_access_token"
        assert result["token_data"]["refresh_token"] == "test_refresh_token"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, auth_token_service, mock_db_client):
        """Test retrieving a non-existent token."""
        _, mock_table = mock_db_client
        
        # Mock empty result
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        result = await auth_token_service.get_token("test-user-id", "nonexistent", AuthType.API_KEY)
        
        assert result is None


class TestAuthService:
    """Test authentication service."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Mock database client."""
        mock_client = Mock()
        mock_auth = Mock()
        mock_table = Mock()
        mock_client.auth = mock_auth
        mock_client.table.return_value = mock_table
        return mock_client, mock_auth, mock_table
    
    @pytest.fixture
    def auth_service(self, mock_db_client):
        """Create auth service with mocked database."""
        db_client, _, _ = mock_db_client
        return AuthService(db_client)
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service, mock_db_client):
        """Test successful token verification."""
        _, mock_auth, _ = mock_db_client
        
        # Mock successful token verification
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"full_name": "Test User"}
        
        mock_response = Mock()
        mock_response.user = mock_user
        mock_auth.get_user.return_value = mock_response
        
        result = await auth_service.verify_token("valid_token")
        
        assert result["user_id"] == "test-user-id"
        assert result["email"] == "test@example.com"
        assert result["user_metadata"]["full_name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service, mock_db_client):
        """Test invalid token verification."""
        _, mock_auth, _ = mock_db_client
        
        # Mock failed token verification
        mock_response = Mock()
        mock_response.user = None
        mock_auth.get_user.return_value = mock_response
        
        with pytest.raises(Exception):  # Should raise AuthenticationError
            await auth_service.verify_token("invalid_token")


if __name__ == "__main__":
    # Run basic encryption tests without pytest
    print("Running basic encryption tests...")
    
    try:
        test_encryption = TestEncryptionService()
        test_encryption.test_encrypt_decrypt_token()
        test_encryption.test_encrypt_decrypt_string()
        
        print("✅ All encryption tests passed!")
        print("\nTo run full test suite with database mocking:")
        print("pip install pytest pytest-asyncio")
        print("pytest backend/tests/test_auth.py -v")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()