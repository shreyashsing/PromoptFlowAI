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
    Mail,
    Send,
    Reply,
    Inbox,
    Search,
    FileText,
    Tag,
    Archive,
    MessageSquare,
    Users,
    Paperclip,
    Eye,
    Edit,
    Trash2,
    Plus,
    Filter,
    Clock,
    Star,
    Flag,
    Loader2
} from 'lucide-react';

interface GmailConfig {
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
}

interface GmailConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: any) => void;
    initialConfig?: Partial<GmailConfig>;
    initialData?: any; // AI-generated parameters
    mode?: 'create' | 'edit';
}

const gmailActions = [
    // Message Operations
    { value: 'send', label: 'Send Email', icon: Send, category: 'Messages' },
    { value: 'reply', label: 'Reply to Email', icon: Reply, category: 'Messages' },
    { value: 'read', label: 'Read Message', icon: Eye, category: 'Messages' },
    { value: 'search', label: 'Search Messages', icon: Search, category: 'Messages' },
    { value: 'list', label: 'List Messages', icon: Inbox, category: 'Messages' },
    { value: 'delete', label: 'Delete Message', icon: Trash2, category: 'Messages' },
    { value: 'mark_as_read', label: 'Mark as Read', icon: CheckCircle, category: 'Messages' },
    { value: 'mark_as_unread', label: 'Mark as Unread', icon: XCircle, category: 'Messages' },
    { value: 'add_labels', label: 'Add Labels', icon: Plus, category: 'Messages' },
    { value: 'remove_labels', label: 'Remove Labels', icon: Trash2, category: 'Messages' },
    
    // Draft Operations
    { value: 'create_draft', label: 'Create Draft', icon: FileText, category: 'Drafts' },
    { value: 'get_draft', label: 'Get Draft', icon: Eye, category: 'Drafts' },
    { value: 'delete_draft', label: 'Delete Draft', icon: Trash2, category: 'Drafts' },
    { value: 'list_drafts', label: 'List Drafts', icon: FileText, category: 'Drafts' },
    
    // Label Operations
    { value: 'get_labels', label: 'Get Labels', icon: Tag, category: 'Labels' },
    { value: 'create_label', label: 'Create Label', icon: Plus, category: 'Labels' },
    { value: 'delete_label', label: 'Delete Label', icon: Trash2, category: 'Labels' },
    { value: 'get_label', label: 'Get Label', icon: Eye, category: 'Labels' },
    
    // Thread Operations
    { value: 'get_thread', label: 'Get Thread', icon: MessageSquare, category: 'Threads' },
    { value: 'list_threads', label: 'List Threads', icon: MessageSquare, category: 'Threads' },
    { value: 'delete_thread', label: 'Delete Thread', icon: Trash2, category: 'Threads' },
    { value: 'trash_thread', label: 'Trash Thread', icon: Archive, category: 'Threads' },
    { value: 'untrash_thread', label: 'Untrash Thread', icon: Archive, category: 'Threads' },
    { value: 'add_thread_labels', label: 'Add Thread Labels', icon: Plus, category: 'Threads' },
    { value: 'remove_thread_labels', label: 'Remove Thread Labels', icon: Trash2, category: 'Threads' }
];

const labelColors = [
    { value: 'red', label: 'Red', color: 'bg-red-500' },
    { value: 'orange', label: 'Orange', color: 'bg-orange-500' },
    { value: 'yellow', label: 'Yellow', color: 'bg-yellow-500' },
    { value: 'green', label: 'Green', color: 'bg-green-500' },
    { value: 'teal', label: 'Teal', color: 'bg-teal-500' },
    { value: 'blue', label: 'Blue', color: 'bg-blue-500' },
    { value: 'purple', label: 'Purple', color: 'bg-purple-500' },
    { value: 'pink', label: 'Pink', color: 'bg-pink-500' },
    { value: 'brown', label: 'Brown', color: 'bg-amber-700' },
    { value: 'gray', label: 'Gray', color: 'bg-gray-500' }
];

