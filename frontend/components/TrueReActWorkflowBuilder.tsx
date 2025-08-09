'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { createClient } from '@supabase/supabase-js';
import {
  CheckCircle, Play, Settings,
  Loader2, Clock, Eye, Layers, Mail, Globe,
  FileText, Webhook, Database, Sparkles, Brain, Code
} from 'lucide-react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { workflowReactAPI } from '@/lib/api';
import StringLikeConnectorModal from '@/components/StringLikeConnectorModal';
import { GoogleDriveConnectorModal } from '@/components/connectors/google_drive';
import { NotionConnectorModal } from '@/components/connectors/notion';
import { YouTubeConnectorModal } from '@/components/connectors/youtube';
import { CodeConnectorModal } from '@/components/connectors/code';
import { AirtableConnectorModal } from '@/components/connectors/airtable';
import { GmailConnectorModal } from '@/components/connectors/gmail';

import { GoogleTranslateConnectorModal } from '@/components/connectors/google_translate';

interface WorkflowStep {
  connector_name: string;
  purpose: string;
  parameters: Record<string, any>;
  config?: Record<string, any>;
}

interface Workflow {
  id?: string;
  name?: string;
  description?: string;
  steps: WorkflowStep[];
  status?: string;
  total_steps?: number;
}

interface TrueReActResponse {
  success: boolean;
  session_id: string;
  message: string;
  workflow?: Workflow;
  reasoning_trace: string[];
  ui_updates: Array<{
    timestamp: string;
    update: {
      type: string;
      message?: string;
      connector_name?: string;
      reasoning?: string;
      step_number?: number;
      status?: string;
    };
  }>;
  error?: string;
  // Conversational planning fields
  phase?: 'planning' | 'completed';
  plan?: any;
  awaiting_approval?: boolean;
}

interface ReActStep {
  id: string;
  type: 'reasoning' | 'action' | 'observation' | 'connector_highlight' | 'step_completed';
  title: string;
  content: string;
  timestamp: Date;
  status: 'active' | 'completed' | 'failed' | 'info';
  connector_name?: string;
  step_number?: number;
}

