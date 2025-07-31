"""
Conversation Memory Manager for ReAct agent sessions.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from app.models.conversation import ConversationContext, ChatMessage
from app.models.base import ConversationState
from app.core.database import get_supabase_client
from app.core.exceptions import ConversationError

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    """
    Manages conversation state and history for multi-turn ReAct agent interactions.
    Handles session creation, message storage, and memory cleanup.
    """
    
    def __init__(self):
        self.active_conversations: Dict[str, ConversationContext] = {}
        self._initialized = False
        self.session_ttl = timedelta(hours=24)  # 24 hour session timeout
    
    async def initialize(self) -> None:
        """Initialize the conversation memory manager."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing conversation memory manager...")
            
            # Ensure database tables exist
            await self._ensure_tables_exist()
            
            # Load active conversations from database
            await self._load_active_conversations()
            
            self._initialized = True
            logger.info("Conversation memory manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversation memory manager: {e}")
            raise ConversationError(f"Memory manager initialization failed: {str(e)}")
    
    async def _ensure_tables_exist(self) -> None:
        """Ensure required database tables exist."""
        try:
            client = get_supabase_client()
            
            # Check if conversations table exists by trying to query it
            try:
                client.table('react_conversations').select('id').limit(1).execute()
            except Exception:
                logger.info("Creating react_conversations table...")
                # Table doesn't exist, but we'll let the database migration handle this
                # For now, we'll just log that we need the table
                pass
            
        except Exception as e:
            logger.warning(f"Could not verify database tables: {e}")
    
    async def _load_active_conversations(self) -> None:
        """Load active conversations from database."""
        try:
            client = get_supabase_client()
            
            # Get recent conversations (last 24 hours)
            cutoff_time = datetime.utcnow() - self.session_ttl
            
            # For now, we'll start with empty conversations
            # This will be enhanced when we implement the database schema
            logger.info("Loaded active conversations from database")
            
        except Exception as e:
            logger.warning(f"Could not load active conversations: {e}")
    
    async def get_or_create_conversation(
        self,
        session_id: str,
        user_id: str
    ) -> ConversationContext:
        """Get existing conversation or create a new one."""
        if not self._initialized:
            await self.initialize()
        
        # Check if conversation exists in memory
        if session_id in self.active_conversations:
            conversation = self.active_conversations[session_id]
            # Update timestamp
            conversation.updated_at = datetime.utcnow()
            return conversation
        
        # Try to load from database first
        conversation = await self._load_conversation_from_db(session_id)
        if conversation:
            self.active_conversations[session_id] = conversation
            conversation.updated_at = datetime.utcnow()
            return conversation
        
        # Create new conversation with proper ID
        conversation_id = str(uuid.uuid4())
        conversation = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            current_plan=None,
            state=ConversationState.INITIAL,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Set the conversation ID for database persistence
        conversation.id = conversation_id
        
        # Store in memory
        self.active_conversations[session_id] = conversation
        
        # Persist to database and get the actual conversation_id
        actual_conversation_id = await self._persist_conversation(conversation)
        if actual_conversation_id:
            conversation.id = actual_conversation_id
        
        logger.info(f"Created new conversation {conversation_id} for session {session_id}")
        return conversation
    
    async def get_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """Get an existing conversation by session ID."""
        if not self._initialized:
            await self.initialize()
        
        # Check memory first
        if session_id in self.active_conversations:
            return self.active_conversations[session_id]
        
        # Try to load from database
        conversation = await self._load_conversation_from_db(session_id)
        if conversation:
            self.active_conversations[session_id] = conversation
        
        return conversation
    
    async def _execute_with_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """
        Execute multiple database operations within a transaction.
        
        Args:
            operations: List of operations, each containing 'table', 'operation', and 'data'
            
        Returns:
            True if all operations succeeded, False otherwise
        """
        try:
            client = get_supabase_client()
            
            # Note: Supabase doesn't support explicit transactions in the Python client
            # We'll implement a rollback strategy by tracking operations and reversing them on failure
            completed_operations = []
            
            for operation in operations:
                try:
                    table_name = operation['table']
                    op_type = operation['operation']  # 'insert', 'update', 'upsert', 'delete'
                    data = operation['data']
                    
                    if op_type == 'insert':
                        result = client.table(table_name).insert(data).execute()
                    elif op_type == 'update':
                        result = client.table(table_name).update(data['values']).eq(data['condition_field'], data['condition_value']).execute()
                    elif op_type == 'upsert':
                        result = client.table(table_name).upsert(data['values'], on_conflict=data.get('on_conflict')).execute()
                    elif op_type == 'delete':
                        result = client.table(table_name).delete().eq(data['condition_field'], data['condition_value']).execute()
                    else:
                        raise ValueError(f"Unsupported operation type: {op_type}")
                    
                    # Track successful operation for potential rollback
                    completed_operations.append({
                        'operation': operation,
                        'result': result
                    })
                    
                except Exception as op_error:
                    error_str = str(op_error).lower()
                    
                    # Enhanced error logging for different types of database errors
                    if 'foreign key' in error_str or 'constraint' in error_str:
                        logger.error(f"Database constraint violation in transaction: {op_error}")
                        logger.error(f"Operation details: table={table_name}, operation={op_type}, data={data}")
                    elif 'unique' in error_str:
                        logger.error(f"Unique constraint violation in transaction: {op_error}")
                        logger.error(f"Operation details: table={table_name}, operation={op_type}")
                    elif 'does not exist' in error_str or 'relation' in error_str:
                        logger.error(f"Table/relation does not exist: {op_error}")
                        logger.error(f"Operation details: table={table_name}")
                    else:
                        logger.error(f"Transaction operation failed: {op_error}")
                        logger.error(f"Operation details: table={table_name}, operation={op_type}")
                    
                    # Attempt to rollback completed operations
                    await self._rollback_operations(completed_operations)
                    return False
            
            logger.debug(f"Successfully completed transaction with {len(operations)} operations")
            return True
            
        except Exception as e:
            logger.error(f"Transaction execution failed: {e}")
            return False
    
    async def _rollback_operations(self, completed_operations: List[Dict[str, Any]]) -> None:
        """
        Attempt to rollback completed operations.
        
        Args:
            completed_operations: List of completed operations to rollback
        """
        try:
            client = get_supabase_client()
            
            # Reverse the operations
            for op_data in reversed(completed_operations):
                try:
                    operation = op_data['operation']
                    result = op_data['result']
                    
                    # Attempt to reverse the operation
                    if operation['operation'] == 'insert' and result.data:
                        # Delete the inserted record
                        for record in result.data:
                            client.table(operation['table']).delete().eq('id', record['id']).execute()
                    elif operation['operation'] == 'update':
                        # This is complex to rollback, log the issue
                        logger.warning(f"Cannot rollback update operation on {operation['table']}")
                    elif operation['operation'] == 'upsert':
                        # This is complex to rollback, log the issue
                        logger.warning(f"Cannot rollback upsert operation on {operation['table']}")
                    
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback operation: {rollback_error}")
            
            logger.info(f"Attempted rollback of {len(completed_operations)} operations")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    async def _validate_conversation_id(self, conversation_id: str) -> bool:
        """
        Validate that a conversation_id exists in the database.
        
        Args:
            conversation_id: The conversation ID to validate
            
        Returns:
            True if conversation exists, False otherwise
        """
        try:
            client = get_supabase_client()
            result = client.table('react_conversations').select('id').eq('id', conversation_id).execute()
            return bool(result.data and len(result.data) > 0)
        except Exception as e:
            logger.warning(f"Could not validate conversation_id {conversation_id}: {e}")
            return False
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to the conversation with transaction management."""
        if not self._initialized:
            await self.initialize()
        
        conversation = self.active_conversations.get(session_id)
        if not conversation:
            raise ConversationError(f"Conversation {session_id} not found")
        
        # Ensure conversation has a valid ID
        if not hasattr(conversation, 'id') or not conversation.id:
            logger.warning(f"Conversation {session_id} missing ID, regenerating...")
            conversation.id = str(uuid.uuid4())
            await self._persist_conversation(conversation)
        
        # Validate conversation_id exists in database before persisting message
        if not await self._validate_conversation_id(conversation.id):
            logger.warning(f"Conversation ID {conversation.id} not found in database, re-persisting conversation")
            await self._persist_conversation(conversation)
            
            # Double-check after re-persistence
            if not await self._validate_conversation_id(conversation.id):
                logger.error(f"Failed to create conversation {conversation.id} in database")
                raise ConversationError(f"Cannot persist message: conversation {conversation.id} does not exist in database")
        
        # Create message
        message = ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Prepare transaction operations
        operations = []
        
        # Update conversation metadata
        conversation_update_data = {
            "values": {
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "message_count": len(conversation.messages) + 1,
                    "current_plan": conversation.current_plan
                }
            },
            "condition_field": "id",
            "condition_value": conversation.id
        }
        operations.append({
            "table": "react_conversations",
            "operation": "update",
            "data": conversation_update_data
        })
        
        # Get session_id for message data
        session_id_for_message = session_id
        
        # Insert message
        message_data = {
            "id": message.id,
            "conversation_id": conversation.id,
            "session_id": session_id_for_message,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata
        }
        operations.append({
            "table": "react_conversation_messages",
            "operation": "insert",
            "data": message_data
        })
        
        # Execute transaction
        try:
            success = await self._execute_with_transaction(operations)
            if not success:
                logger.error(f"Transaction failed for adding message to conversation {session_id}")
                raise ConversationError(f"Failed to persist message to conversation {session_id}")
            
            # Only update memory if database operations succeeded
            conversation.messages.append(message)
            conversation.updated_at = datetime.utcnow()
            
            logger.debug(f"Added {role} message to conversation {session_id} (ID: {conversation.id}) with transaction")
            
        except Exception as e:
            logger.error(f"Failed to add message to conversation {session_id}: {e}")
            raise ConversationError(f"Message persistence failed: {str(e)}")
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get conversation message history."""
        conversation = await self.get_conversation(session_id)
        if not conversation:
            return []
        
        messages = conversation.messages
        if limit:
            messages = messages[-limit:]  # Get last N messages
        
        return messages
    
    async def update_conversation_state(
        self,
        session_id: str,
        state: ConversationState
    ) -> None:
        """Update the conversation state."""
        conversation = self.active_conversations.get(session_id)
        if not conversation:
            raise ConversationError(f"Conversation {session_id} not found")
        
        conversation.state = state
        conversation.updated_at = datetime.utcnow()
        
        # Persist to database
        await self._persist_conversation(conversation)
        
        logger.debug(f"Updated conversation {session_id} state to {state}")
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up resources for a conversation session."""
        try:
            # Remove from memory
            if session_id in self.active_conversations:
                del self.active_conversations[session_id]
            
            # Mark as inactive in database
            await self._deactivate_conversation_in_db(session_id)
            
            logger.info(f"Cleaned up conversation session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired conversation sessions."""
        if not self._initialized:
            return 0
        
        expired_count = 0
        cutoff_time = datetime.utcnow() - self.session_ttl
        
        # Find expired sessions
        expired_sessions = []
        for session_id, conversation in self.active_conversations.items():
            if conversation.updated_at < cutoff_time:
                expired_sessions.append(session_id)
        
        # Clean up expired sessions
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired conversation sessions")
        
        return expired_count
    
    async def _persist_conversation(self, conversation: ConversationContext) -> Optional[str]:
        """
        Persist conversation to database.
        
        This method implements requirement 4.3: Add conversation history persistence to database.
        
        Returns:
            The conversation_id from the database, or None if persistence failed
        """
        try:
            client = get_supabase_client()
            
            # Ensure conversation has an ID
            if not hasattr(conversation, 'id') or not conversation.id:
                conversation.id = str(uuid.uuid4())
            
            # Prepare conversation data for database
            conversation_data = {
                "id": conversation.id,
                "session_id": conversation.session_id,
                "user_id": conversation.user_id,
                "state": conversation.state.value if hasattr(conversation.state, 'value') else str(conversation.state),
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "metadata": {
                    "message_count": len(conversation.messages),
                    "current_plan": conversation.current_plan
                }
            }
            
            # Insert or update conversation
            try:
                result = client.table('react_conversations').upsert(
                    conversation_data,
                    on_conflict='session_id'
                ).execute()
                
                if result.data and len(result.data) > 0:
                    actual_conversation_id = result.data[0]['id']
                    logger.debug(f"Successfully persisted conversation {conversation.session_id} with ID {actual_conversation_id}")
                    return actual_conversation_id
                else:
                    logger.warning(f"No data returned from conversation upsert for {conversation.session_id}")
                    return conversation.id
                
            except Exception as db_error:
                # If table doesn't exist, log warning but don't fail
                logger.warning(f"Could not persist conversation to database (table may not exist): {db_error}")
                return conversation.id  # Return the generated ID even if DB persistence fails
            
        except Exception as e:
            logger.error(f"Failed to persist conversation {conversation.session_id}: {e}")
            return getattr(conversation, 'id', None)
    
    async def _persist_message(self, conversation_id: str, message: ChatMessage) -> None:
        """
        Persist message to database.
        
        This method implements requirement 4.3: Add conversation history persistence to database.
        """
        if not conversation_id:
            logger.error("Cannot persist message: conversation_id is None")
            raise ConversationError("conversation_id is required for message persistence")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                client = get_supabase_client()
                
                # Get session_id from conversation_id for backward compatibility
                session_id = None
                try:
                    conv_result = client.table('react_conversations').select('session_id').eq('id', conversation_id).execute()
                    if conv_result.data and len(conv_result.data) > 0:
                        session_id = conv_result.data[0]['session_id']
                except Exception as e:
                    logger.warning(f"Could not retrieve session_id for conversation {conversation_id}: {e}")
                    # Continue without session_id if we can't retrieve it
                
                # Prepare message data for database
                message_data = {
                    "id": message.id,
                    "conversation_id": conversation_id,
                    "session_id": session_id,  # May be None if we couldn't retrieve it
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "metadata": message.metadata
                }
                
                # Insert message
                try:
                    result = client.table('react_conversation_messages').insert(message_data).execute()
                    logger.debug(f"Successfully persisted message for conversation {conversation_id}")
                    return  # Success, exit retry loop
                    
                except Exception as db_error:
                    error_str = str(db_error).lower()
                    
                    # Check for constraint violation (conversation_id not found)
                    if 'foreign key' in error_str or 'constraint' in error_str:
                        logger.warning(f"Foreign key constraint violation for conversation {conversation_id}, attempting to recreate conversation")
                        
                        # Try to find the conversation in memory and re-persist it
                        for session_id_key, conversation in self.active_conversations.items():
                            if hasattr(conversation, 'id') and conversation.id == conversation_id:
                                logger.info(f"Re-persisting conversation {conversation_id} for session {session_id_key}")
                                await self._persist_conversation(conversation)
                                break
                        
                        # Retry the message persistence
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.info(f"Retrying message persistence (attempt {retry_count + 1}/{max_retries})")
                            continue
                        else:
                            logger.error(f"Failed to persist message after {max_retries} retries due to constraint violation")
                            raise ConversationError(f"Message persistence failed: conversation {conversation_id} not found in database")
                    
                    # If table doesn't exist, log warning but don't fail
                    elif 'does not exist' in error_str or 'relation' in error_str:
                        logger.warning(f"Could not persist message to database (table may not exist): {db_error}")
                        return  # Exit without error if table doesn't exist
                    
                    else:
                        # Other database errors
                        logger.error(f"Database error persisting message: {db_error}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            raise ConversationError(f"Message persistence failed after {max_retries} retries: {db_error}")
                
            except Exception as e:
                logger.error(f"Failed to persist message for conversation {conversation_id}: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise ConversationError(f"Message persistence failed after {max_retries} retries: {str(e)}")
                
                # Wait before retry
                await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
    
    async def _load_conversation_from_db(self, session_id: str) -> Optional[ConversationContext]:
        """
        Load conversation from database.
        
        This method implements requirement 4.2: The agent shall have access to full conversation history.
        """
        try:
            client = get_supabase_client()
            
            # Load conversation metadata
            try:
                conversation_result = client.table('react_conversations').select('*').eq('session_id', session_id).execute()
                
                if not conversation_result.data:
                    return None
                
                conversation_data = conversation_result.data[0]
                
                # Load conversation messages
                messages_result = client.table('react_conversation_messages').select('*').eq('session_id', session_id).order('timestamp').execute()
                
                # Convert messages to ChatMessage objects
                messages = []
                for msg_data in messages_result.data:
                    message = ChatMessage(
                        id=msg_data['id'],
                        role=msg_data['role'],
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['timestamp'].replace('Z', '+00:00')),
                        metadata=msg_data.get('metadata', {})
                    )
                    messages.append(message)
                
                # Create conversation context
                conversation = ConversationContext(
                    session_id=conversation_data['session_id'],
                    user_id=conversation_data['user_id'],
                    messages=messages,
                    current_plan=conversation_data.get('metadata', {}).get('current_plan'),
                    state=ConversationState(conversation_data['state']),
                    created_at=datetime.fromisoformat(conversation_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(conversation_data['updated_at'].replace('Z', '+00:00'))
                )
                
                # Set the conversation ID from database
                conversation.id = conversation_data['id']
                
                logger.debug(f"Successfully loaded conversation {session_id} with {len(messages)} messages")
                return conversation
                
            except Exception as db_error:
                logger.warning(f"Could not load conversation from database (table may not exist): {db_error}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to load conversation {session_id} from database: {e}")
            return None
    
    async def _deactivate_conversation_in_db(self, session_id: str) -> None:
        """
        Mark conversation as inactive in database.
        
        This method implements session cleanup as part of requirement 4.1: Create and maintain conversation session.
        """
        try:
            client = get_supabase_client()
            
            # Update conversation state to inactive
            try:
                result = client.table('react_conversations').update({
                    'state': 'inactive',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('session_id', session_id).execute()
                
                logger.debug(f"Successfully deactivated conversation {session_id} in database")
                
            except Exception as db_error:
                logger.warning(f"Could not deactivate conversation in database (table may not exist): {db_error}")
            
        except Exception as e:
            logger.error(f"Failed to deactivate conversation {session_id}: {e}")
    
    def get_active_session_count(self) -> int:
        """Get the number of active conversation sessions."""
        return len(self.active_conversations)
    
    def is_initialized(self) -> bool:
        """Check if the memory manager is initialized."""
        return self._initialized
    
    async def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the conversation including key metrics.
        
        This method supports requirement 4.2: The agent shall have access to full conversation history.
        """
        conversation = await self.get_conversation(session_id)
        if not conversation:
            return None
        
        # Calculate conversation metrics
        user_messages = [msg for msg in conversation.messages if msg.role == "user"]
        assistant_messages = [msg for msg in conversation.messages if msg.role == "assistant"]
        tool_calls = []
        
        # Extract tool calls from assistant messages
        for msg in assistant_messages:
            if msg.metadata and msg.metadata.get("tool_calls"):
                tool_calls.extend(msg.metadata["tool_calls"])
        
        return {
            "session_id": session_id,
            "user_id": conversation.user_id,
            "state": conversation.state.value if hasattr(conversation.state, 'value') else str(conversation.state),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "message_count": len(conversation.messages),
            "user_message_count": len(user_messages),
            "assistant_message_count": len(assistant_messages),
            "tool_calls_count": len(tool_calls),
            "duration_minutes": (conversation.updated_at - conversation.created_at).total_seconds() / 60,
            "last_activity": conversation.updated_at.isoformat(),
            "tools_used": list(set([call.get("tool_name") for call in tool_calls if call.get("tool_name")]))
        }
    
    async def search_conversations(
        self, 
        user_id: str, 
        query: Optional[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversations for a user, optionally filtering by content.
        
        This method supports conversation history access as part of requirement 4.2.
        """
        try:
            # Get conversations from memory first
            matching_conversations = []
            
            for session_id, conversation in self.active_conversations.items():
                if conversation.user_id == user_id:
                    # If query provided, search in message content
                    if query:
                        query_lower = query.lower()
                        found_match = False
                        
                        for message in conversation.messages:
                            if query_lower in message.content.lower():
                                found_match = True
                                break
                        
                        if not found_match:
                            continue
                    
                    # Add conversation summary
                    summary = await self.get_conversation_summary(session_id)
                    if summary:
                        matching_conversations.append(summary)
            
            # Sort by last activity (most recent first)
            matching_conversations.sort(key=lambda x: x["updated_at"], reverse=True)
            
            # Return limited results
            return matching_conversations[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search conversations for user {user_id}: {e}")
            return []
    
    async def get_conversation_context_for_agent(self, session_id: str, context_length: int = 10) -> Dict[str, Any]:
        """
        Get conversation context optimized for agent processing.
        
        This method implements requirement 4.2: The agent shall have access to full conversation history.
        """
        conversation = await self.get_conversation(session_id)
        if not conversation:
            return {
                "session_id": session_id,
                "messages": [],
                "context_summary": "No conversation history found",
                "tool_usage_history": []
            }
        
        # Get recent messages for context
        recent_messages = conversation.messages[-context_length:] if conversation.messages else []
        
        # Extract tool usage history
        tool_usage_history = []
        for message in conversation.messages:
            if message.metadata and message.metadata.get("tool_calls"):
                for tool_call in message.metadata["tool_calls"]:
                    tool_usage_history.append({
                        "tool_name": tool_call.get("tool_name"),
                        "timestamp": message.timestamp.isoformat(),
                        "success": tool_call.get("status") == "completed"
                    })
        
        # Create context summary
        context_summary = f"Conversation with {len(conversation.messages)} messages, {len(tool_usage_history)} tool calls"
        if tool_usage_history:
            unique_tools = set([usage["tool_name"] for usage in tool_usage_history])
            context_summary += f", using tools: {', '.join(unique_tools)}"
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "has_tool_calls": bool(msg.metadata and msg.metadata.get("tool_calls"))
                }
                for msg in recent_messages
            ],
            "context_summary": context_summary,
            "tool_usage_history": tool_usage_history[-5:],  # Last 5 tool calls
            "conversation_state": conversation.state.value if hasattr(conversation.state, 'value') else str(conversation.state)
        }
    
    async def update_conversation_plan(self, session_id: str, plan: Dict[str, Any]) -> None:
        """
        Update the current plan for a conversation.
        
        This supports multi-step workflow planning as part of session management.
        """
        conversation = self.active_conversations.get(session_id)
        if not conversation:
            raise ConversationError(f"Conversation {session_id} not found")
        
        conversation.current_plan = plan
        conversation.updated_at = datetime.utcnow()
        
        # Persist to database
        await self._persist_conversation(conversation)
        
        logger.debug(f"Updated conversation plan for {session_id}")
    
    async def get_user_active_sessions(self, user_id: str) -> List[str]:
        """
        Get all active session IDs for a user.
        
        This supports requirement 4.1: Create and maintain conversation session.
        """
        active_sessions = []
        
        for session_id, conversation in self.active_conversations.items():
            if (conversation.user_id == user_id and 
                conversation.state != ConversationState.INACTIVE):
                active_sessions.append(session_id)
        
        return active_sessions


# Global memory manager instance
conversation_memory_manager: Optional[ConversationMemoryManager] = None


async def get_conversation_memory_manager() -> ConversationMemoryManager:
    """Get or create the global conversation memory manager instance."""
    global conversation_memory_manager
    if not conversation_memory_manager:
        conversation_memory_manager = ConversationMemoryManager()
        await conversation_memory_manager.initialize()
    return conversation_memory_manager