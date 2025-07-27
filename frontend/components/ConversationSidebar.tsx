'use client'

import { useState } from 'react'
import {
  Plus,
  MessageSquare,
  Trash2,
  Menu,
  X,
  Search,
  MoreHorizontal,
  Edit3,
  Workflow
} from 'lucide-react'
import { ConversationContext } from '../lib/types'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'
import { Input } from './ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu'

interface ConversationSidebarProps {
  conversations: ConversationContext[]
  currentConversation: ConversationContext | null
  onNewChat: () => void
  onSelectConversation: (conversation: ConversationContext) => void
  onDeleteConversation: (sessionId: string) => void
  isOpen: boolean
  onToggle: () => void
  isLoading: boolean
}

export default function ConversationSidebar({
  conversations,
  currentConversation,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  isOpen,
  onToggle,
  isLoading
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  const getConversationTitle = (conversation: ConversationContext) => {
    if (conversation.messages.length > 0) {
      const firstUserMessage = conversation.messages.find(m => m.role === 'user')
      if (firstUserMessage) {
        return firstUserMessage.content.slice(0, 50) + (firstUserMessage.content.length > 50 ? '...' : '')
      }
    }
    return 'New Conversation'
  }

  const filteredConversations = (conversations || []).filter(conv => {
    const title = getConversationTitle(conv)
    return title.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 24 * 7) {
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const handleEditStart = (conversation: ConversationContext) => {
    setEditingId(conversation.session_id)
    setEditingTitle(getConversationTitle(conversation))
  }

  const handleEditSave = () => {
    // TODO: Implement conversation title update API
    setEditingId(null)
    setEditingTitle('')
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditingTitle('')
  }

  if (!isOpen) {
    return (
      <div className="w-12 bg-gray-950 border-r border-gray-800 flex flex-col items-center py-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="text-gray-400 hover:text-white hover:bg-gray-800"
        >
          <Menu className="w-5 h-5" />
        </Button>
      </div>
    )
  }

  return (
    <div className="w-80 bg-gray-950 border-r border-gray-800 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Conversations</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="text-gray-400 hover:text-white hover:bg-gray-800"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* New Chat Button */}
        <Button
          onClick={onNewChat}
          className="w-full bg-gray-800 hover:bg-gray-700 text-white border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Chat
        </Button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-800">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-gray-800 border-gray-700 text-white placeholder:text-gray-400 focus:border-gray-600"
          />
        </div>
      </div>

      {/* Conversations List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-800/50 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">
                {searchQuery ? 'No conversations found' : 'No conversations yet'}
              </p>
              <p className="text-gray-500 text-xs mt-1">
                {searchQuery ? 'Try a different search term' : 'Start a new chat to begin'}
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {filteredConversations.map((conversation) => (
                <div
                  key={conversation.session_id}
                  className={`group relative rounded-lg p-3 cursor-pointer transition-colors ${currentConversation?.session_id === conversation.session_id
                      ? 'bg-gray-800 border border-gray-700'
                      : 'hover:bg-gray-800/50'
                    }`}
                  onClick={() => onSelectConversation(conversation)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {editingId === conversation.session_id ? (
                        <Input
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onBlur={handleEditSave}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleEditSave()
                            if (e.key === 'Escape') handleEditCancel()
                          }}
                          className="h-6 text-sm bg-gray-700 border-gray-600 text-white"
                          autoFocus
                        />
                      ) : (
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-medium text-white truncate flex-1">
                            {getConversationTitle(conversation)}
                          </h3>
                          <div className="text-xs text-gray-500 ml-2">
                            <Workflow className="w-3 h-3" />
                          </div>
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-1">
                        <p className="text-xs text-gray-400">
                          {conversation.messages.length} messages
                        </p>
                        <div className="flex items-center space-x-2">
                          <p className="text-xs text-gray-500">
                            {formatDate(conversation.updated_at)}
                          </p>
                          <p className="text-xs text-gray-500">• Click to view workflow</p>
                        </div>
                      </div>
                    </div>

                    {/* Actions Menu */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-white hover:bg-gray-700 h-6 w-6 p-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="w-3 h-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-gray-800 border-gray-700">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            handleEditStart(conversation)
                          }}
                          className="text-gray-300 hover:text-white hover:bg-gray-700"
                        >
                          <Edit3 className="w-4 h-4 mr-2" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation()
                            onDeleteConversation(conversation.session_id)
                          }}
                          className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {/* Status indicator */}
                  <div className="flex items-center mt-2">
                    <div className={`w-2 h-2 rounded-full mr-2 ${conversation.state === 'executing' ? 'bg-blue-500 animate-pulse' :
                        conversation.state === 'approved' ? 'bg-green-500' :
                          conversation.state === 'planning' ? 'bg-yellow-500' :
                            'bg-gray-500'
                      }`} />
                    <span className="text-xs text-gray-400 capitalize">
                      {conversation.state}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500 text-center">
          {(conversations || []).length} conversation{(conversations || []).length !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  )
}