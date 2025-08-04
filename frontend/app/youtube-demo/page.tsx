"use client";

import React from 'react';
import { YouTubeConnector } from '@/components/connectors/youtube';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Youtube, Zap, Code, Settings } from 'lucide-react';

export default function YouTubeDemoPage() {
    const handleConfigured = (config: any) => {
        console.log('YouTube connector configured:', config);
    };

    return (
        <div className="container mx-auto py-8 px-4">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-3 bg-red-100 rounded-lg">
                        <Youtube className="h-8 w-8 text-red-600" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold">YouTube Connector Demo</h1>
                        <p className="text-gray-600">
                            Test and configure the YouTube API integration for PromptFlow AI
                        </p>
                    </div>
                </div>

                <div className="flex gap-2">
                    <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                        <Youtube className="h-3 w-3 mr-1" />
                        YouTube API v3
                    </Badge>
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <Zap className="h-3 w-3 mr-1" />
                        OAuth2 Ready
                    </Badge>
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        <Code className="h-3 w-3 mr-1" />
                        20 Operations
                    </Badge>
                    <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                        <Settings className="h-3 w-3 mr-1" />
                        Production Ready
                    </Badge>
                </div>
            </div>

            {/* Demo Info */}
            <Card className="mb-8">
                <CardHeader>
                    <CardTitle>Demo Information</CardTitle>
                    <CardDescription>
                        This demo showcases the YouTube connector's capabilities and configuration interface
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-4 bg-red-50 rounded-lg">
                            <h3 className="font-medium text-red-900 mb-2">🎬 Video Operations</h3>
                            <p className="text-sm text-red-700">
                                Upload, update, delete, search, and manage YouTube videos with full metadata support
                            </p>
                        </div>
                        <div className="p-4 bg-blue-50 rounded-lg">
                            <h3 className="font-medium text-blue-900 mb-2">📺 Channel Management</h3>
                            <p className="text-sm text-blue-700">
                                Manage channel settings, upload banners, and access channel analytics
                            </p>
                        </div>
                        <div className="p-4 bg-green-50 rounded-lg">
                            <h3 className="font-medium text-green-900 mb-2">📋 Playlist Control</h3>
                            <p className="text-sm text-green-700">
                                Create, update, and manage playlists with full video organization capabilities
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* YouTube Connector Component */}
            <YouTubeConnector onConfigured={handleConfigured} />

            {/* Footer */}
            <Card className="mt-8">
                <CardContent className="pt-6">
                    <div className="text-center text-sm text-gray-500">
                        <p>
                            YouTube Connector Demo - Part of PromptFlow AI Platform
                        </p>
                        <p className="mt-1">
                            Configure the connector above to test YouTube API integration
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}