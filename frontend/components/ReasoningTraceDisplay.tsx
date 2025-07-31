'use client'

import { useState } from 'react'
import {
  Brain,
  Zap,
  Eye,
  XCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible'
import { ReasoningStep } from '../lib/types'

interface ReasoningTraceDisplayProps {
  reasoningTrace: ReasoningStep[]
  className?: string
}

export default function ReasoningTraceDisplay({
  reasoningTrace,
  className = ""
}: ReasoningTraceDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!reasoningTrace || reasoningTrace.length === 0) {
    return null
  }

  const getStepIcon = (stepType: string) => {
    const lowerType = stepType.toLowerCase()
    if (lowerType.includes('thought') || lowerType.includes('think')) {
      return <Brain className="w-4 h-4 text-blue-400" />
    } else if (lowerType.includes('action') || lowerType.includes('act')) {
      return <Zap className="w-4 h-4 text-yellow-400" />
    } else if (lowerType.includes('observation') || lowerType.includes('observe')) {
      return <Eye className="w-4 h-4 text-green-400" />
    } else if (lowerType.includes('error') || lowerType.includes('fail')) {
      return <XCircle className="w-4 h-4 text-red-400" />
    } else {
      return <AlertCircle className="w-4 h-4 text-gray-400" />
    }
  }

  const getStepColor = (stepType: string) => {
    const lowerType = stepType.toLowerCase()
    if (lowerType.includes('thought') || lowerType.includes('think')) {
      return 'border-l-blue-400 bg-blue-500/5'
    } else if (lowerType.includes('action') || lowerType.includes('act')) {
      return 'border-l-yellow-400 bg-yellow-500/5'
    } else if (lowerType.includes('observation') || lowerType.includes('observe')) {
      return 'border-l-green-400 bg-green-500/5'
    } else if (lowerType.includes('error') || lowerType.includes('fail')) {
      return 'border-l-red-400 bg-red-500/5'
    } else {
      return 'border-l-gray-400 bg-gray-500/5'
    }
  }

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString()
  }

  return (
    <Card className={`bg-slate-800/30 border-slate-700/50 ${className}`}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-4 hover:bg-slate-700/30"
          >
            <div className="flex items-center space-x-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-white">
                Reasoning Trace ({reasoningTrace.length} steps)
              </span>
              <Badge variant="secondary" className="bg-purple-500/20 text-purple-300 text-xs">
                AI Thinking
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
            {reasoningTrace.map((step, index) => (
              <div
                key={index}
                className={`border-l-2 pl-4 py-3 rounded-r-lg ${getStepColor(step.step_type)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getStepIcon(step.step_type)}
                    <span className="text-sm font-medium text-white capitalize">
                      Step {step.step_number}: {step.step_type}
                    </span>
                    {step.tool_name && (
                      <Badge variant="outline" className="text-xs border-slate-600 text-slate-300">
                        {step.tool_name}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center space-x-1 text-xs text-slate-400">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimestamp(step.timestamp)}</span>
                  </div>
                </div>

                <p className="text-sm text-slate-200 leading-relaxed mb-2">
                  {step.content}
                </p>

                {step.action_input && (
                  <div className="mt-2 p-2 bg-slate-900/50 rounded border border-slate-700/50">
                    <p className="text-xs font-medium text-slate-300 mb-1">Action Input:</p>
                    <pre className="text-xs text-slate-400 whitespace-pre-wrap">
                      {JSON.stringify(step.action_input, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}

            {/* Summary */}
            <div className="mt-4 p-3 bg-slate-900/30 rounded-lg border border-slate-700/30">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Total reasoning steps: {reasoningTrace.length}</span>
                <div className="flex items-center space-x-4">
                  <span className="flex items-center space-x-1">
                    <Brain className="w-3 h-3" />
                    <span>{reasoningTrace.filter(s => s.step_type.toLowerCase().includes('thought')).length} thoughts</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Zap className="w-3 h-3" />
                    <span>{reasoningTrace.filter(s => s.step_type.toLowerCase().includes('action')).length} actions</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Eye className="w-3 h-3" />
                    <span>{reasoningTrace.filter(s => s.step_type.toLowerCase().includes('observation')).length} observations</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}