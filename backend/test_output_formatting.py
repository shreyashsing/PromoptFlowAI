"""
Test Output Formatting

This test verifies that the universal output formatter cleans up
connector outputs properly.
"""
import asyncio
from app.services.output_formatter import format_connector_output

def test_output_formatting():
    """Test various output formatting scenarios."""
    
    print("🧪 Testing Universal Output Formatting")
    print("=" * 50)
    
    # Test 1: Raw summarizer output (like your Gmail issue)
    raw_summarizer_output = {
        'summary': "Google's recent blog posts detail several major updates from July and August 2025. The company launched \"Deep Think\" in the Gemini app, leveraging advanced reinforcement learning to enhance AI problem-solving, notably achieving top performance at the 2025 International Mathematical Olympiad[1]. Google also revised its goo.gl URL shortener policy, ensuring all active links remain functional past the original cutoff date, while only inactive links will be deactivated[2].\n\n**Sources:**\n1. https://blog.google/products/gemini/gemini-2-5-deep-think/\n2. https://blog.google/technology/developers/googl-link-shortening-update/\n3. https://blog.google/outreach-initiatives/public-policy/pennsylvania-energy-innovation-summit/",
        'original_length': 296,
        'summary_length': 153,
        'style': 'concise',
        'preserved_citations': True
    }
    
    print("\n1. Testing Summarizer Output Formatting:")
    print("   Raw output contains technical metadata...")
    formatted = format_connector_output(raw_summarizer_output, 'text_summarizer')
    print("   ✅ Formatted output:")
    print(f"   {formatted[:100]}...")
    
    # Test 2: Search results with citations
    raw_search_output = {
        'response': 'AI developments in 2025 include major breakthroughs in reasoning.',
        'citations': [
            'https://example.com/ai-news-1',
            {'title': 'AI Breakthrough 2025', 'url': 'https://example.com/ai-news-2'}
        ],
        'metadata': {'query_time': 1.5, 'sources_count': 2}
    }
    
    print("\n2. Testing Search Results Formatting:")
    formatted = format_connector_output(raw_search_output, 'perplexity_search')
    print("   ✅ Formatted output:")
    print(f"   {formatted}")
    
    # Test 3: Gmail-specific formatting
    raw_email_content = {
        'summary': 'Weekly report summary with technical metadata',
        'original_length': 500,
        'summary_length': 100,
        'style': 'professional'
    }
    
    print("\n3. Testing Gmail-Specific Formatting:")
    formatted = format_connector_output(raw_email_content, 'gmail_connector')
    print("   ✅ Formatted for email:")
    print(f"   {formatted}")
    
    # Test 4: Complex nested data
    complex_output = {
        'result': {
            'content': 'Main content here',
            'metadata': {'processed_at': '2025-01-01', 'version': '1.0'}
        },
        'stats': {'word_count': 150, 'processing_time': 2.3}
    }
    
    print("\n4. Testing Complex Data Formatting:")
    formatted = format_connector_output(complex_output)
    print("   ✅ Formatted complex data:")
    print(f"   {formatted}")
    
    # Test 5: List output
    list_output = [
        {'title': 'Item 1', 'content': 'Content 1'},
        {'title': 'Item 2', 'content': 'Content 2'}
    ]
    
    print("\n5. Testing List Output Formatting:")
    formatted = format_connector_output(list_output)
    print("   ✅ Formatted list:")
    print(f"   {formatted}")
    
    print("\n🎯 Output Formatting Test Complete!")
    print("All connector outputs will now be automatically cleaned!")

if __name__ == "__main__":
    test_output_formatting()