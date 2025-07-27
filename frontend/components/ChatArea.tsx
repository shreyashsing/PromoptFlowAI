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
import { ConversationContext, ChatMessage } from '../lib/types'
import { chatAPI } from '../lib/api'
import { validateMessage } from '../lib/validation'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { ScrollArea } from './ui/scroll-area'
import { UserMenu } from './auth/UserMenu'

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
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [conversation?.messages])

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
      
      if (conversation?.session_id) {
        // Continue existing conversation
        response = await chatAPI.sendMessage({
          message: message.trim(),
          session_id: conversation.session_id
        })
      } else {
        // Start new conversation
        response = await chatAPI.startNewConversation({
          prompt: message.trim()
        })
      }

      // Create a new message for the user
      const userMessage: ChatMessage = {
        id: Date.now().toString() + '-user',
        role: 'user',
        content: message.trim(),
        timestamp: new Date().toISOString()
      }

      // Create a new message for the assistant
      const assistantMessage: ChatMessage = {
        id: Date.now().toString() + '-assistant', 
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString()
      }

      // Update conversation context with new messages
      const updatedContext: ConversationContext = {
        session_id: response.session_id,
        user_id: response.conversation_context?.user_id || '00000000-0000-0000-0000-000000000001',
        messages: [
          ...(conversation?.messages || []),
          userMessage,
          assistantMessage
        ],
        current_plan: response.current_plan,
        state: response.conversation_state as any,
        created_at: conversation?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      onConversationUpdate(updatedContext)
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
            <Badge variant="secondary" className="bg-gray-800 text-gray-300 border-gray-700">
              <Zap className="w-3 h-3 mr-1" />
              AI
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
                      
                      <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/10">
                        <p className="text-xs opacity-70">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </p>
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
        <div className="max-w-4xl mx-auto">
          {error && (
            <Card className="mb-4 p-3 bg-red-900/20 border-red-500/50">
              <p className="text-red-400 text-sm">{error}</p>
            </Card>
          )}
          
          <form onSubmit={handleSubmit} className="flex gap-4">
            <div className="flex-1">
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message PromptFlow AI..."
                className="min-h-[60px] max-h-[200px] bg-gray-800 border-gray-700 text-white placeholder:text-gray-400 focus:border-gray-600 focus:ring-gray-600 resize-none rounded-xl"
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 h-[60px] rounded-xl"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </form>
          
          <div className="text-xs text-gray-500 mt-3 text-center">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
      </div>
    </div>
  )
}