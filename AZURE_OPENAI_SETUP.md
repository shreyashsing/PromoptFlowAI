# Azure OpenAI Setup Guide

This guide will help you set up Azure OpenAI for the PromptFlow AI platform's RAG system.

## Why Azure OpenAI is Needed

The RAG (Retrieval-Augmented Generation) system uses Azure OpenAI for:
- **Text Embeddings**: Converting connector descriptions into vector representations
- **Semantic Search**: Finding relevant connectors based on user queries
- **Future AI Features**: Conversational workflow building and natural language processing

## Setup Steps

### 1. Create Azure OpenAI Resource

1. **Sign up for Azure**: If you don't have an Azure account, create one at [portal.azure.com](https://portal.azure.com)

2. **Request Access**: Azure OpenAI requires approval. Apply at [aka.ms/oai/access](https://aka.ms/oai/access)

3. **Create Resource**:
   - Go to Azure Portal
   - Click "Create a resource"
   - Search for "Azure OpenAI"
   - Click "Create"
   - Fill in the required information:
     - **Subscription**: Your Azure subscription
     - **Resource Group**: Create new or use existing
     - **Region**: Choose a region that supports OpenAI (e.g., East US, West Europe)
     - **Name**: Give your resource a unique name
     - **Pricing Tier**: Standard S0

### 2. Deploy Required Models

After your resource is created:

1. **Go to Azure OpenAI Studio**:
   - Navigate to your Azure OpenAI resource
   - Click "Go to Azure OpenAI Studio"

2. **Deploy Embedding Model**:
   - Go to "Deployments" section
   - Click "Create new deployment"
   - Select model: `text-embedding-3-small`
   - Deployment name: `text-embedding-3-small` (or your preferred name)
   - Click "Create"

3. **Deploy Chat Model** (Optional, for future features):
   - Create another deployment
   - Select model: `gpt-4.1` or `gpt-4o`
   - Deployment name: `gpt-4.1` (or your preferred name)
   - Click "Create"

### 3. Get Your Credentials

1. **Get Endpoint**:
   - In Azure Portal, go to your OpenAI resource
   - In the "Overview" section, copy the "Endpoint" URL
   - It looks like: `https://your-resource-name.openai.azure.com/`

2. **Get API Key**:
   - Go to "Keys and Endpoint" section
   - Copy "KEY 1" or "KEY 2"

### 4. Configure Environment Variables

Update your `backend/.env` file:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

**Important**: Make sure the deployment names match what you created in Azure OpenAI Studio.

### 5. Test Your Setup

Run the RAG system setup script:

```bash
cd backend
python scripts/setup_rag_database.py
```

If successful, you should see:
- ✅ RAG system initialized
- ✅ Sample connectors populated with embeddings
- ✅ Test queries working

## Pricing Information

### Azure OpenAI Costs

**Text Embeddings (text-embedding-3-small)**:
- ~$0.00002 per 1,000 tokens
- Initial setup: ~$0.01 for 12 sample connectors
- Ongoing usage: Minimal for typical queries

**GPT-4.1 (Optional)**:
- ~$0.03 per 1,000 input tokens
- ~$0.06 per 1,000 output tokens
- Only used for conversational features (future implementation)

### Cost Estimation for Development

**Initial Setup**: < $0.10
**Monthly Development Usage**: $1-5
**Production Usage**: Depends on query volume

## Troubleshooting

### Common Issues

1. **"Access Denied" Error**:
   - Ensure you've been approved for Azure OpenAI access
   - Check that your subscription has the necessary permissions

2. **"Model Not Found" Error**:
   - Verify deployment names in your .env file match Azure OpenAI Studio
   - Ensure models are deployed and active

3. **"Quota Exceeded" Error**:
   - Check your Azure OpenAI quota limits
   - Consider upgrading your pricing tier if needed

4. **Connection Timeout**:
   - Verify your endpoint URL is correct
   - Check network connectivity and firewall settings

### Testing Connection

You can test your Azure OpenAI connection with this simple script:

```python
# test_azure_openai.py
import asyncio
from openai import AsyncAzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION")
    )
    
    try:
        response = await client.embeddings.create(
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            input="test connection"
        )
        print("✅ Azure OpenAI connection successful!")
        print(f"Embedding dimensions: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

## Alternative: Development Without Azure OpenAI

If you want to develop other parts of the application without Azure OpenAI:

1. **Mock the RAG System**: The code includes mock implementations for testing
2. **Skip RAG Setup**: You can work on authentication, database, and frontend features
3. **Add Later**: Configure Azure OpenAI when you're ready to implement task 4

The application is designed to work without the RAG system for initial development.

## Support

If you encounter issues:
1. Check the [Azure OpenAI documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
2. Review the [troubleshooting guide](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/troubleshooting)
3. Create an issue in this repository with your error details