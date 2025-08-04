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
    Play,
    Video,
    Users,
    List,
    Plus,
    Trash2,
    Edit,
    ThumbsUp,
    Upload,
    Search,
    Eye,
    Globe,
    Lock,
    Unlock,
    Youtube,
    Star,
    Shield
} from 'lucide-react';

interface YouTubeConfig {
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

interface YouTubeConnectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: YouTubeConfig) => Promise<void>;
    initialData?: any; // AI-generated parameters
}

interface ActionParameter {
    name: string;
    type: string;
    label: string;
    required?: boolean;
    placeholder?: string;
    description?: string;
    options?: { value: string; label: string }[];
    min?: number;
    max?: number;
}

interface YouTubeAction {
    label: string;
    icon: any;
    description: string;
    resource: string;
    requiredParams: string[];
    parameters: ActionParameter[];
}

// YouTube action definitions organized by resource type
const YOUTUBE_ACTIONS: Record<string, YouTubeAction> = {
    // Channel Operations
    channel_get: {
        label: 'Get Channel',
        icon: Users,
        description: 'Get details of a specific YouTube channel',
        resource: 'channel',
        requiredParams: ['channelId'],
        parameters: [
            { name: 'channelId', type: 'string', label: 'Channel ID', required: true, placeholder: 'UCuAXFkgsw1L7xaCfnd5JJOw' },
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,statistics,contentDetails',
                description: 'Comma-separated list of resource properties'
            }
        ]
    },
    channel_getAll: {
        label: 'Get All Channels',
        icon: Users,
        description: 'List channels with filtering options',
        resource: 'channel',
        requiredParams: [],
        parameters: [
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,statistics',
                description: 'Comma-separated list of resource properties'
            },
            { name: 'maxResults', type: 'number', label: 'Max Results', placeholder: '25', min: 1, max: 50, required: false },
            { name: 'categoryId_filter', type: 'string', label: 'Category ID Filter', placeholder: 'Optional category filter', required: false },
            { name: 'forUsername', type: 'string', label: 'Username Filter', placeholder: 'Filter by username', required: false },
            { name: 'managedByMe', type: 'boolean', label: 'Managed by Me Only', required: false }
        ]
    },
    channel_update: {
        label: 'Update Channel',
        icon: Edit,
        description: 'Update channel branding settings',
        resource: 'channel',
        requiredParams: ['channelId'],
        parameters: [
            { name: 'channelId', type: 'string', label: 'Channel ID', required: true, placeholder: 'UCuAXFkgsw1L7xaCfnd5JJOw' },
            { name: 'description', type: 'textarea', label: 'Channel Description', placeholder: 'Updated channel description...', required: false },
            { name: 'keywords', type: 'string', label: 'Keywords', placeholder: 'tech,programming,tutorials', required: false },
            { name: 'country', type: 'string', label: 'Country', placeholder: 'US', required: false },
            { name: 'defaultLanguage', type: 'string', label: 'Default Language', placeholder: 'en', required: false }
        ]
    },
    channel_uploadBanner: {
        label: 'Upload Channel Banner',
        icon: Upload,
        description: 'Upload a banner image for the channel',
        resource: 'channel',
        requiredParams: ['channelId', 'binaryProperty'],
        parameters: [
            { name: 'channelId', type: 'string', label: 'Channel ID', required: true, placeholder: 'UCuAXFkgsw1L7xaCfnd5JJOw' },
            { name: 'binaryProperty', type: 'string', label: 'Binary Property Name', required: true, placeholder: 'data' }
        ]
    },

    // Playlist Operations
    playlist_create: {
        label: 'Create Playlist',
        icon: Plus,
        description: 'Create a new YouTube playlist',
        resource: 'playlist',
        requiredParams: ['title'],
        parameters: [
            { name: 'title', type: 'string', label: 'Playlist Title', required: true, placeholder: 'My Awesome Playlist' },
            { name: 'description', type: 'textarea', label: 'Description', placeholder: 'Playlist description...', required: false },
            {
                name: 'privacyStatus',
                type: 'select',
                label: 'Privacy Status',
                options: [
                    { value: 'private', label: 'Private' },
                    { value: 'public', label: 'Public' },
                    { value: 'unlisted', label: 'Unlisted' }
                ]
            },
            { name: 'tags', type: 'string', label: 'Tags', placeholder: 'music,rock,playlist', required: false },
            { name: 'defaultLanguage', type: 'string', label: 'Default Language', placeholder: 'en', required: false }
        ]
    },
    playlist_delete: {
        label: 'Delete Playlist',
        icon: Trash2,
        description: 'Delete a YouTube playlist',
        resource: 'playlist',
        requiredParams: ['playlistId'],
        parameters: [
            { name: 'playlistId', type: 'string', label: 'Playlist ID', required: true, placeholder: 'PLrAXtmRdnEQy4Qy9RMhfmIh2dpqy9tVy6' }
        ]
    },
    playlist_get: {
        label: 'Get Playlist',
        icon: List,
        description: 'Get details of a specific playlist',
        resource: 'playlist',
        requiredParams: ['playlistId'],
        parameters: [
            { name: 'playlistId', type: 'string', label: 'Playlist ID', required: true, placeholder: 'PLrAXtmRdnEQy4Qy9RMhfmIh2dpqy9tVy6' },
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,contentDetails',
                description: 'Comma-separated list of resource properties'
            }
        ]
    },
    playlist_getAll: {
        label: 'Get All Playlists',
        icon: List,
        description: 'List playlists with filtering options',
        resource: 'playlist',
        requiredParams: [],
        parameters: [
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,contentDetails',
                description: 'Comma-separated list of resource properties'
            },
            { name: 'maxResults', type: 'number', label: 'Max Results', placeholder: '25', min: 1, max: 50, required: false },
            { name: 'channelId', type: 'string', label: 'Channel ID Filter', placeholder: 'Filter by channel', required: false },
            { name: 'playlistId', type: 'string', label: 'Specific Playlist ID', placeholder: 'Get specific playlist', required: false }
        ]
    },
    playlist_update: {
        label: 'Update Playlist',
        icon: Edit,
        description: 'Update playlist metadata',
        resource: 'playlist',
        requiredParams: ['playlistId', 'title'],
        parameters: [
            { name: 'playlistId', type: 'string', label: 'Playlist ID', required: true, placeholder: 'PLrAXtmRdnEQy4Qy9RMhfmIh2dpqy9tVy6' },
            { name: 'title', type: 'string', label: 'Title', required: true, placeholder: 'Updated Playlist Title' },
            { name: 'description', type: 'textarea', label: 'Description', placeholder: 'Updated description...', required: false },
            {
                name: 'privacyStatus',
                type: 'select',
                label: 'Privacy Status',
                options: [
                    { value: 'private', label: 'Private' },
                    { value: 'public', label: 'Public' },
                    { value: 'unlisted', label: 'Unlisted' }
                ]
            },
            { name: 'tags', type: 'string', label: 'Tags', placeholder: 'music,rock,playlist', required: false },
            { name: 'defaultLanguage', type: 'string', label: 'Default Language', placeholder: 'en', required: false }
        ]
    },

    // Playlist Item Operations
    playlistItem_add: {
        label: 'Add to Playlist',
        icon: Plus,
        description: 'Add a video to a playlist',
        resource: 'playlistItem',
        requiredParams: ['playlistId', 'videoId'],
        parameters: [
            { name: 'playlistId', type: 'string', label: 'Playlist ID', required: true, placeholder: 'PLrAXtmRdnEQy4Qy9RMhfmIh2dpqy9tVy6' },
            { name: 'videoId', type: 'string', label: 'Video ID', required: true, placeholder: 'dQw4w9WgXcQ' },
            { name: 'position', type: 'number', label: 'Position', placeholder: '0 (beginning)', min: 0, required: false },
            { name: 'note', type: 'string', label: 'Note', placeholder: 'Optional note (max 280 chars)', required: false },
            { name: 'startAt', type: 'string', label: 'Start Time (seconds)', placeholder: '30', required: false },
            { name: 'endAt', type: 'string', label: 'End Time (seconds)', placeholder: '120', required: false }
        ]
    },
    playlistItem_delete: {
        label: 'Remove from Playlist',
        icon: Trash2,
        description: 'Remove a video from a playlist',
        resource: 'playlistItem',
        requiredParams: ['playlistItemId'],
        parameters: [
            { name: 'playlistItemId', type: 'string', label: 'Playlist Item ID', required: true, placeholder: 'UExBWHRtUmRuRVF5NFF5OVJNaGZtSWgyZHBxeTl0Vnk2LjVGRjMzNDFEQzJGNzU4OTI' }
        ]
    },
    playlistItem_get: {
        label: 'Get Playlist Item',
        icon: Eye,
        description: 'Get details of a specific playlist item',
        resource: 'playlistItem',
        requiredParams: ['playlistItemId'],
        parameters: [
            { name: 'playlistItemId', type: 'string', label: 'Playlist Item ID', required: true, placeholder: 'UExBWHRtUmRuRVF5NFF5OVJNaGZtSWgyZHBxeTl0Vnk2LjVGRjMzNDFEQzJGNzU4OTI' },
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,contentDetails',
                description: 'Comma-separated list of resource properties'
            }
        ]
    },
    playlistItem_getAll: {
        label: 'Get All Playlist Items',
        icon: List,
        description: 'Get all items from a playlist',
        resource: 'playlistItem',
        requiredParams: ['playlistId'],
        parameters: [
            { name: 'playlistId', type: 'string', label: 'Playlist ID', required: true, placeholder: 'PLrAXtmRdnEQy4Qy9RMhfmIh2dpqy9tVy6' },
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,contentDetails',
                description: 'Comma-separated list of resource properties'
            },
            { name: 'maxResults', type: 'number', label: 'Max Results', placeholder: '25', min: 1, max: 50 }
        ]
    },

    // Video Operations
    video_delete: {
        label: 'Delete Video',
        icon: Trash2,
        description: 'Delete a YouTube video',
        resource: 'video',
        requiredParams: ['videoId'],
        parameters: [
            { name: 'videoId', type: 'string', label: 'Video ID', required: true, placeholder: 'dQw4w9WgXcQ' }
        ]
    },
    video_get: {
        label: 'Get Video',
        icon: Video,
        description: 'Get details of a specific video',
        resource: 'video',
        requiredParams: ['videoId'],
        parameters: [
            { name: 'videoId', type: 'string', label: 'Video ID', required: true, placeholder: 'dQw4w9WgXcQ' },
            {
                name: 'part',
                type: 'string',
                label: 'Parts to Include',
                placeholder: 'snippet,statistics,contentDetails',
                description: 'Comma-separated list of resource properties'
            }
        ]
    },
    video_getAll: {
        label: 'Search Videos',
        icon: Search,
        description: 'Search for videos with various filters',
        resource: 'video',
        requiredParams: [],
        parameters: [
            { name: 'query', type: 'string', label: 'Search Query', placeholder: 'python tutorial', required: false },
            { name: 'maxResults', type: 'number', label: 'Max Results', placeholder: '25', min: 1, max: 50, required: false },
            { name: 'channelId', type: 'string', label: 'Channel ID Filter', placeholder: 'Filter by channel', required: false },
            {
                name: 'order',
                type: 'select',
                label: 'Sort Order',
                options: [
                    { value: 'relevance', label: 'Relevance' },
                    { value: 'date', label: 'Date' },
                    { value: 'rating', label: 'Rating' },
                    { value: 'title', label: 'Title' },
                    { value: 'viewCount', label: 'View Count' }
                ]
            },
            {
                name: 'safeSearch',
                type: 'select',
                label: 'Safe Search',
                options: [
                    { value: 'moderate', label: 'Moderate' },
                    { value: 'none', label: 'None' },
                    { value: 'strict', label: 'Strict' }
                ]
            },
            { name: 'regionCode', type: 'string', label: 'Region Code', placeholder: 'US', required: false },
            { name: 'publishedAfter', type: 'string', label: 'Published After', placeholder: '2023-01-01T00:00:00Z', required: false },
            { name: 'publishedBefore', type: 'string', label: 'Published Before', placeholder: '2023-12-31T23:59:59Z', required: false }
        ]
    },
    video_rate: {
        label: 'Rate Video',
        icon: ThumbsUp,
        description: 'Like, dislike, or remove rating from a video',
        resource: 'video',
        requiredParams: ['videoId', 'rating'],
        parameters: [
            { name: 'videoId', type: 'string', label: 'Video ID', required: true, placeholder: 'dQw4w9WgXcQ' },
            {
                name: 'rating',
                type: 'select',
                label: 'Rating',
                required: true,
                options: [
                    { value: 'like', label: 'Like' },
                    { value: 'dislike', label: 'Dislike' },
                    { value: 'none', label: 'Remove Rating' }
                ]
            }
        ]
    },
    video_update: {
        label: 'Update Video',
        icon: Edit,
        description: 'Update video metadata',
        resource: 'video',
        requiredParams: ['videoId', 'title', 'categoryId'],
        parameters: [
            { name: 'videoId', type: 'string', label: 'Video ID', required: true, placeholder: 'dQw4w9WgXcQ' },
            { name: 'title', type: 'string', label: 'Title', required: true, placeholder: 'Updated Video Title' },
            { name: 'categoryId', type: 'string', label: 'Category ID', required: true, placeholder: '22' },
            { name: 'description', type: 'textarea', label: 'Description', placeholder: 'Updated video description...', required: false },
            { name: 'tags', type: 'string', label: 'Tags', placeholder: 'tutorial,programming,python', required: false },
            {
                name: 'privacyStatus',
                type: 'select',
                label: 'Privacy Status',
                options: [
                    { value: 'private', label: 'Private' },
                    { value: 'public', label: 'Public' },
                    { value: 'unlisted', label: 'Unlisted' }
                ]
            },
            { name: 'defaultLanguage', type: 'string', label: 'Default Language', placeholder: 'en' },
            { name: 'embeddable', type: 'boolean', label: 'Embeddable' },
            { name: 'publicStatsViewable', type: 'boolean', label: 'Public Stats Viewable' },
            { name: 'selfDeclaredMadeForKids', type: 'boolean', label: 'Made for Kids' }
        ]
    },
    video_upload: {
        label: 'Upload Video',
        icon: Upload,
        description: 'Upload a new video to YouTube',
        resource: 'video',
        requiredParams: ['title', 'categoryId', 'binaryProperty'],
        parameters: [
            { name: 'title', type: 'string', label: 'Title', required: true, placeholder: 'My New Video' },
            { name: 'categoryId', type: 'string', label: 'Category ID', required: true, placeholder: '22' },
            { name: 'binaryProperty', type: 'string', label: 'Binary Property Name', required: true, placeholder: 'data' },
            { name: 'description', type: 'textarea', label: 'Description', placeholder: 'Video description...' },
            { name: 'tags', type: 'string', label: 'Tags', placeholder: 'tutorial,programming,python' },
            {
                name: 'privacyStatus',
                type: 'select',
                label: 'Privacy Status',
                options: [
                    { value: 'private', label: 'Private' },
                    { value: 'public', label: 'Public' },
                    { value: 'unlisted', label: 'Unlisted' }
                ]
            },
            { name: 'defaultLanguage', type: 'string', label: 'Default Language', placeholder: 'en' },
            { name: 'embeddable', type: 'boolean', label: 'Embeddable' },
            { name: 'publicStatsViewable', type: 'boolean', label: 'Public Stats Viewable' },
            { name: 'selfDeclaredMadeForKids', type: 'boolean', label: 'Made for Kids' },
            { name: 'notifySubscribers', type: 'boolean', label: 'Notify Subscribers' }
        ]
    },

    // Video Category Operations
    videoCategory_getAll: {
        label: 'Get Video Categories',
        icon: List,
        description: 'Get available video categories for a region',
        resource: 'videoCategory',
        requiredParams: ['regionCode'],
        parameters: [
            { name: 'regionCode', type: 'string', label: 'Region Code', required: true, placeholder: 'US' },
            { name: 'maxResults', type: 'number', label: 'Max Results', placeholder: '25', min: 1, max: 50 }
        ]
    }
};

