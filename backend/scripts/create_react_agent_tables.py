"""
Create database tables for ReAct agent conversations.
"""
import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_supabase_client
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_react_agent_tables():
    """Create tables for ReAct agent conversation management."""
    try:
        client = get_supabase_client()
        
        # Create react_conversations table
        conversations_sql = """
        CREATE TABLE IF NOT EXISTS react_conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(255) UNIQUE NOT NULL,
            user_id UUID NOT NULL,
            state VARCHAR(50) DEFAULT 'initial',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        );
        
        -- Create index on session_id for fast lookups
        CREATE INDEX IF NOT EXISTS idx_react_conversations_session_id 
        ON react_conversations(session_id);
        
        -- Create index on user_id for user-specific queries
        CREATE INDEX IF NOT EXISTS idx_react_conversations_user_id 
        ON react_conversations(user_id);
        
        -- Create index on updated_at for cleanup queries
        CREATE INDEX IF NOT EXISTS idx_react_conversations_updated_at 
        ON react_conversations(updated_at);
        """
        
        # Create react_conversation_messages table
        messages_sql = """
        CREATE TABLE IF NOT EXISTS react_conversation_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES react_conversations(id) ON DELETE CASCADE,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'tool'
            content TEXT NOT NULL,
            tool_calls JSONB DEFAULT '[]'::jsonb,
            reasoning_step JSONB DEFAULT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        );
        
        -- Create index on conversation_id for fast message retrieval
        CREATE INDEX IF NOT EXISTS idx_react_messages_conversation_id 
        ON react_conversation_messages(conversation_id);
        
        -- Create index on session_id for direct session queries
        CREATE INDEX IF NOT EXISTS idx_react_messages_session_id 
        ON react_conversation_messages(session_id);
        
        -- Create index on timestamp for chronological ordering
        CREATE INDEX IF NOT EXISTS idx_react_messages_timestamp 
        ON react_conversation_messages(timestamp);
        """
        
        # Create react_tool_executions table for detailed tool tracking
        tool_executions_sql = """
        CREATE TABLE IF NOT EXISTS react_tool_executions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES react_conversations(id) ON DELETE CASCADE,
            message_id UUID REFERENCES react_conversation_messages(id) ON DELETE CASCADE,
            tool_name VARCHAR(255) NOT NULL,
            parameters JSONB NOT NULL,
            result JSONB DEFAULT NULL,
            error_message TEXT DEFAULT NULL,
            execution_time_ms INTEGER DEFAULT NULL,
            status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'completed', 'failed'
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        );
        
        -- Create index on conversation_id for tool usage analysis
        CREATE INDEX IF NOT EXISTS idx_react_tool_executions_conversation_id 
        ON react_tool_executions(conversation_id);
        
        -- Create index on tool_name for tool usage statistics
        CREATE INDEX IF NOT EXISTS idx_react_tool_executions_tool_name 
        ON react_tool_executions(tool_name);
        
        -- Create index on status for monitoring
        CREATE INDEX IF NOT EXISTS idx_react_tool_executions_status 
        ON react_tool_executions(status);
        """
        
        # Create react_reasoning_traces table for detailed reasoning tracking
        reasoning_traces_sql = """
        CREATE TABLE IF NOT EXISTS react_reasoning_traces (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES react_conversations(id) ON DELETE CASCADE,
            message_id UUID REFERENCES react_conversation_messages(id) ON DELETE CASCADE,
            step_number INTEGER NOT NULL,
            thought TEXT DEFAULT NULL,
            action VARCHAR(255) DEFAULT NULL,
            action_input JSONB DEFAULT NULL,
            observation TEXT DEFAULT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create index on conversation_id for trace retrieval
        CREATE INDEX IF NOT EXISTS idx_react_reasoning_traces_conversation_id 
        ON react_reasoning_traces(conversation_id);
        
        -- Create index on message_id for message-specific traces
        CREATE INDEX IF NOT EXISTS idx_react_reasoning_traces_message_id 
        ON react_reasoning_traces(message_id);
        
        -- Create index on step_number for ordering
        CREATE INDEX IF NOT EXISTS idx_react_reasoning_traces_step_number 
        ON react_reasoning_traces(step_number);
        """
        
        # Execute table creation
        logger.info("Creating react_conversations table...")
        client.rpc('exec_sql', {'sql': conversations_sql}).execute()
        
        logger.info("Creating react_conversation_messages table...")
        client.rpc('exec_sql', {'sql': messages_sql}).execute()
        
        logger.info("Creating react_tool_executions table...")
        client.rpc('exec_sql', {'sql': tool_executions_sql}).execute()
        
        logger.info("Creating react_reasoning_traces table...")
        client.rpc('exec_sql', {'sql': reasoning_traces_sql}).execute()
        
        # Create RLS policies for security
        await create_rls_policies(client)
        
        logger.info("ReAct agent database tables created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create ReAct agent tables: {e}")
        raise


