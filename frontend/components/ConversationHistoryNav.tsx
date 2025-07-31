'use client'

import { useState, useEffect } from 'react'
import {
  History,
  Search,
  Filter,
  Bot,
  Workflow,
  Clock,
  MessageSquare,
  Wrench,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { ScrollArea } from './ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible'
import { reactAgentAPI } from '../lib/api'
import { ReactConversation } from '../lib/types'

interface ConversationHistoryNavProps {
  currentSessionId?: string
  onSelectConversation: (conversation: ReactConversation) => void
  className?: string
}

export default function ConversationHistoryNav({
  currentSessionId,
  onSelectConversation,
  className = ""
}: ConversationHistoryNavProps) {
  const [conversations, setConversations] = useState<ReactConversation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [filter, setFilter] = useState<'all' | 'react' | 'workflow'>('all')

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      setIsLoading(true)
      const result = await reactAgentAPI.listConversations(20, searchQuery)

      // Ensure conversations have the expected structure
      const normalizedConversations = (result || []).map(conv => ({
        ...conv,
        messages: conv.messages || [],
        summary: conv.summary || {
          total_messages: 0,
          tools_used: [],
          total_tool_calls: 0,
          avg_response_time: 0
        }
      }))

      setConversations(normalizedConversations)
    } catch (error) {
      console.error('Failed to load conversations:', error)
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = async () => {
    await loadConversations()
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = diffMs / (1000 * 60 * 60)
    const diffDays = diffMs / (1000 * 60 * 60 * 24)

    if (diffHours < 1) {
      return 'Just now'
    } else if (diffHours < 24) {
      return `${Math.floor(diffHours)}h ago`
    } else if (diffDays < 7) {
      return `${Math.floor(diffDays)}d ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  const getConversationPreview = (conversation: ReactConversation) => {
    // Check if messages array exists and has content
    if (!conversation.messages || conversation.messages.length === 0) {
      return 'No messages'
    }

    const lastMessage = conversation.messages[conversation.messages.length - 1]
    if (!lastMessage || !lastMessage.content) return 'No messages'

    const preview = lastMessage.content.substring(0, 100)
    return preview.length < lastMessage.content.length ? `${preview}...` : preview
  }

  const filteredConversations = conversations.filter(conv => {
    if (filter === 'react') {
      return (conv.summary?.tools_used?.length || 0) > 0 // Has tool usage, likely ReAct
    } else if (filter === 'workflow') {
      return (conv.summary?.tools_used?.length || 0) === 0 // No tool usage, likely workflow
    }
    return true // 'all'
  })

  return (
    <Card className={`bg-slate-800/50 border-slate-700/50 ${className}`}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-4 hover:bg-slate-700/30"
          >
            <div className="flex items-center space-x-2">
              <History className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-white">
                Conversation History
              </span>
              <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 text-xs">
                {conversations.length}
              </Badge>
            </div>
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-3">
            {/* Search and Filter */}
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-400"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSearch}
                  disabled={isLoading}
                  className="px-3"
                >
                  <Search className="w-4 h-4" />
                </Button>
              </div>

              <div className="flex gap-1">
                {(['all', 'react', 'workflow'] as const).map((filterOption) => (
                  <Button
                    key={filterOption}
                    variant={filter === filterOption ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setFilter(filterOption)}
                    className={`text-xs ${filter === filterOption
                      ? 'bg-slate-600 text-white'
                      : 'text-slate-400 hover:text-white'
                      }`}
                  >
                    {filterOption === 'react' && <Bot className="w-3 h-3 mr-1" />}
                    {filterOption === 'workflow' && <Workflow className="w-3 h-3 mr-1" />}
                    {filterOption === 'all' && <Filter className="w-3 h-3 mr-1" />}
                    {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
                  </Button>
                ))}
              </div>
            </div>

            {/* Conversations List */}
            <ScrollArea className="h-64">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-sm text-slate-400">Loading conversations...</div>
                </div>
              ) : filteredConversations.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-sm text-slate-400">No conversations found</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredConversations.map((conversation) => (
                    <Card
                      key={conversation.session_id}
                      className={`p-3 cursor-pointer transition-all hover:bg-slate-700/30 ${currentSessionId === conversation.session_id
                        ? 'bg-slate-700/50 border-slate-600'
                        : 'bg-slate-800/30 border-slate-700/30'
                        }`}
                      onClick={() => onSelectConversation(conversation)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {(conversation.summary?.tools_used?.length || 0) > 0 ? (
                            <Bot className="w-4 h-4 text-purple-400" />
                          ) : (
                            <Workflow className="w-4 h-4 text-blue-400" />
                          )}
                          <span className="text-sm font-medium text-white">
                            {(conversation.summary?.tools_used?.length || 0) > 0 ? 'ReAct' : 'Workflow'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-1 text-xs text-slate-400">
                          <Clock className="w-3 h-3" />
                          <span>{formatTimestamp(conversation.updated_at)}</span>
                        </div>
                      </div>

                      <p className="text-sm text-slate-300 mb-2 leading-relaxed">
                        {getConversationPreview(conversation)}
                      </p>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 text-xs text-slate-400">
                          <div className="flex items-center space-x-1">
                            <MessageSquare className="w-3 h-3" />
                            <span>{conversation.summary?.total_messages || 0}</span>
                          </div>
                          {(conversation.summary?.tools_used?.length || 0) > 0 && (
                            <div className="flex items-center space-x-1">
                              <Wrench className="w-3 h-3" />
                              <span>{conversation.summary?.total_tool_calls || 0}</span>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-1">
                          {(conversation.summary?.tools_used || []).slice(0, 3).map((tool, index) => (
                            <Badge
                              key={index}
                              variant="secondary"
                              className="bg-slate-700/50 text-slate-300 text-xs"
                            >
                              {tool}
                            </Badge>
                          ))}
                          {(conversation.summary?.tools_used?.length || 0) > 3 && (
                            <Badge
                              variant="secondary"
                              className="bg-slate-700/50 text-slate-300 text-xs"
                            >
                              +{(conversation.summary?.tools_used?.length || 0) - 3}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}