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
    FileSpreadsheet,
    Table,
    Plus,
    Search,
    Edit,
    Eye,
    Download,
    Upload,
    Grid,
    Loader2
} from 'lucide-react';

interface GoogleSheetsConfig {
    name: string;
    display_name: string;
    description: string;
    auth_type: 'oauth';
    auth_config: {
        access_token?: string;
        refresh_token?: string;
        scopes: string[];
    };
    settings: {
        [key: string]: any;
    };
    parameters?: {
        [key: string]: any;
    };
}

interface GoogleSheetsConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: any) => void;
    initialConfig?: Partial<GoogleSheetsConfig>;
    initialData?: any;
    mode?: 'create' | 'edit';
}

const sheetsActions = [
    { value: 'read_range', label: 'Read Range', icon: Eye, category: 'Read' },
    { value: 'write_range', label: 'Write Range', icon: Edit, category: 'Write' },
    { value: 'append_row', label: 'Append Row', icon: Plus, category: 'Write' },
    { value: 'create_sheet', label: 'Create Sheet', icon: FileSpreadsheet, category: 'Manage' },
    { value: 'get_sheet_info', label: 'Get Sheet Info', icon: Info, category: 'Read' },
    { value: 'list_sheets', label: 'List Sheets', icon: Table, category: 'Read' },
    { value: 'clear_range', label: 'Clear Range', icon: XCircle, category: 'Write' },
    { value: 'batch_update', label: 'Batch Update', icon: Upload, category: 'Write' }
];