// Enhanced WorkflowNode with ReAct status and proper handles
const ReActWorkflowNode = ({ data, id }: { data: any; id: string }) => {
  const getConnectorIcon = (connectorName: string) => {
    switch (connectorName?.toLowerCase()) {
      case 'gmail_connector': return <Mail className="w-5 h-5" />;
      case 'google_sheets': return <Database className="w-5 h-5" />;
      case 'perplexity_search': return <Globe className="w-5 h-5" />;
      case 'text_summarizer': return <FileText className="w-5 h-5" />;
      case 'webhook': return <Webhook className="w-5 h-5" />;
      case 'http_request': return <Globe className="w-5 h-5" />;
      case 'code': return <Code className="w-5 h-5" />;
      default: return <Layers className="w-5 h-5" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'working': return 'bg-blue-500 animate-pulse';
      case 'configured': return 'bg-purple-500';
      case 'failed': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const isHighlighted = data.status === 'working';

  return (
    <div
      className={`bg-gray-800 border rounded-lg p-4 min-w-[200px] shadow-lg transition-all duration-300 cursor-pointer relative ${isHighlighted
        ? 'border-blue-400 shadow-blue-400/50 shadow-lg scale-105'
        : 'border-gray-600 hover:border-blue-500 hover:shadow-lg'
        }`}
    >
      {/* React Flow Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id={`${id}-target`}
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />
      <Handle
        type="source"
        position={Position.Right}
        id={`${id}-source`}
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />

      {/* Highlight indicator */}
      {isHighlighted && (
        <div className="absolute -top-2 -right-2 w-4 h-4 bg-blue-500 rounded-full animate-ping" />
      )}

      <div className="flex items-center gap-3 mb-2">
        <div className={`${isHighlighted ? 'text-blue-300' : 'text-blue-400'}`}>
          {getConnectorIcon(data.connector_name)}
        </div>
        <div className="flex-1">
          <h3 className="text-white font-medium text-sm">
            {data.connector_name?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'Unknown Connector'}
          </h3>
        </div>
        <div className={`w-2 h-2 rounded-full ${getStatusColor(data.status)}`} />
      </div>

      {data.purpose && (
        <p className="text-gray-400 text-xs mb-3">{data.purpose}</p>
      )}

      {/* ReAct Agent thinking indicator */}
      {isHighlighted && (
        <div className="flex items-center gap-2 mb-2 p-2 bg-blue-900/30 rounded">
          <Brain className="w-3 h-3 text-blue-400 animate-pulse" />
          <span className="text-xs text-blue-300">Agent is working...</span>
        </div>
      )}

      {data.parameters && Object.keys(data.parameters).length > 0 && (
        <div className="space-y-1">
          {Object.entries(data.parameters).slice(0, 2).map(([key, value]: [string, any]) => (
            <div key={key} className="flex items-center gap-2 text-xs">
              <span className="text-gray-500">{key}:</span>
              <span className="text-gray-300 truncate">{String(value)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500 mt-3">
        <span>{data.status || 'pending'}</span>
        {isHighlighted ? (
          <Sparkles className="w-3 h-3 text-blue-400 animate-pulse" />
        ) : (
          <div className="flex items-center gap-1">
            <Settings className="w-3 h-3 opacity-70 hover:opacity-100 transition-opacity" />
            <span className="text-xs opacity-70">Click to configure</span>
          </div>
        )}
      </div>
    </div>
  );
};

const nodeTypes = {
  reactWorkflowNode: ReActWorkflowNode,
};

export default function TrueReActWorkflowBuilder() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [reactSteps, setReActSteps] = useState<ReActStep[]>([]);
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null);
  const [progress, setProgress] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);

  // Use shared Supabase client to avoid multiple instances warning
  const supabase = React.useMemo(() => createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  ), []);

  // Conversational planning state
  const [currentPlan, setCurrentPlan] = useState<any>(null);
  const [awaitingApproval, setAwaitingApproval] = useState(false);
  const [planPhase, setPlanPhase] = useState<'initial' | 'planning' | 'completed'>('initial');

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Connector configuration modal state
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);



  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Handle node click to open configuration
  const handleNodeClick = useCallback((nodeData: any) => {
    console.log('🔧 Opening config for:', nodeData);
    console.log('🔧 Node parameters:', nodeData.parameters);
    console.log('🔧 Full node data:', JSON.stringify(nodeData, null, 2));
    setSelectedConnector(nodeData.connector_name);

    // Add the node ID to the selected data for proper updates
    const nodeWithId = {
      ...nodeData,
      id: nodeData.connector_name + (currentWorkflow?.steps?.findIndex((step: any) => step.connector_name === nodeData.connector_name) || 0)
    };

    setSelectedNodeData(nodeWithId);
    setConfigModalOpen(true);
  }, [currentWorkflow]);

  // Add ReAct step
  const addReActStep = (
    type: ReActStep['type'],
    title: string,
    content: string,
    status: 'active' | 'completed' | 'failed' | 'info' = 'active',
    connector_name?: string,
    step_number?: number
  ) => {
    const step: ReActStep = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      title,
      content,
      timestamp: new Date(),
      status,
      connector_name,
      step_number,
    };
    console.log('➕ Adding ReAct step:', step);
    setReActSteps(prev => {
      const newSteps = [...prev, step];
      console.log('📋 Total ReAct steps now:', newSteps.length);
      return newSteps;
    });
  };



  // Handle workflow execution
  const handleExecuteWorkflow = useCallback(async () => {
    console.log('🚀 Run Workflow button clicked!');
    console.log('📋 Current workflow:', currentWorkflow);

    if (!currentWorkflow) {
      console.log('❌ No workflow found - cannot execute');
      return;
    }

    console.log('🔄 Setting isExecuting to true');
    setIsExecuting(true);

    try {
      console.log('🎯 Starting real workflow execution');
      addReActStep('reasoning', 'Workflow Execution', 'Starting workflow execution...', 'active');

      // Get session token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('No authentication session found');
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      let workflowId = currentWorkflow.id;

      console.log('🔍 Current workflow ID:', workflowId);
      console.log('🔍 Current workflow:', currentWorkflow);

      // Always save the workflow to ensure it exists in database with correct format
      console.log('💾 Saving workflow to database...');
      addReActStep('action', 'Saving Workflow', 'Saving workflow to database...', 'active');
      
      const workflowPayload = {
        name: currentWorkflow.name || 'ReAct Generated Workflow',
        description: currentWorkflow.description || 'Workflow generated by ReAct agent',
        nodes: (currentWorkflow.steps || []).map((step: WorkflowStep, index: number) => ({
          id: `${step.connector_name}-${index}`,
          connector_name: step.connector_name,
          parameters: step.parameters || {},
          position: { x: index * 250 + 100, y: 100 },
          dependencies: index > 0 ? [`${currentWorkflow.steps[index - 1].connector_name}-${index - 1}`] : []
        })),
        edges: (currentWorkflow.steps || []).length > 1 ? 
          (currentWorkflow.steps || []).slice(1).map((_, index: number) => ({
            id: `edge-${index + 1}`,
            source: `${currentWorkflow.steps[index].connector_name}-${index}`,
            target: `${currentWorkflow.steps[index + 1].connector_name}-${index + 1}`
          })) : [],
        triggers: []
      };
      
      console.log('📤 Sending workflow payload:', JSON.stringify(workflowPayload, null, 2));
      
      const saveResponse = await fetch(`${baseUrl}/api/v1/workflows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(workflowPayload)
      });

      if (!saveResponse.ok) {
        const errorData = await saveResponse.json().catch(() => ({}));
        console.error('❌ Workflow save failed:', errorData);
        console.error('❌ Response status:', saveResponse.status);
        console.error('❌ Response text:', saveResponse.statusText);
        
        // Better error message formatting
        let errorMessage = 'Failed to save workflow';
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage += ': ' + errorData.detail.map((err: any) => 
              typeof err === 'object' ? `${err.loc?.join('.')} - ${err.msg}` : String(err)
            ).join(', ');
          } else {
            errorMessage += ': ' + errorData.detail;
          }
        } else {
          errorMessage += ': ' + saveResponse.statusText;
        }
        
        throw new Error(errorMessage);
      }

      const savedWorkflow = await saveResponse.json();
      workflowId = savedWorkflow.id;
      
      // Update current workflow with the saved ID
      setCurrentWorkflow((prev: Workflow | null) => prev ? { ...prev, id: workflowId } : null);
      
      console.log('✅ Workflow saved with ID:', workflowId);
      addReActStep('action', 'Workflow Saved', `✅ Workflow saved with ID: ${workflowId}`, 'completed');

      // Call the workflow execution API
      console.log(`🌐 Calling workflow execution API: ${baseUrl}/api/v1/workflows/${workflowId}/execute`);
      
      const response = await fetch(`${baseUrl}/api/v1/workflows/${workflowId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          trigger_type: 'manual',
          parameters: {}
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const executionResult = await response.json();
      console.log('✅ Workflow execution started:', executionResult);

      addReActStep('action', 'Execution Started', 
        `🚀 Workflow execution started with ID: ${executionResult.execution_id}`, 'active');

      // Poll for execution status
      const executionId = executionResult.execution_id;
      let isCompleted = false;
      let pollCount = 0;
      const maxPolls = 30; // 5 minutes max (10 second intervals)

      while (!isCompleted && pollCount < maxPolls) {
        console.log(`🔍 Polling execution status (attempt ${pollCount + 1}/${maxPolls})`);
        
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
        
        try {
          const statusResponse = await fetch(`${baseUrl}/api/v1/executions/${executionId}`, {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            }
          });

          if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            console.log('📊 Execution status:', statusData);

            if (statusData.status === 'completed') {
              isCompleted = true;
              addReActStep('step_completed', 'Workflow Complete',
                '🎉 Workflow executed successfully! Check your email for the results.', 'completed');
              
              // Show execution results if available
              if (statusData.result) {
                addReActStep('observation', 'Execution Results',
                  `📋 Results: ${JSON.stringify(statusData.result, null, 2)}`, 'completed');
              }
            } else if (statusData.status === 'failed') {
              isCompleted = true;
              addReActStep('observation', 'Execution Failed',
                `❌ Workflow execution failed: ${statusData.error || 'Unknown error'}`, 'failed');
            } else {
              // Still running, update status
              addReActStep('action', 'Execution Progress',
                `⏳ Workflow is ${statusData.status}... (${statusData.completed_steps || 0}/${statusData.total_steps || 'unknown'} steps)`, 'active');
            }
          }
        } catch (pollError) {
          console.warn('⚠️ Error polling execution status:', pollError);
        }
        
        pollCount++;
      }

      if (!isCompleted) {
        addReActStep('observation', 'Execution Timeout',
          '⏰ Workflow execution is taking longer than expected. Check the monitoring dashboard for updates.', 'active');
      }

    } catch (error) {
      console.error('❌ Workflow execution failed:', error);
      addReActStep('observation', 'Execution Failed',
        `❌ Workflow execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'failed');
    } finally {
      console.log('🔄 Setting isExecuting to false');
      setIsExecuting(false);
      console.log('✅ Workflow execution finished');
    }
  }, [currentWorkflow, addReActStep, supabase]);

  // Convert workflow to React Flow visualization
  const updateWorkflowVisualization = useCallback((workflow: Workflow) => {
    if (!workflow || !workflow.steps) return;

    const flowNodes: Node[] = workflow.steps.map((step: WorkflowStep, index: number) => {
      const nodeId = `${step.connector_name}-${index}`;
      return {
        id: nodeId,
        type: 'reactWorkflowNode',
        position: { x: index * 250 + 100, y: 100 },
        data: {
          ...step,
          status: 'pending', // Will be updated by ReAct agent
          parameters: step.parameters || {}, // Ensure parameters are always available
          config: step.parameters || step.config || {}, // Backward compatibility
        },
      };
    });

    const flowEdges: Edge[] = [];
    for (let i = 1; i < flowNodes.length; i++) {
      const sourceNodeId = flowNodes[i - 1].id;
      const targetNodeId = flowNodes[i].id;

      flowEdges.push({
        id: `edge-${i}`,
        source: sourceNodeId,
        target: targetNodeId,
        sourceHandle: `${sourceNodeId}-source`,
        targetHandle: `${targetNodeId}-target`,
        type: 'smoothstep',
        style: {
          stroke: '#3b82f6',
          strokeWidth: 2,
        },
      });
    }

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [setNodes, setEdges]);

  // Update visualization when workflow changes
  useEffect(() => {
    if (currentWorkflow) {
      updateWorkflowVisualization(currentWorkflow);
    }
  }, [currentWorkflow, updateWorkflowVisualization]);

  // Highlight connector in visualization
  const highlightConnector = (connectorName: string, status: string = 'working') => {
    setNodes(prevNodes => prevNodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        status: node.data.connector_name === connectorName ? status : node.data.status
      }
    })));
  };

  // Process UI updates from True ReAct Agent
  const processUIUpdates = (updates: TrueReActResponse['ui_updates']) => {
    updates.forEach(update => {
      const { type, message, connector_name, reasoning, step_number } = update.update;

      switch (type) {
        case 'session_started':
          addReActStep('reasoning', 'Session Started', message || 'Starting ReAct analysis...', 'completed');
          setProgress(10);
          break;

        case 'reasoning_update':
          addReActStep('reasoning', 'Agent Reasoning', reasoning || message || 'Analyzing...', 'active');
          setProgress(prev => Math.min(prev + 10, 40));
          break;

        case 'connector_highlight':
          if (connector_name) {
            addReActStep('connector_highlight', `Working on ${connector_name}`, reasoning || message || 'Configuring connector...', 'active', connector_name, step_number);
            highlightConnector(connector_name, 'working');
            setProgress(prev => Math.min(prev + 15, 70));
          }
          break;

        case 'connector_configured':
          if (connector_name) {
            addReActStep('action', `Configured ${connector_name}`, message || 'Connector configured successfully', 'completed', connector_name);
            highlightConnector(connector_name, 'configured');
            setProgress(prev => Math.min(prev + 10, 85));
          }
          break;

        case 'step_completed':
          addReActStep('step_completed', 'Step Completed', message || 'Step completed successfully', 'completed');
          setProgress(prev => Math.min(prev + 5, 90));
          break;

        case 'workflow_completed':
          addReActStep('observation', 'Workflow Complete', message || 'Workflow created successfully!', 'completed');
          setProgress(100);
          break;

        case 'error':
          addReActStep('observation', 'Error', message || 'An error occurred', 'failed');
          break;
      }
    });
  };

  const startTrueReActBuilding = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setReActSteps([]);
    setProgress(0);

    try {
      addReActStep('reasoning', 'Starting Analysis', 'Initializing True ReAct Agent...', 'active');

      const response: TrueReActResponse = await workflowReactAPI.buildWorkflowConversationally({
        query,
        session_id: sessionId || undefined
      });

      setSessionId(response.session_id);

      // Process UI updates
      if (response.ui_updates) {
        processUIUpdates(response.ui_updates);
      }

      // Update workflow visualization
      if (response.workflow) {
        console.log('🔍 ReAct response workflow:', response.workflow);
        console.log('🔍 Workflow has ID:', response.workflow.id);
        console.log('🔍 Workflow steps:', response.workflow.steps);
        
        setCurrentWorkflow(response.workflow);
        updateWorkflowVisualization(response.workflow);
      }

      // Add reasoning trace
      response.reasoning_trace.forEach((reasoning, index) => {
        addReActStep('reasoning', `Reasoning Step ${index + 1}`, reasoning, 'completed');
      });

      if (response.success) {
        // Handle different phases of conversational planning
        if (response.phase === 'planning') {
          addReActStep('observation', 'Plan Created', 'Workflow plan ready for your review', 'completed');
          addReActStep('reasoning', 'Awaiting Approval', response.message, 'active');

          // Update plan state
          setCurrentPlan(response.plan);
          setAwaitingApproval(response.awaiting_approval || false);
          setPlanPhase('planning');

          // Store the plan context for potential approval
          if (response.plan && sessionId) {
            workflowReactAPI.storePlanContext({
              session_id: sessionId,
              plan: response.plan,
              awaiting_approval: response.awaiting_approval || false,
              created_at: new Date().toISOString()
            });
          }
        } else if (response.phase === 'completed') {
          addReActStep('observation', 'Workflow Complete', response.message, 'completed');

          // Clear plan state and set workflow
          setCurrentPlan(null);
          setAwaitingApproval(false);
          setPlanPhase('completed');

          // Clear stored plan context
          if (sessionId) {
            workflowReactAPI.clearPlanContext(sessionId);
          }
        } else {
          addReActStep('observation', 'Success', response.message, 'completed');
        }
      } else {
        // Check if it's a conversational response vs actual error
        const isConversational = response.error === 'no_workflow_needed' ||
          response.error === 'no_actionable_intent' ||
          response.error === 'no_workflow_created' ||
          response.error === 'no_plan_context';

        if (isConversational) {
          addReActStep('observation', 'Conversational Response', response.message, 'info');
        } else {
          addReActStep('observation', 'Failed', response.error || 'Unknown error', 'failed');
        }
      }

    } catch (error) {
      console.error('Error with True ReAct building:', error);
      addReActStep('observation', 'Error', `Failed to build workflow: ${error}`, 'failed');
    } finally {
      setLoading(false);
      // Clear the query so user can type a new message
      setQuery('');
    }
  };

  return (
    <div className="h-[calc(100vh-100px)] bg-gray-900 text-white flex overflow-hidden">
      {/* Left Sidebar - ReAct Trace */}
      <div className="w-96 bg-gray-800 border-r border-gray-700 grid grid-rows-[auto_1fr_auto] h-full">
        {/* Header */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">True ReAct Agent</h2>
              <p className="text-gray-400 text-sm">String Alpha-style reasoning</p>
            </div>
          </div>

          {/* Progress */}
          {progress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-400">
                <span>ReAct Progress</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
        </div>

        {/* ReAct Steps */}
        <div className="overflow-hidden min-h-0">
          <ScrollArea className="h-full max-h-[calc(100vh-200px)]">
            <div className="p-4 space-y-3">
              {reactSteps.map((step) => (
                <div key={step.id} className="space-y-2">
                  <div className={`p-3 rounded-lg border-l-4 ${step.type === 'reasoning' ? 'bg-blue-900/30 border-blue-500' :
                    step.type === 'action' ? 'bg-green-900/30 border-green-500' :
                      step.type === 'connector_highlight' ? 'bg-purple-900/30 border-purple-500' :
                        step.type === 'step_completed' ? 'bg-emerald-900/30 border-emerald-500' :
                          'bg-gray-700 border-gray-500'
                    }`}>
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {step.status === 'completed' ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : step.status === 'failed' ? (
                          <div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                            <div className="w-2 h-2 bg-white rounded-full" />
                          </div>
                        ) : step.status === 'info' ? (
                          <div className="w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center">
                            <div className="w-2 h-2 bg-white rounded-full" />
                          </div>
                        ) : (
                          <Clock className="w-4 h-4 text-blue-400 animate-pulse" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-medium text-gray-200">{step.title}</h4>
                          {step.step_number && (
                            <Badge variant="outline" className="text-xs">
                              Step {step.step_number}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 whitespace-pre-wrap">{step.content}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {step.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Plan Approval Section */}
        {awaitingApproval && currentPlan && (
          <div className="p-3 border-t border-gray-700 bg-gray-750">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-medium text-gray-200">Plan Ready for Approval</h3>
              </div>

              <div className="bg-gray-800 rounded-lg p-3 space-y-2">
                <p className="text-xs text-gray-300 font-medium">Proposed Workflow:</p>
                <p className="text-xs text-gray-400">{currentPlan.summary || 'Workflow plan created'}</p>

                {currentPlan.tasks && (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-300 font-medium">Tasks ({currentPlan.tasks.length}):</p>
                    {currentPlan.tasks.slice(0, 3).map((task: any, index: number) => (
                      <div key={index} className="text-xs text-gray-400 flex items-center gap-2">
                        <span className="w-4 h-4 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs">
                          {task.task_number || index + 1}
                        </span>
                        <span>{task.description}</span>
                      </div>
                    ))}
                    {currentPlan.tasks.length > 3 && (
                      <p className="text-xs text-gray-500">...and {currentPlan.tasks.length - 3} more tasks</p>
                    )}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={() => setQuery('approve')}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm py-2"
                  size="sm"
                >
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Approve Plan
                </Button>
                <Button
                  onClick={() => setQuery('I want to modify this plan')}
                  variant="outline"
                  className="flex-1 border-gray-600 text-gray-300 hover:bg-gray-700 text-sm py-2"
                  size="sm"
                >
                  Modify Plan
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Bottom Input Area - Always Visible */}
        <div className="p-2 border-t border-gray-700 min-h-[100px]">
          <div className="space-y-1">
            <Textarea
              placeholder={
                awaitingApproval
                  ? "Type 'approve' to proceed, or describe changes you'd like to make..."
                  : reactSteps.length === 0
                    ? "Describe the workflow you want to create..."
                    : "Send another message or ask for modifications..."
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-gray-700 border-gray-600 text-white placeholder-gray-400 resize-none"
              rows={2}
            />
            <Button
              onClick={startTrueReActBuilding}
              disabled={loading || !query.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Agent Thinking...
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  {reactSteps.length === 0 ? 'Start ReAct Agent' : 'Send Message'}
                </div>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Right Panel - Workflow Visualization */}
      <div className="flex-1 relative h-full">
        {reactSteps.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Brain className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">True ReAct Agent</h3>
              <p>Start building to see the agent reason and act</p>
            </div>
          </div>
        ) : (
          <div className="h-full relative">
            {/* Workflow Header */}
            <div className="absolute top-4 left-4 right-4 z-10">
              <div className="flex items-center justify-between bg-gray-800/90 backdrop-blur-sm border border-gray-600 rounded-lg p-3">
                <div>
                  <h3 className="font-medium">ReAct Workflow</h3>
                  <p className="text-sm text-gray-400">
                    {nodes.length} connectors • Real-time agent reasoning
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Eye className="w-4 h-4 mr-1" />
                    Watch Agent
                  </Button>
                  {currentWorkflow && (
                    <Button
                      size="sm"
                      onClick={() => {
                        console.log('🔥 Button clicked - calling handleExecuteWorkflow');
                        handleExecuteWorkflow();
                      }}
                      disabled={isExecuting}
                    >
                      {isExecuting ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4 mr-1" />
                      )}
                      {isExecuting ? 'Running...' : 'Run Workflow'}
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      console.log('Test button clicked');
                      setSelectedConnector('gmail_connector');
                      setConfigModalOpen(true);
                    }}
                  >
                    Test Modal
                  </Button>
                </div>
              </div>
            </div>

            {/* React Flow */}
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, node) => {
                console.log('ReactFlow node clicked:', node);
                handleNodeClick(node.data);
              }}
              nodeTypes={nodeTypes}
              className="bg-gray-900 w-full h-full"
              defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
              <Controls className="bg-gray-800 border-gray-600" />
            </ReactFlow>
          </div>
        )}
      </div>

      {/* Connector Configuration Modal */}
      {(() => {
        const modalProps = {
          isOpen: configModalOpen,
          onClose: () => {
            console.log('Closing config modal');
            setConfigModalOpen(false);
            setSelectedConnector(null);
            setSelectedNodeData(null);
          },
          initialConfig: selectedNodeData?.parameters,
          onSave: async (config: any) => {
            // Handle saving connector configuration
            console.log('Saving connector config:', config);

            // Update the workflow nodes with the new configuration
            if (selectedNodeData && selectedNodeData.id) {
              setNodes((nds) =>
                nds.map((node) => {
                  if (node.id === selectedNodeData.id) {
                    return {
                      ...node,
                      data: {
                        ...node.data,
                        parameters: config.settings || config,
                        config: config, // Save full config including auth
                      },
                    };
                  }
                  return node;
                })
              );

              // Also update the workflow state if it exists
              if (currentWorkflow) {
                const updatedWorkflow: Workflow = {
                  ...currentWorkflow,
                  steps: currentWorkflow.steps.map((step: WorkflowStep) => {
                    if (step.connector_name === selectedConnector) {
                      return {
                        ...step,
                        parameters: config.settings || config,
                      };
                    }
                    return step;
                  })
                };
                setCurrentWorkflow(updatedWorkflow);
              }
            }

            setConfigModalOpen(false);
          },
          // Pass AI-generated parameters to custom modals
          initialData: selectedNodeData?.parameters || selectedNodeData?.config || {}
        };

        // Use specific modals for certain connectors
        switch (selectedConnector) {
          case 'notion':
            return <NotionConnectorModal {...modalProps} />;
          case 'google_drive':
            return <GoogleDriveConnectorModal {...modalProps} />;
          case 'youtube':
            return <YouTubeConnectorModal {...modalProps} />;
          case 'code':
            return <CodeConnectorModal {...modalProps} />;
          case 'airtable':
            return <AirtableConnectorModal {...modalProps} />;
          case 'gmail_connector':
            return <GmailConnectorModal {...modalProps} />;

          case 'google_translate':
            return <GoogleTranslateConnectorModal {...modalProps} />;
          default:
            return (
              <StringLikeConnectorModal
                isOpen={configModalOpen}
                onClose={() => {
                  console.log('Closing config modal');
                  setConfigModalOpen(false);
                  setSelectedConnector(null);
                  setSelectedNodeData(null);
                }}
                connectorName={selectedConnector || ''}
                connectorConfig={selectedNodeData?.parameters}
                onSave={(config) => {
                  // Handle saving connector configuration
                  console.log('Saving connector config:', config);

                  // Update the workflow nodes with the new configuration
                  if (selectedNodeData && selectedNodeData.id) {
                    setNodes((nds) =>
                      nds.map((node) => {
                        if (node.id === selectedNodeData.id) {
                          return {
                            ...node,
                            data: {
                              ...node.data,
                              parameters: config,
                              config: config, // Also save as config for backward compatibility
                            },
                          };
                        }
                        return node;
                      })
                    );

                    // Also update the workflow state if it exists
                    if (currentWorkflow) {
                      const updatedWorkflow: Workflow = {
                        ...currentWorkflow,
                        steps: currentWorkflow.steps.map((step: WorkflowStep) => {
                          if (step.connector_name === selectedConnector) {
                            return {
                              ...step,
                              parameters: config,
                            };
                          }
                          return step;
                        })
                      };
                      setCurrentWorkflow(updatedWorkflow);
                    }
                  }

                  setConfigModalOpen(false);
                }}
              />
            );
        }
      })()}
    </div>
  );
}