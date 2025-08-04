"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
    Settings,
    CheckCircle,
    XCircle,
    AlertTriangle,
    ExternalLink,
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
    User,
    Loader2,
    RefreshCw,
    Activity,
    Clock,
    Hash
} from 'lucide-react';
import { NotionConnectorModal } from './NotionConnectorModal';

interface NotionConnectorProps {
    onConfigChange?: (config: any) => void;
    initialConfig?: any;
}

interface NotionStats {
    pages: number;
    databases: number;
    users: number;
    lastSync: string;
}

interface RecentActivity {
    id: string;
    type: 'page_created' | 'page_updated' | 'database_queried' | 'blocks_added';
    title: string;
    timestamp: string;
    status: 'success' | 'error';
}

export function NotionConnector({ onConfigChange, initialConfig }: NotionConnectorProps) {
    const { user, session } = useAuth();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [config, setConfig] = useState(initialConfig || null);
    const [isLoading, setIsLoading] = useState(false);
    const [stats, setStats] = useState<NotionStats | null>(null);
    const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
    const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected');

    useEffect(() => {
        if (config?.status === 'configured') {
            loadStats();
            loadRecentActivity();
            setConnectionStatus('connected');
        }
    }, [config]);

    const loadStats = async () => {
        if (!config?.auth_config?.api_key) return;

        try {
            setIsLoading(true);
            
            // Load basic stats
            const [pagesResponse, databasesResponse, usersResponse] = await Promise.all([
                fetch('/api/connectors/notion/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({
                        auth_config: config.auth_config,
                        parameters: {
                            resource: 'page',
                            operation: 'search_pages',
                            page_size: 1
                        }
                    })
                }),
                fetch('/api/connectors/notion/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({
                        auth_config: config.auth_config,
                        parameters: {
                            resource: 'database',
                            operation: 'get_all_databases',
                            page_size: 1
                        }
                    })
                }),
                fetch('/api/connectors/notion/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({
                        auth_config: config.auth_config,
                        parameters: {
                            resource: 'user',
                            operation: 'get_all_users',
                            page_size: 1
                        }
                    })
                })
            ]);

            const [pagesData, databasesData, usersData] = await Promise.all([
                pagesResponse.json(),
                databasesResponse.json(),
                usersResponse.json()
            ]);

            setStats({
                pages: pagesData.data?.length || 0,
                databases: databasesData.data?.length || 0,
                users: usersData.data?.length || 0,
                lastSync: new Date().toISOString()
            });

            setConnectionStatus('connected');
        } catch (error) {
            console.error('Failed to load stats:', error);
            setConnectionStatus('error');
        } finally {
            setIsLoading(false);
        }
    };

    const loadRecentActivity = async () => {
        // Mock recent activity for demo
        setRecentActivity([
            {
                id: '1',
                type: 'page_created',
                title: 'Created "Meeting Notes" page',
                timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
                status: 'success'
            },
            {
                id: '2',
                type: 'database_queried',
                title: 'Queried "Projects" database',
                timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
                status: 'success'
            },
            {
                id: '3',
                type: 'blocks_added',
                title: 'Added content blocks to page',
                timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
                status: 'success'
            }
        ]);
    };

    const handleConfigSave = async (newConfig: any) => {
        setConfig(newConfig);
        onConfigChange?.(newConfig);
        
        if (newConfig.status === 'configured') {
            await loadStats();
            await loadRecentActivity();
        }
    };

    const handleRefresh = () => {
        if (config?.status === 'configured') {
            loadStats();
            loadRecentActivity();
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'configured':
            case 'connected':
                return 'bg-green-100 text-green-800 border-green-200';
            case 'needs_auth':
            case 'disconnected':
                return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'error':
                return 'bg-red-100 text-red-800 border-red-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'configured':
            case 'connected':
                return <CheckCircle className="w-4 h-4" />;
            case 'needs_auth':
            case 'disconnected':
                return <AlertTriangle className="w-4 h-4" />;
            case 'error':
                return <XCircle className="w-4 h-4" />;
            default:
                return <AlertTriangle className="w-4 h-4" />;
        }
    };

    const getActivityIcon = (type: string) => {
        switch (type) {
            case 'page_created':
                return <Plus className="w-4 h-4 text-green-600" />;
            case 'page_updated':
                return <Edit className="w-4 h-4 text-blue-600" />;
            case 'database_queried':
                return <Search className="w-4 h-4 text-purple-600" />;
            case 'blocks_added':
                return <Blocks className="w-4 h-4 text-orange-600" />;
            default:
                return <Activity className="w-4 h-4 text-gray-600" />;
        }
    };

    const formatTimeAgo = (timestamp: string) => {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInMinutes = Math.floor((now.getTime() - time.getTime()) / (1000 * 60));
        
        if (diffInMinutes < 1) return 'Just now';
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
        if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
        return `${Math.floor(diffInMinutes / 1440)}d ago`;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
                        <span className="text-white font-bold">N</span>
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold">Notion Connector</h2>
                        <p className="text-sm text-gray-600">Manage your Notion workspace content</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Badge className={getStatusColor(config?.status || 'disconnected')}>
                        {getStatusIcon(config?.status || 'disconnected')}
                        <span className="ml-1 capitalize">
                            {config?.status === 'configured' ? 'Connected' : config?.status || 'Disconnected'}
                        </span>
                    </Badge>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isLoading || !config?.auth_config?.api_key}
                        className="flex items-center gap-2"
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button
                        onClick={() => setIsModalOpen(true)}
                        className="flex items-center gap-2"
                    >
                        <Settings className="w-4 h-4" />
                        Configure
                    </Button>
                </div>
            </div>

            {/* Connection Status */}
            {!config?.auth_config?.api_key && (
                <Alert>
                    <AlertTriangle className="w-4 h-4" />
                    <AlertDescription>
                        <div className="flex items-center justify-between">
                            <span>Notion integration not configured. Click Configure to set up your connection.</span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsModalOpen(true)}
                                className="ml-4"
                            >
                                Configure Now
                            </Button>
                        </div>
                    </AlertDescription>
                </Alert>
            )}

            {config?.status === 'error' && (
                <Alert className="border-red-200">
                    <XCircle className="w-4 h-4 text-red-600" />
                    <AlertDescription className="text-red-700">
                        Connection error. Please check your integration token and try again.
                    </AlertDescription>
                </Alert>
            )}

            {/* Stats Cards */}
            {config?.status === 'configured' && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                    <FileText className="w-5 h-5 text-blue-600" />
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Pages</p>
                                    <p className="text-2xl font-semibold">
                                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : stats?.pages || '0'}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                    <Database className="w-5 h-5 text-purple-600" />
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Databases</p>
                                    <p className="text-2xl font-semibold">
                                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : stats?.databases || '0'}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                    <Users className="w-5 h-5 text-green-600" />
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Users</p>
                                    <p className="text-2xl font-semibold">
                                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : stats?.users || '0'}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                    <Clock className="w-5 h-5 text-orange-600" />
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Last Sync</p>
                                    <p className="text-sm font-medium">
                                        {stats?.lastSync ? formatTimeAgo(stats.lastSync) : 'Never'}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Main Content */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Quick Actions */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Hash className="w-5 h-5" />
                            Quick Actions
                        </CardTitle>
                        <CardDescription>
                            Common Notion operations you can perform
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <Button
                                variant="outline"
                                className="flex items-center gap-2 h-auto p-3"
                                disabled={!config?.auth_config?.api_key}
                                onClick={() => setIsModalOpen(true)}
                            >
                                <Plus className="w-4 h-4" />
                                <div className="text-left">
                                    <div className="font-medium">Create Page</div>
                                    <div className="text-xs text-gray-500">New Notion page</div>
                                </div>
                            </Button>

                            <Button
                                variant="outline"
                                className="flex items-center gap-2 h-auto p-3"
                                disabled={!config?.auth_config?.api_key}
                                onClick={() => setIsModalOpen(true)}
                            >
                                <Search className="w-4 h-4" />
                                <div className="text-left">
                                    <div className="font-medium">Search Pages</div>
                                    <div className="text-xs text-gray-500">Find content</div>
                                </div>
                            </Button>

                            <Button
                                variant="outline"
                                className="flex items-center gap-2 h-auto p-3"
                                disabled={!config?.auth_config?.api_key}
                                onClick={() => setIsModalOpen(true)}
                            >
                                <Database className="w-4 h-4" />
                                <div className="text-left">
                                    <div className="font-medium">Query Database</div>
                                    <div className="text-xs text-gray-500">Get database pages</div>
                                </div>
                            </Button>

                            <Button
                                variant="outline"
                                className="flex items-center gap-2 h-auto p-3"
                                disabled={!config?.auth_config?.api_key}
                                onClick={() => setIsModalOpen(true)}
                            >
                                <Blocks className="w-4 h-4" />
                                <div className="text-left">
                                    <div className="font-medium">Add Content</div>
                                    <div className="text-xs text-gray-500">Append blocks</div>
                                </div>
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Recent Activity */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Activity className="w-5 h-5" />
                            Recent Activity
                        </CardTitle>
                        <CardDescription>
                            Latest operations performed with Notion
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {recentActivity.length > 0 ? (
                            <div className="space-y-3">
                                {recentActivity.map((activity, index) => (
                                    <div key={activity.id}>
                                        <div className="flex items-center gap-3">
                                            {getActivityIcon(activity.type)}
                                            <div className="flex-1">
                                                <p className="text-sm font-medium">{activity.title}</p>
                                                <p className="text-xs text-gray-500">
                                                    {formatTimeAgo(activity.timestamp)}
                                                </p>
                                            </div>
                                            <Badge
                                                variant={activity.status === 'success' ? 'default' : 'destructive'}
                                                className="text-xs"
                                            >
                                                {activity.status}
                                            </Badge>
                                        </div>
                                        {index < recentActivity.length - 1 && (
                                            <Separator className="mt-3" />
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-6 text-gray-500">
                                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No recent activity</p>
                                <p className="text-xs">Operations will appear here once you start using the connector</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Resources Overview */}
            {config?.status === 'configured' && (
                <Card>
                    <CardHeader>
                        <CardTitle>Available Resources</CardTitle>
                        <CardDescription>
                            Notion resources you can interact with using this connector
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                            <div className="text-center p-4 border rounded-lg">
                                <FileText className="w-8 h-8 mx-auto mb-2 text-blue-600" />
                                <h4 className="font-medium">Pages</h4>
                                <p className="text-xs text-gray-500 mt-1">Create, read, search, archive</p>
                            </div>
                            <div className="text-center p-4 border rounded-lg">
                                <Database className="w-8 h-8 mx-auto mb-2 text-purple-600" />
                                <h4 className="font-medium">Databases</h4>
                                <p className="text-xs text-gray-500 mt-1">Get, list, search</p>
                            </div>
                            <div className="text-center p-4 border rounded-lg">
                                <FileText className="w-8 h-8 mx-auto mb-2 text-green-600" />
                                <h4 className="font-medium">Database Pages</h4>
                                <p className="text-xs text-gray-500 mt-1">CRUD operations</p>
                            </div>
                            <div className="text-center p-4 border rounded-lg">
                                <Blocks className="w-8 h-8 mx-auto mb-2 text-orange-600" />
                                <h4 className="font-medium">Blocks</h4>
                                <p className="text-xs text-gray-500 mt-1">Append, get children</p>
                            </div>
                            <div className="text-center p-4 border rounded-lg">
                                <Users className="w-8 h-8 mx-auto mb-2 text-red-600" />
                                <h4 className="font-medium">Users</h4>
                                <p className="text-xs text-gray-500 mt-1">Get user info</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Configuration Modal */}
            <NotionConnectorModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleConfigSave}
            />
        </div>
    );
}