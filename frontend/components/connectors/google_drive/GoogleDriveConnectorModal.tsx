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
    Cloud,
    File,
    Folder,
    Download,
    Upload,
    Share,
    Search,
    Copy,
    Trash2,
    Eye,
    Edit,
    Loader2
} from 'lucide-react';

interface GoogleDriveConfig {
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

interface GoogleDriveConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: any) => void;
    initialConfig?: Partial<GoogleDriveConfig>;
    initialData?: any;
    mode?: 'create' | 'edit';
}

const driveActions = [
    { value: 'list_files', label: 'List Files', icon: File, category: 'Read' },
    { value: 'get_file', label: 'Get File Info', icon: Eye, category: 'Read' },
    { value: 'download_file', label: 'Download File', icon: Download, category: 'Read' },
    { value: 'upload_file', label: 'Upload File', icon: Upload, category: 'Write' },
    { value: 'create_folder', label: 'Create Folder', icon: Folder, category: 'Write' },
    { value: 'copy_file', label: 'Copy File', icon: Copy, category: 'Write' },
    { value: 'move_file', label: 'Move File', icon: Edit, category: 'Write' },
    { value: 'delete_file', label: 'Delete File', icon: Trash2, category: 'Write' },
    { value: 'share_file', label: 'Share File', icon: Share, category: 'Manage' },
    { value: 'search_files', label: 'Search Files', icon: Search, category: 'Read' }
];

