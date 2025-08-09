'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Languages, Globe, Settings, TestTube } from 'lucide-react';

interface GoogleTranslateConnectorProps {
  config?: {
    operation?: string;
    text?: string;
    target_language?: string;
    source_language?: string;
    format?: string;
    model?: string;
  };
  onConfigure?: () => void;
  onTest?: () => void;
  isConfigured?: boolean;
}

export function GoogleTranslateConnector({ 
  config, 
  onConfigure, 
  onTest, 
  isConfigured = false 
}: GoogleTranslateConnectorProps) {
  const getLanguageName = (code: string) => {
    const languageMap: Record<string, string> = {
      'auto': 'Auto-detect',
      'en': 'English',
      'es': 'Spanish',
      'fr': 'French',
      'de': 'German',
      'it': 'Italian',
      'pt': 'Portuguese',
      'ru': 'Russian',
      'ja': 'Japanese',
      'ko': 'Korean',
      'zh-cn': 'Chinese (Simplified)',
      'zh-tw': 'Chinese (Traditional)',
      'ar': 'Arabic',
      'hi': 'Hindi',
      'th': 'Thai',
      'vi': 'Vietnamese',
      'nl': 'Dutch',
      'pl': 'Polish',
      'tr': 'Turkish',
      'sv': 'Swedish',
      'da': 'Danish',
      'no': 'Norwegian',
      'fi': 'Finnish',
      'cs': 'Czech',
      'hu': 'Hungarian',
      'ro': 'Romanian',
      'bg': 'Bulgarian',
      'hr': 'Croatian',
      'sk': 'Slovak',
      'sl': 'Slovenian',
      'et': 'Estonian',
      'lv': 'Latvian',
      'lt': 'Lithuanian',
      'uk': 'Ukrainian'
    };
    return languageMap[code] || code?.toUpperCase() || 'Unknown';
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (!text) return '';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  return (
    <Card className="w-full max-w-md border-2 border-blue-200 hover:border-blue-300 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Languages className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-lg font-semibold text-gray-900">
                Google Translate
              </CardTitle>
              <p className="text-sm text-gray-500">Text Translation</p>
            </div>
          </div>
          <Badge 
            variant={isConfigured ? "default" : "secondary"}
            className={isConfigured ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}
          >
            {isConfigured ? "Configured" : "Setup Required"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Configuration Status */}
        <div className="space-y-3">
          {config?.text && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <Globe className="h-4 w-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">Text to Translate</span>
              </div>
              <p className="text-sm text-gray-600 italic">
                "{truncateText(config.text)}"
              </p>
            </div>
          )}

          {config?.target_language && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Target Language:</span>
              <Badge variant="outline" className="text-blue-600 border-blue-200">
                {getLanguageName(config.target_language)}
              </Badge>
            </div>
          )}

          {config?.source_language && config.source_language !== 'auto' && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Source Language:</span>
              <Badge variant="outline" className="text-gray-600 border-gray-200">
                {getLanguageName(config.source_language)}
              </Badge>
            </div>
          )}

          {config?.model && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Model:</span>
              <Badge variant="outline" className="text-purple-600 border-purple-200">
                {config.model === 'nmt' ? 'Neural MT' : 'Base'}
              </Badge>
            </div>
          )}

          {config?.format && config.format !== 'text' && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Format:</span>
              <Badge variant="outline" className="text-orange-600 border-orange-200">
                {config.format.toUpperCase()}
              </Badge>
            </div>
          )}
        </div>

        {/* Feature Highlights */}
        <div className="bg-blue-50 p-3 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Features</h4>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• 100+ supported languages</li>
            <li>• Automatic language detection</li>
            <li>• Neural machine translation</li>
            <li>• HTML content support</li>
            <li>• Real-time translation</li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-2">
          <Button
            onClick={onConfigure}
            variant="outline"
            size="sm"
            className="flex-1 text-blue-600 border-blue-200 hover:bg-blue-50"
          >
            <Settings className="h-4 w-4 mr-1" />
            Configure
          </Button>
          <Button
            onClick={onTest}
            variant="outline"
            size="sm"
            className="flex-1 text-green-600 border-green-200 hover:bg-green-50"
            disabled={!isConfigured}
          >
            <TestTube className="h-4 w-4 mr-1" />
            Test
          </Button>
        </div>

        {/* Quick Setup Hint */}
        {!isConfigured && (
          <div className="text-xs text-gray-500 text-center pt-2 border-t">
            💡 Click Configure to set up Google OAuth and translation preferences
          </div>
        )}
      </CardContent>
    </Card>
  );
}