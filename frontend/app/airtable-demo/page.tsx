'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Database, 
  Table, 
  FileText, 
  Play, 
  Code, 
  BookOpen, 
  Zap,
  CheckCircle,
  Info,
  ExternalLink,
  Copy,
  Download
} from 'lucide-react';
import { AirtableConnector } from '@/components/connectors/airtable/AirtableConnector';

export default function AirtableDemoPage() {
  const [activeDemo, setActiveDemo] = useState<string | null>(null);
  const [demoResults, setDemoResults] = useState<Record<string, any>>({});

  const demoConfigurations = {
    listTables: {
      connector_name: 'airtable',
      settings: {
        resource: 'base',
        operation: 'list_tables',
        base_id: 'appXXXXXXXXXXXXXX',
        api_token: 'your_api_token_here'
      }
    },
    searchRecords: {
      connector_name: 'airtable',
      settings: {
        resource: 'record',
        operation: 'search',
        base_id: 'appXXXXXXXXXXXXXX',
        table_id: 'tblXXXXXXXXXXXXXX',
        max_records: 10,
        filter_formula: 'AND({Status} = "Active")',
        sort: [{ field: 'Created Time', direction: 'desc' }],
        api_token: 'your_api_token_here'
      }
    },
    createRecord: {
      connector_name: 'airtable',
      settings: {
        resource: 'record',
        operation: 'create',
        base_id: 'appXXXXXXXXXXXXXX',
        table_id: 'tblXXXXXXXXXXXXXX',
        fields: {
          'Name': 'New Record',
          'Status': 'Active',
          'Priority': 'High',
          'Notes': 'Created via PromptFlow AI'
        },
        typecast: true,
        api_token: 'your_api_token_here'
      }
    },
    getBaseSchema: {
      connector_name: 'airtable',
      settings: {
        resource: 'base',
        operation: 'get_schema',
        base_id: 'appXXXXXXXXXXXXXX',
        include_comment_count: true,
        api_token: 'your_api_token_here'
      }
    }
  };

  const handleDemoExecution = async (demoKey: string, config: any) => {
    setActiveDemo(demoKey);
    
    // Simulate API call (replace with actual API call)
    try {
      // Mock response based on demo type
      let mockResult;
      switch (demoKey) {
        case 'listTables':
          mockResult = {
            success: true,
            data: {
              base_id: config.settings.base_id,
              tables: [
                { id: 'tblABC123', name: 'Projects', field_count: 8, view_count: 3 },
                { id: 'tblDEF456', name: 'Tasks', field_count: 12, view_count: 5 },
                { id: 'tblGHI789', name: 'Team Members', field_count: 6, view_count: 2 }
              ],
              total_tables: 3,
              result: 'Successfully listed 3 tables in base'
            }
          };
          break;
        case 'searchRecords':
          mockResult = {
            success: true,
            data: {
              records: [
                {
                  id: 'recABC123',
                  fields: {
                    'Name': 'Project Alpha',
                    'Status': 'Active',
                    'Priority': 'High',
                    'Created Time': '2024-01-15T10:30:00.000Z'
                  },
                  createdTime: '2024-01-15T10:30:00.000Z'
                },
                {
                  id: 'recDEF456',
                  fields: {
                    'Name': 'Project Beta',
                    'Status': 'Active',
                    'Priority': 'Medium',
                    'Created Time': '2024-01-14T15:45:00.000Z'
                  },
                  createdTime: '2024-01-14T15:45:00.000Z'
                }
              ],
              total_records: 2,
              result: 'Successfully retrieved 2 records'
            }
          };
          break;
        case 'createRecord':
          mockResult = {
            success: true,
            data: {
              record_id: 'recNEW123',
              fields: config.settings.fields,
              created_time: new Date().toISOString(),
              result: 'Successfully created record with ID recNEW123'
            }
          };
          break;
        case 'getBaseSchema':
          mockResult = {
            success: true,
            data: {
              base_id: config.settings.base_id,
              tables: [
                {
                  id: 'tblABC123',
                  name: 'Projects',
                  description: 'Project management table',
                  fields: [
                    { id: 'fldName', name: 'Name', type: 'singleLineText' },
                    { id: 'fldStatus', name: 'Status', type: 'singleSelect' },
                    { id: 'fldPriority', name: 'Priority', type: 'singleSelect' }
                  ],
                  views: [
                    { id: 'viwGrid', name: 'Grid view', type: 'grid' },
                    { id: 'viwKanban', name: 'Kanban', type: 'kanban' }
                  ]
                }
              ],
              total_tables: 1,
              result: 'Successfully retrieved schema for base'
            }
          };
          break;
        default:
          mockResult = { success: false, error: 'Unknown demo type' };
      }

      setDemoResults(prev => ({ ...prev, [demoKey]: mockResult }));
    } catch (error) {
      setDemoResults(prev => ({ 
        ...prev, 
        [demoKey]: { 
          success: false, 
          error: error instanceof Error ? error.message : 'Demo execution failed' 
        } 
      }));
    } finally {
      setActiveDemo(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportConfig = (config: any) => {
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'airtable-config.json';
    link.click();
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <div className="p-3 bg-blue-100 rounded-xl">
            🗃️
          </div>
          <h1 className="text-4xl font-bold">Airtable Connector Demo</h1>
        </div>
        <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
          Explore the comprehensive Airtable connector with live examples, configurations, and documentation.
          Manage bases, tables, and records with powerful database operations.
        </p>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="demos">Live Demos</TabsTrigger>
          <TabsTrigger value="configurations">Configurations</TabsTrigger>
          <TabsTrigger value="documentation">Documentation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Features Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  Record Operations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Create, read, update, delete records
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Search with advanced filtering
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Upsert operations with merge fields
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Batch operations support
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-purple-600" />
                  Base Management
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Get complete base schema
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    List all tables in base
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Field and view information
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Metadata and statistics
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Table className="h-5 w-5 text-orange-600" />
                  Table Operations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Create new tables
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Update table properties
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Get table schema details
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Field type management
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Key Features */}
          <Card>
            <CardHeader>
              <CardTitle>Key Features & Capabilities</CardTitle>
              <CardDescription>
                Comprehensive Airtable integration with advanced features
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h4 className="font-semibold">🔐 Authentication</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Personal Access Token support</li>
                    <li>• Secure token management</li>
                    <li>• Connection testing</li>
                  </ul>
                </div>
                <div className="space-y-3">
                  <h4 className="font-semibold">🔍 Advanced Filtering</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Formula-based filtering</li>
                    <li>• View-based queries</li>
                    <li>• Sorting and pagination</li>
                  </ul>
                </div>
                <div className="space-y-3">
                  <h4 className="font-semibold">⚡ Performance</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Efficient API usage</li>
                    <li>• Batch operations</li>
                    <li>• Rate limit handling</li>
                  </ul>
                </div>
                <div className="space-y-3">
                  <h4 className="font-semibold">🛠️ Flexibility</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Multiple field types</li>
                    <li>• Custom formatting options</li>
                    <li>• Timezone support</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="demos" className="space-y-6">
          {/* Interactive Connector */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Interactive Airtable Connector
              </CardTitle>
              <CardDescription>
                Configure and test the Airtable connector with your own data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AirtableConnector
                onExecute={async (config) => {
                  // This would normally call your API
                  console.log('Executing Airtable connector with config:', config);
                  return {
                    success: true,
                    data: { message: 'Demo execution - replace with actual API call' }
                  };
                }}
              />
            </CardContent>
          </Card>

          {/* Pre-configured Demos */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Object.entries(demoConfigurations).map(([key, config]) => (
              <Card key={key}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {key === 'listTables' && <Database className="h-5 w-5" />}
                    {key === 'searchRecords' && <FileText className="h-5 w-5" />}
                    {key === 'createRecord' && <Play className="h-5 w-5" />}
                    {key === 'getBaseSchema' && <Table className="h-5 w-5" />}
                    {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                  </CardTitle>
                  <CardDescription>
                    {key === 'listTables' && 'List all tables in an Airtable base'}
                    {key === 'searchRecords' && 'Search and filter records with advanced options'}
                    {key === 'createRecord' && 'Create a new record with multiple fields'}
                    {key === 'getBaseSchema' && 'Get complete schema information for a base'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleDemoExecution(key, config)}
                      disabled={activeDemo === key}
                      size="sm"
                    >
                      {activeDemo === key ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                          Running...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Run Demo
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(JSON.stringify(config, null, 2))}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy Config
                    </Button>
                  </div>

                  {demoResults[key] && (
                    <div className="mt-4">
                      {demoResults[key].success ? (
                        <Alert className="border-green-200 bg-green-50">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <AlertDescription className="text-green-800">
                            <strong>Success:</strong> {demoResults[key].data.result}
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <Alert className="border-red-200 bg-red-50">
                          <AlertDescription className="text-red-800">
                            <strong>Error:</strong> {demoResults[key].error}
                          </AlertDescription>
                        </Alert>
                      )}
                      
                      <details className="mt-2">
                        <summary className="cursor-pointer text-sm font-medium">View Response Data</summary>
                        <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-x-auto">
                          {JSON.stringify(demoResults[key], null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="configurations" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {Object.entries(demoConfigurations).map(([key, config]) => (
              <Card key={key}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(JSON.stringify(config, null, 2))}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => exportConfig(config)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto">
                    {JSON.stringify(config, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="documentation" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Getting Started
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">1. Get Your API Token</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    Create a Personal Access Token at Airtable:
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <a href="https://airtable.com/create/tokens" target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Create Token
                    </a>
                  </Button>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">2. Find Your Base ID</h4>
                  <p className="text-sm text-muted-foreground">
                    Your Base ID is in the URL: <code>https://airtable.com/appXXXXXXXXXXXXXX</code>
                  </p>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">3. Configure the Connector</h4>
                  <p className="text-sm text-muted-foreground">
                    Use the interactive connector above or copy one of the example configurations.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  API Reference
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Resources</h4>
                  <div className="space-y-1 text-sm">
                    <Badge variant="outline">record</Badge> - Individual records
                    <br />
                    <Badge variant="outline">base</Badge> - Base-level operations
                    <br />
                    <Badge variant="outline">table</Badge> - Table management
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Record Operations</h4>
                  <div className="space-y-1 text-sm">
                    <Badge variant="secondary">create</Badge> Create new record
                    <br />
                    <Badge variant="secondary">get</Badge> Get specific record
                    <br />
                    <Badge variant="secondary">update</Badge> Update existing record
                    <br />
                    <Badge variant="secondary">delete</Badge> Delete record
                    <br />
                    <Badge variant="secondary">search</Badge> Search/list records
                    <br />
                    <Badge variant="secondary">upsert</Badge> Create or update
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Base Operations</h4>
                  <div className="space-y-1 text-sm">
                    <Badge variant="secondary">get_schema</Badge> Get complete schema
                    <br />
                    <Badge variant="secondary">list_tables</Badge> List all tables
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Advanced Features</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold mb-3">Filtering & Sorting</h4>
                  <div className="space-y-2 text-sm">
                    <div>
                      <strong>Filter Formula:</strong>
                      <code className="block bg-gray-100 p-2 rounded mt-1">
                        AND({`{Status} = "Active"`, {`{Priority} = "High"`})
                      </code>
                    </div>
                    <div>
                      <strong>Sort Configuration:</strong>
                      <code className="block bg-gray-100 p-2 rounded mt-1">
                        [{`{"field": "Created Time", "direction": "desc"}`}]
                      </code>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-3">Field Types</h4>
                  <div className="space-y-1 text-sm">
                    <Badge variant="outline">singleLineText</Badge>
                    <Badge variant="outline">multilineText</Badge>
                    <Badge variant="outline">number</Badge>
                    <Badge variant="outline">singleSelect</Badge>
                    <Badge variant="outline">multipleSelects</Badge>
                    <Badge variant="outline">date</Badge>
                    <Badge variant="outline">checkbox</Badge>
                    <Badge variant="outline">multipleAttachments</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}