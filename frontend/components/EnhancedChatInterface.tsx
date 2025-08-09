"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Send, 
  User, 
  Bot, 
  Brain,
  Code,
  Settings,
  MessageSquare,
  Loader2,
  AlertCircle,
  CheckCircle,
  Pause,
  Play,
  Clock,
  Zap,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronRight,
  Copy,
  Edit3,
  Save,
  X
} from 'lucide-react';

import { useAuth } from '@/lib/auth-context';

// Enhanced message interface with structured reasoning
interface EnhancedMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  status: 'sending' | 'sent' | 'thinking' | 'waiting_for_user' | 'completed' | 'error';
  reasoning?: {
    thought: string;
    action: string;
    observation: string;
    next_step?: string;
  }[];
  tool_calls?: {
    name: string;
    input: any;
    output: any;
    status: 'pending' | 'completed' | 'error';
  }[];
  user_input_required?: {
    type: 'api_key' | 'authentication' | 'parameter' | 'confirmation';
    message: string;
    field_name?: string;
    options?: string[];
  };
  context_preserved?: boolean;
  execution_time?: number;
  streaming?: boolean;
}

interface ConversationContext {
  id: string;
  title: string;
  plan: string;
  current_step: number;
  total_steps: number;
  variables: Record<string, any>;
  connectors_used: string[];
  last_updated: string;
}

interface EnhancedChatInterfaceProps {
  mode: 'react' | 'conversational';
}

