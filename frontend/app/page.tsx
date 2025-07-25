'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '../components/ChatInterface'
import InteractiveWorkflowVisualization from '@/components/InteractiveWorkflowVisualization'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { UserMenu } from '../components/auth/UserMenu'
import { ConversationContext, WorkflowPlan, ChatMessage } from '../lib/types'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { Bot, Workflow, Sparkles, Zap, RefreshCw } from 'lucide-react'
import { sessionManager } from '../lib/session'
import { chatAPI } from '../lib/api'

export default function Home() {
  const [conversationContext, setConversationContext] = useState<ConversationContext | null>(null)
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowPlan | null>(null)
  const [isRestoringSession, setIsRestoringSession] = useState(true)

  // Restore session on page load
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const sessionData = sessionManager.loadSession()
        
        if (sessionData?.sessionId) {
          console.log('Restoring session:', sessionData.sessionId)
          
          // Load conversation from backend
          const conversationData = await chatAPI.loadConversation(sessionData.sessionId)
          
          if (conversationData) {
            // Convert backend data to frontend format
            const messages: ChatMessage[] = conversationData.messages.map((msg: any) => ({
              ...msg,
              timestamp: msg.timestamp
            }))
            
            const restoredContext: ConversationContext = {
              session_id: conversationData.session_id,
              user_id: conversationData.user_id,
              messages,
              current_plan: conversationData.current_plan,
              state: conversationData.state,
              created_at: conversationData.created_at,
              updated_at: conversationData.updated_at
            }
            
            setConversationContext(restoredContext)
            
            // Restore workflow if available
            if (conversationData.current_plan) {
              setCurrentWorkflow(conversationData.current_plan)
            }
            
            // Update activity timestamp
            sessionManager.updateActivity()
            
            console.log('Session restored successfully')
          } else {
            // Session not found on backend, clear local storage
            sessionManager.clearSession()
          }
        }
        
        // Also try to restore workflow from localStorage as fallback
        const localWorkflow = sessionManager.loadCurrentWorkflow()
        if (localWorkflow && !currentWorkflow) {
          setCurrentWorkflow(localWorkflow)
        }
        
      } catch (error) {
        console.warn('Failed to restore session:', error)
        sessionManager.clearSession()
      } finally {
        setIsRestoringSession(false)
      }
    }

    restoreSession()
  }, [])

  // Save session and workflow data whenever they change
  useEffect(() => {
    if (conversationContext) {
      sessionManager.saveSession(conversationContext.session_id)
    }
  }, [conversationContext])

  useEffect(() => {
    sessionManager.saveCurrentWorkflow(currentWorkflow)
  }, [currentWorkflow])

  // Enhanced setConversationContext that also updates session
  const handleSetConversationContext = (context: ConversationContext) => {
    setConversationContext(context)
    sessionManager.saveSession(context.session_id)
    sessionManager.updateActivity()
  }

  // Enhanced setCurrentWorkflow that also saves to localStorage
  const handleSetCurrentWorkflow = (workflow: WorkflowPlan | null) => {
    setCurrentWorkflow(workflow)
    sessionManager.saveCurrentWorkflow(workflow)
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl animate-pulse delay-500"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 glass-header">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
                </div>
                <div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                    PromptFlow AI
                  </h1>
                  <p className="text-sm text-slate-400">No-code AI automation platform</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Badge variant="secondary" className="bg-slate-800/50 text-slate-300 border-slate-700">
                <Zap className="w-3 h-3 mr-1" />
                Beta
              </Badge>
              <UserMenu />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 py-8">
        {isRestoringSession ? (
          /* Loading State */
          <div className="flex items-center justify-center h-[calc(100vh-12rem)]">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-slate-400">Restoring your session...</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 h-[calc(100vh-12rem)]">
            {/* Chat Interface */}
            <Card className="glass-card border-slate-700/50 overflow-hidden">
              <div className="p-6 border-b border-slate-700/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <h2 className="text-xl font-semibold text-white">Workflow Planning Assistant</h2>
                  </div>
                  {conversationContext && (
                    <Badge variant="secondary" className="bg-green-500/20 text-green-400 border-green-500/30">
                      Session Active
                    </Badge>
                  )}
                </div>
                <p className="text-slate-400">
                  {conversationContext ? 
                    'Continue your conversation or start planning a new workflow' : 
                    'Describe your automation needs and I\'ll help you build a workflow'
                  }
                </p>
              </div>
              <ChatInterface 
                conversationContext={conversationContext}
                setConversationContext={handleSetConversationContext}
                setCurrentWorkflow={handleSetCurrentWorkflow}
              />
            </Card>

            {/* Workflow Visualization */}
            <Card className="glass-card border-slate-700/50 overflow-hidden">
              <div className="p-6 border-b border-slate-700/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                      <Workflow className="w-5 h-5 text-white" />
                    </div>
                    <h2 className="text-xl font-semibold text-white">Workflow Visualization</h2>
                  </div>
                  {currentWorkflow && (
                    <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                      {currentWorkflow.status}
                    </Badge>
                  )}
                </div>
                <p className="text-slate-400">
                  {currentWorkflow ? 
                    'Your workflow is ready - configure and execute' : 
                    'Visual representation of your automation workflow'
                  }
                </p>
              </div>
              <InteractiveWorkflowVisualization 
                workflow={currentWorkflow} 
                onWorkflowUpdate={handleSetCurrentWorkflow}
                onExecuteWorkflow={async (workflowId) => {
                  try {
                    const result = await fetch(`http://localhost:8000/api/v1/workflows/${workflowId}/execute`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer dev-test-token'
                      },
                      body: JSON.stringify({ trigger_type: 'manual' })
                    })
                    const data = await result.json()
                    console.log('Workflow execution started:', data)
                  } catch (error) {
                    console.error('Failed to execute workflow:', error)
                  }
                }}
              />
            </Card>
          </div>
        )}

        {/* Status Bar */}
        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center space-x-4 text-sm text-slate-500">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Frontend Online</span>
            </div>
            <Separator orientation="vertical" className="h-4 bg-slate-700" />
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Backend Online</span>
            </div>
            <Separator orientation="vertical" className="h-4 bg-slate-700" />
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>AI Ready</span>
            </div>
          </div>
          <div className="text-xs text-slate-600">
            v1.0.0-beta
          </div>
        </div>
      </main>
    </div>
    </ProtectedRoute>
  )
}