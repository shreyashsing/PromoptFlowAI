"""
Event-driven executor for AI agent with pause/resume capabilities
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

class ExecutionState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_FOR_USER = "waiting_for_user"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class UserInputType(Enum):
    API_KEY = "api_key"
    AUTHENTICATION = "authentication"
    PARAMETER = "parameter"
    CONFIRMATION = "confirmation"
    CHOICE = "choice"

class ExecutionContext:
    """
    Represents the current execution context that can be paused and resumed
    """
    
    def __init__(self, session_id: str, agent, query: str):
        self.session_id = session_id
        self.agent = agent
        self.query = query
        self.state = ExecutionState.IDLE
        self.current_step = 0
        self.total_steps = 0
        self.execution_plan = []
        self.reasoning_trace = []
        self.tool_calls = []
        self.variables = {}
        self.pause_reason = None
        self.user_input_required = None
        self.created_at = datetime.now()
        self.paused_at = None
        self.resumed_at = None
        self.completed_at = None
        self.error = None

class EventDrivenExecutor:
    """
    Manages event-driven execution with pause/resume capabilities
    """
    
    def __init__(self):
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.paused_executions: Dict[str, ExecutionContext] = {}
        self.execution_callbacks: Dict[str, List[Callable]] = {}
    
    async def execute_with_pause_capability(
        self,
        agent,
        query: str,
        context: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute agent query with ability to pause for user input
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create execution context
        exec_context = ExecutionContext(session_id, agent, query)
        exec_context.state = ExecutionState.PLANNING
        
        self.active_executions[session_id] = exec_context
        
        try:
            # Phase 1: Planning
            planning_result = await self._execute_planning_phase(exec_context, context)
            
            if planning_result.get("requires_user_input"):
                return await self._pause_for_user_input(exec_context, planning_result)
            
            # Phase 2: Execution
            exec_context.state = ExecutionState.EXECUTING
            execution_result = await self._execute_workflow_phase(exec_context, context)
            
            if execution_result.get("requires_user_input"):
                return await self._pause_for_user_input(exec_context, execution_result)
            
            # Phase 3: Completion
            exec_context.state = ExecutionState.COMPLETED
            exec_context.completed_at = datetime.now()
            
            # Move to completed executions
            if session_id in self.active_executions:
                del self.active_executions[session_id]
            
            return {
                "response": execution_result.get("response", "Task completed successfully"),
                "reasoning_trace": exec_context.reasoning_trace,
                "tool_calls": exec_context.tool_calls,
                "waiting_for_user": False,
                "user_input_required": None,
                "execution_state": ExecutionState.COMPLETED.value,
                "variables": exec_context.variables
            }
            
        except Exception as e:
            exec_context.state = ExecutionState.ERROR
            exec_context.error = str(e)
            
            if session_id in self.active_executions:
                del self.active_executions[session_id]
            
            return {
                "response": f"Execution failed: {str(e)}",
                "reasoning_trace": exec_context.reasoning_trace,
                "tool_calls": exec_context.tool_calls,
                "waiting_for_user": False,
                "user_input_required": None,
                "execution_state": ExecutionState.ERROR.value,
                "error": str(e)
            }
    
    async def resume_execution(
        self,
        session_id: str,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resume paused execution with user input
        """
        if session_id not in self.paused_executions:
            raise ValueError(f"No paused execution found for session {session_id}")
        
        exec_context = self.paused_executions[session_id]
        exec_context.resumed_at = datetime.now()
        exec_context.state = ExecutionState.EXECUTING
        
        # Move back to active executions
        self.active_executions[session_id] = exec_context
        del self.paused_executions[session_id]
        
        try:
            # Process user input based on what was requested
            if exec_context.user_input_required:
                await self._process_user_input(exec_context, user_input)
            
            # Continue execution from where it left off
            execution_result = await self._continue_workflow_execution(exec_context, context)
            
            if execution_result.get("requires_user_input"):
                return await self._pause_for_user_input(exec_context, execution_result)
            
            # Execution completed
            exec_context.state = ExecutionState.COMPLETED
            exec_context.completed_at = datetime.now()
            
            if session_id in self.active_executions:
                del self.active_executions[session_id]
            
            return {
                "response": execution_result.get("response", "Task completed successfully"),
                "reasoning_trace": exec_context.reasoning_trace,
                "tool_calls": exec_context.tool_calls,
                "waiting_for_user": False,
                "user_input_required": None,
                "execution_state": ExecutionState.COMPLETED.value,
                "variables": exec_context.variables
            }
            
        except Exception as e:
            exec_context.state = ExecutionState.ERROR
            exec_context.error = str(e)
            
            if session_id in self.active_executions:
                del self.active_executions[session_id]
            
            return {
                "response": f"Execution failed after resume: {str(e)}",
                "reasoning_trace": exec_context.reasoning_trace,
                "tool_calls": exec_context.tool_calls,
                "waiting_for_user": False,
                "user_input_required": None,
                "execution_state": ExecutionState.ERROR.value,
                "error": str(e)
            }
    
    async def _execute_planning_phase(
        self,
        exec_context: ExecutionContext,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the planning phase
        """
        try:
            # Add reasoning trace
            exec_context.reasoning_trace.append({
                "step_number": 1,
                "thought": f"I need to analyze the user's request: '{exec_context.query}'",
                "action": "analyze_request",
                "action_input": {"query": exec_context.query},
                "observation": "Starting analysis of user request"
            })
            
            # Use the agent to create a plan
            planning_result = await exec_context.agent.create_execution_plan(
                query=exec_context.query,
                context=context
            )
            
            exec_context.execution_plan = planning_result.get("plan", [])
            exec_context.total_steps = len(exec_context.execution_plan)
            
            # Check if planning requires user input
            if planning_result.get("requires_user_input"):
                return {
                    "requires_user_input": True,
                    "user_input_type": planning_result.get("user_input_type"),
                    "message": planning_result.get("message"),
                    "field_name": planning_result.get("field_name"),
                    "options": planning_result.get("options")
                }
            
            exec_context.reasoning_trace.append({
                "step_number": 2,
                "thought": f"Created execution plan with {exec_context.total_steps} steps",
                "action": "create_plan",
                "action_input": {"steps": exec_context.total_steps},
                "observation": f"Plan created: {[step.get('description', '') for step in exec_context.execution_plan]}"
            })
            
            return {"requires_user_input": False}
            
        except Exception as e:
            raise Exception(f"Planning phase failed: {str(e)}")
    
    async def _execute_workflow_phase(
        self,
        exec_context: ExecutionContext,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the workflow phase
        """
        try:
            response_parts = []
            
            for i, step in enumerate(exec_context.execution_plan):
                exec_context.current_step = i + 1
                
                # Add reasoning trace for this step
                exec_context.reasoning_trace.append({
                    "step_number": exec_context.current_step + 2,  # +2 for planning steps
                    "thought": f"Executing step {exec_context.current_step}: {step.get('description', '')}",
                    "action": step.get("action", "unknown"),
                    "action_input": step.get("parameters", {}),
                    "observation": "Starting step execution"
                })
                
                # Execute the step
                step_result = await self._execute_single_step(exec_context, step, context)
                
                if step_result.get("requires_user_input"):
                    return step_result
                
                if step_result.get("response"):
                    response_parts.append(step_result["response"])
                
                # Update variables with step results
                if step_result.get("variables"):
                    exec_context.variables.update(step_result["variables"])
                
                # Update reasoning trace with results
                exec_context.reasoning_trace[-1]["observation"] = step_result.get("observation", "Step completed")
            
            return {
                "response": "\n\n".join(response_parts) if response_parts else "All steps completed successfully",
                "requires_user_input": False
            }
            
        except Exception as e:
            raise Exception(f"Workflow execution failed: {str(e)}")
    
    async def _execute_single_step(
        self,
        exec_context: ExecutionContext,
        step: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step
        """
        try:
            action = step.get("action")
            parameters = step.get("parameters", {})
            
            # Check if this step requires user input
            if self._step_requires_user_input(step, exec_context.variables):
                missing_params = self._get_missing_parameters(step, exec_context.variables)
                return {
                    "requires_user_input": True,
                    "user_input_type": self._determine_input_type(missing_params[0]),
                    "message": f"I need additional information to proceed with {step.get('description', 'this step')}. Please provide: {missing_params[0]}",
                    "field_name": missing_params[0],
                    "options": step.get("options")
                }
            
            # Execute the step using the agent
            tool_call = {
                "name": action,
                "input": parameters,
                "status": "pending",
                "started_at": datetime.now().isoformat()
            }
            exec_context.tool_calls.append(tool_call)
            
            # Call the actual tool/connector
            result = await exec_context.agent.execute_tool(action, parameters, context)
            
            # Update tool call status
            tool_call["status"] = "completed" if result.get("success") else "error"
            tool_call["output"] = result.get("result", result.get("error"))
            tool_call["completed_at"] = datetime.now().isoformat()
            
            if not result.get("success"):
                raise Exception(f"Step failed: {result.get('error', 'Unknown error')}")
            
            return {
                "response": result.get("result", "Step completed"),
                "variables": result.get("variables", {}),
                "observation": f"Successfully executed {action}",
                "requires_user_input": False
            }
            
        except Exception as e:
            # Update tool call status
            if exec_context.tool_calls:
                exec_context.tool_calls[-1]["status"] = "error"
                exec_context.tool_calls[-1]["error"] = str(e)
                exec_context.tool_calls[-1]["completed_at"] = datetime.now().isoformat()
            
            raise Exception(f"Step execution failed: {str(e)}")
    
    async def _continue_workflow_execution(
        self,
        exec_context: ExecutionContext,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Continue workflow execution after user input
        """
        try:
            response_parts = []
            
            # Continue from current step
            for i in range(exec_context.current_step - 1, len(exec_context.execution_plan)):
                exec_context.current_step = i + 1
                step = exec_context.execution_plan[i]
                
                # Execute the step
                step_result = await self._execute_single_step(exec_context, step, context)
                
                if step_result.get("requires_user_input"):
                    return step_result
                
                if step_result.get("response"):
                    response_parts.append(step_result["response"])
                
                # Update variables
                if step_result.get("variables"):
                    exec_context.variables.update(step_result["variables"])
            
            return {
                "response": "\n\n".join(response_parts) if response_parts else "Remaining steps completed successfully",
                "requires_user_input": False
            }
            
        except Exception as e:
            raise Exception(f"Continued execution failed: {str(e)}")
    
    async def _pause_for_user_input(
        self,
        exec_context: ExecutionContext,
        pause_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pause execution and wait for user input
        """
        exec_context.state = ExecutionState.WAITING_FOR_USER
        exec_context.paused_at = datetime.now()
        exec_context.pause_reason = pause_info.get("message", "User input required")
        exec_context.user_input_required = {
            "type": pause_info.get("user_input_type", UserInputType.PARAMETER.value),
            "message": pause_info.get("message", "Please provide the required information"),
            "field_name": pause_info.get("field_name"),
            "options": pause_info.get("options")
        }
        
        # Move to paused executions
        session_id = exec_context.session_id
        self.paused_executions[session_id] = exec_context
        if session_id in self.active_executions:
            del self.active_executions[session_id]
        
        return {
            "response": f"I need some information from you to continue. {exec_context.pause_reason}",
            "reasoning_trace": exec_context.reasoning_trace,
            "tool_calls": exec_context.tool_calls,
            "waiting_for_user": True,
            "user_input_required": exec_context.user_input_required,
            "execution_state": ExecutionState.WAITING_FOR_USER.value,
            "variables": exec_context.variables
        }
    
    async def _process_user_input(
        self,
        exec_context: ExecutionContext,
        user_input: str
    ):
        """
        Process user input and update execution context
        """
        if not exec_context.user_input_required:
            return
        
        input_type = exec_context.user_input_required.get("type")
        field_name = exec_context.user_input_required.get("field_name")
        
        # Store user input in variables
        if field_name:
            exec_context.variables[field_name] = user_input
        
        # Add reasoning trace
        exec_context.reasoning_trace.append({
            "step_number": len(exec_context.reasoning_trace) + 1,
            "thought": f"User provided {input_type}: {user_input}",
            "action": "process_user_input",
            "action_input": {"input": user_input, "type": input_type},
            "observation": f"Received and stored user input for {field_name or 'execution'}"
        })
        
        # Clear user input requirement
        exec_context.user_input_required = None
        exec_context.pause_reason = None
    
    def _step_requires_user_input(
        self,
        step: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> bool:
        """
        Check if a step requires user input
        """
        required_params = step.get("required_parameters", [])
        for param in required_params:
            if param not in variables or not variables[param]:
                return True
        return False
    
    def _get_missing_parameters(
        self,
        step: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of missing parameters for a step
        """
        required_params = step.get("required_parameters", [])
        missing = []
        for param in required_params:
            if param not in variables or not variables[param]:
                missing.append(param)
        return missing
    
    def _determine_input_type(self, parameter_name: str) -> str:
        """
        Determine the type of user input required based on parameter name
        """
        param_lower = parameter_name.lower()
        
        if "api" in param_lower and "key" in param_lower:
            return UserInputType.API_KEY.value
        elif "auth" in param_lower or "token" in param_lower or "password" in param_lower:
            return UserInputType.AUTHENTICATION.value
        elif "confirm" in param_lower or "approve" in param_lower:
            return UserInputType.CONFIRMATION.value
        elif "choice" in param_lower or "select" in param_lower:
            return UserInputType.CHOICE.value
        else:
            return UserInputType.PARAMETER.value
    
    def get_execution_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current execution status
        """
        if session_id in self.active_executions:
            exec_context = self.active_executions[session_id]
            return {
                "session_id": session_id,
                "state": exec_context.state.value,
                "current_step": exec_context.current_step,
                "total_steps": exec_context.total_steps,
                "created_at": exec_context.created_at.isoformat(),
                "paused_at": exec_context.paused_at.isoformat() if exec_context.paused_at else None,
                "pause_reason": exec_context.pause_reason,
                "user_input_required": exec_context.user_input_required
            }
        elif session_id in self.paused_executions:
            exec_context = self.paused_executions[session_id]
            return {
                "session_id": session_id,
                "state": exec_context.state.value,
                "current_step": exec_context.current_step,
                "total_steps": exec_context.total_steps,
                "created_at": exec_context.created_at.isoformat(),
                "paused_at": exec_context.paused_at.isoformat() if exec_context.paused_at else None,
                "pause_reason": exec_context.pause_reason,
                "user_input_required": exec_context.user_input_required
            }
        
        return None
    
    def cancel_execution(self, session_id: str) -> bool:
        """
        Cancel an active or paused execution
        """
        if session_id in self.active_executions:
            del self.active_executions[session_id]
            return True
        elif session_id in self.paused_executions:
            del self.paused_executions[session_id]
            return True
        
        return False