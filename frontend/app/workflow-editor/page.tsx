'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '../../components/auth/ProtectedRoute'
import { UserMenu } from '../../components/auth/UserMenu'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Separator } from '../../components/ui/separator'
import { Bot, Sparkles, Zap, ArrowLeft, Workflow } from 'lucide-react'
import InteractiveWorkflowVisualization from '@/components/InteractiveWorkflowVisualization'
import { WorkflowPlan } from '@/lib/types'

export default function WorkflowEditor() {
  const [workflow, setWorkflow] = useState<WorkflowPlan | null>(null)

  useEffect(() => {
    // Load workflow from localStorage (set by ReactWorkflowBuilder)
    const storedWorkflow = localStorage.getItem('currentWorkflow')
    if (storedWorkflow) {
      try {
        const parsedWorkflow = JSON.parse(storedWorkflow)
        setWorkflow(parsedWorkflow)
      } catch (error) {
        console.error('Error parsing stored workflow:', error)
      }
    }
  }, [])

  const handleWorkflowUpdate = (updatedWorkflow: WorkflowPlan) => {
    setWorkflow(updatedWorkflow)
    // Update localStorage
    localStorage.setItem('currentWorkflow', JSON.stringify(updatedWorkflow))
  }

  const handleExecuteWorkflow = (workflowId: string) => {
    // This will be handled by the InteractiveWorkflowVisualization component
    console.log('Executing workflow:', workflowId)
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
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => window.history.back()}
                  className="text-slate-400 hover:text-white"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                
                <Separator orientation="vertical" className="h-6 bg-slate-700" />
                
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                      <Workflow className="w-6 h-6 text-white" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                      Workflow Editor
                    </h1>
                    <p className="text-sm text-slate-400">
                      {workflow ? workflow.name : 'Interactive workflow visualization'}
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Badge variant="secondary" className="bg-slate-800/50 text-slate-300 border-slate-700">
                  <Zap className="w-3 h-3 mr-1" />
                  Live Editor
                </Badge>
                <UserMenu />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 py-8">
          <div className="h-[calc(100vh-12rem)]">
            {workflow ? (
              <InteractiveWorkflowVisualization
                workflow={workflow}
                onWorkflowUpdate={handleWorkflowUpdate}
                onExecuteWorkflow={handleExecuteWorkflow}
              />
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-6">
                  <div className="relative">
                    <div className="w-24 h-24 bg-gradient-to-br from-slate-700 to-slate-800 rounded-2xl flex items-center justify-center mb-4 mx-auto">
                      <Workflow className="w-12 h-12 text-slate-400" />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold text-slate-300">No workflow loaded</h3>
                    <p className="text-slate-500 max-w-sm">
                      Create a workflow using the ReAct builder to visualize and edit it here
                    </p>
                  </div>

                  <Button
                    onClick={() => window.location.href = '/'}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Bot className="w-4 h-4 mr-2" />
                    Create Workflow
                  </Button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}