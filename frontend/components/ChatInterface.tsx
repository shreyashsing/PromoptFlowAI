'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User, Sparkles, MessageSquare, Zap } from 'lucide-react'
import { ConversationContext, WorkflowPlan } from '../lib/types'
import { chatAPI } from '../lib/api'
import { validateMessage } from '../lib/validation'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { ScrollArea } from '../components/ui/scroll-area'
import WorkflowExecutionStatus from './WorkflowExecutionStatus'

interface ChatInterfaceProps {
  conversationContext: ConversationContext | null
  setConversationContext: (context: ConversationContext) => void
  setCurrentWorkflow: (workflow: WorkflowPlan | null) => void
}

export default function ChatInterface({ 
  conversationContext, 
  setConversationContext, 
  setCurrentWorkflow 
}: ChatInterfaceProps) {
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [executionId, setExecutionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [conversationContext?.messages])

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
      
      if (conversationContext?.session_id) {
        // Continue existing conversation
        response = await chatAPI.sendMessage({
          message: message.trim(),
          session_id: conversationContext.session_id
        })
      } else {
        // Start new conversation
        response = await chatAPI.startNewConversation({
          prompt: message.trim()
        })
      }

      // Create a new message for the user
      const userMessage = {
        id: Date.now().toString() + '-user',
        role: 'user' as const,
        content: message.trim(),
        timestamp: new Date().toISOString()
      }

      // Create a new message for the assistant
      const assistantMessage = {
        id: Date.now().toString() + '-assistant', 
        role: 'assistant' as const,
        content: response.message,
        timestamp: new Date().toISOString()
      }

      // Update conversation context with new messages
      const updatedContext: ConversationContext = {
        session_id: response.session_id,
        user_id: response.conversation_context?.user_id || '00000000-0000-0000-0000-000000000001',
        messages: [
          ...(conversationContext?.messages || []),
          userMessage,
          assistantMessage
        ],
        current_plan: response.current_plan,
        state: response.conversation_state as any,
        created_at: conversationContext?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      setConversationContext(updatedContext)
      
      // Update workflow if one was generated
      if (response.current_plan) {
        setCurrentWorkflow(response.current_plan)
      }

      // Check if response contains execution ID (workflow was executed)
      const executionIdMatch = response.message.match(/Execution ID: `([^`]+)`/)
      if (executionIdMatch) {
        setExecutionId(executionIdMatch[1])
      }

      setMessage('')
    } catch (err: any) {
      console.error('Chat error:', err)
      if (err.message && err.message.includes('Failed to fetch')) {
        setError('Backend server is not running. Please start the backend server at http://localhost:8000')
      } else {
        setError(err.response?.data?.detail || 'Failed to send message. Please try again.')
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
    <div className="flex flex-col h-[calc(100vh-16rem)]">
      {/* Messages */}
      <ScrollArea className="flex-1 p-6 custom-scrollbar">
        {!conversationContext?.messages?.length ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="relative">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-4">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                <Zap className="w-3 h-3 text-white" />
              </div>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-white glow-text">Welcome to PromptFlow AI!</h3>
              <p className="text-slate-400 max-w-md">
                Describe what you'd like to automate and I'll help you build a powerful workflow in seconds.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 w-full max-w-md">
              <p className="text-sm font-medium text-slate-300 mb-2">Try something like:</p>
              {examplePrompts.map((prompt, index) => (
                <Card 
                  key={index}
                  className="p-3 bg-slate-800/50 border-slate-700/50 hover:bg-slate-700/50 transition-all cursor-pointer group"
                  onClick={() => setMessage(prompt)}
                >
                  <div className="flex items-start space-x-2">
                    <MessageSquare className="w-4 h-4 text-blue-400 mt-0.5 group-hover:text-blue-300" />
                    <p className="text-sm text-slate-300 group-hover:text-white transition-colors">
                      "{prompt}"
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {conversationContext.messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex items-start space-x-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-br from-blue-500 to-cyan-500' 
                      : 'bg-gradient-to-br from-purple-500 to-pink-500'
                  }`}>
                    {msg.role === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-white" />
                    )}
                  </div>
                  
                  {/* Message */}
                  <Card className={`p-4 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-blue-600 to-blue-700 border-blue-500/50 text-white'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-100'
                  }`}>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    
                    {/* Show execution status if this message contains execution info */}
                    {msg.role === 'assistant' && executionId && msg.content.includes('Execution ID:') && (
                      <WorkflowExecutionStatus 
                        executionId={executionId}
                        workflowName={conversationContext?.current_plan?.name || 'Workflow'}
                        onStatusUpdate={(status) => {
                          console.log('Execution status updated:', status)
                        }}
                      />
                    )}
                    
                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/10">
                      <p className="text-xs opacity-70">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </p>
                      {msg.role === 'assistant' && (
                        <Badge variant="secondary" className="bg-white/10 text-white/80 text-xs">
                          AI
                        </Badge>
                      )}
                    </div>
                  </Card>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      {/* Input Form */}
      <div className="p-6 border-t border-slate-700/50">
        {error && (
          <Card className="mb-4 p-3 bg-red-900/20 border-red-500/50">
            <p className="text-red-400 text-sm">{error}</p>
          </Card>
        )}
        
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your automation needs..."
              className="min-h-[60px] bg-slate-800/50 border-slate-700/50 text-white placeholder:text-slate-400 focus:border-blue-500/50 focus:ring-blue-500/20 resize-none"
              disabled={isLoading}
            />
          </div>
          <Button
            type="submit"
            disabled={isLoading || !message.trim()}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-6 h-[60px] glow-border"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </form>
        
        <div className="text-xs text-slate-500 mt-3 flex items-center space-x-4">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <Badge variant="outline" className="border-slate-700 text-slate-400">
            <Zap className="w-3 h-3 mr-1" />
            AI Powered
          </Badge>
        </div>
      </div>
    </div>
  )
}