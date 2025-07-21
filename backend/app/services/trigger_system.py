"""
Trigger system for scheduled and event-based workflow execution.

This module implements the trigger system that handles:
- Time-based scheduling for workflow execution
- Webhook endpoints for external event triggers
- Trigger validation and configuration management
- Trigger status monitoring and failure notifications
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from uuid import uuid4
import json
from croniter import croniter

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.models.base import Trigger, WorkflowPlan
from app.models.execution import ExecutionResult
from app.core.database import get_supabase_client
from app.core.exceptions import TriggerException


logger = logging.getLogger(__name__)


class TriggerType:
    """Trigger type constants."""
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class ScheduleConfig(BaseModel):
    """Configuration for scheduled triggers."""
    cron_expression: str
    timezone: str = "UTC"
    enabled: bool = True
    max_executions: Optional[int] = None
    execution_count: int = 0


class WebhookConfig(BaseModel):
    """Configuration for webhook triggers."""
    webhook_id: str
    secret_token: Optional[str] = None
    enabled: bool = True
    allowed_origins: List[str] = Field(default_factory=list)
    headers_validation: Dict[str, str] = Field(default_factory=dict)


class TriggerExecution(BaseModel):
    """Record of a trigger execution."""
    trigger_id: str
    workflow_id: str
    execution_id: str
    trigger_type: str
    trigger_data: Dict[str, Any]
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class TriggerSystem:
    """
    Main trigger system for managing workflow triggers.
    
    Handles scheduling, webhook processing, and trigger lifecycle management.
    """
    
    def __init__(self):
        self.active_schedules: Dict[str, asyncio.Task] = {}
        self.webhook_handlers: Dict[str, Callable] = {}
        self.trigger_executions: Dict[str, TriggerExecution] = {}
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the trigger system and load active triggers."""
        logger.info("Starting trigger system...")
        
        try:
            # Load active triggers from database
            await self._load_active_triggers()
            
            # Start background task for trigger monitoring
            asyncio.create_task(self._monitor_triggers())
            
            logger.info("Trigger system started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start trigger system: {str(e)}")
            raise TriggerException(f"Trigger system startup failed: {str(e)}")
    
    async def stop(self):
        """Stop the trigger system and cleanup resources."""
        logger.info("Stopping trigger system...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all active schedule tasks
        for trigger_id, task in self.active_schedules.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.active_schedules.clear()
        self.webhook_handlers.clear()
        
        logger.info("Trigger system stopped")
    
    async def create_trigger(
        self, 
        workflow_id: str, 
        user_id: str, 
        trigger_type: str, 
        config: Dict[str, Any]
    ) -> Trigger:
        """
        Create a new trigger for a workflow.
        
        Args:
            workflow_id: The workflow to trigger
            user_id: The user creating the trigger
            trigger_type: Type of trigger (schedule/webhook)
            config: Trigger configuration
            
        Returns:
            Created Trigger object
        """
        trigger_id = str(uuid4())
        
        # Validate trigger configuration
        await self._validate_trigger_config(trigger_type, config)
        
        trigger = Trigger(
            id=trigger_id,
            type=trigger_type,
            config=config,
            enabled=True
        )
        
        try:
            # Store trigger in database
            await self._store_trigger(workflow_id, user_id, trigger)
            
            # Activate the trigger
            await self._activate_trigger(workflow_id, trigger)
            
            logger.info(f"Created {trigger_type} trigger {trigger_id} for workflow {workflow_id}")
            return trigger
            
        except Exception as e:
            logger.error(f"Failed to create trigger: {str(e)}")
            raise TriggerException(f"Trigger creation failed: {str(e)}")
    
    async def update_trigger(
        self, 
        workflow_id: str, 
        trigger_id: str, 
        config: Dict[str, Any]
    ) -> Trigger:
        """
        Update an existing trigger configuration.
        
        Args:
            workflow_id: The workflow ID
            trigger_id: The trigger to update
            config: New trigger configuration
            
        Returns:
            Updated Trigger object
        """
        try:
            # Get existing trigger
            trigger = await self._get_trigger(workflow_id, trigger_id)
            if not trigger:
                raise TriggerException(f"Trigger {trigger_id} not found")
            
            # Validate new configuration
            await self._validate_trigger_config(trigger.type, config)
            
            # Deactivate old trigger
            await self._deactivate_trigger(trigger_id)
            
            # Update configuration
            trigger.config = config
            
            # Store updated trigger
            await self._update_trigger_in_db(workflow_id, trigger)
            
            # Reactivate with new configuration
            await self._activate_trigger(workflow_id, trigger)
            
            logger.info(f"Updated trigger {trigger_id} for workflow {workflow_id}")
            return trigger
            
        except Exception as e:
            logger.error(f"Failed to update trigger: {str(e)}")
            raise TriggerException(f"Trigger update failed: {str(e)}")
    
    async def delete_trigger(self, workflow_id: str, trigger_id: str):
        """
        Delete a trigger.
        
        Args:
            workflow_id: The workflow ID
            trigger_id: The trigger to delete
        """
        try:
            # Deactivate trigger
            await self._deactivate_trigger(trigger_id)
            
            # Remove from database
            await self._delete_trigger_from_db(workflow_id, trigger_id)
            
            logger.info(f"Deleted trigger {trigger_id} for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete trigger: {str(e)}")
            raise TriggerException(f"Trigger deletion failed: {str(e)}")
    
    async def enable_trigger(self, workflow_id: str, trigger_id: str):
        """Enable a disabled trigger."""
        try:
            trigger = await self._get_trigger(workflow_id, trigger_id)
            if not trigger:
                raise TriggerException(f"Trigger {trigger_id} not found")
            
            trigger.enabled = True
            await self._update_trigger_in_db(workflow_id, trigger)
            await self._activate_trigger(workflow_id, trigger)
            
            logger.info(f"Enabled trigger {trigger_id}")
            
        except Exception as e:
            logger.error(f"Failed to enable trigger: {str(e)}")
            raise TriggerException(f"Trigger enable failed: {str(e)}")
    
    async def disable_trigger(self, workflow_id: str, trigger_id: str):
        """Disable an active trigger."""
        try:
            trigger = await self._get_trigger(workflow_id, trigger_id)
            if not trigger:
                raise TriggerException(f"Trigger {trigger_id} not found")
            
            trigger.enabled = False
            await self._update_trigger_in_db(workflow_id, trigger)
            await self._deactivate_trigger(trigger_id)
            
            logger.info(f"Disabled trigger {trigger_id}")
            
        except Exception as e:
            logger.error(f"Failed to disable trigger: {str(e)}")
            raise TriggerException(f"Trigger disable failed: {str(e)}")
    
    async def process_webhook(
        self, 
        webhook_id: str, 
        payload: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process an incoming webhook request.
        
        Args:
            webhook_id: The webhook identifier
            payload: The webhook payload
            headers: Request headers
            
        Returns:
            Processing result
        """
        try:
            # Find workflow and trigger for this webhook
            workflow_trigger = await self._get_webhook_trigger(webhook_id)
            if not workflow_trigger:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            workflow_id, trigger = workflow_trigger
            webhook_config = WebhookConfig(**trigger.config)
            
            # Validate webhook request
            await self._validate_webhook_request(webhook_config, payload, headers)
            
            # Execute workflow
            execution_result = await self._execute_triggered_workflow(
                workflow_id=workflow_id,
                trigger=trigger,
                trigger_data={
                    "webhook_id": webhook_id,
                    "payload": payload,
                    "headers": dict(headers),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "status": "success",
                "execution_id": execution_result.execution_id,
                "message": "Workflow triggered successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")
    
    async def get_trigger_status(self, trigger_id: str) -> Dict[str, Any]:
        """
        Get the current status of a trigger.
        
        Args:
            trigger_id: The trigger ID
            
        Returns:
            Trigger status information
        """
        try:
            # Check if trigger is active
            is_active = trigger_id in self.active_schedules
            
            # Get recent executions
            recent_executions = await self._get_recent_trigger_executions(trigger_id)
            
            # Get trigger configuration
            trigger = await self._get_trigger_by_id(trigger_id)
            
            return {
                "trigger_id": trigger_id,
                "is_active": is_active,
                "enabled": trigger.enabled if trigger else False,
                "type": trigger.type if trigger else None,
                "recent_executions": [
                    {
                        "execution_id": exec.execution_id,
                        "status": exec.status,
                        "started_at": exec.started_at.isoformat(),
                        "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                        "error": exec.error
                    }
                    for exec in recent_executions
                ],
                "next_execution": await self._get_next_execution_time(trigger) if trigger else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get trigger status: {str(e)}")
            return {
                "trigger_id": trigger_id,
                "error": str(e)
            }
    
    async def _load_active_triggers(self):
        """Load active triggers from database and activate them."""
        try:
            supabase = get_supabase_client()
            
            # Get all workflows with active triggers
            response = supabase.table("workflows").select("id, user_id, triggers").neq("triggers", "[]").execute()
            
            if response.data:
                for workflow_data in response.data:
                    workflow_id = workflow_data["id"]
                    triggers_data = workflow_data["triggers"]
                    
                    for trigger_data in triggers_data:
                        trigger = Trigger(**trigger_data)
                        if trigger.enabled:
                            await self._activate_trigger(workflow_id, trigger)
            
            logger.info(f"Loaded {len(self.active_schedules)} active triggers")
            
        except Exception as e:
            logger.error(f"Failed to load active triggers: {str(e)}")
    
    async def _activate_trigger(self, workflow_id: str, trigger: Trigger):
        """Activate a trigger based on its type."""
        if trigger.type == TriggerType.SCHEDULE:
            await self._activate_schedule_trigger(workflow_id, trigger)
        elif trigger.type == TriggerType.WEBHOOK:
            await self._activate_webhook_trigger(workflow_id, trigger)
    
    async def _activate_schedule_trigger(self, workflow_id: str, trigger: Trigger):
        """Activate a scheduled trigger."""
        try:
            schedule_config = ScheduleConfig(**trigger.config)
            
            # Create scheduled task
            task = asyncio.create_task(
                self._schedule_runner(workflow_id, trigger, schedule_config)
            )
            
            self.active_schedules[trigger.id] = task
            logger.info(f"Activated schedule trigger {trigger.id} with cron: {schedule_config.cron_expression}")
            
        except Exception as e:
            logger.error(f"Failed to activate schedule trigger: {str(e)}")
    
    async def _activate_webhook_trigger(self, workflow_id: str, trigger: Trigger):
        """Activate a webhook trigger."""
        try:
            webhook_config = WebhookConfig(**trigger.config)
            
            # Register webhook handler
            self.webhook_handlers[webhook_config.webhook_id] = {
                "workflow_id": workflow_id,
                "trigger": trigger,
                "config": webhook_config
            }
            
            logger.info(f"Activated webhook trigger {trigger.id} with webhook_id: {webhook_config.webhook_id}")
            
        except Exception as e:
            logger.error(f"Failed to activate webhook trigger: {str(e)}")
    
    async def _deactivate_trigger(self, trigger_id: str):
        """Deactivate a trigger."""
        # Cancel scheduled task if exists
        if trigger_id in self.active_schedules:
            task = self.active_schedules[trigger_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_schedules[trigger_id]
        
        # Remove webhook handler if exists
        webhook_to_remove = None
        for webhook_id, handler_info in self.webhook_handlers.items():
            if handler_info["trigger"].id == trigger_id:
                webhook_to_remove = webhook_id
                break
        
        if webhook_to_remove:
            del self.webhook_handlers[webhook_to_remove]
    
    async def _schedule_runner(self, workflow_id: str, trigger: Trigger, config: ScheduleConfig):
        """Background task for running scheduled workflows."""
        try:
            cron = croniter(config.cron_expression, datetime.utcnow())
            
            while not self._shutdown_event.is_set():
                # Calculate next execution time
                next_run = cron.get_next(datetime)
                wait_seconds = (next_run - datetime.utcnow()).total_seconds()
                
                if wait_seconds > 0:
                    # Wait until next execution time
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), 
                            timeout=wait_seconds
                        )
                        # If we reach here, shutdown was requested
                        break
                    except asyncio.TimeoutError:
                        # Time to execute
                        pass
                
                # Check if we've reached max executions
                if config.max_executions and config.execution_count >= config.max_executions:
                    logger.info(f"Schedule trigger {trigger.id} reached max executions ({config.max_executions})")
                    break
                
                # Execute workflow
                try:
                    await self._execute_triggered_workflow(
                        workflow_id=workflow_id,
                        trigger=trigger,
                        trigger_data={
                            "scheduled_time": next_run.isoformat(),
                            "cron_expression": config.cron_expression,
                            "execution_count": config.execution_count + 1
                        }
                    )
                    
                    # Update execution count
                    config.execution_count += 1
                    await self._update_schedule_config(workflow_id, trigger.id, config)
                    
                except Exception as e:
                    logger.error(f"Scheduled workflow execution failed: {str(e)}")
                    # Continue with next scheduled execution
        
        except Exception as e:
            logger.error(f"Schedule runner failed: {str(e)}")
        finally:
            # Clean up
            if trigger.id in self.active_schedules:
                del self.active_schedules[trigger.id]
    
    async def _execute_triggered_workflow(
        self, 
        workflow_id: str, 
        trigger: Trigger, 
        trigger_data: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute a workflow triggered by a trigger."""
        from app.services.workflow_orchestrator import WorkflowOrchestrator
        
        try:
            # Get workflow
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                raise TriggerException(f"Workflow {workflow_id} not found")
            
            # Create trigger execution record
            trigger_execution = TriggerExecution(
                trigger_id=trigger.id,
                workflow_id=workflow_id,
                execution_id=str(uuid4()),
                trigger_type=trigger.type,
                trigger_data=trigger_data,
                status="running",
                started_at=datetime.utcnow()
            )
            
            self.trigger_executions[trigger_execution.execution_id] = trigger_execution
            
            # Execute workflow
            orchestrator = WorkflowOrchestrator()
            execution_result = await orchestrator.execute_workflow(workflow)
            
            # Update trigger execution record
            trigger_execution.status = execution_result.status.value
            trigger_execution.completed_at = datetime.utcnow()
            if execution_result.error:
                trigger_execution.error = execution_result.error
            
            # Store trigger execution
            await self._store_trigger_execution(trigger_execution)
            
            logger.info(f"Triggered workflow {workflow_id} executed with status: {execution_result.status}")
            return execution_result
            
        except Exception as e:
            logger.error(f"Triggered workflow execution failed: {str(e)}")
            
            # Update trigger execution with error
            if 'trigger_execution' in locals():
                trigger_execution.status = "failed"
                trigger_execution.error = str(e)
                trigger_execution.completed_at = datetime.utcnow()
                await self._store_trigger_execution(trigger_execution)
            
            raise
    
    async def _validate_trigger_config(self, trigger_type: str, config: Dict[str, Any]):
        """Validate trigger configuration."""
        if trigger_type == TriggerType.SCHEDULE:
            schedule_config = ScheduleConfig(**config)
            
            # Validate cron expression
            try:
                croniter(schedule_config.cron_expression)
            except Exception as e:
                raise TriggerException(f"Invalid cron expression: {str(e)}")
        
        elif trigger_type == TriggerType.WEBHOOK:
            webhook_config = WebhookConfig(**config)
            
            # Validate webhook configuration
            if not webhook_config.webhook_id:
                raise TriggerException("Webhook ID is required")
        
        else:
            raise TriggerException(f"Unsupported trigger type: {trigger_type}")
    
    async def _validate_webhook_request(
        self, 
        config: WebhookConfig, 
        payload: Dict[str, Any], 
        headers: Dict[str, str]
    ):
        """Validate incoming webhook request."""
        # Validate secret token if configured
        if config.secret_token:
            auth_header = headers.get("authorization") or headers.get("x-webhook-token")
            if not auth_header or auth_header != config.secret_token:
                raise HTTPException(status_code=401, detail="Invalid webhook token")
        
        # Validate required headers
        for header_name, expected_value in config.headers_validation.items():
            actual_value = headers.get(header_name.lower())
            if actual_value != expected_value:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid header {header_name}: expected {expected_value}, got {actual_value}"
                )
    
    async def _monitor_triggers(self):
        """Background task for monitoring trigger health."""
        while not self._shutdown_event.is_set():
            try:
                # Check for failed scheduled tasks
                failed_triggers = []
                for trigger_id, task in self.active_schedules.items():
                    if task.done() and not task.cancelled():
                        try:
                            await task
                        except Exception as e:
                            logger.error(f"Schedule trigger {trigger_id} failed: {str(e)}")
                            failed_triggers.append(trigger_id)
                
                # Restart failed triggers
                for trigger_id in failed_triggers:
                    try:
                        # Get trigger info and restart
                        workflow_id, trigger = await self._get_trigger_info(trigger_id)
                        if workflow_id and trigger:
                            await self._activate_trigger(workflow_id, trigger)
                            logger.info(f"Restarted failed trigger {trigger_id}")
                    except Exception as e:
                        logger.error(f"Failed to restart trigger {trigger_id}: {str(e)}")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Trigger monitoring error: {str(e)}")
                await asyncio.sleep(60)
    
    # Database helper methods
    async def _store_trigger(self, workflow_id: str, user_id: str, trigger: Trigger):
        """Store trigger in database by updating workflow's triggers array."""
        try:
            supabase = get_supabase_client()
            
            # Get current workflow
            response = supabase.table("workflows").select("triggers").eq("id", workflow_id).execute()
            
            if not response.data:
                raise TriggerException(f"Workflow {workflow_id} not found")
            
            current_triggers = response.data[0]["triggers"] or []
            
            # Add new trigger
            trigger_dict = trigger.dict()
            current_triggers.append(trigger_dict)
            
            # Update workflow
            update_response = supabase.table("workflows").update({
                "triggers": current_triggers,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", workflow_id).execute()
            
            if not update_response.data:
                raise TriggerException("Failed to store trigger")
                
        except Exception as e:
            logger.error(f"Failed to store trigger: {str(e)}")
            raise TriggerException(f"Database error: {str(e)}")
    
    async def _update_trigger_in_db(self, workflow_id: str, trigger: Trigger):
        """Update trigger in database."""
        try:
            supabase = get_supabase_client()
            
            # Get current workflow
            response = supabase.table("workflows").select("triggers").eq("id", workflow_id).execute()
            
            if not response.data:
                raise TriggerException(f"Workflow {workflow_id} not found")
            
            current_triggers = response.data[0]["triggers"] or []
            
            # Find and update trigger
            updated_triggers = []
            for trigger_data in current_triggers:
                if trigger_data["id"] == trigger.id:
                    updated_triggers.append(trigger.dict())
                else:
                    updated_triggers.append(trigger_data)
            
            # Update workflow
            update_response = supabase.table("workflows").update({
                "triggers": updated_triggers,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", workflow_id).execute()
            
            if not update_response.data:
                raise TriggerException("Failed to update trigger")
                
        except Exception as e:
            logger.error(f"Failed to update trigger: {str(e)}")
            raise TriggerException(f"Database error: {str(e)}")
    
    async def _delete_trigger_from_db(self, workflow_id: str, trigger_id: str):
        """Delete trigger from database."""
        try:
            supabase = get_supabase_client()
            
            # Get current workflow
            response = supabase.table("workflows").select("triggers").eq("id", workflow_id).execute()
            
            if not response.data:
                raise TriggerException(f"Workflow {workflow_id} not found")
            
            current_triggers = response.data[0]["triggers"] or []
            
            # Remove trigger
            updated_triggers = [t for t in current_triggers if t["id"] != trigger_id]
            
            # Update workflow
            update_response = supabase.table("workflows").update({
                "triggers": updated_triggers,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", workflow_id).execute()
            
            if not update_response.data:
                raise TriggerException("Failed to delete trigger")
                
        except Exception as e:
            logger.error(f"Failed to delete trigger: {str(e)}")
            raise TriggerException(f"Database error: {str(e)}")
    
    async def _get_trigger(self, workflow_id: str, trigger_id: str) -> Optional[Trigger]:
        """Get trigger from database."""
        try:
            supabase = get_supabase_client()
            
            response = supabase.table("workflows").select("triggers").eq("id", workflow_id).execute()
            
            if response.data:
                triggers_data = response.data[0]["triggers"] or []
                for trigger_data in triggers_data:
                    if trigger_data["id"] == trigger_id:
                        return Trigger(**trigger_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get trigger: {str(e)}")
            return None
    
    async def _get_trigger_by_id(self, trigger_id: str) -> Optional[Trigger]:
        """Get trigger by ID across all workflows."""
        try:
            supabase = get_supabase_client()
            
            # Search all workflows for the trigger
            response = supabase.table("workflows").select("triggers").neq("triggers", "[]").execute()
            
            if response.data:
                for workflow_data in response.data:
                    triggers_data = workflow_data["triggers"] or []
                    for trigger_data in triggers_data:
                        if trigger_data["id"] == trigger_id:
                            return Trigger(**trigger_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get trigger by ID: {str(e)}")
            return None
    
    async def _get_workflow(self, workflow_id: str) -> Optional[WorkflowPlan]:
        """Get workflow from database."""
        try:
            supabase = get_supabase_client()
            
            response = supabase.table("workflows").select("*").eq("id", workflow_id).execute()
            
            if response.data:
                workflow_data = response.data[0]
                
                # Convert database format to WorkflowPlan
                workflow = WorkflowPlan(
                    id=workflow_data["id"],
                    user_id=workflow_data["user_id"],
                    name=workflow_data["name"],
                    description=workflow_data["description"] or "",
                    nodes=[WorkflowNode(**node) for node in workflow_data["nodes"]],
                    edges=[WorkflowEdge(**edge) for edge in workflow_data["edges"]],
                    triggers=[Trigger(**trigger) for trigger in workflow_data["triggers"]],
                    status=workflow_data["status"],
                    created_at=datetime.fromisoformat(workflow_data["created_at"]),
                    updated_at=datetime.fromisoformat(workflow_data["updated_at"])
                )
                
                return workflow
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get workflow: {str(e)}")
            return None
    
    async def _store_trigger_execution(self, execution: TriggerExecution):
        """Store trigger execution record."""
        try:
            supabase = get_supabase_client()
            
            # Create trigger execution record
            execution_data = {
                "id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "trigger_id": execution.trigger_id,
                "trigger_type": execution.trigger_type,
                "trigger_data": execution.trigger_data,
                "status": execution.status,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "error_message": execution.error
            }
            
            response = supabase.table("trigger_executions").insert(execution_data).execute()
            
            if not response.data:
                logger.error("Failed to store trigger execution")
                
        except Exception as e:
            logger.error(f"Failed to store trigger execution: {str(e)}")
    
    async def _get_webhook_trigger(self, webhook_id: str) -> Optional[tuple[str, Trigger]]:
        """Get workflow and trigger for a webhook ID."""
        if webhook_id in self.webhook_handlers:
            handler_info = self.webhook_handlers[webhook_id]
            return handler_info["workflow_id"], handler_info["trigger"]
        return None
    
    async def _get_recent_trigger_executions(self, trigger_id: str, limit: int = 10) -> List[TriggerExecution]:
        """Get recent executions for a trigger."""
        try:
            supabase = get_supabase_client()
            
            response = supabase.table("trigger_executions").select("*").eq(
                "trigger_id", trigger_id
            ).order("started_at", desc=True).limit(limit).execute()
            
            executions = []
            if response.data:
                for exec_data in response.data:
                    execution = TriggerExecution(
                        trigger_id=exec_data["trigger_id"],
                        workflow_id=exec_data["workflow_id"],
                        execution_id=exec_data["id"],
                        trigger_type=exec_data["trigger_type"],
                        trigger_data=exec_data["trigger_data"],
                        status=exec_data["status"],
                        started_at=datetime.fromisoformat(exec_data["started_at"]),
                        completed_at=datetime.fromisoformat(exec_data["completed_at"]) if exec_data["completed_at"] else None,
                        error=exec_data["error_message"]
                    )
                    executions.append(execution)
            
            return executions
            
        except Exception as e:
            logger.error(f"Failed to get recent trigger executions: {str(e)}")
            return []
    
    async def _get_next_execution_time(self, trigger: Trigger) -> Optional[str]:
        """Get next execution time for a scheduled trigger."""
        if trigger.type == TriggerType.SCHEDULE:
            try:
                schedule_config = ScheduleConfig(**trigger.config)
                cron = croniter(schedule_config.cron_expression, datetime.utcnow())
                next_run = cron.get_next(datetime)
                return next_run.isoformat()
            except Exception as e:
                logger.error(f"Failed to calculate next execution time: {str(e)}")
        
        return None
    
    async def _update_schedule_config(self, workflow_id: str, trigger_id: str, config: ScheduleConfig):
        """Update schedule configuration in database."""
        try:
            trigger = await self._get_trigger(workflow_id, trigger_id)
            if trigger:
                trigger.config = config.dict()
                await self._update_trigger_in_db(workflow_id, trigger)
        except Exception as e:
            logger.error(f"Failed to update schedule config: {str(e)}")
    
    async def _get_trigger_info(self, trigger_id: str) -> tuple[Optional[str], Optional[Trigger]]:
        """Get workflow ID and trigger for a trigger ID."""
        try:
            supabase = get_supabase_client()
            
            response = supabase.table("workflows").select("id, triggers").neq("triggers", "[]").execute()
            
            if response.data:
                for workflow_data in response.data:
                    triggers_data = workflow_data["triggers"] or []
                    for trigger_data in triggers_data:
                        if trigger_data["id"] == trigger_id:
                            return workflow_data["id"], Trigger(**trigger_data)
            
            return None, None
            
        except Exception as e:
            logger.error(f"Failed to get trigger info: {str(e)}")
            return None, None