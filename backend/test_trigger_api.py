"""
Test the trigger API endpoints.
"""
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.main import app


def test_trigger_api_endpoints():
    """Test trigger API endpoints with mocked database."""
    print("\n🔄 Testing Trigger API Endpoints...")
    
    client = TestClient(app)
    
    # Mock authentication
    with patch('app.core.auth.get_current_user') as mock_auth:
        mock_auth.return_value = {"id": "user-123", "email": "test@example.com"}
        
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database client
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            
            # Mock database responses for trigger creation
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"triggers": []}
            ]
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "test-workflow-123"}
            ]
            
            # Test schedule trigger creation
            print("   ⏰ Testing schedule trigger creation...")
            schedule_payload = {
                "workflow_id": "test-workflow-123",
                "trigger_type": "schedule",
                "config": {
                    "cron_expression": "0 9 * * 1-5",
                    "timezone": "UTC",
                    "enabled": True,
                    "max_executions": 100
                }
            }
            
            response = client.post("/api/v1/triggers/create", json=schedule_payload)
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      Created trigger: {data['trigger_id']}")
                print("   ✅ Schedule trigger creation successful")
            else:
                print(f"      Error: {response.text}")
                print("   ❌ Schedule trigger creation failed")
            
            # Test webhook trigger creation
            print("   🔗 Testing webhook trigger creation...")
            webhook_payload = {
                "workflow_id": "test-workflow-123",
                "trigger_type": "webhook",
                "config": {
                    "webhook_id": "test-webhook-123",
                    "secret_token": "secret-token-456",
                    "enabled": True,
                    "allowed_origins": ["https://example.com"],
                    "headers_validation": {"x-api-key": "test-key"}
                }
            }
            
            response = client.post("/api/v1/triggers/create", json=webhook_payload)
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      Created trigger: {data['trigger_id']}")
                print("   ✅ Webhook trigger creation successful")
            else:
                print(f"      Error: {response.text}")
                print("   ❌ Webhook trigger creation failed")
            
            # Test trigger examples endpoints
            print("   📋 Testing trigger examples...")
            
            response = client.get("/api/v1/triggers/examples/schedule")
            if response.status_code == 200:
                print("   ✅ Schedule example endpoint working")
            else:
                print("   ❌ Schedule example endpoint failed")
            
            response = client.get("/api/v1/triggers/examples/webhook")
            if response.status_code == 200:
                print("   ✅ Webhook example endpoint working")
            else:
                print("   ❌ Webhook example endpoint failed")
    
    print("   ✅ Trigger API endpoint testing completed")


if __name__ == "__main__":
    test_trigger_api_endpoints()