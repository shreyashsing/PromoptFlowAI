#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import IntelligentConversationHandler

async def test_customer_service_template_intent():
    """Test that customer service template requests are correctly classified as workflow creation."""
    
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    # Test the exact message from the logs
    test_message = """**Goal:** Automate responses to common customer inquiries about product features.

**Context:** Inquiries concern a new line of organic skincare products. The target audience is young adults concerned with sustainability. Responses should be friendly and encouraging.

**Specific Task:** Generate a response template addressing questions about product ingredients, benefits, and how the products contribute to sustainability.

**Desired Output:** A template with placeholders for the customer's name and the specific product. Include details on key ingredients, benefits (e.g., moisturization, anti-aging), and how the product's sourcing and packaging are eco-friendly.

**Example:**
*   **Customer Inquiry:** "Tell me about the ingredients in your new 'Bloom & Glow' moisturizer and how it helps my skin. Also, is it sustainable?"
*   **Expected Response (template):** "Hi [Customer Name], thanks for reaching out! Our 'Bloom & Glow' moisturizer features [key ingredients], known for [benefits]. We're proud to use [sustainable sourcing methods] and package our products in [eco-friendly packaging], {Link: according to our website https://www.salesforce.com/in/artificial-intelligence/generative-ai-prompts/}. We're committed to creating effective products that are kind to both your skin and the planet! Let us know if you have any other questions."

**Constraints:** Do not provide medical advice or make unsubstantiated claims about product effectiveness."""

    print("Testing customer service template request...")
    print(f"Message length: {len(test_message)} characters")
    print()
    
    # Analyze intent
    result = await handler.analyze_intent(test_message)
    
    print(f"Intent: {result.intent.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Extracted info: {result.extracted_info}")
    
    # Check if it's correctly classified as workflow creation
    if result.intent.value == "workflow_creation":
        print("\n✅ SUCCESS: Correctly classified as workflow creation!")
        return True
    else:
        print(f"\n❌ FAILED: Incorrectly classified as {result.intent.value}")
        return False

async def test_technical_question():
    """Test that actual technical questions are still correctly classified."""
    
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    test_message = "How does the YouTube connector extract content from videos?"
    
    print("Testing technical question...")
    print(f"Message: {test_message}")
    print()
    
    # Analyze intent
    result = await handler.analyze_intent(test_message)
    
    print(f"Intent: {result.intent.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")
    
    # Check if it's correctly classified as technical question
    if result.intent.value == "technical_question":
        print("\n✅ SUCCESS: Correctly classified as technical question!")
        return True
    else:
        print(f"\n❌ FAILED: Incorrectly classified as {result.intent.value}")
        return False

async def main():
    print("Testing intent classification fixes...\n")
    
    # Test customer service template
    success1 = await test_customer_service_template_intent()
    print("\n" + "="*50 + "\n")
    
    # Test technical question
    success2 = await test_technical_question()
    
    print("\n" + "="*50)
    if success1 and success2:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")

if __name__ == "__main__":
    asyncio.run(main())