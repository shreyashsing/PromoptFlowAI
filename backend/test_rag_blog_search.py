#!/usr/bin/env python3
"""
Test script to check what connectors are retrieved for blog search queries.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag import RAGRetriever
from app.core.database import get_database

async def test_rag():
    try:
        rag = RAGRetriever()
        
        # Test what connectors are retrieved for blog search
        query = 'find recent blogs posted by Google using Perplexity'
        connectors = await rag.retrieve_connectors(query, limit=5)
        
        print('Query:', query)
        print('Retrieved connectors:')
        for i, conn in enumerate(connectors, 1):
            print(f'{i}. {conn.name} - {conn.description[:100]}...')
            
        print('\n' + '='*50)
        
        # Test another query
        query2 = 'search for Google blog posts'
        connectors2 = await rag.retrieve_connectors(query2, limit=5)
        
        print('Query:', query2)
        print('Retrieved connectors:')
        for i, conn in enumerate(connectors2, 1):
            print(f'{i}. {conn.name} - {conn.description[:100]}...')
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag())