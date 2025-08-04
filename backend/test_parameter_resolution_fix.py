#!/usr/bin/env python3
"""
Test parameter resolution fix for array-like access on single results.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.workflow_orchestrator import WorkflowOrchestrator

def test_parameter_resolution():
    """Test that parameter resolution handles array-like access correctly."""
    orchestrator = WorkflowOrchestrator()
    
    # Mock previous results similar to what we see in the logs
    previous_results = {
        "perplexity_search-0": {
            "data": {
                "response": "The top 5 most recent blog posts on blog.google...",
                "citations": [
                    "https://blog.google/intl/en-in/google-marketing-live-2025-driving-growth-with-search-youtube-ai/",
                    "https://blog.google/technology/developers/googl-link-shortening-update/",
                    "https://blog.google/intl/en-in/feed/ai-mode-in-google-search-rolling-out-in-india/",
                    "https://blog.google/products/gemini/gemini-2-5-deep-think/",
                    "https://blog.google/threat-analysis-group/tag-bulletin-q2-2025/"
                ],
                "model": "sonar",
                "finish_reason": "stop"
            }
        },
        "text_summarizer-1": {
            "data": {
                "summary": "I'm sorry, but I don't see any text to summarize. Please provide the text you'd like summarized.",
                "original_length": 1,
                "summary_length": 17,
                "style": "concise"
            }
        }
    }
    
    connector_to_node_map = {
        "perplexity_search": "perplexity_search-0",
        "text_summarizer": "text_summarizer-1"
    }
    
    # Test cases that match the actual Gmail workflow scenario
    test_cases = [
        # These should work (index 0) - the actual patterns from the Gmail body
        ("text_summarizer.result[0].summary", "I'm sorry, but I don't see any text to summarize. Please provide the text you'd like summarized."),
        ("perplexity_search.result[0].url", "https://blog.google/intl/en-in/google-marketing-live-2025-driving-growth-with-search-youtube-ai/"),
        
        # These should return None (index > 0)
        ("text_summarizer.result[1].summary", None),
        ("perplexity_search.result[1].url", None),
        ("text_summarizer.result[2].summary", None),
        ("perplexity_search.result[2].url", None),
        ("text_summarizer.result[3].summary", None),
        ("perplexity_search.result[3].url", None),
        ("text_summarizer.result[4].summary", None),
        ("perplexity_search.result[4].url", None),
        
        # Direct access should still work
        ("text_summarizer.summary", "I'm sorry, but I don't see any text to summarize. Please provide the text you'd like summarized."),
        ("perplexity_search.citations.0", "https://blog.google/intl/en-in/google-marketing-live-2025-driving-growth-with-search-youtube-ai/"),
    ]
    
    print("Testing parameter resolution...")
    
    for field_path, expected in test_cases:
        try:
            # Extract the reference part (everything before the first dot after the connector name)
            if "." in field_path:
                connector_name, rest = field_path.split(".", 1)
                reference = f"{connector_name}.{rest}"
            else:
                reference = field_path
            
            result = orchestrator._resolve_reference(reference, previous_results, connector_to_node_map)
            
            print(f"✓ {field_path}: {result}")
            
            if expected is not None and result != expected:
                print(f"  ⚠️  Expected: {expected}")
                
        except Exception as e:
            print(f"✗ {field_path}: ERROR - {e}")
    
    print("\nDone!")

if __name__ == "__main__":
    test_parameter_resolution()