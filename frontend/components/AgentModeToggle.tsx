'use client'

import { useState } from 'react'
import { Bot, Workflow, Zap, Info } from 'lucide-react'
import { Button } from './ui/button'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip'

interface AgentModeToggleProps {
  mode: 'workflow' | 'react'
  onModeChange: (mode: 'workflow' | 'react') => void
  disabled?: boolean
}

export default function AgentModeToggle({
  mode,
  onModeChange,
  disabled = false
}: AgentModeToggleProps) {
  const [isHovered, setIsHovered] = useState<string | null>(null)

  const modes = [
    {
      id: 'workflow' as const,
      name: 'Workflow Builder',
      description: 'Create structured workflows with visual planning',
      icon: Workflow,
      color: 'from-blue-500 to-cyan-500',
      features: ['Visual workflow design', 'Step-by-step planning', 'Manual execution control']
    },
    {
      id: 'react' as const,
      name: 'ReAct Agent',
      description: 'Intelligent agent that reasons and acts autonomously',
      icon: Bot,
      color: 'from-purple-500 to-pink-500',
      features: ['Autonomous reasoning', 'Multi-tool orchestration', 'Real-time execution']
    }
  ]

  return (
    <TooltipProvider>
      <Card className="p-4 bg-slate-800/50 border-slate-700/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <h3 className="text-sm font-medium text-white">AI Mode</h3>
          </div>
          <Tooltip>
            <TooltipTrigger>
              <Info className="w-4 h-4 text-slate-400 hover:text-white" />
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-xs">Choose between structured workflow building or autonomous AI agent</p>
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {modes.map((modeOption) => {
            const Icon = modeOption.icon
            const isActive = mode === modeOption.id
            const isHovering = isHovered === modeOption.id

            return (
              <Tooltip key={modeOption.id}>
                <TooltipTrigger asChild>
                  <Button
                    variant={isActive ? "default" : "ghost"}
                    size="sm"
                    onClick={() => onModeChange(modeOption.id)}
                    disabled={disabled}
                    onMouseEnter={() => setIsHovered(modeOption.id)}
                    onMouseLeave={() => setIsHovered(null)}
                    className={`
                      relative h-auto p-3 flex flex-col items-center space-y-2 transition-all duration-200
                      ${isActive
                        ? `bg-gradient-to-br ${modeOption.color} text-white shadow-lg`
                        : 'bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white'
                      }
                      ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    {/* Icon */}
                    <div className={`
                      w-8 h-8 rounded-lg flex items-center justify-center transition-all
                      ${isActive
                        ? 'bg-white/20'
                        : 'bg-slate-600/50'
                      }
                    `}>
                      <Icon className="w-4 h-4" />
                    </div>

                    {/* Name */}
                    <div className="text-center">
                      <p className="text-xs font-medium leading-tight">
                        {modeOption.name}
                      </p>
                    </div>

                    {/* Active indicator */}
                    {isActive && (
                      <div className="absolute -top-1 -right-1">
                        <div className="w-3 h-3 bg-green-400 rounded-full border-2 border-slate-800" />
                      </div>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  <div className="space-y-2">
                    <p className="font-medium">{modeOption.name}</p>
                    <p className="text-sm text-slate-300">{modeOption.description}</p>
                    <div className="space-y-1">
                      {modeOption.features.map((feature, index) => (
                        <div key={index} className="flex items-center space-x-1">
                          <div className="w-1 h-1 bg-slate-400 rounded-full" />
                          <span className="text-xs text-slate-400">{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            )
          })}
        </div>

        {/* Mode description */}
        <div className="mt-3 pt-3 border-t border-slate-700/50">
          <div className="flex items-center space-x-2">
            <Badge
              variant="secondary"
              className={`
                text-xs bg-gradient-to-r ${modes.find(m => m.id === mode)?.color} text-white
              `}
            >
              {mode === 'workflow' ? 'Structured' : 'Autonomous'}
            </Badge>
            <p className="text-xs text-slate-400">
              {modes.find(m => m.id === mode)?.description}
            </p>
          </div>
        </div>
      </Card>
    </TooltipProvider>
  )
}