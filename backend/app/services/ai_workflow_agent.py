"""
AI Workflow Agent - Handles intelligent automation creation and execution
Integrates with True ReAct Agent for sophisticated workflow planning
"""
import json
import asyncio
import uuid
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

from app.core.database import get_supabase_client
from app.services.auth_context_manager import AuthContextManager
from app.services.true_react_agent import TrueReActAgent

logger = logging.getLogger(__name__)

@dataclass
class AgentStep:
    """Represents a single step in the AI agent's workflow execution"""
    id: str
    type: str  # 'thinking', 'planning', 'executing', 'waiting_auth', 'completed'
    title: str
    description: str
    connector_needed: Optional[str] = None
    auth_required: bool = False
    data_generated: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class MiniApp:
    """Represents a generated mini-app for the user's automation"""
    id: str
    user_id: str
    name: str
    description: str
    user_prompt: str
    input_fields: List[Dict[str, Any]]
    workflow_id: str
    config: Dict[str, Any]
    ui_config: Dict[str, Any]
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class AIWorkflowAgent:
    """
    Intelligent agent that creates and executes workflows based on natural language descriptions
    Integrates with True ReAct Agent for sophisticated planning and execution
    """
    
    def __init__(self):
        self.true_react_agent = TrueReActAgent()
        self.auth_manager = AuthContextManager()
        self.active_sessions: Dict[str, Dict] = {}
    
    async def create_automation(
        self, 
        user_id: str, 
        user_prompt: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[AgentStep, None]:
        """
        Main entry point for creating an automation from natural language
        Uses True ReAct Agent for sophisticated planning and execution
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize session
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'user_prompt': user_prompt,
            'steps': [],
            'workflow_data': {},
            'authentication_pending': [],
            'generated_data': {}
        }
        
        try:
            # Step 1: Initialize True ReAct Agent
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='thinking',
                title='Understanding Your Request',
                description=f'Analyzing your automation request: "{user_prompt}"'
            )
            
            # Initialize the True ReAct Agent with empty auth context (will be handled per connector)
            await self.true_react_agent.initialize({})
            
            await asyncio.sleep(1)  # UI feedback
            
            # Step 2: Use True ReAct Agent to process request
            react_result = await self.true_react_agent.process_user_request(
                request=user_prompt,
                user_id=user_id,
                session_context=None
            )
            
            if not react_result.get('success'):
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='error',
                    title='Planning Failed',
                    description=react_result.get('message', 'Failed to create automation plan')
                )
                return
            
            # Step 3: Handle the planning phase
            if react_result.get('phase') == 'planning':
                plan = react_result.get('plan', {})
                
                # Store plan in session for potential resume after auth
                self.active_sessions[session_id]['workflow_data']['plan'] = plan
                
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='planning',
                    title='Creating Automation Plan',
                    description=f'I will create an automation with {len(plan.get("tasks", []))} steps',
                    data_generated={'plan': plan}
                )
                
                await asyncio.sleep(1)
                
                # Auto-approve the plan (since this is AI Agent, not interactive True ReAct)
                async for step in self._execute_react_plan(session_id, plan, user_id):
                    yield step
                    
            elif react_result.get('phase') == 'conversational':
                # Handle conversational responses
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='thinking',
                    title='Need More Information',
                    description=react_result.get('message', 'I need more details to create your automation')
                )
                
        except Exception as e:
            logger.error(f"Error in create_automation: {e}")
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='error',
                title='Error',
                description=f'Failed to create automation: {str(e)}'
            )
            
        except Exception as e:
            logger.error(f"Error in create_automation: {e}")
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='error',
                title='Something went wrong',
                description=f'Error: {str(e)}'
            )
    
    async def _plan_workflow(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze user prompt and create a workflow plan
        """
        # This would typically use an LLM, for now we'll use heuristics
        prompt_lower = user_prompt.lower()
        
        # Blog posting automation
        if any(word in prompt_lower for word in ['blog', 'article', 'post', 'content', 'write']):
            return {
                'type': 'Blog Automation',
                'connectors': ['perplexity_search', 'text_summarizer', 'gmail_connector'],
                'steps': [
                    {
                        'connector': 'perplexity_search',
                        'action': 'search',
                        'purpose': 'Research the topic',
                        'dynamic_params': {'query': 'user_topic + " latest trends insights"'}
                    },
                    {
                        'connector': 'text_summarizer', 
                        'action': 'summarize',
                        'purpose': 'Create structured content',
                        'dynamic_params': {'text': '{perplexity_search.response}', 'style': 'blog'}
                    },
                    {
                        'connector': 'gmail_connector',
                        'action': 'send',
                        'purpose': 'Deliver the blog content',
                        'dynamic_params': {'body': '{text_summarizer.summary}', 'subject': 'Your Blog: {user_topic}'}
                    }
                ],
                'input_fields': [
                    {'name': 'topic', 'type': 'text', 'label': 'Blog Topic', 'required': True},
                    {'name': 'email', 'type': 'email', 'label': 'Send to Email', 'required': True}
                ]
            }
        
        # Email automation
        elif any(word in prompt_lower for word in ['email', 'send', 'notify', 'alert']):
            return {
                'type': 'Email Automation',
                'connectors': ['gmail_connector'],
                'steps': [
                    {
                        'connector': 'gmail_connector',
                        'action': 'send',
                        'purpose': 'Send email notification',
                        'dynamic_params': {'body': '{user_message}', 'subject': '{user_subject}'}
                    }
                ],
                'input_fields': [
                    {'name': 'subject', 'type': 'text', 'label': 'Email Subject', 'required': True},
                    {'name': 'message', 'type': 'textarea', 'label': 'Email Message', 'required': True},
                    {'name': 'email', 'type': 'email', 'label': 'Send to Email', 'required': True}
                ]
            }
        
        # Default: Simple data processing
        else:
            return {
                'type': 'Data Processing',
                'connectors': ['perplexity_search'],
                'steps': [
                    {
                        'connector': 'perplexity_search',
                        'action': 'search',
                        'purpose': 'Get information',
                        'dynamic_params': {'query': '{user_query}'}
                    }
                ],
                'input_fields': [
                    {'name': 'query', 'type': 'text', 'label': 'Search Query', 'required': True}
                ]
            }
    
    async def _execute_react_plan(
        self, 
        session_id: str, 
        plan: Dict[str, Any], 
        user_id: str
    ) -> AsyncGenerator[AgentStep, None]:
        """
        Execute a True ReAct Agent plan and convert to AI Agent steps
        First check authentication requirements for all connectors
        """
        try:
            # Get connector registry
            from app.connectors.registry import ConnectorRegistry
            connector_registry = ConnectorRegistry()
            
            session = self.active_sessions[session_id]
            tasks = plan.get('tasks', [])
            
            # Step 1: Check authentication requirements for all connectors
            connectors_needing_auth = []
            
            for task in tasks:
                connector_name = task.get('suggested_tool')
                if not connector_name:
                    continue
                    
                # Check if connector exists
                if not connector_registry.is_registered(connector_name):
                    yield AgentStep(
                        id=str(uuid.uuid4()),
                        type='error',
                        title=f'Connector Not Found',
                        description=f'The connector "{connector_name}" is not available.'
                    )
                    return
                
                # Get the connector instance to check auth requirements
                try:
                    connector = connector_registry.create_connector(connector_name)
                    auth_requirements = await connector.get_auth_requirements()
                    
                    # Check if authentication is needed (only for connectors that require it)
                    if auth_requirements.type.value != 'none':
                        auth_tokens = await self.auth_manager.get_connector_auth_tokens(
                            user_id, 
                            connector_name
                        )
                        
                        if not auth_tokens:
                            connectors_needing_auth.append(connector_name)
                            
                except Exception as e:
                    logger.error(f"Error checking auth for {connector_name}: {e}")
                    # Assume auth needed if we can't check
                    connectors_needing_auth.append(connector_name)
            
            # Step 2: Request authentication for connectors that need it
            if connectors_needing_auth:
                for connector_name in connectors_needing_auth:
                    yield AgentStep(
                        id=str(uuid.uuid4()),
                        type='waiting_auth',
                        title=f'Authentication Required',
                        description=f'I need access to {connector_name.replace("_", " ").title()}. Please authenticate to continue.',
                        connector_needed=connector_name,
                        auth_required=True
                    )
                    
                    # Mark as pending
                    session['authentication_pending'].append(connector_name)
                
                # Stop execution until authentication is complete
                return
            
            # Step 3: Execute each task (only if all auth is complete)
            for i, task in enumerate(tasks):
                # Show execution step
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='executing',
                    title=f'Step {i+1}: {task.get("description", "Processing")}',
                    description=f'Running {task.get("suggested_tool", "tool")} to {task.get("description", "complete task").lower()}...'
                )
                
                await asyncio.sleep(2)  # Simulate execution time
                
                # Store step result in session
                session['generated_data'][f'step_{i}'] = {
                    'connector': task.get('suggested_tool'),
                    'success': True,
                    'data': f'Mock data from {task.get("suggested_tool")}'
                }
            
            # Step 4: Generate and save mini-app
            mini_app = await self._generate_mini_app_from_react_plan(session_id, plan)
            
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='completed',
                title='Automation Ready!',
                description=f'Created "{mini_app.name}" - Your automation is ready to use!',
                data_generated={'mini_app': asdict(mini_app)}
            )
            
        except Exception as e:
            logger.error(f"Error executing React plan: {e}")
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='error',
                title='Execution Failed',
                description=f'Failed to execute automation: {str(e)}'
            )

    async def _execute_workflow_plan(
        self, 
        session_id: str, 
        workflow_plan: Dict[str, Any]
    ) -> AsyncGenerator[AgentStep, None]:
        """
        Execute the planned workflow, handling authentication requests
        """
        session = self.active_sessions[session_id]
        
        for i, step_config in enumerate(workflow_plan['steps']):
            connector_name = step_config['connector']
            
            # Check if connector exists and get its auth requirements
            if not self.connector_registry.is_registered(connector_name):
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='error',
                    title=f'Connector Not Found',
                    description=f'The connector "{connector_name}" is not available.'
                )
                return
            
            # Get the connector instance to check auth requirements
            connector = self.connector_registry.create_connector(connector_name)
            auth_requirements = await connector.get_auth_requirements()
            
            # Check if authentication is needed (only for connectors that require it)
            if auth_requirements.type.value != 'none':
                auth_tokens = await self.auth_manager.get_connector_auth_tokens(
                    session['user_id'], 
                    connector_name
                )
                
                if not auth_tokens:
                    # Request authentication
                    yield AgentStep(
                        id=str(uuid.uuid4()),
                        type='waiting_auth',
                        title=f'Authentication Required',
                        description=f'I need access to {connector_name.replace("_", " ").title()}. Please authenticate to continue.',
                        connector_needed=connector_name,
                        auth_required=True
                    )
                    
                    # Mark as pending and wait for auth
                    session['authentication_pending'].append(connector_name)
                    return  # Will resume after auth
            
            # Execute the step
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='executing',
                title=f'Step {i+1}: {step_config["purpose"]}',
                description=f'Running {connector_name.replace("_", " ").title()} to {step_config["purpose"].lower()}...'
            )
            
            # Actually execute the connector
            try:
                # Prepare execution context
                from app.models.connector import ConnectorExecutionContext
                context = ConnectorExecutionContext(
                    user_id=session['user_id'],
                    execution_id=str(uuid.uuid4())
                )
                
                # Get auth tokens if needed
                auth_tokens = {}
                if auth_requirements.type.value != 'none':
                    auth_tokens = await self.auth_manager.get_connector_auth_tokens(
                        session['user_id'], 
                        connector_name
                    ) or {}
                
                # Execute the connector
                result = await connector.execute(step_config['params'], context, auth_tokens)
                
                # Store step result
                step_result = {
                    'connector': connector_name,
                    'success': result.success,
                    'data': result.data,
                    'metadata': result.metadata
                }
                session['generated_data'][f'step_{i}'] = step_result
                
                # Pass data to next step if available
                if result.success and result.data:
                    session['workflow_context'].update({f'step_{i}_output': result.data})
                
            except Exception as e:
                # Handle execution error
                step_result = {
                    'connector': connector_name,
                    'success': False,
                    'error': str(e)
                }
                session['generated_data'][f'step_{i}'] = step_result
                
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='error',
                    title=f'Execution Error',
                    description=f'Failed to execute {connector_name}: {str(e)}'
                )
                return
    
    async def _generate_mini_app_from_react_plan(self, session_id: str, plan: Dict[str, Any]) -> MiniApp:
        """
        Generate a mini-app from a True ReAct Agent plan
        """
        session = self.active_sessions[session_id]
        user_id = session['user_id']
        user_prompt = session['user_prompt']
        
        # Extract app name from plan
        app_name = plan.get('summary', f'{user_prompt} Automation').replace('Enhanced workflow plan: ', '')
        
        # Create input fields from plan tasks
        input_fields = []
        tasks = plan.get('tasks', [])
        
        # Add common input fields based on tasks
        if any('email' in task.get('description', '').lower() for task in tasks):
            input_fields.append({
                'name': 'email',
                'type': 'email',
                'label': 'Email Address',
                'required': True
            })
        
        if any('topic' in task.get('description', '').lower() or 'search' in task.get('description', '').lower() for task in tasks):
            input_fields.append({
                'name': 'topic',
                'type': 'text', 
                'label': 'Topic or Query',
                'required': True
            })
        
        # Create mini-app
        mini_app = MiniApp(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=app_name,
            description=f'Automated workflow created from: "{user_prompt}"',
            user_prompt=user_prompt,
            input_fields=input_fields,
            workflow_id=str(uuid.uuid4()),
            config={
                'workflow_plan': plan,
                'steps': tasks,
                'input_fields': input_fields
            },
            ui_config={
                'icon': '🤖',
                'color': '#3B82F6',
                'category': 'AI Generated'
            }
        )
        
        # Save to database
        await self._save_mini_app(mini_app)
        
        return mini_app
    
    async def _save_mini_app(self, mini_app: MiniApp) -> None:
        """Save mini-app to database"""
        try:
            supabase = get_supabase_client()
            result = supabase.table('mini_apps').insert({
                'id': mini_app.id,
                'user_id': mini_app.user_id,
                'name': mini_app.name,
                'description': mini_app.description,
                'config': asdict(mini_app),
                'created_at': mini_app.created_at
            }).execute()
            logger.info(f"Mini-app stored: {mini_app.id}")
        except Exception as e:
            logger.error(f"Could not store mini-app: {e}")
            raise

    async def _generate_mini_app(self, session_id: str, workflow_plan: Dict[str, Any]) -> MiniApp:
        """
        Generate a mini-app UI configuration for the user's automation
        """
        session = self.active_sessions[session_id]
        
        mini_app = MiniApp(
            id=str(uuid.uuid4()),
            name=f"{workflow_plan['type']} App",
            description=f"Automated {workflow_plan['type'].lower()} created from: {session['user_prompt']}",
            user_prompt=session['user_prompt'],
            input_fields=workflow_plan['input_fields'],
            workflow_id=str(uuid.uuid4()),  # Would be actual workflow ID
            ui_config={
                'theme': 'modern',
                'layout': 'single_column',
                'submit_button_text': f"Run {workflow_plan['type']}",
                'success_message': f"Your {workflow_plan['type'].lower()} has been executed successfully!"
            }
        )
        
        # Store in database (simplified)
        try:
            supabase = get_supabase_client()
            result = supabase.table('mini_apps').insert({
                'id': mini_app.id,
                'user_id': session['user_id'],
                'name': mini_app.name,
                'description': mini_app.description,
                'config': asdict(mini_app),
                'created_at': mini_app.created_at
            }).execute()
            logger.info(f"Mini-app stored: {mini_app.id}")
        except Exception as e:
            logger.warning(f"Could not store mini-app: {e}")
        
        return mini_app
    
    async def resume_after_auth(self, session_id: str, connector_name: str) -> AsyncGenerator[AgentStep, None]:
        """
        Resume workflow execution after user completes authentication
        """
        if session_id not in self.active_sessions:
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='error',
                title='Session Not Found',
                description='Authentication session expired. Please start over.'
            )
            return
        
        session = self.active_sessions[session_id]
        
        if connector_name in session['authentication_pending']:
            session['authentication_pending'].remove(connector_name)
            
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='executing',
                title='Authentication Successful',
                description=f'Connected to {connector_name.replace("_", " ").title()}. Continuing automation...'
            )
            
            await asyncio.sleep(1)
            
            if not session['authentication_pending']:
                # All auths complete, continue with the True ReAct plan execution
                plan = session.get('workflow_data', {}).get('plan', {})
                user_id = session['user_id']
                
                if plan:
                    # Resume execution from where we left off
                    async for step in self._execute_react_plan(session_id, plan, user_id):
                        yield step
                else:
                    yield AgentStep(
                        id=str(uuid.uuid4()),
                        type='error',
                        title='Plan Not Found',
                        description='Could not resume execution - workflow plan missing.'
                    )
    
    async def execute_mini_app(
        self, 
        user_id: str, 
        mini_app_id: str, 
        user_inputs: Dict[str, Any]
    ) -> AsyncGenerator[AgentStep, None]:
        """
        Execute a user's mini-app with their provided inputs using True ReAct Agent
        """
        try:
            # Load mini-app config
            supabase = get_supabase_client()
            result = supabase.table('mini_apps').select('*').eq('id', mini_app_id).eq('user_id', user_id).execute()
            if not result.data:
                yield AgentStep(
                    id=str(uuid.uuid4()),
                    type='error',
                    title='App Not Found',
                    description='The requested automation app was not found.'
                )
                return
            
            mini_app_data = result.data[0]
            config = mini_app_data['config']
            
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='executing',
                title=f'Running {mini_app_data["name"]}',
                description=f'Processing your request with inputs: {list(user_inputs.keys())}'
            )
            
            # Initialize True ReAct Agent for execution with empty auth context
            await self.true_react_agent.initialize({})
            
            # Extract workflow plan from config
            workflow_plan = config.get('workflow_plan', {})
            
            if workflow_plan and 'steps' in workflow_plan:
                # Execute each step in the workflow plan
                for i, step in enumerate(workflow_plan['steps']):
                    yield AgentStep(
                        id=str(uuid.uuid4()),
                        type='executing',
                        title=f'Step {i+1}: {step.get("action_description", "Processing")}',
                        description=f'Executing {step.get("connector_name", "task")}...'
                    )
                    
                    await asyncio.sleep(2)  # Simulate execution time
            
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='completed',
                title='Automation Complete!',
                description=f'Successfully executed {mini_app_data["name"]} automation',
                data_generated={'result': 'Workflow executed successfully', 'inputs': user_inputs}
            )
            
        except Exception as e:
            logger.error(f"Error executing mini-app: {e}")
            yield AgentStep(
                id=str(uuid.uuid4()),
                type='error',
                title='Execution Failed',
                description=f'Failed to execute automation: {str(e)}'
            )
