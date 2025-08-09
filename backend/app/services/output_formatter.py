"""
Universal Output Formatter

This service provides intelligent formatting for all connector outputs to ensure
clean, user-friendly results across the entire platform.
"""
import json
import re
import logging
from typing import Any, Dict, List, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormattingRule:
    """Represents a formatting rule for cleaning output."""
    pattern: str
    replacement: str
    description: str


class UniversalOutputFormatter:
    """
    Universal formatter that cleans and enhances output from all connectors.
    
    This ensures consistent, professional formatting across:
    - Gmail emails
    - Notion pages
    - Airtable records
    - All other connector outputs
    """
    
    def __init__(self):
        self.formatting_rules = self._initialize_formatting_rules()
    
    def _initialize_formatting_rules(self) -> List[FormattingRule]:
        """Initialize comprehensive formatting rules."""
        return [
            # Remove technical metadata
            FormattingRule(
                pattern=r"'[a-zA-Z_]+': \d+,?\s*",
                replacement="",
                description="Remove technical metadata like 'original_length': 296"
            ),
            FormattingRule(
                pattern=r"'[a-zA-Z_]+': '[^']*',?\s*",
                replacement="",
                description="Remove technical string metadata"
            ),
            FormattingRule(
                pattern=r"'[a-zA-Z_]+': (True|False),?\s*",
                replacement="",
                description="Remove boolean metadata"
            ),
            
            # Clean up citation formatting
            FormattingRule(
                pattern=r"\*\*Sources:\*\*\s*\n((?:\d+\.\s*https?://[^\n]+\n?)+)",
                replacement=r"\n\n**Sources:**\n\1",
                description="Improve source formatting"
            ),
            
            # Remove JSON-like structures at the beginning/end
            FormattingRule(
                pattern=r"^\{[^}]*\}\s*",
                replacement="",
                description="Remove JSON objects at start"
            ),
            FormattingRule(
                pattern=r"\s*\{[^}]*\}$",
                replacement="",
                description="Remove JSON objects at end"
            ),
            
            # Clean up multiple newlines
            FormattingRule(
                pattern=r"\n{3,}",
                replacement="\n\n",
                description="Reduce excessive newlines"
            ),
            
            # Fix link formatting in citations
            FormattingRule(
                pattern=r"(\d+)\.\s*(https?://[^\s\]]+)(\]?\([^)]*\))?",
                replacement=r"\1. \2",
                description="Clean up citation links"
            ),
            
            # Remove trailing commas and brackets
            FormattingRule(
                pattern=r",\s*[\]}]\s*$",
                replacement="",
                description="Remove trailing JSON syntax"
            ),
        ]
    
    def format_output(self, raw_output: Any, connector_name: str = None) -> str:
        """
        Format any connector output into clean, user-friendly text.
        
        Args:
            raw_output: Raw output from any connector
            connector_name: Name of the connector (for context-specific formatting)
            
        Returns:
            Clean, formatted string ready for end users
        """
        try:
            # Convert to string if needed
            if isinstance(raw_output, dict):
                formatted_text = self._format_dict_output(raw_output, connector_name)
            elif isinstance(raw_output, list):
                formatted_text = self._format_list_output(raw_output, connector_name)
            elif isinstance(raw_output, str):
                formatted_text = raw_output
            else:
                formatted_text = str(raw_output)
            
            # Apply universal formatting rules
            formatted_text = self._apply_formatting_rules(formatted_text)
            
            # Apply connector-specific formatting
            if connector_name:
                formatted_text = self._apply_connector_specific_formatting(formatted_text, connector_name)
            
            # Final cleanup
            formatted_text = self._final_cleanup(formatted_text)
            
            return formatted_text.strip()
            
        except Exception as e:
            logger.error(f"Error formatting output: {e}")
            # Return safe fallback
            return str(raw_output) if raw_output else ""
    
    def _format_dict_output(self, data: Dict[str, Any], connector_name: str = None) -> str:
        """Format dictionary output intelligently."""
        
        # Handle common response patterns
        if 'summary' in data and isinstance(data['summary'], str):
            # This is likely a summarizer response - extract just the summary
            return data['summary']
        
        if 'response' in data and isinstance(data['response'], str):
            # This is likely a search/AI response
            response_text = data['response']
            
            # Add citations if available
            if 'citations' in data and data['citations']:
                citations = self._format_citations(data['citations'])
                if citations:
                    response_text += f"\n\n**Sources:**\n{citations}"
            
            return response_text
        
        if 'content' in data and isinstance(data['content'], str):
            return data['content']
        
        if 'result' in data and isinstance(data['result'], str):
            return data['result']
        
        if 'message' in data and isinstance(data['message'], str):
            return data['message']
        
        # For other dictionaries, extract meaningful content
        meaningful_content = []
        for key, value in data.items():
            if key in ['original_length', 'summary_length', 'style', 'preserved_citations']:
                continue  # Skip technical metadata
            
            if isinstance(value, str) and len(value) > 10:
                meaningful_content.append(value)
            elif isinstance(value, (list, dict)):
                formatted_value = self.format_output(value, connector_name)
                if formatted_value:
                    meaningful_content.append(formatted_value)
        
        return '\n\n'.join(meaningful_content)
    
    def _format_list_output(self, data: List[Any], connector_name: str = None) -> str:
        """Format list output intelligently."""
        formatted_items = []
        
        for item in data:
            if isinstance(item, dict):
                formatted_item = self._format_dict_output(item, connector_name)
            elif isinstance(item, str):
                formatted_item = item
            else:
                formatted_item = str(item)
            
            if formatted_item and formatted_item.strip():
                formatted_items.append(formatted_item.strip())
        
        return '\n\n'.join(formatted_items)
    
    def _format_citations(self, citations: List[Any]) -> str:
        """Format citations in a clean, readable way."""
        if not citations:
            return ""
        
        formatted_citations = []
        for i, citation in enumerate(citations, 1):
            if isinstance(citation, str):
                # Clean URL citation
                clean_url = citation.strip()
                formatted_citations.append(f"{i}. {clean_url}")
            elif isinstance(citation, dict):
                # Structured citation
                title = citation.get('title', citation.get('url', 'Unknown'))
                url = citation.get('url', '')
                if url:
                    formatted_citations.append(f"{i}. [{title}]({url})")
                else:
                    formatted_citations.append(f"{i}. {title}")
        
        return '\n'.join(formatted_citations)
    
    def _apply_formatting_rules(self, text: str) -> str:
        """Apply all universal formatting rules."""
        for rule in self.formatting_rules:
            try:
                text = re.sub(rule.pattern, rule.replacement, text, flags=re.MULTILINE | re.DOTALL)
            except Exception as e:
                logger.warning(f"Failed to apply formatting rule '{rule.description}': {e}")
        
        return text
    
    def _apply_connector_specific_formatting(self, text: str, connector_name: str) -> str:
        """Apply connector-specific formatting rules."""
        
        if connector_name == 'gmail_connector':
            return self._format_for_email(text)
        elif connector_name == 'notion':
            return self._format_for_notion(text)
        elif connector_name == 'airtable':
            return self._format_for_airtable(text)
        elif connector_name == 'text_summarizer':
            return self._format_for_summary(text)
        elif connector_name == 'perplexity_search':
            return self._format_for_search_results(text)
        
        return text
    
    def _format_for_email(self, text: str) -> str:
        """Format text specifically for email content."""
        # Ensure proper email formatting
        text = re.sub(r'\n{2,}', '\n\n', text)  # Normalize paragraph breaks
        
        # Ensure sources are properly formatted for email
        text = re.sub(
            r'\*\*Sources:\*\*\s*\n',
            '\n\nSources:\n',
            text
        )
        
        return text
    
    def _format_for_notion(self, text: str) -> str:
        """Format text for Notion pages."""
        # Notion supports markdown, so keep formatting
        return text
    
    def _format_for_airtable(self, text: str) -> str:
        """Format text for Airtable records."""
        # Airtable prefers plain text, so remove markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Remove links, keep text
        return text
    
    def _format_for_summary(self, text: str) -> str:
        """Format text from summarizer."""
        # Summaries should be clean and concise
        return text
    
    def _format_for_search_results(self, text: str) -> str:
        """Format search results."""
        # Ensure citations are properly formatted
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass."""
        # Remove any remaining technical artifacts
        text = re.sub(r"^\s*['\"].*?['\"]:\s*", "", text, flags=re.MULTILINE)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'^\s+|\s+$', '', text)
        
        # Remove any remaining JSON-like artifacts
        text = re.sub(r'[{}]', '', text)
        text = re.sub(r"'[^']*':\s*[^,\n]*,?\s*", '', text)
        
        return text


# Global formatter instance
_formatter_instance = None

def get_output_formatter() -> UniversalOutputFormatter:
    """Get the global output formatter instance."""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = UniversalOutputFormatter()
    return _formatter_instance

def format_connector_output(raw_output: Any, connector_name: str = None) -> str:
    """
    Convenience function to format any connector output.
    
    Args:
        raw_output: Raw output from any connector
        connector_name: Name of the connector for context-specific formatting
        
    Returns:
        Clean, formatted string ready for end users
    """
    formatter = get_output_formatter()
    return formatter.format_output(raw_output, connector_name)