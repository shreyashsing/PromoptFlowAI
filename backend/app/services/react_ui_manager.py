"""
ReAct UI Manager - Handles real-time UI updates during agent reasoning.
Shows users exactly what the agent is thinking and doing.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReActUIManager:
    """
    Manages real-time UI updates during ReAct agent execution.
    Provides transparency into agent reasoning and actions.
    """
    
    def __init__(self):
        self.active_sessions = {}
        self.reasoning_history = {}
    
    async def start_session(self, session_id: str, user_request: str) -> None:
        """Start a new ReAct session with UI tracking."""
        self.active_sessions[session_id] = {
            "user_request": user_request,
            "start_time": datetime.now(),
            "current_step": 0,
            "status": "initializing",
            "reasoning_trace": []
        }
        
        await self._send_ui_update(session_id, {
            "type": "session_started",
            "message": f"🤔 Starting to analyze your request: '{user_request}'",
            "status": "thinking"
        })
    
    async def update_reasoning(self, session_id: str, reasoning: str, step_type: str = "reasoning") -> None:
        """Update the UI with current agent reasoning."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session["reasoning_trace"].append({
            "timestamp": datetime.now(),
            "type": step_type,
            "content": reasoning
        })
        
        await self._send_ui_update(session_id, {
            "type": "reasoning_update",
            "step_type": step_type,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat()
        })
    
    async def highlight_connector(self, session_id: str, connector_name: str, action: str, reasoning: str) -> None:
        """Highlight a connector in the UI while the agent works on it."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session["current_step"] += 1
        session["status"] = "working"
        
        await self._send_ui_update(session_id, {
            "type": "connector_highlight",
            "connector_name": connector_name,
            "action": action,
            "reasoning": reasoning,
            "step_number": session["current_step"],
            "status": "working"
        })
        
        # Show thinking animation for a moment
        await asyncio.sleep(1)
    
    async def connector_configured(self, session_id: str, connector_name: str, parameters: Dict[str, Any]) -> None:
        """Show that a connector has been successfully configured."""
        await self._send_ui_update(session_id, {
            "type": "connector_configured",
            "connector_name": connector_name,
            "parameters": parameters,
            "status": "configured"
        })
    
    async def workflow_step_completed(self, session_id: str, step_info: Dict[str, Any]) -> None:
        """Mark a workflow step as completed."""
        await self._send_ui_update(session_id, {
            "type": "step_completed",
            "step_info": step_info,
            "message": f"✅ Completed: {step_info.get('purpose', 'Step')}"
        })
    
    async def workflow_completed(self, session_id: str, final_workflow: Dict[str, Any]) -> None:
        """Mark the entire workflow as completed."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session["status"] = "completed"
        session["end_time"] = datetime.now()
        
        await self._send_ui_update(session_id, {
            "type": "workflow_completed",
            "workflow": final_workflow,
            "total_steps": len(final_workflow.get("steps", [])),
            "duration": (session["end_time"] - session["start_time"]).total_seconds(),
            "message": "🎉 Workflow created successfully!"
        })
    
    async def show_error(self, session_id: str, error: str, step: Optional[str] = None) -> None:
        """Show an error in the UI."""
        await self._send_ui_update(session_id, {
            "type": "error",
            "error": error,
            "step": step,
            "message": f"❌ Error: {error}"
        })
    
    def get_session_trace(self, session_id: str) -> Dict[str, Any]:
        """Get the complete reasoning trace for a session."""
        if session_id not in self.active_sessions:
            return {}
        
        return {
            "session_id": session_id,
            "session_info": self.active_sessions[session_id],
            "reasoning_trace": self.active_sessions[session_id]["reasoning_trace"]
        }
    
    async def _send_ui_update(self, session_id: str, update: Dict[str, Any]) -> None:
        """Send real-time update to the UI (WebSocket or SSE)."""
        # For now, just log the updates
        # In production, this would send to WebSocket/SSE endpoint
        logger.info(f"UI Update [{session_id}]: {update['type']} - {update.get('message', '')}")
        
        # Store for debugging
        if session_id not in self.reasoning_history:
            self.reasoning_history[session_id] = []
        
        self.reasoning_history[session_id].append({
            "timestamp": datetime.now().isoformat(),
            "update": update
        })
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up session data."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Keep reasoning history for debugging
        # Could implement cleanup policy here