export const EnhancedChatInterface: React.FC<EnhancedChatInterfaceProps> = ({ mode }) => {
  const { session, user, loading } = useAuth();
  
  const [messages, setMessages] = useState<EnhancedMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isWaitingForUser, setIsWaitingForUser] = useState(false);
  const [currentContext, setCurrentContext] = useState<ConversationContext | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [showReasoningTrace, setShowReasoningTrace] = useState(true);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll with smooth animation
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ 
      behavior: 'smooth',
      block: 'end'
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-focus input when not waiting for user
  useEffect(() => {
    if (!isWaitingForUser && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isWaitingForUser]);

  // Typing effect for streaming messages
  const [typingText, setTypingText] = useState('');
  const [currentTypingIndex, setCurrentTypingIndex] = useState(0);

  const simulateTyping = useCallback((text: string, messageId: string) => {
    setStreamingMessageId(messageId);
    setCurrentTypingIndex(0);
    setTypingText('');

    const typeNextChar = (index: number) => {
      if (index < text.length) {
        setTypingText(prev => prev + text[index]);
        setCurrentTypingIndex(index + 1);
        setTimeout(() => typeNextChar(index + 1), 30 + Math.random() * 20);
      } else {
        setStreamingMessageId(null);
        // Update the actual message content
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, content: text, streaming: false, status: 'completed' }
            : msg
        ));
      }
    };

    typeNextChar(0);
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: EnhancedMessage = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date().toISOString(),
      status: 'sent',
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      if (!session?.access_token) throw new Error('No authentication token');
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = mode === 'react' ? `${baseUrl}/api/v1/react/enhanced-chat` : `${baseUrl}/api/v1/agent/enhanced-chat`;
      
      const requestBody = {
        message: input,
        context: currentContext,
        preserve_context: true,
        enable_reasoning: true,
        mode: mode,
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

      // Create assistant message with enhanced features
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: EnhancedMessage = {
        id: assistantMessageId,
        content: '',
        role: 'assistant',
        timestamp: new Date().toISOString(),
        status: data.waiting_for_user ? 'waiting_for_user' : 'thinking',
        reasoning: data.reasoning_trace,
        tool_calls: data.tool_calls,
        user_input_required: data.user_input_required,
        context_preserved: true,
        execution_time: data.execution_time_ms,
        streaming: true,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update conversation context
      if (data.context) {
        setCurrentContext(data.context);
      }

      // Handle waiting for user input
      if (data.waiting_for_user) {
        setIsWaitingForUser(true);
      }

      // Start typing animation
      if (data.response) {
        simulateTyping(data.response, assistantMessageId);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      const errorMessage: EnhancedMessage = {
        id: (Date.now() + 1).toString(),
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        role: 'assistant',
        timestamp: new Date().toISOString(),
        status: 'error',
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUserResponse = async (response: string, messageId: string) => {
    // Find the message that was waiting for user input
    const waitingMessage = messages.find(msg => msg.id === messageId);
    if (!waitingMessage) return;

    // Add user response
    const userResponseMessage: EnhancedMessage = {
      id: Date.now().toString(),
      content: response,
      role: 'user',
      timestamp: new Date().toISOString(),
      status: 'sent',
    };

    setMessages(prev => [...prev, userResponseMessage]);
    setIsWaitingForUser(false);

    // Continue execution from where it left off
    try {
      if (!session?.access_token) throw new Error('No authentication token');
      const token = session.access_token;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/react/continue-execution`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_response: response,
          context: currentContext,
          waiting_message_id: messageId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Create continuation message
        const continuationMessageId = (Date.now() + 2).toString();
        const continuationMessage: EnhancedMessage = {
          id: continuationMessageId,
          content: '',
          role: 'assistant',
          timestamp: new Date().toISOString(),
          status: data.waiting_for_user ? 'waiting_for_user' : 'completed',
          reasoning: data.reasoning_trace,
          tool_calls: data.tool_calls,
          user_input_required: data.user_input_required,
          context_preserved: true,
          execution_time: data.execution_time_ms,
          streaming: true,
        };

        setMessages(prev => [...prev, continuationMessage]);

        // Update context
        if (data.context) {
          setCurrentContext(data.context);
        }

        // Handle continued waiting
        if (data.waiting_for_user) {
          setIsWaitingForUser(true);
        }

        // Start typing animation
        if (data.response) {
          simulateTyping(data.response, continuationMessageId);
        }
      }
    } catch (error) {
      console.error('Failed to continue execution:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startEditingMessage = (messageId: string, content: string) => {
    setEditingMessageId(messageId);
    setEditingContent(content);
  };

  const saveEditedMessage = () => {
    if (!editingMessageId) return;
    
    setMessages(prev => prev.map(msg => 
      msg.id === editingMessageId 
        ? { ...msg, content: editingContent }
        : msg
    ));
    
    setEditingMessageId(null);
    setEditingContent('');
  };

  const cancelEditing = () => {
    setEditingMessageId(null);
    setEditingContent('');
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  // Show loading state while authentication is being checked
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <motion.div 
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-400" />
          <p className="text-gray-300">Loading...</p>
        </motion.div>
      </div>
    );
  }

  // Show auth required message if not authenticated
  if (!session || !user) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <motion.div 
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <AlertCircle className="w-8 h-8 text-yellow-400 mx-auto mb-4" />
          <p className="text-gray-300 mb-4">Please sign in to access the enhanced chat interface</p>
          <Button onClick={() => window.location.href = '/auth'} className="bg-blue-600 hover:bg-blue-700">
            Sign In
          </Button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gray-900 text-white">
      {/* Enhanced Sidebar with Context */}
      <motion.div 
        className="w-80 border-r border-gray-700 bg-gray-800 flex flex-col"
        initial={{ x: -320 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Brain className="h-5 w-5 text-blue-400" />
              {mode === 'react' ? 'ReAct Agent' : 'Enhanced AI'}
            </h2>
            <Badge variant={mode === 'react' ? 'default' : 'secondary'} className="bg-blue-600">
              {mode === 'react' ? 'ReAct' : 'Chat'}
            </Badge>
          </div>
          
          <Button 
            onClick={() => {
              setMessages([]);
              setCurrentContext(null);
              setIsWaitingForUser(false);
            }} 
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            New Conversation
          </Button>
        </div>

        {/* Context Panel */}
        {currentContext && (
          <motion.div 
            className="p-4 border-b border-gray-700 bg-gray-750"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
          >
            <h3 className="font-medium text-white mb-2 flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-400" />
              Current Context
            </h3>
            <div className="space-y-2 text-sm">
              <div className="text-gray-300">
                <span className="text-gray-400">Plan:</span> {currentContext.title}
              </div>
              <div className="text-gray-300">
                <span className="text-gray-400">Progress:</span> {currentContext.current_step}/{currentContext.total_steps}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {currentContext.connectors_used.map((connector, index) => (
                  <Badge key={index} variant="outline" className="text-xs border-gray-600 text-gray-300">
                    {connector}
                  </Badge>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Settings */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Show Reasoning</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowReasoningTrace(!showReasoningTrace)}
              className="text-gray-300 hover:text-white"
            >
              {showReasoningTrace ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        <div className="flex-1" />
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area with Enhanced Styling */}
        <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
          <AnimatePresence>
            <div className="space-y-6 max-w-4xl mx-auto">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ 
                    type: "spring", 
                    stiffness: 500, 
                    damping: 30,
                    delay: index * 0.05 
                  }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`
                      max-w-[85%] rounded-2xl px-6 py-4 space-y-3 relative group
                      ${message.role === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-500/25'
                        : message.status === 'waiting_for_user'
                        ? 'bg-gradient-to-r from-yellow-600 to-orange-600 text-white shadow-lg shadow-yellow-500/25 animate-pulse'
                        : message.status === 'error'
                        ? 'bg-gradient-to-r from-red-600 to-red-700 text-white shadow-lg shadow-red-500/25'
                        : 'bg-gray-800 text-gray-100 border border-gray-700 shadow-lg'
                      }
                    `}
                  >
                    {/* Message Header */}
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        {message.role === 'user' ? (
                          <User className="h-5 w-5 mt-0.5" />
                        ) : (
                          <div className="relative">
                            <Bot className="h-5 w-5 mt-0.5" />
                            {message.status === 'thinking' && (
                              <motion.div
                                className="absolute -top-1 -right-1 w-3 h-3 bg-blue-400 rounded-full"
                                animate={{ scale: [1, 1.2, 1] }}
                                transition={{ repeat: Infinity, duration: 1.5 }}
                              />
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        {/* Message Content */}
                        {editingMessageId === message.id ? (
                          <div className="space-y-2">
                            <Textarea
                              value={editingContent}
                              onChange={(e) => setEditingContent(e.target.value)}
                              className="bg-gray-700 border-gray-600 text-white"
                            />
                            <div className="flex gap-2">
                              <Button size="sm" onClick={saveEditedMessage} className="bg-green-600 hover:bg-green-700">
                                <Save className="h-3 w-3 mr-1" />
                                Save
                              </Button>
                              <Button size="sm" variant="outline" onClick={cancelEditing}>
                                <X className="h-3 w-3 mr-1" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap break-words">
                            {message.streaming && streamingMessageId === message.id ? typingText : message.content}
                            {message.streaming && streamingMessageId === message.id && (
                              <motion.span
                                className="inline-block w-2 h-5 bg-current ml-1"
                                animate={{ opacity: [1, 0] }}
                                transition={{ repeat: Infinity, duration: 0.8 }}
                              />
                            )}
                          </div>
                        )}

                        {/* Status Indicators */}
                        {message.status === 'waiting_for_user' && message.user_input_required && (
                          <motion.div 
                            className="mt-4 p-4 bg-black/20 rounded-lg border border-yellow-400/30"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Pause className="h-4 w-4 text-yellow-300" />
                              <span className="font-medium text-yellow-300">Waiting for your input</span>
                            </div>
                            <p className="text-sm mb-3">{message.user_input_required.message}</p>
                            
                            {message.user_input_required.type === 'confirmation' && message.user_input_required.options ? (
                              <div className="flex gap-2">
                                {message.user_input_required.options.map((option, idx) => (
                                  <Button
                                    key={idx}
                                    size="sm"
                                    onClick={() => handleUserResponse(option, message.id)}
                                    className="bg-yellow-600 hover:bg-yellow-700 text-white"
                                  >
                                    {option}
                                  </Button>
                                ))}
                              </div>
                            ) : (
                              <div className="flex gap-2">
                                <input
                                  type="text"
                                  placeholder={`Enter ${message.user_input_required.field_name || 'value'}...`}
                                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') {
                                      handleUserResponse((e.target as HTMLInputElement).value, message.id);
                                    }
                                  }}
                                />
                                <Button
                                  size="sm"
                                  onClick={() => {
                                    const input = document.querySelector('input[type="text"]') as HTMLInputElement;
                                    if (input) handleUserResponse(input.value, message.id);
                                  }}
                                  className="bg-yellow-600 hover:bg-yellow-700"
                                >
                                  <Send className="h-3 w-3" />
                                </Button>
                              </div>
                            )}
                          </motion.div>
                        )}

                        {/* Reasoning Trace */}
                        {showReasoningTrace && message.reasoning && message.reasoning.length > 0 && (
                          <motion.div 
                            className="mt-4 space-y-2"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="text-xs font-medium opacity-75 flex items-center gap-1">
                              <Brain className="h-3 w-3" />
                              Reasoning Trace
                            </div>
                            {message.reasoning.map((step, idx) => (
                              <div key={idx} className="text-xs bg-black/20 rounded p-2 space-y-1">
                                <div><span className="opacity-60">Thought:</span> {step.thought}</div>
                                <div><span className="opacity-60">Action:</span> {step.action}</div>
                                {step.observation && (
                                  <div><span className="opacity-60">Observation:</span> {step.observation}</div>
                                )}
                              </div>
                            ))}
                          </motion.div>
                        )}

                        {/* Tool Calls */}
                        {message.tool_calls && message.tool_calls.length > 0 && (
                          <motion.div 
                            className="mt-3 space-y-2"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="text-xs font-medium opacity-75">Tools Used:</div>
                            <div className="flex flex-wrap gap-1">
                              {message.tool_calls.map((tool, idx) => (
                                <Badge 
                                  key={idx} 
                                  variant="outline" 
                                  className={`text-xs ${
                                    tool.status === 'completed' ? 'border-green-500 text-green-400' :
                                    tool.status === 'error' ? 'border-red-500 text-red-400' :
                                    'border-yellow-500 text-yellow-400'
                                  }`}
                                >
                                  {tool.name}
                                  {tool.status === 'pending' && <Loader2 className="h-2 w-2 ml-1 animate-spin" />}
                                  {tool.status === 'completed' && <CheckCircle className="h-2 w-2 ml-1" />}
                                  {tool.status === 'error' && <AlertCircle className="h-2 w-2 ml-1" />}
                                </Badge>
                              ))}
                            </div>
                          </motion.div>
                        )}

                        {/* Metadata */}
                        <div className="flex items-center justify-between mt-3 text-xs opacity-60">
                          <span>{formatTimestamp(message.timestamp)}</span>
                          {message.execution_time && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {(message.execution_time / 1000).toFixed(2)}s
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Message Actions */}
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => copyToClipboard(message.content)}
                          className="h-6 w-6 p-0 hover:bg-white/10"
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                        {message.role === 'user' && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => startEditingMessage(message.id, message.content)}
                            className="h-6 w-6 p-0 hover:bg-white/10"
                          >
                            <Edit3 className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
              
              {/* Thinking Animation */}
              {isLoading && (
                <motion.div 
                  className="flex justify-start"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="bg-gray-800 rounded-2xl px-6 py-4 border border-gray-700 shadow-lg">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <Bot className="h-5 w-5" />
                        <motion.div
                          className="absolute -top-1 -right-1 w-3 h-3 bg-blue-400 rounded-full"
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ repeat: Infinity, duration: 1.5 }}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <motion.div
                          className="flex gap-1"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                        >
                          {[0, 1, 2].map((i) => (
                            <motion.div
                              key={i}
                              className="w-2 h-2 bg-blue-400 rounded-full"
                              animate={{ y: [0, -8, 0] }}
                              transition={{
                                repeat: Infinity,
                                duration: 1.5,
                                delay: i * 0.2,
                              }}
                            />
                          ))}
                        </motion.div>
                        <span className="text-sm text-gray-400 ml-2">
                          {mode === 'react' ? 'Agent is reasoning...' : 'Thinking...'}
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </AnimatePresence>
        </ScrollArea>

        {/* Enhanced Input Area */}
        <motion.div 
          className="border-t border-gray-700 p-4 bg-gray-800/50 backdrop-blur-sm"
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <div className="max-w-4xl mx-auto">
            {/* Waiting Overlay */}
            <AnimatePresence>
              {isWaitingForUser && (
                <motion.div
                  className="absolute inset-0 bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <div className="text-center">
                    <motion.div
                      className="w-12 h-12 border-4 border-yellow-400 border-t-transparent rounded-full mx-auto mb-4"
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1 }}
                    />
                    <p className="text-yellow-400 font-medium">Waiting for your response...</p>
                    <p className="text-gray-400 text-sm mt-1">The AI has paused execution</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="relative">
              <div className="flex gap-3">
                <Textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={
                    mode === 'react' 
                      ? "Describe what you want to accomplish, and I'll plan and execute it step by step..." 
                      : "Ask me anything, and I'll provide detailed reasoning..."
                  }
                  className="flex-1 min-h-[60px] max-h-[120px] resize-none bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500/20"
                  disabled={isLoading || isWaitingForUser}
                />
                <Button
                  onClick={sendMessage}
                  disabled={!input.trim() || isLoading || isWaitingForUser}
                  size="lg"
                  className="px-6 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              
              <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
                <div className="flex items-center gap-4">
                  <span>Press Enter to send, Shift+Enter for new line</span>
                  {currentContext && (
                    <span className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 text-green-400" />
                      Context preserved
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {mode === 'react' && (
                    <Badge variant="outline" className="text-xs border-blue-500 text-blue-400">
                      ReAct Mode
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};