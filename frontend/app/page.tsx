'use client'

import TrueReActWorkflowBuilder from '@/components/TrueReActWorkflowBuilder'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { UserMenu } from '../components/auth/UserMenu'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { Bot, Sparkles, Zap, MessageSquare } from 'lucide-react'

export default function Home() {

  return (
    <ProtectedRoute>
      <div className="h-screen bg-slate-950 overflow-hidden">
        {/* Header - Simplified for String-like interface */}
        <header className="relative z-20 bg-slate-900/90 backdrop-blur-sm border-b border-slate-700">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex justify-between items-center py-3">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                  <div>
                    <h1 className="text-lg font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                      PromptFlow AI
                    </h1>
                    <p className="text-xs text-slate-400">No-code AI automation platform</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <a 
                  href="/chat"
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-md transition-colors text-sm font-medium flex items-center gap-2"
                >
                  <MessageSquare className="w-3 h-3" />
                  Advanced Chat
                </a>
                <Badge variant="secondary" className="bg-slate-800/50 text-slate-300 border-slate-700">
                  <Zap className="w-3 h-3 mr-1" />
                  Beta
                </Badge>
                <UserMenu />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content - Full height True ReAct interface */}
        <main className="h-[calc(100vh-60px)]">
          <TrueReActWorkflowBuilder />
        </main>
      </div>
    </ProtectedRoute>
  )
}