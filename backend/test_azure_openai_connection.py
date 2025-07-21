#!/usr/bin/env python3
"""
Test Azure OpenAI connection with your configured credentials.
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_azure_openai_connection():
    """Test the Azure OpenAI connection."""
    print("Testing Azure OpenAI connection...")
    
    # Check if required environment variables are set
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    print(f"Endpoint: {endpoint}")
    print(f"API Version: {api_version}")
    print(f"Embedding Deployment: {embedding_deployment}")
    print(f"API Key: {'*' * 20 if api_key else 'NOT SET'}")
    
    if not all([endpoint, api_key, api_version, embedding_deployment]):
        print("❌ Missing required environment variables!")
        return False
    
    try:
        # Try to import the Azure OpenAI client
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        # Test embedding creation
        print("\nTesting embedding creation...")
        response = await client.embeddings.create(
            model=embedding_deployment,
            input="This is a test connection to Azure OpenAI"
        )
        
        print("✅ Azure OpenAI connection successful!")
        print(f"✅ Embedding dimensions: {len(response.data[0].embedding)}")
        print(f"✅ Model used: {response.model}")
        
        return True
        
    except ImportError:
        print("❌ OpenAI library not installed. Run: pip install openai")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Verify your endpoint URL is correct")
        print("2. Check that your API key is valid")
        print("3. Ensure the embedding deployment name matches Azure OpenAI Studio")
        print("4. Confirm your Azure OpenAI resource is active")
        return False

if __name__ == "__main__":
    asyncio.run(test_azure_openai_connection())