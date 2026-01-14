'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Play, 
  Square, 
  RefreshCw, 
  Clock, 
  CheckCircle, 
  XCircle,
  Eye,
  Code,
  Database,
  ArrowRight,
  AlertTriangle,
  Info
} from 'lucide-react';
import { supabase } from '@/lib/supabase';

interface NodeExecutionResult {
  success: boolean;
  execution_id: string;
  connector_name: string;
  output_data: any;
  formatted_output?: string;
  execution_time_ms: number;
  timestamp: string;
  error_message?: string;
  metadata: Record<string, any>;
}

interface NodeDataSidebarProps {
  selectedNode: any;
  isExecuting: boolean;
  onExecuteNode: (nodeId: string) => Promise<void>;
  onExecuteNodeSequential?: (nodeId: string) => Promise<void>;
  executionResults: Record<string, NodeExecutionResult>;
  sequentialResults?: Record<string, NodeExecutionResult>;
  previousNodeId?: string | null;
}

export const NodeDataSidebar: React.FC<NodeDataSidebarProps> = ({
  selectedNode,
  isExecuting,
  onExecuteNode,
  onExecuteNodeSequential,
  executionResults,
  sequentialResults = {},
  previousNodeId = null
}) => {
  const [activeTab, setActiveTab] = useState<string>('preview');
  const [dataPreview, setDataPreview] = useState<any>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);

  const nodeId = selectedNode?.id;
  const connectorName = selectedNode?.data?.connector_name || selectedNode?.type;
  const executionResult = nodeId ? executionResults[nodeId] : null;

  // Load data preview when connector changes
  useEffect(() => {
    if (connectorName && activeTab === 'preview') {
      loadDataPreview();
    }
  }, [connectorName, activeTab]);

  const loadDataPreview = async () => {
    if (!connectorName) return;
    
    setIsLoadingPreview(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/nodes/preview/${connectorName}`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const preview = await response.json();
        setDataPreview(preview);
      }
    } catch (error) {
      console.error('Error loading data preview:', error);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleExecuteNode = async () => {
    if (nodeId) {
      await onExecuteNode(nodeId);
    }
  };

  const formatJsonData = (data: any): string => {
    try {
      return JSON.stringify(data, null, 2);
    } catch (error) {
      return String(data);
    }
  };

  const getExecutionStatusIcon = () => {
    if (isExecuting) {
      return <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />;
    }
    if (executionResult?.success) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    if (executionResult?.success === false) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    }
    return <Play className="w-4 h-4 text-gray-500" />;
  };

  const getExecutionStatusText = () => {
    if (isExecuting) return 'Executing...';
    if (executionResult?.success) return 'Success';
    if (executionResult?.success === false) return 'Failed';
    return 'Ready to execute';
  };

  if (!selectedNode) {
    return (
      <div className="w-96 bg-gray-900 border-l border-gray-700 flex items-center justify-center p-8">
        <div className="text-center text-gray-400">
          <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm">Select a node to view its data</p>
          <p className="text-xs mt-2 opacity-75">
            Click on any workflow node to see its configuration and execution results
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-96 bg-gray-900 border-l border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white truncate">
            {selectedNode.data?.label || connectorName || 'Node'}
          </h3>
          <Badge variant="outline" className="text-xs">
            {connectorName}
          </Badge>
        </div>
        
        {/* Execution Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getExecutionStatusIcon()}
            <span className="text-sm text-gray-300">{getExecutionStatusText()}</span>
          </div>
          
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleExecuteNode}
              disabled={isExecuting}
              className="bg-blue-600 hover:bg-blue-700 flex-1"
            >
              {isExecuting ? (
                <>
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                  Running
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 mr-1" />
                  Execute
                </>
              )}
            </Button>
            
            {/* Sequential execution button - shown when there's a previous node and sequential function is available */}
            {previousNodeId && onExecuteNodeSequential && (
              <Button
                size="sm"
                onClick={() => onExecuteNodeSequential(selectedNode.id)}
                disabled={isExecuting}
                variant="outline"
                className="border-green-600 text-green-400 hover:bg-green-600 hover:text-white flex-1"
                title="Execute with previous node's results"
              >
                {isExecuting ? (
                  <>
                    <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                    Chain
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 mr-1" />
                    Chain Execute
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Execution Metadata */}
        {executionResult && (
          <div className="mt-2 text-xs text-gray-400 flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {executionResult.execution_time_ms}ms
            </div>
            <div>
              {new Date(executionResult.timestamp).toLocaleTimeString()}
            </div>
          </div>
        )}
      </div>

      {/* Content Tabs */}
      <div className="flex-1 flex flex-col min-h-0">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-4 bg-gray-800 flex-shrink-0">
            <TabsTrigger value="preview" className="text-xs">
              <Eye className="w-3 h-3 mr-1" />
              Preview
            </TabsTrigger>
            <TabsTrigger value="output" className="text-xs">
              <Database className="w-3 h-3 mr-1" />
              Output
            </TabsTrigger>
            <TabsTrigger value="flow" className="text-xs">
              <ArrowRight className="w-3 h-3 mr-1" />
              Flow
            </TabsTrigger>
            <TabsTrigger value="config" className="text-xs">
              <Code className="w-3 h-3 mr-1" />
              Config
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 flex flex-col min-h-0">
            <TabsContent value="preview" className="flex-1 m-0 p-0 data-[state=active]:flex data-[state=active]:flex-col min-h-0">
              <ScrollArea className="flex-1 p-4">
                {isLoadingPreview ? (
                  <div className="flex items-center justify-center p-8">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
                    <span className="ml-2 text-gray-400">Loading preview...</span>
                  </div>
                ) : dataPreview ? (
                  <div className="space-y-4">
                    <Card className="bg-gray-800 border-gray-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-gray-200">Data Structure</CardTitle>
                      </CardHeader>
                      <CardContent className="text-xs">
                        <div className="space-y-2">
                          <div>
                            <span className="text-gray-400">Category:</span>
                            <span className="ml-2 text-green-400">
                              {dataPreview.data_structure?.connector_category || 'unknown'}
                            </span>
                          </div>
                          {dataPreview.record_count && (
                            <div>
                              <span className="text-gray-400">Expected Records:</span>
                              <span className="ml-2 text-blue-400">{dataPreview.record_count}</span>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-gray-800 border-gray-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-gray-200">Sample Output</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-3 rounded">
                          {formatJsonData(dataPreview.sample_data)}
                        </pre>
                      </CardContent>
                    </Card>

                    {dataPreview.data_types && Object.keys(dataPreview.data_types).length > 0 && (
                      <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm text-gray-200">Data Types</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-1">
                            {Object.entries(dataPreview.data_types).map(([key, type]) => (
                              <div key={key} className="flex justify-between text-xs">
                                <span className="text-gray-300">{key}:</span>
                                <span className="text-yellow-400">{String(type)}</span>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-gray-400 p-8">
                    <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No preview available</p>
                    <p className="text-xs mt-1">Execute the node to see output data</p>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="output" className="flex-1 m-0 p-0 data-[state=active]:flex data-[state=active]:flex-col min-h-0">
              <ScrollArea className="flex-1 p-4">
                {executionResult ? (
                  <div className="space-y-4">
                    {/* Handle new format with status */}
                    {(executionResult as any).status === 'error' ? (
                      <Card className="bg-yellow-900/20 border-yellow-700/50">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm text-yellow-400 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" />
                            Configuration Required
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="text-xs space-y-3">
                          <div className="text-yellow-300 mb-2">
                            {(executionResult as any).error}
                          </div>
                          
                          {(executionResult as any).error?.includes('Authentication required') && (
                            <div className="bg-gray-800 border border-gray-600 rounded p-3">
                              <div className="text-yellow-400 text-sm font-medium mb-2">
                                💡 Configuration Needed:
                              </div>
                              <div className="text-gray-300 text-xs mb-2">
                                This AI-generated node needs authentication setup.
                              </div>
                              <ol className="text-gray-300 text-xs space-y-1 list-decimal list-inside mb-3">
                                <li>Double-click on the {connectorName || 'connector'} node to open configuration</li>
                                <li>Go to the "Authentication" or "API Key" tab</li>
                                <li>Add your {(connectorName || 'connector').replace('_', ' ')} API key</li>
                                <li>Save configuration and try executing again</li>
                              </ol>
                            </div>
                          )}
                          
                          <div className="text-gray-400 text-xs">
                            Time: {(executionResult as any).timestamp ? new Date((executionResult as any).timestamp).toLocaleTimeString() : 'Unknown'}
                          </div>
                        </CardContent>
                      </Card>
                    ) : executionResult.success ? (
                      <>
                        <Card className="bg-green-900/20 border-green-700/50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm text-green-400 flex items-center gap-2">
                              <CheckCircle className="w-4 h-4" />
                              Execution Successful
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="text-xs text-gray-300">
                            <div>Execution ID: {executionResult.execution_id}</div>
                            <div>Time: {executionResult.execution_time_ms}ms</div>
                          </CardContent>
                        </Card>

                        <Card className="bg-gray-800 border-gray-700">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm text-gray-200">Output Data</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-3 rounded max-h-96">
                              {formatJsonData(executionResult.output_data)}
                            </pre>
                          </CardContent>
                        </Card>

                        {executionResult.formatted_output && (
                          <Card className="bg-gray-800 border-gray-700">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm text-gray-200">Formatted Output</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="text-xs text-gray-300 whitespace-pre-wrap">
                                {executionResult.formatted_output}
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </>
                    ) : (
                      <Card className={`border-red-700/50 ${
                        executionResult.metadata?.error_type === 'authentication_error' 
                          ? 'bg-yellow-900/20 border-yellow-700/50' 
                          : 'bg-red-900/20'
                      }`}>
                        <CardHeader className="pb-2">
                          <CardTitle className={`text-sm flex items-center gap-2 ${
                            executionResult.metadata?.error_type === 'authentication_error' 
                              ? 'text-yellow-400' 
                              : 'text-red-400'
                          }`}>
                            {executionResult.metadata?.error_type === 'authentication_error' ? (
                              <>
                                <AlertTriangle className="w-4 h-4" />
                                Authentication Required
                              </>
                            ) : (
                              <>
                                <XCircle className="w-4 h-4" />
                                Execution Failed
                              </>
                            )}
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="text-xs space-y-3">
                          <div className={`mb-2 ${
                            executionResult.metadata?.error_type === 'authentication_error' 
                              ? 'text-yellow-300' 
                              : 'text-red-300'
                          }`}>
                            {executionResult.error_message || 'Unknown error occurred'}
                          </div>
                          
                          {executionResult.metadata?.error_type === 'authentication_error' && (
                            <div className="bg-gray-800 border border-gray-600 rounded p-3">
                              <div className="text-yellow-400 text-sm font-medium mb-2">
                                💡 Configuration Needed:
                              </div>
                              <div className="text-gray-300 text-xs mb-2">
                                This AI-generated node needs authentication setup.
                              </div>
                              <ol className="text-gray-300 text-xs space-y-1 list-decimal list-inside mb-3">
                                <li>Click on the {connectorName || 'connector'} node to select it</li>
                                <li>The configuration modal will open automatically</li>
                                <li>Go to the "Authentication" or "Settings" tab</li>
                                <li>Add your {(connectorName || 'connector').replace('_', ' ')} API key</li>
                                <li>Save and try executing again</li>
                              </ol>
                              <button
                                onClick={() => {
                                  // Try to trigger node selection
                                  const event = new CustomEvent('nodeSelect', { 
                                    detail: { nodeId: selectedNode.id } 
                                  });
                                  window.dispatchEvent(event);
                                }}
                                className="bg-yellow-600 hover:bg-yellow-700 text-white text-xs px-3 py-1.5 rounded transition-colors"
                              >
                                Configure Authentication
                              </button>
                            </div>
                          )}
                          
                          <div className="text-gray-400">
                            Execution ID: {executionResult.execution_id}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-gray-400 p-8">
                    <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No execution results</p>
                    <p className="text-xs mt-1">Click Execute to run this node and see output</p>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="flow" className="flex-1 m-0 p-0 data-[state=active]:flex data-[state=active]:flex-col min-h-0">
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {previousNodeId && sequentialResults[previousNodeId] ? (
                    <>
                      <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm text-gray-200 flex items-center gap-2">
                            <ArrowRight className="w-4 h-4" />
                            Previous Node Data
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-xs text-gray-400 mb-2">
                            From: {sequentialResults[previousNodeId].connector_name} ({previousNodeId})
                          </div>
                          <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-3 rounded max-h-40">
                            {formatJsonData(sequentialResults[previousNodeId].output_data)}
                          </pre>
                        </CardContent>
                      </Card>
                      
                      <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm text-gray-200">Data Flow Chain</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 text-xs">
                              <div className="w-3 h-3 bg-green-500 rounded-full flex-shrink-0"></div>
                              <span className="text-gray-300">{sequentialResults[previousNodeId].connector_name}</span>
                              <ArrowRight className="w-3 h-3 text-gray-500" />
                              <span className="text-blue-400">{connectorName}</span>
                            </div>
                            <div className="text-xs text-gray-500 ml-5">
                              Sequential execution with data passing
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {sequentialResults[selectedNode.id] && (
                        <Card className="bg-gray-800 border-gray-700">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm text-gray-200">Current Node Output</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-3 rounded max-h-40">
                              {formatJsonData(sequentialResults[selectedNode.id].output_data)}
                            </pre>
                          </CardContent>
                        </Card>
                      )}
                    </>
                  ) : (
                    <div className="text-center text-gray-400 p-8">
                      <ArrowRight className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Sequential Data Flow</p>
                      <p className="text-xs mt-1">
                        {previousNodeId 
                          ? `Waiting for previous node (${previousNodeId}) to execute`
                          : 'This is the first node in the sequence'
                        }
                      </p>
                      {previousNodeId && (
                        <div className="mt-3 text-xs text-blue-400">
                          💡 Execute the previous node first to see data flow
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="config" className="flex-1 m-0 p-0 data-[state=active]:flex data-[state=active]:flex-col min-h-0">
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  <Card className="bg-gray-800 border-gray-700">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm text-gray-200">Node Configuration</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-3 rounded">
                        {formatJsonData({
                          connector_name: connectorName,
                          parameters: selectedNode.data?.parameters || {},
                          position: selectedNode.position || {},
                          ...selectedNode.data
                        })}
                      </pre>
                    </CardContent>
                  </Card>

                  {selectedNode.data?.dependencies && selectedNode.data.dependencies.length > 0 && (
                    <Card className="bg-gray-800 border-gray-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-gray-200">Dependencies</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {selectedNode.data.dependencies.map((dep: string, index: number) => (
                            <div key={index} className="flex items-center gap-2 text-xs">
                              <ArrowRight className="w-3 h-3 text-gray-500" />
                              <span className="text-blue-400">{dep}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
};

export default NodeDataSidebar;
