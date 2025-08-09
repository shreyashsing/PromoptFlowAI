"""
Test Google Translate Connector implementation.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from app.connectors.core.google_translate_connector import GoogleTranslateConnector
from app.models.connector import ConnectorExecutionContext, ConnectorResult
from app.core.exceptions import ConnectorException, AuthenticationException


class TestGoogleTranslateConnector:
    """Test cases for Google Translate Connector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.connector = GoogleTranslateConnector()
        self.mock_context = ConnectorExecutionContext(
            user_id="test-user",
            auth_context={"access_token": "mock-token"},
            previous_results={}
        )
    
    def test_connector_initialization(self):
        """Test connector initialization and properties."""
        assert self.connector.name == "google_translate"
        assert self.connector.category == "utility"
        assert "Google Translate Connector" in self.connector.description
        
        # Test schema structure
        schema = self.connector.schema
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "target_language" in schema["properties"]
        assert "operation" in schema["properties"]
        assert schema["required"] == ["text", "target_language"]
    
    def test_example_params(self):
        """Test example parameters."""
        params = self.connector.get_example_params()
        assert "operation" in params
        assert "text" in params
        assert "target_language" in params
        assert params["operation"] == "translate"
    
    def test_example_prompts(self):
        """Test example prompts."""
        prompts = self.connector.get_example_prompts()
        assert len(prompts) > 0
        assert any("translate" in prompt.lower() for prompt in prompts)
    
    async def test_auth_requirements(self):
        """Test authentication requirements."""
        auth_req = await self.connector.get_auth_requirements()
        assert auth_req.type.value == "oauth2"
        assert "https://www.googleapis.com/auth/cloud-translation" in auth_req.oauth_scopes
    
    def test_language_validation(self):
        """Test language code validation."""
        # Valid language codes
        assert self.connector.validate_language_code("en")
        assert self.connector.validate_language_code("es")
        assert self.connector.validate_language_code("fr")
        assert self.connector.validate_language_code("auto")
        
        # Invalid language codes
        assert not self.connector.validate_language_code("invalid")
        assert not self.connector.validate_language_code("")
    
    def test_language_names(self):
        """Test language name mapping."""
        assert self.connector.get_language_name("en") == "English"
        assert self.connector.get_language_name("es") == "Spanish"
        assert self.connector.get_language_name("fr") == "French"
        assert self.connector.get_language_name("unknown") == "UNKNOWN"
    
    @patch('httpx.AsyncClient')
    async def test_successful_translation(self, mock_client):
        """Test successful text translation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "translations": [{
                    "translatedText": "Hola mundo",
                    "detectedSourceLanguage": "en"
                }]
            }
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Test parameters
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "es",
            "source_language": "auto"
        }
        
        # Execute translation
        result = await self.connector.execute(params, self.mock_context)
        
        # Verify result
        assert result.success is True
        assert "translatedText" in result.data
        assert result.data["translatedText"] == "Hola mundo"
        assert result.data["detectedSourceLanguage"] == "en"
        assert result.data["originalText"] == "Hello world"
        assert result.data["targetLanguage"] == "es"
    
    @patch('httpx.AsyncClient')
    async def test_translation_with_source_language(self, mock_client):
        """Test translation with specified source language."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "translations": [{
                    "translatedText": "Bonjour le monde"
                }]
            }
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Test parameters with specific source language
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "fr",
            "source_language": "en",
            "format": "text",
            "model": "nmt"
        }
        
        # Execute translation
        result = await self.connector.execute(params, self.mock_context)
        
        # Verify result
        assert result.success is True
        assert result.data["translatedText"] == "Bonjour le monde"
        assert result.data["sourceLanguage"] == "en"
        assert result.data["format"] == "text"
        assert result.data["model"] == "nmt"
    
    async def test_missing_text_parameter(self):
        """Test error handling for missing text parameter."""
        params = {
            "operation": "translate",
            "target_language": "es"
            # Missing 'text' parameter
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "Text parameter is required" in result.error
    
    async def test_missing_target_language_parameter(self):
        """Test error handling for missing target language parameter."""
        params = {
            "operation": "translate",
            "text": "Hello world"
            # Missing 'target_language' parameter
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "Target language parameter is required" in result.error
    
    async def test_missing_auth_token(self):
        """Test error handling for missing authentication token."""
        context_no_auth = ConnectorExecutionContext(
            user_id="test-user",
            auth_context={},  # No access token
            previous_results={}
        )
        
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "es"
        }
        
        result = await self.connector.execute(params, context_no_auth)
        
        assert result.success is False
        assert "access token is required" in result.error
    
    @patch('httpx.AsyncClient')
    async def test_api_authentication_error(self, mock_client):
        """Test handling of API authentication errors."""
        # Mock 401 authentication error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "es"
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "Invalid or expired Google OAuth token" in result.error
    
    @patch('httpx.AsyncClient')
    async def test_api_permission_error(self, mock_client):
        """Test handling of API permission errors."""
        # Mock 403 permission error
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access denied"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "es"
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "Google Cloud Translation API access denied" in result.error
    
    @patch('httpx.AsyncClient')
    async def test_api_timeout_error(self, mock_client):
        """Test handling of API timeout errors."""
        # Mock timeout exception
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = asyncio.TimeoutError()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        params = {
            "operation": "translate",
            "text": "Hello world",
            "target_language": "es"
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "timed out" in result.error
    
    @patch('httpx.AsyncClient')
    async def test_get_supported_languages(self, mock_client):
        """Test fetching supported languages."""
        # Mock successful languages API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "languages": [
                    {"language": "en"},
                    {"language": "es"},
                    {"language": "fr"}
                ]
            }
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        languages = await self.connector.get_supported_languages("mock-token")
        
        assert len(languages) == 3
        assert {"code": "en", "name": "EN"} in languages
        assert {"code": "es", "name": "ES"} in languages
        assert {"code": "fr", "name": "FR"} in languages
    
    async def test_unsupported_operation(self):
        """Test error handling for unsupported operations."""
        params = {
            "operation": "unsupported_operation",
            "text": "Hello world",
            "target_language": "es"
        }
        
        result = await self.connector.execute(params, self.mock_context)
        
        assert result.success is False
        assert "Unsupported operation" in result.error


