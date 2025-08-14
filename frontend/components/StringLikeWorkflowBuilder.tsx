'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Bot, CheckCircle, Play, ArrowRight, Zap, Settings, MessageSquare,
  Workflow, Loader2, Clock, Eye, Layers, GitBranch, Mail, Globe,
  FileText, Webhook, Database, MoreHorizontal
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
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { workflowReactAPI } from '@/lib/api';
import StringLikeConnectorModal from './StringLikeConnectorModal';

interface WorkflowBuildResponse {
  message: string;
  session_id: string;
  conversation_state: string;
  workflow_plan?: any;
  reasoning?: any;
  next_steps?: string[];
}

type BuildingState = 'initial' | 'planning' | 'configuring' | 'confirming' | 'approved' | 'completed' | 'executing';

interface ProgressStep {
  id: string;
  title: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: Date;
  details?: string;
}

// Custom node component to match String's styling
const WorkflowNode = ({ data }: { data: any }) => {
  const getConnectorIcon = (connectorName: string) => {
    switch (connectorName?.toLowerCase()) {
      case 'gmail_connector': return <Mail className="w-5 h-5" />;
      case 'google_sheets': return <Database className="w-5 h-5" />;
      case 'perplexity_search': return <Globe className="w-5 h-5" />;
      case 'text_summarizer': return <FileText className="w-5 h-5" />;
      case 'webhook': return <Webhook className="w-5 h-5" />;
      case 'http_request': return <Globe className="w-5 h-5" />;
      default: return <Layers className="w-5 h-5" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'active': return 'bg-blue-500';
      case 'failed': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const handleClick = () => {
    if (data.onNodeClick) {
      data.onNodeClick(data);
    }
  };

  return (
    <div
      className="bg-gray-800 border border-gray-600 rounded-lg p-4 min-w-[200px] shadow-lg hover:border-blue-500 transition-colors cursor-pointer"
      onClick={handleClick}
    >
      <div className="flex items-center gap-3 mb-2">
        <div className="text-blue-400">
          {getConnectorIcon(data.connector_name)}
        </div>
        <div className="flex-1">
          <h3 className="text-white font-medium text-sm">
            {data.connector_name?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'Unknown Connector'}
          </h3>
        </div>
        <div className={`w-2 h-2 rounded-full ${getStatusColor(data.status)}`} />
      </div>

      {data.description && (
        <p className="text-gray-400 text-xs mb-3">{data.description}</p>
      )}

      {data.configuration && (
        <div className="space-y-1">
          {Object.entries(data.configuration).slice(0, 2).map(([key, value]: [string, any]) => (
            <div key={key} className="flex items-center gap-2 text-xs">
              <span className="text-gray-500">{key}:</span>
              <span className="text-gray-300 truncate">{String(value)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500 mt-3">
        <span>{data.status || 'pending'}</span>
        <Settings className="w-3 h-3 opacity-50" />
      </div>

      <div className="mt-2 text-xs text-blue-400 text-center">
        Click to configure
      </div>
    </div>
  );
};

// Move nodeTypes outside component to prevent React Flow warnings
const nodeTypes = {
  workflowNode: WorkflowNode,
};

// Generate unique IDs to prevent duplicate key errors
let stepCounter = 0;
const generateUniqueId = () => {
  stepCounter += 1;
  return `${Date.now()}-${stepCounter}`;
};

export default function StringLikeWorkflowBuilder() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [buildingState, setBuildingState] = useState<BuildingState>('initial');
  const [conversation, setConversation] = useState<Array<{ role: string, content: string, timestamp: Date }>>([]);
  const [currentResponse, setCurrentResponse] = useState<WorkflowBuildResponse | null>(null);
  const [userInput, setUserInput] = useState('');
  const [workflowPlan, setWorkflowPlan] = useState<any>(null);
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [progress, setProgress] = useState(0);
  const [showConnectorModal, setShowConnectorModal] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<any>(null);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Convert workflow plan to React Flow nodes/edges
  const updateWorkflowVisualization = useCallback((plan: any) => {
    if (!plan || !plan.nodes) return;

    const handleNodeClick = (nodeData: any) => {
      setSelectedConnector(nodeData);
      setShowConnectorModal(true);
    };

    const flowNodes: Node[] = plan.nodes.map((node: any) => ({
      id: node.id,
      type: 'workflowNode',
      position: node.position || { x: Math.random() * 400, y: Math.random() * 300 },
      data: {
        ...node,
        onNodeClick: handleNodeClick
      },
    }));

    const flowEdges: Edge[] = plan.edges?.map((edge: any) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      style: {
        stroke: '#3b82f6',
        strokeWidth: 2,
      },
    })) || [];

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [setNodes, setEdges]);

  // Add progress step
  const addProgressStep = (title: string, status: 'active' | 'completed' = 'active', details?: string) => {
    const step: ProgressStep = {
      id: generateUniqueId(),
      title,
      status,
      timestamp: new Date(),
      details,
    };
    setProgressSteps(prev => [...prev, step]);
  };

  // Update progress step
  const updateProgressStep = (id: string, status: 'completed' | 'failed', details?: string) => {
    setProgressSteps(prev => prev.map(step =>
      step.id === id ? { ...step, status, details } : step
    ));
  };

  const startWorkflowBuilding = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setConversation([]);
    setBuildingState('planning');
    setProgressSteps([]);
    setProgress(20);

    addProgressStep('Analyzing your request...', 'active');

    try {
      const response: WorkflowBuildResponse = await workflowReactAPI.buildWorkflow({
        query,
        session_id: sessionId || undefined
      });

      // Update the analyzing step to completed
      setProgressSteps(prev => prev.map(step =>
        step.title === 'Analyzing your request...' ? { ...step, status: 'completed' } : step
      ));

      setSessionId(response.session_id);
      setCurrentResponse(response);
      setBuildingState(response.conversation_state as BuildingState);
      setProgress(80);

      // Add to conversation
      setConversation([
        { role: 'user', content: query, timestamp: new Date() },
        { role: 'assistant', content: response.message, timestamp: new Date() }
      ]);

      addProgressStep('Response generated', 'completed');

      // If we're still in planning after first response, move to configuring for better UX
      if (response.conversation_state === 'planning') {
        setBuildingState('configuring');
        addProgressStep('Ready for next input', 'completed');
      }

      if (response.workflow_plan) {
        setWorkflowPlan(response.workflow_plan);
        updateWorkflowVisualization(response.workflow_plan);
        addProgressStep('Workflow plan created', 'completed');
        setProgress(100);
      } else {
        setProgress(90);
      }

    } catch (error) {
      console.error('Error starting workflow building:', error);
      setConversation(prev => [...prev,
      { role: 'error', content: 'Failed to start workflow building. Please try again.', timestamp: new Date() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const continueBuilding = async () => {
    if (!userInput.trim() || !sessionId) return;

    setLoading(true);
    addProgressStep('Processing your message...', 'active');

    try {
      const response: WorkflowBuildResponse = await workflowReactAPI.continueWorkflowBuild({
        message: userInput,
        session_id: sessionId
      });

      // Update the processing step to completed
      setProgressSteps(prev => prev.map(step =>
        step.title === 'Processing your message...' ? { ...step, status: 'completed' } : step
      ));

      setCurrentResponse(response);
      setBuildingState(response.conversation_state as BuildingState);

      // Add to conversation
      setConversation(prev => [
        ...prev,
        { role: 'user', content: userInput, timestamp: new Date() },
        { role: 'assistant', content: response.message, timestamp: new Date() }
      ]);

      addProgressStep('Response generated', 'completed');

      // Ensure we don't get stuck in planning state
      if (response.conversation_state === 'planning') {
        setBuildingState('configuring');
        addProgressStep('Continuing conversation', 'completed');
      }

      if (response.workflow_plan) {
        setWorkflowPlan(response.workflow_plan);
        updateWorkflowVisualization(response.workflow_plan);
        addProgressStep('Workflow updated', 'completed');
      }

      setUserInput('');

    } catch (error) {
      console.error('Error continuing workflow building:', error);
      setProgressSteps(prev => prev.map(step =>
        step.title === 'Processing your message...' ? { ...step, status: 'failed', details: 'Failed to process message' } : step
      ));
      setConversation(prev => [...prev,
      { role: 'error', content: 'Failed to continue building. Please try again.', timestamp: new Date() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen bg-gray-900 text-white flex overflow-hidden">
      {/* Left Sidebar - Chat & Progress */}
      <div className="w-96 bg-gray-800 border-r border-gray-700 flex flex-col max-h-screen">
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">Workflow Builder</h2>
              <p className="text-gray-400 text-sm">AI-powered automation</p>
            </div>
          </div>

          {buildingState === 'initial' && (
            <div className="space-y-3">
              <Textarea
                placeholder="Describe the workflow you want to create..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-gray-700 border-gray-600 text-white placeholder-gray-400 resize-none"
                rows={3}
              />
              <Button
                onClick={startWorkflowBuilding}
                disabled={loading || !query.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Building...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    Start Building
                  </div>
                )}
              </Button>
            </div>
          )}
        </div>

        {/* Scrollable Content Area - Calculated height to leave room for input */}
        <div className="flex-1 overflow-hidden" style={{ maxHeight: 'calc(100vh - 280px)' }}>
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              {/* Progress Section */}
              {progressSteps.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Settings className="w-4 h-4 text-blue-400" />
                    <h3 className="font-medium text-sm">Progress</h3>
                  </div>

                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {progressSteps.map((step) => (
                      <div key={step.id} className="flex items-start gap-3 p-2 rounded bg-gray-700">
                        <div className="mt-1">
                          {step.status === 'completed' ? (
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          ) : step.status === 'failed' ? (
                            <div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                              <div className="w-2 h-2 bg-white rounded-full" />
                            </div>
                          ) : (
                            <Clock className="w-4 h-4 text-blue-400 animate-pulse" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-200">{step.title}</p>
                          {step.details && (
                            <p className="text-xs text-gray-400 mt-1">{step.details}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {progress > 0 && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs text-gray-400">
                        <span>Progress</span>
                        <span>{progress}%</span>
                      </div>
                      <Progress value={progress} className="h-2" />
                    </div>
                  )}
                </div>
              )}

              {/* Chat Section */}
              {conversation.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-green-400" />
                    <h3 className="font-medium text-sm">Conversation</h3>
                  </div>

                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {conversation.map((msg, index) => (
                      <div key={`msg-${index}`} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] ${msg.role === 'user'
                            ? 'bg-blue-600 ml-8'
                            : msg.role === 'error'
                              ? 'bg-red-900 border border-red-600'
                              : 'bg-gray-700'
                          } p-3 rounded-lg`}>
                          <div className="whitespace-pre-wrap break-words text-sm">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Input Field - Fixed at bottom with guaranteed visibility */}
        {conversation.length > 0 && (
          <div className="p-3 border-t-4 border-blue-500 bg-gray-800 flex-shrink-0" style={{ minHeight: '120px' }}>
            <div className="text-yellow-400 text-xs mb-2 font-bold">
              💬 Chat Active (Messages: {conversation.length}, State: {buildingState}, Loading: {loading ? 'yes' : 'no'})
            </div>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                placeholder="Type your message here..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !loading && continueBuilding()}
                className="flex-1 px-3 py-2 bg-gray-600 border-2 border-blue-400 rounded-lg text-white placeholder-gray-300 focus:outline-none focus:border-blue-300 text-sm"
                style={{ height: '40px' }}
              />
              <button
                onClick={continueBuilding}
                disabled={loading || !userInput.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg flex items-center gap-2 text-sm"
                style={{ height: '40px' }}
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
                Send
              </button>
            </div>
            <div className="text-xs text-green-400">
              🟢 Input ready - Press Enter or click Send
            </div>
          </div>
        )}
      </div>

      {/* Right Panel - Workflow Visualization */}
      <div className="flex-1 relative h-full">
        {buildingState === 'initial' ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Workflow className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">Workflow Preview</h3>
              <p>Start building to see your workflow visualization</p>
            </div>
          </div>
        ) : (
          <div className="h-full relative">
            {/* Workflow Header */}
            <div className="absolute top-4 left-4 right-4 z-10">
              <div className="flex items-center justify-between bg-gray-800/90 backdrop-blur-sm border border-gray-600 rounded-lg p-3">
                <div>
                  <h3 className="font-medium">Workflow Preview</h3>
                  <p className="text-sm text-gray-400">
                    {nodes.length} connectors • {edges.length} connections
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Eye className="w-4 h-4 mr-1" />
                    Preview
                  </Button>
                  {workflowPlan && (
                    <Button size="sm">
                      <Play className="w-4 h-4 mr-1" />
                      Deploy
                    </Button>
                  )}
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
              nodeTypes={nodeTypes}
              className="bg-gray-900 w-full h-full"
              defaultViewport={{ x: 0, y: 0, zoom: 1 }}
              style={{ width: '100%', height: '100%' }}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
              <Controls className="bg-gray-800 border-gray-600" />
            </ReactFlow>
          </div>
        )}
      </div>

      {showConnectorModal && selectedConnector && (
        <StringLikeConnectorModal
          isOpen={showConnectorModal}
          onClose={() => setShowConnectorModal(false)}
          connectorName={selectedConnector.connector_name || 'Unknown Connector'}
          connectorConfig={selectedConnector.parameters}
          onSave={(config: any) => {
            // Update the node in the React Flow graph
            setNodes(prevNodes => prevNodes.map(node =>
              node.id === selectedConnector.id ? {
                ...node,
                data: {
                  ...node.data,
                  parameters: config,
                  status: 'configured'
                }
              } : node
            ));
            setSelectedConnector(null);
            setShowConnectorModal(false);
          }}
        />
      )}
    </div>
  );
} 