'use client'

import { useState, useEffect } from 'react'
import { 
  Bot, 
  Brain, 
  Zap, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Loader2,
  Eye,
  Wrench
} from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'
import { ReactAgentStatus, ReasoningStep, ToolCall } from '../lib/types'

interface ReactAgentStatusProps {
  status: ReactAgentStatus
  reasoningTrace?: ReasoningStep[]
  toolCalls?: ToolCall[]
  className?: string
}

export default function ReactAgentStatusDisplay({ 
  status, 
  reasoningTrace = [], 
  toolCalls = [],
  className = ""
}: ReactAgentStatusProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (status.current_step && status.total_steps) {
      setProgress((status.current_step / status.total_steps) * 100)
    } else {
      setProgress(status.status === 'completed' ? 100 : 0)
    }
  }, [status])

  const getStatusIcon = () => {
    const lowerStatus = status.status.toLowerCase()
    if (lowerStatus.includes('think')) {
      return <Brain className="w-4 h-4 text-blue-400 animate-pulse" />
    } else if (lowerStatus.includes('act')) {
      return <Zap className="w-4 h-4 text-yellow-400 animate-bounce" />
    } else if (lowerStatus.includes('observ')) {
      return <Eye className="w-4 h-4 text-green-400" />
    } else if (lowerStatus.includes('complet')) {
      return <CheckCircle className="w-4 h-4 text-green-400" />
    } else if (lowerStatus.includes('error') || lowerStatus.includes('fail')) {
      return <XCircle className="w-4 h-4 text-red-400" />
    } else {
      return <Bot className="w-4 h-4 text-slate-400" />
    }
  }

  const getStatusColor = () => {
    const lowerStatus = status.status.toLowerCase()
    if (lowerStatus.includes('think')) {
      return 'bg-blue-500/20 border-blue-500/50 text-blue-300'
    } else if (lowerStatus.includes('act')) {
      return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-300'
    } else if (lowerStatus.includes('observ')) {
      return 'bg-green-500/20 border-green-500/50 text-green-300'
    } else if (lowerStatus.includes('complet')) {
      return 'bg-green-500/20 border-green-500/50 text-green-300'
    } else if (lowerStatus.includes('error') || lowerStatus.includes('fail')) {
      return 'bg-red-500/20 border-red-500/50 text-red-300'
    } else {
      return 'bg-slate-500/20 border-slate-500/50 text-slate-300'
    }
  }

  const getStatusMessage = () => {
    if (status.message) return status.message
    
    const lowerStatus = status.status.toLowerCase()
    if (lowerStatus.includes('think')) {
      return 'Analyzing your request and planning next steps...'
    } else if (lowerStatus.includes('act')) {
      return status.current_tool ? `Using ${status.current_tool}...` : 'Executing action...'
    } else if (lowerStatus.includes('observ')) {
      return 'Processing results and determining next action...'
    } else if (lowerStatus.includes('complet')) {
      return 'Task completed successfully!'
    } else if (lowerStatus.includes('error') || lowerStatus.includes('fail')) {
      return 'An error occurred during processing'
    } else {
      return 'Ready to assist'
    }
  }

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString()
  }

  if (status.status === 'idle') {
    return null
  }

  return (
    <Card className={`p-4 ${getStatusColor()} ${className}`}>
      {/* Status Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="text-sm font-medium capitalize">
            {status.status === 'acting' && status.current_tool 
              ? `Using ${status.current_tool}` 
              : status.status
            }
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          {status.current_step && status.total_steps && (
            <Badge variant="secondary" className="text-xs">
              {status.current_step}/{status.total_steps}
            </Badge>
          )}
          <span className="text-xs opacity-70">
            {formatTimestamp(status.timestamp)}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      {status.total_steps && status.total_steps > 1 && (
        <div className="mb-3">
          <Progress value={progress} className="h-2" />
        </div>
      )}

      {/* Status Message */}
      <p className="text-sm opacity-90 mb-3">
        {getStatusMessage()}
      </p>

      {/* Current Reasoning Step */}
      {reasoningTrace.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium opacity-70">Current Reasoning:</h4>
          <div className="bg-black/20 rounded-lg p-3">
            {reasoningTrace.slice(-1).map((step, index) => (
              <div key={index} className="flex items-start space-x-2">
                <div className="flex-shrink-0 mt-1">
                  {step.step_type.toLowerCase().includes('thought') && <Brain className="w-3 h-3" />}
                  {step.step_type.toLowerCase().includes('action') && <Zap className="w-3 h-3" />}
                  {step.step_type.toLowerCase().includes('observation') && <Eye className="w-3 h-3" />}
                  {step.step_type.toLowerCase().includes('error') && <XCircle className="w-3 h-3" />}
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium capitalize opacity-70">
                    {step.step_type}
                  </p>
                  <p className="text-sm">{step.content}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Tool Calls */}
      {toolCalls.length > 0 && status.status === 'acting' && (
        <div className="mt-3 space-y-2">
          <h4 className="text-xs font-medium opacity-70">Tool Activity:</h4>
          <div className="space-y-1">
            {toolCalls.slice(-3).map((call, index) => (
              <div key={index} className="flex items-center space-x-2 text-xs">
                <Wrench className="w-3 h-3" />
                <span className="font-medium">{call.tool_name}</span>
                {call.error ? (
                  <Badge variant="destructive" className="text-xs">Error</Badge>
                ) : call.result ? (
                  <Badge variant="secondary" className="text-xs">Complete</Badge>
                ) : (
                  <Loader2 className="w-3 h-3 animate-spin" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}