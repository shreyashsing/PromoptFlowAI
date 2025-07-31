'use client'

import { useState, useRef, useEffect } from 'react'
import { 
  Send, 
  Loader2, 
  Bot, 
  User, 
  Sparkles, 
  MessageSquare, 
  Zap,
  Menu,
  Settings,
  Share
} from 'lucide-react'
import { ConversationContext, ChatMessage, ReactAgentStatus } from '../lib/types'
import { chatAPI, reactAgentAPI } from '../lib/api'
import { validateMessage } from '../lib/validation'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { ScrollArea } from './ui/scroll-area'
import { UserMenu } from './auth/UserMenu'
import AgentModeToggle from './AgentModeToggle'
import ReactAgentStatusDisplay from './ReactAgentStatus'
import ReasoningTraceDisplay from './ReasoningTraceDisplay'
import ToolCallsDisplay from './ToolCallsDisplay'
import ConversationHistoryNav from './ConversationHistoryNav'

interface ChatAreaProps {
  conversation: ConversationContext | null
  onConversationUpdate: (conversation: ConversationContext) => void
  onToggleSidebar: () => void
}

export default function ChatArea({
  conversation,
  onConversationUpdate,
  onToggleSidebar
}: ChatAreaProps) {
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [agentMode, setAgentMode] = useState<'workflow' | 'react'>('workflow')
  const [reactStatus, setReactStatus] = useState<ReactAgentStatus>({
    status: 'idle',
    timestamp: Date.now()
  })
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [conversation?.messages])

  // Set up WebSocket connection for ReAct agent real-time updates
  useEffect(() => {
    if (agentMode === 'react' && conversation?.session_id) {
      const userId = conversation.user_id
      const ws = reactAgentAPI.connectWebSocket(userId, conversation.session_id)
      
      ws.onopen = () => {
        console.log('WebSocket connected for ReAct agent updates')
        setWsConnection(ws)
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'processing_started') {
            setReactStatus({
              status: 'thinking',
              timestamp: data.timestamp,
              message: 'Starting to process your request...'
            })
          } else if (data.type === 'reasoning_step') {
            const stepType = data.step_type?.toLowerCase() || ''
            let status = 'thinking'
            if (stepType.includes('action')) {
              status = 'acting'
            } else if (stepType.includes('observation')) {
              status = 'observing'
            }
            
            setReactStatus({
              status,
              current_step: data.step_number,
              total_steps: data.total_steps,
              timestamp: data.timestamp,
              message: data.content,
              current_tool: data.tool_name
            })
          } else if (data.type === 'tool_execution') {
            setReactStatus({
              status: 'acting',
              timestamp: data.timestamp,
              current_tool: data.tool_name,
              message: `Executing ${data.tool_name}...`
            })
          } else if (data.type === 'completed') {
            setReactStatus({
              status: 'completed',
              timestamp: data.timestamp,
              message: 'Task completed successfully!'
            })
            // Clear status after a delay
            setTimeout(() => {
              setReactStatus({ status: 'idle', timestamp: Date.now() })
            }, 3000)
          } else if (data.type === 'error') {
            setReactStatus({
              status: 'error',
              timestamp: data.timestamp,
              message: data.error || 'An error occurred'
            })
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      ws.onclose = () => {
        console.log('WebSocket connection closed')
        setWsConnection(null)
      }
      
      return () => {
        ws.close()
        setWsConnection(null)
      }
    }
  }, [agentMode, conversation?.session_id, conversation?.user_id])

  // Update conversation agent mode when mode changes
  useEffect(() => {
    if (conversation) {
      const updatedConversation = {
        ...conversation,
        agent_mode: agentMode
      }
      onConversationUpdate(updatedConversation)
    }
  }, [agentMode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validation = validateMessage(message)
    if (!validation.isValid) {
      setError(validation.errors[0])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      let response
      
      if (agentMode === 'react') {
        // Use ReAct agent
        setReactStatus({
          status: 'thinking',
          timestamp: Date.now(),
          message: 'Processing your request...'
        })
        
        response = await reactAgentAPI.chatWithAgent({
          query: message.trim(),
          ...(conversation?.session_id && { session_id: conversation.session_id }),
          max_iterations: 10
        })
        
        // Create user message
        const userMessage: ChatMessage = {
          id: Date.now().toString() + '-user',
          role: 'user',
          content: message.trim(),
          timestamp: new Date().toISOString()
        }

        // Create assistant message with ReAct data
        const assistantMessage: ChatMessage = {
          id: Date.now().toString() + '-assistant', 
          role: 'assistant',
          content: response.response,
          timestamp: new Date().toISOString(),
          reasoning_trace: response.reasoning_trace,
          tool_calls: response.tool_calls,
          metadata: {
            processing_time_ms: response.processing_time_ms,
            iterations_used: response.iterations_used,
            tools_used: response.tools_used,
            status: response.status
          }
        }

        // Update conversation context
        const updatedContext: ConversationContext = {
          session_id: response.session_id,
          user_id: conversation?.user_id || '00000000-0000-0000-0000-000000000001',
          messages: [
            ...(conversation?.messages || []),
            userMessage,
            assistantMessage
          ],
          current_plan: conversation?.current_plan,
          state: (conversation?.state || 'initial') as 'initial' | 'planning' | 'confirming' | 'approved' | 'executing',
          created_at: conversation?.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString(),
          agent_mode: 'react'
        }

        onConversationUpdate(updatedContext)
        
        // Update status to completed
        setReactStatus({
          status: 'completed',
          timestamp: Date.now(),
          message: 'Response generated successfully!'
        })
        
        // Clear status after delay
        setTimeout(() => {
          setReactStatus({ status: 'idle', timestamp: Date.now() })
        }, 3000)
        
      } else {
        // Use workflow mode (existing logic)
        if (conversation?.session_id) {
          response = await chatAPI.sendMessage({
            message: message.trim(),
            session_id: conversation.session_id
          })
        } else {
          response = await chatAPI.startNewConversation({
            prompt: message.trim()
          })
        }

        const userMessage: ChatMessage = {
          id: Date.now().toString() + '-user',
          role: 'user',
          content: message.trim(),
          timestamp: new Date().toISOString()
        }

        const assistantMessage: ChatMessage = {
          id: Date.now().toString() + '-assistant', 
          role: 'assistant',
          content: response.message,
          timestamp: new Date().toISOString()
        }

        const updatedContext: ConversationContext = {
          session_id: response.session_id,
          user_id: response.conversation_context?.user_id || '00000000-0000-0000-0000-000000000001',
          messages: [
            ...(conversation?.messages || []),
            userMessage,
            assistantMessage
          ],
          current_plan: response.current_plan,
          state: (response.conversation_state as 'initial' | 'planning' | 'confirming' | 'approved' | 'executing') || 'initial',
          created_at: conversation?.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString(),
          agent_mode: 'workflow'
        }

        onConversationUpdate(updatedContext)
      }

      setMessage('')
    } catch (err: any) {
      console.error('Chat error:', err)
      
      // Update ReAct status on error
      if (agentMode === 'react') {
        setReactStatus({
          status: 'error',
          timestamp: Date.now(),
          message: err.message || 'An error occurred'
        })
      }
      
      if (err.message && err.message.includes('Failed to fetch')) {
        setError('Backend server is not running. Please start the backend server at http://localhost:8000')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to send message. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as any)
    }
  }

  const examplePrompts = [
    "Send me an email when someone fills out my contact form",
    "Update a Google Sheet when I receive a payment",
    "Post to Slack when a new GitHub issue is created",
    "Create a task in Notion when I get a new lead"
  ]

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-950 border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleSidebar}
              className="text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <Menu className="w-5 h-5" />
            </Button>
            
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">
                  {conversation ? 'PromptFlow AI' : 'New Conversation'}
                </h1>
                {conversation && (
                  <p className="text-sm text-gray-400">
                    {conversation.messages.length} messages
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {conversation && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-gray-400 hover:text-white hover:bg-gray-800"
                >
                  <Share className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-gray-400 hover:text-white hover:bg-gray-800"
                >
                  <Settings className="w-4 h-4" />
                </Button>
              </>
            )}
            <Badge variant="secondary" className={`border-gray-700 ${
              agentMode === 'react' 
                ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white' 
                : 'bg-gray-800 text-gray-300'
            }`}>
              {agentMode === 'react' ? <Bot className="w-3 h-3 mr-1" /> : <Zap className="w-3 h-3 mr-1" />}
              {agentMode === 'react' ? 'ReAct Agent' : 'Workflow'}
            </Badge>
            <UserMenu />
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6">
        {!conversation?.messages?.length ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-8 max-w-2xl mx-auto">
            <div className="relative">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center mb-6">
                <Sparkles className="w-12 h-12 text-white" />
              </div>
              <div className="absolute -top-2 -right-2 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                <Zap className="w-4 h-4 text-white" />
              </div>
            </div>
            
            <div className="space-y-3">
              <h2 className="text-3xl font-bold text-white">
                How can I help you today?
              </h2>
              <p className="text-gray-400 text-lg max-w-md">
                Describe what you'd like to automate and I'll help you build a powerful workflow.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
              {examplePrompts.map((prompt, index) => (
                <Card 
                  key={index}
                  className="p-4 bg-gray-800/50 border-gray-700/50 hover:bg-gray-700/50 transition-all cursor-pointer group"
                  onClick={() => setMessage(prompt)}
                >
                  <div className="flex items-start space-x-3">
                    <MessageSquare className="w-5 h-5 text-blue-400 mt-0.5 group-hover:text-blue-300 flex-shrink-0" />
                    <p className="text-sm text-gray-300 group-hover:text-white transition-colors">
                      {prompt}
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto py-6">
            <div className="space-y-6">
              {conversation.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start space-x-4 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    {/* Avatar */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      msg.role === 'user' 
                        ? 'bg-gradient-to-br from-blue-500 to-cyan-500' 
                        : 'bg-gradient-to-br from-purple-500 to-pink-500'
                    }`}>
                      {msg.role === 'user' ? (
                        <User className="w-5 h-5 text-white" />
                      ) : (
                        <Bot className="w-5 h-5 text-white" />
                      )}
                    </div>
                    
                    {/* Message */}
                    <div className={`rounded-2xl px-6 py-4 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-100 border border-gray-700'
                    }`}>
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      
                      {/* ReAct Agent specific displays */}
                      {msg.role === 'assistant' && agentMode === 'react' && (
                        <div className="mt-4 space-y-3">
                          {/* Reasoning Trace */}
                          {msg.reasoning_trace && msg.reasoning_trace.length > 0 && (
                            <ReasoningTraceDisplay reasoningTrace={msg.reasoning_trace} />
                          )}
                          
                          {/* Tool Calls */}
                          {msg.tool_calls && msg.tool_calls.length > 0 && (
                            <ToolCallsDisplay toolCalls={msg.tool_calls} />
                          )}
                          
                          {/* Metadata */}
                          {msg.metadata && (
                            <div className="flex flex-wrap gap-2 mt-3">
                              {msg.metadata.processing_time_ms && (
                                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 text-xs">
                                  {msg.metadata.processing_time_ms}ms
                                </Badge>
                              )}
                              {msg.metadata.iterations_used && (
                                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 text-xs">
                                  {msg.metadata.iterations_used} iterations
                                </Badge>
                              )}
                              {msg.metadata.tools_used && (
                                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 text-xs">
                                  {msg.metadata.tools_used} tools used
                                </Badge>
                              )}
                              {msg.metadata.status && (
                                <Badge 
                                  variant="secondary" 
                                  className={`text-xs ${
                                    msg.metadata.status === 'completed' 
                                      ? 'bg-green-500/20 text-green-300' 
                                      : msg.metadata.status === 'failed'
                                      ? 'bg-red-500/20 text-red-300'
                                      : 'bg-slate-700/50 text-slate-300'
                                  }`}
                                >
                                  {msg.metadata.status}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/10">
                        <p className="text-xs opacity-70">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </p>
                        {msg.role === 'assistant' && agentMode === 'react' && (
                          <Badge variant="secondary" className="bg-purple-500/20 text-purple-300 text-xs">
                            ReAct Agent
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Input Area */}
      <div className="bg-gray-950 border-t border-gray-800 p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Agent Mode Toggle */}
          <div className="flex justify-center">
            <AgentModeToggle
              mode={agentMode}
              onModeChange={setAgentMode}
              disabled={isLoading}
            />
          </div>

          {/* Conversation History Navigation */}
          {agentMode === 'react' && (
            <ConversationHistoryNav
              currentSessionId={conversation?.session_id}
              onSelectConversation={async (selectedConversation) => {
                try {
                  // Load the full conversation history
                  const fullHistory = await reactAgentAPI.getConversationHistory(selectedConversation.session_id)
                  
                  // Convert to ConversationContext format
                  const conversationContext: ConversationContext = {
                    session_id: fullHistory.session_id,
                    user_id: selectedConversation.user_id,
                    messages: fullHistory.messages.map(msg => ({
                      ...msg,
                      role: msg.role as 'user' | 'assistant'
                    })),
                    current_plan: conversation?.current_plan,
                    state: (conversation?.state || 'initial') as 'initial' | 'planning' | 'confirming' | 'approved' | 'executing',
                    created_at: fullHistory.created_at || new Date().toISOString(),
                    updated_at: fullHistory.updated_at || new Date().toISOString(),
                    agent_mode: 'react' as const
                  }
                  
                  onConversationUpdate(conversationContext)
                } catch (error) {
                  console.error('Failed to load conversation:', error)
                  setError('Failed to load conversation history')
                }
              }}
            />
          )}

          {/* ReAct Agent Status */}
          {agentMode === 'react' && reactStatus.status !== 'idle' && (
            <ReactAgentStatusDisplay
              status={reactStatus}
              reasoningTrace={conversation?.messages
                .filter(m => m.role === 'assistant')
                .slice(-1)[0]?.reasoning_trace}
              toolCalls={conversation?.messages
                .filter(m => m.role === 'assistant')
                .slice(-1)[0]?.tool_calls}
            />
          )}

          {error && (
            <Card className="p-3 bg-red-900/20 border-red-500/50">
              <p className="text-red-400 text-sm">{error}</p>
            </Card>
          )}
          
          <form onSubmit={handleSubmit} className="flex gap-4">
            <div className="flex-1">
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={agentMode === 'react' 
                  ? "Ask me anything - I'll reason through it and use tools as needed..." 
                  : "Message PromptFlow AI..."
                }
                className="min-h-[60px] max-h-[200px] bg-gray-800 border-gray-700 text-white placeholder:text-gray-400 focus:border-gray-600 focus:ring-gray-600 resize-none rounded-xl"
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              disabled={isLoading || !message.trim()}
              className={`px-6 h-[60px] rounded-xl text-white ${
                agentMode === 'react'
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </form>
          
          <div className="text-xs text-gray-500 text-center">
            Press Enter to send, Shift+Enter for new line
            {agentMode === 'react' && (
              <span className="ml-2 text-purple-400">• ReAct Agent Mode Active</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}