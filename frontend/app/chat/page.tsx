'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '../../components/auth/ProtectedRoute'
import ConversationSidebar from '../../components/ConversationSidebar'
import ChatArea from '../../components/ChatArea'
import { ConversationContext, ChatMessage } from '../../lib/types'
import { chatAPI } from '../../lib/api'

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationContext[]>([])
  const [currentConversation, setCurrentConversation] = useState<ConversationContext | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  // Load conversation history on mount
  useEffect(() => {
    loadConversationHistory()
  }, [])

  const loadConversationHistory = async () => {
    try {
      setIsLoading(true)
      const history = await chatAPI.getConversationHistory()
      setConversations(Array.isArray(history) ? history : [])
    } catch (error) {
      console.error('Failed to load conversation history:', error)
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = () => {
    setCurrentConversation(null)
  }

  const handleSelectConversation = (conversation: ConversationContext) => {
    // Navigate to home page with the conversation context
    // Store the conversation in sessionStorage for the home page to pick up
    sessionStorage.setItem('selected_conversation', JSON.stringify(conversation))
    window.location.href = '/'
  }

  const handleConversationUpdate = (updatedConversation: ConversationContext) => {
    setCurrentConversation(updatedConversation)
    
    // Update conversations list
    setConversations(prev => {
      const existingIndex = prev.findIndex(c => c.session_id === updatedConversation.session_id)
      if (existingIndex >= 0) {
        const updated = [...prev]
        updated[existingIndex] = updatedConversation
        return updated
      } else {
        return [updatedConversation, ...prev]
      }
    })
  }

  const handleDeleteConversation = async (sessionId: string) => {
    try {
      await chatAPI.deleteConversation(sessionId)
      setConversations(prev => prev.filter(c => c.session_id !== sessionId))
      
      // If the deleted conversation was currently selected, clear it
      if (currentConversation?.session_id === sessionId) {
        setCurrentConversation(null)
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-900">
        {/* Sidebar */}
        <ConversationSidebar
          conversations={conversations}
          currentConversation={currentConversation}
          onNewChat={handleNewChat}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          isLoading={isLoading}
        />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          <ChatArea
            conversation={currentConversation}
            onConversationUpdate={handleConversationUpdate}
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          />
        </div>
      </div>
    </ProtectedRoute>
  )
}