async def test_google_translate_connector_integration():
    """Integration test for Google Translate connector."""
    print("\n🔄 Testing Google Translate Connector Integration...")
    
    try:
        # Initialize connector
        connector = GoogleTranslateConnector()
        
        # Test basic properties
        assert connector.name == "google_translate"
        assert connector.category == "utility"
        print("   ✅ Connector initialization successful")
        
        # Test schema validation
        schema = connector.schema
        assert "text" in schema["properties"]
        assert "target_language" in schema["properties"]
        print("   ✅ Schema validation successful")
        
        # Test auth requirements
        auth_req = await connector.get_auth_requirements()
        assert auth_req.type.value == "oauth2"
        print("   ✅ Auth requirements validation successful")
        
        # Test language validation
        assert connector.validate_language_code("en")
        assert connector.validate_language_code("es")
        assert not connector.validate_language_code("invalid")
        print("   ✅ Language validation successful")
        
        print("   🎉 Google Translate connector integration test passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Google Translate connector integration test failed: {str(e)}")
        return False


async def main():
    """Run all Google Translate connector tests."""
    print("🚀 Starting Google Translate Connector Tests")
    
    # Run integration test
    integration_success = await test_google_translate_connector_integration()
    
    if integration_success:
        print("🎉 All Google Translate connector tests passed!")
    else:
        print("❌ Some Google Translate connector tests failed")
    
    return integration_success


if __name__ == "__main__":
    asyncio.run(main())