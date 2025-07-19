"""
Basic tests for authentication system without external dependencies.
"""
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.encryption import EncryptionService


def test_encryption_service():
    """Test encryption service functionality."""
    print("Testing EncryptionService...")
    
    encryption = EncryptionService("test_secret_key_12345")
    
    # Test token encryption/decryption
    token_data = {
        "access_token": "test_access_token_123",
        "refresh_token": "test_refresh_token_456",
        "expires_in": 3600
    }
    
    # Encrypt token
    encrypted = encryption.encrypt_token(token_data)
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    print("✅ Token encryption successful")
    
    # Decrypt token
    decrypted = encryption.decrypt_token(encrypted)
    assert decrypted == token_data
    print("✅ Token decryption successful")
    
    # Test string encryption/decryption
    test_string = "sensitive_api_key_12345"
    
    # Encrypt string
    encrypted_str = encryption.encrypt_string(test_string)
    assert isinstance(encrypted_str, str)
    assert encrypted_str != test_string
    print("✅ String encryption successful")
    
    # Decrypt string
    decrypted_str = encryption.decrypt_string(encrypted_str)
    assert decrypted_str == test_string
    print("✅ String decryption successful")


def test_models_import():
    """Test that all models can be imported."""
    print("Testing model imports...")
    
    try:
        from app.models.base import WorkflowStatus, ConversationState, AuthType
        from app.models.database import UserProfile, WorkflowDB, ConnectorDB
        print("✅ Base models imported successfully")
        
        # Test enum values
        assert WorkflowStatus.DRAFT == "draft"
        assert AuthType.OAUTH2 == "oauth2"
        print("✅ Enum values correct")
        
    except ImportError as e:
        print(f"❌ Model import failed: {e}")
        raise


def test_config_import():
    """Test configuration import."""
    print("Testing configuration...")
    
    try:
        from app.core.config import settings
        print("✅ Configuration imported successfully")
        
        # Check that settings object exists
        assert hasattr(settings, 'APP_NAME')
        assert hasattr(settings, 'SUPABASE_URL')
        print("✅ Configuration attributes present")
        
    except ImportError as e:
        print(f"❌ Configuration import failed: {e}")
        raise


def main():
    """Run all basic tests."""
    print("Running basic authentication system tests...\n")
    
    try:
        test_config_import()
        print()
        
        test_models_import()
        print()
        
        test_encryption_service()
        print()
        
        print("🎉 All basic tests passed!")
        print("\nNext steps:")
        print("1. Set up your Supabase project and update .env file")
        print("2. Run: python scripts/init_db.py")
        print("3. Start the server: uvicorn app.main:app --reload")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)