const GmailConnectorModal: React.FC<GmailConnectorModalProps> = ({
    isOpen,
    onClose,
    onSave,
    initialConfig,
    initialData,
    mode = 'create'
}) => {
    const { user, session } = useAuth();
    const [activeTab, setActiveTab] = useState('action');
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [authStatus, setAuthStatus] = useState<'none' | 'authenticated' | 'error'>('none');

    // Function to check authentication status
    const checkAuthStatus = async () => {
        if (!session?.access_token) {
            console.log('🔐 Gmail Modal: No session token available');
            return;
        }
        
        console.log('🔐 Gmail Modal: Checking authentication status...');
        
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
                console.log('🔐 Gmail Modal: Auth tokens response:', data);
                
                const gmailToken = data.tokens?.find((token: any) => {
                    console.log('🔐 Gmail Modal: Checking token:', token);
                    return token.connector_name === 'gmail_connector' && 
                           token.token_type === 'oauth2';
                });

                if (gmailToken) {
                    console.log('🔐 Gmail Modal: Found valid Gmail token, setting authenticated');
                    setAuthStatus('authenticated');
                    // Note: token_data is not available in list response (it's encrypted)
                    // We just need to know the token exists for UI status
                } else {
                    console.log('🔐 Gmail Modal: No valid Gmail token found');
                    setAuthStatus('none');
                }
            } else {
                console.error('🔐 Gmail Modal: Failed to check auth status:', response.status);
                setAuthStatus('none');
            }
        } catch (error) {
            console.error('🔐 Gmail Modal: Error checking auth status:', error);
            setAuthStatus('none');
        }
    };

    // Gmail Configuration State
    const [config, setConfig] = useState<GmailConfig>({
        name: 'gmail_connector',
        display_name: 'Gmail Connector',
        description: 'Gmail email operations connector',
        auth_type: 'oauth',
        auth_config: {
            scopes: [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels'
            ]
        },
        settings: {}
    });

    // Action Configuration State
    const [actionConfig, setActionConfig] = useState({
        action: 'send',
        // Message operations
        to: '',
        cc: '',
        bcc: '',
        subject: '',
        body: '',
        html_body: '',
        reply_to: '',
        sender_name: '',
        message_id: '',
        thread_id: '',
        // Search/List operations
        query: '',
        max_results: 10,
        include_spam_trash: false,
        // Label operations
        label_ids: [] as string[],
        label_name: '',
        label_color: '',
        // Draft operations
        draft_id: '',
        // Advanced options
        format: 'full',
        simple: false,
        return_all: false,
        limit: 10,
        // Attachments
        attachments: [] as Array<{ filename: string, content: string, mime_type: string }>
    });



    useEffect(() => {
        if (initialConfig) {
            setConfig(prev => ({ ...prev, ...initialConfig }));
            if (initialConfig.auth_config?.access_token) {
                setAuthStatus('authenticated');
            }
        }
    }, [initialConfig]);

    // Check authentication status when modal opens
    useEffect(() => {
        if (!isOpen) return;
        
        console.log('🔐 Gmail Modal: Modal opened, checking auth status');
        
        // Clean up any leftover OAuth data
        localStorage.removeItem('oauth_state');
        localStorage.removeItem('oauth_connector');
        localStorage.removeItem('oauth_tokens');
        
        checkAuthStatus();
    }, [isOpen, session?.access_token]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        console.log('🤖 Gmail Modal: useEffect triggered with initialData:', initialData);
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 Gmail Modal: Received AI-generated parameters:', initialData);
            
            // Update actionConfig with AI-generated parameters
            setActionConfig(prev => {
                const newConfig = {
                    ...prev,
                    ...initialData
                };
                console.log('🤖 Gmail Modal: Updated actionConfig:', newConfig);
                return newConfig;
            });

            // Set the action if provided in initialData
            if (initialData.action) {
                // Make sure the action is valid
                const validActions = gmailActions.map(a => a.value);
                console.log('🤖 Gmail Modal: Valid actions:', validActions);
                console.log('🤖 Gmail Modal: Requested action:', initialData.action);
                if (validActions.includes(initialData.action)) {
                    console.log('🤖 Gmail Modal: Action is valid, setting it');
                    setActionConfig(prev => ({
                        ...prev,
                        action: initialData.action
                    }));
                } else {
                    console.log('🤖 Gmail Modal: Action is not valid');
                }
            }
        } else {
            console.log('🤖 Gmail Modal: No initialData or empty initialData');
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
                    connector_name: 'gmail_connector',
                    redirect_uri: 'http://localhost:3000/auth/oauth/callback'
                })
            });

            if (!response.ok) {
                throw new Error(`OAuth initiate failed: ${response.status}`);
            }

            const oauthData = await response.json();

            localStorage.setItem('oauth_state', oauthData.state);
            localStorage.setItem('oauth_connector', 'gmail_connector');

            const popup = window.open(oauthData.authorization_url, 'oauth-popup', 'width=600,height=600');

            const checkClosed = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(checkClosed);
                    setIsLoading(false);
                    
                    // Check authentication status after popup closes
                    setTimeout(() => {
                        console.log('🔐 Gmail Modal: OAuth popup closed, checking auth status');
                        checkAuthStatus();
                    }, 1000); // Wait 1 second for backend to process the callback
                }
            }, 1000);

        } catch (error) {
            console.error('OAuth error:', error);
            setAuthStatus('error');
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
                    connector_name: 'gmail_connector'
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
            case 'send':
            case 'create_draft':
                return (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="to">To (Required)</Label>
                                <Input
                                    id="to"
                                    value={actionConfig.to}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, to: e.target.value }))}
                                    placeholder="recipient@example.com"
                                />
                            </div>
                            <div>
                                <Label htmlFor="sender_name">Sender Name</Label>
                                <Input
                                    id="sender_name"
                                    value={actionConfig.sender_name}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, sender_name: e.target.value }))}
                                    placeholder="Your Name"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="cc">CC</Label>
                                <Input
                                    id="cc"
                                    value={actionConfig.cc}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, cc: e.target.value }))}
                                    placeholder="cc@example.com"
                                />
                            </div>
                            <div>
                                <Label htmlFor="bcc">BCC</Label>
                                <Input
                                    id="bcc"
                                    value={actionConfig.bcc}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, bcc: e.target.value }))}
                                    placeholder="bcc@example.com"
                                />
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="subject">Subject {action === 'send' ? '(Required)' : ''}</Label>
                            <Input
                                id="subject"
                                value={actionConfig.subject}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, subject: e.target.value }))}
                                placeholder="Email subject"
                            />
                        </div>

                        <div>
                            <Label htmlFor="body">Body</Label>
                            <Textarea
                                id="body"
                                value={actionConfig.body}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, body: e.target.value }))}
                                placeholder="Email body content"
                                rows={4}
                            />
                        </div>

                        <div>
                            <Label htmlFor="html_body">HTML Body (Optional)</Label>
                            <Textarea
                                id="html_body"
                                value={actionConfig.html_body}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, html_body: e.target.value }))}
                                placeholder="<p>HTML email content</p>"
                                rows={3}
                            />
                        </div>

                        <div>
                            <Label htmlFor="reply_to">Reply-To</Label>
                            <Input
                                id="reply_to"
                                value={actionConfig.reply_to}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, reply_to: e.target.value }))}
                                placeholder="reply@example.com"
                            />
                        </div>
                    </div>
                );

            case 'reply':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="message_id">Message ID (Required)</Label>
                            <Input
                                id="message_id"
                                value={actionConfig.message_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, message_id: e.target.value }))}
                                placeholder="Gmail message ID"
                            />
                        </div>

                        <div>
                            <Label htmlFor="body">Reply Body (Required)</Label>
                            <Textarea
                                id="body"
                                value={actionConfig.body}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, body: e.target.value }))}
                                placeholder="Your reply message"
                                rows={4}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="to">Override To</Label>
                                <Input
                                    id="to"
                                    value={actionConfig.to}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, to: e.target.value }))}
                                    placeholder="Override recipient"
                                />
                            </div>
                            <div>
                                <Label htmlFor="sender_name">Sender Name</Label>
                                <Input
                                    id="sender_name"
                                    value={actionConfig.sender_name}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, sender_name: e.target.value }))}
                                    placeholder="Your Name"
                                />
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
                                placeholder="from:example@gmail.com is:unread"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Use Gmail search syntax (e.g., from:, to:, subject:, is:unread, has:attachment)
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="max_results">Max Results</Label>
                                <Input
                                    id="max_results"
                                    type="number"
                                    value={actionConfig.max_results}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, max_results: parseInt(e.target.value) || 10 }))}
                                    min="1"
                                    max="500"
                                />
                            </div>
                            <div className="flex items-center space-x-2 pt-6">
                                <Switch
                                    id="include_spam_trash"
                                    checked={actionConfig.include_spam_trash}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, include_spam_trash: checked }))}
                                />
                                <Label htmlFor="include_spam_trash">Include Spam/Trash</Label>
                            </div>
                        </div>
                    </div>
                );

            case 'read':
            case 'delete':
            case 'mark_as_read':
            case 'mark_as_unread':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="message_id">Message ID (Required)</Label>
                            <Input
                                id="message_id"
                                value={actionConfig.message_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, message_id: e.target.value }))}
                                placeholder="Gmail message ID"
                            />
                        </div>

                        {action === 'read' && (
                            <div>
                                <Label htmlFor="format">Response Format</Label>
                                <Select value={actionConfig.format} onValueChange={(value) => setActionConfig(prev => ({ ...prev, format: value }))}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="full">Full</SelectItem>
                                        <SelectItem value="metadata">Metadata Only</SelectItem>
                                        <SelectItem value="minimal">Minimal</SelectItem>
                                        <SelectItem value="raw">Raw</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                    </div>
                );

            case 'add_labels':
            case 'remove_labels':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="message_id">Message ID (Required)</Label>
                            <Input
                                id="message_id"
                                value={actionConfig.message_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, message_id: e.target.value }))}
                                placeholder="Gmail message ID"
                            />
                        </div>

                        <div>
                            <Label htmlFor="label_ids">Label IDs (Required)</Label>
                            <Input
                                id="label_ids"
                                value={actionConfig.label_ids.join(', ')}
                                onChange={(e) => setActionConfig(prev => ({
                                    ...prev,
                                    label_ids: e.target.value.split(',').map(id => id.trim()).filter(Boolean)
                                }))}
                                placeholder="IMPORTANT, WORK, Label_123"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Comma-separated list of label IDs or names
                            </p>
                        </div>
                    </div>
                );

            case 'create_label':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="label_name">Label Name (Required)</Label>
                            <Input
                                id="label_name"
                                value={actionConfig.label_name}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, label_name: e.target.value }))}
                                placeholder="My Custom Label"
                            />
                        </div>

                        <div>
                            <Label htmlFor="label_color">Label Color</Label>
                            <Select value={actionConfig.label_color} onValueChange={(value) => setActionConfig(prev => ({ ...prev, label_color: value }))}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select color" />
                                </SelectTrigger>
                                <SelectContent>
                                    {labelColors.map((color) => (
                                        <SelectItem key={color.value} value={color.value}>
                                            <div className="flex items-center gap-2">
                                                <div className={`w-3 h-3 rounded-full ${color.color}`} />
                                                {color.label}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                );

            case 'get_draft':
            case 'delete_draft':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="draft_id">Draft ID (Required)</Label>
                            <Input
                                id="draft_id"
                                value={actionConfig.draft_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, draft_id: e.target.value }))}
                                placeholder="Gmail draft ID"
                            />
                        </div>
                    </div>
                );

            case 'get_thread':
            case 'delete_thread':
            case 'trash_thread':
            case 'untrash_thread':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="thread_id">Thread ID (Required)</Label>
                            <Input
                                id="thread_id"
                                value={actionConfig.thread_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, thread_id: e.target.value }))}
                                placeholder="Gmail thread ID"
                            />
                        </div>

                        {action === 'get_thread' && (
                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="simple"
                                    checked={actionConfig.simple}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, simple: checked }))}
                                />
                                <Label htmlFor="simple">Simple Format</Label>
                            </div>
                        )}
                    </div>
                );

            case 'add_thread_labels':
            case 'remove_thread_labels':
                return (
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="thread_id">Thread ID (Required)</Label>
                            <Input
                                id="thread_id"
                                value={actionConfig.thread_id}
                                onChange={(e) => setActionConfig(prev => ({ ...prev, thread_id: e.target.value }))}
                                placeholder="Gmail thread ID"
                            />
                        </div>

                        <div>
                            <Label htmlFor="label_ids">Label IDs (Required)</Label>
                            <Input
                                id="label_ids"
                                value={actionConfig.label_ids.join(', ')}
                                onChange={(e) => setActionConfig(prev => ({
                                    ...prev,
                                    label_ids: e.target.value.split(',').map(id => id.trim()).filter(Boolean)
                                }))}
                                placeholder="IMPORTANT, WORK, Label_123"
                            />
                        </div>
                    </div>
                );

            case 'list':
            case 'list_drafts':
            case 'list_threads':
                return (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="limit">Limit</Label>
                                <Input
                                    id="limit"
                                    type="number"
                                    value={actionConfig.limit}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, limit: parseInt(e.target.value) || 10 }))}
                                    min="1"
                                    max="500"
                                />
                            </div>
                            <div className="flex items-center space-x-2 pt-6">
                                <Switch
                                    id="return_all"
                                    checked={actionConfig.return_all}
                                    onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, return_all: checked }))}
                                />
                                <Label htmlFor="return_all">Return All</Label>
                            </div>
                        </div>

                        {(action === 'list' || action === 'list_threads') && (
                            <div>
                                <Label htmlFor="query">Search Query (Optional)</Label>
                                <Input
                                    id="query"
                                    value={actionConfig.query}
                                    onChange={(e) => setActionConfig(prev => ({ ...prev, query: e.target.value }))}
                                    placeholder="Filter results with Gmail search syntax"
                                />
                            </div>
                        )}

                        <div className="flex items-center space-x-2">
                            <Switch
                                id="simple"
                                checked={actionConfig.simple}
                                onCheckedChange={(checked) => setActionConfig(prev => ({ ...prev, simple: checked }))}
                            />
                            <Label htmlFor="simple">Simple Format</Label>
                        </div>
                    </div>
                );

            default:
                return (
                    <div className="text-center py-8 text-gray-500">
                        <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Select an action to configure parameters</p>
                    </div>
                );
        }
    };

    const groupedActions = gmailActions.reduce((acc, action) => {
        if (!acc[action.category]) {
            acc[action.category] = [];
        }
        acc[action.category].push(action);
        return acc;
    }, {} as Record<string, typeof gmailActions>);

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-red-600" />
                        {mode === 'create' ? 'Configure Gmail Connector' : 'Edit Gmail Connector'}
                    </DialogTitle>
                    <DialogDescription>
                        Configure Gmail connector with comprehensive email management capabilities
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="action" className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Action
                        </TabsTrigger>
                        <TabsTrigger value="auth" className="flex items-center gap-2">
                            <Key className="h-4 w-4" />
                            Authentication
                        </TabsTrigger>
                        <TabsTrigger value="test" className="flex items-center gap-2">
                            <TestTube className="h-4 w-4" />
                            Test
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="action" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Gmail Action Configuration</CardTitle>
                                <CardDescription>
                                    Choose and configure the Gmail operation you want to perform
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div>
                                    <Label htmlFor="action">Gmail Action</Label>
                                    <Select value={actionConfig.action} onValueChange={(value) => setActionConfig(prev => ({ ...prev, action: value }))}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {Object.entries(groupedActions).map(([category, actions]) => (
                                                <div key={category}>
                                                    <div className="px-2 py-1 text-sm font-semibold text-gray-500 bg-gray-50">
                                                        {category}
                                                    </div>
                                                    {actions.map((action) => (
                                                        <SelectItem key={action.value} value={action.value}>
                                                            <div className="flex items-center gap-2">
                                                                <action.icon className="h-4 w-4" />
                                                                {action.label}
                                                            </div>
                                                        </SelectItem>
                                                    ))}
                                                </div>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <Separator />

                                <div>
                                    <h4 className="font-medium mb-4">Action Parameters</h4>
                                    {renderActionFields()}
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="auth" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Gmail Authentication</CardTitle>
                                <CardDescription>
                                    Authenticate with Google to access Gmail API
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center justify-between p-4 border rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-full ${authStatus === 'authenticated' ? 'bg-green-100' :
                                            authStatus === 'error' ? 'bg-red-100' : 'bg-gray-100'
                                            }`}>
                                            {authStatus === 'authenticated' ? (
                                                <CheckCircle className="h-5 w-5 text-green-600" />
                                            ) : authStatus === 'error' ? (
                                                <XCircle className="h-5 w-5 text-red-600" />
                                            ) : (
                                                <Key className="h-5 w-5 text-gray-600" />
                                            )}
                                        </div>
                                        <div>
                                            <p className="font-medium">
                                                {authStatus === 'authenticated' ? 'Authenticated' :
                                                    authStatus === 'error' ? 'Authentication Error' : 'Not Authenticated'}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {authStatus === 'authenticated' ? 'Gmail access configured' :
                                                    authStatus === 'error' ? 'Please try authenticating again' : 'Connect your Gmail account'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            onClick={handleGoogleOAuth}
                                            disabled={isLoading}
                                            variant={authStatus === 'authenticated' ? 'outline' : 'default'}
                                        >
                                            {isLoading ? (
                                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                            ) : (
                                                <Key className="h-4 w-4 mr-2" />
                                            )}
                                            {authStatus === 'authenticated' ? 'Re-authenticate' : 'Connect Gmail'}
                                        </Button>
                                        <Button
                                            onClick={checkAuthStatus}
                                            variant="ghost"
                                            size="sm"
                                            title="Refresh authentication status"
                                        >
                                            <Loader2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>

                                <Alert>
                                    <Info className="h-4 w-4" />
                                    <AlertDescription>
                                        Gmail connector requires OAuth2 authentication with the following permissions:
                                        <ul className="list-disc list-inside mt-2 space-y-1">
                                            <li>Read Gmail messages</li>
                                            <li>Send emails</li>
                                            <li>Modify messages and labels</li>
                                            <li>Manage Gmail labels</li>
                                        </ul>
                                    </AlertDescription>
                                </Alert>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <Label>Required Scopes</Label>
                                        <div className="mt-2 space-y-1">
                                            {config.auth_config.scopes.map((scope, index) => (
                                                <Badge key={index} variant="secondary" className="text-xs">
                                                    {scope.split('/').pop()}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <Label>Authentication Type</Label>
                                        <div className="mt-2">
                                            <Badge variant="outline">OAuth 2.0</Badge>
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="test" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Test Gmail Connection</CardTitle>
                                <CardDescription>
                                    Verify that your Gmail connector is properly configured
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Button
                                    onClick={handleTestConnection}
                                    disabled={isLoading || authStatus !== 'authenticated'}
                                    className="w-full"
                                >
                                    {isLoading ? (
                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                    ) : (
                                        <TestTube className="h-4 w-4 mr-2" />
                                    )}
                                    Test Connection
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

                                <div className="space-y-3">
                                    <h4 className="font-medium">Connection Details</h4>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-gray-500">Connector:</span>
                                            <span className="ml-2 font-medium">Gmail API v1</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500">Authentication:</span>
                                            <span className="ml-2 font-medium">
                                                {authStatus === 'authenticated' ? 'OAuth 2.0' : 'Not configured'}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500">Actions Available:</span>
                                            <span className="ml-2 font-medium">{gmailActions.length} operations</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500">Status:</span>
                                            <Badge
                                                variant={authStatus === 'authenticated' ? 'default' : 'secondary'}
                                                className="ml-2"
                                            >
                                                {authStatus === 'authenticated' ? 'Ready' : 'Needs Setup'}
                                            </Badge>
                                        </div>
                                    </div>
                                </div>
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
                        disabled={authStatus !== 'authenticated'}
                    >
                        <Save className="h-4 w-4 mr-2" />
                        Save Configuration
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default GmailConnectorModal;