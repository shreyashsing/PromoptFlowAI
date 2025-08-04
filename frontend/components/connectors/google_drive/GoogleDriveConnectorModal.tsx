"use client";

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
import { Separator } from '@/components/ui/separator';
import {
    Save,
    TestTube,
    CheckCircle,
    XCircle,
    AlertTriangle,
    Key,
    Settings,
    Info,
    Upload,
    Download,
    FolderPlus,
    Trash2,
    Move,
    Copy,
    Share,
    Search,
    FileText,
    Edit,
    Shield,
    HardDrive
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
    status: 'configured' | 'needs_auth' | 'error';
}

interface GoogleDriveConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: GoogleDriveConfig) => Promise<void>;
    initialData?: any; // AI-generated parameters
}

// Google Drive action definitions with their specific parameters
const GOOGLE_DRIVE_ACTIONS = {
    upload: {
        label: 'Upload File',
        icon: Upload,
        description: 'Upload a file to Google Drive',
        requiredParams: ['file_name', 'file_content'],
        parameters: [
            { name: 'file_name', type: 'string', label: 'File Name', required: true, placeholder: 'document.pdf' },
            { name: 'file_content', type: 'textarea', label: 'File Content (Base64)', required: true, placeholder: 'Base64 encoded file content...' },
            { name: 'parent_folder_id', type: 'string', label: 'Parent Folder ID', placeholder: 'root (default)' },
            { name: 'mime_type', type: 'string', label: 'MIME Type', placeholder: 'application/pdf' },
            { name: 'description', type: 'string', label: 'Description', placeholder: 'File description' },
            { name: 'convert_to_google_docs', type: 'boolean', label: 'Convert to Google Docs' }
        ]
    },
    download: {
        label: 'Download File',
        icon: Download,
        description: 'Download a file from Google Drive',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            {
                name: 'export_format',
                type: 'select',
                label: 'Export Format (for Google Workspace files)',
                options: [
                    { value: 'application/pdf', label: 'PDF' },
                    { value: 'text/html', label: 'HTML' },
                    { value: 'text/plain', label: 'Plain Text' },
                    { value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', label: 'Word Document' },
                    { value: 'text/csv', label: 'CSV' },
                    { value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', label: 'Excel' },
                    { value: 'image/png', label: 'PNG' },
                    { value: 'image/jpeg', label: 'JPEG' }
                ]
            }
        ]
    },
    create_folder: {
        label: 'Create Folder',
        icon: FolderPlus,
        description: 'Create a new folder in Google Drive',
        requiredParams: ['file_name'],
        parameters: [
            { name: 'file_name', type: 'string', label: 'Folder Name', required: true, placeholder: 'My New Folder' },
            { name: 'parent_folder_id', type: 'string', label: 'Parent Folder ID', placeholder: 'root (default)' },
            { name: 'description', type: 'string', label: 'Description', placeholder: 'Folder description' }
        ]
    },
    delete: {
        label: 'Delete File/Folder',
        icon: Trash2,
        description: 'Delete a file or folder from Google Drive',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' }
        ]
    },
    move: {
        label: 'Move File/Folder',
        icon: Move,
        description: 'Move a file or folder to a different location',
        requiredParams: ['file_id', 'new_parent_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            { name: 'new_parent_id', type: 'string', label: 'New Parent Folder ID', required: true, placeholder: 'Target folder ID' }
        ]
    },
    copy: {
        label: 'Copy File',
        icon: Copy,
        description: 'Create a copy of a file',
        requiredParams: ['file_id', 'new_name'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            { name: 'new_name', type: 'string', label: 'New File Name', required: true, placeholder: 'Copy of document.pdf' },
            { name: 'parent_folder_id', type: 'string', label: 'Parent Folder ID', placeholder: 'root (default)' }
        ]
    },
    share: {
        label: 'Share File/Folder',
        icon: Share,
        description: 'Share a file or folder with others',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            {
                name: 'share_type',
                type: 'select',
                label: 'Share Type',
                required: true,
                options: [
                    { value: 'user', label: 'Specific User' },
                    { value: 'group', label: 'Group' },
                    { value: 'domain', label: 'Domain' },
                    { value: 'anyone', label: 'Anyone with Link' }
                ]
            },
            {
                name: 'share_role',
                type: 'select',
                label: 'Permission Level',
                required: true,
                options: [
                    { value: 'reader', label: 'Reader' },
                    { value: 'commenter', label: 'Commenter' },
                    { value: 'writer', label: 'Writer' },
                    { value: 'owner', label: 'Owner' }
                ]
            },
            { name: 'share_email', type: 'email', label: 'Email Address', placeholder: 'user@example.com' },
            { name: 'share_domain', type: 'string', label: 'Domain', placeholder: 'example.com' },
            { name: 'send_notification', type: 'boolean', label: 'Send Notification Email', default: true },
            { name: 'share_message', type: 'textarea', label: 'Custom Message', placeholder: 'Optional message to include...' }
        ]
    },
    search: {
        label: 'Search Files',
        icon: Search,
        description: 'Search for files and folders in Google Drive',
        requiredParams: ['query'],
        parameters: [
            { name: 'query', type: 'string', label: 'Search Query', required: true, placeholder: "name contains 'report'" },
            { name: 'max_results', type: 'number', label: 'Max Results', default: 100, min: 1, max: 1000 },
            { name: 'order_by', type: 'string', label: 'Order By', placeholder: 'modifiedTime desc' },
            { name: 'include_items_from_all_drives', type: 'boolean', label: 'Include Shared Drives', default: true }
        ]
    },
    get_info: {
        label: 'Get File Info',
        icon: Info,
        description: 'Get detailed information about a file or folder',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            { name: 'fields', type: 'string', label: 'Fields to Return', placeholder: 'id,name,mimeType,size,createdTime' }
        ]
    },
    list_files: {
        label: 'List Files',
        icon: FileText,
        description: 'List files and folders in a directory',
        requiredParams: [],
        parameters: [
            { name: 'parent_folder_id', type: 'string', label: 'Parent Folder ID', placeholder: 'root (default)' },
            { name: 'max_results', type: 'number', label: 'Max Results', default: 100, min: 1, max: 1000 },
            { name: 'order_by', type: 'string', label: 'Order By', placeholder: 'modifiedTime desc' },
            { name: 'include_items_from_all_drives', type: 'boolean', label: 'Include Shared Drives', default: true }
        ]
    },
    create_from_text: {
        label: 'Create Text File',
        icon: FileText,
        description: 'Create a text file from content',
        requiredParams: ['file_name', 'text_content'],
        parameters: [
            { name: 'file_name', type: 'string', label: 'File Name', required: true, placeholder: 'document.txt' },
            { name: 'text_content', type: 'textarea', label: 'Text Content', required: true, placeholder: 'File content...' },
            { name: 'parent_folder_id', type: 'string', label: 'Parent Folder ID', placeholder: 'root (default)' },
            { name: 'mime_type', type: 'string', label: 'MIME Type', placeholder: 'text/plain' },
            { name: 'description', type: 'string', label: 'Description', placeholder: 'File description' }
        ]
    },
    update_file: {
        label: 'Update File',
        icon: Edit,
        description: 'Update file content or metadata',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            { name: 'new_name', type: 'string', label: 'New Name', placeholder: 'Updated filename' },
            { name: 'description', type: 'string', label: 'Description', placeholder: 'Updated description' },
            { name: 'starred', type: 'boolean', label: 'Starred' },
            { name: 'file_content', type: 'textarea', label: 'New Content (Base64)', placeholder: 'Base64 encoded content...' },
            { name: 'mime_type', type: 'string', label: 'MIME Type', placeholder: 'application/pdf' }
        ]
    },
    get_permissions: {
        label: 'Get Permissions',
        icon: Shield,
        description: 'Get permissions for a file or folder',
        requiredParams: ['file_id'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' }
        ]
    },
    update_permissions: {
        label: 'Update Permissions',
        icon: Shield,
        description: 'Update existing permissions for a file or folder',
        requiredParams: ['file_id', 'permission_id', 'share_role'],
        parameters: [
            { name: 'file_id', type: 'string', label: 'File/Folder ID', required: true, placeholder: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms' },
            { name: 'permission_id', type: 'string', label: 'Permission ID', required: true, placeholder: 'Permission ID to update' },
            {
                name: 'share_role',
                type: 'select',
                label: 'New Permission Level',
                required: true,
                options: [
                    { value: 'reader', label: 'Reader' },
                    { value: 'commenter', label: 'Commenter' },
                    { value: 'writer', label: 'Writer' },
                    { value: 'owner', label: 'Owner' }
                ]
            }
        ]
    }
};

