'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Database, Table, FileText, Settings, Key, TestTube, CheckCircle, XCircle, Info } from 'lucide-react';

interface AirtableConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialData?: any; // AI-generated parameters
  onSave: (config: any) => Promise<void>;
  initialConfig?: any;
}

interface AirtableConfig {
  resource: 'record' | 'base' | 'table';
  operation: string;
  base_id?: string;
  base_url?: string;
  table_id?: string;
  table_url?: string;
  record_id?: string;
  fields?: string;
  filter_formula?: string;
  view?: string;
  max_records?: number;
  fields_to_return?: string;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
  merge_fields?: string;
  table_name?: string;
  table_description?: string;
  // Authentication
  api_token?: string;
  // Advanced options
  typecast?: boolean;
  return_fields_by_field_id?: boolean;
  cell_format?: 'json' | 'string';
  time_zone?: string;
  user_locale?: string;
  page_size?: number;
  include_comment_count?: boolean;
  include_created_time?: boolean;
}

const RESOURCE_OPTIONS = [
  { value: 'record', label: 'Record', icon: FileText, description: 'Work with individual records' },
  { value: 'base', label: 'Base', icon: Database, description: 'Access base-level information' },
  { value: 'table', label: 'Table', icon: Table, description: 'Manage table structure' }
];

const OPERATION_OPTIONS = {
  record: [
    { value: 'create', label: 'Create Record', description: 'Create a new record' },
    { value: 'get', label: 'Get Record', description: 'Retrieve a specific record' },
    { value: 'update', label: 'Update Record', description: 'Update an existing record' },
    { value: 'delete', label: 'Delete Record', description: 'Delete a record' },
    { value: 'search', label: 'Search Records', description: 'Search and list records' },
    { value: 'upsert', label: 'Create or Update', description: 'Create or update based on merge fields' }
  ],
  base: [
    { value: 'get_schema', label: 'Get Base Schema', description: 'Get complete base schema' },
    { value: 'list_tables', label: 'List Tables', description: 'List all tables in base' }
  ],
  table: [
    { value: 'create_table', label: 'Create Table', description: 'Create a new table' },
    { value: 'update_table', label: 'Update Table', description: 'Update table properties' },
    { value: 'get_table_schema', label: 'Get Table Schema', description: 'Get table schema' }
  ]
};

