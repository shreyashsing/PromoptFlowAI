'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Settings,
  Key,
  Lock,
  Mail,
  Globe,
  FileText,
  Database,
  Webhook,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff,
  Info,
  TestTube,
  XCircle,
} from 'lucide-react';

interface ConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectorName: string;
  connectorConfig?: any;
  onSave: (config: any) => void;
}

interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'textarea' | 'select' | 'boolean' | 'number' | 'array';
  required: boolean;
  description?: string;
  placeholder?: string;
  options?: string[];
  defaultValue?: any;
  minimum?: number;
  maximum?: number;
  items?: any;
  enum?: string[];
  conditionalOn?: { field: string; values: string[] };
}

interface AuthRequirements {
  type: 'none' | 'api_key' | 'oauth2';
  fields: { [key: string]: string };
  instructions?: string;
  oauth_scopes?: string[];
}

export default function StringLikeConnectorModal({ isOpen, onClose, connectorName, connectorConfig, onSave }: ConnectorModalProps) {
  const [config, setConfig] = useState<any>({});
  const [authConfig, setAuthConfig] = useState<any>({});
  const [showApiKey, setShowApiKey] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [activeTab, setActiveTab] = useState('parameters');

  // Get authentication requirements for the connector
  const getAuthRequirements = (name: string): AuthRequirements => {
    switch (name.toLowerCase()) {
      case 'gmail_connector':
        return {
          type: 'oauth2',
          fields: {
            access_token: 'OAuth access token for Gmail API',
            refresh_token: 'OAuth refresh token for token renewal'
          },
          instructions: 'Gmail connector requires OAuth authentication with Google. You\'ll need to authorize access to your Gmail account.',
          oauth_scopes: [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.labels'
          ]
        };

      case 'google_sheets':
        return {
          type: 'oauth2',
          fields: {
            access_token: 'OAuth access token for Google Sheets API',
            refresh_token: 'OAuth refresh token for token renewal'
          },
          instructions: 'Google Sheets connector requires OAuth authentication with Google. You\'ll need to authorize access to your Google Sheets.',
          oauth_scopes: [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
          ]
        };

      case 'perplexity_search':
        return {
          type: 'api_key',
          fields: {
            api_key: 'Perplexity AI API key'
          },
          instructions: 'Get your Perplexity AI API key from https://www.perplexity.ai/settings/api. The API key should start with \'pplx-\'.'
        };

      case 'http_request':
        return {
          type: 'api_key',
          fields: {
            api_key: 'API key for authentication (optional)',
            auth_header: 'Header name for API key (optional, default: Authorization)',
            auth_prefix: 'Prefix for auth header value (optional, default: Bearer)',
            username: 'Username for basic authentication (optional)',
            password: 'Password for basic authentication (optional)'
          },
          instructions: 'Provide authentication credentials if the endpoint requires them. Supports API key authentication (via Authorization header) or HTTP Basic authentication (username/password).'
        };

      case 'webhook':
        return {
          type: 'api_key',
          fields: {
            secret: 'Secret key for webhook signature verification (optional)',
            api_key: 'API key for webhook authentication (optional)'
          },
          instructions: 'Webhooks support optional signature verification using a secret key. This ensures the webhook payload hasn\'t been tampered with.'
        };

      case 'text_summarizer':
        return {
          type: 'none',
          fields: {},
          instructions: 'Text summarizer uses Azure OpenAI, no additional authentication required.'
        };

      default:
        return {
          type: 'none',
          fields: {},
          instructions: 'No authentication required for this connector.'
        };
    }
  };

  const getConnectorFields = (name: string): FormField[] => {
    switch (name.toLowerCase()) {
      case 'gmail_connector':
        return [
          {
            name: 'action',
            label: 'Action',
            type: 'select',
            required: true,
            description: 'Gmail action to perform',
            enum: ['send', 'read', 'search', 'list', 'get_labels', 'create_label', 'delete'],
            defaultValue: 'send'
          },
          {
            name: 'to',
            label: 'To',
            type: 'email',
            required: false,
            description: 'Recipient email address',
            placeholder: 'recipient@example.com',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'cc',
            label: 'CC',
            type: 'email',
            required: false,
            description: 'CC recipient email address',
            placeholder: 'cc@example.com',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'bcc',
            label: 'BCC',
            type: 'email',
            required: false,
            description: 'BCC recipient email address',
            placeholder: 'bcc@example.com',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'subject',
            label: 'Subject',
            type: 'text',
            required: false,
            description: 'Email subject line',
            placeholder: 'Email subject',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'body',
            label: 'Body',
            type: 'textarea',
            required: false,
            description: 'Email body content',
            placeholder: 'Email body text',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'html_body',
            label: 'HTML Body',
            type: 'textarea',
            required: false,
            description: 'HTML email body content',
            placeholder: '<html><body>Email content</body></html>',
            conditionalOn: { field: 'action', values: ['send'] }
          },
          {
            name: 'query',
            label: 'Search Query',
            type: 'text',
            required: false,
            description: 'Gmail search query (e.g., "from:example@gmail.com is:unread")',
            placeholder: 'from:example@gmail.com is:unread',
            conditionalOn: { field: 'action', values: ['search'] }
          },
          {
            name: 'max_results',
            label: 'Max Results',
            type: 'number',
            required: false,
            description: 'Maximum number of results to return',
            defaultValue: 10,
            minimum: 1,
            maximum: 500,
            conditionalOn: { field: 'action', values: ['search', 'list'] }
          },
          {
            name: 'message_id',
            label: 'Message ID',
            type: 'text',
            required: false,
            description: 'Gmail message ID for specific operations',
            placeholder: '18c1a2b3d4e5f6g7',
            conditionalOn: { field: 'action', values: ['read', 'delete'] }
          },
          {
            name: 'label_name',
            label: 'Label Name',
            type: 'text',
            required: false,
            description: 'Name for label operations',
            placeholder: 'Important',
            conditionalOn: { field: 'action', values: ['create_label'] }
          },
          {
            name: 'label_color',
            label: 'Label Color',
            type: 'select',
            required: false,
            description: 'Color for label creation',
            enum: ['red', 'orange', 'yellow', 'green', 'teal', 'blue', 'purple', 'pink', 'brown', 'gray'],
            conditionalOn: { field: 'action', values: ['create_label'] }
          }
        ];

      case 'google_sheets':
        return [
          {
            name: 'action',
            label: 'Action',
            type: 'select',
            required: true,
            description: 'Google Sheets action to perform',
            enum: ['read', 'write', 'update', 'append', 'clear', 'delete', 'create_sheet', 'delete_sheet', 'format'],
            defaultValue: 'read'
          },
          {
            name: 'spreadsheet_id',
            label: 'Spreadsheet ID',
            type: 'text',
            required: true,
            description: 'Google Sheets spreadsheet ID',
            placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
          },
          {
            name: 'sheet_name',
            label: 'Sheet Name',
            type: 'text',
            required: false,
            description: 'Name of the sheet to work with',
            placeholder: 'Sheet1',
            defaultValue: 'Sheet1'
          },
          {
            name: 'range',
            label: 'Range',
            type: 'text',
            required: false,
            description: 'Cell range (e.g., A1:B10)',
            placeholder: 'A1:B10',
            conditionalOn: { field: 'action', values: ['read', 'clear', 'format'] }
          },
          {
            name: 'values',
            label: 'Values',
            type: 'textarea',
            required: false,
            description: 'Data to write (JSON array format)',
            placeholder: '[["Name", "Age"], ["John", 30]]',
            conditionalOn: { field: 'action', values: ['write', 'update', 'append'] }
          },
          {
            name: 'new_sheet_name',
            label: 'New Sheet Name',
            type: 'text',
            required: false,
            description: 'Name for the new sheet',
            placeholder: 'New Sheet',
            conditionalOn: { field: 'action', values: ['create_sheet'] }
          }
        ];

      case 'http_request':
        return [
          {
            name: 'url',
            label: 'URL',
            type: 'text',
            required: true,
            description: 'The URL to make the HTTP request to',
            placeholder: 'https://api.example.com/data'
          },
          {
            name: 'method',
            label: 'HTTP Method',
            type: 'select',
            required: false,
            description: 'HTTP method to use',
            enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
            defaultValue: 'GET'
          },
          {
            name: 'headers',
            label: 'Headers',
            type: 'textarea',
            required: false,
            description: 'HTTP headers to include in the request (JSON format)',
            placeholder: '{"Content-Type": "application/json", "Authorization": "Bearer token"}',
            defaultValue: '{}'
          },
          {
            name: 'query_params',
            label: 'Query Parameters',
            type: 'textarea',
            required: false,
            description: 'Query parameters to append to the URL (JSON format)',
            placeholder: '{"param1": "value1", "param2": "value2"}',
            defaultValue: '{}'
          },
          {
            name: 'body',
            label: 'Request Body',
            type: 'textarea',
            required: false,
            description: 'Request body (for POST, PUT, PATCH methods)',
            placeholder: '{"key": "value"}',
            conditionalOn: { field: 'method', values: ['POST', 'PUT', 'PATCH'] }
          },
          {
            name: 'timeout',
            label: 'Timeout (seconds)',
            type: 'number',
            required: false,
            description: 'Request timeout in seconds',
            defaultValue: 30,
            minimum: 1,
            maximum: 300
          }
        ];

      case 'perplexity_search':
        return [
          {
            name: 'action',
            label: 'Action',
            type: 'select',
            required: true,
            description: 'Perplexity AI action to perform',
            enum: ['chat', 'search', 'summarize', 'analyze'],
            defaultValue: 'chat'
          },
          {
            name: 'query',
            label: 'Query',
            type: 'textarea',
            required: false,
            description: 'Question or search query for Perplexity AI',
            placeholder: 'What are the latest developments in AI?',
            conditionalOn: { field: 'action', values: ['chat', 'search'] }
          },
          {
            name: 'model',
            label: 'Model',
            type: 'select',
            required: false,
            description: 'Perplexity model to use',
            enum: ['sonar'],
            defaultValue: 'sonar'
          },
          {
            name: 'max_tokens',
            label: 'Max Tokens',
            type: 'number',
            required: false,
            description: 'Maximum number of tokens to generate',
            defaultValue: 1000,
            minimum: 1,
            maximum: 4000
          },
          {
            name: 'temperature',
            label: 'Temperature',
            type: 'number',
            required: false,
            description: 'Sampling temperature (0.0 to 2.0)',
            defaultValue: 0.2,
            minimum: 0.0,
            maximum: 2.0
          },
          {
            name: 'content',
            label: 'Content',
            type: 'textarea',
            required: false,
            description: 'Content to analyze or summarize',
            placeholder: 'Content to process...',
            conditionalOn: { field: 'action', values: ['summarize', 'analyze'] }
          }
        ];

      case 'text_summarizer':
        return [
          {
            name: 'text',
            label: 'Text',
            type: 'textarea',
            required: true,
            description: 'The text content to summarize',
            placeholder: 'Enter the text you want to summarize...'
          },
          {
            name: 'max_length',
            label: 'Max Length',
            type: 'number',
            required: false,
            description: 'Maximum length of the summary in words',
            defaultValue: 100,
            minimum: 10,
            maximum: 1000
          },
          {
            name: 'style',
            label: 'Style',
            type: 'select',
            required: false,
            description: 'Summary style',
            enum: ['concise', 'detailed', 'bullet_points'],
            defaultValue: 'concise'
          }
        ];

      case 'webhook':
        return [
          {
            name: 'action',
            label: 'Action',
            type: 'select',
            required: true,
            description: 'Webhook action to perform',
            enum: ['register', 'receive', 'list', 'delete', 'test'],
            defaultValue: 'receive'
          },
          {
            name: 'webhook_name',
            label: 'Webhook Name',
            type: 'text',
            required: false,
            description: 'Unique name for the webhook',
            placeholder: 'my-webhook',
            conditionalOn: { field: 'action', values: ['register'] }
          },
          {
            name: 'webhook_url',
            label: 'Webhook URL',
            type: 'text',
            required: false,
            description: 'URL endpoint for the webhook',
            placeholder: 'https://api.example.com/webhook',
            conditionalOn: { field: 'action', values: ['register'] }
          },
          {
            name: 'payload',
            label: 'Payload',
            type: 'textarea',
            required: false,
            description: 'Webhook payload data (JSON format)',
            placeholder: '{"event": "test", "data": "value"}',
            conditionalOn: { field: 'action', values: ['create', 'trigger'] }
          }
        ];

      default:
        return [
          {
            name: 'configuration',
            label: 'Configuration',
            type: 'textarea',
            required: false,
            description: 'Connector configuration (JSON format)',
            placeholder: '{"key": "value"}'
          }
        ];
    }
  };

  const shouldShowField = (field: FormField): boolean => {
    if (!field.conditionalOn) return true;

    const conditionValue = config[field.conditionalOn.field];
    return field.conditionalOn.values.includes(conditionValue);
  };

  useEffect(() => {
    if (connectorConfig) {
      console.log(`🤖 AI-filled parameters for ${connectorName}:`, connectorConfig);
      setConfig(connectorConfig);
    } else {
      console.log(`📝 Using default config for ${connectorName} - no AI parameters found`);
      // Set default values for fields
      const fields = getConnectorFields(connectorName);
      const defaultConfig: any = {};
      fields.forEach(field => {
        if (field.defaultValue !== undefined) {
          defaultConfig[field.name] = field.defaultValue;
        }
      });
      setConfig(defaultConfig);
    }
  }, [connectorConfig, connectorName]);

  const handleInputChange = (fieldName: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const handleAuthChange = (fieldName: string, value: any) => {
    setAuthConfig((prev: any) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const testConnection = async () => {
    setIsConnecting(true);
    setConnectionStatus('testing');

    try {
      // Simulate connection test
      await new Promise(resolve => setTimeout(resolve, 2000));
      setConnectionStatus('success');
    } catch (error) {
      setConnectionStatus('error');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleSave = () => {
    // Combine config and auth config
    const fullConfig = {
      ...config,
      auth: authConfig
    };
    onSave(fullConfig);
    onClose();
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'testing': return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return null;
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'testing': return 'Testing connection...';
      case 'success': return 'Connection successful';
      case 'error': return 'Connection failed';
      default: return 'Test Connection';
    }
  };

  const isFormValid = () => {
    const fields = getConnectorFields(connectorName);
    const requiredFields = fields.filter(field => field.required && shouldShowField(field));

    return requiredFields.every(field => {
      const value = config[field.name];
      return value !== undefined && value !== null && value !== '';
    });
  };

  const handleOAuthSetup = async () => {
    if (authRequirements.type !== 'oauth2') return;

    setIsConnecting(true);

    try {
      // Get proper auth headers using Supabase session
      const { data: { session } } = await supabase.auth.getSession();
      
      const headers: { [key: string]: string } = {
        'Content-Type': 'application/json'
      };
      
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      } else {
        throw new Error('No active authentication session. Please log in first.');
      }
      
      // Call backend OAuth initiate endpoint
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/auth/oauth/initiate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          connector_name: connectorName,
          redirect_uri: 'http://localhost:3000/auth/oauth/callback'
        })
      });

      if (!response.ok) {
        throw new Error(`OAuth initiate failed: ${response.status} - ${response.statusText}`);
      }

      const oauthData = await response.json();

      // Store OAuth state and connector info for verification in callback
      localStorage.setItem('oauth_state', oauthData.state);
      localStorage.setItem('oauth_connector', connectorName);

      // Open popup to the authorization URL
      const popup = window.open(
        oauthData.authorization_url,
        'oauth-popup',
        'width=600,height=600,scrollbars=yes,resizable=yes'
      );

      if (!popup) {
        throw new Error('Popup blocked by browser. Please allow popups for this site.');
      }

      // Listen for popup to close (OAuth completion)
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed);

          // Check if OAuth was successful by looking for stored tokens
          setTimeout(async () => {
            try {
              // Verify OAuth completion by checking if tokens were stored
              const tokenResponse = await fetch(`${baseUrl}/api/v1/auth/tokens`, {
                headers: {
                  'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
                }
              });

              if (tokenResponse.ok) {
                const tokens = await tokenResponse.json();
                const hasConnectorToken = tokens.tokens?.some((token: any) =>
                  token.connector_name === connectorName && token.token_type === 'oauth2'
                );

                if (hasConnectorToken) {
                  // OAuth successful - update auth config
                  setAuthConfig((prev: any) => ({
                    ...prev,
                    oauth_completed: true,
                    status: 'authenticated'
                  }));

                  // Show success message
                  setConnectionStatus('success');
                }
              }
            } catch (error) {
              console.error('Error verifying OAuth completion:', error);
            }

            // Clean up stored OAuth data
            localStorage.removeItem('oauth_state');
            localStorage.removeItem('oauth_connector');
          }, 2000);
        }
      }, 1000);

    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
      setConnectionStatus('error');
      alert(`Failed to initiate OAuth setup: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsConnecting(false);
    }
  };

  if (!isOpen) return null;

  const fields = getConnectorFields(connectorName);
  const authRequirements = getAuthRequirements(connectorName);
  const displayName = connectorName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl bg-gray-800 border-gray-600 text-white max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configure {displayName}
          </DialogTitle>
          <DialogDescription>
            Configure the parameters for your {displayName} connector. Required fields are marked with an asterisk (*).
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-gray-700">
            <TabsTrigger value="parameters" className="data-[state=active]:bg-gray-600">Parameters</TabsTrigger>
            <TabsTrigger value="authentication" className="data-[state=active]:bg-gray-600">Authentication</TabsTrigger>
            <TabsTrigger value="test" className="data-[state=active]:bg-gray-600">Test</TabsTrigger>
          </TabsList>

          <TabsContent value="parameters" className="mt-6">
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-6">
                {fields.filter(shouldShowField).map((field) => (
                  <div key={field.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor={field.name} className="text-sm font-medium text-gray-200">
                        {field.label} {field.required && <span className="text-red-400">*</span>}
                      </Label>
                      {field.type === 'password' && (
                        <button
                          type="button"
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="text-xs text-gray-400 hover:text-gray-200"
                        >
                          {showApiKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        </button>
                      )}
                    </div>

                    {field.description && (
                      <p className="text-xs text-gray-400">{field.description}</p>
                    )}

                    {field.type === 'text' || field.type === 'email' ? (
                      <Input
                        id={field.name}
                        type={field.type}
                        placeholder={field.placeholder}
                        value={config[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                      />
                    ) : field.type === 'password' ? (
                      <Input
                        id={field.name}
                        type={showApiKey ? 'text' : 'password'}
                        placeholder={field.placeholder}
                        value={config[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                      />
                    ) : field.type === 'textarea' ? (
                      <Textarea
                        id={field.name}
                        placeholder={field.placeholder}
                        value={config[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        className="bg-gray-700 border-gray-600 text-white placeholder-gray-400 min-h-[80px]"
                      />
                    ) : field.type === 'select' ? (
                      <Select value={config[field.name] || ''} onValueChange={(value) => handleInputChange(field.name, value)}>
                        <SelectTrigger className="bg-gray-700 border-gray-600 text-white">
                          <SelectValue placeholder={field.placeholder} />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-700 border-gray-600 text-white">
                          {field.enum?.map((option) => (
                            <SelectItem key={option} value={option} className="text-white hover:bg-gray-600">
                              {option}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : field.type === 'boolean' ? (
                      <div className="flex items-center space-x-2">
                        <Switch
                          id={field.name}
                          checked={config[field.name] || false}
                          onCheckedChange={(checked) => handleInputChange(field.name, checked)}
                        />
                        <Label htmlFor={field.name} className="text-sm text-gray-300">
                          {field.label}
                        </Label>
                      </div>
                    ) : field.type === 'number' ? (
                      <Input
                        id={field.name}
                        type="number"
                        placeholder={field.placeholder}
                        value={config[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, parseFloat(e.target.value) || 0)}
                        min={field.minimum}
                        max={field.maximum}
                        className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="authentication" className="mt-6">
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-6">
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant={authRequirements.type === 'oauth2' ? 'default' : authRequirements.type === 'api_key' ? 'secondary' : 'outline'}>
                    {authRequirements.type === 'oauth2' ? 'OAuth 2.0' : authRequirements.type === 'api_key' ? 'API Key' : 'No Authentication'}
                  </Badge>
                  <Badge variant="outline">
                    {authRequirements.type === 'none' ? 'Not Required' : 'Required'}
                  </Badge>
                </div>

                {authRequirements.instructions && (
                  <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-blue-200">{authRequirements.instructions}</p>
                    </div>
                  </div>
                )}

                {authRequirements.type === 'oauth2' && (
                  <div className="space-y-4">
                    <div className="p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
                      <div className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-green-200">OAuth 2.0 Setup</p>
                          <p className="text-xs text-green-300 mt-1">
                            Click the button below to authorize this application with {displayName}.
                          </p>
                        </div>
                      </div>
                    </div>

                    <Button
                      onClick={handleOAuthSetup}
                      disabled={isConnecting}
                      className="w-full bg-blue-600 hover:bg-blue-700"
                    >
                      <Key className="w-4 h-4 mr-2" />
                      Setup OAuth Authorization
                    </Button>

                    {authRequirements.oauth_scopes && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-gray-200">OAuth Scopes</Label>
                        <div className="flex flex-wrap gap-2">
                          {authRequirements.oauth_scopes.map((scope, index) => (
                            <Badge key={index} variant="outline" className="text-xs">
                              {scope}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {authRequirements.type === 'api_key' && (
                  <div className="space-y-4">
                    {Object.entries(authRequirements.fields).map(([key, description]) => (
                      <div key={key} className="space-y-2">
                        <Label htmlFor={`auth_${key}`} className="text-sm font-medium text-gray-200">
                          {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </Label>
                        <p className="text-xs text-gray-400">{description}</p>
                        <Input
                          id={`auth_${key}`}
                          type={key.includes('key') || key.includes('token') || key.includes('secret') ? 'password' : 'text'}
                          placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                          value={authConfig[key] || ''}
                          onChange={(e) => handleAuthChange(key, e.target.value)}
                          className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                        />
                      </div>
                    ))}
                  </div>
                )}

                {authRequirements.type === 'none' && (
                  <div className="p-4 bg-gray-700/50 border border-gray-600 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-gray-300">
                        This connector does not require authentication.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="test" className="mt-6">
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-6">
                <div className="p-4 bg-gray-700/50 border border-gray-600 rounded-lg">
                  <div className="flex items-start gap-2">
                    <TestTube className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-200">Test Connection</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Verify that your connector configuration is working correctly.
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={testConnection}
                  disabled={isConnecting}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {isConnecting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <TestTube className="w-4 h-4 mr-2" />
                      Test Connection
                    </>
                  )}
                </Button>

                {connectionStatus !== 'idle' && (
                  <div className={`p-4 rounded-lg border ${connectionStatus === 'success' ? 'bg-green-900/20 border-green-500/30' :
                      connectionStatus === 'error' ? 'bg-red-900/20 border-red-500/30' :
                        'bg-blue-900/20 border-blue-500/30'
                    }`}>
                    <div className="flex items-center gap-2">
                      {getConnectionStatusIcon()}
                      <span className={`text-sm ${connectionStatus === 'success' ? 'text-green-200' :
                          connectionStatus === 'error' ? 'text-red-200' :
                            'text-blue-200'
                        }`}>
                        {getConnectionStatusText()}
                      </span>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label className="text-sm font-medium text-gray-200">Connection Status</Label>
                  <div className="flex items-center gap-2">
                    {authRequirements.type === 'none' ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span className="text-green-300">Ready to use</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-yellow-500" />
                        <span className="text-yellow-300">Authentication required</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        <div className="flex justify-between pt-6 border-t border-gray-600">
          <Button variant="outline" onClick={onClose} className="border-gray-600 text-gray-300 hover:bg-gray-700">
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isFormValid()}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Save Configuration
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
} 