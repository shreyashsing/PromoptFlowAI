#!/usr/bin/env python3
"""
Test script for dynamic connector fields functionality.
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_TOKEN = "your-test-token-here"  # Replace with actual token

async def test_gmail_fields():
    """Test Gmail dynamic field fetching."""
    print("🧪 Testing Gmail dynamic fields...")
    
    async with httpx.AsyncClient() as client:
        # Test Gmail labels
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "gmail_connector",
                "field_name": "label_ids"
            }
        )
        
        print(f"Gmail Labels Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
            if data.get('options'):
                print(f"Sample option: {data['options'][0]}")
        else:
            print(f"Error: {response.text}")
        
        # Test Gmail messages
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "gmail_connector",
                "field_name": "message_id",
                "context": {"query": "is:unread"}
            }
        )
        
        print(f"Gmail Messages Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
        else:
            print(f"Error: {response.text}")

async def test_notion_fields():
    """Test Notion dynamic field fetching."""
    print("\n🧪 Testing Notion dynamic fields...")
    
    async with httpx.AsyncClient() as client:
        # Test Notion databases
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "notion",
                "field_name": "database_id"
            }
        )
        
        print(f"Notion Databases Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
            if data.get('options'):
                print(f"Sample option: {data['options'][0]}")
        else:
            print(f"Error: {response.text}")
        
        # Test Notion pages
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "notion",
                "field_name": "page_id",
                "context": {"query": "project"}
            }
        )
        
        print(f"Notion Pages Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
        else:
            print(f"Error: {response.text}")

async def test_google_sheets_fields():
    """Test Google Sheets dynamic field fetching."""
    print("\n🧪 Testing Google Sheets dynamic fields...")
    
    async with httpx.AsyncClient() as client:
        # Test Google Spreadsheets
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "google_sheets",
                "field_name": "spreadsheet_id"
            }
        )
        
        print(f"Google Spreadsheets Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
            if data.get('options'):
                print(f"Sample option: {data['options'][0]}")
                
                # Test sheet names for the first spreadsheet
                spreadsheet_id = data['options'][0]['value']
                sheet_response = await client.post(
                    f"{BASE_URL}/api/v1/connector-fields/fetch",
                    headers={
                        "Authorization": f"Bearer {TEST_USER_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "connector_name": "google_sheets",
                        "field_name": "sheet_name",
                        "context": {"spreadsheet_id": spreadsheet_id}
                    }
                )
                
                print(f"Sheet Names Response: {sheet_response.status_code}")
                if sheet_response.status_code == 200:
                    sheet_data = sheet_response.json()
                    print(f"Sheet Success: {sheet_data['success']}")
                    print(f"Sheet Options count: {len(sheet_data.get('options', []))}")
        else:
            print(f"Error: {response.text}")

async def test_airtable_fields():
    """Test Airtable dynamic field fetching."""
    print("\n🧪 Testing Airtable dynamic fields...")
    
    async with httpx.AsyncClient() as client:
        # Test Airtable bases
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "airtable",
                "field_name": "base_id"
            }
        )
        
        print(f"Airtable Bases Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Options count: {len(data.get('options', []))}")
            if data.get('options'):
                print(f"Sample option: {data['options'][0]}")
        else:
            print(f"Error: {response.text}")

async def test_error_handling():
    """Test error handling for dynamic fields."""
    print("\n🧪 Testing error handling...")
    
    async with httpx.AsyncClient() as client:
        # Test unsupported connector
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "unsupported_connector",
                "field_name": "some_field"
            }
        )
        
        print(f"Unsupported Connector Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Error: {data.get('error')}")
        
        # Test unsupported field
        response = await client.post(
            f"{BASE_URL}/api/v1/connector-fields/fetch",
            headers={
                "Authorization": f"Bearer {TEST_USER_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "connector_name": "gmail_connector",
                "field_name": "unsupported_field"
            }
        )
        
        print(f"Unsupported Field Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Error: {data.get('error')}")

async def main():
    """Run all tests."""
    print("🚀 Starting Dynamic Connector Fields Tests")
    print("=" * 50)
    
    if TEST_USER_TOKEN == "your-test-token-here":
        print("❌ Please set a valid TEST_USER_TOKEN in the script")
        return
    
    try:
        await test_gmail_fields()
        await test_notion_fields()
        await test_google_sheets_fields()
        await test_airtable_fields()
        await test_error_handling()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())