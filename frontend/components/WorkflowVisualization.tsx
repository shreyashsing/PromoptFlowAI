'use client'

import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { WorkflowPlan } from '../lib/types'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Workflow, Play, Pause, Clock, CheckCircle, XCircle, GitBranch, Layers } from 'lucide-react'

interface WorkflowVisualizationProps {
  workflow: WorkflowPlan | null
}

const nodeTypes = {
  // We can add custom node types here if needed
}

export default function WorkflowVisualization({ workflow }: WorkflowVisualizationProps) {
  // Convert workflow data to react-flow format
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!workflow) {
      return { nodes: [], edges: [] }
    }

    const nodes: Node[] = workflow.nodes.map((node) => ({
      id: node.id,
      type: 'default',
      position: node.position,
      data: {
        label: (
          <div className="text-center p-2">
            <div className="font-semibold text-sm text-white mb-1">{node.connector_name}</div>
            <div className="text-xs text-slate-300">
              {Object.keys(node.parameters).length > 0 && (
                <div className="space-y-1">
                  {Object.entries(node.parameters).slice(0, 2).map(([key, value]) => (
                    <div key={key} className="truncate">
                      <span className="text-slate-400">{key}:</span> {String(value).substring(0, 15)}
                      {String(value).length > 15 ? '...' : ''}
                    </div>
                  ))}
                  {Object.keys(node.parameters).length > 2 && (
                    <div className="text-slate-400">+{Object.keys(node.parameters).length - 2} more</div>
                  )}
                </div>
              )}
            </div>
          </div>
        ),
      },
      style: {
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        border: '2px solid #475569',
        borderRadius: '12px',
        padding: '8px',
        minWidth: '180px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      },
    }))

    const edges: Edge[] = workflow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.condition || '',
      type: 'smoothstep',
      style: {
        stroke: '#3b82f6',
        strokeWidth: 3,
        filter: 'drop-shadow(0 0 6px rgba(59, 130, 246, 0.4))',
      },
      labelStyle: {
        fontSize: '11px',
        fontWeight: 600,
        color: '#e2e8f0',
        background: 'rgba(15, 23, 42, 0.8)',
        padding: '2px 6px',
        borderRadius: '4px',
        border: '1px solid #475569',
      },
    }))

    return { nodes, edges }
  }, [workflow])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <Play className="w-3 h-3" />
      case 'paused': return <Pause className="w-3 h-3" />
      case 'completed': return <CheckCircle className="w-3 h-3" />
      case 'failed': return <XCircle className="w-3 h-3" />
      default: return <Clock className="w-3 h-3" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'paused': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'completed': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30'
    }
  }

  if (!workflow) {
    return (
      <div className="h-[calc(100vh-16rem)] flex items-center justify-center">
        <div className="text-center space-y-6">
          <div className="relative">
            <div className="w-24 h-24 bg-gradient-to-br from-slate-700 to-slate-800 rounded-2xl flex items-center justify-center mb-4 mx-auto">
              <Workflow className="w-12 h-12 text-slate-400" />
            </div>
            <div className="absolute -top-2 -right-2 w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-slate-300" />
            </div>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-xl font-semibold text-slate-300">No workflow yet</h3>
            <p className="text-slate-500 max-w-sm">
              Start a conversation with the AI assistant to generate your first automation workflow
            </p>
          </div>

          <div className="flex items-center justify-center space-x-4 text-sm text-slate-600">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span>Ready to create</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-16rem)] relative">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 to-slate-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          className="bg-transparent"
        >
          <Controls 
            className="bg-slate-800/80 border-slate-700"
          />
          <MiniMap 
            nodeColor="#3b82f6"
            maskColor="rgba(15, 23, 42, 0.8)"
            position="top-right"
            className="bg-slate-800/80 border border-slate-700 rounded-lg"
          />
          <Background 
            variant={BackgroundVariant.Dots} 
            gap={20} 
            size={1}
            color="#475569"
            className="opacity-30"
          />
        </ReactFlow>
      </div>
      
      {/* Workflow Info Panel */}
      <Card className="absolute top-4 left-4 bg-slate-800/90 border-slate-700/50 backdrop-blur-sm max-w-xs">
        <div className="p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                <Layers className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-white">{workflow.name}</h3>
                <p className="text-xs text-slate-400 mt-1">{workflow.description}</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-slate-300">{workflow.nodes.length} steps</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-slate-300">{workflow.triggers.length} triggers</span>
            </div>
          </div>

          <Badge className={`${getStatusColor(workflow.status)} flex items-center gap-1 w-fit`}>
            {getStatusIcon(workflow.status)}
            {workflow.status}
          </Badge>
        </div>
      </Card>
    </div>
  )
}