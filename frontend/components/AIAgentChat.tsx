'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, CheckCircle, AlertCircle, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { createClient } from '@/lib/supabase/client';

interface AgentStep {
  id: string;
  type: 'thinking' | 'planning' | 'executing' | 'waiting_auth' | 'completed' | 'error';
  title: string;
  description: string;
  connector_needed?: string;
  auth_required?: boolean;
  data_generated?: any;
  timestamp: string;
}

interface MiniApp {
  id: string;
  name: string;
  description: string;
  user_prompt: string;
  input_fields: Array<{
    name: string;
    type: string;
    label: string;
    required: boolean;
  }>;
  workflow_id: string;
  created_at: string;
  ui_config: {
    theme: string;
    layout: string;
    submit_button_text: string;
    success_message: string;
  };
}

interface ChatMessage {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: string;
  step?: AgentStep;
  miniApp?: MiniApp;
}

export default function AIAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'agent',
      content: "👋 Hi! I'm your AI automation assistant. Tell me what you'd like to automate and I'll create a smart app for you!\n\nFor example:\n• \"Create a blog posting system\"\n• \"Set up email notifications\"\n• \"Build a content research tool\"",
      timestamp: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const supabase = createClient();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getStepIcon = (step: AgentStep) => {
    switch (step.type) {
      case 'thinking':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'planning':
        return <Bot className="w-4 h-4 text-purple-500" />;
      case 'executing':
        return <Loader2 className="w-4 h-4 animate-spin text-green-500" />;
      case 'waiting_auth':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Bot className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStepColor = (type: string) => {
    switch (type) {
      case 'thinking': return 'bg-blue-50 border-blue-200';
      case 'planning': return 'bg-purple-50 border-purple-200';
      case 'executing': return 'bg-green-50 border-green-200';
      case 'waiting_auth': return 'bg-yellow-50 border-yellow-200';
      case 'completed': return 'bg-green-50 border-green-200';
      case 'error': return 'bg-red-50 border-red-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  const handleAuthRedirect = (connectorName: string) => {
    // Redirect to authentication page
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    window.open(`/auth/connector/${connectorName}`, '_blank');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('No authentication session found');
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/ai-agent/create-automation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          prompt: input,
          session_id: currentSessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const step: AgentStep = JSON.parse(line.slice(6));
              
              // Create agent message for this step
              const agentMessage: ChatMessage = {
                id: step.id,
                type: 'agent',
                content: step.description,
                timestamp: step.timestamp,
                step: step
              };

              // If this is a mini-app completion, extract the mini-app data
              if (step.type === 'completed' && step.data_generated?.mini_app) {
                agentMessage.miniApp = step.data_generated.mini_app;
              }

              setMessages(prev => [...prev, agentMessage]);

              // If authentication is required, we can handle it here
              if (step.auth_required && step.connector_needed) {
                setCurrentSessionId(step.id);
              }

            } catch (e) {
              console.error('Error parsing step:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('Error creating automation:', error);
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'agent',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
        step: {
          id: 'error',
          type: 'error',
          title: 'Error',
          description: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString()
        }
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMiniApp = (miniApp: MiniApp) => (
    <Card className="mt-4 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-purple-900">{miniApp.name}</h3>
            <p className="text-sm text-purple-700">{miniApp.description}</p>
          </div>
          <Badge variant="secondary" className="bg-purple-100 text-purple-800">
            Ready to Use
          </Badge>
        </div>
        
        <div className="space-y-3">
          {miniApp.input_fields.map((field, idx) => (
            <div key={idx}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label} {field.required && <span className="text-red-500">*</span>}
              </label>
              {field.type === 'textarea' ? (
                <textarea 
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder={`Enter ${field.label.toLowerCase()}`}
                />
              ) : (
                <Input 
                  type={field.type}
                  placeholder={`Enter ${field.label.toLowerCase()}`}
                  className="focus:ring-2 focus:ring-purple-500"
                />
              )}
            </div>
          ))}
          
          <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white">
            <Play className="w-4 h-4 mr-2" />
            {miniApp.ui_config.submit_button_text}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">AI Automation Assistant</h1>
            <p className="text-sm text-gray-500">Tell me what you want to automate</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-3xl ${message.type === 'user' ? 'order-2' : 'order-1'}`}>
              <div className="flex items-start space-x-3">
                {message.type === 'agent' && (
                  <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                
                <div className="flex-1">
                  <div
                    className={`p-4 rounded-lg ${
                      message.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : message.step
                        ? `${getStepColor(message.step.type)} border`
                        : 'bg-white border border-gray-200'
                    }`}
                  >
                    {message.step && (
                      <div className="flex items-center space-x-2 mb-2">
                        {getStepIcon(message.step)}
                        <span className="text-sm font-medium">{message.step.title}</span>
                      </div>
                    )}
                    
                    <div className="whitespace-pre-wrap text-sm">
                      {message.content}
                    </div>

                    {message.step?.auth_required && message.step.connector_needed && (
                      <Button
                        onClick={() => handleAuthRedirect(message.step!.connector_needed!)}
                        className="mt-3 bg-yellow-600 hover:bg-yellow-700 text-white"
                        size="sm"
                      >
                        Authenticate {message.step.connector_needed.replace('_', ' ')}
                      </Button>
                    )}
                  </div>

                  {message.miniApp && renderMiniApp(message.miniApp)}
                </div>
                
                {message.type === 'user' && (
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              </div>
              <div className="bg-gray-100 border border-gray-200 p-4 rounded-lg">
                <div className="text-sm text-gray-600">AI is thinking...</div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe the automation you want to create..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
