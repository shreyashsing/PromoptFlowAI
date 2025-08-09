'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CodeConnector } from '@/components/connectors/code/CodeConnector';
import { CodeConnectorModal } from '@/components/connectors/code/CodeConnectorModal';
import { 
  Code2, 
  Play, 
  Settings, 
  Info, 
  CheckCircle, 
  AlertTriangle,
  Zap,
  Shield,
  Clock,
  Cpu
} from 'lucide-react';

export default function CodeConnectorDemo() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [connectorConfig, setConnectorConfig] = useState<any>(null);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleSaveConfig = async (config: any) => {
    setConnectorConfig(config);
    console.log('Code connector configured:', config);
  };

  const handleTestExecution = async () => {
    if (!connectorConfig) return;
    
    setIsExecuting(true);
    setExecutionResult(null);
    
    try {
      // Mock execution - in real implementation, this would call the backend
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate execution time
      
      const mockResult = {
        success: true,
        data: {
          items: [
            { 
              json: { 
                name: "John Doe", 
                age: 30, 
                processed: true,
                timestamp: new Date().toISOString()
              } 
            },
            { 
              json: { 
                name: "Jane Smith", 
                age: 25, 
                processed: true,
                timestamp: new Date().toISOString()
              } 
            }
          ],
          console_output: "Processing completed successfully\nProcessed 2 items",
          execution_time: 0.156
        },
        metadata: {
          language: connectorConfig.language,
          mode: connectorConfig.mode,
          items_processed: 2,
          safe_mode: connectorConfig.safe_mode
        }
      };
      
      setExecutionResult(mockResult);
    } catch (error) {
      setExecutionResult({
        success: false,
        error: 'Execution failed: ' + (error as Error).message
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const sampleConfigs = [
    {
      name: "Data Transformation",
      description: "Transform JSON data with JavaScript",
      config: {
        language: "javascript",
        mode: "runOnceForAllItems",
        code: `// Transform all items by adding processed flag
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString(),
    name_upper: item.json.name?.toUpperCase()
  }
}));`,
        timeout: 30,
        safe_mode: true,
        allow_network: false,
        allow_file_system: false,
        max_memory_mb: 128,
        return_console_output: true
      }
    },
    {
      name: "Python Data Analysis",
      description: "Analyze data using Python",
      config: {
        language: "python",
        mode: "runOnceForAllItems",
        code: `# Analyze data with Python
import json
from datetime import datetime

# Calculate statistics
ages = [item["json"].get("age", 0) for item in items]
total_age = sum(ages)
average_age = total_age / len(ages) if ages else 0

result = [{
    "json": {
        "analysis": {
            "total_people": len(items),
            "average_age": round(average_age, 2),
            "oldest": max(ages) if ages else 0,
            "youngest": min(ages) if ages else 0
        },
        "timestamp": datetime.now().isoformat()
    }
}]

print(f"Analyzed {len(items)} people")
print(f"Average age: {average_age:.2f}")`,
        timeout: 30,
        safe_mode: true,
        allow_network: false,
        allow_file_system: false,
        max_memory_mb: 128,
        return_console_output: true
      }
    },
    {
      name: "Item Processing",
      description: "Process each item individually",
      config: {
        language: "javascript",
        mode: "runOnceForEachItem",
        code: `// Process individual item
console.log('Processing:', item.json.name);

return {
  json: {
    ...item.json,
    processed: true,
    age_category: item.json.age >= 18 ? 'adult' : 'minor',
    processing_time: new Date().toISOString()
  }
};`,
        timeout: 30,
        safe_mode: true,
        allow_network: false,
        allow_file_system: false,
        max_memory_mb: 128,
        return_console_output: true
      }
    }
  ];

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center space-x-3">
          <div className="p-3 bg-purple-100 rounded-lg">
            <Code2 className="h-8 w-8 text-purple-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Code Connector Demo</h1>
            <p className="text-gray-600">Execute custom JavaScript or Python code with sandboxing</p>
          </div>
        </div>

        <div className="flex items-center justify-center space-x-4">
          <Badge className="bg-purple-100 text-purple-800 border-purple-200">
            JavaScript Support
          </Badge>
          <Badge className="bg-blue-100 text-blue-800 border-blue-200">
            Python Support
          </Badge>
          <Badge className="bg-green-100 text-green-800 border-green-200">
            Sandboxed Execution
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="demo" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="demo">Interactive Demo</TabsTrigger>
          <TabsTrigger value="features">Features</TabsTrigger>
          <TabsTrigger value="examples">Code Examples</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="demo" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Connector Configuration */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center space-x-2">
                <Settings className="h-5 w-5" />
                <span>Connector Configuration</span>
              </h2>
              
              <CodeConnector
                config={connectorConfig}
                onConfigure={() => setIsModalOpen(true)}
                onTest={handleTestExecution}
                isConfigured={!!connectorConfig}
              />

              {/* Sample Configurations */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Quick Start Templates</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {sampleConfigs.map((sample, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <h4 className="font-medium text-sm">{sample.name}</h4>
                        <p className="text-xs text-gray-500">{sample.description}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setConnectorConfig(sample.config)}
                      >
                        Load
                      </Button>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            {/* Execution Results */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center space-x-2">
                  <Play className="h-5 w-5" />
                  <span>Execution Results</span>
                </h2>
                {connectorConfig && (
                  <Button
                    onClick={handleTestExecution}
                    disabled={isExecuting}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    {isExecuting ? 'Executing...' : 'Run Code'}
                  </Button>
                )}
              </div>

              {!connectorConfig && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Configure the connector above or load a template to see execution results.
                  </AlertDescription>
                </Alert>
              )}

              {isExecuting && (
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                      <span>Executing code...</span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {executionResult && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center space-x-2">
                      {executionResult.success ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                      )}
                      <span>Execution Result</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {executionResult.success ? (
                      <div className="space-y-4">
                        {/* Metadata */}
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="font-medium">Language:</span> {executionResult.metadata?.language}
                          </div>
                          <div>
                            <span className="font-medium">Mode:</span> {executionResult.metadata?.mode}
                          </div>
                          <div>
                            <span className="font-medium">Items Processed:</span> {executionResult.metadata?.items_processed}
                          </div>
                          <div>
                            <span className="font-medium">Execution Time:</span> {executionResult.data?.execution_time}s
                          </div>
                        </div>

                        {/* Console Output */}
                        {executionResult.data?.console_output && (
                          <div>
                            <h4 className="font-medium text-sm mb-2">Console Output:</h4>
                            <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto">
                              {executionResult.data.console_output}
                            </pre>
                          </div>
                        )}

                        {/* Result Data */}
                        <div>
                          <h4 className="font-medium text-sm mb-2">Result Data:</h4>
                          <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto max-h-64">
                            {JSON.stringify(executionResult.data?.items || executionResult.data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    ) : (
                      <div className="text-red-600">
                        <p className="font-medium">Execution Failed:</p>
                        <p className="text-sm">{executionResult.error}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="features" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Code2 className="h-4 w-4 text-purple-600" />
                  <span>Multi-Language Support</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• JavaScript (Node.js runtime)</li>
                  <li>• Python 3.x support</li>
                  <li>• Syntax validation</li>
                  <li>• Error handling & reporting</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Zap className="h-4 w-4 text-yellow-600" />
                  <span>Execution Modes</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• Run once for all items</li>
                  <li>• Run once for each item</li>
                  <li>• Configurable timeouts</li>
                  <li>• Memory limits</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Shield className="h-4 w-4 text-green-600" />
                  <span>Security Features</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• Sandboxed execution</li>
                  <li>• Safe mode restrictions</li>
                  <li>• Network access control</li>
                  <li>• File system protection</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-blue-600" />
                  <span>Performance Controls</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• Configurable timeouts (1-300s)</li>
                  <li>• Memory limits (16-1024MB)</li>
                  <li>• Execution time tracking</li>
                  <li>• Resource monitoring</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Info className="h-4 w-4 text-indigo-600" />
                  <span>Debugging Support</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• Console output capture</li>
                  <li>• Error line numbers</li>
                  <li>• Stack trace information</li>
                  <li>• Validation feedback</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Cpu className="h-4 w-4 text-red-600" />
                  <span>Data Processing</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-2">
                  <li>• JSON data transformation</li>
                  <li>• Array processing</li>
                  <li>• Custom business logic</li>
                  <li>• Data validation</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="examples" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">JavaScript - Data Transformation</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto">
{`// Transform all items
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString(),
    name_upper: item.json.name?.toUpperCase()
  }
}));`}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Python - Data Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto">
{`# Analyze data with Python
ages = [item["json"].get("age", 0) for item in items]
average_age = sum(ages) / len(ages) if ages else 0

result = [{
    "json": {
        "analysis": {
            "total_people": len(items),
            "average_age": round(average_age, 2),
            "oldest": max(ages) if ages else 0
        }
    }
}]

print(f"Analyzed {len(items)} people")`}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">JavaScript - Filtering</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto">
{`// Filter items based on condition
return items.filter(item => {
  const age = item.json.age;
  return age >= 18 && age <= 65;
}).map(item => ({
  json: {
    ...item.json,
    category: 'working_age'
  }
}));`}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Python - Individual Processing</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-3 rounded border overflow-x-auto">
{`# Process individual item (each item mode)
result = {
    "json": {
        **item["json"],
        "processed": True,
        "age_category": "adult" if item["json"]["age"] >= 18 else "minor"
    }
}

print(f"Processed: {item['json']['name']}")`}
                </pre>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <div className="space-y-6">
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription>
                The Code connector implements multiple security layers to ensure safe execution of user code.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-green-700">Safe Mode (Enabled by Default)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Safe mode restricts dangerous operations and provides a secure execution environment.
                  </p>
                  <ul className="text-sm space-y-1">
                    <li>• Blocks file system access</li>
                    <li>• Prevents network requests</li>
                    <li>• Restricts system calls</li>
                    <li>• Validates code syntax</li>
                    <li>• Enforces memory limits</li>
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-orange-700">Advanced Permissions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Advanced users can enable additional permissions when needed.
                  </p>
                  <ul className="text-sm space-y-1">
                    <li>• Network access (HTTP requests)</li>
                    <li>• File system operations</li>
                    <li>• Extended memory limits</li>
                    <li>• Longer execution timeouts</li>
                  </ul>
                  <Alert className="mt-3">
                    <AlertTriangle className="h-3 w-3" />
                    <AlertDescription className="text-xs">
                      Only enable these with trusted code
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Security Best Practices</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium text-sm text-green-700 mb-2">✅ Recommended</h4>
                    <ul className="text-sm space-y-1">
                      <li>• Keep safe mode enabled</li>
                      <li>• Use reasonable timeouts</li>
                      <li>• Validate input data</li>
                      <li>• Test code thoroughly</li>
                      <li>• Monitor execution logs</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-medium text-sm text-red-700 mb-2">❌ Avoid</h4>
                    <ul className="text-sm space-y-1">
                      <li>• Executing untrusted code</li>
                      <li>• Disabling all restrictions</li>
                      <li>• Infinite loops or recursion</li>
                      <li>• Hardcoded credentials</li>
                      <li>• Excessive memory usage</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Configuration Modal */}
      <CodeConnectorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveConfig}
        initialConfig={connectorConfig}
      />
    </div>
  );
}