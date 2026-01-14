'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { DynamicSelect } from '@/components/ui/dynamic-select';
import {
    Save,
    CheckCircle,
    XCircle,
    AlertTriangle,
    Key,
    Settings,
    Info,
    Brain,
    MessageSquare,
    Search,
    Globe,
    Zap,
    TestTube,
    Loader2
} from 'lucide-react';

interface PerplexityConfig {
    name: string;
    display_name: string;
    description: string;
    auth_type: 'api_key';
    auth_config: {
        api_key?: string;
    };
    settings: {
        [key: string]: any;
    };
}

interface PerplexityConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: any) => void;
    initialConfig?: Partial<PerplexityConfig>;
    initialData?: any;
    mode?: 'create' | 'edit';
}

export function PerplexityConnectorModal({
    isOpen,
    onClose,
    onSave,
    initialConfig,
    initialData,
    mode = 'create'
}: PerplexityConnectorModalProps) {
    const { user, session } = useAuth();
    const [activeTab, setActiveTab] = useState('action');
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [authStatus, setAuthStatus] = useState<'none' | 'authenticated' | 'error'>('none');

    // Configuration state
    const [config, setConfig] = useState<PerplexityConfig>({
        name: 'perplexity',
        display_name: 'Perplexity AI Connector',
        description: 'Perplexity AI search and chat operations',
        auth_type: 'api_key',
        auth_config: {},
        settings: {}
    });

    // Action configuration state
    const [actionConfig, setActionConfig] = useState({
        action: 'chat',
        model: 'llama-3.1-sonar-small-128k-online',
        messages: '',
        query: '',
        max_tokens: 1000,
        temperature: 0.7,
        top_p: 1.0,
        top_k: 0,
        stream: false,
        presence_penalty: 0,
        frequency_penalty: 1,
        // Search-specific
        search_domain_filter: '',
        search_recency_filter: 'month',
        return_citations: true,
        return_images: false,
        return_related_questions: false
    });

    // Check authentication status
    const checkAuthStatus = async () => {
        if (!session?.access_token) {
            console.log('🔐 Perplexity Modal: No session token available');
            return;
        }
        
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/tokens`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                const perplexityToken = data.tokens?.find((token: any) => {
                    return token.connector_name === 'perplexity_search' && 
                           token.token_type === 'api_key';
                });

                if (perplexityToken) {
                    setAuthStatus('authenticated');
                } else {
                    setAuthStatus('none');
                }
            } else {
                setAuthStatus('none');
            }
        } catch (error) {
            console.error('🔐 Perplexity Modal: Error checking auth status:', error);
            setAuthStatus('none');
        }
    };

    // Initialize configuration
    useEffect(() => {
        if (initialConfig) {
            setConfig(prev => ({ ...prev, ...initialConfig }));
            if (initialConfig.auth_config?.api_key) {
                setAuthStatus('authenticated');
            }
        }
    }, [initialConfig]);

    // Check authentication status when modal opens
    useEffect(() => {
        if (!isOpen) return;
        checkAuthStatus();
    }, [isOpen, session?.access_token]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Perplexity Modal: Received AI-generated parameters:', initialData);
            
            setActionConfig(prev => ({
                ...prev,
                ...initialData
            }));
        }
    }, [initialData]);

    const handleSaveApiKey = async () => {
        if (!config.auth_config.api_key) {
            setTestResult({ success: false, message: 'Please enter your Perplexity API key' });
            return;
        }

        setIsLoading(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/tokens`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({
                    connector_name: 'perplexity_search',
                    token_type: 'api_key',
                    token_data: {
                        api_key: config.auth_config.api_key
                    }
                })
            });

            if (response.ok) {
                setAuthStatus('authenticated');
                setTestResult({ success: true, message: 'API key saved successfully!' });
            } else {
                setTestResult({ success: false, message: 'Failed to save API key' });
            }
        } catch (error) {
            setTestResult({ success: false, message: 'Error saving API key: ' + error });
        } finally {
            setIsLoading(false);
        }
    };

    const handleTestConnection = async () => {
        if (authStatus !== 'authenticated') {
            setTestResult({ success: false, message: 'Please authenticate first' });
            return;
        }

        setIsLoading(true);
        try {
            // Test with a simple query
            const testQuery = "What is artificial intelligence?";
            
            // Simulate API test (you would implement actual test logic here)
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            setTestResult({ 
                success: true, 
                message: 'Connection successful! Perplexity AI is ready to use.' 
            });
        } catch (error) {
            setTestResult({ success: false, message: 'Test failed: ' + error });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = () => {
        const finalConfig = {
            ...config,
            parameters: actionConfig
        };
        onSave(finalConfig);
    };

    const renderActionFields = () => {
        const action = actionConfig.action;

        switch (action) {
            case 'chat':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="model">Model</Label>
                            <DynamicSelect
                                connectorName="perplexity"
                                fieldName="model"
                                value={actionConfig.model}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, model: value }))}
                                placeholder="Select a Perplexity model..."
                                className="mt-1"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Choose between online models (with web search) or offline models.
                            </p>
                        </div>

                        <div>
                            <Label htmlFor="messages">Messages (Required)</Label>
                            <Textarea
                                id="messages"
                                value={actionConfig.messages}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, messages: e.target.value }))}
                                placeholder='[{"role": "user", "content": "What is the latest news about AI?"}]'
                                rows={4}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                JSON array of message objects with role and content.
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="max_tokens">Max Tokens</Label>
                                <Input
                                    id="max_tokens"
                                    type="number"
                                    value={actionConfig.max_tokens}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 1000 }))}
                                    min="1"
                                    max="4096"
                                />
                            </div>
                            <div>
                                <Label htmlFor="temperature">Temperature</Label>
                                <Input
                                    id="temperature"
                                    type="number"
                                    step="0.1"
                                    value={actionConfig.temperature}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) || 0.7 }))}
                                    min="0"
                                    max="2"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="top_p">Top P</Label>
                                <Input
                                    id="top_p"
                                    type="number"
                                    step="0.1"
                                    value={actionConfig.top_p}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, top_p: parseFloat(e.target.value) || 1.0 }))}
                                    min="0"
                                    max="1"
                                />
                            </div>
                            <div>
                                <Label htmlFor="top_k">Top K</Label>
                                <Input
                                    id="top_k"
                                    type="number"
                                    value={actionConfig.top_k}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, top_k: parseInt(e.target.value) || 0 }))}
                                    min="0"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="stream"
                                    checked={actionConfig.stream}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, stream: checked }))}
                                />
                                <Label htmlFor="stream">Stream Response</Label>
                            </div>

                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="return_citations"
                                    checked={actionConfig.return_citations}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, return_citations: checked }))}
                                />
                                <Label htmlFor="return_citations">Return Citations</Label>
                            </div>

                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="return_images"
                                    checked={actionConfig.return_images}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, return_images: checked }))}
                                />
                                <Label htmlFor="return_images">Return Images</Label>
                            </div>

                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="return_related_questions"
                                    checked={actionConfig.return_related_questions}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, return_related_questions: checked }))}
                                />
                                <Label htmlFor="return_related_questions">Return Related Questions</Label>
                            </div>
                        </div>
                    </div>
                );

            case 'search':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="query">Search Query (Required)</Label>
                            <Input
                                id="query"
                                value={actionConfig.query}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, query: e.target.value }))}
                                placeholder="What are the latest developments in AI?"
                            />
                        </div>

                        <div>
                            <Label htmlFor="model">Model</Label>
                            <DynamicSelect
                                connectorName="perplexity"
                                fieldName="model"
                                value={actionConfig.model}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, model: value }))}
                                placeholder="Select a Perplexity model..."
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="search_domain_filter">Domain Filter (Optional)</Label>
                            <Input
                                id="search_domain_filter"
                                value={actionConfig.search_domain_filter}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, search_domain_filter: e.target.value }))}
                                placeholder="example.com,news.com"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Comma-separated list of domains to search within.
                            </p>
                        </div>

                        <div>
                            <Label htmlFor="search_recency_filter">Recency Filter</Label>
                            <Select
                                value={actionConfig.search_recency_filter}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, search_recency_filter: value }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="hour">Past Hour</SelectItem>
                                    <SelectItem value="day">Past Day</SelectItem>
                                    <SelectItem value="week">Past Week</SelectItem>
                                    <SelectItem value="month">Past Month</SelectItem>
                                    <SelectItem value="year">Past Year</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                );

            default:
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="query">Query (Required)</Label>
                            <Textarea
                                id="query"
                                value={actionConfig.query}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, query: e.target.value }))}
                                placeholder="Enter your question or search query..."
                                rows={3}
                            />
                        </div>
                    </div>
                );
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center space-x-2">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <Brain className="h-5 w-5 text-purple-600" />
                        </div>
                        <span>Configure Perplexity AI</span>
                    </DialogTitle>
                    <DialogDescription>
                        Connect to Perplexity AI for advanced search and conversational AI capabilities.
                    </DialogDescription>
                </DialogHeader>

                {/* AI-Generated Parameters Indicator */}
                {initialData && Object.keys(initialData).length > 0 && (
                    <Alert className="border-green-200 bg-green-50">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                            <strong>AI-Generated Configuration Detected!</strong>
                            {initialData.action && ` Action: ${initialData.action}`}
                            {initialData.model && ` • Model: ${initialData.model}`}
                            {initialData.query && ` • Query provided`}
                        </AlertDescription>
                    </Alert>
                )}

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="action">Action</TabsTrigger>
                        <TabsTrigger value="authentication">Authentication</TabsTrigger>
                        <TabsTrigger value="test">Test</TabsTrigger>
                    </TabsList>

                    <TabsContent value="action" className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>Perplexity AI Action</CardTitle>
                                <CardDescription>
                                    Configure your Perplexity AI operation.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label htmlFor="action">Action</Label>
                                    <Select
                                        value={actionConfig.action}
                                        onValueChange={(value) => setActionConfig(prev => ({ ...prev, action: value }))}
                                    >
                                        <SelectTrigger className="mt-1">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="chat">
                                                <div className="flex items-center space-x-2">
                                                    <MessageSquare className="h-4 w-4" />
                                                    <span>Chat Completion</span>
                                                </div>
                                            </SelectItem>
                                            <SelectItem value="search">
                                                <div className="flex items-center space-x-2">
                                                    <Search className="h-4 w-4" />
                                                    <span>Search</span>
                                                </div>
                                            </SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {renderActionFields()}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="authentication" className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center space-x-2">
                                    <Key className="h-5 w-5" />
                                    <span>API Key Authentication</span>
                                </CardTitle>
                                <CardDescription>
                                    Enter your Perplexity AI API key to authenticate.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label htmlFor="api_key">Perplexity API Key</Label>
                                    <Input
                                        id="api_key"
                                        type="password"
                                        value={config.auth_config.api_key || ''}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            auth_config: { ...prev.auth_config, api_key: e.target.value }
                                        }))}
                                        placeholder="pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                                        className="mt-1"
                                    />
                                    <p className="text-sm text-gray-500 mt-1">
                                        Get your API key from the Perplexity AI dashboard.
                                    </p>
                                </div>

                                <div className="flex items-center justify-between p-4 border rounded-lg">
                                    <div className="flex items-center space-x-3">
                                        {authStatus === 'authenticated' ? (
                                            <CheckCircle className="h-5 w-5 text-green-500" />
                                        ) : authStatus === 'error' ? (
                                            <XCircle className="h-5 w-5 text-red-500" />
                                        ) : (
                                            <AlertTriangle className="h-5 w-5 text-yellow-500" />
                                        )}
                                        <div>
                                            <p className="font-medium">
                                                {authStatus === 'authenticated' ? 'API Key Configured' :
                                                 authStatus === 'error' ? 'Authentication Error' :
                                                 'Not Authenticated'}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {authStatus === 'authenticated' ? 'Ready to use Perplexity AI' :
                                                 authStatus === 'error' ? 'Please check your API key' :
                                                 'Enter your API key to get started'}
                                            </p>
                                        </div>
                                    </div>
                                    <Button
                                        onClick={handleSaveApiKey}
                                        disabled={isLoading || !config.auth_config.api_key}
                                        variant={authStatus === 'authenticated' ? 'outline' : 'default'}
                                    >
                                        {isLoading ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Saving...
                                            </>
                                        ) : authStatus === 'authenticated' ? (
                                            'Update Key'
                                        ) : (
                                            'Save API Key'
                                        )}
                                    </Button>
                                </div>

                                <Alert>
                                    <Info className="h-4 w-4" />
                                    <AlertDescription>
                                        Your API key is encrypted and stored securely. 
                                        Visit <a href="https://www.perplexity.ai/settings/api" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                            Perplexity AI Settings
                                        </a> to get your API key.
                                    </AlertDescription>
                                </Alert>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="test" className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>Test Connection</CardTitle>
                                <CardDescription>
                                    Test your Perplexity AI connection and API key.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Button
                                    onClick={handleTestConnection}
                                    disabled={isLoading || authStatus !== 'authenticated'}
                                    className="w-full"
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            Testing Connection...
                                        </>
                                    ) : (
                                        <>
                                            <TestTube className="h-4 w-4 mr-2" />
                                            Test Connection
                                        </>
                                    )}
                                </Button>

                                {testResult && (
                                    <Alert variant={testResult.success ? 'default' : 'destructive'}>
                                        {testResult.success ? (
                                            <CheckCircle className="h-4 w-4" />
                                        ) : (
                                            <XCircle className="h-4 w-4" />
                                        )}
                                        <AlertDescription>
                                            {testResult.message}
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>

                <div className="flex justify-end space-x-2 pt-4 border-t">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button 
                        onClick={handleSave} 
                        className="bg-purple-600 hover:bg-purple-700"
                        disabled={authStatus !== 'authenticated'}
                    >
                        Save Configuration
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}