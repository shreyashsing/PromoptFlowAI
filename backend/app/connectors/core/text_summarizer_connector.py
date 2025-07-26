"""
Text Summarizer Connector - AI-powered text summarization.
"""
import json
from typing import Dict, Any, List, Optional
import httpx

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext, AuthRequirements
from app.models.base import AuthType
from app.core.exceptions import ConnectorException, AuthenticationException
from app.core.config import settings


class TextSummarizerConnector(BaseConnector):
    """
    Text Summarizer Connector for AI-powered text summarization.
    
    Uses Azure OpenAI to summarize long text content into concise summaries.
    """
    
    def _get_connector_name(self) -> str:
        return "text_summarizer"
    
    def _get_category(self) -> str:
        return "ai_services"
    
    def _define_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content to summarize"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of the summary in words",
                    "default": 100
                },
                "style": {
                    "type": "string",
                    "description": "Summary style",
                    "enum": ["concise", "detailed", "bullet_points"],
                    "default": "concise"
                }
            },
            "required": ["text"]
        }
    
    async def execute(self, parameters: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """Execute text summarization."""
        try:
            text = parameters["text"]
            max_length = parameters.get("max_length", 100)
            style = parameters.get("style", "concise")
            
            # Detect if text contains citations/sources that should be preserved
            has_citations = "📚 **Sources:**" in text or "Sources:" in text or "Citations:" in text
            
            # Create summarization prompt based on style and citation preservation
            if has_citations:
                # Special handling for text with citations - instruct AI to preserve them
                if style == "bullet_points":
                    prompt = f"""Summarize the following text in bullet points (max {max_length} words for the summary content). 

IMPORTANT: The text contains source links/citations. Please:
1. Create a concise bullet-point summary of the main content
2. PRESERVE the complete "📚 **Sources:**" section exactly as provided at the end
3. Do not modify, remove, or shorten any of the source URLs

Text to summarize:
{text}"""
                elif style == "detailed":
                    prompt = f"""Provide a detailed summary of the following text (max {max_length} words for the summary content).

IMPORTANT: The text contains source links/citations. Please:
1. Create a comprehensive summary of the main content  
2. PRESERVE the complete "📚 **Sources:**" section exactly as provided at the end
3. Do not modify, remove, or shorten any of the source URLs

Text to summarize:
{text}"""
                else:
                    prompt = f"""Provide a concise summary of the following text (max {max_length} words for the summary content).

IMPORTANT: The text contains source links/citations. Please:
1. Create a brief summary of the main content
2. PRESERVE the complete "📚 **Sources:**" section exactly as provided at the end  
3. Do not modify, remove, or shorten any of the source URLs

Text to summarize:
{text}"""
            else:
                # Standard summarization without citations
                if style == "bullet_points":
                    prompt = f"Summarize the following text in bullet points (max {max_length} words):\n\n{text}"
                elif style == "detailed":
                    prompt = f"Provide a detailed summary of the following text (max {max_length} words):\n\n{text}"
                else:
                    prompt = f"Provide a concise summary of the following text (max {max_length} words):\n\n{text}"
            
            # Use Azure OpenAI for summarization
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions",
                    headers={
                        "api-key": settings.AZURE_OPENAI_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_length * 3 if has_citations else max_length * 2,  # Extra space for citations
                        "temperature": 0.3
                    },
                    params={"api-version": settings.AZURE_OPENAI_API_VERSION}
                )
                
                if response.status_code != 200:
                    raise ConnectorException(f"OpenAI API error: {response.status_code} - {response.text}")
                
                result = response.json()
                summary = result["choices"][0]["message"]["content"].strip()
                
                return ConnectorResult(
                    success=True,
                    data={
                        "summary": summary,
                        "original_length": len(text.split()),
                        "summary_length": len(summary.split()),
                        "style": style,
                        "preserved_citations": has_citations
                    }
                )
                
        except Exception as e:
            return ConnectorResult(
                success=False,
                error=f"Text summarization failed: {str(e)}"
            )
    
    async def get_auth_requirements(self) -> AuthRequirements:
        """Text summarizer uses Azure OpenAI, no additional auth needed."""
        return AuthRequirements(
            type=AuthType.NONE,
            fields={}
        )