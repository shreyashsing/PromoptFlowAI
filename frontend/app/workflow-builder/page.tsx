'use client'

import TrueReActWorkflowBuilder from '@/components/TrueReActWorkflowBuilder'
import { ProtectedRoute } from '../../components/auth/ProtectedRoute'
import { UserMenu } from '../../components/auth/UserMenu'
import { Badge } from '../../components/ui/badge'
import { Bot, Sparkles, Zap, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '../../components/ui/button'

export default function WorkflowBuilderPage() {
  return (
    <ProtectedRoute>
      <div className="h-screen bg-slate-950 overflow-hidden">
        {/* Header */}
        <header className="relative z-20 bg-slate-900/90 backdrop-blur-sm border-b border-slate-700">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex justify-between items-center py-3">
              <div className="flex items-center space-x-4">
                <Link href="/">
                  <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Chat
                  </Button>
                </Link>
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                  <div>
                    <h1 className="text-lg font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                      Workflow Builder
                    </h1>
                    <p className="text-xs text-slate-400">Visual workflow creation</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Badge variant="secondary" className="bg-slate-800/50 text-slate-300 border-slate-700">
                  <Zap className="w-3 h-3 mr-1" />
                  Legacy
                </Badge>
                <UserMenu />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content - Workflow Builder */}
        <main className="h-[calc(100vh-60px)]">
          <TrueReActWorkflowBuilder />
        </main>
      </div>
    </ProtectedRoute>
  )
}