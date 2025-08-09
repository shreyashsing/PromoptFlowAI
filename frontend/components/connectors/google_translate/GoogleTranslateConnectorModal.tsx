'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Languages, Globe, Settings, TestTube, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface GoogleTranslateConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: any) => void;
  initialConfig?: any;
}

export function GoogleTranslateConnectorModal({
  isOpen,
  onClose,
  onSave,
  initialConfig = {}
}: GoogleTranslateConnectorModalProps) {
  const [config, setConfig] = useState({
    operation: 'translate',
    text: '',
    target_language: '',
    source_language: 'auto',
    format: 'text',
    model: 'nmt',
    ...initialConfig
  });

  const [authConfig, setAuthConfig] = useState({
    access_token: '',
    ...initialConfig.auth
  });

  const [testResult, setTestResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialConfig) {
      setConfig(prev => ({ ...prev, ...initialConfig }));
      if (initialConfig.auth) {
        setAuthConfig(prev => ({ ...prev, ...initialConfig.auth }));
      }
    }
  }, [initialConfig]);

  const languages = [
    { value: 'af', label: 'Afrikaans' },
    { value: 'sq', label: 'Albanian' },
    { value: 'am', label: 'Amharic' },
    { value: 'ar', label: 'Arabic' },
    { value: 'hy', label: 'Armenian' },
    { value: 'az', label: 'Azerbaijani' },
    { value: 'eu', label: 'Basque' },
    { value: 'be', label: 'Belarusian' },
    { value: 'bn', label: 'Bengali' },
    { value: 'bs', label: 'Bosnian' },
    { value: 'bg', label: 'Bulgarian' },
    { value: 'ca', label: 'Catalan' },
    { value: 'ceb', label: 'Cebuano' },
    { value: 'ny', label: 'Chichewa' },
    { value: 'zh-cn', label: 'Chinese (Simplified)' },
    { value: 'zh-tw', label: 'Chinese (Traditional)' },
    { value: 'co', label: 'Corsican' },
    { value: 'hr', label: 'Croatian' },
    { value: 'cs', label: 'Czech' },
    { value: 'da', label: 'Danish' },
    { value: 'nl', label: 'Dutch' },
    { value: 'en', label: 'English' },
    { value: 'eo', label: 'Esperanto' },
    { value: 'et', label: 'Estonian' },
    { value: 'tl', label: 'Filipino' },
    { value: 'fi', label: 'Finnish' },
    { value: 'fr', label: 'French' },
    { value: 'fy', label: 'Frisian' },
    { value: 'gl', label: 'Galician' },
    { value: 'ka', label: 'Georgian' },
    { value: 'de', label: 'German' },
    { value: 'el', label: 'Greek' },
    { value: 'gu', label: 'Gujarati' },
    { value: 'ht', label: 'Haitian Creole' },
    { value: 'ha', label: 'Hausa' },
    { value: 'haw', label: 'Hawaiian' },
    { value: 'he', label: 'Hebrew' },
    { value: 'hi', label: 'Hindi' },
    { value: 'hmn', label: 'Hmong' },
    { value: 'hu', label: 'Hungarian' },
    { value: 'is', label: 'Icelandic' },
    { value: 'ig', label: 'Igbo' },
    { value: 'id', label: 'Indonesian' },
    { value: 'ga', label: 'Irish' },
    { value: 'it', label: 'Italian' },
    { value: 'ja', label: 'Japanese' },
    { value: 'jw', label: 'Javanese' },
    { value: 'kn', label: 'Kannada' },
    { value: 'kk', label: 'Kazakh' },
    { value: 'km', label: 'Khmer' },
    { value: 'ko', label: 'Korean' },
    { value: 'ku', label: 'Kurdish (Kurmanji)' },
    { value: 'ky', label: 'Kyrgyz' },
    { value: 'lo', label: 'Lao' },
    { value: 'la', label: 'Latin' },
    { value: 'lv', label: 'Latvian' },
    { value: 'lt', label: 'Lithuanian' },
    { value: 'lb', label: 'Luxembourgish' },
    { value: 'mk', label: 'Macedonian' },
    { value: 'mg', label: 'Malagasy' },
    { value: 'ms', label: 'Malay' },
    { value: 'ml', label: 'Malayalam' },
    { value: 'mt', label: 'Maltese' },
    { value: 'mi', label: 'Maori' },
    { value: 'mr', label: 'Marathi' },
    { value: 'mn', label: 'Mongolian' },
    { value: 'my', label: 'Myanmar (Burmese)' },
    { value: 'ne', label: 'Nepali' },
    { value: 'no', label: 'Norwegian' },
    { value: 'or', label: 'Odia' },
    { value: 'ps', label: 'Pashto' },
    { value: 'fa', label: 'Persian' },
    { value: 'pl', label: 'Polish' },
    { value: 'pt', label: 'Portuguese' },
    { value: 'pa', label: 'Punjabi' },
    { value: 'ro', label: 'Romanian' },
    { value: 'ru', label: 'Russian' },
    { value: 'sm', label: 'Samoan' },
    { value: 'gd', label: 'Scots Gaelic' },
    { value: 'sr', label: 'Serbian' },
    { value: 'st', label: 'Sesotho' },
    { value: 'sn', label: 'Shona' },
    { value: 'sd', label: 'Sindhi' },
    { value: 'si', label: 'Sinhala' },
    { value: 'sk', label: 'Slovak' },
    { value: 'sl', label: 'Slovenian' },
    { value: 'so', label: 'Somali' },
    { value: 'es', label: 'Spanish' },
    { value: 'su', label: 'Sundanese' },
    { value: 'sw', label: 'Swahili' },
    { value: 'sv', label: 'Swedish' },
    { value: 'tg', label: 'Tajik' },
    { value: 'ta', label: 'Tamil' },
    { value: 'te', label: 'Telugu' },
    { value: 'th', label: 'Thai' },
    { value: 'tr', label: 'Turkish' },
    { value: 'uk', label: 'Ukrainian' },
    { value: 'ur', label: 'Urdu' },
    { value: 'ug', label: 'Uyghur' },
    { value: 'uz', label: 'Uzbek' },
    { value: 'vi', label: 'Vietnamese' },
    { value: 'cy', label: 'Welsh' },
    { value: 'xh', label: 'Xhosa' },
    { value: 'yi', label: 'Yiddish' },
    { value: 'yo', label: 'Yoruba' },
    { value: 'zu', label: 'Zulu' }
  ];

  const sourceLanguages = [
    { value: 'auto', label: 'Auto-detect' },
    ...languages
  ];

  const examples = [
    {
      title: 'Basic Translation',
      description: 'Translate English text to Spanish',
      config: {
        text: 'Hello, how are you today?',
        target_language: 'es',
        source_language: 'en'
      }
    },
    {
      title: 'Auto-detect Language',
      description: 'Let Google detect the source language',
      config: {
        text: 'Bonjour, comment allez-vous?',
        target_language: 'en',
        source_language: 'auto'
      }
    },
    {
      title: 'HTML Content',
      description: 'Translate HTML content while preserving tags',
      config: {
        text: '<p>Welcome to our <strong>website</strong>!</p>',
        target_language: 'fr',
        source_language: 'en',
        format: 'html'
      }
    },
    {
      title: 'Multiple Languages',
      description: 'Translate to Chinese (Simplified)',
      config: {
        text: 'Artificial Intelligence is transforming the world',
        target_language: 'zh-cn',
        source_language: 'en'
      }
    }
  ];

  const handleSave = () => {
    const fullConfig = {
      ...config,
      auth: authConfig
    };
    onSave(fullConfig);
    onClose();
  };

  const handleTest = async () => {
    if (!config.text || !config.target_language) {
      setError('Please provide text and target language for testing');
      return;
    }

    if (!authConfig.access_token) {
      setError('Please provide OAuth access token for testing');
      return;
    }

    setIsLoading(true);
    setError(null);
    setTestResult(null);

    try {
      // Simulate API call for testing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock successful translation result
      const mockResult = {
        translatedText: config.target_language === 'es' ? 'Hola, ¿cómo estás hoy?' : 
                       config.target_language === 'fr' ? 'Bonjour, comment allez-vous aujourd\'hui?' :
                       config.target_language === 'de' ? 'Hallo, wie geht es dir heute?' :
                       'Translation result would appear here',
        detectedSourceLanguage: config.source_language === 'auto' ? 'en' : config.source_language,
        originalText: config.text,
        targetLanguage: config.target_language
      };

      setTestResult(mockResult);
    } catch (err) {
      setError('Translation test failed. Please check your configuration and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadExample = (example: any) => {
    setConfig(prev => ({
      ...prev,
      ...example.config
    }));
    setError(null);
    setTestResult(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Languages className="h-5 w-5 text-blue-600" />
            </div>
            <span>Configure Google Translate</span>
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="configuration" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="configuration">Configuration</TabsTrigger>
            <TabsTrigger value="authentication">Authentication</TabsTrigger>
            <TabsTrigger value="examples">Examples</TabsTrigger>
            <TabsTrigger value="test">Test</TabsTrigger>
          </TabsList>

          <TabsContent value="configuration" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="text">Text to Translate *</Label>
                  <Textarea
                    id="text"
                    placeholder="Enter the text you want to translate..."
                    value={config.text}
                    onChange={(e) => setConfig(prev => ({ ...prev, text: e.target.value }))}
                    rows={4}
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="target_language">Target Language *</Label>
                  <Select
                    value={config.target_language}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, target_language: value }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select target language" />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="source_language">Source Language</Label>
                  <Select
                    value={config.source_language}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, source_language: value }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select source language" />
                    </SelectTrigger>
                    <SelectContent>
                      {sourceLanguages.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="format">Text Format</Label>
                  <Select
                    value={config.format}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, format: value }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text">Plain Text</SelectItem>
                      <SelectItem value="html">HTML</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="model">Translation Model</Label>
                  <Select
                    value={config.model}
                    onValueChange={(value) => setConfig(prev => ({ ...prev, model: value }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="nmt">Neural Machine Translation (Recommended)</SelectItem>
                      <SelectItem value="base">Base Model</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Configuration Preview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Configuration Preview</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Operation:</span>
                      <Badge variant="outline">Translate</Badge>
                    </div>
                    {config.target_language && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Target:</span>
                        <Badge variant="outline" className="text-blue-600">
                          {languages.find(l => l.value === config.target_language)?.label}
                        </Badge>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Source:</span>
                      <Badge variant="outline" className="text-gray-600">
                        {sourceLanguages.find(l => l.value === config.source_language)?.label}
                      </Badge>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Model:</span>
                      <Badge variant="outline" className="text-purple-600">
                        {config.model === 'nmt' ? 'Neural MT' : 'Base'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="authentication" className="space-y-4">
            <Alert>
              <Globe className="h-4 w-4" />
              <AlertDescription>
                Google Translate requires OAuth2 authentication with Google Cloud Translation API access.
                You'll need to set up a Google Cloud project and enable the Translation API.
              </AlertDescription>
            </Alert>

            <div className="space-y-4">
              <div>
                <Label htmlFor="access_token">OAuth2 Access Token *</Label>
                <Input
                  id="access_token"
                  type="password"
                  placeholder="Enter your Google OAuth2 access token"
                  value={authConfig.access_token}
                  onChange={(e) => setAuthConfig(prev => ({ ...prev, access_token: e.target.value }))}
                  className="mt-1"
                />
                <p className="text-sm text-gray-500 mt-1">
                  This token should have the 'https://www.googleapis.com/auth/cloud-translation' scope.
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Setup Instructions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <ol className="list-decimal list-inside space-y-1 text-gray-600">
                    <li>Go to Google Cloud Console</li>
                    <li>Create or select a project</li>
                    <li>Enable the Cloud Translation API</li>
                    <li>Create OAuth2 credentials</li>
                    <li>Generate an access token with translation scope</li>
                    <li>Paste the token above</li>
                  </ol>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="examples" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {examples.map((example, index) => (
                <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-sm">{example.title}</CardTitle>
                    <p className="text-xs text-gray-500">{example.description}</p>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-xs">
                      <div><strong>Text:</strong> {example.config.text}</div>
                      <div><strong>Target:</strong> {languages.find(l => l.value === example.config.target_language)?.label}</div>
                      <div><strong>Source:</strong> {sourceLanguages.find(l => l.value === example.config.source_language)?.label}</div>
                      {example.config.format && example.config.format !== 'text' && (
                        <div><strong>Format:</strong> {example.config.format.toUpperCase()}</div>
                      )}
                    </div>
                    <Button
                      onClick={() => loadExample(example)}
                      variant="outline"
                      size="sm"
                      className="w-full mt-3"
                    >
                      Load Example
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="test" className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Test Translation</h3>
                <Button
                  onClick={handleTest}
                  disabled={isLoading || !config.text || !config.target_language || !authConfig.access_token}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <TestTube className="h-4 w-4 mr-2" />
                      Test Translation
                    </>
                  )}
                </Button>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {testResult && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span>Translation Successful</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label className="text-sm font-medium">Original Text:</Label>
                      <p className="text-sm text-gray-600 mt-1 p-2 bg-gray-50 rounded">
                        {testResult.originalText}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Translated Text:</Label>
                      <p className="text-sm text-blue-600 mt-1 p-2 bg-blue-50 rounded font-medium">
                        {testResult.translatedText}
                      </p>
                    </div>
                    <div className="flex space-x-4 text-sm">
                      <div>
                        <span className="text-gray-600">Detected Source:</span>
                        <Badge variant="outline" className="ml-2">
                          {sourceLanguages.find(l => l.value === testResult.detectedSourceLanguage)?.label}
                        </Badge>
                      </div>
                      <div>
                        <span className="text-gray-600">Target:</span>
                        <Badge variant="outline" className="ml-2 text-blue-600">
                          {languages.find(l => l.value === testResult.targetLanguage)?.label}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="text-sm text-gray-500">
                <p><strong>Note:</strong> This test uses your current configuration and authentication settings.</p>
                <p>Make sure you have valid OAuth2 credentials and the text/target language are set.</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end space-x-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">
            Save Configuration
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}