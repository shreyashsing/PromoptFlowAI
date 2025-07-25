'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Eye,
  AlertCircle
} from 'lucide-react'
import { workflowAPI } from '@/lib/api'

interface WorkflowExecutionStatusProps {
  executionId: string
  workflowName: string
  onStatusUpdate?: (status: string) => void
}

export default function WorkflowExecutionStatus({
  executionId,
  workflowName,
  onStatusUpdate
}: WorkflowExecutionStatusProps) {
  const [status, setStatus] = useState<string>('pending')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [nodeResults, setNodeResults] = useState<any[]>([])
  const [isPolling, setIsPolling] = useState(true)

  useEffect(() => {
    if (!isPolling) return

    const pollStatus = setInterval(async () => {
      try {
        const result = await workflowAPI.getExecutionStatus(executionId)

        setStatus(result.status)
        setError(result.error)
        setNodeResults(result.node_results || [])

        // Calculate progress based on completed nodes
        if (result.node_results && result.node_results.length > 0) {
          const completedNodes = result.node_results.filter((nr: any) =>
            nr.status === 'completed' || nr.status === 'failed'
          ).length
          const progressPercent = (completedNodes / result.node_results.length) * 100
          setProgress(progressPercent)
        }

        // Stop polling if execution is complete
        if (['completed', 'failed', 'cancelled'].includes(result.status)) {
          setIsPolling(false)
          clearInterval(pollStatus)
        }

        onStatusUpdate?.(result.status)

      } catch (error) {
        console.error('Error polling execution status:', error)
        setError('Failed to get execution status')
        setIsPolling(false)
        clearInterval(pollStatus)
      }
    }, 2000)

    return () => clearInterval(pollStatus)
  }, [executionId, isPolling, onStatusUpdate])

  const getStatusIcon = () => {
    switch (status) {
      case 'running': return <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-400" />
      case 'cancelled': return <Pause className="w-4 h-4 text-yellow-400" />
      default: return <Clock className="w-4 h-4 text-slate-400" />
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'running': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'completed': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'cancelled': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30'
    }
  }

  return (
    <Card className="bg-slate-800/50 border-slate-700/50 p-4 mt-3">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Play className="w-4 h-4 text-blue-400" />
            <span className="font-medium text-white text-sm">Workflow Execution</span>
          </div>
          <Badge className={`${getStatusColor()} flex items-center gap-1 text-xs`}>
            {getStatusIcon()}
            {status}
          </Badge>
        </div>

        {/* Workflow name */}
        <div className="text-sm text-slate-300">
          <span className="text-slate-400">Workflow:</span> {workflowName}
        </div>

        {/* Progress bar */}
        {status === 'running' && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-400">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="flex items-start space-x-2 p-2 bg-red-900/20 border border-red-500/30 rounded">
            <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-red-300">{error}</div>
          </div>
        )}

        {/* Node results summary */}
        {nodeResults.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-slate-400 font-medium">Step Results:</div>
            <div className="space-y-1">
              {nodeResults.map((nodeResult: any, index: number) => (
                <div key={nodeResult.node_id} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${nodeResult.status === 'completed' ? 'bg-green-400' :
                      nodeResult.status === 'failed' ? 'bg-red-400' :
                        nodeResult.status === 'running' ? 'bg-blue-400 animate-pulse' :
                          'bg-slate-400'
                      }`} />
                    <span className="text-slate-300">{nodeResult.connector_name}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    {nodeResult.duration_ms && (
                      <span className="text-slate-500">{nodeResult.duration_ms}ms</span>
                    )}
                    <Badge variant="outline" className={`text-xs h-5 ${nodeResult.status === 'completed' ? 'border-green-500/30 text-green-400' :
                      nodeResult.status === 'failed' ? 'border-red-500/30 text-red-400' :
                        nodeResult.status === 'running' ? 'border-blue-500/30 text-blue-400' :
                          'border-slate-500/30 text-slate-400'
                      }`}>
                      {nodeResult.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-700/50">
          <div className="text-xs text-slate-500">
            Execution ID: {executionId.substring(0, 8)}...
          </div>
          <Button size="sm" variant="outline" className="h-6 text-xs border-slate-600">
            <Eye className="w-3 h-3 mr-1" />
            View Details
          </Button>
        </div>
      </div>
    </Card>
  )
}