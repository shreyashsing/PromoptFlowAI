"use client";

import React, { useState } from 'react';
import { NotionConnector } from './NotionConnector';
import { NotionConnectorModal } from './NotionConnectorModal';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function NotionConnectorTest() {
    const [showConnector, setShowConnector] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [config, setConfig] = useState(null);

    const handleConfigChange = (newConfig: any) => {
        setConfig(newConfig);
        console.log('Config updated:', newConfig);
    };

    const handleModalSave = async (newConfig: any) => {
        setConfig(newConfig);
        console.log('Modal config saved:', newConfig);
    };

    return (
        <div className="p-6 space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Notion Connector Test</CardTitle>
                    <CardDescription>
                        Test the Notion connector components
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex gap-4">
                        <Button 
                            onClick={() => setShowConnector(!showConnector)}
                            variant={showConnector ? "secondary" : "default"}
                        >
                            {showConnector ? 'Hide' : 'Show'} Notion Connector
                        </Button>
                        <Button 
                            onClick={() => setShowModal(true)}
                            variant="outline"
                        >
                            Open Configuration Modal
                        </Button>
                    </div>

                    {config && (
                        <div className="p-4 bg-gray-50 rounded-lg">
                            <h4 className="font-medium mb-2">Current Configuration:</h4>
                            <pre className="text-sm overflow-auto">
                                {JSON.stringify(config, null, 2)}
                            </pre>
                        </div>
                    )}
                </CardContent>
            </Card>

            {showConnector && (
                <NotionConnector 
                    onConfigChange={handleConfigChange}
                    initialConfig={config}
                />
            )}

            <NotionConnectorModal
                isOpen={showModal}
                onClose={() => setShowModal(false)}
                onSave={handleModalSave}
            />
        </div>
    );
}