"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
    Youtube, 
    Settings, 
    CheckCircle, 
    AlertTriangle, 
    Video,
    Users,
    List,
    Play,
    Upload,
    Search,
    ThumbsUp,
    Edit,
    Trash2,
    Plus,
    Eye,
    Globe
} from 'lucide-react';
import { YouTubeConnectorModal } from './YouTubeConnectorModal';

interface YouTubeConnectorProps {
    onConfigured?: (config: any) => void;
}

const YOUTUBE_FEATURES = [
    {
        icon: Video,
        title: 'Video Management',
        description: 'Upload, update, delete, and search YouTube videos',
        operations: ['Upload Video', 'Update Video', 'Delete Video', 'Search Videos', 'Get Video Details']
    },
    {
        icon: Users,
        title: 'Channel Operations',
        description: 'Manage YouTube channels and their settings',
        operations: ['Get Channel Info', 'Update Channel', 'Upload Banner', 'List Channels']
    },
    {
        icon: List,
        title: 'Playlist Management',
        description: 'Create and manage YouTube playlists',
        operations: ['Create Playlist', 'Update Playlist', 'Delete Playlist', 'Add/Remove Videos']
    },
    {
        icon: ThumbsUp,
        title: 'Engagement',
        description: 'Interact with videos through ratings and comments',
        operations: ['Rate Videos', 'Manage Comments', 'View Statistics']
    },
    {
        icon: Search,
        title: 'Content Discovery',
        description: 'Search and discover YouTube content',
        operations: ['Search Videos', 'Get Categories', 'Filter by Region', 'Advanced Search']
    },
    {
        icon: Globe,
        title: 'Analytics & Insights',
        description: 'Access YouTube analytics and performance data',
        operations: ['View Statistics', 'Get Insights', 'Track Performance', 'Audience Data']
    }
];

const YOUTUBE_OPERATIONS = [
    { category: 'Channel', operations: ['Get Channel', 'Get All Channels', 'Update Channel', 'Upload Banner'] },
    { category: 'Playlist', operations: ['Create Playlist', 'Delete Playlist', 'Get Playlist', 'Get All Playlists', 'Update Playlist'] },
    { category: 'Playlist Items', operations: ['Add to Playlist', 'Remove from Playlist', 'Get Playlist Item', 'Get All Items'] },
    { category: 'Video', operations: ['Delete Video', 'Get Video', 'Search Videos', 'Rate Video', 'Update Video', 'Upload Video'] },
    { category: 'Categories', operations: ['Get Video Categories'] }
];

