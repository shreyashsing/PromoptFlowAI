'use client'

import { useCallback, useMemo, useState, useEffect } from 'react'
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
  NodeChange,
  EdgeChange,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { WorkflowPlan, WorkflowNode as WorkflowNodeType } from '@/lib/types'
import { updateWorkflow, createWorkflow } from '@/lib/api'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import ConnectorConfigModal from './ConnectorConfigModal'
import {
  Workflow,
  Play,
  Pause,
  Clock,
  CheckCircle,
  XCircle,
  GitBranch,
  Layers,
  Settings,
  Trash2,
  Copy,
  Download,
  Upload,
  RefreshCw,
  Zap,
  Eye,
  Edit3,
  AlertCircle
} from 'lucide-react'
import { workflowAPI } from '@/lib/api'

interface InteractiveWorkflowVisualizationProps {
  workflow: WorkflowPlan | null
  onWorkflowUpdate?: (workflow: WorkflowPlan) => void
  onExecuteWorkflow?: (workflowId: string) => void
}

// Custom node component for clean, minimal design
const CustomWorkflowNode = ({ data, selected }: { data: any, selected: boolean }) => {
  const [isHovered, setIsHovered] = useState(false)

  const getConnectorIcon = (connectorName: string) => {
    if (connectorName.includes('gmail')) return '📧'
    if (connectorName.includes('perplexity')) return '🔍'
    if (connectorName.includes('sheets')) return '📊'
    if (connectorName.includes('webhook')) return '🔗'
    if (connectorName.includes('http')) return '🌐'
    if (connectorName.includes('summarizer')) return '📝'
    return '⚡'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'failed': return 'bg-red-500'
      case 'running': return 'bg-blue-500'
      default: return 'bg-gray-400'
    }
  }

  return (
    <div
      className={`relative bg-white rounded-lg border-2 transition-all duration-200 min-w-[180px] shadow-sm cursor-pointer ${selected
        ? 'border-blue-500 shadow-lg'
        : isHovered
          ? 'border-gray-400 shadow-md'
          : 'border-gray-200'
        }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      title="Click to configure this connector"
    >
      {/* Status indicator */}
      <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${getStatusColor(data.status)}`} />

      {/* Node content */}
      <div className="p-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center text-lg">
            {getConnectorIcon(data.connector_name)}
          </div>
          <div className="flex-1">
            <div className="font-medium text-gray-900 text-sm">
              {data.connector_name.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
            </div>
            <div className="text-xs text-gray-500">
              {data.connector_name}
            </div>
          </div>
        </div>

        {/* Configuration status */}
        {data.parameters && Object.keys(data.parameters).length > 0 ? (
          <div className="flex items-center gap-1 text-xs text-green-600">
            <CheckCircle className="w-3 h-3" />
            <span>Configured</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-xs text-orange-600">
            <AlertCircle className="w-3 h-3" />
            <span>Click to configure</span>
          </div>
        )}
      </div>

      {/* Hover overlay */}
      {isHovered && (
        <div className="absolute inset-0 bg-blue-50 bg-opacity-50 rounded-lg flex items-center justify-center">
          <div className="bg-blue-600 text-white px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1">
            <Settings className="w-3 h-3" />
            Click to configure
          </div>
        </div>
      )}
    </div>
  )
}

const nodeTypes = {
  workflowNode: CustomWorkflowNode,
}

