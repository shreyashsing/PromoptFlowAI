'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Loader2, Bot, CheckCircle, Play, ArrowRight, Zap, Settings, MessageSquare, Workflow } from 'lucide-react';
import { workflowReactAPI, workflowAPI } from '@/lib/api';

interface WorkflowBuildResponse {
  message: string;
  session_id: string;
  conversation_state: string;
  workflow_plan?: any;
  reasoning?: any;
  next_steps?: string[];
}

type BuildingState = 'initial' | 'planning' | 'configuring' | 'confirming' | 'approved' | 'completed';

export default function ReactWorkflowBuilder() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [buildingState, setBuildingState] = useState<BuildingState>('initial');
  const [conversation, setConversation] = useState<Array<{role: string, content: string}>>([]);
  const [currentResponse, setCurrentResponse] = useState<WorkflowBuildResponse | null>(null);
  const [userInput, setUserInput] = useState('');
  const [workflowPlan, setWorkflowPlan] = useState<any>(null);

  const startWorkflowBuilding = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setConversation([]);
    setBuildingState('planning');

    try {
      const response: WorkflowBuildResponse = await workflowReactAPI.buildWorkflow({
        query,
        session_id: sessionId || undefined
      });

      setSessionId(response.session_id);
      setCurrentResponse(response);
      setBuildingState(response.conversation_state as BuildingState);
      
      // Add to conversation
      setConversation([
        { role: 'user', content: query },
        { role: 'assistant', content: response.message }
      ]);

      if (response.workflow_plan) {
        setWorkflowPlan(response.workflow_plan);
      }

    } catch (error) {
      console.error('Error starting workflow building:', error);
      setConversation(prev => [...prev, 
        { role: 'error', content: 'Failed to start workflow building. Please try again.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const continueBuilding = async () => {
    if (!userInput.trim() || !sessionId) return;

    setLoading(true);

    try {
      const response: WorkflowBuildResponse = await workflowReactAPI.continueWorkflowBuild({
        message: userInput,
        session_id: sessionId
      });

      setCurrentResponse(response);
      setBuildingState(response.conversation_state as BuildingState);
      
      // Add to conversation
      setConversation(prev => [
        ...prev,
        { role: 'user', content: userInput },
        { role: 'assistant', content: response.message }
      ]);

      if (response.workflow_plan) {
        setWorkflowPlan(response.workflow_plan);
      }

      setUserInput('');

    } catch (error) {
      console.error('Error continuing workflow building:', error);
      setConversation(prev => [...prev, 
        { role: 'error', content: 'Failed to continue building. Please try again.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const executeWorkflow = async (workflowId: string) => {
    if (!workflowId) return;
    
    try {
      setLoading(true);
      const result = await workflowAPI.executeWorkflow(workflowId);
      
      // Show success message
      setConversation(prev => [...prev, {
        role: 'assistant',
        content: `🚀 **Workflow Execution Started!**\n\nExecution ID: ${result.execution_id}\nStatus: ${result.status}\n\nYour workflow is now running. You can monitor its progress in the executions dashboard.`
      }]);
      
    } catch (error) {
      console.error('Error executing workflow:', error);
      setConversation(prev => [...prev, {
        role: 'error',
        content: 'Failed to execute workflow. Please try again or check the workflow configuration.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const resetBuilder = () => {
    setQuery('');
    setUserInput('');
    setSessionId('');
    setBuildingState('initial');
    setConversation([]);
    setCurrentResponse(null);
    setWorkflowPlan(null);
  };

  const getStateIcon = (state: BuildingState) => {
    switch (state) {
      case 'planning': return '🤔';
      case 'configuring': return '🔧';
      case 'confirming': return '✅';
      case 'approved': return '🎉';
      default: return '💭';
    }
  };

  const getStateDescription = (state: BuildingState) => {
    switch (state) {
      case 'planning': return 'AI is analyzing your request and planning the workflow';
      case 'configuring': return 'Configuring connectors step by step';
      case 'confirming': return 'Ready to finalize your workflow';
      case 'approved': return 'Workflow created successfully!';
      default: return 'Ready to start building';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <Bot className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">ReAct Workflow Builder</h1>
        </div>
        <p className="text-muted-foreground">
          Build workflows step-by-step with AI guidance - just like n8n
        </p>
        <div className="flex items-center justify-center gap-2">
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            <Zap className="h-3 w-3 mr-1" />
            ReAct Agent
          </Badge>
          <Badge variant="outline">
            {getStateIcon(buildingState)} {getStateDescription(buildingState)}
          </Badge>
        </div>
      </div>

      {/* Initial Input */}
      {buildingState === 'initial' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Workflow className="h-5 w-5" />
              What workflow would you like to create?
            </CardTitle>
            <CardDescription>
              Describe what you want to automate. The AI will reason through the requirements and guide you step-by-step.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="Examples:
• Send me daily AI news summaries via email
• Get weather data and update a Google Sheet daily  
• Monitor my website and send Slack alerts if it's down
• Scrape product prices and notify me of changes"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="resize-none"
            />
            
            <Button 
              onClick={startWorkflowBuilding}
              disabled={loading || !query.trim()}
              className="w-full"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  AI is reasoning...
                </>
              ) : (
                <>
                  <Bot className="mr-2 h-4 w-4" />
                  Start Building Workflow
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Conversation Flow */}
      {buildingState !== 'initial' && (
        <div className="space-y-4">
          {/* Conversation History */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Workflow Building Conversation
              </CardTitle>
              <CardDescription>
                Follow the AI's guidance to build your workflow step by step
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {conversation.map((msg, index) => (
                  <div key={index} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-3 rounded-lg ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : msg.role === 'error'
                        ? 'bg-red-100 text-red-800 border border-red-200'
                        : 'bg-gray-100 text-gray-900'
                    }`}>
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-2">
                          <Bot className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-medium text-blue-600">AI Assistant</span>
                        </div>
                      )}
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* User Input for Continuing */}
          {buildingState !== 'approved' && (
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Settings className="h-4 w-4" />
                    <span>Your response:</span>
                  </div>
                  
                  <div className="flex gap-2">
                    <Input
                      placeholder={
                        buildingState === 'planning' ? "Say 'yes' to approve the plan or ask for changes..." :
                        buildingState === 'configuring' ? "Provide the required information..." :
                        buildingState === 'confirming' ? "Say 'finalize' to complete the workflow..." :
                        "Type your response..."
                      }
                      value={userInput}
                      onChange={(e) => setUserInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !loading && continueBuilding()}
                      className="flex-1"
                    />
                    <Button 
                      onClick={continueBuilding}
                      disabled={loading || !userInput.trim()}
                    >
                      {loading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <ArrowRight className="h-4 w-4" />
                      )}
                    </Button>
                  </div>

                  {/* Quick Action Buttons */}
                  <div className="flex gap-2">
                    {buildingState === 'planning' && (
                      <>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setUserInput('yes, looks good');
                            setTimeout(continueBuilding, 100);
                          }}
                          disabled={loading}
                        >
                          ✅ Approve Plan
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setUserInput('I need to modify the plan');
                            setTimeout(continueBuilding, 100);
                          }}
                          disabled={loading}
                        >
                          🔄 Modify Plan
                        </Button>
                      </>
                    )}
                    
                    {buildingState === 'confirming' && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          setUserInput('finalize');
                          setTimeout(continueBuilding, 100);
                        }}
                        disabled={loading}
                      >
                        🎯 Finalize Workflow
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Workflow Plan Display */}
          {workflowPlan && (
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
                    {workflowPlan.name}
                  </h3>
                  <p className="text-gray-600 mt-1">
                    {workflowPlan.description}
                  </p>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                    <div>
                      <span className="font-medium">Workflow ID:</span>
                      <br />
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {workflowPlan.id}
                      </code>
                    </div>
                    <div>
                      <span className="font-medium">Automation Steps:</span>
                      <br />
                      <span className="text-lg font-bold text-green-600">
                        {workflowPlan.nodes?.length || 0}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => executeWorkflow(workflowPlan.id)}
                    className="flex-1"
                    size="lg"
                  >
                    <Play className="mr-2 h-4 w-4" />
                    Execute Now
                  </Button>
                  
                  <Button
                    onClick={() => {
                      // Store workflow in localStorage for the visualization page
                      localStorage.setItem('currentWorkflow', JSON.stringify(workflowPlan));
                      // Navigate to workflow editor (you can implement this route)
                      window.open('/workflow-editor', '_blank');
                    }}
                    variant="outline"
                    size="lg"
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    View & Edit
                  </Button>
                  
                  <Button
                    onClick={resetBuilder}
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
                    scheduled to run automatically, or triggered by events. You can also modify it in the workflow editor.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          )}

          {/* Current State Info */}
          {currentResponse && (
            <div className="text-center text-sm text-gray-500">
              <div className="flex items-center justify-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span>State: {buildingState}</span>
                {currentResponse.reasoning?.processing_time_ms && (
                  <>
                    <span>•</span>
                    <span>⚡ {currentResponse.reasoning.processing_time_ms}ms</span>
                  </>
                )}
              </div>
              
              {currentResponse.next_steps && currentResponse.next_steps.length > 0 && (
                <div className="mt-2 text-xs text-gray-400">
                  Next: {currentResponse.next_steps.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}