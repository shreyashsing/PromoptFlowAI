import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Code2, 
  Play, 
  Save, 
  AlertTriangle, 
  Shield, 
  Network, 
  HardDrive,
  Clock,
  Cpu,
  Info,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface CodeConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: any) => Promise<void>;
  initialConfig?: any;
}

interface CodeConfig {
  language: string;
  mode: string;
  code: string;
  timeout: number;
  safe_mode: boolean;
  allow_network: boolean;
  allow_file_system: boolean;
  max_memory_mb: number;
  return_console_output: boolean;
}

const defaultConfig: CodeConfig = {
  language: 'javascript',
  mode: 'runOnceForAllItems',
  code: '',
  timeout: 30,
  safe_mode: true,
  allow_network: false,
  allow_file_system: false,
  max_memory_mb: 128,
  return_console_output: true
};

const codeExamples = {
  javascript: {
    allItems: `// Transform all items by adding processed flag
return items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString()
  }
}));`,
    eachItem: `// Process individual item
return {
  json: {
    ...item.json,
    processed: true,
    double_value: item.json.value * 2
  }
};`,
    filtering: `// Filter items based on condition
return items.filter(item => 
  item.json.status === 'active'
);`,
    aggregation: `// Calculate aggregated data
const total = items.reduce((sum, item) => 
  sum + (item.json.amount || 0), 0
);

return [{
  json: {
    total_amount: total,
    item_count: items.length,
    average: total / items.length
  }
}];`
  },
  python: {
    allItems: `# Transform all items using Python
result = []
for item in items:
    new_item = {
        "json": {
            **item["json"],
            "processed": True,
            "name_length": len(item["json"].get("name", ""))
        }
    }
    result.append(new_item)

print(f"Processed {len(result)} items")`,
    eachItem: `# Process individual item
result = {
    "json": {
        **item["json"],
        "processed": True,
        "age_category": "adult" if item["json"]["age"] >= 18 else "minor"
    }
}

print(f"Processed: {item['json']['name']}")`,
    dataAnalysis: `# Data analysis with Python
import json
from datetime import datetime

# Calculate statistics
values = [item["json"].get("value", 0) for item in items]
total = sum(values)
average = total / len(values) if values else 0

result = [{
    "json": {
        "analysis": {
            "total": total,
            "average": average,
            "count": len(items),
            "max": max(values) if values else 0,
            "min": min(values) if values else 0
        },
        "timestamp": datetime.now().isoformat()
    }
}]

print(f"Analyzed {len(items)} items")`
  }
};

