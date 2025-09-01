#!/usr/bin/env python3
"""
Test that agent specification detection works with any name, not just "Clara AI".
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_different_agent_names():
    """Test intent analysis with different agent names."""
    
    test_cases = [
        # Different AI names
        'You are "Alex AI", an intelligent research assistant designed to help with data analysis.',
        'You are "DataBot", an AI agent that processes spreadsheets and generates reports.',
        'You are "WriteHelper", an intelligent writing assistant for content creation.',
        
        # Different formats
        'Create an AI agent called "TaskMaster" that automates email workflows.',
        'Build an intelligent assistant named "DocProcessor" with these capabilities: PDF analysis, text extraction.',
        
        # Generic agent requests
        'Create an AI agent that can summarize documents',
        'Build an intelligent assistant for customer support',
        'I want to create an automation agent',
        
        # Structured specifications without names
        '''An intelligent assistant with these capabilities:
        
        Content Processing:
        - Analyze documents and extract key information
        - Generate summaries and reports
        
        Response Behavior:
        - Provide accurate, referenced answers
        - Maintain professional tone
        
        Limitations:
        - Cannot access external APIs without permission'''
    ]
    
    conversation_handler = await get_conversation_handler()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {test_case[:100]}{'...' if len(test_case) > 100 else ''}")
        
        try:
            intent_analysis = await conversation_handler.analyze_intent(test_case)
            
            print(f"Intent: {intent_analysis.intent.value}")
            print(f"Confidence: {intent_analysis.confidence}")
            print(f"Reasoning: {intent_analysis.reasoning[:100]}...")
            
            if intent_analysis.intent.value == "workflow_creation":
                print("✅ SUCCESS: Correctly identified as workflow creation!")
            else:
                print(f"❌ FAILED: Incorrectly identified as {intent_analysis.intent.value}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_different_agent_names())