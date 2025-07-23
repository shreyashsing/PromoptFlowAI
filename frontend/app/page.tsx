'use client'

import { useState } from 'react'
import ChatInterface from '../components/ChatInterface'
import WorkflowVisualization from '../components/WorkflowVisualization'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { UserMenu } from '../components/auth/UserMenu'
import { ConversationContext, WorkflowPlan } from '../lib/types'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { Bot, Workflow, Sparkles, Zap } from 'lucide-react'

export default function Home() {
  const [conversationContext, setConversationContext] = useState<ConversationContext | null>(null)
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowPlan | null>(null)

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
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 h-[calc(100vh-12rem)]">
          {/* Chat Interface */}
          <Card className="glass-card border-slate-700/50 overflow-hidden">
            <div className="p-6 border-b border-slate-700/50">
              <div className="flex items-center space-x-3 mb-2">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white">Workflow Planning Assistant</h2>
              </div>
              <p className="text-slate-400">Describe your automation needs and I'll help you build a workflow</p>
            </div>
            <ChatInterface 
              conversationContext={conversationContext}
              setConversationContext={setConversationContext}
              setCurrentWorkflow={setCurrentWorkflow}
            />
          </Card>

          {/* Workflow Visualization */}
          <Card className="glass-card border-slate-700/50 overflow-hidden">
            <div className="p-6 border-b border-slate-700/50">
              <div className="flex items-center space-x-3 mb-2">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                  <Workflow className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white">Workflow Visualization</h2>
              </div>
              <p className="text-slate-400">Visual representation of your automation workflow</p>
            </div>
            <WorkflowVisualization workflow={currentWorkflow} />
          </Card>
        </div>

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