#!/usr/bin/env python3
"""
Debug the rule-based detection for Clara AI specification.
"""
import re

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

message_lower = clara_ai_prompt.lower().strip()

print("Testing agent specification patterns:")

agent_specification_patterns = [
    r'\byou\s+are\b.*\bai\b',
    r'\byou\s+are\b.*\bassistant\b',
    r'\byou\s+are\b.*\bagent\b',
    r'\bintelligent\b.*\bassistant\b',
    r'\bresearch\b.*\bassistant\b',
    r'\bcapabilities\b.*:',
    r'\bunderstand\s+content\b',
    r'\bcite\b.*\bwrite\b',
    r'\bresearch\s+tools\b',
    r'\busability\s+features\b',
    r'\bresponse\s+behavior\b',
    r'\blimitations\b.*:',
    r'\bworld-class\b.*\bassistant\b',
    r'\btrusted\s+by\b.*\bresearchers\b'
]

for i, pattern in enumerate(agent_specification_patterns):
    match = re.search(pattern, message_lower)
    if match:
        print(f"✅ Pattern {i+1} MATCHED: {pattern}")
        print(f"   Match: '{match.group()}'")
    else:
        print(f"❌ Pattern {i+1} NO MATCH: {pattern}")

print(f"\nMessage length: {len(clara_ai_prompt)}")
print(f"Contains 'capabilities': {'capabilities' in message_lower}")
print(f"Contains 'features': {'features' in message_lower}")
print(f"Contains 'behavior': {'behavior' in message_lower}")
print(f"Contains 'limitations': {'limitations' in message_lower}")
print(f"Newline count: {clara_ai_prompt.count(chr(10))}")
print(f"Colon count: {clara_ai_prompt.count(':')}")

# Check detailed spec criteria
is_detailed_spec = len(clara_ai_prompt) > 500 and any([
    "capabilities" in message_lower,
    "features" in message_lower,
    "behavior" in message_lower,
    "limitations" in message_lower,
    clara_ai_prompt.count('\n') > 5,  # Multi-line structured request
    clara_ai_prompt.count(':') > 3    # Structured with colons (like specifications)
])

print(f"\nIs detailed spec: {is_detailed_spec}")

has_agent_specification = any(re.search(pattern, message_lower) for pattern in agent_specification_patterns)
print(f"Has agent specification: {has_agent_specification}")