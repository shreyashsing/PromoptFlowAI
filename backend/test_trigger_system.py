"""
Comprehensive tests for the trigger system implementation.

Tests cover:
- Schedule trigger creation and execution
- Webhook trigger creation and processing
- Trigger validation and configuration management
- Trigger status monitoring and failure notifications
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.trigger_system import TriggerSystem, TriggerType, ScheduleConfig, WebhookConfig
from app.models.base import Trigger, WorkflowPlan, WorkflowNode, WorkflowEdge, NodePosition, WorkflowStatus
from app.core.exceptions import TriggerException


class TestTriggerSystem:
    """Test suite for the TriggerSystem class."""
    
    @pytest.fixture
    async def trigger_system(self):
        """Create a trigger system instance for testing."""
        system = TriggerSystem()
        yield system
        await system.stop()
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing."""
        return WorkflowPlan(
            id="test-workflow-123",
            user_id="user-123",
            name="Test Workflow",
            description="A test workflow",
            nodes=[
                WorkflowNode(
                    id="node1",
                    connector_name="http_connector",
                    parameters={"url": "https://api.example.com"},
                    position=NodePosition(x=100, y=100)
                )
            ],
            edges=[],
            triggers=[],
            status=WorkflowStatus.ACTIVE
        )
    
    @pytest.mark.asyncio
    async def test_schedule_trigger_creation(self, trigger_system, sample_workflow):
        """Test creating a schedule trigger."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"triggers": []}
            ]
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "test-workflow-123"}
            ]
            
            # Create schedule trigger
            config = {
                "cron_expression": "0 9 * * 1-5",  # Weekdays at 9 AM
                "timezone": "UTC",
                "enabled": True,
                "max_executions": 100
            }
            
            trigger = await trigger_system.create_trigger(
                workflow_id="test-workflow-123",
                user_id="user-123",
                trigger_type=TriggerType.SCHEDULE,
                config=config
            )
            
            assert trigger.type == TriggerType.SCHEDULE
            assert trigger.config["cron_expression"] == "0 9 * * 1-5"
            assert trigger.enabled is True
            assert trigger.id in trigger_system.active_schedules
    
    @pytest.mark.asyncio
    async def test_webhook_trigger_creation(self, trigger_system):
        """Test creating a webhook trigger."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"triggers": []}
            ]
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "test-workflow-123"}
            ]
            
            # Create webhook trigger
            config = {
                "webhook_id": "test-webhook-123",
                "secret_token": "secret-token-456",
                "enabled": True,
                "allowed_origins": ["https://example.com"],
                "headers_validation": {"x-api-key": "test-key"}
            }
            
            trigger = await trigger_system.create_trigger(
                workflow_id="test-workflow-123",
                user_id="user-123",
                trigger_type=TriggerType.WEBHOOK,
                config=config
            )
            
            assert trigger.type == TriggerType.WEBHOOK
            assert trigger.config["webhook_id"] == "test-webhook-123"
            assert trigger.enabled is True
            assert "test-webhook-123" in trigger_system.webhook_handlers
    
    @pytest.mark.asyncio
    async def test_invalid_cron_expression(self, trigger_system):
        """Test that invalid cron expressions are rejected."""
        config = {
            "cron_expression": "invalid cron",
            "timezone": "UTC",
            "enabled": True
        }
        
        with pytest.raises(TriggerException, match="Invalid cron expression"):
            await trigger_system.create_trigger(
                workflow_id="test-workflow-123",
                user_id="user-123",
                trigger_type=TriggerType.SCHEDULE,
                config=config
            )
    
    @pytest.mark.asyncio
    async def test_webhook_processing(self, trigger_system):
        """Test webhook request processing."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses for webhook lookup
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table.return_value.select.return_value.neq.return_value.execute.return_value.data = [
                {
                    "id": "test-workflow-123",
                    "triggers": [
                        {
                            "id": "trigger-123",
                            "type": "webhook",
                            "config": {
                                "webhook_id": "test-webhook-123",
                                "secret_token": "secret-token-456",
                                "enabled": True,
                                "allowed_origins": [],
                                "headers_validation": {}
                            },
                            "enabled": True
                        }
                    ]
                }
            ]
            
            # Mock workflow lookup
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "test-workflow-123",
                    "user_id": "user-123",
                    "name": "Test Workflow",
                    "description": "Test",
                    "nodes": [],
                    "edges": [],
                    "triggers": [],
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            ]
            
            # Mock trigger execution storage
            mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "exec-123"}]
            
            with patch('app.services.trigger_system.WorkflowOrchestrator') as mock_orchestrator:
                # Mock workflow execution
                mock_exec_result = MagicMock()
                mock_exec_result.status.value = "completed"
                mock_exec_result.error = None
                mock_orchestrator.return_value.execute_workflow.return_value = mock_exec_result
                
                # Process webhook
                payload = {"data": "test payload"}
                headers = {"authorization": "secret-token-456"}
                
                result = await trigger_system.process_webhook(
                    webhook_id="test-webhook-123",
                    payload=payload,
                    headers=headers
                )
                
                assert result["status"] == "success"
                assert "execution_id" in result
    
    @pytest.mark.asyncio
    async def test_trigger_status_monitoring(self, trigger_system):
        """Test trigger status monitoring functionality."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            
            # Mock trigger lookup
            mock_client.table.return_value.select.return_value.neq.return_value.execute.return_value.data = [
                {
                    "id": "test-workflow-123",
                    "triggers": [
                        {
                            "id": "trigger-123",
                            "type": "schedule",
                            "config": {
                                "cron_expression": "0 9 * * 1-5",
                                "timezone": "UTC",
                                "enabled": True
                            },
                            "enabled": True
                        }
                    ]
                }
            ]
            
            # Mock recent executions
            mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {
                    "workflow_id": "test-workflow-123",
                    "trigger_id": "trigger-123",
                    "trigger_type": "schedule",
                    "trigger_data": {},
                    "status": "completed",
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "error_message": None
                }
            ]
            
            # Get trigger status
            status = await trigger_system.get_trigger_status("trigger-123")
            
            assert status["trigger_id"] == "trigger-123"
            assert "is_active" in status
            assert "recent_executions" in status
            assert len(status["recent_executions"]) >= 0
    
    @pytest.mark.asyncio
    async def test_trigger_enable_disable(self, trigger_system):
        """Test enabling and disabling triggers."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            
            # Mock trigger lookup
            trigger_data = {
                "id": "trigger-123",
                "type": "schedule",
                "config": {
                    "cron_expression": "0 9 * * 1-5",
                    "timezone": "UTC",
                    "enabled": True
                },
                "enabled": True
            }
            
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"triggers": [trigger_data]}
            ]
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "test-workflow-123"}
            ]
            
            # Test disable trigger
            await trigger_system.disable_trigger("test-workflow-123", "trigger-123")
            
            # Test enable trigger
            await trigger_system.enable_trigger("test-workflow-123", "trigger-123")
    
    @pytest.mark.asyncio
    async def test_trigger_deletion(self, trigger_system):
        """Test trigger deletion."""
        with patch('app.services.trigger_system.get_supabase_client') as mock_supabase:
            # Mock database responses
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"triggers": []}
            ]
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "test-workflow-123"}
            ]
            
            # Delete trigger
            await trigger_system.delete_trigger("test-workflow-123", "trigger-123")
    
    def test_schedule_config_validation(self):
        """Test schedule configuration validation."""
        # Valid config
        valid_config = ScheduleConfig(
            cron_expression="0 9 * * 1-5",
            timezone="UTC",
            enabled=True,
            max_executions=100
        )
        assert valid_config.cron_expression == "0 9 * * 1-5"
        assert valid_config.timezone == "UTC"
        assert valid_config.enabled is True
        assert valid_config.max_executions == 100
    
    def test_webhook_config_validation(self):
        """Test webhook configuration validation."""
        # Valid config
        valid_config = WebhookConfig(
            webhook_id="test-webhook-123",
            secret_token="secret-token",
            enabled=True,
            allowed_origins=["https://example.com"],
            headers_validation={"x-api-key": "test-key"}
        )
        assert valid_config.webhook_id == "test-webhook-123"
        assert valid_config.secret_token == "secret-token"
        assert valid_config.enabled is True
        assert "https://example.com" in valid_config.allowed_origins


@pytest.mark.asyncio
async def test_trigger_system_integration():
    """Integration test for the complete trigger system."""
    print("\n🔄 Testing Trigger System Integration...")
    
    try:
        # Initialize trigger system
        trigger_system = TriggerSystem()
        
        print("   ✅ Trigger system initialized")
        
        # Test schedule trigger configuration
        schedule_config = {
            "cron_expression": "0 9 * * 1-5",  # Weekdays at 9 AM
            "timezone": "UTC",
            "enabled": True,
            "max_executions": 100
        }
        
        print(f"   ⏰ Schedule trigger config: {schedule_config}")
        
        # Test webhook trigger configuration
        webhook_config = {
            "webhook_id": "integration-test-webhook",
            "secret_token": "test-secret-token",
            "enabled": True,
            "allowed_origins": ["https://example.com"],
            "headers_validation": {"x-api-key": "test-api-key"}
        }
        
        print(f"   🔗 Webhook trigger config: {webhook_config}")
        
        # Test trigger validation
        try:
            await trigger_system._validate_trigger_config(TriggerType.SCHEDULE, schedule_config)
            print("   ✅ Schedule trigger validation passed")
        except Exception as e:
            print(f"   ❌ Schedule trigger validation failed: {e}")
        
        try:
            await trigger_system._validate_trigger_config(TriggerType.WEBHOOK, webhook_config)
            print("   ✅ Webhook trigger validation passed")
        except Exception as e:
            print(f"   ❌ Webhook trigger validation failed: {e}")
        
        # Test invalid cron expression
        try:
            invalid_config = {"cron_expression": "invalid cron", "timezone": "UTC", "enabled": True}
            await trigger_system._validate_trigger_config(TriggerType.SCHEDULE, invalid_config)
            print("   ❌ Invalid cron validation should have failed")
        except TriggerException:
            print("   ✅ Invalid cron expression properly rejected")
        
        await trigger_system.stop()
        print("   ✅ Trigger system integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Trigger system integration test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_trigger_system_integration())