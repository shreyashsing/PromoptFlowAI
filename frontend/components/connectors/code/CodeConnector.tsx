import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Code2, Play, Settings, Shield, Clock, Cpu } from 'lucide-react';

interface CodeConnectorProps {
  config?: {
    language?: string;
    mode?: string;
    code?: string;
    timeout?: number;
    safe_mode?: boolean;
    allow_network?: boolean;
    allow_file_system?: boolean;
    max_memory_mb?: number;
  };
  onConfigure?: () => void;
  onTest?: () => void;
  isConfigured?: boolean;
}

export function CodeConnector({ 
  config, 
  onConfigure, 
  onTest, 
  isConfigured = false 
}: CodeConnectorProps) {
  const language = config?.language || 'javascript';
  const mode = config?.mode || 'runOnceForAllItems';
  const codePreview = config?.code ? 
    config.code.substring(0, 100) + (config.code.length > 100 ? '...' : '') : 
    'No code configured';
  const timeout = config?.timeout || 30;
  const safeMode = config?.safe_mode !== false;
  const allowNetwork = config?.allow_network === true;
  const allowFileSystem = config?.allow_file_system === true;
  const maxMemory = config?.max_memory_mb || 128;

  const getLanguageColor = (lang: string) => {
    switch (lang) {
      case 'javascript':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'python':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getModeDisplay = (mode: string) => {
    return mode === 'runOnceForAllItems' ? 'All Items' : 'Each Item';
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Code2 className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <CardTitle className="text-lg">Code Executor</CardTitle>
              <p className="text-sm text-gray-500">Custom code execution</p>
            </div>
          </div>
          <div className="flex items-center space-x-1">
            {isConfigured ? (
              <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                Configured
              </Badge>
            ) : (
              <Badge variant="secondary">Not Configured</Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Language and Mode */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Badge className={getLanguageColor(language)}>
              {language.charAt(0).toUpperCase() + language.slice(1)}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {getModeDisplay(mode)}
            </Badge>
          </div>
        </div>

        {/* Code Preview */}
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Code2 className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Code Preview</span>
          </div>
          <div className="bg-gray-50 rounded-md p-3 border">
            <code className="text-xs text-gray-600 font-mono break-all">
              {codePreview}
            </code>
          </div>
        </div>

        {/* Configuration Details */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <Clock className="h-3 w-3 text-gray-400" />
            <span className="text-gray-600">Timeout: {timeout}s</span>
          </div>
          <div className="flex items-center space-x-2">
            <Cpu className="h-3 w-3 text-gray-400" />
            <span className="text-gray-600">Memory: {maxMemory}MB</span>
          </div>
        </div>

        {/* Safety Indicators */}
        <div className="flex flex-wrap gap-1">
          {safeMode && (
            <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
              <Shield className="h-3 w-3 mr-1" />
              Safe Mode
            </Badge>
          )}
          {allowNetwork && (
            <Badge variant="outline" className="text-xs bg-orange-50 text-orange-700 border-orange-200">
              Network Access
            </Badge>
          )}
          {allowFileSystem && (
            <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
              File System Access
            </Badge>
          )}
        </div>

        {/* Feature Highlights */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Features</h4>
          <div className="grid grid-cols-1 gap-1 text-xs text-gray-600">
            <div className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
              <span>JavaScript & Python support</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
              <span>Sandboxed execution environment</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
              <span>Console output capture</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
              <span>Memory & timeout limits</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onConfigure}
            className="flex-1"
          >
            <Settings className="h-4 w-4 mr-2" />
            Configure
          </Button>
          {isConfigured && (
            <Button
              variant="default"
              size="sm"
              onClick={onTest}
              className="flex-1 bg-purple-600 hover:bg-purple-700"
            >
              <Play className="h-4 w-4 mr-2" />
              Test
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}