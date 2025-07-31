"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Send, 
  User, 
  Bot, 
  Settings,
  Activity,
  MessageSquare,
  Loader2,
  AlertCircle,
  CheckCircle,
  Brain
} from 'lucide-react';

// Import our new components
import { ReactAgentWorkflowVisualization } from './ReactAgentWorkflowVisualization';
import { ConnectorConfigModal } from './ConnectorConfigModal';
import { useAuth } from '@/lib/auth-context';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  metadata?: {
    reasoning_trace?: Array<{
      step_number: number;
      thought: string;
      action: string;
      action_input: any;
      observation: string;
    }>;
    tool_calls?: Array<{
      tool_name: string;
      input: string;
      output: string;
    }>;
    execution_time?: number;
  };
}

interface ConversationHistory {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

interface ChatInterfaceProps {
  mode: 'react' | 'conversational';
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ mode }) => {
  const { session, user, loading } = useAuth();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState<ConversationHistory[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [selectedConnector, setSelectedConnector] = useState<string | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load conversations on mount when authenticated
  useEffect(() => {
    if (session?.access_token) {
      loadConversations();
    }
  }, [mode, session]);

  const loadConversations = async () => {
    try {
      if (!session?.access_token) return;
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = mode === 'react' ? `${baseUrl}/api/v1/react/conversations` : `${baseUrl}/api/v1/agent/conversations`;
      
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const createNewConversation = () => {
    setMessages([]);
    setCurrentSessionId(null);
  };

  const loadConversation = async (conversationId: string) => {
    try {
      if (!session?.access_token) return;
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = mode === 'react' 
        ? `${baseUrl}/api/v1/react/conversations/${conversationId}`
        : `${baseUrl}/api/v1/agent/conversations/${conversationId}`;
      
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
        setCurrentSessionId(conversationId);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      if (!session?.access_token) throw new Error('No authentication token');
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = mode === 'react' ? `${baseUrl}/api/v1/react/chat` : `${baseUrl}/api/v1/agent/chat-agent`;
      
      const requestBody = mode === 'react' 
        ? {
            query: input,
            session_id: currentSessionId,
            max_iterations: 10,
          }
        : {
            message: input,
            session_id: currentSessionId,
          };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response || data.message || 'No response received',
        role: 'assistant',
        timestamp: new Date().toISOString(),
        metadata: {
          reasoning_trace: data.reasoning_trace,
          tool_calls: data.tool_calls,
          execution_time: data.execution_time_ms,
        },
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Update session ID if this was a new conversation
      if (!currentSessionId && data.session_id) {
        setCurrentSessionId(data.session_id);
        loadConversations(); // Refresh conversation list
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        role: 'assistant',
        timestamp: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleConnectorConfigure = (connectorName: string) => {
    setSelectedConnector(connectorName);
    setIsConfigModalOpen(true);
  };

  const handleConnectorSave = async (config: any) => {
    try {
      if (!session?.access_token) throw new Error('No authentication token');
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/connectors/${config.name}/configure`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error('Failed to save connector configuration');
      }

      // Configuration saved successfully
      console.log('Connector configuration saved');
    } catch (error) {
      console.error('Failed to save connector configuration:', error);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  // Show loading state while authentication is being checked
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth required message if not authenticated
  if (!session || !user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-yellow-500 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">Please sign in to access the chat interface</p>
          <Button onClick={() => window.location.href = '/auth'}>
            Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar - Conversations */}
      <div className="w-80 border-r bg-gray-50 flex flex-col">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">
              {mode === 'react' ? 'ReAct Agent' : 'Conversational AI'}
            </h2>
            <Badge variant={mode === 'react' ? 'default' : 'secondary'}>
              {mode === 'react' ? 'ReAct' : 'Chat'}
            </Badge>
          </div>
          
          <Button onClick={createNewConversation} className="w-full">
            New Conversation
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-4 space-y-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() => loadConversation(conversation.id)}
                className={`
                  p-3 rounded-lg cursor-pointer transition-colors
                  ${currentSessionId === conversation.id 
                    ? 'bg-blue-100 border border-blue-200' 
                    : 'bg-white hover:bg-gray-100 border border-gray-200'
                  }
                `}
              >
                <div className="font-medium text-sm text-gray-900 truncate">
                  {conversation.title}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {conversation.message_count} messages • {formatTimestamp(conversation.updated_at)}
                </div>
              </div>
            ))}
            
            {conversations.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No conversations yet</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <div className="border-b">
            <TabsList className="w-full justify-start h-auto p-0 bg-transparent">
              <TabsTrigger 
                value="chat" 
                className="flex items-center gap-2 px-4 py-3 data-[state=active]:bg-blue-50 data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
              >
                <MessageSquare className="h-4 w-4" />
                Chat
              </TabsTrigger>
              
              {mode === 'react' && (
                <TabsTrigger 
                  value="workflow" 
                  className="flex items-center gap-2 px-4 py-3 data-[state=active]:bg-blue-50 data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
                >
                  <Activity className="h-4 w-4" />
                  Workflow
                </TabsTrigger>
              )}
            </TabsList>
          </div>

          <TabsContent value="chat" className="flex-1 flex flex-col m-0 p-0">
            {/* Messages Area */}
            <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
              <div className="space-y-4 max-w-4xl mx-auto">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`
                        max-w-[80%] rounded-lg px-4 py-3 space-y-2
                        ${message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900 border'
                        }
                      `}
                    >
                      <div className="flex items-start gap-2">
                        {message.role === 'user' ? (
                          <User className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        ) : (
                          <Bot className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        )}
                        
                        <div className="flex-1 min-w-0">
                          <div className="whitespace-pre-wrap break-words">
                            {message.content}
                          </div>
                          
                          {/* Metadata for assistant messages */}
                          {message.role === 'assistant' && message.metadata && (
                            <div className="mt-3 space-y-2">
                              {message.metadata.execution_time && (
                                <div className="text-xs opacity-75">
                                  Execution time: {(message.metadata.execution_time / 1000).toFixed(2)}s
                                </div>
                              )}
                              
                              {message.metadata.tool_calls && message.metadata.tool_calls.length > 0 && (
                                <div className="space-y-1">
                                  <div className="text-xs font-medium opacity-75">Tools used:</div>
                                  {message.metadata.tool_calls.map((tool, index) => (
                                    <Badge key={index} variant="outline" className="text-xs">
                                      {tool.tool_name}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="text-xs opacity-60">
                        {formatTimestamp(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}
                
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-3 border">
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-sm text-gray-600">
                          {mode === 'react' ? 'Agent is thinking...' : 'Generating response...'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="border-t p-4">
              <div className="max-w-4xl mx-auto">
                <div className="flex gap-2">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={
                      mode === 'react' 
                        ? "Ask the ReAct agent to help you with workflows..." 
                        : "Type your message..."
                    }
                    className="flex-1 min-h-[60px] max-h-[120px] resize-none"
                    disabled={isLoading}
                  />
                  <Button
                    onClick={sendMessage}
                    disabled={!input.trim() || isLoading}
                    size="lg"
                    className="px-6"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                {mode === 'react' && (
                  <div className="text-xs text-gray-500 mt-2">
                    The ReAct agent can plan and execute multi-step workflows using available connectors.
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {mode === 'react' && (
            <TabsContent value="workflow" className="flex-1 m-0 p-4">
              <div className="max-w-6xl mx-auto">
                <ReactAgentWorkflowVisualization
                  sessionId={currentSessionId || ''}
                  isActive={currentSessionId !== null}
                  onConfigureConnector={handleConnectorConfigure}
                />
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>

      {/* Connector Configuration Modal */}
      <ConnectorConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => {
          setIsConfigModalOpen(false);
          setSelectedConnector(null);
        }}
        connectorName={selectedConnector}
        onSave={handleConnectorSave}
      />
    </div>
  );
};