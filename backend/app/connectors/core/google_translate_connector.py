"""
Google Translate Connector - OAuth-based translation service with full n8n feature parity.
"""
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException
from app.core.error_utils import handle_connector_errors, handle_external_api_errors

logger = logging.getLogger(__name__)


class GoogleTranslateConnector(BaseConnector):
    """
    Google Translate Connector for text translation using OAuth authentication.
    
    Supports text translation with automatic language detection and comprehensive
    language support through the Google Cloud Translation API.
    """
    
    def _get_connector_name(self) -> str:
        return "google_translate"
    
    def _get_category(self) -> str:
        return "utility"
    
    def get_example_params(self) -> Dict[str, Any]:
        """Get example parameters for Google Translate connector."""
        return {
            "operation": "translate",
            "text": "Hello, how are you?",
            "target_language": "es",
            "source_language": "auto"
        }
    
    def get_example_prompts(self) -> List[str]:
        """Get Google Translate-specific example prompts."""
        return [
            "Translate 'Hello world' to Spanish",
            "Translate this text to French: 'Good morning everyone'",
            "Detect the language of this text and translate it to German",
            "Translate multiple sentences to Japanese",
            "Convert English text to Chinese (Simplified)"
        ]
    
    def _define_schema(self) -> Dict[str, Any]:
        """Define the schema for Google Translate connector parameters."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["translate"],
                    "default": "translate",
                    "description": "The operation to perform"
                },
                "text": {
                    "type": "string",
                    "description": "The text to translate",
                    "minLength": 1
                },
                "target_language": {
                    "type": "string",
                    "description": "Target language code (e.g., 'es' for Spanish, 'fr' for French)",
                    "minLength": 2,
                    "maxLength": 10
                },
                "source_language": {
                    "type": "string",
                    "description": "Source language code (use 'auto' for automatic detection)",
                    "default": "auto"
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "html"],
                    "default": "text",
                    "description": "Format of the source text"
                },
                "model": {
                    "type": "string",
                    "enum": ["base", "nmt"],
                    "default": "nmt",
                    "description": "Translation model to use (nmt for Neural Machine Translation)"
                }
            },
            "required": ["text", "target_language"],
            "additionalProperties": False
        }
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """Get authentication requirements for Google Translate."""
        return AuthRequirements(
            type=AuthType.OAUTH2,
            oauth_scopes=[
                "https://www.googleapis.com/auth/cloud-translation"
            ],
            instructions="OAuth authentication required for Google Cloud Translation API access"
        )
    
    @handle_connector_errors
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Execute Google Translate operation."""
        try:
            # Validate required parameters
            operation = params.get("operation", "translate")
            text = params.get("text")
            target_language = params.get("target_language")
            
            if not text:
                raise ConnectorException("Text parameter is required")
            
            if not target_language:
                raise ConnectorException("Target language parameter is required")
            
            # Get authentication token
            auth_token = context.auth_context.get("access_token")
            if not auth_token:
                raise AuthenticationException("Google OAuth access token is required")
            
            # Execute the translation operation
            if operation == "translate":
                result = await self._translate_text(
                    text=text,
                    target_language=target_language,
                    source_language=params.get("source_language", "auto"),
                    format_type=params.get("format", "text"),
                    model=params.get("model", "nmt"),
                    auth_token=auth_token
                )
                
                return ConnectorResult(
                    success=True,
                    data=result,
                    message=f"Successfully translated text to {target_language}"
                )
            else:
                raise ConnectorException(f"Unsupported operation: {operation}")
                
        except Exception as e:
            logger.error(f"Google Translate connector execution failed: {str(e)}")
            return ConnectorResult(
                success=False,
                error=str(e),
                message="Google Translate operation failed"
            )
    
    async def _translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        format_type: str = "text",
        model: str = "nmt",
        auth_token: str = None
    ) -> Dict[str, Any]:
        """Translate text using Google Cloud Translation API."""
        
        # Prepare request payload
        payload = {
            "q": text,
            "target": target_language,
            "format": format_type,
            "model": model
        }
        
        # Add source language if not auto-detect
        if source_language and source_language != "auto":
            payload["source"] = source_language
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://translation.googleapis.com/language/translate/v2",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise AuthenticationException("Invalid or expired Google OAuth token")
                elif response.status_code == 403:
                    raise AuthenticationException("Google Cloud Translation API access denied. Check your project permissions.")
                elif response.status_code != 200:
                    error_detail = response.text
                    raise ConnectorException(f"Google Translate API error: {response.status_code} - {error_detail}")
                
                response_data = response.json()
                
                # Extract translation result
                if "data" in response_data and "translations" in response_data["data"]:
                    translations = response_data["data"]["translations"]
                    if translations:
                        translation = translations[0]
                        
                        result = {
                            "translatedText": translation.get("translatedText", ""),
                            "detectedSourceLanguage": translation.get("detectedSourceLanguage"),
                            "originalText": text,
                            "targetLanguage": target_language,
                            "sourceLanguage": source_language if source_language != "auto" else translation.get("detectedSourceLanguage"),
                            "model": model,
                            "format": format_type
                        }
                        
                        return result
                    else:
                        raise ConnectorException("No translation results returned from Google Translate API")
                else:
                    raise ConnectorException("Invalid response format from Google Translate API")
                    
            except httpx.TimeoutException:
                raise ConnectorException("Google Translate API request timed out")
            except httpx.RequestError as e:
                raise ConnectorException(f"Network error while calling Google Translate API: {str(e)}")
    
    async def get_supported_languages(self, auth_token: str) -> List[Dict[str, str]]:
        """Get list of supported languages from Google Translate API."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://translation.googleapis.com/language/translate/v2/languages",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "data" in response_data and "languages" in response_data["data"]:
                        return [
                            {
                                "code": lang["language"],
                                "name": lang["language"].upper()
                            }
                            for lang in response_data["data"]["languages"]
                        ]
                
                return []
                
            except Exception as e:
                logger.warning(f"Failed to fetch supported languages: {str(e)}")
                return []
    
    def validate_language_code(self, language_code: str) -> bool:
        """Validate if a language code is supported."""
        # Common language codes supported by Google Translate
        common_languages = {
            'af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'ceb', 'ny', 'zh-cn', 'zh-tw',
            'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'tl', 'fi', 'fr', 'fy', 'gl', 'ka', 'de', 'el', 'gu',
            'ht', 'ha', 'haw', 'iw', 'he', 'hi', 'hmn', 'hu', 'is', 'ig', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk',
            'km', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn',
            'my', 'ne', 'no', 'or', 'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sd',
            'si', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'ug', 'uz',
            'vi', 'cy', 'xh', 'yi', 'yo', 'zu'
        }
        
        return language_code.lower() in common_languages or language_code == "auto"
    
    def get_language_name(self, language_code: str) -> str:
        """Get human-readable language name from code."""
        language_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian',
            'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean', 'zh-cn': 'Chinese (Simplified)',
            'zh-tw': 'Chinese (Traditional)', 'ar': 'Arabic', 'hi': 'Hindi', 'th': 'Thai', 'vi': 'Vietnamese',
            'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish', 'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian',
            'fi': 'Finnish', 'cs': 'Czech', 'hu': 'Hungarian', 'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian',
            'sk': 'Slovak', 'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian', 'uk': 'Ukrainian',
            'be': 'Belarusian', 'mk': 'Macedonian', 'sr': 'Serbian', 'bs': 'Bosnian', 'sq': 'Albanian', 'mt': 'Maltese',
            'ga': 'Irish', 'cy': 'Welsh', 'is': 'Icelandic', 'eu': 'Basque', 'ca': 'Catalan', 'gl': 'Galician'
        }
        
        return language_names.get(language_code.lower(), language_code.upper())