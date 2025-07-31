#!/usr/bin/env python3
"""
Quick test to verify email extraction is working.
"""
import re

def test_email_extraction():
    user_request = "Build me a workflow that finds the top 5 recent blogs posted by Google using Perplexity, summarizes all 5 into one combined summary, and sends the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body"
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, user_request)
    
    print(f"User request: {user_request}")
    print(f"Email pattern: {email_pattern}")
    
    if email_match:
        print(f"✅ Found email: {email_match.group()}")
    else:
        print("❌ No email found")
    
    # Test with simpler request
    simple_request = "Send email to john@example.com"
    simple_match = re.search(email_pattern, simple_request)
    
    print(f"\nSimple request: {simple_request}")
    if simple_match:
        print(f"✅ Found email: {simple_match.group()}")
    else:
        print("❌ No email found")

if __name__ == "__main__":
    test_email_extraction()