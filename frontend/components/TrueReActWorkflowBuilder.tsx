'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { createClient } from '@supabase/supabase-js';
import {
  CheckCircle, Play, Settings,
  Loader2, Clock, Eye, Layers, Mail, Globe,
  FileText, Webhook, Database, Sparkles, Brain, Code,
  User, Send, Zap, AlertCircle
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
import { GoogleSheetsConnectorModal } from '@/components/connectors/google_sheets';
import { PerplexityConnectorModal } from '@/components/connectors/perplexity';
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
  phase?: 'planning' | 'completed' | 'modified';
  plan?: any;
  awaiting_approval?: boolean;
  // Workflow modification fields
  modification_applied?: boolean;
  changes?: Array<{
    type: string;
    task_number?: number;
    current_connector?: string;
    new_connector?: string;
    reason?: string;
  }>;
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
  const [sessionId, setSessionId] = useState<string>(() => {
    // Generate a consistent session ID that persists across component re-renders
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('current_session_id');
      if (stored) return stored;
    }
    const newSessionId = `react_${Date.now()}`;
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_session_id', newSessionId);
    }
    return newSessionId;
  });

  const startNewSession = () => {
    const newSessionId = `react_${Date.now()}`;
    setSessionId(newSessionId);
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_session_id', newSessionId);
      // Clear any existing plan context
      workflowReactAPI.clearPlanContext(sessionId);
    }
    // Clear conversation state
    setConversationHistory([]);
    setCurrentWorkflow(null);
    setReActSteps([]);
    setCurrentAgentResponse('');
  };
  const [reactSteps, setReActSteps] = useState<ReActStep[]>([]);
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null);
  const [progress, setProgress] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isTyping?: boolean;
  }>>([]);
  const [currentAgentResponse, setCurrentAgentResponse] = useState<string>('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use shared Supabase client to avoid multiple instances warning
  const supabase = React.useMemo(() => createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  ), []);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversationHistory, currentAgentResponse, scrollToBottom]);

  // Typing animation function
  const typeMessage = useCallback(async (message: string) => {
    setIsTyping(true);
    setCurrentAgentResponse('');

    const words = message.split(' ');
    let currentText = '';

    for (let i = 0; i < words.length; i++) {
      currentText += (i > 0 ? ' ' : '') + words[i];
      setCurrentAgentResponse(currentText);

      // Adjust typing speed - faster for longer messages
      const delay = words.length > 50 ? 30 : 50;
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    setIsTyping(false);
  }, []);

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

  // Normalize parameter references like {{steps.1.results}} -> {{perplexity_search.result}}
  const normalizeParameterReferences = useCallback((params: Record<string, any>, workflow: Workflow | null) => {
    if (!params || !workflow || !workflow.steps) return params;
    const normalized: Record<string, any> = { ...params };

    const replaceStepsRef = (val: string): string => {
      // Match patterns like {{steps.1.results}} or {{ steps.2.result }}
      const regex = /\{\{\s*steps\.(\d+)\.(result|results)\s*\}\}/gi;
      return val.replace(regex, (_m, stepNumStr: string) => {
        const stepNum = parseInt(stepNumStr, 10);
        // task_number is 1-based; find step with that task_number
        const step = (workflow.steps as any[]).find((s: any) => s.task_number === stepNum) || workflow.steps[stepNum - 1];
        const connector = step?.connector_name || `step_${stepNum}`;
        return `{{${connector}.result}}`;
      });
    };

    Object.entries(normalized).forEach(([key, value]) => {
      if (typeof value === 'string') {
        normalized[key] = replaceStepsRef(value);
      }
    });

    return normalized;
  }, []);



  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Handle node click to open configuration
  const handleNodeClick = useCallback((nodeData: any) => {
    // Create safe version for logging (redact sensitive data)
    const safeNodeData = { ...nodeData };
    if (safeNodeData.parameters?.api_token) {
      safeNodeData.parameters = { ...safeNodeData.parameters, api_token: '[REDACTED]' };
    }
    if (safeNodeData.config?.api_token) {
      safeNodeData.config = { ...safeNodeData.config, api_token: '[REDACTED]' };
    }
    
    console.log('🔧 Opening config for:', safeNodeData.connector_name);
    console.log('🔧 Node parameters:', safeNodeData.parameters);
    console.log('🔧 Full node data:', JSON.stringify(safeNodeData, null, 2));
    setSelectedConnector(nodeData.connector_name);

    // Add the node ID to the selected data for proper updates
    const nodeWithId = {
      ...nodeData,
      id: nodeData.connector_name + (currentWorkflow?.steps?.findIndex((step: any) => step.connector_name === nodeData.connector_name) || 0)
    };

    setSelectedNodeData(nodeWithId);
    setConfigModalOpen(true);
  }, [currentWorkflow]);

  // Add ReAct step - now consolidates into a single response
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

      // Create a more natural, conversational response
      let consolidatedMessage = '';

      if (newSteps.length === 1 && step.type === 'reasoning') {
        consolidatedMessage = `I'm analyzing your request: "${step.content}"`;
      } else {
        // Build a flowing narrative from all steps
        const narrative: string[] = [];
        let hasReasoning = false;
        let hasActions = false;
        let hasResults = false;

        newSteps.forEach(s => {
          if (s.type === 'reasoning' && !hasReasoning) {
            narrative.push(`I'm thinking about this: ${s.content}`);
            hasReasoning = true;
          } else if (s.type === 'action' || s.type === 'connector_highlight') {
            if (!hasActions) {
              narrative.push(`\nNow I'm working on the solution:`);
              hasActions = true;
            }
            narrative.push(`• ${s.content}`);
          } else if (s.type === 'step_completed' && !hasResults) {
            narrative.push(`\n✅ ${s.content}`);
            hasResults = true;
          }
        });

        consolidatedMessage = narrative.join('\n');
      }

      // Only trigger typing animation for significant updates
      if (newSteps.length === 1 || step.status === 'completed' || step.type === 'step_completed') {
        typeMessage(consolidatedMessage);
      } else {
        setCurrentAgentResponse(consolidatedMessage);
      }

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

    console.log('🔧 Setting flow nodes:', flowNodes);
    console.log('🔧 Setting flow edges:', flowEdges);
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

  // Process UI updates from True ReAct Agent to build natural response
  const processUIUpdates = (updates: TrueReActResponse['ui_updates']) => {
    let responseText = '';

    updates.forEach((update, index) => {
      const { type, message, connector_name, reasoning, step_number } = update.update;

      switch (type) {
        case 'session_started':
          // Skip the generic "Starting to analyze" message
          if (message && !message.includes('Starting to analyze')) {
            responseText += message;
          }
          setProgress(10);
          break;

        case 'reasoning_update':
          if (reasoning || message) {
            const content = reasoning || message || '';
            if (!content.includes('Starting to analyze') && !content.includes('Initializing')) {
              responseText += (responseText ? '\n\n' : '') + content;
            }
          }
          setProgress(prev => Math.min(prev + 10, 40));
          break;

        case 'connector_highlight':
          if (connector_name && message) {
            responseText += (responseText ? '\n\n' : '') + `🔧 ${message}`;
            highlightConnector(connector_name, 'working');
            setProgress(prev => Math.min(prev + 15, 70));
          }
          break;

        case 'connector_configured':
          if (connector_name && message) {
            responseText += (responseText ? '\n\n' : '') + `✅ ${message}`;
            highlightConnector(connector_name, 'configured');
            setProgress(prev => Math.min(prev + 10, 85));
          }
          break;

        case 'step_completed':
          if (message) {
            responseText += (responseText ? '\n\n' : '') + `🎉 ${message}`;
          }
          setProgress(prev => Math.min(prev + 5, 90));
          break;

        case 'workflow_completed':
          if (message) {
            responseText += (responseText ? '\n\n' : '') + `🚀 ${message}`;
          }
          setProgress(100);
          break;

        case 'error':
          if (message) {
            responseText += (responseText ? '\n\n' : '') + `❌ ${message}`;
          }
          break;
      }
    });

    // Update the current agent response with the consolidated text
    if (responseText) {
      setCurrentAgentResponse(responseText);
    }
  };

  const startTrueReActBuilding = async () => {
    if (!query.trim()) return;

    // Add user message to conversation history
    const userMessage = {
      id: Date.now().toString(),
      type: 'user' as const,
      content: query,
      timestamp: new Date()
    };
    setConversationHistory(prev => [...prev, userMessage]);

    const currentQuery = query;
    setQuery(''); // Clear input immediately
    setLoading(true);
    setReActSteps([]); // Clear steps for new conversation turn
    // Only clear currentAgentResponse if we're not in a planning phase
    if (planPhase !== 'planning') {
      setCurrentAgentResponse('');
    }
    setIsTyping(false);
    setProgress(0);

    try {
      // Don't show internal initialization messages to user

      const response: TrueReActResponse = await workflowReactAPI.buildWorkflowConversationally({
        query: currentQuery,
        session_id: sessionId
      });

      console.log('🔍 Full API response:', response);
      console.log('🔍 Response success:', response.success);
      console.log('🔍 Response phase:', response.phase);
      console.log('🔍 Response has plan:', !!response.plan);
      console.log('🔍 Response awaiting approval:', response.awaiting_approval);

      // Update session ID if it changed, and persist it
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
        if (typeof window !== 'undefined') {
          localStorage.setItem('current_session_id', response.session_id);
        }
      }

      // Process UI updates to show step-by-step progress
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

      // Skip reasoning trace processing - use main message instead

      // Handle different types of responses
      if (response.success) {
        console.log('✅ Success response received:', response);
        // Handle different phases of conversational planning
        if (response.phase === 'planning') {
          console.log('📋 Planning phase detected, message:', response.message);
          // For planning phase, always show the plan message
          if (response.message) {
            setCurrentAgentResponse(response.message);
            console.log('💬 Set agent response:', response.message.substring(0, 100));

            // Immediately save to conversation history
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: response.message,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved planning message to conversation history');
          }

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
          console.log('✅ Completion phase detected, message:', response.message);
          // For completed phase, always show the completion message
          if (response.message) {
            setCurrentAgentResponse(response.message);

            // Immediately save to conversation history
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: response.message,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved completion message to conversation history');
          }

          // Clear plan state and set workflow
          setCurrentPlan(null);
          setAwaitingApproval(false);
          setPlanPhase('completed');

          // Set the completed workflow for visualization
          if (response.workflow) {
            console.log('🔧 Setting completed workflow:', response.workflow);
            console.log('🔧 Workflow has steps:', response.workflow.steps?.length || 0);
            setCurrentWorkflow(response.workflow);
            updateWorkflowVisualization(response.workflow);

            // Force a re-render to ensure the workflow visualization updates
            setTimeout(() => {
              console.log('🔄 Current workflow state:', currentWorkflow);
              console.log('🔄 Current nodes state:', nodes);
              console.log('🔄 Current edges state:', edges);
            }, 100);
          } else {
            console.log('⚠️ No workflow in completion response');
            console.log('🔍 Full response keys:', Object.keys(response));
          }

          // Clear stored plan context
          if (sessionId) {
            workflowReactAPI.clearPlanContext(sessionId);
          }
        } else if (response.phase === 'modified') {
          console.log('🔧 Modification phase detected, message:', response.message);
          console.log('🔧 Modification applied:', response.modification_applied);
          console.log('🔧 Changes:', response.changes);
          // For modification phase, show the modification message
          if (response.message) {
            setCurrentAgentResponse(response.message);

            // Immediately save to conversation history
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: response.message,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved modification message to conversation history');
          }

          // Update workflow if provided
          if (response.workflow) {
            console.log('🔧 Setting modified workflow:', response.workflow);
            console.log('🔧 Modified workflow has steps:', response.workflow.steps?.length || 0);
            setCurrentWorkflow(response.workflow);
            updateWorkflowVisualization(response.workflow);
          }

          // Clear plan state
          setCurrentPlan(null);
          setAwaitingApproval(false);
          setPlanPhase('completed');
        } else if (response.phase === 'conversational') {
          console.log('💬 Conversational phase detected, message:', response.message);
          // For conversational phase, always show the conversational message
          if (response.message) {
            setCurrentAgentResponse(response.message);

            // Immediately save to conversation history
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: response.message,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved conversational message to conversation history');
          }

          // Clear any plan state since this is just a conversational response
          setCurrentPlan(null);
          setAwaitingApproval(false);
          setPlanPhase('initial');
        } else {
          // For other successful responses, use the message if no UI updates provided content
          if (response.message && !currentAgentResponse) {
            setCurrentAgentResponse(response.message);

            // Save to conversation history
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: response.message,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved other successful response to conversation history');
          }
        }
      } else {
        // Handle different types of non-success responses
        const isConversational = response.error === 'no_workflow_needed' ||
          response.error === 'no_actionable_intent' ||
          response.error === 'no_workflow_created' ||
          response.error === 'no_plan_context';

        if (isConversational) {
          // For conversational responses (greetings, etc.), show the message
          let messageToShow = '';
          if (response.message) {
            messageToShow = response.message;
            setCurrentAgentResponse(response.message);
          } else {
            // Provide a friendly default response for greetings
            if (currentQuery.toLowerCase().includes('hi') || currentQuery.toLowerCase().includes('hello')) {
              messageToShow = "Hello! I'm here to help you create workflows and automate tasks. What would you like to build today?";
            } else {
              messageToShow = "I understand you're looking for help. Could you please describe what kind of workflow or automation you'd like me to create for you?";
            }
            setCurrentAgentResponse(messageToShow);
          }

          // Immediately save to conversation history
          if (messageToShow) {
            const assistantMessage = {
              id: (Date.now() + 1).toString(),
              type: 'assistant' as const,
              content: messageToShow,
              timestamp: new Date()
            };
            setConversationHistory(prev => [...prev, assistantMessage]);
            console.log('💾 Saved conversational message to conversation history');
          }
        } else {
          // For actual errors
          const errorMessage = `I encountered an issue: ${response.error || 'Unknown error'}. Please try again.`;
          setCurrentAgentResponse(errorMessage);

          // Save error to conversation history
          const assistantMessage = {
            id: (Date.now() + 1).toString(),
            type: 'assistant' as const,
            content: errorMessage,
            timestamp: new Date()
          };
          setConversationHistory(prev => [...prev, assistantMessage]);
          console.log('💾 Saved error message to conversation history');
        }
      }

    } catch (error) {
      console.error('Error with True ReAct building:', error);
      const errorMessage = `I encountered an error while processing your request: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`;
      setCurrentAgentResponse(errorMessage);

      // Save error to conversation history
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant' as const,
        content: errorMessage,
        timestamp: new Date()
      };
      setConversationHistory(prev => [...prev, assistantMessage]);
      console.log('💾 Saved catch error message to conversation history');
    } finally {
      setLoading(false);

      // Conversation history is now saved immediately in each response handler above
      // No need to save again here
    }
  };

  return (
    <div className="h-[calc(100vh-100px)] bg-gray-900 text-white flex overflow-hidden">
      {/* Left Sidebar - Modern Chat Interface */}
      <div className="w-96 bg-gray-800 border-r border-gray-700 flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">True ReAct Agent</h2>
              <p className="text-gray-400 text-sm">AI Workflow Assistant</p>
            </div>
          </div>

          {/* Progress */}
          {progress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-400">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              {/* Welcome Message */}
              {reactSteps.length === 0 && (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-lg font-medium text-white mb-2">
                    How can I help you today?
                  </h3>
                  <p className="text-gray-400 text-sm mb-4">
                    I can help you create workflows, automate tasks, and build AI-powered solutions.
                  </p>
                  <div className="space-y-2">
                    {[
                      "Create a workflow to summarize emails",
                      "Build an automation for data processing",
                      "Set up a notification system"
                    ].map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setQuery(suggestion)}
                        className="w-full p-2 text-left bg-gray-700/50 hover:bg-gray-700 border border-gray-600 rounded-lg transition-colors text-xs text-gray-300 hover:text-white"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Conversation History */}
              {conversationHistory.map((msg) => (
                <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
                  <div className={`max-w-[85%] ${msg.type === 'user'
                    ? 'bg-blue-600 rounded-2xl rounded-br-md'
                    : 'bg-gray-700 border border-gray-600 rounded-2xl rounded-bl-md'
                    } px-4 py-3`}>
                    <div className="flex items-start gap-3">
                      {msg.type === 'assistant' && (
                        <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Brain className="w-3 h-3 text-white" />
                        </div>
                      )}
                      <div className="flex-1 space-y-2">
                        {msg.type === 'assistant' && (
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-medium text-gray-200">AI Assistant</h4>
                          </div>
                        )}
                        <div className={`text-sm leading-relaxed whitespace-pre-wrap ${msg.type === 'user' ? 'text-white' : 'text-gray-300'
                          }`}>
                          {msg.content}
                        </div>
                        <div className="flex items-center justify-between pt-1">
                          {msg.type === 'assistant' && (
                            <div className="flex items-center gap-1">
                              <Brain className="w-3 h-3 text-blue-400" />
                              <span className="text-xs text-gray-500">Response</span>
                            </div>
                          )}
                          {msg.type === 'user' && <div />}
                          <span className="text-xs text-gray-500">
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                      {msg.type === 'user' && (
                        <User className="w-4 h-4 text-blue-100 flex-shrink-0 mt-0.5" />
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Current Agent Response (while loading) */}
              {loading && (
                <div className="flex justify-start mb-4">
                  <div className="max-w-[85%] bg-gray-700 border border-gray-600 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Loader2 className="w-3 h-3 text-white animate-spin" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-medium text-gray-200">AI Assistant</h4>
                          <Badge variant="outline" className="text-xs border-gray-500 text-gray-400">
                            Thinking...
                          </Badge>
                        </div>
                        <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {currentAgentResponse || "Let me think about that..."}
                          {isTyping && (
                            <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse" />
                          )}
                        </div>
                        <div className="flex items-center justify-between pt-1">
                          <div className="flex items-center gap-1">
                            <Brain className="w-3 h-3 text-blue-400" />
                            <span className="text-xs text-gray-500">
                              {isTyping ? 'Typing...' : 'Processing...'}
                            </span>
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
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
                  onClick={() => {
                    console.log('🎯 Approve Plan button clicked - setting query to approve');
                    setQuery('approve');
                    // Automatically submit the approval
                    setTimeout(() => {
                      startTrueReActBuilding();
                    }, 100);
                  }}
                  disabled={loading}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm py-2"
                  size="sm"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4 mr-1" />
                  )}
                  Approve Plan
                </Button>
                <Button
                  onClick={() => {
                    setQuery('');
                    // Focus the input so user can type their modification
                    const textarea = document.querySelector('textarea');
                    if (textarea) {
                      textarea.focus();
                      textarea.placeholder = 'Describe the changes you want to make...';
                    }
                  }}
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

        {/* Modern Chat Input Area */}
        <div className="p-4 border-t border-gray-700 flex-shrink-0">
          <div className="relative">
            <Textarea
              placeholder={
                awaitingApproval
                  ? "Type 'approve' to proceed, or describe changes..."
                  : reactSteps.length === 0
                    ? "Ask me to create a workflow..."
                    : "Send a message..."
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  startTrueReActBuilding();
                }
              }}
              className="w-full bg-gray-700 border-gray-600 text-white placeholder-gray-400 resize-none pr-12 min-h-[52px] max-h-[120px] rounded-xl"
              disabled={loading}
              rows={1}
            />
            <Button
              onClick={startTrueReActBuilding}
              disabled={loading || !query.trim()}
              size="sm"
              className="absolute right-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-3 py-1.5"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>

          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <div className="flex items-center gap-2">
              <Button
                onClick={startNewSession}
                variant="outline"
                size="sm"
                className="text-xs h-6 px-2 border-gray-600 text-gray-400 hover:text-white hover:border-gray-500"
              >
                New Chat
              </Button>
              {sessionId && (
                <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                  Session: {sessionId.slice(0, 8)}...
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Workflow Visualization */}
      <div className="flex-1 relative h-full">
        {reactSteps.length === 0 && !currentWorkflow ? (
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
                    {nodes.length} connectors • {currentWorkflow ? 'Workflow completed' : 'Real-time agent reasoning'}
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
        const initialDataRaw = selectedNodeData?.parameters || selectedNodeData?.config || {};
        const normalizedInitialData = normalizeParameterReferences(initialDataRaw, currentWorkflow);
        const modalProps = {
          isOpen: configModalOpen,
          onClose: () => {
            console.log('Closing config modal');
            setConfigModalOpen(false);
            setSelectedConnector(null);
            setSelectedNodeData(null);
          },
          initialConfig: selectedNodeData?.config || { parameters: selectedNodeData?.parameters },
          onSave: async (config: any) => {
            // Handle saving connector configuration
            const safeConfig = { ...config };
            if (safeConfig.settings?.api_token) {
              safeConfig.settings = { ...safeConfig.settings, api_token: '[REDACTED]' };
            }
            console.log('Saving connector config:', safeConfig);

            // Update the workflow nodes with the new configuration
            if (selectedNodeData && selectedNodeData.id) {
              setNodes((nds) =>
                nds.map((node) => {
                  if (node.id === selectedNodeData.id) {
                    return {
                      ...node,
                      data: {
                        ...node.data,
                        parameters: config.parameters || config.settings || config,
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
                        parameters: config.parameters || config.settings || config,
                        config: config, // Also save full config in workflow
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
          // Pass AI-generated parameters to custom modals (normalized for readability)
          initialData: normalizedInitialData
        };

        // Use specific modals for certain connectors
        switch (selectedConnector) {
          case 'notion':
            return <NotionConnectorModal {...modalProps} />;
          case 'google_drive':
            return <GoogleDriveConnectorModal {...modalProps} />;
          case 'google_sheets':
            return <GoogleSheetsConnectorModal {...modalProps} />;
          case 'youtube':
            return <YouTubeConnectorModal {...modalProps} />;
          case 'code':
            return <CodeConnectorModal {...modalProps} />;
          case 'airtable':
            return <AirtableConnectorModal {...modalProps} />;
          case 'gmail_connector':
            return <GmailConnectorModal {...modalProps} />;
          case 'perplexity':
          case 'perplexity_search':
            return <PerplexityConnectorModal {...modalProps} />;
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
                connectorConfig={selectedNodeData?.config || { parameters: selectedNodeData?.parameters }}
                onSave={(config) => {
                  // Handle saving connector configuration
                  const safeConfig = { ...config };
                  if (safeConfig.settings?.api_token) {
                    safeConfig.settings = { ...safeConfig.settings, api_token: '[REDACTED]' };
                  }
                  console.log('Saving connector config:', safeConfig);

                  // Update the workflow nodes with the new configuration
                  if (selectedNodeData && selectedNodeData.id) {
                    setNodes((nds) =>
                      nds.map((node) => {
                        if (node.id === selectedNodeData.id) {
                          return {
                            ...node,
                            data: {
                              ...node.data,
                              parameters: config.parameters || config,
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
                              parameters: config.parameters || config,
                              config: config, // Also save full config in workflow
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