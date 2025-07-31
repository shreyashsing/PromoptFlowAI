'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Bot, CheckCircle, Play, ArrowRight, Zap, Settings, Eye } from 'lucide-react';
import { workflowReactAPI } from '@/lib/api';

interface ReasoningStep {
  step: number;
  thought: string;
  action?: string;
  tool_name?: string;
  status: 'thinking' | 'acting' | 'completed' | 'error';
  result?: string;
}

interface ToolCall {
  tool_name: string;
  parameters: any;
  result?: string;
  status: 'pending' | 'running' | 'completed' | 'error';
}

interface WorkflowPlan {
  id: string;
  name: string;
  description: string;
  nodes: any[];
  edges: any[];
}

interface ConversationalResponse {
  response: string;
  session_id: string;
  reasoning_trace: ReasoningStep[];
  tool_calls: ToolCall[];
  workflow_created: boolean;
  workflow_id?: string;
  workflow_plan?: WorkflowPlan;
  status: string;
  processing_time_ms?: number;
}

export default function IntegratedWorkflowInterface() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ConversationalResponse | null>(null);
  const [sessionId, setSessionId] = useState<string>('');
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [activeTab, setActiveTab] = useState('progress');

  const createWorkflowConversationally = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);
    setCurrentStep(0);
    setShowWorkflow(false);

    try {
      const data: ConversationalResponse = await workflowReactAPI.createWorkflowConversationally({
        query,
        session_id: sessionId || undefined,
        context: { interface: 'web' },
        max_iterations: 15,
        save_as_workflow: true,
      });
        setResponse(data);
      setSessionId(data.session_id);
      
      // Simulate step-by-step progression
      if (data.reasoning_trace.length > 0) {
        for (let i = 0; i <= data.reasoning_trace.length; i++) {
          setTimeout(() => {
            setCurrentStep(i);
            if (i === data.reasoning_trace.length && data.workflow_created) {
              setTimeout(() => {
                setShowWorkflow(true);
                // Auto-switch to Preview tab when workflow is ready
                setActiveTab('preview');
              }, 1000);
            }
          }, i * 1500);
        }
      } else if (data.workflow_created) {
        setTimeout(() => {
          setShowWorkflow(true);
          setActiveTab('preview');
        }, 1000);
      }
    } catch (error) {
      console.error('Error creating workflow:', error);
    } finally {
      setLoading(false);
    }
  };

  const executeWorkflow = async (workflowId: string) => {
    try {
      const data = await workflowReactAPI.executeWorkflowInteractively(workflowId, {
        workflow_id: workflowId,
        parameters: {},
        interactive_mode: false, // Manual execution
      });
      
      alert('Workflow execution started! Check the executions tab for progress.');
    } catch (error) {
      console.error('Error executing workflow:', error);
    }
  };

  const resetInterface = () => {
    setQuery('');
    setResponse(null);
    setCurrentStep(0);
    setShowWorkflow(false);
    setSessionId('');
    setActiveTab('progress');
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <Bot className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">AI Workflow Builder</h1>
        </div>
        <p className="text-muted-foreground">
          Describe what you want to automate, and I'll create a workflow for you
        </p>
        <Badge variant="secondary" className="bg-green-100 text-green-800">
          <Zap className="h-3 w-3 mr-1" />
          Powered by ReAct Agent • No Setup Required
        </Badge>
      </div>

      {/* Main Input */}
      {!response && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              What would you like to automate?
            </CardTitle>
            <CardDescription>
              Be specific about what you want to accomplish. I'll figure out the steps and tools needed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="Examples:
• Search for latest AI news and email me a summary
• Get weather data and update a Google Sheet daily  
• Monitor my website and send alerts if it's down
• Scrape product prices and notify me of changes"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="resize-none"
            />
            
            <Button 
              onClick={createWorkflowConversationally}
              disabled={loading || !query.trim()}
              className="w-full"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  AI is thinking and planning...
                </>
              ) : (
                <>
                  <Bot className="mr-2 h-4 w-4" />
                  Create My Workflow
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* AI Reasoning Process with Tabs */}
      {response && (
        <div className="space-y-4">
          {/* Agent Response */}
          <Alert className="border-blue-200 bg-blue-50">
            <Bot className="h-4 w-4" />
            <AlertDescription className="text-blue-800">
              <strong>AI Agent:</strong> {response.response}
            </AlertDescription>
          </Alert>

          {/* Tabbed Interface */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="progress" className="flex items-center gap-2">
                <Loader2 className="h-4 w-4" />
                Progress
              </TabsTrigger>
              <TabsTrigger value="preview" className="flex items-center gap-2">
                <Eye className="h-4 w-4" />
                Preview
              </TabsTrigger>
            </TabsList>

            <TabsContent value="progress" className="space-y-4 mt-4">

          {/* Reasoning Steps */}
          {response.reasoning_trace.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">🧠 AI Reasoning Process</CardTitle>
                <CardDescription>
                  Watch how the AI thinks through your request step by step
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {response.reasoning_trace.slice(0, currentStep).map((step, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                        {step.step}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          💭 <strong>Thinking:</strong> {step.thought}
                        </p>
                        {step.action && (
                          <p className="text-sm text-blue-600 mt-1">
                            ⚡ <strong>Action:</strong> {step.action}
                          </p>
                        )}
                        {step.tool_name && (
                          <Badge variant="outline" className="mt-2">
                            🔧 {step.tool_name}
                          </Badge>
                        )}
                      </div>
                      <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                    </div>
                  ))}
                  
                  {currentStep < response.reasoning_trace.length && (
                    <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border-2 border-yellow-200">
                      <Loader2 className="h-5 w-5 animate-spin text-yellow-600" />
                      <span className="text-sm text-yellow-800">AI is working on the next step...</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tool Execution */}
          {response.tool_calls.length > 0 && currentStep >= response.reasoning_trace.length && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">🔧 Tools & Connectors Used</CardTitle>
                <CardDescription>
                  These connectors were selected and executed by the AI
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3">
                  {response.tool_calls.map((call, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center">
                        <CheckCircle className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-green-800">{call.tool_name}</p>
                        <p className="text-sm text-green-600">
                          Executed successfully with parameters
                        </p>
                      </div>
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        Completed
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Generated Workflow */}
          {showWorkflow && response.workflow_created && response.workflow_plan && (
            <Card className="border-2 border-green-200 bg-green-50">
              <CardHeader>
                <CardTitle className="text-lg text-green-800 flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  🎉 Workflow Created Successfully!
                </CardTitle>
                <CardDescription className="text-green-700">
                  Your automation workflow is ready to use
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-white p-4 rounded-lg border border-green-200">
                  <h3 className="font-semibold text-lg text-gray-900">
                    {response.workflow_plan.name}
                  </h3>
                  <p className="text-gray-600 mt-1">
                    {response.workflow_plan.description}
                  </p>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                    <div>
                      <span className="font-medium">Workflow ID:</span>
                      <br />
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {response.workflow_plan.id}
                      </code>
                    </div>
                    <div>
                      <span className="font-medium">Automation Steps:</span>
                      <br />
                      <span className="text-lg font-bold text-green-600">
                        {response.workflow_plan.nodes.length}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={() => response.workflow_id && executeWorkflow(response.workflow_id)}
                    className="flex-1"
                    size="lg"
                  >
                    <Play className="mr-2 h-4 w-4" />
                    Execute Workflow Now
                  </Button>
                  
                  <Button
                    onClick={resetInterface}
                    variant="outline"
                    size="lg"
                  >
                    Create Another
                  </Button>
                </div>

                <Alert>
                  <ArrowRight className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Next Steps:</strong> Your workflow has been saved and can be executed manually, 
                    scheduled to run automatically, or triggered by events. You can also modify it later 
                    in the workflow editor.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          )}

              {/* Processing Time */}
              {response.processing_time_ms && (
                <div className="text-center text-sm text-gray-500">
                  ⚡ Completed in {response.processing_time_ms}ms
                </div>
              )}
            </TabsContent>

            <TabsContent value="preview" className="space-y-4 mt-4">
              {/* Workflow Preview Section */}
              {response.workflow_plan && (
                <Card className="border-2 border-blue-200 bg-blue-50">
                  <CardHeader>
                    <CardTitle className="text-lg text-blue-800 flex items-center gap-2">
                      <Eye className="h-5 w-5" />
                      🔧 Workflow Preview
                    </CardTitle>
                    <CardDescription className="text-blue-700">
                      {response.workflow_plan.description || 'AI-generated workflow ready for configuration'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {/* Workflow Visualization */}
                    <div className="bg-white rounded-lg border p-4 mb-4">
                      <h4 className="font-medium text-gray-900 mb-3">
                        Connectors ({response.workflow_plan.nodes?.length || 0})
                      </h4>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {response.workflow_plan.nodes?.map((node: any, index: number) => (
                          <div key={node.id} className="border rounded-lg p-3 hover:shadow-md transition-shadow bg-white">
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-medium text-sm text-gray-900">
                                {node.connector_name?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'Unknown Connector'}
                              </h5>
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                Step {index + 1}
                              </span>
                            </div>
                            
                            <div className="text-xs text-gray-600 mb-2">
                              <strong>Parameters:</strong>
                            </div>
                            
                            <div className="space-y-1">
                              {Object.entries(node.parameters || {}).slice(0, 3).map(([key, value]: [string, any]) => (
                                <div key={key} className="text-xs">
                                  <span className="font-medium text-gray-700">{key}:</span>
                                  <span className="text-gray-600 ml-1">
                                    {typeof value === 'string' && value.length > 30 
                                      ? `${value.substring(0, 30)}...` 
                                      : String(value)
                                    }
                                  </span>
                                </div>
                              ))}
                              {Object.keys(node.parameters || {}).length > 3 && (
                                <div className="text-xs text-gray-500">
                                  +{Object.keys(node.parameters).length - 3} more parameters
                                </div>
                              )}
                            </div>
                            
                            <button 
                              className="mt-2 w-full text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 py-1 px-2 rounded transition-colors flex items-center justify-center gap-1"
                              onClick={() => {
                                // TODO: Open connector configuration modal
                                console.log('Configure connector:', node.connector_name);
                                alert(`Configure ${node.connector_name} - Coming soon!`);
                              }}
                            >
                              <Settings className="h-3 w-3" />
                              Configure
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    {/* Workflow Actions */}
                    {response.workflow_created && (
                      <div className="flex gap-2 justify-end">
                        <Button 
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            // TODO: Open workflow editor
                            console.log('Edit workflow:', response.workflow_plan?.id);
                            alert('Workflow editor - Coming soon!');
                          }}
                        >
                          ✏️ Edit Workflow
                        </Button>
                        
                        <Button 
                          size="sm"
                          onClick={() => response.workflow_id && executeWorkflow(response.workflow_id)}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          🚀 Execute Workflow
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* No workflow message */}
              {!response.workflow_plan && (
                <Card>
                  <CardContent className="text-center py-8">
                    <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">
                      No workflow preview available yet. The AI is still working on creating your workflow.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}