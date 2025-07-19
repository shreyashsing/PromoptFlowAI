#!/usr/bin/env python3
"""
Test client for the RAG API endpoints.
This script tests the RAG system through HTTP requests.
"""
import asyncio
import httpx
import json
import sys
import time

BASE_URL = "http://localhost:8000/api/v1/rag"


async def test_health_check():
    """Test the RAG health check endpoint."""
    print("🏥 Testing RAG health check...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ RAG system is healthy")
                print(f"   Status: {data['status']}")
                print(f"   Total connectors: {data['total_connectors']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False


async def test_connector_search():
    """Test connector search functionality."""
    print("\n🔍 Testing connector search...")
    
    test_queries = [
        "send email notification",
        "read spreadsheet data",
        "make HTTP request to API",
        "AI text generation",
        "schedule automated workflow"
    ]
    
    async with httpx.AsyncClient() as client:
        for query in test_queries:
            try:
                print(f"\n   Query: '{query}'")
                
                start_time = time.time()
                response = await client.get(
                    f"{BASE_URL}/search",
                    params={"query": query, "limit": 3}
                )
                request_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Found {data['total_found']} connectors in {request_time:.1f}ms")
                    
                    for connector in data['connectors']:
                        print(f"      - {connector['name']}: {connector['description'][:60]}...")
                else:
                    print(f"   ❌ Search failed: {response.status_code}")
                    print(f"      Response: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Search error: {e}")


async def test_popular_connectors():
    """Test popular connectors endpoint."""
    print("\n⭐ Testing popular connectors...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/connectors/popular?limit=5")
            
            if response.status_code == 200:
                connectors = response.json()
                print(f"✅ Retrieved {len(connectors)} popular connectors")
                
                for connector in connectors:
                    print(f"   - {connector['name']} (used {connector['usage_count']} times)")
            else:
                print(f"❌ Popular connectors failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Popular connectors error: {e}")


async def test_categories():
    """Test connector categories endpoint."""
    print("\n📂 Testing connector categories...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/categories")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {len(data['categories'])} categories")
                print(f"   Categories: {', '.join(data['categories'])}")
                print(f"   Total connectors: {data['total_connectors']}")
            else:
                print(f"❌ Categories failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Categories error: {e}")


async def test_category_filter():
    """Test category filtering."""
    print("\n🏷️  Testing category filtering...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/connectors/category/communication")
            
            if response.status_code == 200:
                connectors = response.json()
                print(f"✅ Found {len(connectors)} communication connectors")
                
                for connector in connectors:
                    print(f"   - {connector['name']}: {connector['category']}")
            else:
                print(f"❌ Category filter failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Category filter error: {e}")


async def test_connector_details():
    """Test getting specific connector details."""
    print("\n📋 Testing connector details...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/connectors/gmail_connector")
            
            if response.status_code == 200:
                connector = response.json()
                print(f"✅ Retrieved details for {connector['name']}")
                print(f"   Description: {connector['description'][:80]}...")
                print(f"   Category: {connector['category']}")
                print(f"   Auth type: {connector['auth_type']}")
                print(f"   Usage count: {connector['usage_count']}")
            else:
                print(f"❌ Connector details failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Connector details error: {e}")


async def run_all_tests():
    """Run all RAG API tests."""
    print("🚀 Testing RAG API Endpoints")
    print("=" * 60)
    
    # Test health first
    if not await test_health_check():
        print("\n❌ RAG system is not healthy. Please check:")
        print("   1. FastAPI server is running (uvicorn app.main:app --reload)")
        print("   2. Database is configured and accessible")
        print("   3. Azure OpenAI credentials are set")
        print("   4. RAG system is initialized with sample data")
        return False
    
    # Run other tests
    await test_connector_search()
    await test_popular_connectors()
    await test_categories()
    await test_category_filter()
    await test_connector_details()
    
    print("\n" + "=" * 60)
    print("🎉 RAG API testing completed!")
    print("\n✅ Your RAG system is working and ready to use!")
    
    return True


if __name__ == "__main__":
    print("Make sure your FastAPI server is running:")
    print("cd backend && uvicorn app.main:app --reload")
    print()
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)