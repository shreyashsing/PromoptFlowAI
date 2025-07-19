"""
Encryption utilities for secure token storage.
"""
import base64
import json
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self, secret_key: str):
        """Initialize encryption service with secret key."""
        self._fernet = self._create_fernet(secret_key)
    
    def _create_fernet(self, secret_key: str) -> Fernet:
        """Create Fernet instance from secret key."""
        # Use PBKDF2 to derive a key from the secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'promptflow_salt',  # In production, use a random salt per user
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(key)
    
    def encrypt_token(self, token_data: Dict[str, Any]) -> str:
        """Encrypt token data and return base64 encoded string."""
        try:
            # Convert to JSON string
            json_data = json.dumps(token_data, default=str)
            
            # Encrypt the data
            encrypted_data = self._fernet.encrypt(json_data.encode())
            
            # Return base64 encoded string
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> Dict[str, Any]:
        """Decrypt token data from base64 encoded string."""
        try:
            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
            
            # Decrypt the data
            decrypted_data = self._fernet.decrypt(encrypted_data)
            
            # Parse JSON
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise
    
    def encrypt_string(self, data: str) -> str:
        """Encrypt a string and return base64 encoded result."""
        try:
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"String encryption failed: {e}")
            raise
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """Decrypt a base64 encoded string."""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"String decryption failed: {e}")
            raise


# Global encryption service instance
encryption_service = EncryptionService(settings.SECRET_KEY)


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    return encryption_service