export function YouTubeConnectorModal({ isOpen, onClose, onSave, initialData }: YouTubeConnectorModalProps) {
    const { user } = useAuth();
    const [selectedAction, setSelectedAction] = useState<string>('video_getAll');
    const [parameters, setParameters] = useState<Record<string, any>>({});
    const [authConfig, setAuthConfig] = useState({
        access_token: '',
        refresh_token: ''
    });
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [activeTab, setActiveTab] = useState('action');

    const currentAction = YOUTUBE_ACTIONS[selectedAction as keyof typeof YOUTUBE_ACTIONS];

    useEffect(() => {
        if (selectedAction) {
            // Reset parameters when action changes
            const newParams: Record<string, any> = {};
            currentAction?.parameters?.forEach(param => {
                if (param.type === 'boolean') {
                    newParams[param.name] = false;
                } else if (param.placeholder && !param.required) {
                    newParams[param.name] = '';
                }
            });
            setParameters(newParams);
        }
    }, [selectedAction]);

    // Populate form with AI-generated parameters
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            console.log('🤖 YouTube Modal: Received AI-generated parameters:', initialData);
            
            // Update parameters with AI-generated data
            setParameters(prev => ({
                ...prev,
                ...initialData
            }));

            // Set the action if provided in initialData
            if (initialData.action) {
                setSelectedAction(initialData.action);
            }
        }
    }, [initialData]);

    const handleParameterChange = (paramName: string, value: any) => {
        setParameters(prev => ({
            ...prev,
            [paramName]: value
        }));
    };

    const handleTestConnection = async () => {
        setIsLoading(true);
        setTestResult(null);

        try {
            // Simulate connection test
            await new Promise(resolve => setTimeout(resolve, 1500));

            if (!authConfig.access_token) {
                setTestResult({
                    success: false,
                    message: 'Access token is required for YouTube API authentication'
                });
                return;
            }

            setTestResult({
                success: true,
                message: 'Successfully connected to YouTube API! Ready to perform operations.'
            });
        } catch (error) {
            setTestResult({
                success: false,
                message: 'Failed to connect to YouTube API. Please check your credentials.'
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        setIsLoading(true);

        try {
            const config: YouTubeConfig = {
                name: 'youtube',
                display_name: 'YouTube',
                description: 'YouTube API integration for video and channel management',
                auth_type: 'oauth',
                auth_config: {
                    access_token: authConfig.access_token,
                    refresh_token: authConfig.refresh_token,
                    scopes: [
                        'https://www.googleapis.com/auth/youtube',
                        'https://www.googleapis.com/auth/youtube.upload',
                        'https://www.googleapis.com/auth/youtube.readonly'
                    ]
                },
                settings: {
                    resource: currentAction?.resource || 'video',
                    operation: selectedAction,
                    ...parameters
                },
                status: authConfig.access_token ? 'configured' : 'needs_auth'
            };

            await onSave(config);
            onClose();
        } catch (error) {
            console.error('Failed to save YouTube configuration:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const renderParameterField = (param: ActionParameter) => {
        const value = parameters[param.name] || '';

        switch (param.type) {
            case 'select':
                return (
                    <Select value={value} onValueChange={(val) => handleParameterChange(param.name, val)}>
                        <SelectTrigger>
                            <SelectValue placeholder={`Select ${param.label}`} />
                        </SelectTrigger>
                        <SelectContent>
                            {param.options?.map((option: any) => (
                                <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                );
            case 'textarea':
                return (
                    <Textarea
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.placeholder}
                        rows={3}
                    />
                );
            case 'boolean':
                return (
                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            id={param.name}
                            checked={value}
                            onChange={(e) => handleParameterChange(param.name, e.target.checked)}
                            className="rounded border-gray-300"
                        />
                        <Label htmlFor={param.name}>Enable</Label>
                    </div>
                );
            case 'number':
                return (
                    <Input
                        type="number"
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, parseInt(e.target.value) || '')}
                        placeholder={param.placeholder}
                        min={param.min}
                        max={param.max}
                    />
                );
            default:
                return (
                    <Input
                        type="text"
                        value={value}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.placeholder}
                    />
                );
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Youtube className="h-5 w-5 text-red-600" />
                        YouTube Connector Configuration
                    </DialogTitle>
                    <DialogDescription>
                        Configure YouTube API integration for video and channel management operations.
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="action">Action & Parameters</TabsTrigger>
                        <TabsTrigger value="auth">Authentication</TabsTrigger>
                        <TabsTrigger value="test">Test & Validate</TabsTrigger>
                    </TabsList>

                    <TabsContent value="action" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Settings className="h-4 w-4" />
                                    YouTube Operation
                                </CardTitle>
                                <CardDescription>
                                    Select the YouTube operation you want to perform
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div>
                                    <Label htmlFor="action-select">YouTube Action</Label>
                                    <Select value={selectedAction} onValueChange={setSelectedAction}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select YouTube action" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <div className="p-2 text-sm font-medium text-gray-500">Channel Operations</div>
                                            {Object.entries(YOUTUBE_ACTIONS)
                                                .filter(([_, action]) => action.resource === 'channel')
                                                .map(([key, action]) => (
                                                    <SelectItem key={key} value={key}>
                                                        <div className="flex items-center gap-2">
                                                            <action.icon className="h-4 w-4" />
                                                            {action.label}
                                                        </div>
                                                    </SelectItem>
                                                ))}

                                            <Separator className="my-2" />
                                            <div className="p-2 text-sm font-medium text-gray-500">Playlist Operations</div>
                                            {Object.entries(YOUTUBE_ACTIONS)
                                                .filter(([_, action]) => action.resource === 'playlist')
                                                .map(([key, action]) => (
                                                    <SelectItem key={key} value={key}>
                                                        <div className="flex items-center gap-2">
                                                            <action.icon className="h-4 w-4" />
                                                            {action.label}
                                                        </div>
                                                    </SelectItem>
                                                ))}

                                            <Separator className="my-2" />
                                            <div className="p-2 text-sm font-medium text-gray-500">Playlist Item Operations</div>
                                            {Object.entries(YOUTUBE_ACTIONS)
                                                .filter(([_, action]) => action.resource === 'playlistItem')
                                                .map(([key, action]) => (
                                                    <SelectItem key={key} value={key}>
                                                        <div className="flex items-center gap-2">
                                                            <action.icon className="h-4 w-4" />
                                                            {action.label}
                                                        </div>
                                                    </SelectItem>
                                                ))}

                                            <Separator className="my-2" />
                                            <div className="p-2 text-sm font-medium text-gray-500">Video Operations</div>
                                            {Object.entries(YOUTUBE_ACTIONS)
                                                .filter(([_, action]) => action.resource === 'video')
                                                .map(([key, action]) => (
                                                    <SelectItem key={key} value={key}>
                                                        <div className="flex items-center gap-2">
                                                            <action.icon className="h-4 w-4" />
                                                            {action.label}
                                                        </div>
                                                    </SelectItem>
                                                ))}

                                            <Separator className="my-2" />
                                            <div className="p-2 text-sm font-medium text-gray-500">Video Category Operations</div>
                                            {Object.entries(YOUTUBE_ACTIONS)
                                                .filter(([_, action]) => action.resource === 'videoCategory')
                                                .map(([key, action]) => (
                                                    <SelectItem key={key} value={key}>
                                                        <div className="flex items-center gap-2">
                                                            <action.icon className="h-4 w-4" />
                                                            {action.label}
                                                        </div>
                                                    </SelectItem>
                                                ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {currentAction && (
                                    <Alert>
                                        <Info className="h-4 w-4" />
                                        <AlertDescription>
                                            <strong>{currentAction.label}:</strong> {currentAction.description}
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>

                        {currentAction && currentAction.parameters && currentAction.parameters.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Parameters</CardTitle>
                                    <CardDescription>
                                        Configure the parameters for the selected YouTube operation
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {currentAction.parameters.map((param) => (
                                        <div key={param.name} className="space-y-2">
                                            <Label htmlFor={param.name} className="flex items-center gap-2">
                                                {param.label}
                                                {param.required && <Badge variant="destructive" className="text-xs">Required</Badge>}
                                            </Label>
                                            {renderParameterField(param)}
                                            {param.description && (
                                                <p className="text-sm text-gray-500">{param.description}</p>
                                            )}
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    <TabsContent value="auth" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Key className="h-4 w-4" />
                                    OAuth2 Authentication
                                </CardTitle>
                                <CardDescription>
                                    Configure YouTube API OAuth2 credentials for secure access
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Alert>
                                    <Info className="h-4 w-4" />
                                    <AlertDescription>
                                        YouTube API requires OAuth2 authentication. You'll need to obtain access tokens through the Google OAuth2 flow.
                                        Required scopes: youtube, youtube.upload, youtube.readonly
                                    </AlertDescription>
                                </Alert>

                                <div className="space-y-2">
                                    <Label htmlFor="access_token">Access Token *</Label>
                                    <Input
                                        id="access_token"
                                        type="password"
                                        value={authConfig.access_token}
                                        onChange={(e) => setAuthConfig(prev => ({ ...prev, access_token: e.target.value }))}
                                        placeholder="Enter your YouTube API access token"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="refresh_token">Refresh Token</Label>
                                    <Input
                                        id="refresh_token"
                                        type="password"
                                        value={authConfig.refresh_token}
                                        onChange={(e) => setAuthConfig(prev => ({ ...prev, refresh_token: e.target.value }))}
                                        placeholder="Enter your refresh token (optional)"
                                    />
                                </div>

                                <div className="bg-blue-50 p-4 rounded-lg">
                                    <h4 className="font-medium text-blue-900 mb-2">OAuth2 Setup Instructions:</h4>
                                    <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                                        <li>Go to the Google Cloud Console</li>
                                        <li>Create or select a project</li>
                                        <li>Enable the YouTube Data API v3</li>
                                        <li>Create OAuth2 credentials</li>
                                        <li>Use the OAuth2 flow to obtain access tokens</li>
                                    </ol>
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
                                    Verify your YouTube API configuration and credentials
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Button
                                    onClick={handleTestConnection}
                                    disabled={isLoading || !authConfig.access_token}
                                    className="w-full"
                                >
                                    {isLoading ? 'Testing Connection...' : 'Test YouTube API Connection'}
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

                                <div className="bg-gray-50 p-4 rounded-lg">
                                    <h4 className="font-medium mb-2">Configuration Summary:</h4>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span>Selected Action:</span>
                                            <Badge variant="outline">{currentAction?.label || 'None'}</Badge>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Resource Type:</span>
                                            <Badge variant="outline">{currentAction?.resource || 'None'}</Badge>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Authentication:</span>
                                            <Badge variant={authConfig.access_token ? 'default' : 'destructive'}>
                                                {authConfig.access_token ? 'Configured' : 'Missing'}
                                            </Badge>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Required Parameters:</span>
                                            <Badge variant="outline">
                                                {currentAction?.requiredParams?.length || 0} required
                                            </Badge>
                                        </div>
                                    </div>
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
                        disabled={isLoading || !authConfig.access_token}
                        className="bg-red-600 hover:bg-red-700"
                    >
                        <Save className="h-4 w-4 mr-2" />
                        {isLoading ? 'Saving...' : 'Save Configuration'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}