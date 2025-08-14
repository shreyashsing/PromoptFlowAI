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
import { DynamicSelect } from '@/components/ui/dynamic-select';
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
    initialConfig?: Partial<YouTubeConfig>; // Saved configuration
    initialData?: any; // AI-generated parameters
    mode?: 'create' | 'edit';
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

export function YouTubeConnectorModal({
    isOpen,
    onClose,
    onSave,
    initialConfig,
    initialData,
    mode = 'create'
}: YouTubeConnectorModalProps) {
    const { user, session } = useAuth();
    const [selectedAction, setSelectedAction] = useState<string>('video_getAll');
    const [parameters, setParameters] = useState<Record<string, any>>({});
    const [authConfig, setAuthConfig] = useState({
        access_token: '',
        refresh_token: ''
    });
    const [isLoading, setIsLoading] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [activeTab, setActiveTab] = useState('action');
    const [authStatus, setAuthStatus] = useState<'none' | 'authenticated' | 'error'>('none');

    // Check authentication status
    const checkAuthStatus = async () => {
        if (!session?.access_token) {
            console.log('🔐 YouTube Modal: No session token available');
            return;
        }

        console.log('🔐 YouTube Modal: Checking authentication status...');

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
                const tokens = await response.json();
                console.log('🔐 YouTube Modal: Retrieved tokens:', Object.keys(tokens));

                // Check for YouTube-specific token in the tokens array
                const tokensList = tokens.tokens || [];

                const youtubeTokenRecord = tokensList.find((token: any) => {
                    const isYoutube = token.connector_name === 'youtube';
                    const isOAuth = token.token_type?.toLowerCase() === 'oauth2' ||
                        token.token_type === 'OAUTH2' ||
                        token.token_type === 'oauth';
                    return isYoutube && isOAuth;
                });

                if (youtubeTokenRecord) {
                    console.log('🔐 YouTube Modal: Found valid YouTube token');
                    setAuthStatus('authenticated');
                    // Note: We don't set the actual token values here since they're encrypted
                    // The actual tokens will be retrieved by the backend when needed
                } else {
                    console.log('🔐 YouTube Modal: No valid YouTube token found');
                    console.log('🔐 YouTube Modal: Available tokens:', tokensList.map((t: any) => ({ name: t.connector_name, type: t.token_type })));
                    setAuthStatus('none');
                }
            } else {
                console.error('🔐 YouTube Modal: Failed to check auth status:', response.status);
                setAuthStatus('none');
            }
        } catch (error) {
            console.error('🔐 YouTube Modal: Error checking auth status:', error);
            setAuthStatus('none');
        }
    };

    // Initialize configuration - reload every time modal opens with saved config
    useEffect(() => {
        if (isOpen && initialConfig) {
            console.log('🔄 YouTube Modal: Loading saved configuration:', initialConfig);

            // Load saved parameters from settings
            if (initialConfig.settings) {
                console.log('🔄 YouTube Modal: Loading saved parameters:', initialConfig.settings);
                setParameters(prev => ({ ...prev, ...initialConfig.settings }));

                // Update selected action if available
                if (initialConfig.settings.operation) {
                    setSelectedAction(initialConfig.settings.operation);
                }
            }

            // Load auth config if available
            if (initialConfig.auth_config) {
                setAuthConfig(prev => ({ ...prev, ...initialConfig.auth_config }));
                if (initialConfig.auth_config.access_token) {
                    setAuthStatus('authenticated');
                }
            }
        }
    }, [isOpen, initialConfig]);

    // Check authentication status when modal opens
    useEffect(() => {
        if (isOpen) {
            console.log('🔐 YouTube Modal: Modal opened, checking auth status');
            checkAuthStatus();
        }
    }, [isOpen]);

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
            if (initialData.operation || initialData.action) {
                setSelectedAction(initialData.operation || initialData.action);
            }
        }
    }, [initialData]);

    const handleParameterChange = (paramName: string, value: any) => {
        setParameters(prev => ({
            ...prev,
            [paramName]: value
        }));
    };

    const handleOAuthConnect = async () => {
        setIsLoading(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/oauth/initiate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({
                    connector_name: 'youtube',
                    redirect_uri: `${window.location.origin}/auth/oauth/callback`
                })
            });

            if (!response.ok) {
                throw new Error(`OAuth initiate failed: ${response.status}`);
            }

            const { authorization_url, state } = await response.json();

            // Store OAuth state and connector name for callback
            localStorage.setItem('oauth_state', state);
            localStorage.setItem('oauth_connector', 'youtube');

            // Open OAuth popup
            const popup = window.open(authorization_url, 'oauth', 'width=500,height=600');

            if (popup) {
                // Listen for messages from the popup
                const handleMessage = (event: MessageEvent) => {
                    if (event.origin !== window.location.origin) return;

                    if (event.data.type === 'OAUTH_SUCCESS' || event.data.type === 'OAUTH_ERROR') {
                        window.removeEventListener('message', handleMessage);
                        setTimeout(() => {
                            console.log('🔐 YouTube Modal: OAuth completed, checking auth status');
                            checkAuthStatus();
                        }, 2000); // Increased delay to allow database commit
                    }
                };

                window.addEventListener('message', handleMessage);

                // Fallback: Check if popup is closed (may not work due to CORS)
                const checkClosed = setInterval(() => {
                    try {
                        if (popup.closed) {
                            clearInterval(checkClosed);
                            window.removeEventListener('message', handleMessage);
                            setTimeout(() => {
                                console.log('🔐 YouTube Modal: OAuth popup closed, checking auth status');
                                checkAuthStatus();
                            }, 2000); // Increased delay to allow database commit
                        }
                    } catch (error) {
                        // Ignore CORS errors, rely on message-based approach
                    }
                }, 1000);

                // Cleanup after 5 minutes
                setTimeout(() => {
                    clearInterval(checkClosed);
                    window.removeEventListener('message', handleMessage);
                }, 300000);
            }
        } catch (error) {
            console.error('OAuth error:', error);
            setAuthStatus('error');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDisconnect = async () => {
        setIsLoading(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/auth/oauth/disconnect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({ connector_name: 'youtube' })
            });

            if (response.ok) {
                setAuthStatus('none');
                setAuthConfig({ access_token: '', refresh_token: '' });
                console.log('🔐 YouTube: Successfully disconnected');
            } else {
                console.error('Failed to disconnect:', response.status);
            }
        } catch (error) {
            console.error('Disconnect error:', error);
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
        setTestResult(null);

        try {
            // Test connection by calling the backend YouTube connector test
            const response = await fetch('/api/v1/connectors/youtube/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({
                    resource: 'channel',
                    operation: 'channel_getAll',
                    part: ['snippet'],
                    maxResults: 1
                })
            });

            if (response.ok) {
                const data = await response.json();
                setTestResult({
                    success: true,
                    message: 'Successfully connected to YouTube API! Connection test passed.'
                });
            } else {
                const errorData = await response.json().catch(() => ({}));
                setTestResult({
                    success: false,
                    message: `Failed to connect to YouTube API: ${errorData.detail || 'Unknown error'}`
                });
            }
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
                    // Token data is stored encrypted in the backend
                    // We don't store actual tokens in the frontend for security
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
                status: authStatus === 'authenticated' ? 'configured' : 'needs_auth'
            };

            console.log('🔄 YouTube Modal: Saving configuration:', config);
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
                // Check if this field should use dynamic data
                if (param.name === 'videoId') {
                    return (
                        <DynamicSelect
                            connectorName="youtube"
                            fieldName="video_id"
                            value={value}
                            onValueChange={(val) => handleParameterChange(param.name, val)}
                            placeholder="Select a YouTube video..."
                            searchable={true}
                        />
                    );
                } else if (param.name === 'playlistId') {
                    return (
                        <DynamicSelect
                            connectorName="youtube"
                            fieldName="playlist_id"
                            value={value}
                            onValueChange={(val) => handleParameterChange(param.name, val)}
                            placeholder="Select a YouTube playlist..."
                            searchable={true}
                        />
                    );
                } else if (param.name === 'channelId') {
                    return (
                        <DynamicSelect
                            connectorName="youtube"
                            fieldName="channel_id"
                            value={value}
                            onValueChange={(val) => handleParameterChange(param.name, val)}
                            placeholder="Select a YouTube channel..."
                            searchable={true}
                        />
                    );
                }

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
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="action">Action & Parameters</TabsTrigger>
                        <TabsTrigger value="auth">Authentication</TabsTrigger>

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
                                    YouTube Authentication
                                </CardTitle>
                                <CardDescription>
                                    Connect your YouTube account to access videos, channels, and playlists
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {/* Authentication Status Display */}
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
                                                {authStatus === 'authenticated' ? 'Connected to YouTube' :
                                                    authStatus === 'error' ? 'Authentication Error' :
                                                        'Not Connected'}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {authStatus === 'authenticated' ? 'You can access your YouTube content' :
                                                    authStatus === 'error' ? 'Please try authenticating again' :
                                                        'Connect to access your YouTube account'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex space-x-2">
                                        {authStatus === 'authenticated' ? (
                                            <>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={handleTestConnection}
                                                    disabled={isLoading}
                                                >
                                                    <TestTube className="h-4 w-4 mr-2" />
                                                    Test
                                                </Button>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={handleDisconnect}
                                                    disabled={isLoading}
                                                >
                                                    Disconnect
                                                </Button>
                                            </>
                                        ) : (
                                            <>
                                                <Button
                                                    onClick={handleOAuthConnect}
                                                    disabled={isLoading}
                                                    size="sm"
                                                >
                                                    <Youtube className="h-4 w-4 mr-2" />
                                                    Connect YouTube
                                                </Button>
                                                <Button
                                                    variant="outline"
                                                    onClick={checkAuthStatus}
                                                    disabled={isLoading}
                                                    size="sm"
                                                >
                                                    Refresh Status
                                                </Button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Test Results */}
                                {testResult && (
                                    <Alert className={testResult.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
                                        {testResult.success ? (
                                            <CheckCircle className="h-4 w-4 text-green-600" />
                                        ) : (
                                            <XCircle className="h-4 w-4 text-red-600" />
                                        )}
                                        <AlertDescription className={testResult.success ? "text-green-800" : "text-red-800"}>
                                            {testResult.message}
                                        </AlertDescription>
                                    </Alert>
                                )}

                                {/* OAuth Setup Instructions */}
                                <div className="bg-blue-50 p-4 rounded-lg">
                                    <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                                        <Info className="h-4 w-4" />
                                        OAuth2 Setup Instructions:
                                    </h4>
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


                </Tabs>

                <div className="flex justify-end gap-2 pt-4 border-t">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={authStatus !== 'authenticated'}
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