export const GoogleDriveConnectorModal: React.FC<GoogleDriveConnectorModalProps> = ({
    isOpen,
    onClose,
    onSave,
    initialData
}) => {
    const { session } = useAuth();
    const [config, setConfig] = useState<GoogleDriveConfig>({
        name: 'google_drive',
        display_name: 'Google Drive',
        description: 'Upload, download, and manage files in Google Drive',
        auth_type: 'oauth',
        auth_config: {
            scopes: [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
        },
        settings: {
            action: 'list_files'
        },
        status: 'needs_auth'
    });

    const [selectedAction, setSelectedAction] = useState<string>('list_files');
    const [isLoading, setIsLoading] = useState(false);
    const [isTesting, setIsTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [activeTab, setActiveTab] = useState('action');
    const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});

    const currentActionConfig = GOOGLE_DRIVE_ACTIONS[selectedAction as keyof typeof GOOGLE_DRIVE_ACTIONS];

    useEffect(() => {
        // Reset parameters when action changes
        setConfig(prev => ({
            ...prev,
            settings: {
                action: selectedAction,
                // Keep only relevant parameters for the new action
                ...Object.fromEntries(
                    Object.entries(prev.settings).filter(([key]) =>
                        key === 'action' || currentActionConfig?.parameters.some(p => p.name === key)
                    )
                )
            }
        }));
        setValidationErrors({});
    }, [selectedAction, currentActionConfig]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Google Drive Modal: Received AI-generated parameters:', initialData);
            
            // Update config with AI-generated parameters
            setConfig(prev => ({
                ...prev,
                settings: {
                    ...prev.settings,
                    ...initialData
                }
            }));

            // Set the action if provided in initialData
            if (initialData.action) {
                setSelectedAction(initialData.action);
            }
        }
    }, [initialData]);

    const handleParameterChange = (paramName: string, value: any) => {
        setConfig(prev => ({
            ...prev,
            settings: {
                ...prev.settings,
                [paramName]: value
            }
        }));

        // Clear validation error for this field
        if (validationErrors[paramName]) {
            setValidationErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors[paramName];
                return newErrors;
            });
        }
    };

    const validateParameters = (): boolean => {
        const errors: { [key: string]: string } = {};

        if (!currentActionConfig) return false;

        // Check required parameters
        currentActionConfig.requiredParams.forEach(paramName => {
            const value = config.settings[paramName];
            if (!value || (typeof value === 'string' && value.trim() === '')) {
                errors[paramName] = 'This field is required';
            }
        });

        // Conditional validation for share action
        if (selectedAction === 'share') {
            const shareType = config.settings.share_type;
            if (shareType === 'user' || shareType === 'group') {
                if (!config.settings.share_email) {
                    errors.share_email = 'Email is required for user/group sharing';
                }
            } else if (shareType === 'domain') {
                if (!config.settings.share_domain) {
                    errors.share_domain = 'Domain is required for domain sharing';
                }
            }
        }

        setValidationErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleOAuthSetup = async () => {
        setIsLoading(true);

        try {
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
                    setTimeout(() => {
                        localStorage.removeItem('oauth_state');
                        localStorage.removeItem('oauth_connector');
                        // Update config status
                        setConfig(prev => ({ ...prev, status: 'configured' }));
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
        if (!validateParameters()) {
            setTestResult({ success: false, message: 'Please fix validation errors before testing' });
            return;
        }

        setIsTesting(true);
        setTestResult(null);

        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/connectors/google_drive/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({
                    parameters: config.settings,
                    auth_config: config.auth_config
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
        if (!validateParameters()) {
            setActiveTab('action');
            return;
        }

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

    const renderParameterField = (param: any) => {
        const value = config.settings[param.name] || param.default || '';
        const hasError = validationErrors[param.name];

        return (
            <div key={param.name} className="space-y-2">
                <Label htmlFor={param.name} className={hasError ? 'text-red-600' : ''}>
                    {param.label}
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                </Label>

                {param.type === 'select' ? (
                    <Select value={value} onValueChange={(val) => handleParameterChange(param.name, val)}>
                        <SelectTrigger className={hasError ? 'border-red-500' : ''}>
                            <SelectValue placeholder={`Select ${param.label.toLowerCase()}`} />
                        </SelectTrigger>
                        <SelectContent>
                            {param.options?.map((option: any) => (
                                <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                ) : param.type === 'textarea' ? (
                    <Textarea
                        id={param.name}
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.placeholder}
                        rows={4}
                        className={hasError ? 'border-red-500' : ''}
                    />
                ) : param.type === 'boolean' ? (
                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            id={param.name}
                            checked={value || false}
                            onChange={(e) => handleParameterChange(param.name, e.target.checked)}
                            className="rounded border-gray-300"
                        />
                        <span className="text-sm text-muted-foreground">
                            {value ? 'Enabled' : 'Disabled'}
                        </span>
                    </div>
                ) : param.type === 'number' ? (
                    <Input
                        id={param.name}
                        type="number"
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, parseInt(e.target.value) || 0)}
                        placeholder={param.placeholder}
                        min={param.min}
                        max={param.max}
                        className={hasError ? 'border-red-500' : ''}
                    />
                ) : (
                    <Input
                        id={param.name}
                        type={param.type === 'email' ? 'email' : 'text'}
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.placeholder}
                        className={hasError ? 'border-red-500' : ''}
                    />
                )}

                {hasError && (
                    <p className="text-sm text-red-600">{hasError}</p>
                )}
            </div>
        );
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <HardDrive className="h-5 w-5 text-blue-600" />
                        Configure Google Drive
                    </DialogTitle>
                    <DialogDescription>
                        Upload, download, and manage files and folders in Google Drive
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="action">Action & Parameters</TabsTrigger>
                        <TabsTrigger value="authentication">Authentication</TabsTrigger>
                        <TabsTrigger value="test">Test & Validate</TabsTrigger>
                    </TabsList>

                    <TabsContent value="action" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Select Action</CardTitle>
                                <CardDescription>
                                    Choose what you want to do with Google Drive
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                    {Object.entries(GOOGLE_DRIVE_ACTIONS).map(([actionKey, actionConfig]) => {
                                        const IconComponent = actionConfig.icon;
                                        const isSelected = selectedAction === actionKey;

                                        return (
                                            <button
                                                key={actionKey}
                                                onClick={() => setSelectedAction(actionKey)}
                                                className={`p-3 rounded-lg border-2 transition-all text-left ${isSelected
                                                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                                                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-2 mb-1">
                                                    <IconComponent className="h-4 w-4" />
                                                    <span className="font-medium text-sm">{actionConfig.label}</span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    {actionConfig.description}
                                                </p>
                                            </button>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>

                        {currentActionConfig && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <currentActionConfig.icon className="h-4 w-4" />
                                        {currentActionConfig.label} Parameters
                                    </CardTitle>
                                    <CardDescription>
                                        {currentActionConfig.description}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {currentActionConfig.parameters.map(renderParameterField)}

                                    {currentActionConfig.requiredParams.length > 0 && (
                                        <Alert>
                                            <Info className="h-4 w-4" />
                                            <AlertDescription>
                                                Required fields: {currentActionConfig.requiredParams.join(', ')}
                                            </AlertDescription>
                                        </Alert>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    <TabsContent value="authentication" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Key className="h-4 w-4" />
                                    OAuth Authentication
                                </CardTitle>
                                <CardDescription>
                                    Google Drive requires OAuth 2.0 authentication
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="default">OAuth 2.0</Badge>
                                        <Badge variant={config.status === 'configured' ? 'default' : 'destructive'}>
                                            {config.status === 'configured' ? 'Configured' : 'Needs Setup'}
                                        </Badge>
                                    </div>

                                    <Alert>
                                        <Info className="h-4 w-4" />
                                        <AlertDescription>
                                            OAuth authentication allows secure access to your Google Drive without storing passwords.
                                            Click the button below to authorize this application.
                                        </AlertDescription>
                                    </Alert>

                                    <Button onClick={handleOAuthSetup} className="w-full" disabled={isLoading}>
                                        {isLoading ? 'Setting up OAuth...' : 'Setup Google Drive Authorization'}
                                    </Button>

                                    <div className="space-y-2">
                                        <Label>Required Permissions</Label>
                                        <div className="space-y-1">
                                            {config.auth_config.scopes.map((scope, index) => (
                                                <Badge key={index} variant="outline" className="mr-2 mb-1">
                                                    {scope.replace('https://www.googleapis.com/auth/', '')}
                                                </Badge>
                                            ))}
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            These permissions allow the connector to read, write, and manage your Google Drive files.
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="test" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <TestTube className="h-4 w-4" />
                                    Test Configuration
                                </CardTitle>
                                <CardDescription>
                                    Test your Google Drive connector configuration
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Current Action</Label>
                                    <div className="flex items-center gap-2">
                                        <currentActionConfig.icon className="h-4 w-4" />
                                        <span className="font-medium">{currentActionConfig.label}</span>
                                    </div>
                                </div>

                                <Separator />

                                <Button
                                    onClick={handleTestConnection}
                                    disabled={isTesting || config.status !== 'configured'}
                                    className="w-full"
                                >
                                    {isTesting ? 'Testing...' : 'Test Connection & Parameters'}
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

                                {Object.keys(validationErrors).length > 0 && (
                                    <Alert className="border-red-200 bg-red-50">
                                        <AlertTriangle className="h-4 w-4 text-red-600" />
                                        <AlertDescription className="text-red-800">
                                            Please fix the following validation errors:
                                            <ul className="list-disc list-inside mt-2">
                                                {Object.entries(validationErrors).map(([field, error]) => (
                                                    <li key={field} className="text-sm">
                                                        <strong>{field}:</strong> {error}
                                                    </li>
                                                ))}
                                            </ul>
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>

                <div className="flex justify-end gap-3 pt-4 border-t">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isLoading || config.status !== 'configured'}
                    >
                        <Save className="h-4 w-4 mr-2" />
                        {isLoading ? 'Saving...' : 'Save Configuration'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
};