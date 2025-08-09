'use client';

import React, { useState } from 'react';
import { GoogleTranslateConnector, GoogleTranslateConnectorModal } from '@/components/connectors/google_translate';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Languages, ArrowLeft, Globe, Zap, Shield, Clock } from 'lucide-react';
import Link from 'next/link';

export default function GoogleTranslateDemoPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [connectorConfig, setConnectorConfig] = useState({
    operation: 'translate',
    text: 'Hello, welcome to our platform!',
    target_language: 'es',
    source_language: 'auto',
    format: 'text',
    model: 'nmt'
  });

  const handleSave = (config: any) => {
    setConnectorConfig(config);
    console.log('Google Translate configuration saved:', config);
  };

  const handleTest = () => {
    console.log('Testing Google Translate connector with config:', connectorConfig);
    alert('Test functionality would connect to Google Translate API here');
  };

  const features = [
    {
      icon: <Globe className="h-5 w-5 text-blue-600" />,
      title: '100+ Languages',
      description: 'Support for over 100 languages with automatic detection'
    },
    {
      icon: <Zap className="h-5 w-5 text-green-600" />,
      title: 'Neural Translation',
      description: 'Advanced neural machine translation for better accuracy'
    },
    {
      icon: <Shield className="h-5 w-5 text-purple-600" />,
      title: 'Secure OAuth',
      description: 'Secure Google OAuth2 authentication with proper scopes'
    },
    {
      icon: <Clock className="h-5 w-5 text-orange-600" />,
      title: 'Real-time',
      description: 'Fast, real-time translation with minimal latency'
    }
  ];

  const useCases = [
    {
      title: 'Content Localization',
      description: 'Translate website content, documentation, and marketing materials',
      example: 'Translate product descriptions for international markets'
    },
    {
      title: 'Customer Support',
      description: 'Provide multilingual customer support and communication',
      example: 'Translate customer inquiries and support responses'
    },
    {
      title: 'Document Processing',
      description: 'Process and translate documents in various formats',
      example: 'Translate legal documents, contracts, and reports'
    },
    {
      title: 'Social Media',
      description: 'Translate social media posts and user-generated content',
      example: 'Translate comments and posts for global engagement'
    }
  ];

  const examples = [
    {
      title: 'English to Spanish',
      original: 'Hello, how are you today?',
      translated: 'Hola, ¿cómo estás hoy?',
      languages: 'EN → ES'
    },
    {
      title: 'French to English',
      original: 'Bonjour, comment allez-vous?',
      translated: 'Hello, how are you?',
      languages: 'FR → EN'
    },
    {
      title: 'German to Chinese',
      original: 'Guten Tag, wie geht es Ihnen?',
      translated: '你好，你好吗？',
      languages: 'DE → ZH'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Languages className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Google Translate</h1>
                  <p className="text-sm text-gray-500">Text Translation Connector</p>
                </div>
              </div>
            </div>
            <Badge variant="outline" className="text-blue-600 border-blue-200">
              Utility Connector
            </Badge>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Connector Demo */}
            <Card>
              <CardHeader>
                <CardTitle>Connector Demo</CardTitle>
                <p className="text-sm text-gray-600">
                  Interactive demo of the Google Translate connector component
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex justify-center">
                  <GoogleTranslateConnector
                    config={connectorConfig}
                    onConfigure={() => setIsModalOpen(true)}
                    onTest={handleTest}
                    isConfigured={!!connectorConfig.text && !!connectorConfig.target_language}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Features */}
            <Card>
              <CardHeader>
                <CardTitle>Key Features</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {features.map((feature, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-shrink-0">
                        {feature.icon}
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">{feature.title}</h3>
                        <p className="text-sm text-gray-600 mt-1">{feature.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Translation Examples */}
            <Card>
              <CardHeader>
                <CardTitle>Translation Examples</CardTitle>
                <p className="text-sm text-gray-600">
                  See how Google Translate handles different language pairs
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {examples.map((example, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-medium text-gray-900">{example.title}</h3>
                        <Badge variant="outline" className="text-blue-600">
                          {example.languages}
                        </Badge>
                      </div>
                      <div className="space-y-2">
                        <div>
                          <span className="text-sm font-medium text-gray-700">Original:</span>
                          <p className="text-sm text-gray-600 mt-1 p-2 bg-gray-50 rounded">
                            {example.original}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-700">Translation:</span>
                          <p className="text-sm text-blue-600 mt-1 p-2 bg-blue-50 rounded font-medium">
                            {example.translated}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Use Cases */}
            <Card>
              <CardHeader>
                <CardTitle>Use Cases</CardTitle>
                <p className="text-sm text-gray-600">
                  Common scenarios where Google Translate connector adds value
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {useCases.map((useCase, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-2">{useCase.title}</h3>
                      <p className="text-sm text-gray-600 mb-3">{useCase.description}</p>
                      <div className="bg-blue-50 p-2 rounded text-xs text-blue-700">
                        <strong>Example:</strong> {useCase.example}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => setIsModalOpen(true)}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  Configure Connector
                </Button>
                <Button
                  onClick={handleTest}
                  variant="outline"
                  className="w-full"
                  disabled={!connectorConfig.text || !connectorConfig.target_language}
                >
                  Test Translation
                </Button>
              </CardContent>
            </Card>

            {/* Configuration Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Current Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Operation:</span>
                    <Badge variant="outline">Translate</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Target Language:</span>
                    <Badge variant="outline" className="text-blue-600">
                      {connectorConfig.target_language?.toUpperCase() || 'Not set'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Source Language:</span>
                    <Badge variant="outline" className="text-gray-600">
                      {connectorConfig.source_language === 'auto' ? 'Auto-detect' : connectorConfig.source_language?.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Model:</span>
                    <Badge variant="outline" className="text-purple-600">
                      {connectorConfig.model === 'nmt' ? 'Neural MT' : 'Base'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Format:</span>
                    <Badge variant="outline" className="text-orange-600">
                      {connectorConfig.format?.toUpperCase()}
                    </Badge>
                  </div>
                </div>
                {connectorConfig.text && (
                  <div className="mt-3 pt-3 border-t">
                    <span className="text-sm font-medium text-gray-700">Sample Text:</span>
                    <p className="text-sm text-gray-600 mt-1 p-2 bg-gray-50 rounded">
                      {connectorConfig.text.length > 100 
                        ? `${connectorConfig.text.substring(0, 100)}...` 
                        : connectorConfig.text}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Technical Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Technical Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <span className="font-medium">API:</span>
                  <p className="text-gray-600">Google Cloud Translation API v2</p>
                </div>
                <div>
                  <span className="font-medium">Authentication:</span>
                  <p className="text-gray-600">OAuth2 with cloud-translation scope</p>
                </div>
                <div>
                  <span className="font-medium">Rate Limits:</span>
                  <p className="text-gray-600">Based on Google Cloud quotas</p>
                </div>
                <div>
                  <span className="font-medium">Supported Formats:</span>
                  <p className="text-gray-600">Plain text, HTML</p>
                </div>
                <div>
                  <span className="font-medium">Languages:</span>
                  <p className="text-gray-600">100+ languages supported</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Configuration Modal */}
      <GoogleTranslateConnectorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        initialConfig={connectorConfig}
      />
    </div>
  );
}