export default function InteractiveWorkflowVisualization({
  workflow,
  onWorkflowUpdate,
  onExecuteWorkflow
}: InteractiveWorkflowVisualizationProps) {
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionStatus, setExecutionStatus] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [configNodeId, setConfigNodeId] = useState<string | null>(null)

  // Convert workflow data to react-flow format
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!workflow) {
      return { nodes: [], edges: [] }
    }

    const nodes: Node[] = workflow.nodes.map((node) => ({
      id: node.id,
      type: 'workflowNode',
      position: node.position,
      data: {
        nodeId: node.id,
        connector_name: node.connector_name,
        parameters: node.parameters,
        status: node.status || 'pending',
        executionInfo: node.executionInfo,
        onConfigure: (nodeId: string) => {
          setConfigNodeId(nodeId);
          setConfigModalOpen(true);
        },
      },
    }))

    const edges: Edge[] = workflow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.condition || '',
      type: 'smoothstep',
      style: {
        stroke: '#6b7280',
        strokeWidth: 2,
      },
      labelStyle: {
        fontSize: '11px',
        fontWeight: 500,
        color: '#374151',
        background: 'white',
        padding: '2px 6px',
        borderRadius: '4px',
        border: '1px solid #d1d5db',
      },
    }))

    return { nodes, edges }
  }, [workflow])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Update nodes when workflow changes
  useEffect(() => {
    if (workflow) {
      const updatedNodes = workflow.nodes.map((node) => ({
        id: node.id,
        type: 'workflowNode',
        position: node.position,
        data: {
          nodeId: node.id,
          connector_name: node.connector_name,
          parameters: node.parameters,
          status: node.status || 'pending',
          executionInfo: node.executionInfo,
          onConfigure: (nodeId: string) => {
            setConfigNodeId(nodeId);
            setConfigModalOpen(true);
          },
        },
      }))
      setNodes(updatedNodes)
    }
  }, [workflow, setNodes])

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const handleExecuteWorkflow = async () => {
    if (!workflow || !onExecuteWorkflow) return

    setIsExecuting(true)
    setExecutionStatus('starting')

    try {
      const executionResult = await workflowAPI.executeWorkflow(workflow.id)
      const executionId = executionResult.execution_id

      setExecutionStatus('running')

      // Poll for execution status
      const pollStatus = setInterval(async () => {
        try {
          const status = await workflowAPI.getExecutionStatus(executionId)

          // Update node statuses based on execution progress
          if (status.node_results && status.node_results.length > 0) {
            const updatedNodes = nodes.map(node => {
              const nodeResult = status.node_results.find((nr: any) => nr.node_id === node.id)
              if (nodeResult) {
                return {
                  ...node,
                  data: {
                    ...node.data,
                    status: nodeResult.status,
                    executionInfo: {
                      duration_ms: nodeResult.duration_ms,
                      error: nodeResult.error
                    }
                  }
                }
              }
              return node
            })
            setNodes(updatedNodes)
          }

          // Check if execution is complete
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            clearInterval(pollStatus)
            setIsExecuting(false)
            setExecutionStatus(status.status)

            if (status.status === 'completed') {
              console.log('Workflow completed successfully!')
            } else if (status.status === 'failed') {
              // Check for specific error or failed nodes
              if (status.error) {
                console.error('Workflow execution failed:', status.error)
              } else if (status.node_results) {
                const failedNodes = status.node_results.filter((nr: any) => nr.status === 'failed')
                if (failedNodes.length > 0) {
                  console.error('Workflow execution failed: Some nodes failed:', failedNodes.map((n: any) => `${n.connector_name}: ${n.error}`).join(', '))
                } else {
                  console.error('Workflow execution failed: Unknown reason')
                }
              } else {
                console.error('Workflow execution failed: Unknown reason')
              }
            }
          }

        } catch (error) {
          console.error('Error polling execution status:', error)
          clearInterval(pollStatus)
          setIsExecuting(false)
          setExecutionStatus('failed')
        }
      }, 2000)

      // Clear polling after 5 minutes as safety measure
      setTimeout(() => {
        clearInterval(pollStatus)
        if (isExecuting) {
          setIsExecuting(false)
          setExecutionStatus('timeout')
        }
      }, 300000)

    } catch (error) {
      console.error('Error executing workflow:', error)
      setIsExecuting(false)
      setExecutionStatus('failed')
    }
  }

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node.id)
    // Open configuration modal on single click
    setConfigNodeId(node.id);
    setConfigModalOpen(true);
  }, [])

  const handleNodeDoubleClick = useCallback((event: React.MouseEvent, node: Node) => {
    // Also handle double-click for configuration
    setConfigNodeId(node.id);
    setConfigModalOpen(true);
  }, [])

  const handleConfigSave = useCallback(async (nodeId: string, config: any) => {
    if (!workflow || !onWorkflowUpdate) return;

    const updatedWorkflow = {
      ...workflow,
      nodes: workflow.nodes.map(node =>
        node.id === nodeId
          ? { ...node, parameters: config }
          : node
      )
    };

    try {
      // Save to database first
      if (workflow.id) {
        console.log('Saving workflow configuration...', workflow.id);
        
        await updateWorkflow(workflow.id, updatedWorkflow);
        console.log('Workflow configuration saved to database successfully');
        
        // Show success feedback to user
        // Create a temporary toast-like notification
        const notification = document.createElement('div');
        notification.innerHTML = '✅ Configuration saved successfully!';
        notification.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: #10B981;
          color: white;
          padding: 12px 20px;
          border-radius: 8px;
          z-index: 9999;
          font-weight: 500;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          transition: all 0.3s ease;
        `;
        document.body.appendChild(notification);
        setTimeout(() => {
          notification.style.opacity = '0';
          setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
      } else {
        console.warn('No workflow ID found, skipping database save');
      }
      
      // Update local state regardless of database save status
      onWorkflowUpdate(updatedWorkflow);
      setConfigModalOpen(false);
      setConfigNodeId(null);
    } catch (error) {
      console.error('Failed to save workflow configuration:', error);
      
      if (error instanceof Error && error.message.includes('404')) {
        // Workflow not found - try to create it first
                  console.log('Creating missing workflow...');
          try {
            await createWorkflow(updatedWorkflow);
            await updateWorkflow(workflow.id, updatedWorkflow);
            console.log('Workflow created and configuration saved');
          
          // Show success feedback
          const notification = document.createElement('div');
          notification.innerHTML = '✅ Workflow created and configuration saved!';
          notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10B981;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 9999;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s ease;
          `;
          document.body.appendChild(notification);
          setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => document.body.removeChild(notification), 300);
          }, 3000);
          
          // Update local state
          onWorkflowUpdate(updatedWorkflow);
          setConfigModalOpen(false);
          setConfigNodeId(null);
          
        } catch (createError) {
          console.error('Failed to create workflow:', createError);
          console.warn('Saving configuration locally only');
          onWorkflowUpdate(updatedWorkflow);
          setConfigModalOpen(false);
          setConfigNodeId(null);
          
          // Show warning to user
          const notification = document.createElement('div');
          notification.innerHTML = '⚠️ Configuration saved locally (couldn\'t sync to database)';
          notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #F59E0B;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 9999;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s ease;
          `;
          document.body.appendChild(notification);
          setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => document.body.removeChild(notification), 300);
          }, 4000);
        }
      } else {
        // Show error feedback for other errors
        alert('Failed to save configuration. Please try again.');
      }
    }
  }, [workflow, onWorkflowUpdate])

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
    <div className="h-[calc(100vh-16rem)] relative bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        className="bg-gray-50"
      >
        <Controls className="bg-white border border-gray-200 rounded-lg shadow-sm" />
        <MiniMap
          nodeColor="#3b82f6"
          maskColor="rgba(255, 255, 255, 0.8)"
          position="top-right"
          className="bg-white border border-gray-200 rounded-lg shadow-sm"
        />
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#e5e7eb"
        />

        {/* Clean Control Panel */}
        <Panel position="top-left">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 min-w-[280px]">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <Workflow className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{workflow.name}</h3>
                <p className="text-sm text-gray-500">Workflow automation</p>
              </div>
            </div>

            <div className="flex items-center gap-2 mb-4">
              <div className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${workflow.status === 'active' ? 'bg-green-100 text-green-800' :
                workflow.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                {getStatusIcon(workflow.status)}
                {workflow.status}
              </div>
              {executionStatus && (
                <div className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {executionStatus}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleExecuteWorkflow}
                disabled={isExecuting || workflow.status !== 'active'}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isExecuting ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {isExecuting ? 'Running...' : 'Execute'}
              </button>

              <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                <Settings className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>
        </Panel>
      </ReactFlow>

      {/* Configuration Modal */}
      {configModalOpen && configNodeId && workflow && (
        <ConnectorConfigModal
          isOpen={configModalOpen}
          onClose={() => {
            setConfigModalOpen(false);
            setConfigNodeId(null);
          }}
          node={workflow.nodes.find(n => n.id === configNodeId) || null}
          onSave={async (nodeId: string, parameters: Record<string, any>) => {
            await handleConfigSave(nodeId, parameters);
          }}
        />
      )}
    </div>
  )
}