async def create_rls_policies(client):
    """Create Row Level Security policies for ReAct agent tables."""
    try:
        logger.info("Creating RLS policies for ReAct agent tables...")
        
        # Enable RLS on all tables
        rls_enable_sql = """
        ALTER TABLE react_conversations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE react_conversation_messages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE react_tool_executions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE react_reasoning_traces ENABLE ROW LEVEL SECURITY;
        """
        
        # Create policies for react_conversations
        conversations_policies_sql = """
        -- Users can only access their own conversations
        CREATE POLICY IF NOT EXISTS "Users can access own conversations" 
        ON react_conversations FOR ALL 
        USING (auth.uid() = user_id);
        
        -- Service role can access all conversations
        CREATE POLICY IF NOT EXISTS "Service role can access all conversations" 
        ON react_conversations FOR ALL 
        USING (auth.role() = 'service_role');
        """
        
        # Create policies for react_conversation_messages
        messages_policies_sql = """
        -- Users can access messages from their own conversations
        CREATE POLICY IF NOT EXISTS "Users can access own conversation messages" 
        ON react_conversation_messages FOR ALL 
        USING (
            conversation_id IN (
                SELECT id FROM react_conversations WHERE user_id = auth.uid()
            )
        );
        
        -- Service role can access all messages
        CREATE POLICY IF NOT EXISTS "Service role can access all messages" 
        ON react_conversation_messages FOR ALL 
        USING (auth.role() = 'service_role');
        """
        
        # Create policies for react_tool_executions
        tool_executions_policies_sql = """
        -- Users can access tool executions from their own conversations
        CREATE POLICY IF NOT EXISTS "Users can access own tool executions" 
        ON react_tool_executions FOR ALL 
        USING (
            conversation_id IN (
                SELECT id FROM react_conversations WHERE user_id = auth.uid()
            )
        );
        
        -- Service role can access all tool executions
        CREATE POLICY IF NOT EXISTS "Service role can access all tool executions" 
        ON react_tool_executions FOR ALL 
        USING (auth.role() = 'service_role');
        """
        
        # Create policies for react_reasoning_traces
        reasoning_traces_policies_sql = """
        -- Users can access reasoning traces from their own conversations
        CREATE POLICY IF NOT EXISTS "Users can access own reasoning traces" 
        ON react_reasoning_traces FOR ALL 
        USING (
            conversation_id IN (
                SELECT id FROM react_conversations WHERE user_id = auth.uid()
            )
        );
        
        -- Service role can access all reasoning traces
        CREATE POLICY IF NOT EXISTS "Service role can access all reasoning traces" 
        ON react_reasoning_traces FOR ALL 
        USING (auth.role() = 'service_role');
        """
        
        # Execute RLS setup
        client.rpc('exec_sql', {'sql': rls_enable_sql}).execute()
        client.rpc('exec_sql', {'sql': conversations_policies_sql}).execute()
        client.rpc('exec_sql', {'sql': messages_policies_sql}).execute()
        client.rpc('exec_sql', {'sql': tool_executions_policies_sql}).execute()
        client.rpc('exec_sql', {'sql': reasoning_traces_policies_sql}).execute()
        
        logger.info("RLS policies created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create RLS policies: {e}")
        # Don't raise here as the tables are still functional without RLS
        logger.warning("Continuing without RLS policies...")


if __name__ == "__main__":
    asyncio.run(create_react_agent_tables())