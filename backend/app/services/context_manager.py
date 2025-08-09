"""
Enhanced Context Manager for long-term conversation context preservation
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
from collections import defaultdict

class EnhancedContextManager:
    """
    Manages long-term conversation context with intelligent memory management
    """
    
    def __init__(self, max_contexts: int = 1000, context_ttl_hours: int = 24):
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.context_access_times: Dict[str, datetime] = {}
        self.max_contexts = max_contexts
        self.context_ttl = timedelta(hours=context_ttl_hours)
        self.lock = threading.RLock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def get_or_create_context(
        self, 
        session_id: str, 
        user_id: str, 
        preserve_context: bool = True
    ) -> Dict[str, Any]:
        """
        Get existing context or create new one
        """
        with self.lock:
            if session_id in self.contexts:
                # Update access time
                self.context_access_times[session_id] = datetime.now()
                return self.contexts[session_id]
            
            # Create new context
            context = {
                "id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "preserve_context": preserve_context,
                "plan": None,
                "current_step": 0,
                "total_steps": 0,
                "variables": {},
                "connectors_used": [],
                "conversation_history": [],
                "reasoning_history": [],
                "tool_usage_history": [],
                "user_preferences": {},
                "execution_state": "idle",  # idle, planning, executing, waiting_for_user, completed
                "paused_execution": None,
                "long_term_memory": {
                    "key_facts": [],
                    "user_goals": [],
                    "successful_patterns": [],
                    "failed_attempts": []
                }
            }
            
            self.contexts[session_id] = context
            self.context_access_times[session_id] = datetime.now()
            
            # Cleanup old contexts if needed
            self._cleanup_old_contexts()
            
            return context
    
    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context by session ID
        """
        with self.lock:
            if session_id in self.contexts:
                self.context_access_times[session_id] = datetime.now()
                return self.contexts[session_id]
            return None
    
    def update_context(self, session_id: str, new_data: Dict[str, Any]) -> bool:
        """
        Update context with new data
        """
        with self.lock:
            if session_id not in self.contexts:
                return False
            
            context = self.contexts[session_id]
            
            # Update basic fields
            for key, value in new_data.items():
                if key in context:
                    context[key] = value
            
            # Special handling for arrays that should be appended
            if "conversation_history" in new_data:
                if "conversation_history" not in context:
                    context["conversation_history"] = []
                context["conversation_history"].extend(new_data["conversation_history"])
                
                # Keep only last 50 messages to prevent memory bloat
                if len(context["conversation_history"]) > 50:
                    context["conversation_history"] = context["conversation_history"][-50:]
            
            if "reasoning_history" in new_data:
                if "reasoning_history" not in context:
                    context["reasoning_history"] = []
                context["reasoning_history"].extend(new_data["reasoning_history"])
                
                # Keep only last 20 reasoning traces
                if len(context["reasoning_history"]) > 20:
                    context["reasoning_history"] = context["reasoning_history"][-20:]
            
            if "tool_usage_history" in new_data:
                if "tool_usage_history" not in context:
                    context["tool_usage_history"] = []
                context["tool_usage_history"].extend(new_data["tool_usage_history"])
                
                # Keep only last 30 tool calls
                if len(context["tool_usage_history"]) > 30:
                    context["tool_usage_history"] = context["tool_usage_history"][-30:]
            
            # Update connectors used
            if "connectors_used" in new_data:
                if "connectors_used" not in context:
                    context["connectors_used"] = []
                for connector in new_data["connectors_used"]:
                    if connector not in context["connectors_used"]:
                        context["connectors_used"].append(connector)
            
            # Update long-term memory
            if "key_facts" in new_data:
                if "long_term_memory" not in context:
                    context["long_term_memory"] = {"key_facts": [], "user_goals": [], "successful_patterns": [], "failed_attempts": []}
                context["long_term_memory"]["key_facts"].extend(new_data["key_facts"])
                
                # Deduplicate and limit
                context["long_term_memory"]["key_facts"] = list(set(context["long_term_memory"]["key_facts"]))[-20:]
            
            context["updated_at"] = datetime.now().isoformat()
            self.context_access_times[session_id] = datetime.now()
            
            return True
    
    def get_context_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the context for frontend display
        """
        context = self.get_context(session_id)
        if not context:
            return None
        
        return {
            "id": context["id"],
            "title": context.get("plan", "Conversation")[:50],
            "current_step": context.get("current_step", 0),
            "total_steps": context.get("total_steps", 0),
            "variables": context.get("variables", {}),
            "connectors_used": context.get("connectors_used", []),
            "execution_state": context.get("execution_state", "idle"),
            "last_updated": context.get("updated_at"),
            "message_count": len(context.get("conversation_history", [])),
            "key_facts": context.get("long_term_memory", {}).get("key_facts", [])
        }
    
    def clear_context(self, session_id: str) -> bool:
        """
        Clear context for a session
        """
        with self.lock:
            if session_id in self.contexts:
                del self.contexts[session_id]
                if session_id in self.context_access_times:
                    del self.context_access_times[session_id]
                return True
            return False
    
    def get_user_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all contexts for a user
        """
        with self.lock:
            user_contexts = []
            for session_id, context in self.contexts.items():
                if context.get("user_id") == user_id:
                    user_contexts.append(self.get_context_summary(session_id))
            
            # Sort by last updated
            user_contexts.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
            return user_contexts
    
    def extract_key_insights(self, session_id: str) -> Dict[str, Any]:
        """
        Extract key insights from conversation for long-term memory
        """
        context = self.get_context(session_id)
        if not context:
            return {}
        
        insights = {
            "user_goals": [],
            "successful_patterns": [],
            "failed_attempts": [],
            "key_facts": []
        }
        
        # Analyze conversation history
        conversation_history = context.get("conversation_history", [])
        reasoning_history = context.get("reasoning_history", [])
        tool_usage_history = context.get("tool_usage_history", [])
        
        # Extract user goals from messages
        for message in conversation_history:
            if message.get("role") == "user":
                content = message.get("content", "").lower()
                if any(keyword in content for keyword in ["want to", "need to", "goal", "objective", "achieve"]):
                    insights["user_goals"].append(message.get("content", "")[:100])
        
        # Extract successful patterns from completed tool calls
        successful_tools = [tool for tool in tool_usage_history if tool.get("status") == "completed"]
        if successful_tools:
            tool_names = [tool.get("name") for tool in successful_tools]
            insights["successful_patterns"].append(f"Successfully used tools: {', '.join(set(tool_names))}")
        
        # Extract failed attempts
        failed_tools = [tool for tool in tool_usage_history if tool.get("status") == "error"]
        if failed_tools:
            for tool in failed_tools:
                insights["failed_attempts"].append(f"Failed to use {tool.get('name')}: {tool.get('error', 'Unknown error')}")
        
        # Extract key facts from reasoning
        for reasoning in reasoning_history:
            if reasoning.get("observation"):
                insights["key_facts"].append(reasoning.get("observation")[:100])
        
        return insights
    
    def _cleanup_old_contexts(self):
        """
        Remove old or excess contexts
        """
        now = datetime.now()
        
        # Remove expired contexts
        expired_sessions = []
        for session_id, access_time in self.context_access_times.items():
            if now - access_time > self.context_ttl:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            if session_id in self.contexts:
                del self.contexts[session_id]
            if session_id in self.context_access_times:
                del self.context_access_times[session_id]
        
        # Remove excess contexts (keep most recently accessed)
        if len(self.contexts) > self.max_contexts:
            # Sort by access time and remove oldest
            sorted_sessions = sorted(
                self.context_access_times.items(),
                key=lambda x: x[1]
            )
            
            excess_count = len(self.contexts) - self.max_contexts
            for session_id, _ in sorted_sessions[:excess_count]:
                if session_id in self.contexts:
                    del self.contexts[session_id]
                if session_id in self.context_access_times:
                    del self.context_access_times[session_id]
    
    def _start_cleanup_thread(self):
        """
        Start background thread for periodic cleanup
        """
        import threading
        import time
        
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    with self.lock:
                        self._cleanup_old_contexts()
                except Exception as e:
                    print(f"Context cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about context usage
        """
        with self.lock:
            return {
                "total_contexts": len(self.contexts),
                "max_contexts": self.max_contexts,
                "context_ttl_hours": self.context_ttl.total_seconds() / 3600,
                "oldest_context": min(self.context_access_times.values()) if self.context_access_times else None,
                "newest_context": max(self.context_access_times.values()) if self.context_access_times else None
            }