export function GoogleDriveConnectorModal({
    isOpen,
    onClose,
    onSave,
    initialConfig,
    initialData,
    mode = 'create'
}: GoogleDriveConnectorModalProps) {
    const { user, session } = useAuth();
    const [activeTab, setActiveTab] = useState('action');
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [authStatus, setAuthStatus] = useState<'none' | 'authenticated' | 'error'>('none');

    // Configuration state
    const [config, setConfig] = useState<GoogleDriveConfig>({
        name: 'google_drive',
        display_name: 'Google Drive Connector',
        description: 'Google Drive file operations connector',
        auth_type: 'oauth',
        auth_config: {
            scopes: [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
        },
        settings: {}
    });

    // Action configuration state
    const [actionConfig, setActionConfig] = useState({
        action: 'list_files',
        file_id: '',
        folder_id: '',
        file_name: '',
        query: '',
        mime_type: '',
        parent_folder_id: '',
        // Upload/Create operations
        file_content: '',
        folder_name: '',
        // Share operations
        email: '',
        role: 'reader',
        // Advanced options
        include_trashed: false,
        page_size: 100,
        order_by: 'modifiedTime desc'
    });

    // Initialize configuration - reload every time modal opens with saved config
    useEffect(() => {
        if (isOpen && initialConfig) {
            console.log('🔄 Google Drive Modal: Loading saved configuration:', initialConfig);

            // Load general config
            setConfig(prev => ({ ...prev, ...initialConfig }));

            // Load saved parameters into actionConfig
            if (initialConfig.parameters) {
                console.log('🔄 Google Drive Modal: Loading saved parameters:', initialConfig.parameters);
                setActionConfig(prev => ({ ...prev, ...initialConfig.parameters }));
            }

            if (initialConfig.auth_config?.access_token) {
                setAuthStatus('authenticated');
            }
        }
    }, [isOpen, initialConfig]);

    // Check authentication status
    const checkAuthStatus = async () => {
        if (!session?.access_token) {
            console.log('🔐 Google Drive Modal: No session token available');
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
                const driveToken = data.tokens?.find((token: any) => {
                    return token.connector_name === 'google_drive' &&
                        token.token_type === 'oauth2';
                });

                if (driveToken) {
                    setAuthStatus('authenticated');
                } else {
                    setAuthStatus('none');
                }
            } else {
                setAuthStatus('none');
            }
        } catch (error) {
            console.error('🔐 Google Drive Modal: Error checking auth status:', error);
            setAuthStatus('none');
        }
    };



    // Check authentication status when modal opens
    useEffect(() => {
        if (!isOpen) return;
        checkAuthStatus();
    }, [isOpen, session?.access_token]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Google Drive Modal: Received AI-generated parameters:', initialData);

            setActionConfig(prev => ({
                ...prev,
                ...initialData
            }));

            if (initialData.action) {
                const validActions = driveActions.map(a => a.value);
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
                    connector_name: 'google_drive',
                    redirect_uri: 'http://localhost:3000/auth/oauth/callback'
                })
            });

            if (!response.ok) {
                throw new Error(`OAuth initiate failed: ${response.status}`);
            }

            const oauthData = await response.json();

            localStorage.setItem('oauth_state', oauthData.state);
            localStorage.setItem('oauth_connector', 'google_drive');

            const popup = window.open(oauthData.authorization_url, 'oauth-popup', 'width=600,height=600');

            const checkClosed = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(checkClosed);
                    setIsLoading(false);

                    setTimeout(() => {
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
            const response = await fetch(`${baseUrl}/api/v1/auth/tokens/google_drive/oauth2`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setAuthStatus('none');
                console.log('🔐 Google Drive: Successfully disconnected');
            } else {
                console.error('🔐 Google Drive: Failed to disconnect');
            }
        } catch (error) {
            console.error('🔐 Google Drive: Error disconnecting:', error);
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
            case 'list_files':
            case 'search_files':
                return (
                    <div className="space-y-4">
                        {action === 'list_files' && (
                            <div>
                                <Label htmlFor="folder_id">Folder (Optional)</Label>
                                <DynamicSelect
                                    connectorName="google_drive"
                                    fieldName="folder_id"
                                    value={actionConfig.folder_id}
                                    onValueChange={(value) => setActionConfig(prev => ({ ...prev, folder_id: value }))}
                                    placeholder="Select a folder (or leave empty for root)..."
                                    searchable={true}
                                    className="mt-1"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Select a specific folder to list files from, or leave empty to list from root.
                                </p>
                            </div>
                        )}

                        {action === 'search_files' && (
                            <div>
                                <Label htmlFor="query">Search Query (Required)</Label>
                                <Input
                                    id="query"
                                    value={actionConfig.query}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, query: e.target.value }))}
                                    placeholder="name contains 'document' or mimeType='application/pdf'"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Use Google Drive search syntax (e.g., name contains 'text', mimeType='image/jpeg')
                                </p>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="page_size">Max Results</Label>
                                <Input
                                    id="page_size"
                                    type="number"
                                    value={actionConfig.page_size}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, page_size: parseInt(e.target.value) || 100 }))}
                                    min="1"
                                    max="1000"
                                />
                            </div>
                            <div className="flex items-center space-x-2 pt-6">
                                <Switch
                                    id="include_trashed"
                                    checked={actionConfig.include_trashed}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, include_trashed: checked }))}
                                />
                                <Label htmlFor="include_trashed">Include Trashed</Label>
                            </div>
                        </div>
                    </div>
                );

            case 'get_file':
            case 'download_file':
            case 'delete_file':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="file_id">Google Drive File (Required)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="file_id"
                                value={actionConfig.file_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, file_id: value }))}
                                placeholder="Select a Google Drive file..."
                                searchable={true}
                                className="mt-1"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Select from your Google Drive files. Files are fetched from your authenticated account.
                            </p>
                        </div>
                    </div>
                );

            case 'upload_file':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="file_name">File Name (Required)</Label>
                            <Input
                                id="file_name"
                                value={actionConfig.file_name}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, file_name: e.target.value }))}
                                placeholder="document.pdf"
                            />
                        </div>

                        <div>
                            <Label htmlFor="file_content">File Content (Required)</Label>
                            <Textarea
                                id="file_content"
                                value={actionConfig.file_content}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, file_content: e.target.value }))}
                                placeholder="File content or base64 encoded data"
                                rows={4}
                            />
                        </div>

                        <div>
                            <Label htmlFor="parent_folder_id">Parent Folder (Optional)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="folder_id"
                                value={actionConfig.parent_folder_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, parent_folder_id: value }))}
                                placeholder="Select parent folder (or leave empty for root)..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>
                    </div>
                );

            case 'create_folder':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="folder_name">Folder Name (Required)</Label>
                            <Input
                                id="folder_name"
                                value={actionConfig.folder_name}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, folder_name: e.target.value }))}
                                placeholder="My New Folder"
                            />
                        </div>

                        <div>
                            <Label htmlFor="parent_folder_id">Parent Folder (Optional)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="folder_id"
                                value={actionConfig.parent_folder_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, parent_folder_id: value }))}
                                placeholder="Select parent folder (or leave empty for root)..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>
                    </div>
                );

            case 'copy_file':
            case 'move_file':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="file_id">Source File (Required)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="file_id"
                                value={actionConfig.file_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, file_id: value }))}
                                placeholder="Select file to copy/move..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="parent_folder_id">Destination Folder (Optional)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="folder_id"
                                value={actionConfig.parent_folder_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, parent_folder_id: value }))}
                                placeholder="Select destination folder..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        {action === 'copy_file' && (
                            <div>
                                <Label htmlFor="file_name">New File Name (Optional)</Label>
                                <Input
                                    id="file_name"
                                    value={actionConfig.file_name}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, file_name: e.target.value }))}
                                    placeholder="Leave empty to keep original name"
                                />
                            </div>
                        )}
                    </div>
                );

            case 'share_file':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="file_id">File to Share (Required)</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="file_id"
                                value={actionConfig.file_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, file_id: value }))}
                                placeholder="Select file to share..."
                                searchable={true}
                                className="mt-1"
                            />
                        </div>

                        <div>
                            <Label htmlFor="email">Email Address (Required)</Label>
                            <Input
                                id="email"
                                type="email"
                                value={actionConfig.email}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, email: e.target.value }))}
                                placeholder="user@example.com"
                            />
                        </div>

                        <div>
                            <Label htmlFor="role">Permission Role</Label>
                            <Select
                                value={actionConfig.role}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, role: value }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="reader">Reader (View only)</SelectItem>
                                    <SelectItem value="commenter">Commenter (View and comment)</SelectItem>
                                    <SelectItem value="writer">Writer (Edit access)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                );

            default:
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="file_id">Google Drive File</Label>
                            <DynamicSelect
                                connectorName="google_drive"
                                fieldName="file_id"
                                value={actionConfig.file_id}
                                onValueChange={(value) => setActionConfig(prev => ({ ...prev, file_id: value }))}
                                placeholder="Select a Google Drive file..."
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
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <Cloud className="h-5 w-5 text-blue-600" />
                        </div>
                        <span>Configure Google Drive</span>
                    </DialogTitle>
                    <DialogDescription>
                        Connect to Google Drive to manage files and folders.
                    </DialogDescription>
                </DialogHeader>

                {/* AI-Generated Parameters Indicator */}
                {initialData && Object.keys(initialData).length > 0 && (
                    <Alert className="border-green-200 bg-green-50">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                            <strong>AI-Generated Configuration Detected!</strong>
                            {initialData.action && ` Action: ${initialData.action}`}
                            {initialData.file_name && ` • File: ${initialData.file_name}`}
                            {initialData.query && ` • Query: ${initialData.query}`}
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
                                <CardTitle>Google Drive Action</CardTitle>
                                <CardDescription>
                                    Select the operation you want to perform on Google Drive.
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
                                            {driveActions.map((action) => {
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
                                    Authenticate with Google to access your Drive files.
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
                                                {authStatus === 'authenticated' ? 'Connected to Google Drive' :
                                                    authStatus === 'error' ? 'Authentication Error' :
                                                        'Not Connected'}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {authStatus === 'authenticated' ? 'You can access your Google Drive files' :
                                                    authStatus === 'error' ? 'Please try authenticating again' :
                                                        'Connect to access your files and folders'}
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
                                        This will open a popup window to authenticate with Google Drive.
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
                                    Test your Google Drive connection and authentication.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Button
                                    onClick={() => {/* Add test logic */ }}
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
                        className="bg-blue-600 hover:bg-blue-700"
                        disabled={authStatus !== 'authenticated'}
                    >
                        Save Configuration
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}