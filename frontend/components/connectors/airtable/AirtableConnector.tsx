'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Database, 
  Table, 
  FileText, 
  Settings, 
  Play, 
  CheckCircle, 
  XCircle, 
  Loader2,
  Info,
  Plus,
  Search,
  Edit,
  Trash2
} from 'lucide-react';
import { AirtableConnectorModal } from './AirtableConnectorModal';

interface AirtableConnectorProps {
  onExecute?: (config: any) => Promise<any>;
  initialConfig?: any;
}

export function AirtableConnector({ onExecute, initialConfig }: AirtableConnectorProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [config, setConfig] = useState(initialConfig || null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  const handleSaveConfig = async (newConfig: any) => {
    setConfig(newConfig);
    setIsModalOpen(false);
  };

  const handleExecute = async () => {
    if (!config || !onExecute) return;

    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);

    try {
      const result = await onExecute(config);
      setExecutionResult(result);
    } catch (error) {
      setExecutionError(error instanceof Error ? error.message : 'Execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const getResourceIcon = (resource: string) => {
    switch (resource) {
      case 'record': return <FileText className="h-4 w-4" />;
      case 'base': return <Database className="h-4 w-4" />;
      case 'table': return <Table className="h-4 w-4" />;
      default: return <Database className="h-4 w-4" />;
    }
  };

  const getOperationIcon = (operation: string) => {
    switch (operation) {
      case 'create': return <Plus className="h-4 w-4" />;
      case 'search': return <Search className="h-4 w-4" />;
      case 'update': return <Edit className="h-4 w-4" />;
      case 'delete': return <Trash2 className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const getOperationColor = (operation: string) => {
    switch (operation) {
      case 'create': return 'bg-green-100 text-green-800';
      case 'get': return 'bg-blue-100 text-blue-800';
      case 'update': return 'bg-yellow-100 text-yellow-800';
      case 'delete': return 'bg-red-100 text-red-800';
      case 'search': return 'bg-purple-100 text-purple-800';
      case 'upsert': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatConfigValue = (key: string, value: any) => {
    if (value === null || value === undefined) return 'Not set';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    if (typeof value === 'string' && value.length > 50) {
      return value.substring(0, 50) + '...';
    }
    return String(value);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              🗃️
            </div>
            Airtable Connector
          </CardTitle>
          <CardDescription>
            Manage Airtable bases, tables, and records with comprehensive database operations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button onClick={() => setIsModalOpen(true)} className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              {config ? 'Edit Configuration' : 'Configure'}
            </Button>
            {config && (
              <Button 
                onClick={handleExecute} 
                disabled={isExecuting}
                variant="default"
                className="flex items-center gap-2"
              >
                {isExecuting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Execute
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Configuration Display */}
      {config && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              Current Configuration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Resource and Operation */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {getResourceIcon(config.settings?.resource)}
                  <span className="font-medium">Resource:</span>
                  <Badge variant="outline">{config.settings?.resource}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  {getOperationIcon(config.settings?.operation)}
                  <span className="font-medium">Operation:</span>
                  <Badge className={getOperationColor(config.settings?.operation)}>
                    {config.settings?.operation}
                  </Badge>
                </div>
              </div>

              {/* Base Information */}
              <div className="space-y-2">
                <div>
                  <span className="font-medium">Base ID:</span>
                  <p className="text-sm text-muted-foreground font-mono">
                    {config.settings?.base_id || 'Not set'}
                  </p>
                </div>
                {config.settings?.table_id && (
                  <div>
                    <span className="font-medium">Table:</span>
                    <p className="text-sm text-muted-foreground">
                      {config.settings.table_id}
                    </p>
                  </div>
                )}
              </div>

              {/* Additional Parameters */}
              <div className="space-y-2">
                {config.settings?.record_id && (
                  <div>
                    <span className="font-medium">Record ID:</span>
                    <p className="text-sm text-muted-foreground font-mono">
                      {config.settings.record_id}
                    </p>
                  </div>
                )}
                {config.settings?.max_records && (
                  <div>
                    <span className="font-medium">Max Records:</span>
                    <p className="text-sm text-muted-foreground">
                      {config.settings.max_records}
                    </p>
                  </div>
                )}
                {config.settings?.filter_formula && (
                  <div>
                    <span className="font-medium">Filter:</span>
                    <p className="text-sm text-muted-foreground">
                      {config.settings.filter_formula.length > 30 
                        ? config.settings.filter_formula.substring(0, 30) + '...'
                        : config.settings.filter_formula
                      }
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Fields Display */}
            {config.settings?.fields && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <span className="font-medium">Fields:</span>
                <pre className="text-sm text-muted-foreground mt-1 overflow-x-auto">
                  {JSON.stringify(config.settings.fields, null, 2)}
                </pre>
              </div>
            )}

            {/* Advanced Options */}
            {(config.settings?.typecast || config.settings?.return_fields_by_field_id || config.settings?.cell_format !== 'json') && (
              <div className="mt-4">
                <span className="font-medium">Advanced Options:</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {config.settings.typecast && (
                    <Badge variant="secondary">Typecast Enabled</Badge>
                  )}
                  {config.settings.return_fields_by_field_id && (
                    <Badge variant="secondary">Return Field IDs</Badge>
                  )}
                  {config.settings.cell_format === 'string' && (
                    <Badge variant="secondary">String Format</Badge>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Execution Results */}
      {executionResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Execution Result
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Summary */}
              {executionResult.result && (
                <Alert className="border-green-200 bg-green-50">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800">
                    {executionResult.result}
                  </AlertDescription>
                </Alert>
              )}

              {/* Records Display */}
              {executionResult.records && Array.isArray(executionResult.records) && (
                <div>
                  <h4 className="font-medium mb-2">Records ({executionResult.records.length}):</h4>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {executionResult.records.slice(0, 10).map((record: any, index: number) => (
                      <div key={record.id || index} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="h-4 w-4" />
                          <span className="font-mono text-sm">{record.id}</span>
                          {record.createdTime && (
                            <Badge variant="outline" className="text-xs">
                              {new Date(record.createdTime).toLocaleDateString()}
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm">
                          {Object.entries(record.fields || {}).slice(0, 3).map(([key, value]) => (
                            <div key={key} className="flex gap-2">
                              <span className="font-medium">{key}:</span>
                              <span className="text-muted-foreground">
                                {formatConfigValue(key, value)}
                              </span>
                            </div>
                          ))}
                          {Object.keys(record.fields || {}).length > 3 && (
                            <div className="text-xs text-muted-foreground mt-1">
                              ... and {Object.keys(record.fields).length - 3} more fields
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {executionResult.records.length > 10 && (
                      <div className="text-center text-sm text-muted-foreground">
                        ... and {executionResult.records.length - 10} more records
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Single Record Display */}
              {executionResult.record_id && !executionResult.records && (
                <div>
                  <h4 className="font-medium mb-2">Record Details:</h4>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="h-4 w-4" />
                      <span className="font-mono text-sm">{executionResult.record_id}</span>
                    </div>
                    {executionResult.fields && (
                      <div className="text-sm space-y-1">
                        {Object.entries(executionResult.fields).map(([key, value]) => (
                          <div key={key} className="flex gap-2">
                            <span className="font-medium">{key}:</span>
                            <span className="text-muted-foreground">
                              {formatConfigValue(key, value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tables Display */}
              {executionResult.tables && Array.isArray(executionResult.tables) && (
                <div>
                  <h4 className="font-medium mb-2">Tables ({executionResult.tables.length}):</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {executionResult.tables.map((table: any, index: number) => (
                      <div key={table.id || index} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Table className="h-4 w-4" />
                          <span className="font-medium">{table.name}</span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {table.description && (
                            <p className="mb-1">{table.description}</p>
                          )}
                          <div className="flex gap-4">
                            {table.field_count && (
                              <span>{table.field_count} fields</span>
                            )}
                            {table.view_count && (
                              <span>{table.view_count} views</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw Data */}
              <details className="mt-4">
                <summary className="cursor-pointer font-medium">Raw Response Data</summary>
                <pre className="mt-2 p-3 bg-gray-100 rounded-lg text-sm overflow-x-auto">
                  {JSON.stringify(executionResult, null, 2)}
                </pre>
              </details>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Execution Error */}
      {executionError && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              Execution Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Alert className="border-red-200 bg-red-50">
              <XCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">
                {executionError}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* Configuration Modal */}
      <AirtableConnectorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveConfig}
        initialConfig={config?.settings}
      />
    </div>
  );
}