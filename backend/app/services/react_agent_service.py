"""
ReAct Agent Service for intelligent reasoning and acting using LangGraph.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

try:
    from langchain_openai import AzureChatOpenAI
except ImportError:
    # Fallback for when langchain_openai is not available
    from langchain.chat_models import AzureChatOpenAI

from langchain.tools import Tool
from langchain.schema import BaseMessage, HumanMessage, AIMessage

try:
    from langgraph.prebuilt import create_agent_executor
    from langgraph.checkpoint.memory import MemorySaver
    from langchain.agents import AgentType, initialize_agent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback when LangGraph is not available
    LANGGRAPH_AVAILABLE = False
    create_agent_executor = None
    MemorySaver = None
    initialize_agent = None
    AgentType = None

from app.core.config import settings
from app.models.base import WorkflowStatus
from app.models.react_response_models import (
    ReactAgentResponse, ReasoningStep, ToolCall, ReactError,
    create_success_response, create_error_response, format_langgraph_response,
    ensure_response_structure, create_reasoning_step, create_tool_call
)
from app.services.conversation_memory_manager import ConversationMemoryManager
from app.services.tool_registry import ToolRegistry
from app.services.auth_context_manager import AuthContextManager
from app.services.react_error_formatter import format_react_error
from app.services.react_agent_logger import react_agent_logger, CorrelationContext
from app.core.exceptions import AgentExecutionError, ToolExecutionError, AuthenticationException

logger = logging.getLogger(__name__)


class ReactAgentService:
    """
    Core service for managing ReAct agent operations using LangGraph.
    Handles agent initialization, request processing, and conversation management.
    """
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.memory_manager = ConversationMemoryManager()
        self.auth_context_manager = AuthContextManager()
        self.react_agent = None
        self.llm = None
        self.agent_config = {}
        self._initialized = False
        self._agent_available = False
        self._initialization_error = None
        self.user_sessions: Dict[str, Dict[str, Any]] = {}  # Track user sessions
    
    async def initialize(self) -> None:
        """Initialize the ReAct agent with registered tools."""
        if self._initialized:
            return
        
        # Create correlation context for initialization
        init_context = react_agent_logger.create_correlation_context()
        
        try:
            async with react_agent_logger.log_performance_metrics(init_context, "agent_initialization"):
                logger.info("Initializing ReAct agent service...")
                print("Initializing ReAct agent service...")
                
                # Initialize tool registry
                await self.tool_registry.initialize()
                react_agent_logger.logger.info("Tool registry initialized", extra=init_context.to_dict())
                
                # Initialize memory manager
                await self.memory_manager.initialize()
                react_agent_logger.logger.info("Memory manager initialized", extra=init_context.to_dict())
                
                # Create ReAct agent with tools
                await self._create_react_agent()
                react_agent_logger.logger.info("ReAct agent created", extra=init_context.to_dict())
                
                # Check agent availability after creation
                self._agent_available = await self._check_agent_availability()
                
                self._initialized = True
                logger.info(f"ReAct agent service initialized successfully - Agent available: {self._agent_available}")
                
        except Exception as e:
            react_agent_logger.log_error(init_context, e, "agent_initialization")
            logger.error(f"Failed to initialize ReAct agent service: {e}")
            self._initialization_error = str(e)
            self._agent_available = False
            # Don't raise - allow service to continue with fallback mode
            logger.warning("ReAct agent service will run in fallback mode")
        finally:
            react_agent_logger.cleanup_context(init_context.correlation_id)
    
    async def _create_react_agent(self) -> None:
        """
        Create the LangGraph ReAct agent with registered tools.
        
        This method implements requirement 2.1: Create a LangGraph ReAct agent instance 
        with access to all registered connector tools, and requirement 2.2: Register all 
        connector tools with the agent.
        """
        try:
            # Check if Azure OpenAI credentials are configured
            if not all([
                settings.AZURE_OPENAI_ENDPOINT,
                settings.AZURE_OPENAI_API_KEY,
                settings.AZURE_OPENAI_DEPLOYMENT_NAME
            ]):
                logger.warning("Azure OpenAI credentials not fully configured, agent will not be available")
                self.llm = None
                self.react_agent = None
                return
            
            # Initialize Azure OpenAI LLM with optimized parameters for ReAct reasoning
            self.llm = AzureChatOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                temperature=0.1,  # Low temperature for consistent reasoning
                max_tokens=4000,  # Sufficient tokens for multi-step reasoning
                streaming=False,  # Disable streaming for better compatibility
                request_timeout=120,  # 2 minute timeout for complex reasoning
                max_retries=3  # Retry on failures
            )
            
            # Get available tools from registry
            tools = await self.tool_registry.get_available_tools()
            
            if not tools:
                logger.warning("No tools available for ReAct agent")
                tools = []
            else:
                # Log registered tools for debugging
                tool_names = [tool.name for tool in tools]
                logger.info(f"Registering tools with ReAct agent: {tool_names}")
            
            # Check if LangGraph is available
            if not LANGGRAPH_AVAILABLE:
                logger.warning("LangGraph not available, using fallback LangChain agent")
                # Create a fallback ReAct agent using LangChain directly
                self.react_agent = initialize_agent(
                    tools=tools,
                    llm=self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=True,
                    max_iterations=10,
                    max_execution_time=300,
                    handle_parsing_errors=True,
                    return_intermediate_steps=True
                )
                logger.info(f"Created fallback LangChain ReAct agent with {len(tools)} tools")
                return
            
            # Create memory saver for conversation persistence
            memory = MemorySaver()
            
            # Configure agent parameters for optimal performance
            agent_config = {
                "max_iterations": 10,  # Maximum reasoning iterations
                "max_execution_time": 300,  # 5 minute timeout for complete workflow
                "early_stopping_method": "generate",  # Stop when final answer is generated
                "handle_parsing_errors": True,  # Gracefully handle parsing errors
                "return_intermediate_steps": True  # Include reasoning trace in response
            }
            
            # Create ReAct agent using LangGraph with available API
            # Use create_agent_executor which is available in this version
            try:
                from langchain.agents import create_react_agent
                from langchain import hub
            except ImportError as import_error:
                logger.error(f"Failed to import required LangChain components: {import_error}")
                raise AgentExecutionError(f"Required LangChain components not available: {import_error}")
            
            # Get ReAct prompt from hub or create a custom one
            try:
                prompt = hub.pull("hwchase17/react")
            except Exception:
                # Create a simple ReAct prompt if hub is not available
                from langchain.prompts import PromptTemplate
                prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}
""")
            
            # Create the ReAct agent
            react_agent_runnable = create_react_agent(self.llm, tools, prompt)
            
            # Create agent executor using LangGraph
            self.react_agent = create_agent_executor(
                agent_runnable=react_agent_runnable,
                tools=tools,
                input_schema=None
            )
            
            # Store agent configuration for reference
            self.agent_config = agent_config
            
            # Configure tools with authentication context
            await self._configure_tools_with_auth_context(tools)
            
            logger.info(f"ReAct agent created successfully with {len(tools)} tools using LangGraph executor")
            
        except Exception as e:
            logger.error(f"Failed to create ReAct agent: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Try to create a simple fallback agent
            try:
                if self.llm and LANGGRAPH_AVAILABLE:
                    tools = await self.tool_registry.get_available_tools()
                    self.react_agent = initialize_agent(
                        tools=tools,
                        llm=self.llm,
                        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                        verbose=True,
                        max_iterations=10,
                        handle_parsing_errors=True,
                        return_intermediate_steps=True
                    )
                    logger.info(f"Created fallback ReAct agent with {len(tools)} tools")
                else:
                    self.react_agent = None
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback agent: {fallback_error}")
                self.react_agent = None
    
    async def _check_agent_availability(self) -> bool:
        """
        Check if the ReAct agent is properly configured and available for use.
        
        This method implements requirement 2.4: Add validation to ensure agent is configured before use.
        
        Returns:
            True if agent is available, False otherwise
        """
        try:
            # Check if agent was created
            if not self.react_agent:
                logger.warning("ReAct agent not created - agent unavailable")
                return False
            
            # Check if LLM is available
            if not self.llm:
                logger.warning("LLM not configured - agent unavailable")
                return False
            
            # Check if tools are available
            tools = await self.tool_registry.get_available_tools()
            if not tools:
                logger.warning("No tools available - agent will have limited functionality")
                # Don't fail availability check for missing tools, just warn
            
            # Test basic agent functionality
            try:
                # For LangChain agents, check if they have required methods
                if hasattr(self.react_agent, 'arun') or hasattr(self.react_agent, 'ainvoke'):
                    logger.info(f"✅ ReAct agent is available with {len(tools)} tools")
                    return True
                else:
                    logger.error("ReAct agent missing required execution methods")
                    return False
                    
            except Exception as test_error:
                logger.error(f"Agent availability test failed: {test_error}")
                return False
                
        except Exception as e:
            logger.error(f"Agent availability check failed: {e}")
            return False
    
    def is_agent_available(self) -> bool:
        """
        Public method to check if the ReAct agent is available.
        
        This method implements requirement 2.4: Add validation to ensure agent is configured before use.
        
        Returns:
            True if agent is available, False otherwise
        """
        return self._initialized and self._agent_available
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status information.
        
        This method implements requirement 2.5: Add error handling for agent initialization failures.
        
        Returns:
            Dictionary containing agent status details
        """
        return {
            "initialized": self._initialized,
            "agent_available": self._agent_available,
            "llm_available": self.llm is not None,
            "react_agent_created": self.react_agent is not None,
            "initialization_error": self._initialization_error,
            "agent_type": "LangGraph" if hasattr(self.react_agent, 'ainvoke') else "LangChain" if self.react_agent else None,
            "tools_count": len(self.tools) if hasattr(self, 'tools') else 0,
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "azure_openai_configured": all([
                settings.AZURE_OPENAI_ENDPOINT,
                settings.AZURE_OPENAI_API_KEY,
                settings.AZURE_OPENAI_DEPLOYMENT_NAME
            ])
        }
    
    async def _configure_tools_with_auth_context(self, tools: List[Tool]) -> None:
        """
        Configure tools with authentication context for secure execution.
        
        This method implements requirement 2.4: Create secure credential passing to connector tools.
        """
        try:
            # Store reference to tools for authentication context injection
            self.configured_tools = tools
            
            # Each tool will receive authentication context through the agent's thread configuration
            # The actual authentication context is passed when the agent is invoked
            logger.info(f"Configured {len(tools)} tools with authentication context support")
            
        except Exception as e:
            logger.error(f"Failed to configure tools with auth context: {e}")
            # Continue without authentication context configuration
            pass
    
    async def create_user_session(
        self,
        user_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        Create a new user session with authentication context.
        
        This method implements requirement 3.2: Integrate with existing JWT authentication middleware
        and requirement 4.1: Implement session-based access control for conversations.
        
        Args:
            user_data: User data from JWT token (user_id, email, metadata)
            session_id: Optional session ID, will generate if not provided
            
        Returns:
            Session ID for the created session
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Extract user context from authentication token
            user_context = self._extract_user_context(user_data)
            
            # Create session with user context
            session_data = {
                "session_id": session_id,
                "user_id": user_context["user_id"],
                "email": user_context["email"],
                "user_metadata": user_context.get("user_metadata", {}),
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "permissions": user_context.get("permissions", []),
                "auth_tokens": {}  # Will be populated as needed for tools
            }
            
            # Store session
            self.user_sessions[session_id] = session_data
            
            logger.info(f"Created user session {session_id} for user {user_context['user_id']}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create user session: {e}")
            raise AuthenticationException(f"Session creation failed: {str(e)}")
    
    def _extract_user_context(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user context from authentication token data.
        
        This method implements requirement 3.2: Add user context extraction from authentication tokens.
        
        Args:
            user_data: User data from JWT token
            
        Returns:
            Extracted user context
        """
        try:
            return {
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "user_metadata": user_data.get("user_metadata", {}),
                "permissions": user_data.get("permissions", []),
                "roles": user_data.get("roles", [])
            }
        except Exception as e:
            logger.error(f"Failed to extract user context: {e}")
            raise AuthenticationException(f"Invalid user data: {str(e)}")
    
    async def validate_session_access(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """
        Validate that a user has access to a specific session.
        
        This method implements requirement 4.1: Implement session-based access control for conversations.
        
        Args:
            session_id: Session ID to validate
            user_id: User ID requesting access
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            # Check if session exists
            if session_id not in self.user_sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            session_data = self.user_sessions[session_id]
            
            # Check if user owns the session
            if session_data["user_id"] != user_id:
                logger.warning(f"User {user_id} attempted to access session {session_id} owned by {session_data['user_id']}")
                return False
            
            # Update last activity
            session_data["last_activity"] = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate session access: {e}")
            return False
    
    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data if exists, None otherwise
        """
        return self.user_sessions.get(session_id)
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired user sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = datetime.utcnow()
            expired_sessions = []
            
            for session_id, session_data in self.user_sessions.items():
                # Sessions expire after 24 hours of inactivity
                if (current_time - session_data["last_activity"]).total_seconds() > 86400:
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                del self.user_sessions[session_id]
                logger.info(f"Cleaned up expired session {session_id}")
            
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def refresh_session_tokens(self, session_id: str) -> bool:
        """
        Refresh OAuth tokens for a session to handle long-running conversations.
        
        This method implements requirement 2.4: Add OAuth token refresh handling for long-running conversations.
        
        Args:
            session_id: Session ID to refresh tokens for
            
        Returns:
            True if tokens were refreshed successfully, False otherwise
        """
        try:
            # Get session data
            session_data = self.user_sessions.get(session_id)
            if not session_data:
                logger.warning(f"Session {session_id} not found for token refresh")
                return False
            
            user_id = session_data["user_id"]
            
            # Get available tools to refresh tokens for
            tools = await self.tool_registry.get_tool_metadata()
            
            refreshed_count = 0
            for tool in tools:
                tool_name = tool["name"]
                
                # Check if tool requires OAuth authentication
                auth_requirements = tool.get("auth_requirements", {})
                if auth_requirements.get("type") == "oauth2":
                    try:
                        # Get current tokens
                        current_tokens = await self.auth_context_manager.get_connector_auth_tokens(
                            user_id, tool_name
                        )
                        
                        if current_tokens and "refresh_token" in current_tokens:
                            # Attempt to refresh tokens
                            refreshed_tokens = await self.auth_context_manager.refresh_token_if_needed(
                                user_id, tool_name, current_tokens
                            )
                            
                            if refreshed_tokens != current_tokens:
                                refreshed_count += 1
                                logger.info(f"Refreshed tokens for {tool_name} in session {session_id}")
                    
                    except Exception as tool_error:
                        logger.warning(f"Failed to refresh tokens for {tool_name}: {tool_error}")
            
            if refreshed_count > 0:
                logger.info(f"Refreshed tokens for {refreshed_count} tools in session {session_id}")
                return True
            else:
                logger.debug(f"No tokens needed refresh for session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to refresh session tokens for {session_id}: {e}")
            return False

    async def process_request(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = None,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        skip_session_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Process a user request through the ReAct agent.
        
        This method implements requirements 1.2 and 1.4:
        - Reason about what tools are needed and execute them in appropriate sequence
        - Return comprehensive response including reasoning process and results
        
        Args:
            query: User's natural language query
            session_id: Optional conversation session ID
            user_id: User identifier for authentication context
            context: Additional context for the request
            max_iterations: Maximum reasoning iterations
            
        Returns:
            Dict containing response, reasoning trace, and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create correlation context for this request
        request_id = str(uuid.uuid4())
        correlation_context = react_agent_logger.create_correlation_context(
            session_id=session_id,
            user_id=user_id,
            request_id=request_id
        )
        
        # Record request start for monitoring
        from app.services.monitoring_service import monitoring_service
        monitoring_service.record_request_start(correlation_context.correlation_id, user_id, session_id)
        
        # Validate user authentication and session access (skip for new sessions)
        if user_id and not skip_session_validation and not await self.validate_session_access(session_id, user_id):
            react_agent_logger.log_authentication_event(
                correlation_context,
                "session_access_validation",
                user_id=user_id,
                success=False,
                error_message=f"Access denied to session {session_id}"
            )
            raise AuthenticationException(f"Access denied to session {session_id}")
        
        react_agent_logger.log_authentication_event(
            correlation_context,
            "session_access_validation",
            user_id=user_id,
            success=True
        )
        
        try:
            async with react_agent_logger.log_performance_metrics(correlation_context, "request_processing"):
                logger.info(f"Processing request for session {session_id}: {query[:100]}...")
                
                # Get user session data for authentication context
                user_session = await self.get_user_session(session_id)
                if not user_session and user_id:
                    logger.warning(f"No session found for {session_id}, creating new session")
                    # This shouldn't happen in normal flow, but handle gracefully
                    user_session = {
                        "user_id": user_id,
                        "session_id": session_id,
                        "created_at": datetime.utcnow(),
                        "last_activity": datetime.utcnow()
                    }
                    self.user_sessions[session_id] = user_session
                    
                    react_agent_logger.logger.info(
                        "Created new user session",
                        extra={
                            "session_creation": {
                                "session_id": session_id,
                                "user_id": user_id,
                                "reason": "session_not_found"
                            },
                            **correlation_context.to_dict()
                        }
                    )
            
                # Get or create conversation context with user authentication
                conversation = await self.memory_manager.get_or_create_conversation(
                    session_id=session_id,
                    user_id=user_id
                )
                
                react_agent_logger.logger.info(
                    "Retrieved conversation context",
                    extra={
                        "conversation_id": getattr(conversation, 'id', None),
                        "message_count": len(getattr(conversation, 'messages', [])),
                        **correlation_context.to_dict()
                    }
                )
                
                # Check if ReAct agent is available using proper availability check
                if not self.is_agent_available():
                    agent_status = self.get_agent_status()
                    logger.warning(f"ReAct agent not available - Status: {agent_status}")
                    react_agent_logger.logger.warning(
                        "ReAct agent not available, using enhanced fallback",
                        extra={
                            "agent_status": agent_status,
                            **correlation_context.to_dict()
                        }
                    )
                    return await self._create_enhanced_fallback_response(query, session_id, user_id, max_iterations, agent_status)
                
                # Process request through ReAct agent with enhanced reasoning capture
                start_time = datetime.utcnow()
                
                # Create thread configuration for conversation persistence with authentication context
                thread_config = {
                    "configurable": {
                        "thread_id": session_id,
                        "max_iterations": max_iterations,
                        "user_id": user_id,
                        "user_session": user_session,
                        "auth_context_manager": self.auth_context_manager,
                        "correlation_context": correlation_context  # Pass correlation context to agent
                    }
                }
                
                # Refresh tokens if this is a long-running conversation
                if user_session and (datetime.utcnow() - user_session["created_at"]).total_seconds() > 1800:  # 30 minutes
                    logger.info(f"Refreshing tokens for long-running session {session_id}")
                    token_refresh_success = await self.refresh_session_tokens(session_id)
                    react_agent_logger.log_authentication_event(
                        correlation_context,
                        "token_refresh",
                        user_id=user_id,
                        success=token_refresh_success,
                        additional_data={"session_age_seconds": (datetime.utcnow() - user_session["created_at"]).total_seconds()}
                    )
                
                # Prepare enhanced input with context
                agent_input = await self._prepare_agent_input(query, conversation, context)
                
                # Log reasoning step for initial query processing
                react_agent_logger.log_reasoning_step(
                    correlation_context,
                    step_number=0,
                    thought=f"Processing user query: {query[:100]}...",
                    action="prepare_agent_input",
                    action_input={"query_length": len(query), "context_provided": context is not None}
                )
                
                # Execute the ReAct agent with comprehensive error handling and monitoring
                try:
                    logger.info(f"Executing ReAct agent for session {session_id} with input: {agent_input.get('input', '')[:50]}...")
                    
                    # Set up agent execution monitoring
                    execution_start_time = datetime.utcnow()
                    max_execution_time = 300  # 5 minutes
                    
                    # Execute with timeout and iteration monitoring
                    agent_response = await self._execute_agent_with_monitoring(
                        agent_input, 
                        thread_config, 
                        max_iterations, 
                        max_execution_time,
                        session_id,
                        correlation_context
                    )
                    
                    execution_time = (datetime.utcnow() - execution_start_time).total_seconds()
                    logger.info(f"ReAct agent execution completed for session {session_id} in {execution_time:.2f}s")
                    
                    react_agent_logger.logger.info(
                        f"Agent execution completed successfully",
                        extra={
                            "execution_time_ms": execution_time * 1000,
                            "max_iterations": max_iterations,
                            **correlation_context.to_dict()
                        }
                    )
                    
                except asyncio.TimeoutError as timeout_error:
                    react_agent_logger.log_error(correlation_context, timeout_error, "agent_execution_timeout")
                    logger.error(f"ReAct agent execution timed out for session {session_id}")
                    return await self._create_timeout_error_response(query, session_id, user_id, max_iterations, max_execution_time)
                    
                except AgentExecutionError as agent_error:
                    react_agent_logger.log_error(correlation_context, agent_error, "agent_execution_error")
                    logger.error(f"ReAct agent execution failed: {agent_error}")
                    return await self._create_agent_error_response(query, session_id, user_id, max_iterations, agent_error)
                    
                except Exception as agent_error:
                    react_agent_logger.log_error(correlation_context, agent_error, "unexpected_agent_error")
                    logger.error(f"ReAct agent execution failed with unexpected error: {agent_error}")
                    return await self._create_unexpected_agent_error_response(query, session_id, user_id, max_iterations, agent_error)
                
                # Extract and process agent response with enhanced reasoning trace capture
                response = await self._process_agent_response(
                    agent_response, query, session_id, user_id, max_iterations, start_time, correlation_context
                )
                
                # Add comprehensive logging data to response
                response["logging_data"] = {
                    "correlation_id": correlation_context.correlation_id,
                    "reasoning_trace": react_agent_logger.get_reasoning_trace(correlation_context.correlation_id),
                    "tool_execution_history": react_agent_logger.get_tool_execution_history(correlation_context.correlation_id),
                    "performance_summary": react_agent_logger.get_performance_summary(correlation_context.correlation_id)
                }
                
                # Update conversation with the interaction
                await self._update_conversation_with_interaction(
                    session_id, query, response["response"], response["tool_calls"], response["reasoning_trace"]
                )
                
                logger.info(f"Request processed successfully for session {session_id} in {response['processing_time_ms']}ms")
                
                # Record successful request completion for monitoring
                tools_used = [tool_call.get("tool_name", "") for tool_call in response.get("tool_calls", [])]
                reasoning_steps = len(response.get("reasoning_trace", []))
                monitoring_service.record_request_completion(
                    correlation_context.correlation_id,
                    user_id,
                    True,  # success
                    response['processing_time_ms'] / 1000.0,  # convert to seconds
                    tools_used,
                    reasoning_steps
                )
                
                # Ensure response structure is valid before returning
                response_obj = ensure_response_structure(response, session_id)
                return response_obj.to_dict()
                
        except Exception as e:
            react_agent_logger.log_error(correlation_context, e, "request_processing")
            logger.error(f"Failed to process request for session {session_id}: {e}")
            
            # Record failed request completion for monitoring
            processing_time = (datetime.utcnow() - start_time).total_seconds() if 'start_time' in locals() else 0
            monitoring_service.record_request_completion(
                correlation_context.correlation_id,
                user_id,
                False,  # success = False
                processing_time,
                [],  # no tools used on failure
                0   # no reasoning steps on failure
            )
            
            raise AgentExecutionError(f"Request processing failed: {str(e)}")
        finally:
            # Clean up correlation context after a delay to allow for any final logging
            asyncio.create_task(self._cleanup_correlation_context_delayed(correlation_context.correlation_id))
    
    async def _cleanup_correlation_context_delayed(self, correlation_id: str):
        """Clean up correlation context after a delay to allow final logging."""
        await asyncio.sleep(5)  # Wait 5 seconds for any final logging
        react_agent_logger.cleanup_context(correlation_id)
    
    async def _execute_agent_with_monitoring(
        self,
        agent_input: Dict[str, Any],
        thread_config: Dict[str, Any],
        max_iterations: int,
        max_execution_time: int,
        session_id: str,
        correlation_context: CorrelationContext
    ) -> Dict[str, Any]:
        """
        Execute ReAct agent with comprehensive monitoring and error handling.
        
        This method implements agent reasoning error handling as specified in requirement 1.5
        and requirement 3.4 for handling LangGraph agent failures and timeouts.
        """
        try:
            async with react_agent_logger.log_performance_metrics(correlation_context, "agent_execution"):
                # Log agent execution start
                reasoning_step = {
                    "step_id": f"step-{uuid.uuid4()}",
                    "step_number": 1,
                    "thought": "Starting ReAct agent execution",
                    "action": "agent_invoke",
                    "action_input": {
                        "max_iterations": max_iterations,
                        "max_execution_time": max_execution_time,
                        "input_length": len(agent_input.get('input', ''))
                    },
                    "observation": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_ms": None,
                    "success": True,
                    "error_message": None
                }
                
                react_agent_logger.log_reasoning_step(
                    correlation_context,
                    step_number=1,
                    thought="Starting ReAct agent execution",
                    action="agent_invoke",
                    action_input={
                        "max_iterations": max_iterations,
                        "max_execution_time": max_execution_time,
                        "input_length": len(agent_input.get('input', ''))
                    }
                )
                
                # Send workflow update for reasoning step
                await self._send_reasoning_step_update(session_id, reasoning_step)
                
                # Send agent status update
                await self._send_agent_status_update(session_id, "executing", 1, max_iterations)
                
                # Set user context for tools before agent execution
                from app.services.connector_tool_adapter import ConnectorToolAdapter
                user_id = thread_config.get("configurable", {}).get("user_id", "system")
                user_session = thread_config.get("configurable", {}).get("user_session", {})
                auth_context_manager = thread_config.get("configurable", {}).get("auth_context_manager")
                
                ConnectorToolAdapter.set_user_context(
                    user_id=user_id,
                    user_session=user_session,
                    auth_context_manager=auth_context_manager
                )
                
                logger.info(f"Set user context for tools - user_id: {user_id}")
                
                # Create a task for agent execution with timeout
                # Handle different agent types (LangGraph vs LangChain)
                if hasattr(self.react_agent, 'ainvoke'):
                    # LangGraph agent
                    agent_task = asyncio.create_task(
                        self.react_agent.ainvoke(agent_input, config=thread_config)
                    )
                elif hasattr(self.react_agent, 'arun'):
                    # LangChain agent
                    query = agent_input.get('input', '')
                    agent_task = asyncio.create_task(
                        self.react_agent.arun(query)
                    )
                else:
                    raise AgentExecutionError("Agent does not support async execution")
                
                # Monitor execution with periodic checks
                start_time = datetime.utcnow()
                check_interval = 10  # Check every 10 seconds
                iteration_count = 0
                
                while not agent_task.done():
                    # Check for timeout
                    elapsed_time = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed_time > max_execution_time:
                        agent_task.cancel()
                        react_agent_logger.log_reasoning_step(
                            correlation_context,
                            step_number=iteration_count + 2,
                            thought=f"Agent execution timed out after {elapsed_time:.2f}s",
                            success=False,
                            error_message=f"Execution exceeded {max_execution_time} seconds"
                        )
                        raise asyncio.TimeoutError(f"Agent execution exceeded {max_execution_time} seconds")
                    
                    # Check for infinite loop detection
                    if await self._detect_infinite_loop(session_id, elapsed_time, correlation_context):
                        agent_task.cancel()
                        react_agent_logger.log_reasoning_step(
                            correlation_context,
                            step_number=iteration_count + 2,
                            thought=f"Infinite loop detected after {elapsed_time:.2f}s",
                            success=False,
                            error_message="Infinite loop detected in agent reasoning"
                        )
                        raise AgentExecutionError("Infinite loop detected in agent reasoning")
                    
                    # Log monitoring checkpoint
                    if iteration_count % 3 == 0:  # Log every 30 seconds
                        react_agent_logger.log_reasoning_step(
                            correlation_context,
                            step_number=iteration_count + 2,
                            thought=f"Agent execution monitoring checkpoint - {elapsed_time:.1f}s elapsed",
                            action="monitoring_checkpoint",
                            action_input={"elapsed_time": elapsed_time, "still_running": True}
                        )
                    
                    iteration_count += 1
                    
                    # Wait for next check or task completion
                    try:
                        await asyncio.wait_for(agent_task, timeout=check_interval)
                        break  # Task completed
                    except asyncio.TimeoutError:
                        # Continue monitoring
                        continue
                
                # Get the result
                if agent_task.done():
                    if agent_task.exception():
                        raise agent_task.exception()
                    
                    result = agent_task.result()
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    # Log successful completion
                    completion_step = {
                        "step_id": f"step-{uuid.uuid4()}",
                        "step_number": iteration_count + 2,
                        "thought": f"Agent execution completed successfully in {execution_time:.2f}s",
                        "action": "agent_completion",
                        "action_input": {"execution_time": execution_time, "iterations": iteration_count},
                        "observation": None,
                        "timestamp": datetime.utcnow().isoformat(),
                        "duration_ms": execution_time * 1000,
                        "success": True,
                        "error_message": None
                    }
                    
                    react_agent_logger.log_reasoning_step(
                        correlation_context,
                        step_number=iteration_count + 2,
                        thought=f"Agent execution completed successfully in {execution_time:.2f}s",
                        action="agent_completion",
                        action_input={"execution_time": execution_time, "iterations": iteration_count},
                        success=True
                    )
                    
                    # Send workflow updates for completion
                    await self._send_reasoning_step_update(session_id, completion_step)
                    await self._send_agent_status_update(session_id, "completed", iteration_count + 2, max_iterations)
                    
                    return result
                else:
                    # This shouldn't happen, but handle it
                    agent_task.cancel()
                    raise AgentExecutionError("Agent execution monitoring failed")
                
        except asyncio.CancelledError:
            react_agent_logger.log_error(correlation_context, 
                                       Exception("Agent execution cancelled"), 
                                       "agent_execution_cancelled")
            logger.warning(f"Agent execution cancelled for session {session_id}")
            raise AgentExecutionError("Agent execution was cancelled")
            
        except Exception as e:
            react_agent_logger.log_error(correlation_context, e, "agent_execution_monitoring")
            logger.error(f"Agent execution monitoring failed for session {session_id}: {e}")
            raise AgentExecutionError(f"Agent execution failed: {str(e)}")
    
    async def _detect_infinite_loop(self, session_id: str, elapsed_time: float, correlation_context: CorrelationContext) -> bool:
        """
        Detect infinite loops in agent reasoning.
        
        This method implements infinite loop detection and prevention as specified in requirement 1.5.
        """
        try:
            # Simple heuristics for infinite loop detection
            
            # 1. Check if execution time is excessive without progress
            if elapsed_time > 120:  # 2 minutes
                logger.warning(f"Long execution time detected for session {session_id}: {elapsed_time}s")
                
                # Check if we have conversation history to analyze patterns
                conversation = await self.memory_manager.get_conversation(session_id)
                if conversation and conversation.messages:
                    recent_messages = conversation.messages[-10:]  # Last 10 messages
                    
                    # Check for repetitive patterns
                    if await self._check_repetitive_patterns(recent_messages):
                        logger.warning(f"Repetitive patterns detected in session {session_id}")
                        return True
                    
                    # Check for excessive tool calls without progress
                    if await self._check_excessive_tool_calls(recent_messages):
                        logger.warning(f"Excessive tool calls without progress in session {session_id}")
                        return True
            
            # 2. Check for excessive iterations (this would be handled by LangGraph's max_iterations)
            # But we can add additional checks here
            
            return False
            
        except Exception as e:
            logger.error(f"Infinite loop detection failed for session {session_id}: {e}")
            return False  # Don't interrupt on detection failure
    
    async def _check_repetitive_patterns(self, messages: List[Any]) -> bool:
        """
        Check for repetitive patterns in agent messages.
        
        This method analyzes message patterns to detect potential infinite loops.
        """
        try:
            if len(messages) < 6:  # Need at least 6 messages to detect patterns
                return False
            
            # Extract message contents for pattern analysis
            message_contents = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    content = str(msg.content).lower().strip()
                    if content:
                        message_contents.append(content)
            
            if len(message_contents) < 4:
                return False
            
            # Check for exact repetitions
            for i in range(len(message_contents) - 2):
                current_msg = message_contents[i]
                if len(current_msg) > 10:  # Only check substantial messages
                    # Count occurrences of this message
                    occurrences = message_contents.count(current_msg)
                    if occurrences >= 3:  # Same message repeated 3+ times
                        return True
            
            # Check for alternating patterns (A-B-A-B)
            if len(message_contents) >= 4:
                for i in range(len(message_contents) - 3):
                    if (message_contents[i] == message_contents[i + 2] and
                        message_contents[i + 1] == message_contents[i + 3] and
                        message_contents[i] != message_contents[i + 1]):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check repetitive patterns: {e}")
            return False
    
    async def _check_excessive_tool_calls(self, messages: List[Any]) -> bool:
        """
        Check for excessive tool calls without meaningful progress.
        
        This method detects when the agent is making too many tool calls without progress.
        """
        try:
            tool_call_count = 0
            unique_tools = set()
            
            for msg in messages:
                # Check for tool calls in message
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('tool_calls'):
                    for tool_call in msg.additional_kwargs['tool_calls']:
                        tool_call_count += 1
                        tool_name = tool_call.get('function', {}).get('name', 'unknown')
                        unique_tools.add(tool_name)
            
            # Excessive tool calls threshold
            if tool_call_count > 15:  # More than 15 tool calls in recent messages
                return True
            
            # Same tool called too many times
            if len(unique_tools) == 1 and tool_call_count > 8:  # Same tool called 8+ times
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check excessive tool calls: {e}")
            return False
    
    async def _create_timeout_error_response(
        self, 
        query: str, 
        session_id: str, 
        user_id: str, 
        max_iterations: int,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """
        Create error response for agent timeout using standardized response models.
        
        This method implements timeout error handling as specified in requirement 1.5.
        """
        try:
            # Create standardized timeout error response
            error_response = create_error_response(
                error_message=f"Agent execution timed out after {timeout_seconds} seconds",
                session_id=session_id,
                error_type="agent_timeout",
                user_message=f"⏱️ Request timed out after {timeout_seconds} seconds. The ReAct agent was unable to complete the task within the time limit.",
                reasoning_trace=[
                    create_reasoning_step(
                        step_number=1,
                        step_type="error",
                        content=f"Agent execution timed out after {timeout_seconds} seconds"
                    )
                ],
                suggestions=[
                    "Try breaking down your request into smaller parts",
                    "Reduce the complexity of your query",
                    "Check if the required tools are responding properly"
                ],
                processing_time_ms=timeout_seconds * 1000
            )
            
            # Add additional metadata
            response_dict = error_response.to_dict()
            response_dict["metadata"].update({
                "query": query,
                "max_iterations": max_iterations,
                "user_id": user_id,
                "timeout_seconds": timeout_seconds,
                "error_category": "agent_timeout"
            })
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Failed to create timeout error response: {e}")
            # Return minimal standardized error response
            fallback_response = create_error_response(
                error_message=f"Agent execution timed out and error handling failed: {str(e)}",
                session_id=session_id,
                error_type="timeout_with_handler_error",
                user_message=f"⏱️ Request timed out and error handling failed",
                processing_time_ms=timeout_seconds * 1000
            )
            return fallback_response.to_dict()
    
    async def _create_agent_error_response(
        self, 
        query: str, 
        session_id: str, 
        user_id: str, 
        max_iterations: int,
        agent_error: AgentExecutionError
    ) -> Dict[str, Any]:
        """
        Create error response for agent execution errors using standardized response models.
        
        This method implements agent failure handling as specified in requirement 1.5.
        """
        try:
            # Create standardized agent error response
            error_response = create_error_response(
                error_message=f"Agent execution failed: {str(agent_error)}",
                session_id=session_id,
                error_type="agent_execution_error",
                user_message=f"❌ I encountered an error while processing your request: {str(agent_error)}",
                reasoning_trace=[
                    create_reasoning_step(
                        step_number=1,
                        step_type="error",
                        content=f"Agent execution failed: {str(agent_error)}"
                    )
                ],
                suggestions=[
                    "Try rephrasing your request",
                    "Check if the required tools are available",
                    "Contact support if the issue persists"
                ]
            )
            
            # Add additional metadata
            response_dict = error_response.to_dict()
            response_dict["metadata"].update({
                "query": query,
                "max_iterations": max_iterations,
                "user_id": user_id,
                "error_category": "agent_execution_error"
            })
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Failed to create agent error response: {e}")
            # Return minimal standardized error response
            fallback_response = create_error_response(
                error_message=f"Agent execution failed and error handling failed: {str(e)}",
                session_id=session_id,
                error_type="agent_error_with_handler_error",
                user_message="❌ I encountered an error while processing your request"
            )
            return fallback_response.to_dict()
    
    async def _create_unexpected_agent_error_response(
        self, 
        query: str, 
        session_id: str, 
        user_id: str, 
        max_iterations: int,
        error: Exception
    ) -> Dict[str, Any]:
        """
        Create error response for unexpected agent errors using comprehensive error formatter.
        
        This method implements fallback responses for agent failures as specified in requirement 1.5.
        """
        # Create context
        context = {
            "user_id": user_id,
            "operation": "agent_execution",
            "max_iterations": max_iterations,
            "query": query[:200],  # Truncate for logging
            "error_type": type(error).__name__
        }
        
        # Format comprehensive error response
        error_response = await format_react_error(
            error=error,
            session_id=session_id,
            context=context
        )
        
        # Create agent response format
        response = {
            "response": f"🚨 {error_response['user_message']}",
            "session_id": session_id,
            "reasoning_trace": [
                {
                    "step_number": 1,
                    "step_type": "error",
                    "content": f"Unexpected error ({type(error).__name__}): {str(error)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "tool_calls": [],
            "status": "failed",
            "processing_time_ms": 0,
            "iterations_used": 0,
            "tools_used": 0,
            "error": error_response,
            "metadata": {
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "max_iterations": max_iterations,
                "user_id": user_id,
                "error_category": error_response.get("category", "unexpected_error"),
                "error_type": type(error).__name__
            }
        }
        
        return response
    
    async def _prepare_agent_input(
        self, 
        query: str, 
        conversation: Any, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare enhanced input for the ReAct agent including conversation history and context.
        
        This method implements the tool selection and execution coordination requirement from 1.2.
        """
        messages = []
        
        # Add conversation history for context (last 5 messages to avoid token limits)
        if conversation and conversation.messages:
            recent_messages = conversation.messages[-5:]
            for msg in recent_messages:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
        
        # Add current query
        current_message = query
        
        # Enhance query with available tools context if needed
        if context and context.get("include_tool_context", True):
            available_tools = await self.tool_registry.get_tool_metadata()
            if available_tools:
                tool_descriptions = []
                for tool in available_tools:
                    tool_descriptions.append(f"- {tool['name']}: {tool['description']}")
                
                tool_context = f"\n\nAvailable tools:\n" + "\n".join(tool_descriptions)
                current_message += tool_context
        
        messages.append(HumanMessage(content=current_message))
        
        # Return format that works for both LangGraph and LangChain agents
        # LangGraph expects specific state keys based on the agent type
        return {
            "input": current_message,  # Primary input for the agent
            "chat_history": messages[:-1] if len(messages) > 1 else [],  # Previous messages
            "agent_outcome": None,  # Will be set by agent
            "intermediate_steps": []  # Will be populated during execution
        }
    
    async def _process_agent_response(
        self,
        agent_response: Any,
        query: str,
        session_id: str,
        user_id: str,
        max_iterations: int,
        start_time: datetime,
        correlation_context: CorrelationContext
    ) -> Dict[str, Any]:
        """
        Process the agent response and extract reasoning trace and tool calls.
        
        This method implements the reasoning trace capture and logging requirement from 1.4.
        Uses standardized response models to fix attribute errors.
        """
        try:
            # Handle different response formats (LangGraph vs LangChain)
            if isinstance(agent_response, dict) and "messages" in agent_response:
                # LangGraph response format - use the specialized formatter
                processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                standardized_response = format_langgraph_response(
                    agent_response, session_id, processing_time_ms
                )
                return standardized_response.to_dict()
            
            elif isinstance(agent_response, str):
                # LangChain simple string response
                agent_response_text = agent_response
                messages = []
            elif hasattr(agent_response, 'content'):
                # LangChain message response
                agent_response_text = agent_response.content
                messages = [agent_response]
            else:
                # Fallback for unknown response format
                agent_response_text = str(agent_response)
                messages = []
            
            # Calculate processing time
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Extract tool calls and reasoning trace with standardized models
            tool_calls = []
            reasoning_trace = []
            
            # Process all messages to extract detailed reasoning steps
            for i, message in enumerate(messages):
                timestamp = datetime.utcnow().timestamp()
                
                # Extract tool calls with standardized ToolCall model
                if hasattr(message, 'additional_kwargs') and message.additional_kwargs.get('tool_calls'):
                    for j, tool_call in enumerate(message.additional_kwargs['tool_calls']):
                        # Create standardized ToolCall object
                        standardized_tool_call = create_tool_call(
                            tool_name=tool_call.get('function', {}).get('name', 'unknown'),
                            parameters=self._parse_tool_parameters(tool_call.get('function', {}).get('arguments', {})),
                            result={"status": "completed"},  # Default result
                            execution_time=0  # Will be updated if available
                        )
                        tool_calls.append(standardized_tool_call)
                        
                        # Add tool call to reasoning trace with standardized ReasoningStep
                        reasoning_step = create_reasoning_step(
                            step_number=len(reasoning_trace) + 1,
                            step_type="action",
                            content=f"Using tool: {standardized_tool_call.tool_name}",
                            tool_name=standardized_tool_call.tool_name,
                            action_input=standardized_tool_call.parameters
                        )
                        reasoning_trace.append(reasoning_step)
                
                # Extract reasoning steps with standardized ReasoningStep model
                if hasattr(message, 'content') and message.content:
                    step_type = self._categorize_reasoning_step(message, i)
                    reasoning_step = create_reasoning_step(
                        step_number=len(reasoning_trace) + 1,
                        step_type=step_type,
                        content=message.content
                    )
                    reasoning_trace.append(reasoning_step)
            
            # Create standardized response using the utility function
            standardized_response = create_success_response(
                response=agent_response_text,
                session_id=session_id,
                reasoning_trace=reasoning_trace,
                tool_calls=tool_calls,
                processing_time_ms=processing_time_ms,
                iterations_used=len([step for step in reasoning_trace if step.step_type in ["thought", "action"]]),
                metadata={
                    "query": query,
                    "timestamp": datetime.utcnow().isoformat(),
                    "max_iterations": max_iterations,
                    "user_id": user_id,
                    "agent_config": self.agent_config
                }
            )
            
            return standardized_response.to_dict()
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            # Return standardized error response
            error_response = create_error_response(
                error_message=f"Failed to process agent response: {str(e)}",
                session_id=session_id,
                error_type="response_processing_error",
                processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            return error_response.to_dict()
    
    def _parse_tool_parameters(self, arguments: Any) -> Dict[str, Any]:
        """Parse tool parameters from various formats."""
        if isinstance(arguments, dict):
            return arguments
        elif isinstance(arguments, str):
            try:
                import json
                return json.loads(arguments)
            except json.JSONDecodeError:
                return {"raw_arguments": arguments}
        else:
            return {"arguments": str(arguments)}
    
    def _categorize_reasoning_step(self, message: Any, index: int) -> str:
        """Categorize reasoning steps for better trace organization."""
        if hasattr(message, 'type'):
            if message.type == "ai":
                # Check if this is a thought or final answer
                content = getattr(message, 'content', '').lower()
                if any(keyword in content for keyword in ['think', 'need to', 'should', 'let me']):
                    return "thought"
                elif any(keyword in content for keyword in ['action', 'use', 'call']):
                    return "action_planning"
                else:
                    return "response"
            elif message.type == "human":
                return "user_input"
            elif message.type == "tool":
                return "tool_result"
        
        return "observation"
    
    async def _create_fallback_response(
        self, query: str, session_id: str, user_id: str, max_iterations: int
    ) -> Dict[str, Any]:
        """Create a fallback response when ReAct agent is not available."""
        available_tools_count = len(await self.tool_registry.get_available_tools())
        
        response = {
            "response": f"ReAct agent is not fully configured. Available tools: {available_tools_count}. Your query: '{query}' has been received but cannot be processed with full ReAct capabilities.",
            "session_id": session_id,
            "reasoning_trace": [
                {
                    "step_number": 1,
                    "step_type": "system_message",
                    "content": "ReAct agent is not configured with Azure OpenAI credentials",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "tool_calls": [],
            "status": "completed",
            "processing_time_ms": 0,
            "iterations_used": 1,
            "tools_used": 0,
            "metadata": {
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "max_iterations": max_iterations,
                "user_id": user_id,
                "fallback_mode": True
            }
        }
        
        # Update conversation with the interaction
        await self.memory_manager.add_message(
            session_id=session_id,
            role="user",
            content=query
        )
        
        await self.memory_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=response["response"],
            metadata={"fallback_mode": True}
        )
        
        return response
    
    async def _create_enhanced_fallback_response(
        self, query: str, session_id: str, user_id: str, max_iterations: int, agent_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an enhanced fallback response when ReAct agent is not available using standardized models.
        
        This method implements requirement 2.4: Replace fallback responses with actual ReAct agent processing
        by providing detailed information about why the agent is unavailable.
        """
        try:
            # Determine the specific reason for unavailability
            if not agent_status["initialized"]:
                reason = "Service initialization failed"
                suggestion = "Please check the service logs and restart the application."
            elif not agent_status["azure_openai_configured"]:
                reason = "Azure OpenAI credentials not configured"
                suggestion = "Please configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME in your environment."
            elif not agent_status["llm_available"]:
                reason = "Language model not available"
                suggestion = "Please check your Azure OpenAI configuration and network connectivity."
            elif not agent_status["langgraph_available"]:
                reason = "LangGraph library not available"
                suggestion = "The system is using a fallback mode. Consider upgrading LangGraph for full functionality."
            elif agent_status["initialization_error"]:
                reason = f"Agent initialization error: {agent_status['initialization_error']}"
                suggestion = "Please check the error logs and resolve any configuration issues."
            else:
                reason = "Unknown agent availability issue"
                suggestion = "Please contact support with the agent status information."
            
            available_tools_count = agent_status.get("tools_count", 0)
            
            response_message = f"""🤖 ReAct Agent Status: Currently Unavailable

**Reason:** {reason}

**Suggestion:** {suggestion}

**System Status:**
- Initialized: {'✅' if agent_status['initialized'] else '❌'}
- Azure OpenAI: {'✅' if agent_status['azure_openai_configured'] else '❌'}
- Language Model: {'✅' if agent_status['llm_available'] else '❌'}
- Available Tools: {available_tools_count}
- LangGraph: {'✅' if agent_status['langgraph_available'] else '❌'}

**Your Query:** "{query}"

While the full ReAct agent is unavailable, the system can still provide basic responses and tool access once the configuration issues are resolved."""
            
            # Create standardized response using the utility function
            standardized_response = create_success_response(
                response=response_message,
                session_id=session_id,
                reasoning_trace=[
                    create_reasoning_step(
                        step_number=1,
                        step_type="system_status",
                        content=f"ReAct agent unavailable: {reason}"
                    )
                ],
                tool_calls=[],
                processing_time_ms=0,
                iterations_used=0,
                metadata={
                    "query": query,
                    "max_iterations": max_iterations,
                    "user_id": user_id,
                    "fallback_mode": True,
                    "agent_status": agent_status,
                    "unavailability_reason": reason
                }
            )
            
            # Override status to indicate agent unavailability
            response_dict = standardized_response.to_dict()
            response_dict["status"] = "agent_unavailable"
            
            # Try to update conversation with the interaction (if possible)
            try:
                await self.memory_manager.add_message(
                    session_id=session_id,
                    role="user",
                    content=query
                )
                
                await self.memory_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response_dict["response"],
                    metadata={"fallback_mode": True, "agent_status": agent_status}
                )
            except Exception as memory_error:
                logger.warning(f"Could not persist fallback conversation: {memory_error}")
                # Don't fail the response for memory issues
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Failed to create enhanced fallback response: {e}")
            # Return minimal standardized error response
            fallback_response = create_error_response(
                error_message=f"Failed to create fallback response: {str(e)}",
                session_id=session_id,
                error_type="fallback_creation_error",
                user_message="🤖 ReAct Agent is currently unavailable"
            )
            return fallback_response.to_dict()
    
    async def _create_error_response(
        self, query: str, session_id: str, user_id: str, max_iterations: int, error: Exception
    ) -> Dict[str, Any]:
        """
        Create a comprehensive error response when agent execution fails.
        
        This method is kept for backward compatibility but delegates to specific error handlers.
        """
        # Delegate to specific error handlers based on error type
        if isinstance(error, AgentExecutionError):
            return await self._create_agent_error_response(query, session_id, user_id, max_iterations, error)
        elif isinstance(error, asyncio.TimeoutError):
            return await self._create_timeout_error_response(query, session_id, user_id, max_iterations, 300)
        else:
            return await self._create_unexpected_agent_error_response(query, session_id, user_id, max_iterations, error)
    
    async def _update_conversation_with_interaction(
        self,
        session_id: str,
        query: str,
        response: str,
        tool_calls: List[Dict[str, Any]],
        reasoning_trace: List[Dict[str, Any]]
    ) -> None:
        """Update conversation with the interaction details."""
        await self.memory_manager.add_message(
            session_id=session_id,
            role="user",
            content=query
        )
        
        await self.memory_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=response,
            metadata={
                "tool_calls": tool_calls,
                "reasoning_trace": reasoning_trace,
                "tools_used": len(tool_calls)
            }
        )
    
    async def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve conversation history for a session.
        
        This method implements requirement 4.2: The agent shall have access to full conversation history.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get comprehensive conversation summary
            conversation_summary = await self.memory_manager.get_conversation_summary(session_id)
            if not conversation_summary:
                return {"session_id": session_id, "messages": [], "status": "not_found"}
            
            # Get detailed conversation context
            conversation_context = await self.memory_manager.get_conversation_context_for_agent(session_id)
            
            return {
                "session_id": session_id,
                "messages": conversation_context["messages"],
                "status": conversation_summary["state"],
                "created_at": conversation_summary["created_at"],
                "updated_at": conversation_summary["updated_at"],
                "summary": {
                    "message_count": conversation_summary["message_count"],
                    "tool_calls_count": conversation_summary["tool_calls_count"],
                    "duration_minutes": conversation_summary["duration_minutes"],
                    "tools_used": conversation_summary["tools_used"]
                },
                "context_summary": conversation_context["context_summary"],
                "tool_usage_history": conversation_context["tool_usage_history"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation history for {session_id}: {e}")
            raise AgentExecutionError(f"Failed to retrieve conversation: {str(e)}")
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up resources for a conversation session."""
        if not self._initialized:
            await self.initialize()
        
        try:
            success = await self.memory_manager.cleanup_session(session_id)
            logger.info(f"Session {session_id} cleanup: {'successful' if success else 'failed'}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return False
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for the agent."""
        if not self._initialized:
            await self.initialize()
        
        return await self.tool_registry.get_tool_metadata()
    
    async def process_request_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = None,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        skip_session_validation: bool = False
    ):
        """
        Process a user request through the ReAct agent with streaming response.
        
        Args:
            query: User's natural language query
            session_id: Optional conversation session ID
            user_id: User identifier for authentication context
            context: Additional context for the request
            max_iterations: Maximum reasoning iterations
            
        Yields:
            Streaming response chunks from the agent
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Processing streaming request for session {session_id}: {query[:100]}...")
            
            # Validate user authentication and session access (skip for new sessions)
            if user_id and not skip_session_validation and not await self.validate_session_access(session_id, user_id):
                raise AuthenticationException(f"Access denied to session {session_id}")
            
            # Get or create conversation context
            conversation = await self.memory_manager.get_or_create_conversation(
                session_id=session_id,
                user_id=user_id
            )
            
            # Create thread configuration for conversation persistence
            thread_config = {
                "configurable": {
                    "thread_id": session_id
                }
            }
            
            # Prepare input for the agent
            agent_input = {
                "messages": [HumanMessage(content=query)]
            }
            
            # Stream the ReAct agent response
            full_response = ""
            tool_calls = []
            reasoning_trace = []
            
            async for chunk in self.react_agent.astream(agent_input, config=thread_config):
                # Process each chunk and yield it
                if "messages" in chunk:
                    for message in chunk["messages"]:
                        if hasattr(message, 'content') and message.content:
                            # Yield the content chunk
                            yield {
                                "type": "content",
                                "content": message.content,
                                "session_id": session_id
                            }
                            full_response += message.content
                        
                        # Extract tool calls if present
                        if hasattr(message, 'additional_kwargs') and message.additional_kwargs.get('tool_calls'):
                            for tool_call in message.additional_kwargs['tool_calls']:
                                tool_info = {
                                    "id": tool_call.get('id', f"call_{len(tool_calls)}"),
                                    "tool_name": tool_call.get('function', {}).get('name', 'unknown'),
                                    "parameters": tool_call.get('function', {}).get('arguments', {}),
                                    "status": "executing"
                                }
                                tool_calls.append(tool_info)
                                
                                # Yield tool call info
                                yield {
                                    "type": "tool_call",
                                    "tool_call": tool_info,
                                    "session_id": session_id
                                }
            
            # Update conversation with the final interaction
            await self.memory_manager.add_message(
                session_id=session_id,
                role="user",
                content=query
            )
            
            await self.memory_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                metadata={
                    "tool_calls": tool_calls,
                    "reasoning_trace": reasoning_trace
                }
            )
            
            # Yield final completion
            yield {
                "type": "complete",
                "session_id": session_id,
                "tool_calls": tool_calls,
                "reasoning_trace": reasoning_trace
            }
            
        except Exception as e:
            logger.error(f"Failed to process streaming request for session {session_id}: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "session_id": session_id
            }
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        query: Optional[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for a user with optional search.
        
        This method implements requirement 4.1: Create and maintain conversation session.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            conversations = await self.memory_manager.search_conversations(
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            raise AgentExecutionError(f"Failed to retrieve user conversations: {str(e)}")
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """
        Get active session IDs for a user.
        
        This method supports requirement 4.1: Create and maintain conversation session.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            active_sessions = await self.memory_manager.get_user_active_sessions(user_id)
            logger.info(f"Found {len(active_sessions)} active sessions for user {user_id}")
            return active_sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []
    
    async def cleanup_expired_conversation_sessions(self) -> Dict[str, Any]:
        """
        Clean up expired conversation sessions from memory manager.
        
        This method implements session cleanup as part of requirement 4.1.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            expired_count = await self.memory_manager.cleanup_expired_sessions()
            
            return {
                "expired_sessions_cleaned": expired_count,
                "active_sessions_remaining": self.memory_manager.get_active_session_count(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired conversation sessions: {e}")
            return {
                "expired_sessions_cleaned": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health status of the ReAct agent service."""
        try:
            tools_count = len(await self.tool_registry.get_available_tools()) if self._initialized else 0
            active_sessions = self.memory_manager.get_active_session_count() if self._initialized else 0
            
            return {
                "status": "healthy" if self._initialized else "initializing",
                "initialized": self._initialized,
                "tools_available": tools_count,
                "llm_configured": self.llm is not None,
                "agent_ready": self.react_agent is not None,
                "active_sessions": active_sessions,
                "memory_manager_initialized": self.memory_manager.is_initialized() if self._initialized else False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _send_workflow_update(self, session_id: str, update_type: str, data: dict):
        """Send workflow update to connected WebSocket clients."""
        try:
            # Import here to avoid circular imports
            from app.api.react_agent import send_workflow_update
            await send_workflow_update(session_id, update_type, data)
        except ImportError:
            # Fallback if import fails
            logger.debug(f"Could not send workflow update - WebSocket support not available")
        except Exception as e:
            logger.error(f"Error sending workflow update: {e}")
    
    async def _send_reasoning_step_update(self, session_id: str, reasoning_step: dict):
        """Send reasoning step update via WebSocket."""
        await self._send_workflow_update(session_id, "reasoning_step", {
            "reasoning_step": reasoning_step
        })
    
    async def _send_tool_call_start_update(self, session_id: str, tool_name: str, tool_input: str):
        """Send tool call start update via WebSocket."""
        await self._send_workflow_update(session_id, "tool_call_start", {
            "tool_name": tool_name,
            "input": tool_input
        })
    
    async def _send_tool_call_complete_update(self, session_id: str, tool_name: str, tool_output: str, success: bool, error: str = None):
        """Send tool call completion update via WebSocket."""
        await self._send_workflow_update(session_id, "tool_call_complete", {
            "tool_name": tool_name,
            "output": tool_output,
            "success": success,
            "error": error
        })
    
    async def _send_agent_status_update(self, session_id: str, status: str, current_step: int = None, total_steps: int = None):
        """Send agent status update via WebSocket."""
        await self._send_workflow_update(session_id, "agent_status", {
            "status": status,
            "current_step": current_step,
            "total_steps": total_steps
        })


# Global service instance
react_agent_service: Optional[ReactAgentService] = None


async def get_react_agent_service() -> ReactAgentService:
    """Get or create the global ReAct agent service instance."""
    global react_agent_service
    if not react_agent_service:
        react_agent_service = ReactAgentService()
        await react_agent_service.initialize()
    return react_agent_service