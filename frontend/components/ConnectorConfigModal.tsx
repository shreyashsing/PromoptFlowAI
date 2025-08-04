"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  TestTube,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Key,
  Settings,
  Info
} from 'lucide-react';
import { GoogleDriveConnectorModal } from './connectors/google_drive';
import { NotionConnectorModal } from './connectors/notion';
import { YouTubeConnectorModal } from './connectors/youtube';
import { GmailConnectorModal } from './connectors/gmail';

interface ConnectorConfig {
  name: string;
  display_name: string;
  description: string;
  auth_type: 'oauth' | 'api_key' | 'none';
  auth_config: {
    [key: string]: any;
  };
  settings: {
    [key: string]: any;
  };
  status: 'configured' | 'needs_auth' | 'error';
}

interface ConnectorConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectorName: string | null;
  onSave: (config: ConnectorConfig) => Promise<void>;
}

const CONNECTOR_TEMPLATES: { [key: string]: Partial<ConnectorConfig> } = {
  gmail_connector: {
    display_name: 'Gmail',
    description: 'Send and receive emails through Gmail',
    auth_type: 'oauth',
    auth_config: {
      scopes: ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly'],
      redirect_uri: 'http://localhost:3000/auth/oauth/callback'
    },
    settings: {
      default_sender: '',
      signature: '',
      auto_reply: false
    }
  },
  google_sheets: {
    display_name: 'Google Sheets',
    description: 'Read and write data to Google Sheets',
    auth_type: 'oauth',
    auth_config: {
      scopes: ['https://www.googleapis.com/auth/spreadsheets'],
      redirect_uri: 'http://localhost:3000/auth/oauth/callback'
    },
    settings: {
      default_spreadsheet_id: '',
      default_sheet_name: 'Sheet1'
    }
  },
  google_drive: {
    display_name: 'Google Drive',
    description: 'Upload, download, and manage files and folders in Google Drive',
    auth_type: 'oauth',
    auth_config: {
      scopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file'],
      redirect_uri: 'http://localhost:3000/auth/oauth/callback'
    },
    settings: {
      default_action: 'list_files',
      default_parent_folder: 'root',
      max_results: 100
    }
  },
  http_request: {
    display_name: 'HTTP Request',
    description: 'Make HTTP requests to external APIs',
    auth_type: 'api_key',
    auth_config: {
      header_name: 'Authorization',
      prefix: 'Bearer '
    },
    settings: {
      base_url: '',
      timeout: 30,
      retry_count: 3
    }
  },
  perplexity_search: {
    display_name: 'Perplexity Search',
    description: 'Search and analyze web content using Perplexity AI',
    auth_type: 'api_key',
    auth_config: {
      header_name: 'Authorization',
      prefix: 'Bearer '
    },
    settings: {
      model: 'llama-3.1-sonar-small-128k-online',
      max_tokens: 1000
    }
  },
  text_summarizer: {
    display_name: 'Text Summarizer',
    description: 'Summarize long text content using AI',
    auth_type: 'none',
    auth_config: {},
    settings: {
      max_length: 500,
      style: 'concise'
    }
  },
  webhook: {
    display_name: 'Webhook',
    description: 'Trigger workflows via HTTP webhooks',
    auth_type: 'none',
    auth_config: {},
    settings: {
      allowed_methods: ['POST'],
      response_format: 'json'
    }
  },
  notion: {
    display_name: 'Notion',
    description: 'Interact with Notion workspaces, databases, pages, and blocks',
    auth_type: 'api_key',
    auth_config: {
      header_name: 'Authorization',
      prefix: 'Bearer '
    },
    settings: {
      resource: 'page',
      operation: 'get_page',
      simple_output: false,
      return_all: false,
      page_size: 100,
      include_nested_blocks: false
    }
  }
};