export function YouTubeConnector({ onConfigured }: YouTubeConnectorProps) {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [config, setConfig] = useState<any>(null);

    const handleSaveConfig = async (newConfig: any) => {
        setConfig(newConfig);
        if (onConfigured) {
            onConfigured(newConfig);
        }
    };

    const getStatusBadge = () => {
        if (!config) {
            return <Badge variant="secondary">Not Configured</Badge>;
        }
        
        switch (config.status) {
            case 'configured':
                return <Badge variant="default" className="bg-green-600">Configured</Badge>;
            case 'needs_auth':
                return <Badge variant="destructive">Needs Authentication</Badge>;
            case 'error':
                return <Badge variant="destructive">Error</Badge>;
            default:
                return <Badge variant="secondary">Unknown</Badge>;
        }
    };

    return (
        <div className="space-y-6">
            {/* Header Card */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-red-100 rounded-lg">
                                <Youtube className="h-6 w-6 text-red-600" />
                            </div>
                            <div>
                                <CardTitle className="text-xl">YouTube Connector</CardTitle>
                                <CardDescription>
                                    Comprehensive YouTube API integration for video and channel management
                                </CardDescription>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {getStatusBadge()}
                            <Button onClick={() => setIsModalOpen(true)} className="bg-red-600 hover:bg-red-700">
                                <Settings className="h-4 w-4 mr-2" />
                                Configure
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                
                {config && (
                    <CardContent>
                        <Alert className="bg-green-50 border-green-200">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-800">
                                YouTube connector is configured and ready to use. 
                                Current operation: <strong>{config.settings?.operation || 'Not set'}</strong>
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                )}
            </Card>

            {/* Features Overview */}
            <Card>
                <CardHeader>
                    <CardTitle>YouTube API Capabilities</CardTitle>
                    <CardDescription>
                        Comprehensive YouTube integration with full API coverage
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {YOUTUBE_FEATURES.map((feature, index) => (
                            <div key={index} className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                                <div className="flex items-center gap-2 mb-2">
                                    <feature.icon className="h-5 w-5 text-red-600" />
                                    <h3 className="font-medium">{feature.title}</h3>
                                </div>
                                <p className="text-sm text-gray-600 mb-3">{feature.description}</p>
                                <div className="flex flex-wrap gap-1">
                                    {feature.operations.slice(0, 3).map((op, opIndex) => (
                                        <Badge key={opIndex} variant="outline" className="text-xs">
                                            {op}
                                        </Badge>
                                    ))}
                                    {feature.operations.length > 3 && (
                                        <Badge variant="outline" className="text-xs">
                                            +{feature.operations.length - 3} more
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Available Operations */}
            <Card>
                <CardHeader>
                    <CardTitle>Available Operations</CardTitle>
                    <CardDescription>
                        Complete list of YouTube API operations supported by this connector
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {YOUTUBE_OPERATIONS.map((category, index) => (
                            <div key={index} className="border rounded-lg p-4">
                                <h3 className="font-medium mb-3 text-red-700">{category.category} Operations</h3>
                                <div className="flex flex-wrap gap-2">
                                    {category.operations.map((operation, opIndex) => (
                                        <Badge key={opIndex} variant="outline" className="hover:bg-red-50">
                                            {operation}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Authentication Info */}
            <Card>
                <CardHeader>
                    <CardTitle>Authentication Requirements</CardTitle>
                    <CardDescription>
                        YouTube API uses OAuth2 authentication for secure access
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <Alert>
                            <AlertTriangle className="h-4 w-4" />
                            <AlertDescription>
                                <strong>OAuth2 Required:</strong> YouTube API requires OAuth2 authentication with Google. 
                                You'll need to set up a Google Cloud project and obtain OAuth2 credentials.
                            </AlertDescription>
                        </Alert>
                        
                        <div className="bg-blue-50 p-4 rounded-lg">
                            <h4 className="font-medium text-blue-900 mb-2">Required OAuth2 Scopes:</h4>
                            <ul className="text-sm text-blue-800 space-y-1">
                                <li>• <code>https://www.googleapis.com/auth/youtube</code> - Full YouTube access</li>
                                <li>• <code>https://www.googleapis.com/auth/youtube.upload</code> - Video upload permissions</li>
                                <li>• <code>https://www.googleapis.com/auth/youtube.readonly</code> - Read-only access</li>
                            </ul>
                        </div>

                        <div className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium mb-2">Setup Steps:</h4>
                            <ol className="text-sm space-y-1 list-decimal list-inside">
                                <li>Create a project in Google Cloud Console</li>
                                <li>Enable the YouTube Data API v3</li>
                                <li>Create OAuth2 credentials (Client ID and Secret)</li>
                                <li>Configure authorized redirect URIs</li>
                                <li>Use the OAuth2 flow to obtain access tokens</li>
                                <li>Configure the connector with your tokens</li>
                            </ol>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Usage Examples */}
            <Card>
                <CardHeader>
                    <CardTitle>Usage Examples</CardTitle>
                    <CardDescription>
                        Common YouTube automation scenarios you can implement
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 border rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                                <Search className="h-4 w-4 text-red-600" />
                                <h3 className="font-medium">Content Discovery</h3>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                                Search for videos by keywords, get trending content, and discover new channels
                            </p>
                            <Badge variant="outline" className="text-xs">video_getAll</Badge>
                        </div>

                        <div className="p-4 border rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                                <Upload className="h-4 w-4 text-red-600" />
                                <h3 className="font-medium">Video Upload</h3>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                                Automatically upload videos with metadata, thumbnails, and privacy settings
                            </p>
                            <Badge variant="outline" className="text-xs">video_upload</Badge>
                        </div>

                        <div className="p-4 border rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                                <List className="h-4 w-4 text-red-600" />
                                <h3 className="font-medium">Playlist Management</h3>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                                Create playlists, add/remove videos, and organize your content automatically
                            </p>
                            <Badge variant="outline" className="text-xs">playlist_create</Badge>
                        </div>

                        <div className="p-4 border rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                                <Users className="h-4 w-4 text-red-600" />
                                <h3 className="font-medium">Channel Analytics</h3>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                                Monitor channel performance, subscriber growth, and video statistics
                            </p>
                            <Badge variant="outline" className="text-xs">channel_getAll</Badge>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Configuration Modal */}
            <YouTubeConnectorModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleSaveConfig}
            />
        </div>
    );
}