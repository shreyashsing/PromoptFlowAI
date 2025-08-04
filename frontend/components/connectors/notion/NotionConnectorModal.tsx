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
import { Switch } from '@/components/ui/switch';
import {
    Save,
    TestTube,
    CheckCircle,
    XCircle,
    AlertTriangle,
    Key,
    Settings,
    Info,
    FileText,
    Database,
    Users,
    Blocks,
    Plus,
    Search,
    Edit,
    Archive,
    Eye,
    List,
    Filter,
    Hash,
    Calendar,
    User,
    Folder,
    Link,
    Type,
    AlignLeft,
    CheckSquare,
    Code,
    Quote,
    Heading1,
    Heading2,
    Heading3,
    ListOrdered,
    ListTodo,
    ExternalLink
} from 'lucide-react';

interface NotionConfig {
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
    status: 'configured' | 'needs_auth' | 'error';
}

interface NotionConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: NotionConfig) => Promise<void>;
    initialData?: any; // AI-generated parameters
}

// Notion resource definitions with their operations
const NOTION_RESOURCES = {
    page: {
        label: 'Page',
        icon: FileText,
        description: 'Create, read, search, and archive Notion pages',
        operations: [
            { value: 'create_page', label: 'Create Page', icon: Plus },
            { value: 'get_page', label: 'Get Page', icon: Eye },
            { value: 'search_pages', label: 'Search Pages', icon: Search },
            { value: 'archive_page', label: 'Archive Page', icon: Archive }
        ]
    },
    database: {
        label: 'Database',
        icon: Database,
        description: 'Get and search Notion databases',
        operations: [
            { value: 'get_database', label: 'Get Database', icon: Eye },
            { value: 'get_all_databases', label: 'Get All Databases', icon: List },
            { value: 'search_databases', label: 'Search Databases', icon: Search }
        ]
    },
    database_page: {
        label: 'Database Page',
        icon: FileText,
        description: 'Manage pages within databases',
        operations: [
            { value: 'create_database_page', label: 'Create Database Page', icon: Plus },
            { value: 'get_database_page', label: 'Get Database Page', icon: Eye },
            { value: 'get_all_database_pages', label: 'Get All Database Pages', icon: List },
            { value: 'update_database_page', label: 'Update Database Page', icon: Edit }
        ]
    },
    block: {
        label: 'Block',
        icon: Blocks,
        description: 'Manage content blocks within pages',
        operations: [
            { value: 'append_block', label: 'Append Block', icon: Plus },
            { value: 'get_block_children', label: 'Get Block Children', icon: List }
        ]
    },
    user: {
        label: 'User',
        icon: Users,
        description: 'Get user information',
        operations: [
            { value: 'get_user', label: 'Get User', icon: User },
            { value: 'get_all_users', label: 'Get All Users', icon: Users }
        ]
    }
};

// Block types for content creation
const BLOCK_TYPES = [
    { value: 'paragraph', label: 'Paragraph', icon: AlignLeft },
    { value: 'heading_1', label: 'Heading 1', icon: Heading1 },
    { value: 'heading_2', label: 'Heading 2', icon: Heading2 },
    { value: 'heading_3', label: 'Heading 3', icon: Heading3 },
    { value: 'bulleted_list_item', label: 'Bullet List', icon: List },
    { value: 'numbered_list_item', label: 'Numbered List', icon: ListOrdered },
    { value: 'to_do', label: 'To-Do', icon: ListTodo },
    { value: 'toggle', label: 'Toggle', icon: CheckSquare },
    { value: 'code', label: 'Code', icon: Code },
    { value: 'quote', label: 'Quote', icon: Quote }
];

// Parameter interface
interface OperationParameter {
    name: string;
    type: 'string' | 'textarea' | 'select' | 'boolean' | 'number' | 'array';
    label: string;
    required?: boolean;
    placeholder?: string;
    options?: { value: string; label: string }[];
}

