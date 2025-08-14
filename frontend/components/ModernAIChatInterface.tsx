'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { createClient } from '@supabase/supabase-js';
import {
  Send, User, Bot, Loader2, Copy, ThumbsUp, ThumbsDown,
  Sparkles, Brain, Code, Play, Settings, Eye, RefreshCw,
  MessageSquare, Zap, CheckCircle, AlertCircle, Clock
} from 'lucide-react';
import { workflowReactAPI } from '@/lib/api';

interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  metadata?: {
    reasoning_trace?: string[];
    workflow?: any;
    ui_updates?: any[];
    execution_time?: number;
    session_id?: string;
  };
}

interface ReasoningStep {
  id: string;
  type: 'thought' | 'action' | 'observation' | 'result';
  content: string;
  timestamp: Date;
  status: 'active' | 'completed' | 'failed';
}

export default function ModernAIChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [showReasoning, setShowReasoning] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Use shared Supabase client
  const supabase = React.useMemo(() => createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  ), []);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  // Add reasoning step
  const addReasoningStep = (
    type: ReasoningStep['type'],
    content: string,
    status: 'active' | 'completed' | 'failed' = 'active'
  ) => {
    const step: ReasoningStep = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      content,
      timestamp: new Date(),
      status,
    };
    setReasoningSteps(prev => [...prev, step]);
  };

  // Process UI updates from the agent
  const processUIUpdates = (updates: any[]) => {
    updates.forEach(update => {
      const { type, message, reasoning } = update.update;

      switch (type) {
        case 'session_started':
          addReasoningStep('thought', 'Starting analysis...', 'completed');
          break;
        case 'reasoning_update':
          addReasoningStep('thought', reasoning || message || 'Thinking...', 'active');
          break;
        case 'connector_highlight':
          addReasoningStep('action', message || 'Working on connector...', 'active');
          break;
        case 'connector_configured':
          addReasoningStep('action', message || 'Connector configured', 'completed');
          break;
        case 'workflow_completed':
          addReasoningStep('result', message || 'Workflow completed!', 'completed');
          break;
        case 'error':
          addReasoningStep('observation', message || 'An error occurred', 'failed');
          break;
      }
    });
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);
    setReasoningSteps([]);

    try {
      // Show initial thinking state
      addReasoningStep('thought', 'Processing your request...', 'active');

      const response = await workflowReactAPI.buildWorkflowConversationally({
        query: currentInput,
        session_id: sessionId || undefined
      });

      setSessionId(response.session_id);

      // Process UI updates for reasoning
      if (response.ui_updates) {
        processUIUpdates(response.ui_updates);
      }

      // Add reasoning trace
      if (response.reasoning_trace) {
        response.reasoning_trace.forEach((reasoning, index) => {
          addReasoningStep('thought', reasoning, 'completed');
        });
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: response.message,
        role: 'assistant',
        timestamp: new Date(),
        metadata: {
          reasoning_trace: response.reasoning_trace,
          workflow: response.workflow,
          ui_updates: response.ui_updates,
          session_id: response.session_id,
        },
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Mark final reasoning step as completed
      setReasoningSteps(prev => prev.map(step => ({ ...step, status: 'completed' as const })));

    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        role: 'assistant',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      addReasoningStep('observation', 'Error occurred', 'failed');
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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getReasoningIcon = (type: ReasoningStep['type']) => {
    switch (type) {
      case 'thought': return <Brain className="w-3 h-3" />;
      case 'action': return <Zap className="w-3 h-3" />;
      case 'observation': return <Eye className="w-3 h-3" />;
      case 'result': return <CheckCircle className="w-3 h-3" />;
      default: return <MessageSquare className="w-3 h-3" />;
    }
  };

  const getStatusColor = (status: ReasoningStep['status']) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'failed': return 'text-red-400';
      case 'active': return 'text-blue-400 animate-pulse';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="h-full bg-slate-950 text-white flex">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Messages */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="max-w-4xl mx-auto p-6 space-y-6">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="w-8 h-8 text-white" />
                  </div>
                  <h2 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                    How can I help you today?
                  </h2>
                  <p className="text-slate-400 mb-6">
                    I can help you create workflows, automate tasks, and build AI-powered solutions.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                    {[
                      "Create a workflow to summarize emails",
                      "Build an automation for data processing",
                      "Set up a notification system",
                      "Generate a report from spreadsheet data"
                    ].map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setInput(suggestion)}
                        className="p-3 text-left bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors text-sm text-slate-300 hover:text-white"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <div key={message.id} className="space-y-4">
                  {/* User Message */}
                  {message.role === 'user' && (
                    <div className="flex justify-end">
                      <div className="max-w-[80%] bg-blue-600 rounded-2xl rounded-br-md px-4 py-3">
                        <div className="flex items-start gap-3">
                          <div className="flex-1">
                            <p className="text-white whitespace-pre-wrap">{message.content}</p>
                          </div>
                          <User className="w-5 h-5 text-blue-100 flex-shrink-0 mt-0.5" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Assistant Message */}
                  {message.role === 'assistant' && (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-md px-4 py-3">
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Bot className="w-4 h-4 text-white" />
                          </div>
                          <div className="flex-1 space-y-3">
                            <p className="text-slate-100 whitespace-pre-wrap leading-relaxed">
                              {message.content}
                            </p>
                            
                            {/* Message Actions */}
                            <div className="flex items-center gap-2 pt-2">
                              <button
                                onClick={() => copyToClipboard(message.content)}
                                className="p-1.5 hover:bg-slate-700 rounded-md transition-colors"
                                title="Copy message"
                              >
                                <Copy className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
                              </button>
                              <button
                                className="p-1.5 hover:bg-slate-700 rounded-md transition-colors"
                                title="Good response"
                              >
                                <ThumbsUp className="w-3.5 h-3.5 text-slate-400 hover:text-green-400" />
                              </button>
                              <button
                                className="p-1.5 hover:bg-slate-700 rounded-md transition-colors"
                                title="Poor response"
                              >
                                <ThumbsDown className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" />
                              </button>
                              <div className="flex-1" />
                              <span className="text-xs text-slate-500">
                                {formatTimestamp(message.timestamp)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Loading State */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Loader2 className="w-4 h-4 text-white animate-spin" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-300">Thinking...</span>
                          <div className="flex gap-1">
                            <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-700 bg-slate-900/50 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto p-4">
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask me anything about workflows, automation, or AI..."
                className="w-full bg-slate-800 border-slate-600 text-white placeholder-slate-400 resize-none pr-12 min-h-[52px] max-h-[120px] rounded-xl"
                disabled={isLoading}
                rows={1}
              />
              <Button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                size="sm"
                className="absolute right-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-3 py-1.5"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
            
            <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <div className="flex items-center gap-2">
                {sessionId && (
                  <Badge variant="outline" className="text-xs border-slate-600 text-slate-400">
                    Session: {sessionId.slice(0, 8)}...
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reasoning Panel (Collapsible) */}
      {(reasoningSteps.length > 0 || isLoading) && (
        <div className={`bg-slate-900 border-l border-slate-700 transition-all duration-300 ${showReasoning ? 'w-80' : 'w-12'}`}>
          <div className="h-full flex flex-col">
            {/* Reasoning Header */}
            <div className="p-3 border-b border-slate-700 flex items-center justify-between">
              {showReasoning ? (
                <>
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-blue-400" />
                    <span className="text-sm font-medium text-slate-200">Agent Reasoning</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowReasoning(false)}
                    className="p-1 h-auto text-slate-400 hover:text-slate-200"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </Button>
                </>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowReasoning(true)}
                  className="p-2 h-auto text-slate-400 hover:text-slate-200 mx-auto"
                  title="Show reasoning"
                >
                  <Brain className="w-4 h-4" />
                </Button>
              )}
            </div>

            {/* Reasoning Steps */}
            {showReasoning && (
              <ScrollArea className="flex-1">
                <div className="p-3 space-y-2">
                  {reasoningSteps.map((step) => (
                    <div key={step.id} className="flex items-start gap-2 p-2 rounded-lg bg-slate-800/50">
                      <div className={`mt-0.5 ${getStatusColor(step.status)}`}>
                        {getReasoningIcon(step.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {step.content}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {formatTimestamp(step.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>
      )}
    </div>
  );
}