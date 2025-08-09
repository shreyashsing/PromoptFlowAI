"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Play, 
  Pause, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Settings,
  Loader2,
  Brain,
  MessageSquare,
  Wrench,
  Code
} from 'lucide-react';

interface ReasoningStep {
  step_id: string;
  step_number: number;
  thought: string;
  action: string;
  action_input: any;
  observation: string | null;
  timestamp: string;
  duration_ms: number | null;
  success: boolean;
  error_message: string | null;
}

interface ToolCall {
  tool_name: string;
  input: string;
  output: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  error?: string;
}

interface AgentStatus {
  current_step: number;
  total_steps: number;
  status: 'idle' | 'planning' | 'executing' | 'completed' | 'failed';
  current_action: string;
  progress_percentage: number;
}

type ConnectorStatus = 'idle' | 'running' | 'completed' | 'failed';

interface ReactAgentWorkflowVisualizationProps {
  sessionId: string;
  isActive: boolean;
  onConfigureConnector?: (connectorName: string) => void;
}

export const ReactAgentWorkflowVisualization: React.FC<ReactAgentWorkflowVisualizationProps> = ({
  sessionId,
  isActive,
  onConfigureConnector
}) => {
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    current_step: 0,
    total_steps: 0,
    status: 'idle',
    current_action: '',
    progress_percentage: 0
  });
  const [availableConnectors, setAvailableConnectors] = useState<string[]>([
    'gmail_connector',
    'google_sheets',
    'http_request',
    'perplexity_search',
    'text_summarizer',
    'webhook'
  ]);
  const [activeConnector, setActiveConnector] = useState<string | null>(null);
  
  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!sessionId || !isActive) return;

    const wsUrl = `ws://localhost:8000/api/v1/react/ws/workflow/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to ReAct workflow WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWorkflowUpdate(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from ReAct workflow WebSocket');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [sessionId, isActive]);

  const handleWorkflowUpdate = useCallback((data: any) => {
    switch (data.type) {
      case 'reasoning_step':
        setReasoningSteps(prev => [...prev, data.reasoning_step]);
        setAgentStatus(prev => ({
          ...prev,
          current_step: data.reasoning_step.step_number,
          current_action: data.reasoning_step.action,
          progress_percentage: Math.min((data.reasoning_step.step_number / 10) * 100, 100)
        }));
        break;
        
      case 'tool_call_start':
        setActiveConnector(data.tool_name);
        setToolCalls(prev => [...prev, {
          tool_name: data.tool_name,
          input: data.input,
          output: '',
          status: 'running',
          started_at: new Date().toISOString()
        }]);
        break;
        
      case 'tool_call_complete':
        setActiveConnector(null);
        setToolCalls(prev => prev.map(call => 
          call.tool_name === data.tool_name && call.status === 'running'
            ? {
                ...call,
                output: data.output,
                status: data.success ? 'completed' : 'failed',
                completed_at: new Date().toISOString(),
                error: data.error
              }
            : call
        ));
        break;
        
      case 'agent_status':
        setAgentStatus(prev => ({
          ...prev,
          status: data.status,
          total_steps: data.total_steps || prev.total_steps
        }));
        break;
    }
  }, []);

  const getConnectorIcon = (connectorName: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'gmail_connector': <MessageSquare className="h-4 w-4" />,
      'google_sheets': <Wrench className="h-4 w-4" />,
      'http_request': <Wrench className="h-4 w-4" />,
      'perplexity_search': <Brain className="h-4 w-4" />,
      'text_summarizer': <Brain className="h-4 w-4" />,
      'webhook': <Wrench className="h-4 w-4" />,
      'code': <Code className="h-4 w-4" />
    };
    return iconMap[connectorName] || <Wrench className="h-4 w-4" />;
  };

  const getConnectorStatus = (connectorName: string): ConnectorStatus => {
    if (activeConnector === connectorName) {
      return 'running';
    }
    const lastCall = toolCalls.filter(call => call.tool_name === connectorName).pop();
    return (lastCall?.status as ConnectorStatus) || 'idle';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      default: return 'bg-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executing': 
      case 'running': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'failed': return <XCircle className="h-4 w-4" />;
      case 'planning': return <Brain className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Agent Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon(agentStatus.status)}
            ReAct Agent Workflow
            <Badge variant={agentStatus.status === 'executing' ? 'default' : 'secondary'}>
              {agentStatus.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Progress</span>
                <span>{agentStatus.current_step}/{agentStatus.total_steps || '?'} steps</span>
              </div>
              <Progress value={agentStatus.progress_percentage} className="w-full" />
            </div>
            
            {agentStatus.current_action && (
              <div className="text-sm text-muted-foreground">
                Current: {agentStatus.current_action}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Connector Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Available Connectors</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {availableConnectors.map((connector) => {
              const status = getConnectorStatus(connector);
              const isActive = activeConnector === connector;
              
              return (
                <div
                  key={connector}
                  className={`
                    relative p-4 border rounded-lg transition-all duration-300 cursor-pointer
                    ${isActive ? 'border-blue-500 bg-blue-50 shadow-lg scale-105' : 'border-gray-200 hover:border-gray-300'}
                    ${status === 'completed' ? 'border-green-500 bg-green-50' : ''}
                    ${status === 'failed' ? 'border-red-500 bg-red-50' : ''}
                  `}
                  onClick={() => onConfigureConnector?.(connector)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getConnectorIcon(connector)}
                      <span className="text-sm font-medium">
                        {connector.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(status)}`} />
                  </div>
                  
                  {isActive && (
                    <div className="absolute inset-0 border-2 border-blue-500 rounded-lg pointer-events-none">
                      <div className="absolute -top-1 -right-1">
                        <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                      </div>
                    </div>
                  )}
                  
                  <div className="mt-2 text-xs text-muted-foreground">
                    {status === 'running' && 'Executing...'}
                    {status === 'completed' && 'Completed'}
                    {status === 'failed' && 'Failed'}
                    {status === 'idle' && 'Ready'}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Reasoning Trace */}
      <Card>
        <CardHeader>
          <CardTitle>Reasoning Trace</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-80">
            <div className="space-y-4">
              {reasoningSteps.map((step, index) => (
                <div key={step.step_id} className="border-l-2 border-gray-200 pl-4">
                  <div className="flex items-start gap-2 mb-2">
                    <Badge variant="outline">Step {step.step_number}</Badge>
                    {step.success ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                    )}
                    <span className="text-xs text-muted-foreground">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">Thought:</span> {step.thought}
                    </div>
                    
                    {step.action && (
                      <div>
                        <span className="font-medium">Action:</span> {step.action}
                      </div>
                    )}
                    
                    {step.action_input && (
                      <div>
                        <span className="font-medium">Input:</span>
                        <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                          {JSON.stringify(step.action_input, null, 2)}
                        </pre>
                      </div>
                    )}
                    
                    {step.observation && (
                      <div>
                        <span className="font-medium">Observation:</span> {step.observation}
                      </div>
                    )}
                    
                    {step.error_message && (
                      <div className="text-red-600">
                        <span className="font-medium">Error:</span> {step.error_message}
                      </div>
                    )}
                  </div>
                  
                  {index < reasoningSteps.length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </div>
              ))}
              
              {reasoningSteps.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  No reasoning steps yet. Start a conversation to see the agent's thinking process.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Tool Calls History */}
      <Card>
        <CardHeader>
          <CardTitle>Tool Execution History</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-60">
            <div className="space-y-3">
              {toolCalls.map((call, index) => (
                <div key={index} className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getConnectorIcon(call.tool_name)}
                      <span className="font-medium">{call.tool_name}</span>
                    </div>
                    <Badge variant={call.status === 'completed' ? 'default' : call.status === 'failed' ? 'destructive' : 'secondary'}>
                      {call.status}
                    </Badge>
                  </div>
                  
                  <div className="text-sm space-y-1">
                    <div>
                      <span className="font-medium">Input:</span> {call.input.substring(0, 100)}...
                    </div>
                    
                    {call.output && (
                      <div>
                        <span className="font-medium">Output:</span> {call.output.substring(0, 100)}...
                      </div>
                    )}
                    
                    {call.error && (
                      <div className="text-red-600">
                        <span className="font-medium">Error:</span> {call.error}
                      </div>
                    )}
                    
                    <div className="text-xs text-muted-foreground">
                      Started: {new Date(call.started_at).toLocaleTimeString()}
                      {call.completed_at && (
                        <> | Completed: {new Date(call.completed_at).toLocaleTimeString()}</>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {toolCalls.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  No tool calls yet. Tools will appear here as the agent uses them.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}; 