#!/usr/bin/env python3
"""
Interactive manual testing script for PromptFlow AI platform.
This script allows you to manually test the system with your own prompts.
"""
import asyncio
import sys
import json
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.database import init_database
from app.services.rag import RAGRetriever, init_rag_system
from app.services.conversational_agent import ConversationalAgent, init_conversational_agent
from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.connectors.core.register import register_core_connectors
from app.core.logging_config import init_logging
from app.core.config import settings

import logging

# Initialize logging
init_logging()
logger = logging.getLogger(__name__)


class InteractiveTestSession:
    """Interactive testing session for manual verification."""
    
    def __init__(self):
        self.rag_retriever = None
        self.conversational_agent = None
        self.workflow_orchestrator = None
        self.setup_complete = False
    
    async def setup(self):
        """Set up the testing environment."""
        print("🚀 Setting up PromptFlow AI Interactive Test Session...")
        print("="*60)
        
        try:
            # Check environment
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
                return False
            
            if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
                print("❌ Error: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set")
                return False
            
            # Initialize systems
            print("Initializing database...")
            await init_database()
            
            print("Registering connectors...")
            register_core_connectors()
            
            print("Initializing RAG system...")
            await init_rag_system()
            self.rag_retriever = RAGRetriever()
            await self.rag_retriever.initialize()
            
            print("Initializing conversational agent...")
            await init_conversational_agent()
            from app.services.conversational_agent import get_conversational_agent
            self.conversational_agent = await get_conversational_agent()
            
            print("Initializing workflow orchestrator...")
            self.workflow_orchestrator = WorkflowOrchestrator()
            
            print("✅ Setup completed successfully!")
            self.setup_complete = True
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def test_rag_search(self, query: str):
        """Test RAG search with a user query."""
        print(f"\n🔍 RAG Search: '{query}'")
        print("-" * 50)
        
        try:
            connectors = await self.rag_retriever.retrieve_connectors(query, limit=5, similarity_threshold=0.3)
            
            if not connectors:
                print("No relevant connectors found.")
                return
            
            print(f"Found {len(connectors)} relevant connectors:")
            for i, connector in enumerate(connectors[:5], 1):  # Show top 5
                print(f"{i}. {connector.name}")
                print(f"   Category: {connector.category}")
                print(f"   Description: {connector.description[:100]}...")
                print()
            
        except Exception as e:
            print(f"❌ RAG search failed: {e}")
    
    async def test_workflow_planning(self, prompt: str):
        """Test workflow planning with a user prompt."""
        print(f"\n🤖 Workflow Planning: '{prompt}'")
        print("-" * 50)
        
        try:
            conversation_context, response = await self.conversational_agent.process_initial_prompt(prompt, user_id="test_user")
            
            if not conversation_context:
                print("No conversation context generated.")
                return
            
            print("Generated Response:")
            print(f"Response: {response}")
            print(f"Conversation State: {conversation_context.state}")
            print(f"Messages: {len(conversation_context.messages)}")
            print()
            
            # If there's a current plan, show it
            if hasattr(conversation_context, 'current_plan') and conversation_context.current_plan:
                plan = conversation_context.current_plan
                print("Current Workflow Plan:")
                print(f"Name: {plan.get('name', 'Untitled Workflow')}")
                print(f"Description: {plan.get('description', 'No description')}")
                print(f"Nodes: {len(plan.get('nodes', []))}")
                print(f"Edges: {len(plan.get('edges', []))}")
                print()
                
                # Test workflow validation with a simple workflow structure
                test_workflow = {
                    "name": "Test Workflow",
                    "steps": [{"id": "step1", "connector_id": "webhook"}]
                }
                validation_result = await self.workflow_orchestrator.validate_workflow(test_workflow)
                print(f"Workflow Validation: {'✅ Valid' if validation_result['valid'] else '❌ Invalid'}")
                if not validation_result['valid']:
                    print(f"Validation Errors: {validation_result['errors']}")
            else:
                print("No workflow plan generated yet - agent is in planning phase.")
            
        except Exception as e:
            print(f"❌ Workflow planning failed: {e}")
    
    async def test_complete_flow(self, user_input: str):
        """Test the complete flow from user input to workflow."""
        print(f"\n🔄 Complete Flow Test: '{user_input}'")
        print("=" * 60)
        
        # Step 1: RAG Search
        await self.test_rag_search(user_input)
        
        # Step 2: Workflow Planning
        await self.test_workflow_planning(user_input)
    
    def print_menu(self):
        """Print the interactive menu."""
        print("\n" + "="*60)
        print("PromptFlow AI Interactive Test Menu")
        print("="*60)
        print("1. Test RAG Search")
        print("2. Test Workflow Planning")
        print("3. Test Complete Flow")
        print("4. Run Predefined Tests")
        print("5. Exit")
        print("-"*60)
    
    async def run_predefined_tests(self):
        """Run a set of predefined tests."""
        print("\n🧪 Running Predefined Tests...")
        print("="*60)
        
        test_cases = [
            "Send an email using Gmail when a webhook receives data",
            "Read data from Google Sheets and send it to an HTTP API",
            "Create a notification system using webhooks and email",
            "Automate data processing between Google Sheets and external APIs",
            "Set up a workflow that monitors webhooks and updates spreadsheets"
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest Case {i}/{len(test_cases)}:")
            await self.test_complete_flow(test_case)
            
            if i < len(test_cases):
                input("\nPress Enter to continue to next test case...")
    
    async def run_interactive_session(self):
        """Run the interactive testing session."""
        if not self.setup_complete:
            print("❌ Setup not completed. Cannot run interactive session.")
            return
        
        print("\n🎉 Welcome to PromptFlow AI Interactive Testing!")
        print("You can now test the system with your own prompts and queries.")
        
        while True:
            self.print_menu()
            
            try:
                choice = input("Enter your choice (1-5): ").strip()
                
                if choice == '1':
                    query = input("\nEnter your RAG search query: ").strip()
                    if query:
                        await self.test_rag_search(query)
                    else:
                        print("Empty query. Please try again.")
                
                elif choice == '2':
                    prompt = input("\nEnter your workflow planning prompt: ").strip()
                    if prompt:
                        await self.test_workflow_planning(prompt)
                    else:
                        print("Empty prompt. Please try again.")
                
                elif choice == '3':
                    user_input = input("\nEnter your complete flow test input: ").strip()
                    if user_input:
                        await self.test_complete_flow(user_input)
                    else:
                        print("Empty input. Please try again.")
                
                elif choice == '4':
                    await self.run_predefined_tests()
                
                elif choice == '5':
                    print("\n👋 Goodbye! Thanks for testing PromptFlow AI!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-5.")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thanks for testing PromptFlow AI!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main function for interactive testing."""
    session = InteractiveTestSession()
    
    # Setup
    if not await session.setup():
        return 1
    
    # Run interactive session
    await session.run_interactive_session()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)