// Parameter definitions for each operation
const OPERATION_PARAMETERS: Record<string, OperationParameter[]> = {
    // Page operations
    create_page: [
        { name: 'title', type: 'string', label: 'Page Title', required: true, placeholder: 'My New Page' },
        { name: 'parent_page_id', type: 'string', label: 'Parent Page ID', placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'parent_database_id', type: 'string', label: 'Parent Database ID', placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'blocks', type: 'array', label: 'Page Blocks', placeholder: 'Structured content blocks' },
        { name: 'content', type: 'textarea', label: 'Content', placeholder: 'Enter your content here...\n\nUse double line breaks for new paragraphs.' },
        { name: 'icon_type', type: 'select', label: 'Icon Type', options: [{ value: 'emoji', label: 'Emoji' }, { value: 'external', label: 'External URL' }] },
        { name: 'icon_value', type: 'string', label: 'Icon Value', placeholder: '📝 or https://example.com/icon.png' }
    ],
    get_page: [
        { name: 'page_id', type: 'string', label: 'Page ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' }
    ],
    search_pages: [
        { name: 'query', type: 'string', label: 'Search Query', placeholder: 'Search terms...' }
    ],
    archive_page: [
        { name: 'page_id', type: 'string', label: 'Page ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' }
    ],

    // Database operations
    get_database: [
        { name: 'database_id', type: 'string', label: 'Database ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' }
    ],
    get_all_databases: [],
    search_databases: [
        { name: 'query', type: 'string', label: 'Search Query', placeholder: 'Search terms...' }
    ],

    // Database page operations
    create_database_page: [
        { name: 'database_id', type: 'string', label: 'Database ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'title', type: 'string', label: 'Page Title', placeholder: 'New Database Page' },
        { name: 'content', type: 'textarea', label: 'Content', placeholder: 'Enter your content here...' },
        { name: 'properties', type: 'textarea', label: 'Properties (JSON)', placeholder: '{"Status": {"name": "In Progress"}, "Priority": {"name": "High"}}' }
    ],
    get_database_page: [
        { name: 'page_id', type: 'string', label: 'Page ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' }
    ],
    get_all_database_pages: [
        { name: 'database_id', type: 'string', label: 'Database ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'filter', type: 'textarea', label: 'Filter (JSON)', placeholder: '{"property": "Status", "select": {"equals": "In Progress"}}' },
        { name: 'sorts', type: 'textarea', label: 'Sorts (JSON)', placeholder: '[{"property": "Created", "direction": "descending"}]' }
    ],
    update_database_page: [
        { name: 'page_id', type: 'string', label: 'Page ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'properties', type: 'textarea', label: 'Properties (JSON)', placeholder: '{"Status": {"name": "Completed"}}' }
    ],

    // Block operations
    append_block: [
        { name: 'block_id', type: 'string', label: 'Block/Page ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' },
        { name: 'content', type: 'textarea', label: 'Content', placeholder: 'Enter content to add...\n\nUse double line breaks for new paragraphs.' }
    ],
    get_block_children: [
        { name: 'block_id', type: 'string', label: 'Block ID', required: true, placeholder: '12345678-1234-1234-1234-123456789012' }
    ],

    // User operations
    get_user: [
        { name: 'user_id', type: 'string', label: 'User ID', required: true, placeholder: 'user-id-here' }
    ],
    get_all_users: []
};

export function NotionConnectorModal({ isOpen, onClose, onSave, initialData }: NotionConnectorModalProps) {
    const { user, session } = useAuth();
    const [config, setConfig] = useState<NotionConfig>({
        name: 'notion',
        display_name: 'Notion',
        description: 'Interact with Notion workspaces, databases, pages, and blocks',
        auth_type: 'api_key',
        auth_config: {},
        settings: {
            resource: 'page',
            operation: 'get_page',
            simple_output: false,
            return_all: false,
            page_size: 100,
            include_nested_blocks: false
        },
        status: 'needs_auth'
    });

    const [selectedResource, setSelectedResource] = useState<string>('page');
    const [selectedOperation, setSelectedOperation] = useState<string>('get_page');
    const [parameters, setParameters] = useState<{ [key: string]: any }>({});
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});

    // Update operation when resource changes
    useEffect(() => {
        const resource = NOTION_RESOURCES[selectedResource as keyof typeof NOTION_RESOURCES];
        if (resource && resource.operations.length > 0) {
            setSelectedOperation(resource.operations[0].value);
        }
    }, [selectedResource]);

    // Clear parameters when operation changes
    useEffect(() => {
        setParameters({});
        setValidationErrors({});
    }, [selectedOperation]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Notion Modal: Received AI-generated parameters:', initialData);

            // Update parameters with AI-generated data
            setParameters(prev => ({
                ...prev,
                ...initialData
            }));

            // Set the resource if provided in initialData
            if (initialData.resource) {
                setSelectedResource(initialData.resource);
            }

            // Set the operation if provided in initialData
            if (initialData.operation) {
                setSelectedOperation(initialData.operation);
            }
        }
    }, [initialData]);

    const validateParameters = () => {
        const errors: { [key: string]: string } = {};
        const operationParams: OperationParameter[] = OPERATION_PARAMETERS[selectedOperation] || [];

        operationParams.forEach(param => {
            if (param.required === true && !parameters[param.name]) {
                errors[param.name] = `${param.label} is required`;
            }

            // Validate Notion ID format
            if (param.name.includes('_id') && parameters[param.name]) {
                const id = parameters[param.name];
                const cleanId = id.replace(/-/g, '');
                if (cleanId.length !== 32 || !/^[a-f0-9]{32}$/i.test(cleanId)) {
                    errors[param.name] = 'Invalid Notion ID format (should be 32-character UUID)';
                }
            }

            // Validate JSON parameters
            if (param.name === 'properties' || param.name === 'filter' || param.name === 'sorts') {
                if (parameters[param.name]) {
                    try {
                        JSON.parse(parameters[param.name]);
                    } catch (e) {
                        errors[param.name] = 'Invalid JSON format';
                    }
                }
            }
        });

        setValidationErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleParameterChange = (name: string, value: any) => {
        setParameters(prev => ({ ...prev, [name]: value }));

        // Clear validation error for this field
        if (validationErrors[name]) {
            setValidationErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors[name];
                return newErrors;
            });
        }
    };

    const handleTestConnection = async () => {
        if (!config.auth_config.api_key) {
            setTestResult({ success: false, message: 'Please enter your Notion integration token' });
            return;
        }

        setIsLoading(true);
        setTestResult(null);

        try {
            // Test with a simple operation
            const testParams = {
                resource: 'user',
                operation: 'get_all_users',
                page_size: 1
            };

            const response = await fetch('/api/connectors/notion/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({
                    auth_config: config.auth_config,
                    parameters: testParams
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                setTestResult({ success: true, message: 'Connection successful! Notion integration is working.' });
                setConfig(prev => ({ ...prev, status: 'configured' }));
            } else {
                setTestResult({ success: false, message: result.error || 'Connection failed' });
                setConfig(prev => ({ ...prev, status: 'error' }));
            }
        } catch (error) {
            setTestResult({ success: false, message: 'Failed to test connection' });
            setConfig(prev => ({ ...prev, status: 'error' }));
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        if (!validateParameters()) {
            return;
        }

        setIsLoading(true);
        try {
            const finalConfig = {
                ...config,
                settings: {
                    ...config.settings,
                    resource: selectedResource,
                    operation: selectedOperation,
                    ...parameters
                }
            };

            await onSave(finalConfig);
            onClose();
        } catch (error) {
            console.error('Failed to save configuration:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const renderParameterField = (param: OperationParameter) => {
        const value = parameters[param.name] || '';
        const hasError = validationErrors[param.name];

        // Special handling for AI-generated blocks array
        if (param.name === 'blocks' && Array.isArray(parameters.blocks)) {
            return (
                <div key={param.name} className="space-y-2">
                    <Label>
                        Page Blocks (AI Generated)
                        <span className="text-green-500 ml-1">✓</span>
                    </Label>
                    <div className="bg-gray-50 border rounded-lg p-4 max-h-60 overflow-y-auto">
                        <div className="space-y-2">
                            {parameters.blocks.map((block: any, index: number) => (
                                <div key={index} className="bg-white border rounded p-3 text-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Badge variant="outline" className="text-xs">
                                            {block.type?.replace('_', ' ') || 'block'}
                                        </Badge>
                                        <span className="text-gray-500">#{index + 1}</span>
                                    </div>
                                    <div className="text-gray-700 font-mono text-xs bg-gray-50 p-2 rounded">
                                        {block.content || JSON.stringify(block, null, 2)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <p className="text-xs text-gray-500">
                        {parameters.blocks.length} blocks generated by AI
                    </p>
                </div>
            );
        }

        // Special handling for title when it's pre-filled by AI
        if (param.name === 'title' && parameters.title) {
            return (
                <div key={param.name} className="space-y-2">
                    <Label htmlFor={param.name}>
                        {param.label}
                        {param.required === true && <span className="text-red-500 ml-1">*</span>}
                        <span className="text-green-500 ml-1">✓ AI Generated</span>
                    </Label>
                    <Input
                        id={param.name}
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.placeholder}
                        className={`${hasError ? 'border-red-500' : 'border-green-500'} bg-green-50`}
                    />
                    {hasError && <p className="text-sm text-red-500">{hasError}</p>}
                </div>
            );
        }

        switch (param.type) {
            case 'select':
                return (
                    <div key={param.name} className="space-y-2">
                        <Label htmlFor={param.name}>
                            {param.label}
                            {param.required === true && <span className="text-red-500 ml-1">*</span>}
                        </Label>
                        <Select value={value} onValueChange={(val) => handleParameterChange(param.name, val)}>
                            <SelectTrigger className={hasError ? 'border-red-500' : ''}>
                                <SelectValue placeholder={`Select ${param.label}`} />
                            </SelectTrigger>
                            <SelectContent>
                                {param.options?.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        {option.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {hasError && <p className="text-sm text-red-500">{hasError}</p>}
                    </div>
                );

            case 'textarea':
                return (
                    <div key={param.name} className="space-y-2">
                        <Label htmlFor={param.name}>
                            {param.label}
                            {param.required === true && <span className="text-red-500 ml-1">*</span>}
                        </Label>
                        <Textarea
                            id={param.name}
                            value={value}
                            onChange={(e) => handleParameterChange(param.name, e.target.value)}
                            placeholder={param.placeholder}
                            className={hasError ? 'border-red-500' : ''}
                            rows={4}
                        />
                        {hasError && <p className="text-sm text-red-500">{hasError}</p>}
                    </div>
                );

            case 'boolean':
                return (
                    <div key={param.name} className="flex items-center space-x-2">
                        <Switch
                            id={param.name}
                            checked={value}
                            onCheckedChange={(checked) => handleParameterChange(param.name, checked)}
                        />
                        <Label htmlFor={param.name}>{param.label}</Label>
                    </div>
                );

            default:
                return (
                    <div key={param.name} className="space-y-2">
                        <Label htmlFor={param.name}>
                            {param.label}
                            {param.required === true && <span className="text-red-500 ml-1">*</span>}
                        </Label>
                        <Input
                            id={param.name}
                            type={param.type === 'number' ? 'number' : 'text'}
                            value={value}
                            onChange={(e) => handleParameterChange(param.name, e.target.value)}
                            placeholder={param.placeholder}
                            className={hasError ? 'border-red-500' : ''}
                        />
                        {hasError && <p className="text-sm text-red-500">{hasError}</p>}
                    </div>
                );
        }
    };

    const currentResource = NOTION_RESOURCES[selectedResource as keyof typeof NOTION_RESOURCES];
    const operationParams: OperationParameter[] = OPERATION_PARAMETERS[selectedOperation] || [];

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
                            <span className="text-white text-sm font-bold">N</span>
                        </div>
                        Configure Notion Connector
                    </DialogTitle>
                    <DialogDescription>
                        Connect to your Notion workspace to manage pages, databases, and content blocks.
                    </DialogDescription>
                </DialogHeader>

                {/* AI-Generated Parameters Indicator */}
                {initialData && Object.keys(initialData).length > 0 && (
                    <Alert className="border-green-200 bg-green-50">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                            <strong>AI-Generated Configuration Detected!</strong>
                            {initialData.title && ` Title: "${initialData.title}"`}
                            {initialData.blocks && ` • ${initialData.blocks.length} content blocks`}
                            {initialData.operation && ` • Operation: ${initialData.operation}`}
                        </AlertDescription>
                    </Alert>
                )}

                <Tabs defaultValue="configuration" className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="configuration" className="flex items-center gap-2">
                            <Settings className="w-4 h-4" />
                            Configuration
                        </TabsTrigger>
                        <TabsTrigger value="authentication" className="flex items-center gap-2">
                            <Key className="w-4 h-4" />
                            Authentication
                        </TabsTrigger>
                        <TabsTrigger value="advanced" className="flex items-center gap-2">
                            <Info className="w-4 h-4" />
                            Advanced
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="configuration" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Database className="w-5 h-5" />
                                    Resource & Operation
                                </CardTitle>
                                <CardDescription>
                                    Select the Notion resource and operation you want to perform.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Resource</Label>
                                        <Select value={selectedResource} onValueChange={setSelectedResource}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {Object.entries(NOTION_RESOURCES).map(([key, resource]) => {
                                                    const Icon = resource.icon;
                                                    return (
                                                        <SelectItem key={key} value={key}>
                                                            <div className="flex items-center gap-2">
                                                                <Icon className="w-4 h-4" />
                                                                {resource.label}
                                                            </div>
                                                        </SelectItem>
                                                    );
                                                })}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="space-y-2">
                                        <Label>Operation</Label>
                                        <Select value={selectedOperation} onValueChange={setSelectedOperation}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {currentResource?.operations.map((op) => {
                                                    const Icon = op.icon;
                                                    return (
                                                        <SelectItem key={op.value} value={op.value}>
                                                            <div className="flex items-center gap-2">
                                                                <Icon className="w-4 h-4" />
                                                                {op.label}
                                                            </div>
                                                        </SelectItem>
                                                    );
                                                })}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                {currentResource && (
                                    <Alert>
                                        <Info className="w-4 h-4" />
                                        <AlertDescription>
                                            {currentResource.description}
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>

                        {operationParams.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Parameters</CardTitle>
                                    <CardDescription>
                                        Configure the parameters for the selected operation.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {operationParams.map(renderParameterField)}
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    <TabsContent value="authentication" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Key className="w-5 h-5" />
                                    Notion Integration Token
                                </CardTitle>
                                <CardDescription>
                                    Enter your Notion integration token to authenticate with the Notion API.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="api_key">Integration Token</Label>
                                    <Input
                                        id="api_key"
                                        type="password"
                                        value={config.auth_config.api_key || ''}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            auth_config: { ...prev.auth_config, api_key: e.target.value }
                                        }))}
                                        placeholder="secret_..."
                                    />
                                </div>

                                <Alert>
                                    <ExternalLink className="w-4 h-4" />
                                    <AlertDescription>
                                        <div className="space-y-2">
                                            <p>To get your integration token:</p>
                                            <ol className="list-decimal list-inside space-y-1 text-sm">
                                                <li>Go to <a href="https://www.notion.so/my-integrations" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Notion Integrations</a></li>
                                                <li>Create a new integration or select an existing one</li>
                                                <li>Copy the integration token (starts with "secret_")</li>
                                                <li>Make sure to add the integration to your Notion pages/databases</li>
                                            </ol>
                                        </div>
                                    </AlertDescription>
                                </Alert>

                                <div className="flex gap-2">
                                    <Button
                                        onClick={handleTestConnection}
                                        disabled={isLoading || !config.auth_config.api_key}
                                        variant="outline"
                                        className="flex items-center gap-2"
                                    >
                                        <TestTube className="w-4 h-4" />
                                        {isLoading ? 'Testing...' : 'Test Connection'}
                                    </Button>
                                </div>

                                {testResult && (
                                    <Alert className={testResult.success ? 'border-green-500' : 'border-red-500'}>
                                        {testResult.success ? (
                                            <CheckCircle className="w-4 h-4 text-green-600" />
                                        ) : (
                                            <XCircle className="w-4 h-4 text-red-600" />
                                        )}
                                        <AlertDescription className={testResult.success ? 'text-green-700' : 'text-red-700'}>
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
                                <CardTitle>Advanced Settings</CardTitle>
                                <CardDescription>
                                    Configure advanced options for the Notion connector.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="flex items-center space-x-2">
                                        <Switch
                                            id="simple_output"
                                            checked={config.settings.simple_output}
                                            onCheckedChange={(checked) => setConfig(prev => ({
                                                ...prev,
                                                settings: { ...prev.settings, simple_output: checked }
                                            }))}
                                        />
                                        <Label htmlFor="simple_output">Simple Output</Label>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        <Switch
                                            id="return_all"
                                            checked={config.settings.return_all}
                                            onCheckedChange={(checked) => setConfig(prev => ({
                                                ...prev,
                                                settings: { ...prev.settings, return_all: checked }
                                            }))}
                                        />
                                        <Label htmlFor="return_all">Return All Results</Label>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        <Switch
                                            id="include_nested_blocks"
                                            checked={config.settings.include_nested_blocks}
                                            onCheckedChange={(checked) => setConfig(prev => ({
                                                ...prev,
                                                settings: { ...prev.settings, include_nested_blocks: checked }
                                            }))}
                                        />
                                        <Label htmlFor="include_nested_blocks">Include Nested Blocks</Label>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="page_size">Page Size (1-100)</Label>
                                    <Input
                                        id="page_size"
                                        type="number"
                                        min="1"
                                        max="100"
                                        value={config.settings.page_size}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            settings: { ...prev.settings, page_size: parseInt(e.target.value) || 100 }
                                        }))}
                                    />
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Block Types Reference</CardTitle>
                                <CardDescription>
                                    Available block types for content creation.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 gap-2">
                                    {BLOCK_TYPES.map((blockType) => {
                                        const Icon = blockType.icon;
                                        return (
                                            <div key={blockType.value} className="flex items-center gap-2 p-2 rounded border">
                                                <Icon className="w-4 h-4" />
                                                <span className="text-sm">{blockType.label}</span>
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>

                <div className="flex justify-end gap-2 pt-4 border-t">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isLoading || !config.auth_config.api_key}
                        className="flex items-center gap-2"
                    >
                        <Save className="w-4 h-4" />
                        {isLoading ? 'Saving...' : 'Save Configuration'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}