export function GoogleSheetsConnectorModal({
    isOpen,
    onClose,
    onSave,
    initialConfig,
    initialData,
    mode = 'create'
}: GoogleSheetsConnectorModalProps) {
    const { user, session } = useAuth();
    const [activeTab, setActiveTab] = useState('action');
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [authStatus, setAuthStatus] = useState<'none' | 'authenticated' | 'error'>('none');

    // Configuration state
    const [config, setConfig] = useState<GoogleSheetsConfig>({
        name: 'google_sheets',
        display_name: 'Google Sheets Connector',
        description: 'Google Sheets operations connector',
        auth_type: 'oauth',
        auth_config: {
            scopes: [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        },
        settings: {}
    });

    // Action configuration state
    const [actionConfig, setActionConfig] = useState({
        action: 'read_range',
        spreadsheet_id: '',
        sheet_name: '',
        range: 'A1:Z100',
        values: [] as string[][],
        value_input_option: 'RAW',
        major_dimension: 'ROWS',
        include_headers: true,
        // Write operations
        data: '',
        // Sheet creation
        sheet_title: '',
        // Advanced options
        format: 'json',
        return_all: false
    });

    // Check authentication status
    const checkAuthStatus = async () => {
        if (!session?.access_token) {
            console.log('🔐 Google Sheets Modal: No session token available');
            return;
        }

        console.log('🔐 Google Sheets Modal: Checking authentication status...');

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
                console.log('🔐 Google Sheets Modal: Auth tokens response:', data);

                const sheetsToken = data.tokens?.find((token: any) => {
                    return token.connector_name === 'google_sheets' &&
                        token.token_type === 'oauth2';
                });

                if (sheetsToken) {
                    console.log('🔐 Google Sheets Modal: Found valid Google Sheets token');
                    setAuthStatus('authenticated');
                } else {
                    console.log('🔐 Google Sheets Modal: No valid Google Sheets token found');
                    setAuthStatus('none');
                }
            } else {
                console.error('🔐 Google Sheets Modal: Failed to check auth status:', response.status);
                setAuthStatus('none');
            }
        } catch (error) {
            console.error('🔐 Google Sheets Modal: Error checking auth status:', error);
            setAuthStatus('none');
        }
    };

    // Initialize configuration - reload every time modal opens with saved config
    useEffect(() => {
        if (isOpen && initialConfig) {
            console.log('🔄 Google Sheets Modal: Loading saved configuration:', initialConfig);

            // Load general config
            setConfig(prev => ({ ...prev, ...initialConfig }));

            // Load saved parameters into actionConfig
            if (initialConfig.parameters) {
                console.log('🔄 Google Sheets Modal: Loading saved parameters:', initialConfig.parameters);
                setActionConfig(prev => ({ ...prev, ...initialConfig.parameters }));
            }

            if (initialConfig.auth_config?.access_token) {
                setAuthStatus('authenticated');
            }
        }
    }, [isOpen, initialConfig]);

    // Check authentication status when modal opens/closes
    useEffect(() => {
        if (isOpen) {
            console.log('🔐 Google Sheets Modal: Modal opened, checking auth status');
            checkAuthStatus();
            
            // Reset to saved configuration when modal opens
            if (initialConfig && initialConfig.parameters) {
                console.log('🔄 Google Sheets Modal: Resetting to saved configuration on open');
                setActionConfig(prev => ({ 
                    ...prev, 
                    ...initialConfig.parameters 
                }));
            }
        } else {
            // Reset only UI state when modal closes, preserve configuration
            console.log('🔄 Google Sheets Modal: Modal closed, resetting state');
            setActiveTab('action');
            setTestResult(null);
            // Don't reset actionConfig here as it should persist for saved configurations
        }
    }, [isOpen, session?.access_token, initialConfig]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Google Sheets Modal: Received AI-generated parameters:', initialData);

            setActionConfig(prev => ({
                ...prev,
                ...initialData
            }));

            if (initialData.action) {
                const validActions = sheetsActions.map(a => a.value);
                if (validActions.includes(initialData.action)) {
                    setActionConfig(prev => ({
                        ...prev,
                        action: initialData.action
                    }));
                }
            }
        }
    }, [initialData]);

    const handleGoogleOAuth = async () => {
        try {
            setIsLoading(true);
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/oauth/initiate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({
                    connector_name: 'google_sheets',
                    redirect_uri: 'http://localhost:3000/auth/oauth/callback'
                })
            });

            if (!response.ok) {
                throw new Error(`OAuth initiate failed: ${response.status}`);
            }

            const oauthData = await response.json();

            localStorage.setItem('oauth_state', oauthData.state);
            localStorage.setItem('oauth_connector', 'google_sheets');

            const popup = window.open(oauthData.authorization_url, 'oauth-popup', 'width=600,height=600');

            const checkClosed = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(checkClosed);
                    setIsLoading(false);

                    setTimeout(() => {
                        console.log('🔐 Google Sheets Modal: OAuth popup closed, checking auth status');
                        checkAuthStatus();
                    }, 1000);
                }
            }, 1000);

        } catch (error) {
            console.error('OAuth error:', error);
            setAuthStatus('error');
            setIsLoading(false);
        }
    };

    const handleDisconnect = async () => {
        try {
            setIsLoading(true);
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/tokens/google_sheets/oauth2`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setAuthStatus('none');
                console.log('🔐 Google Sheets: Successfully disconnected');
            } else {
                console.error('🔐 Google Sheets: Failed to disconnect');
            }
        } catch (error) {
            console.error('🔐 Google Sheets: Error disconnecting:', error);
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
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/test-connector`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({
                    connector_name: 'google_sheets'
                })
            });

            const result = await response.json();
            setTestResult({
                success: result.success,
                message: result.success ? 'Connection successful!' : result.error || 'Connection failed'
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
            case 'read_range':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
                                skipInitialFetch={!!actionConfig.spreadsheet_id}
                                cacheKey="sheets-spreadsheets"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Select from your Google Drive spreadsheets. Files are fetched from your authenticated account.
                            </p>
                        </div>

                        <div>
                            <Label htmlFor="sheet_name">Sheet Name (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="sheet_name"
                                value={actionConfig.sheet_name}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, sheet_name: value }))}
                                placeholder="Select a sheet..."
                                searchable={true}
                                className="mt-1"
                                context={{ spreadsheet_id: actionConfig.spreadsheet_id }}
                                disabled={!actionConfig.spreadsheet_id}
                                skipInitialFetch={!!actionConfig.sheet_name}
                                cacheKey={`sheets-${actionConfig.spreadsheet_id}`}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Select a sheet from the chosen spreadsheet. Available after selecting a spreadsheet.
                            </p>
                        </div>

                        <div>
                            <Label htmlFor="range">Range</Label>
                            <Input
                                id="range"
                                value={actionConfig.range}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, range: e.target.value }))}
                                placeholder="A1:Z100"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Specify the range in A1 notation (e.g., A1:C10, Sheet1!A1:B5)
                            </p>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Switch
                                id="include_headers"
                                checked={actionConfig.include_headers}
                                onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, include_headers: checked }))}
                            />
                            <Label htmlFor="include_headers">Include Headers</Label>
                        </div>
                    </div>
                );

            case 'write_range':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="sheet_name">Sheet Name (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="sheet_name"
                                value={actionConfig.sheet_name}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, sheet_name: value }))}
                                placeholder="Select a sheet..."
                                searchable={true}
                                className="mt-1"
                                context={{ spreadsheet_id: actionConfig.spreadsheet_id }}
                                disabled={!actionConfig.spreadsheet_id}
                            />
                        </div>

                        <div>
                            <Label htmlFor="range">Range (Required)</Label>
                            <Input
                                id="range"
                                value={actionConfig.range}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, range: e.target.value }))}
                                placeholder="A1:C3"
                            />
                        </div>

                        <div>
                            <Label htmlFor="data">Data (Required)</Label>
                            <Textarea
                                id="data"
                                value={actionConfig.data}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, data: e.target.value }))}
                                placeholder="Enter data as JSON array or CSV format"
                                rows={4}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Format: [["A1", "B1", "C1"], ["A2", "B2", "C2"]] or CSV format
                            </p>
                        </div>

                        <div>
                            <Label htmlFor="value_input_option">Value Input Option</Label>
                            <Select
                                value={actionConfig.value_input_option}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, value_input_option: value }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="RAW">Raw (no parsing)</SelectItem>
                                    <SelectItem value="USER_ENTERED">User Entered (parse formulas)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                );

            case 'append_row':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="sheet_name">Sheet Name (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="sheet_name"
                                value={actionConfig.sheet_name}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, sheet_name: value }))}
                                placeholder="Select a sheet..."
                                searchable={true}
                                className="mt-1"
                                context={{ spreadsheet_id: actionConfig.spreadsheet_id }}
                                disabled={!actionConfig.spreadsheet_id}
                            />
                        </div>

                        <div>
                            <Label htmlFor="data">Row Data (Required)</Label>
                            <Textarea
                                id="data"
                                value={actionConfig.data}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, data: e.target.value }))}
                                placeholder='["Column 1", "Column 2", "Column 3"]'
                                rows={3}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Enter row data as JSON array: ["value1", "value2", "value3"]
                            </p>
                        </div>
                    </div>
                );

            case 'create_sheet':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="sheet_title">Sheet Title (Required)</Label>
                            <Input
                                id="sheet_title"
                                value={actionConfig.sheet_title}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, sheet_title: e.target.value }))}
                                placeholder="New Sheet Name"
                            />
                        </div>
                    </div>
                );

            case 'list_sheets':
            case 'get_sheet_info':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>
                    </div>
                );

            default:
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="spreadsheet_id">Google Spreadsheet (Required)</Label>
                            <DynamicSelect
                                connectorName="google_sheets"
                                fieldName="spreadsheet_id"
                                value={actionConfig.spreadsheet_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, spreadsheet_id: value }))}
                                placeholder="Select a Google Spreadsheet..."
                                searchable={true}
                                className="mt-1"
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
                        <div className="p-2 bg-green-100 rounded-lg">
                            <FileSpreadsheet className="h-5 w-5 text-green-600" />
                        </div>
                        <span>Configure Google Sheets</span>
                    </DialogTitle>
                    <DialogDescription>
                        Connect to Google Sheets to read, write, and manage spreadsheet data.
                    </DialogDescription>
                </DialogHeader>

                {/* AI-Generated Parameters Indicator */}
                {initialData && Object.keys(initialData).length > 0 && (
                    <Alert className="border-green-200 bg-green-50">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                            <strong>AI-Generated Configuration Detected!</strong>
                            {initialData.action && ` Action: ${initialData.action}`}
                            {initialData.spreadsheet_id && ` • Spreadsheet selected`}
                            {initialData.range && ` • Range: ${initialData.range}`}
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
                                <CardTitle>Google Sheets Action</CardTitle>
                                <CardDescription>
                                    Select the operation you want to perform on Google Sheets.
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
                                            {sheetsActions.map((action) => {
                                                const Icon = action.icon;
                                                return (
                                                    <SelectItem key={action.value} value={action.value}>
                                                        <div className="flex items-center space-x-2">
                                                            <Icon className="h-4 w-4" />
                                                            <span>{action.label}</span>
                                                            <Badge variant="outline" className="text-xs">
                                                                {action.category}
                                                            </Badge>
                                                        </div>
                                                    </SelectItem>
                                                );
                                            })}
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
                                    <span>Google OAuth Authentication</span>
                                </CardTitle>
                                <CardDescription>
                                    Authenticate with Google to access your spreadsheets.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
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
                                                {authStatus === 'authenticated' ? 'Connected to Google' :
                                                    authStatus === 'error' ? 'Authentication Error' :
                                                        'Not Connected'}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {authStatus === 'authenticated' ? 'You can access your Google Sheets' :
                                                    authStatus === 'error' ? 'Please try authenticating again' :
                                                        'Connect to access your spreadsheets'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex space-x-2">
                                        {authStatus === 'authenticated' ? (
                                            <>
                                                <Button
                                                    onClick={handleGoogleOAuth}
                                                    disabled={isLoading}
                                                    variant="outline"
                                                    size="sm"
                                                >
                                                    {isLoading ? (
                                                        <>
                                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                            Connecting...
                                                        </>
                                                    ) : (
                                                        'Reauthenticate'
                                                    )}
                                                </Button>
                                                <Button
                                                    onClick={handleDisconnect}
                                                    disabled={isLoading}
                                                    variant="outline"
                                                    size="sm"
                                                >
                                                    {isLoading ? (
                                                        <>
                                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                            Disconnecting...
                                                        </>
                                                    ) : (
                                                        'Disconnect'
                                                    )}
                                                </Button>
                                            </>
                                        ) : (
                                            <Button
                                                onClick={handleGoogleOAuth}
                                                disabled={isLoading}
                                                variant="default"
                                            >
                                                {isLoading ? (
                                                    <>
                                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                        Connecting...
                                                    </>
                                                ) : (
                                                    'Connect to Google'
                                                )}
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                <Alert>
                                    <Info className="h-4 w-4" />
                                    <AlertDescription>
                                        This will open a popup window to authenticate with Google.
                                        Make sure to allow popups for this site.
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
                                    Test your Google Sheets connection and authentication.
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
                                        'Test Connection'
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
                        className="bg-green-600 hover:bg-green-700"
                        disabled={authStatus !== 'authenticated'}
                    >
                        Save Configuration
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}