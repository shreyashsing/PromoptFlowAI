'use client'

import { useState } from 'react'
import { 
  Wrench, 
  CheckCircle, 
  XCircle, 
  Clock, 
  ChevronDown, 
  ChevronRight,
  ExternalLink,
  Copy,
  Eye,
  EyeOff
} from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible'
import { ToolCall } from '../lib/types'

interface ToolCallsDisplayProps {
  toolCalls: ToolCall[]
  className?: string
}

export default function ToolCallsDisplay({ 
  toolCalls, 
  className = "" 
}: ToolCallsDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedCalls, setExpandedCalls] = useState<Set<number>>(new Set())

  if (!toolCalls || toolCalls.length === 0) {
    return null
  }

  const toggleCallExpansion = (index: number) => {
    const newExpanded = new Set(expandedCalls)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedCalls(newExpanded)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const getToolIcon = (toolName: string) => {
    // You can customize icons based on tool names
    switch (toolName.toLowerCase()) {
      case 'gmail':
        return '📧'
      case 'google_sheets':
        return '📊'
      case 'perplexity':
        return '🔍'
      case 'text_summarizer':
        return '📝'
      default:
        return '🔧'
    }
  }

  const formatExecutionTime = (timeMs: number) => {
    if (timeMs < 1000) {
      return `${timeMs}ms`
    } else {
      return `${(timeMs / 1000).toFixed(1)}s`
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const totalExecutionTime = toolCalls.reduce((sum, call) => sum + call.execution_time, 0)
  const successfulCalls = toolCalls.filter(call => !call.error).length
  const failedCalls = toolCalls.filter(call => call.error).length

  return (
    <Card className={`bg-slate-800/30 border-slate-700/50 ${className}`}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-4 hover:bg-slate-700/30"
          >
            <div className="flex items-center space-x-2">
              <Wrench className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-medium text-white">
                Tool Usage ({toolCalls.length} calls)
              </span>
              <div className="flex items-center space-x-1">
                {successfulCalls > 0 && (
                  <Badge variant="secondary" className="bg-green-500/20 text-green-300 text-xs">
                    {successfulCalls} success
                  </Badge>
                )}
                {failedCalls > 0 && (
                  <Badge variant="secondary" className="bg-red-500/20 text-red-300 text-xs">
                    {failedCalls} failed
                  </Badge>
                )}
              </div>
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
            {toolCalls.map((call, index) => {
              const isCallExpanded = expandedCalls.has(index)
              
              return (
                <Card 
                  key={index}
                  className={`p-3 ${
                    call.error 
                      ? 'bg-red-500/10 border-red-500/30' 
                      : 'bg-green-500/10 border-green-500/30'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{getToolIcon(call.tool_name)}</span>
                      <div>
                        <h4 className="text-sm font-medium text-white">
                          {call.tool_name}
                        </h4>
                        <div className="flex items-center space-x-2 text-xs text-slate-400">
                          <Clock className="w-3 h-3" />
                          <span>{formatExecutionTime(call.execution_time)}</span>
                          <span>•</span>
                          <span>{formatTimestamp(call.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {call.error ? (
                        <XCircle className="w-4 h-4 text-red-400" />
                      ) : (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleCallExpansion(index)}
                        className="h-6 w-6 p-0"
                      >
                        {isCallExpanded ? (
                          <EyeOff className="w-3 h-3" />
                        ) : (
                          <Eye className="w-3 h-3" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {isCallExpanded && (
                    <div className="space-y-3 mt-3 pt-3 border-t border-slate-700/50">
                      {/* Parameters */}
                      {call.parameters && Object.keys(call.parameters).length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="text-xs font-medium text-slate-300">Parameters</h5>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(JSON.stringify(call.parameters, null, 2))}
                              className="h-6 w-6 p-0"
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <div className="p-2 bg-slate-900/50 rounded border border-slate-700/50">
                            <pre className="text-xs text-slate-400 whitespace-pre-wrap">
                              {JSON.stringify(call.parameters, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Result */}
                      {call.result && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="text-xs font-medium text-slate-300">Result</h5>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(JSON.stringify(call.result, null, 2))}
                              className="h-6 w-6 p-0"
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <div className="p-2 bg-slate-900/50 rounded border border-slate-700/50">
                            <pre className="text-xs text-slate-400 whitespace-pre-wrap">
                              {JSON.stringify(call.result, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Error */}
                      {call.error && (
                        <div>
                          <h5 className="text-xs font-medium text-red-300 mb-2">Error</h5>
                          <div className="p-2 bg-red-900/20 rounded border border-red-500/30">
                            <p className="text-xs text-red-400">{call.error}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              )
            })}
            
            {/* Summary */}
            <div className="mt-4 p-3 bg-slate-900/30 rounded-lg border border-slate-700/30">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-slate-400">
                <div className="text-center">
                  <p className="font-medium text-white">{toolCalls.length}</p>
                  <p>Total Calls</p>
                </div>
                <div className="text-center">
                  <p className="font-medium text-green-400">{successfulCalls}</p>
                  <p>Successful</p>
                </div>
                <div className="text-center">
                  <p className="font-medium text-red-400">{failedCalls}</p>
                  <p>Failed</p>
                </div>
                <div className="text-center">
                  <p className="font-medium text-orange-400">{formatExecutionTime(totalExecutionTime)}</p>
                  <p>Total Time</p>
                </div>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}