export function AirtableConnectorModal({ isOpen, onClose, onSave, initialConfig, initialData }: AirtableConnectorModalProps) {
  const [config, setConfig] = useState<AirtableConfig>({
    resource: 'record',
    operation: 'get',
    max_records: 100,
    sort_direction: 'asc',
    cell_format: 'json',
    time_zone: 'UTC',
    user_locale: 'en',
    page_size: 100,
    typecast: false,
    return_fields_by_field_id: false,
    include_comment_count: false,
    include_created_time: false
  });

  const [isLoading, setIsLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialConfig) {
      setConfig({ ...config, ...initialConfig });
    }
  }, [initialConfig]);

  // Populate form with AI-generated parameters
  useEffect(() => {
    if (initialData && Object.keys(initialData).length > 0) {
      console.log('🤖 Airtable Modal: Received AI-generated parameters:', initialData);
      
      // Update config with AI-generated data
      setConfig(prev => ({
        ...prev,
        ...initialData
      }));
    }
  }, [initialData]);

  const validateConfig = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Resource and operation validation
    if (!config.resource) {
      newErrors.resource = 'Resource is required';
    }
    if (!config.operation) {
      newErrors.operation = 'Operation is required';
    }

    // Base ID validation
    if (!config.base_id && !config.base_url) {
      newErrors.base_id = 'Base ID or Base URL is required';
    }
    if (config.base_id && !/^app[a-zA-Z0-9]+$/.test(config.base_id)) {
      newErrors.base_id = 'Base ID must start with "app" followed by alphanumeric characters';
    }

    // Table ID validation for record and table operations
    if ((config.resource === 'record' || config.resource === 'table') && !config.table_id && !config.table_url) {
      newErrors.table_id = 'Table ID or Table URL is required';
    }

    // Record ID validation for specific operations
    if (['get', 'update', 'delete'].includes(config.operation) && !config.record_id) {
      newErrors.record_id = 'Record ID is required for this operation';
    }
    if (config.record_id && !/^rec[a-zA-Z0-9]+$/.test(config.record_id)) {
      newErrors.record_id = 'Record ID must start with "rec" followed by alphanumeric characters';
    }

    // Fields validation for create/update operations
    if (['create', 'update'].includes(config.operation) && !config.fields) {
      newErrors.fields = 'Fields are required for this operation';
    }

    // Upsert validation
    if (config.operation === 'upsert' && !config.merge_fields) {
      newErrors.merge_fields = 'Merge fields are required for upsert operation';
    }

    // Table creation validation
    if (config.operation === 'create_table' && !config.table_name) {
      newErrors.table_name = 'Table name is required for table creation';
    }

    // Authentication validation
    if (!config.api_token) {
      newErrors.api_token = 'API token is required';
    }

    // JSON validation for fields
    if (config.fields) {
      try {
        JSON.parse(config.fields);
      } catch (e) {
        newErrors.fields = 'Fields must be valid JSON';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateConfig()) {
      return;
    }

    setIsLoading(true);
    try {
      const configToSave = {
        ...config,
        // Parse JSON fields
        fields: config.fields ? JSON.parse(config.fields) : undefined,
        // Convert comma-separated strings to arrays
        fields_to_return: config.fields_to_return ? config.fields_to_return.split(',').map(f => f.trim()) : undefined,
        merge_fields: config.merge_fields ? config.merge_fields.split(',').map(f => f.trim()) : undefined,
        // Add sort configuration
        sort: config.sort_field ? [{
          field: config.sort_field,
          direction: config.sort_direction
        }] : undefined
      };

      await onSave({
        connector_name: 'airtable',
        settings: configToSave
      });
      onClose();
    } catch (error) {
      console.error('Failed to save Airtable configuration:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!config.api_token) {
      setTestResult({ success: false, message: 'API token is required for testing' });
      return;
    }

    setIsLoading(true);
    setTestResult(null);

    try {
      // Test connection by making a simple API call
      const response = await fetch('https://api.airtable.com/v0/meta/bases', {
        headers: {
          'Authorization': `Bearer ${config.api_token}`
        }
      });

      if (response.ok) {
        setTestResult({ success: true, message: 'Connection successful! API token is valid.' });
      } else {
        setTestResult({ success: false, message: 'Connection failed. Please check your API token.' });
      }
    } catch (error) {
      setTestResult({ success: false, message: 'Connection test failed. Please check your network connection.' });
    } finally {
      setIsLoading(false);
    }
  };

  const getOperationOptions = () => {
    return OPERATION_OPTIONS[config.resource] || [];
  };

  const isFieldRequired = (field: string): boolean => {
    switch (field) {
      case 'record_id':
        return ['get', 'update', 'delete'].includes(config.operation);
      case 'fields':
        return ['create', 'update'].includes(config.operation);
      case 'merge_fields':
        return config.operation === 'upsert';
      case 'table_name':
        return config.operation === 'create_table';
      case 'table_id':
        return config.resource === 'record' || config.resource === 'table';
      default:
        return false;
    }
  };

  const renderResourceIcon = (resource: string) => {
    const resourceOption = RESOURCE_OPTIONS.find(r => r.value === resource);
    if (!resourceOption) return null;
    const Icon = resourceOption.icon;
    return <Icon className="h-4 w-4" />;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              🗃️
            </div>
            Configure Airtable Connector
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="configuration" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="configuration">Configuration</TabsTrigger>
            <TabsTrigger value="authentication">Authentication</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="configuration" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Basic Configuration
                </CardTitle>
                <CardDescription>
                  Configure the basic Airtable operation settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Resource Selection */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="resource">Resource Type *</Label>
                    <Select
                      value={config.resource}
                      onValueChange={(value: 'record' | 'base' | 'table') => {
                        setConfig({ ...config, resource: value, operation: OPERATION_OPTIONS[value]?.[0]?.value || '' });
                        setErrors({ ...errors, resource: '' });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select resource type" />
                      </SelectTrigger>
                      <SelectContent>
                        {RESOURCE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            <div className="flex items-center gap-2">
                              <option.icon className="h-4 w-4" />
                              <div>
                                <div className="font-medium">{option.label}</div>
                                <div className="text-xs text-muted-foreground">{option.description}</div>
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.resource && <p className="text-sm text-red-500">{errors.resource}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="operation">Operation *</Label>
                    <Select
                      value={config.operation}
                      onValueChange={(value) => {
                        setConfig({ ...config, operation: value });
                        setErrors({ ...errors, operation: '' });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select operation" />
                      </SelectTrigger>
                      <SelectContent>
                        {getOperationOptions().map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            <div>
                              <div className="font-medium">{option.label}</div>
                              <div className="text-xs text-muted-foreground">{option.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.operation && <p className="text-sm text-red-500">{errors.operation}</p>}
                  </div>
                </div>

                {/* Base Configuration */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="base_id">Base ID *</Label>
                    <Input
                      id="base_id"
                      value={config.base_id || ''}
                      onChange={(e) => {
                        setConfig({ ...config, base_id: e.target.value });
                        setErrors({ ...errors, base_id: '' });
                      }}
                      placeholder="appXXXXXXXXXXXXXX"
                    />
                    {errors.base_id && <p className="text-sm text-red-500">{errors.base_id}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="base_url">Base URL (Alternative)</Label>
                    <Input
                      id="base_url"
                      value={config.base_url || ''}
                      onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
                      placeholder="https://airtable.com/appXXXXXXXXXXXXXX/..."
                    />
                  </div>
                </div>

                {/* Table Configuration */}
                {(config.resource === 'record' || config.resource === 'table') && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="table_id">
                        Table ID or Name {isFieldRequired('table_id') && '*'}
                      </Label>
                      <Input
                        id="table_id"
                        value={config.table_id || ''}
                        onChange={(e) => {
                          setConfig({ ...config, table_id: e.target.value });
                          setErrors({ ...errors, table_id: '' });
                        }}
                        placeholder="tblXXXXXXXXXXXXXX or Table Name"
                      />
                      {errors.table_id && <p className="text-sm text-red-500">{errors.table_id}</p>}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="table_url">Table URL (Alternative)</Label>
                      <Input
                        id="table_url"
                        value={config.table_url || ''}
                        onChange={(e) => setConfig({ ...config, table_url: e.target.value })}
                        placeholder="https://airtable.com/appXXX/tblXXXXXXXXXXXXXX/..."
                      />
                    </div>
                  </div>
                )}

                {/* Record ID */}
                {isFieldRequired('record_id') && (
                  <div className="space-y-2">
                    <Label htmlFor="record_id">Record ID *</Label>
                    <Input
                      id="record_id"
                      value={config.record_id || ''}
                      onChange={(e) => {
                        setConfig({ ...config, record_id: e.target.value });
                        setErrors({ ...errors, record_id: '' });
                      }}
                      placeholder="recXXXXXXXXXXXXXX"
                    />
                    {errors.record_id && <p className="text-sm text-red-500">{errors.record_id}</p>}
                  </div>
                )}

                {/* Fields for create/update operations */}
                {isFieldRequired('fields') && (
                  <div className="space-y-2">
                    <Label htmlFor="fields">Record Fields (JSON) *</Label>
                    <Textarea
                      id="fields"
                      value={config.fields || ''}
                      onChange={(e) => {
                        setConfig({ ...config, fields: e.target.value });
                        setErrors({ ...errors, fields: '' });
                      }}
                      placeholder='{"Name": "John Doe", "Email": "john@example.com", "Age": 30}'
                      rows={4}
                    />
                    {errors.fields && <p className="text-sm text-red-500">{errors.fields}</p>}
                  </div>
                )}

                {/* Merge fields for upsert */}
                {isFieldRequired('merge_fields') && (
                  <div className="space-y-2">
                    <Label htmlFor="merge_fields">Merge Fields (Comma-separated) *</Label>
                    <Input
                      id="merge_fields"
                      value={config.merge_fields || ''}
                      onChange={(e) => {
                        setConfig({ ...config, merge_fields: e.target.value });
                        setErrors({ ...errors, merge_fields: '' });
                      }}
                      placeholder="Email, Phone"
                    />
                    {errors.merge_fields && <p className="text-sm text-red-500">{errors.merge_fields}</p>}
                  </div>
                )}

                {/* Table creation fields */}
                {isFieldRequired('table_name') && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="table_name">Table Name *</Label>
                      <Input
                        id="table_name"
                        value={config.table_name || ''}
                        onChange={(e) => {
                          setConfig({ ...config, table_name: e.target.value });
                          setErrors({ ...errors, table_name: '' });
                        }}
                        placeholder="My New Table"
                      />
                      {errors.table_name && <p className="text-sm text-red-500">{errors.table_name}</p>}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="table_description">Table Description</Label>
                      <Textarea
                        id="table_description"
                        value={config.table_description || ''}
                        onChange={(e) => setConfig({ ...config, table_description: e.target.value })}
                        placeholder="This table contains..."
                        rows={3}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Query and Filtering Options */}
            {config.operation === 'search' && (
              <Card>
                <CardHeader>
                  <CardTitle>Search & Filter Options</CardTitle>
                  <CardDescription>
                    Configure search parameters and filtering
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="filter_formula">Filter Formula</Label>
                    <Input
                      id="filter_formula"
                      value={config.filter_formula || ''}
                      onChange={(e) => setConfig({ ...config, filter_formula: e.target.value })}
                      placeholder="AND({Status} = 'Active', {Age} > 18)"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="view">View Name/ID</Label>
                    <Input
                      id="view"
                      value={config.view || ''}
                      onChange={(e) => setConfig({ ...config, view: e.target.value })}
                      placeholder="Grid view or viwXXXXXXXXXXXXXX"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="max_records">Max Records</Label>
                      <Input
                        id="max_records"
                        type="number"
                        value={config.max_records || 100}
                        onChange={(e) => setConfig({ ...config, max_records: parseInt(e.target.value) || 100 })}
                        min={1}
                        max={1000}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="fields_to_return">Fields to Return</Label>
                      <Input
                        id="fields_to_return"
                        value={config.fields_to_return || ''}
                        onChange={(e) => setConfig({ ...config, fields_to_return: e.target.value })}
                        placeholder="Name, Email, Status"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="sort_field">Sort Field</Label>
                      <Input
                        id="sort_field"
                        value={config.sort_field || ''}
                        onChange={(e) => setConfig({ ...config, sort_field: e.target.value })}
                        placeholder="Created Time"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="sort_direction">Sort Direction</Label>
                      <Select
                        value={config.sort_direction}
                        onValueChange={(value: 'asc' | 'desc') => setConfig({ ...config, sort_direction: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="asc">Ascending</SelectItem>
                          <SelectItem value="desc">Descending</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="authentication" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  Airtable Authentication
                </CardTitle>
                <CardDescription>
                  Configure your Airtable Personal Access Token
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="api_token">Personal Access Token *</Label>
                  <Input
                    id="api_token"
                    type="password"
                    value={config.api_token || ''}
                    onChange={(e) => {
                      setConfig({ ...config, api_token: e.target.value });
                      setErrors({ ...errors, api_token: '' });
                    }}
                    placeholder="patXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                  />
                  {errors.api_token && <p className="text-sm text-red-500">{errors.api_token}</p>}
                </div>

                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Create a Personal Access Token at{' '}
                    <a
                      href="https://airtable.com/create/tokens"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      https://airtable.com/create/tokens
                    </a>
                    . Make sure to grant appropriate scopes for your bases and tables.
                  </AlertDescription>
                </Alert>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestConnection}
                    disabled={isLoading || !config.api_token}
                    className="flex items-center gap-2"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <TestTube className="h-4 w-4" />
                    )}
                    Test Connection
                  </Button>
                </div>

                {testResult && (
                  <Alert className={testResult.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
                    {testResult.success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <AlertDescription className={testResult.success ? 'text-green-800' : 'text-red-800'}>
                      {testResult.message}
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Advanced Options</CardTitle>
                <CardDescription>
                  Configure advanced Airtable API options
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="cell_format">Cell Format</Label>
                    <Select
                      value={config.cell_format}
                      onValueChange={(value: 'json' | 'string') => setConfig({ ...config, cell_format: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="json">JSON</SelectItem>
                        <SelectItem value="string">String</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="page_size">Page Size</Label>
                    <Input
                      id="page_size"
                      type="number"
                      value={config.page_size || 100}
                      onChange={(e) => setConfig({ ...config, page_size: parseInt(e.target.value) || 100 })}
                      min={1}
                      max={100}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="time_zone">Time Zone</Label>
                    <Input
                      id="time_zone"
                      value={config.time_zone || 'UTC'}
                      onChange={(e) => setConfig({ ...config, time_zone: e.target.value })}
                      placeholder="America/New_York"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="user_locale">User Locale</Label>
                    <Input
                      id="user_locale"
                      value={config.user_locale || 'en'}
                      onChange={(e) => setConfig({ ...config, user_locale: e.target.value })}
                      placeholder="en-US"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="typecast"
                      checked={config.typecast || false}
                      onChange={(e) => setConfig({ ...config, typecast: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <Label htmlFor="typecast">Typecast Values</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="return_fields_by_field_id"
                      checked={config.return_fields_by_field_id || false}
                      onChange={(e) => setConfig({ ...config, return_fields_by_field_id: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <Label htmlFor="return_fields_by_field_id">Return Field IDs</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="include_comment_count"
                      checked={config.include_comment_count || false}
                      onChange={(e) => setConfig({ ...config, include_comment_count: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <Label htmlFor="include_comment_count">Include Comment Count</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="include_created_time"
                      checked={config.include_created_time || false}
                      onChange={(e) => setConfig({ ...config, include_created_time: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <Label htmlFor="include_created_time">Include Created Time</Label>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              'Save Configuration'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}