export const ConnectorConfigModal: React.FC<ConnectorConfigModalProps> = ({
  isOpen,
  onClose,
  connectorName,
  onSave
}) => {
  // Use specialized modals for specific connectors
  if (connectorName === 'google_drive') {
    return (
      <GoogleDriveConnectorModal
        isOpen={isOpen}
        onClose={onClose}
        onSave={onSave}
      />
    );
  }

  if (connectorName === 'notion') {
    return (
      <NotionConnectorModal
        isOpen={isOpen}
        onClose={onClose}
        onSave={onSave}
      />
    );
  }

  if (connectorName === 'youtube') {
    return (
      <YouTubeConnectorModal
        isOpen={isOpen}
        onClose={onClose}
        onSave={onSave}
      />
    );
  }

  if (connectorName === 'gmail_connector') {
    return (
      <GmailConnectorModal
        isOpen={isOpen}
        onClose={onClose}
        onSave={onSave}
      />
    );
  }
  const { session } = useAuth();
  const [config, setConfig] = useState<ConnectorConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [activeTab, setActiveTab] = useState('settings');

  useEffect(() => {
    if (connectorName && CONNECTOR_TEMPLATES[connectorName]) {
      const template = CONNECTOR_TEMPLATES[connectorName];
      setConfig({
        name: connectorName,
        display_name: template.display_name || connectorName,
        description: template.description || '',
        auth_type: template.auth_type || 'none',
        auth_config: template.auth_config || {},
        settings: template.settings || {},
        status: 'needs_auth'
      });
    }
  }, [connectorName]);

  const handleSettingChange = (key: string, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      settings: {
        ...config.settings,
        [key]: value
      }
    });
  };

  const handleAuthConfigChange = (key: string, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      auth_config: {
        ...config.auth_config,
        [key]: value
      }
    });
  };

  const handleOAuthSetup = async () => {
    if (!config || config.auth_type !== 'oauth') return;

    setIsLoading(true);

    try {
      // First, get the authorization URL and state from the backend
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/auth/oauth/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          connector_name: config.name,
          redirect_uri: 'http://localhost:3000/auth/oauth/callback'
        })
      });

      if (!response.ok) {
        throw new Error(`OAuth initiate failed: ${response.status}`);
      }

      const oauthData = await response.json();

      // Store state and connector info for verification in callback
      localStorage.setItem('oauth_state', oauthData.state);
      localStorage.setItem('oauth_connector', config.name);

      // Open popup to the authorization URL
      const popup = window.open(oauthData.authorization_url, 'oauth-popup', 'width=600,height=600');

      // Listen for popup to close (OAuth completion)
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed);
          // Clean up stored OAuth data after a delay to allow callback processing
          setTimeout(() => {
            localStorage.removeItem('oauth_state');
            localStorage.removeItem('oauth_connector');
          }, 2000);
        }
      }, 1000);

    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
      alert('Failed to initiate OAuth setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!config) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/connectors/${config.name}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          auth_config: config.auth_config,
          settings: config.settings
        })
      });

      const result = await response.json();

      if (response.ok) {
        setTestResult({ success: true, message: 'Connection test successful!' });
      } else {
        setTestResult({ success: false, message: result.detail || 'Connection test failed' });
      }
    } catch (error) {
      setTestResult({ success: false, message: 'Failed to test connection' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    setIsLoading(true);
    try {
      await onSave(config);
      onClose();
    } catch (error) {
      console.error('Failed to save connector config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!config) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configure {config.display_name}
          </DialogTitle>
          <DialogDescription>
            {config.description}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="authentication">Authentication</TabsTrigger>
            <TabsTrigger value="test">Test & Validate</TabsTrigger>
          </TabsList>

          <TabsContent value="settings" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>
                  Configure the basic settings for this connector
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(config.settings).map(([key, value]) => (
                  <div key={key} className="space-y-2">
                    <Label htmlFor={key}>
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Label>
                    {typeof value === 'boolean' ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={key}
                          checked={value}
                          onChange={(e) => handleSettingChange(key, e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm text-muted-foreground">
                          {value ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    ) : typeof value === 'number' ? (
                      <Input
                        id={key}
                        type="number"
                        value={value}
                        onChange={(e) => handleSettingChange(key, parseInt(e.target.value))}
                        placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                      />
                    ) : Array.isArray(value) ? (
                      <Textarea
                        id={key}
                        value={value.join(', ')}
                        onChange={(e) => handleSettingChange(key, e.target.value.split(', ').filter(Boolean))}
                        placeholder={`Enter ${key.replace(/_/g, ' ')} separated by commas`}
                        rows={3}
                      />
                    ) : (
                      <Input
                        id={key}
                        value={value}
                        onChange={(e) => handleSettingChange(key, e.target.value)}
                        placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="authentication" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-4 w-4" />
                  Authentication Setup
                </CardTitle>
                <CardDescription>
                  Configure authentication for {config.display_name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge variant={config.auth_type === 'oauth' ? 'default' : 'secondary'}>
                      {config.auth_type === 'oauth' ? 'OAuth 2.0' : config.auth_type === 'api_key' ? 'API Key' : 'No Authentication'}
                    </Badge>
                    <Badge variant={config.status === 'configured' ? 'default' : 'destructive'}>
                      {config.status === 'configured' ? 'Configured' : 'Needs Setup'}
                    </Badge>
                  </div>

                  {config.auth_type === 'oauth' && (
                    <div className="space-y-4">
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          OAuth authentication requires you to authorize this application with {config.display_name}.
                          Click the button below to start the authorization process.
                        </AlertDescription>
                      </Alert>

                      <Button onClick={handleOAuthSetup} className="w-full" disabled={isLoading}>
                        {isLoading ? 'Setting up OAuth...' : 'Setup OAuth Authorization'}
                      </Button>

                      <div className="space-y-2">
                        <Label>OAuth Scopes</Label>
                        <div className="flex flex-wrap gap-2">
                          {config.auth_config.scopes?.map((scope: string, index: number) => (
                            <Badge key={index} variant="outline">{scope}</Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {config.auth_type === 'api_key' && (
                    <div className="space-y-4">
                      {Object.entries(config.auth_config).map(([key, value]) => (
                        <div key={key} className="space-y-2">
                          <Label htmlFor={`auth_${key}`}>
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </Label>
                          <Input
                            id={`auth_${key}`}
                            value={value as string}
                            onChange={(e) => handleAuthConfigChange(key, e.target.value)}
                            placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                            type={key.includes('key') || key.includes('token') ? 'password' : 'text'}
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {config.auth_type === 'none' && (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        This connector does not require authentication.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="test" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TestTube className="h-4 w-4" />
                  Test Connection
                </CardTitle>
                <CardDescription>
                  Verify that your connector configuration is working correctly
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  className="w-full"
                >
                  {isTesting ? 'Testing...' : 'Test Connection'}
                </Button>

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

                <div className="space-y-2">
                  <Label>Connection Status</Label>
                  <div className="flex items-center gap-2">
                    {config.status === 'configured' ? (
                      <>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-green-700">Ready to use</span>
                      </>
                    ) : config.status === 'needs_auth' ? (
                      <>
                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                        <span className="text-yellow-700">Authentication required</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-red-500" />
                        <span className="text-red-700">Configuration error</span>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-between pt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};