export function CodeConnectorModal({ 
  isOpen, 
  onClose, 
  onSave, 
  initialConfig 
}: CodeConnectorModalProps) {
  const [config, setConfig] = useState<CodeConfig>(defaultConfig);
  const [testResult, setTestResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (initialConfig) {
      setConfig({ ...defaultConfig, ...initialConfig });
    } else {
      setConfig(defaultConfig);
    }
  }, [initialConfig, isOpen]);

  const validateConfig = (): string[] => {
    const errors: string[] = [];
    
    if (!config.code.trim()) {
      errors.push('Code is required');
    }
    
    if (config.timeout < 1 || config.timeout > 300) {
      errors.push('Timeout must be between 1 and 300 seconds');
    }
    
    if (config.max_memory_mb < 16 || config.max_memory_mb > 1024) {
      errors.push('Memory limit must be between 16 and 1024 MB');
    }
    
    if (!config.safe_mode && (config.allow_network || config.allow_file_system)) {
      // This is allowed but we should warn
    }
    
    return errors;
  };

  const handleSave = async () => {
    const errors = validateConfig();
    setValidationErrors(errors);
    
    if (errors.length > 0) {
      return;
    }
    
    setIsLoading(true);
    try {
      await onSave(config);
      onClose();
    } catch (error) {
      console.error('Failed to save configuration:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTest = async () => {
    const errors = validateConfig();
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }
    
    setIsLoading(true);
    setTestResult(null);
    
    try {
      // Mock test execution - in real implementation, this would call the backend
      const mockResult = {
        success: true,
        data: {
          items: [
            { json: { test: true, processed: true } }
          ],
          console_output: 'Test execution completed successfully',
          execution_time: 0.123
        },
        metadata: {
          language: config.language,
          mode: config.mode,
          items_processed: 1
        }
      };
      
      setTestResult(mockResult);
    } catch (error) {
      setTestResult({
        success: false,
        error: 'Test execution failed: ' + (error as Error).message
      });
    } finally {
      setIsLoading(false);
    }
  };

  const insertExample = (exampleKey: string) => {
    const examples = codeExamples[config.language as keyof typeof codeExamples];
    if (examples && examples[exampleKey as keyof typeof examples]) {
      setConfig(prev => ({
        ...prev,
        code: examples[exampleKey as keyof typeof examples]
      }));
    }
  };

  const getPlaceholder = () => {
    if (config.language === 'javascript') {
      return config.mode === 'runOnceForAllItems' 
        ? '// Access all items\nreturn items.map(item => ({\n  json: {\n    ...item.json,\n    processed: true\n  }\n}));'
        : '// Access current item\nreturn {\n  json: {\n    ...item.json,\n    processed: true\n  }\n};';
    } else {
      return config.mode === 'runOnceForAllItems'
        ? '# Access all items\nresult = []\nfor item in items:\n    # Process item\n    result.append(item)\n\nprint(f"Processed {len(result)} items")'
        : '# Access current item\nresult = {\n    "json": {\n        **item["json"],\n        "processed": True\n    }\n}\n\nprint("Item processed")';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Code2 className="h-5 w-5 text-purple-600" />
            <span>Code Connector Configuration</span>
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="editor" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="editor">Code Editor</TabsTrigger>
            <TabsTrigger value="examples">Examples</TabsTrigger>
            <TabsTrigger value="test">Test & Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="editor" className="space-y-6">
            {/* Basic Configuration */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="language">Programming Language</Label>
                <Select
                  value={config.language}
                  onValueChange={(value) => setConfig(prev => ({ ...prev, language: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="javascript">JavaScript</SelectItem>
                    <SelectItem value="python">Python</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="mode">Execution Mode</Label>
                <Select
                  value={config.mode}
                  onValueChange={(value) => setConfig(prev => ({ ...prev, mode: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="runOnceForAllItems">Run Once for All Items</SelectItem>
                    <SelectItem value="runOnceForEachItem">Run Once for Each Item</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Code Editor */}
            <div className="space-y-2">
              <Label htmlFor="code">Code</Label>
              <Textarea
                id="code"
                value={config.code}
                onChange={(e) => setConfig(prev => ({ ...prev, code: e.target.value }))}
                placeholder={getPlaceholder()}
                className="min-h-[300px] font-mono text-sm"
              />
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <Info className="h-3 w-3" />
                <span>
                  Use "{config.mode === 'runOnceForAllItems' ? 'items' : 'item'}" to access input data. 
                  Use console.log() (JS) or print() (Python) for debugging.
                </span>
              </div>
            </div>

            {/* Basic Settings */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout (seconds)</Label>
                <Input
                  id="timeout"
                  type="number"
                  min="1"
                  max="300"
                  value={config.timeout}
                  onChange={(e) => setConfig(prev => ({ ...prev, timeout: parseInt(e.target.value) || 30 }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="memory">Max Memory (MB)</Label>
                <Input
                  id="memory"
                  type="number"
                  min="16"
                  max="1024"
                  value={config.max_memory_mb}
                  onChange={(e) => setConfig(prev => ({ ...prev, max_memory_mb: parseInt(e.target.value) || 128 }))}
                />
              </div>
            </div>

            {/* Security Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center space-x-2">
                  <Shield className="h-4 w-4" />
                  <span>Security Settings</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Safe Mode</Label>
                    <p className="text-xs text-gray-500">Restrict dangerous operations</p>
                  </div>
                  <Switch
                    checked={config.safe_mode}
                    onCheckedChange={(checked) => setConfig(prev => ({ ...prev, safe_mode: checked }))}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium flex items-center space-x-1">
                      <Network className="h-3 w-3" />
                      <span>Allow Network Access</span>
                    </Label>
                    <p className="text-xs text-gray-500">Enable HTTP requests and network operations</p>
                  </div>
                  <Switch
                    checked={config.allow_network}
                    onCheckedChange={(checked) => setConfig(prev => ({ 
                      ...prev, 
                      allow_network: checked,
                      safe_mode: checked ? false : prev.safe_mode
                    }))}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium flex items-center space-x-1">
                      <HardDrive className="h-3 w-3" />
                      <span>Allow File System Access</span>
                    </Label>
                    <p className="text-xs text-gray-500">Enable file read/write operations</p>
                  </div>
                  <Switch
                    checked={config.allow_file_system}
                    onCheckedChange={(checked) => setConfig(prev => ({ 
                      ...prev, 
                      allow_file_system: checked,
                      safe_mode: checked ? false : prev.safe_mode
                    }))}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">Return Console Output</Label>
                    <p className="text-xs text-gray-500">Include console.log/print output in results</p>
                  </div>
                  <Switch
                    checked={config.return_console_output}
                    onCheckedChange={(checked) => setConfig(prev => ({ ...prev, return_console_output: checked }))}
                  />
                </div>

                {(!config.safe_mode && (config.allow_network || config.allow_file_system)) && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      Warning: Disabling safe mode and allowing network/file system access can be dangerous. 
                      Only use with trusted code.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <ul className="list-disc list-inside space-y-1">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="examples" className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <h3 className="text-lg font-semibold">Code Examples</h3>
              
              {config.language === 'javascript' ? (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Data Transformation</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.javascript.allItems}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('allItems')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Item Processing</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.javascript.eachItem}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('eachItem')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Data Filtering</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.javascript.filtering}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('filtering')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Data Aggregation</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.javascript.aggregation}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('aggregation')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Data Processing</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.python.allItems}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('allItems')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Item Processing</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.python.eachItem}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('eachItem')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Data Analysis</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                        <code>{codeExamples.python.dataAnalysis}</code>
                      </pre>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => insertExample('dataAnalysis')}
                      >
                        Use This Example
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="test" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Test Code Execution</h3>
              <Button 
                onClick={handleTest} 
                disabled={isLoading || !config.code.trim()}
                className="bg-purple-600 hover:bg-purple-700"
              >
                <Play className="h-4 w-4 mr-2" />
                {isLoading ? 'Testing...' : 'Run Test'}
              </Button>
            </div>

            {testResult && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center space-x-2">
                    {testResult.success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <span>Test Result</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {testResult.success ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Language:</span> {testResult.metadata?.language}
                        </div>
                        <div>
                          <span className="font-medium">Mode:</span> {testResult.metadata?.mode}
                        </div>
                        <div>
                          <span className="font-medium">Execution Time:</span> {testResult.data?.execution_time}s
                        </div>
                      </div>
                      
                      {testResult.data?.console_output && (
                        <div>
                          <Label className="text-sm font-medium">Console Output:</Label>
                          <pre className="text-xs bg-gray-50 p-3 rounded mt-1 overflow-x-auto">
                            {testResult.data.console_output}
                          </pre>
                        </div>
                      )}
                      
                      <div>
                        <Label className="text-sm font-medium">Result Data:</Label>
                        <pre className="text-xs bg-gray-50 p-3 rounded mt-1 overflow-x-auto">
                          {JSON.stringify(testResult.data?.items || testResult.data, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-red-600">
                      <p className="font-medium">Error:</p>
                      <p className="text-sm">{testResult.error}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Test execution runs your code with sample data to verify it works correctly. 
                The actual execution will use real workflow data.
              </AlertDescription>
            </Alert>
          </TabsContent>
        </Tabs>

        {/* Footer Actions */}
        <div className="flex justify-end space-x-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={isLoading}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Save className="h-4 w-4 mr-2" />
            {isLoading ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}