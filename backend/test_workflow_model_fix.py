#!/usr/bin/env python3
"""
Test the workflow model fix for the status attribute issue.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import CreateWorkflowRequest
from app.models.base import WorkflowStatus

def test_workflow_model():
    """Test that the CreateWorkflowRequest model has the status attribute."""
    print("🧪 Testing CreateWorkflowRequest model...")
    
    # Test 1: Create request with status
    try:
        request_with_status = CreateWorkflowRequest(
            name="Test Workflow",
            description="Test description",
            status=WorkflowStatus.ACTIVE
        )
        print(f"✅ Request with status created: {request_with_status.status}")
    except Exception as e:
        print(f"❌ Failed to create request with status: {e}")
        return False
    
    # Test 2: Create request without status (should use default)
    try:
        request_without_status = CreateWorkflowRequest(
            name="Test Workflow",
            description="Test description"
        )
        print(f"✅ Request without status created: {request_without_status.status}")
    except Exception as e:
        print(f"❌ Failed to create request without status: {e}")
        return False
    
    # Test 3: Test getattr access (what the API uses)
    try:
        status = getattr(request_without_status, 'status', WorkflowStatus.ACTIVE)
        print(f"✅ getattr access works: {status}")
    except Exception as e:
        print(f"❌ getattr access failed: {e}")
        return False
    
    print("🎉 All tests passed!")
    return True

if __name__ == "__main__":
    test_workflow_model()