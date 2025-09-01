#!/usr/bin/env python3
"""
Debug pattern matching for technical questions.
"""
import re

def test_pattern_matching():
    user_message = "how is youtube extracting data from video and transferring it to text summariser"
    message_lower = user_message.lower()
    
    print(f"Testing message: '{user_message}'")
    print(f"Lowercase: '{message_lower}'")
    print("="*60)
    
    # Test technical question patterns
    technical_question_patterns = [
        r'\bhow\s+(is|are|does|do)\b.*\b(processing|processed|working|works|storing|stored|sending|sent|passing|passed)\b',
        r'\bwhat\s+(is|are|does|do)\b.*\b(connector|step|parameter|data|content|output|input)\b',
        r'\bhow\s+(does|do|is|are)\b.*\b(youtube|gmail|sheets|drive|notion|perplexity|summarizer|translate)\b',
        r'\bwhat\s+(data|content|information)\b.*\b(stored|processed|extracted|passed|sent|received)\b',
        r'\bhow\s+.*\b(data flow|data flows|content flows|information flows)\b',
        r'\bwhat\s+.*\b(parameters|configuration|settings|options)\b.*\b(used|needed|required)\b',
        r'\bhow\s+.*\b(extracted|content|data)\b.*\b(from|to)\b.*\b(youtube|gmail|sheets|drive|notion)\b',
        r'\bwhat\s+.*\b(format|structure|type)\b.*\b(data|content|output|input)\b',
        r'\bhow\s+.*\b(connector|step|tool)\b.*\b(communicates?|connects?|integrates?)\b',
        r'\bwhat\s+.*\b(api|endpoint|method|function)\b.*\b(called|used|invoked)\b'
    ]
    
    print("Testing technical question patterns:")
    for i, pattern in enumerate(technical_question_patterns):
        match = re.search(pattern, message_lower)
        if match:
            print(f"✅ Pattern {i+1} MATCHED: {pattern}")
            print(f"   Match: '{match.group()}'")
        else:
            print(f"❌ Pattern {i+1} NO MATCH: {pattern}")
    
    # Test connector names
    connector_names = [
        'youtube', 'gmail', 'sheets', 'drive', 'notion', 'perplexity', 
        'summarizer', 'translate', 'airtable', 'webhook', 'http'
    ]
    
    print(f"\nTesting connector names:")
    mentions_connector = any(connector in message_lower for connector in connector_names)
    mentioned_connectors = [c for c in connector_names if c in message_lower]
    print(f"Mentions connector: {mentions_connector}")
    print(f"Mentioned connectors: {mentioned_connectors}")
    
    # Test question words
    question_words = ['how', 'what', 'processing', 'data', 'content']
    has_question_words = any(word in message_lower for word in question_words)
    found_question_words = [word for word in question_words if word in message_lower]
    print(f"Has question words: {has_question_words}")
    print(f"Found question words: {found_question_words}")
    
    # Final determination
    has_technical_pattern = any(re.search(pattern, message_lower) for pattern in technical_question_patterns)
    should_be_technical = has_technical_pattern or (mentions_connector and has_question_words)
    
    print(f"\nFinal determination:")
    print(f"Has technical pattern: {has_technical_pattern}")
    print(f"Should be technical question: {should_be_technical}")

if __name__ == "__main__":
    test_pattern_matching()