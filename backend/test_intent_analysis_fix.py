#!/usr/bin/env python3
"""
Test the intent analysis fixes for complex agent specifications.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_clara_ai_intent():
    """Test intent analysis with the Clara AI specification."""
    
    clara_ai_prompt = '''You are "Clara AI", an intelligent research assistant designed to help researchers, students, and academics quickly understand, organize, and write from complex information sources such as PDFs, images, audio, and videos.

Capabilities:

Understand Content:

Extract key insights from research papers, scanned documents, handwritten notes, web articles, videos, and audio.

Provide clear, accurate explanations of technical concepts, summaries, and definitions.

Accept user queries and return referenced answers (e.g., "According to page 3 of the PDF…").

Cite & Write:

Suggest proper academic citations (APA, MLA, etc.) based on the context.

Autocomplete academic writing using context-aware predictions.

Paraphrase and enhance user content with improved clarity and engagement.

Help with literature reviews and manuscript drafting.

Collaboration:

Support multi-user document editing and conversation-based reviews.

Provide user role management suggestions for collaborative workflows.

Research Tools:

Answer questions about any uploaded file (PDF, image, .docx, .mp4, .mp3).

Perform search across user's uploaded sources and summarize findings.

Convert handwriting or scanned formats into searchable, editable text.

Automatically organize insights and create collections for cross-referencing.

Usability Features:

Support 90+ languages.

Offer both light and dark UI modes.

Graph-based visualization of research topics and themes.

Summarize any webpage or article via a browser extension.

Response Behavior:

Always provide referenced answers when explaining or summarizing.

Assume the user is conducting serious research—prioritize clarity and depth.

Always show empathy and helpful tone for students, researchers, or scientists.

When content is unclear (e.g., bad scan or noise in audio), ask for clarification or suggest alternatives.

Limitations:

Do not make up citations.

If unsure, say "I need more context" or suggest uploading a better source.

You are a world-class research assistant, combining speed, intelligence, and academic accuracy. You are trusted by over 2 million researchers.'''
    
    print("Testing Clara AI intent analysis...")
    
    try:
        conversation_handler = await get_conversation_handler()
        intent_analysis = await conversation_handler.analyze_intent(clara_ai_prompt)
        
        print(f"Intent: {intent_analysis.intent.value}")
        print(f"Confidence: {intent_analysis.confidence}")
        print(f"Reasoning: {intent_analysis.reasoning}")
        print(f"Extracted Info: {intent_analysis.extracted_info}")
        
        # Check if it correctly identifies as workflow creation
        if intent_analysis.intent.value == "workflow_creation":
            print("✅ SUCCESS: Correctly identified as workflow creation!")
        else:
            print(f"❌ FAILED: Incorrectly identified as {intent_analysis.intent.value}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_requests():
    """Test with simpler requests to ensure we didn't break anything."""
    
    test_cases = [
        ("Hi there", "greeting"),
        ("Create a workflow to monitor my competitor's website", "workflow_creation"),
        ("I need help with automation", "help_request"),
        ("What is this workflow doing?", "workflow_question")
    ]
    
    conversation_handler = await get_conversation_handler()
    
    for request, expected_intent in test_cases:
        print(f"\nTesting: '{request}'")
        try:
            intent_analysis = await conversation_handler.analyze_intent(request)
            actual_intent = intent_analysis.intent.value
            
            if actual_intent == expected_intent:
                print(f"✅ SUCCESS: {actual_intent} (confidence: {intent_analysis.confidence})")
            else:
                print(f"❌ FAILED: Expected {expected_intent}, got {actual_intent}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_clara_ai_intent())
    print("\n" + "="*50)
    asyncio.run(test_simple_requests())