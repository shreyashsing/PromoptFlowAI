#!/usr/bin/env python3
"""
Debug the synthesis logic for intent analysis.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import IntelligentConversationHandler, ConversationIntent, IntentAnalysis

async def debug_synthesis():
    """Debug the synthesis logic."""
    
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
    
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    # Test rule-based detection directly
    print("Testing rule-based detection:")
    rule_result = handler._rule_based_intent_detection(clara_ai_prompt)
    print(f"Rule-based result: {rule_result.intent.value} (confidence: {rule_result.confidence})")
    print(f"Reasoning: {rule_result.reasoning}")
    
    # Test AI analysis (will likely fail with JSON parsing)
    print("\nTesting AI analysis:")
    ai_result = await handler._ai_intent_analysis(clara_ai_prompt)
    if ai_result:
        print(f"AI result: {ai_result.intent.value} (confidence: {ai_result.confidence})")
        print(f"Reasoning: {ai_result.reasoning}")
    else:
        print("AI analysis returned None (JSON parsing failed)")
    
    # Test synthesis
    print("\nTesting synthesis:")
    final_result = await handler._synthesize_intent_analysis(clara_ai_prompt, None, rule_result, ai_result)
    print(f"Final result: {final_result.intent.value} (confidence: {final_result.confidence})")
    print(f"Reasoning: {final_result.reasoning}")

if __name__ == "__main__":
    asyncio.run(debug_synthesis())