'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, AlertCircle, FolderOpen, Upload, FileText, Image, Video } from 'lucide-react';

interface GoogleDriveConnectorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: GoogleDriveConfig) => void;
  initialConfig?: GoogleDriveConfig;
  mode?: 'create' | 'edit';
}

interface GoogleDriveConfig {
  action: 'list_files' | 'create_folder' | 'upload_file' | 'create_from_text' | 'get_file_content' | 'delete_file' | 'share_file';
  file_name?: string;
  text_content?: string;
  parent_folder_id?: string;
  mime_type?: string;
  description?: string;
  file_id?: string;
  query?: string;
  max_results?: number;
  folder_name?: string;
  file_path?: string;
  share_type?: 'anyone' | 'domain' | 'user';
  role?: 'reader' | 'writer' | 'commenter';
  email?: string;
}

interface AuthStatus {
  is_authenticated: boolean;
  user_email?: string;
  error?: string;
}

const MIME_TYPES = {
  'text/plain': 'Text File',
  'application/pdf': 'PDF Document',
  'application/vnd.google-apps.document': 'Google Doc',
  'application/vnd.google-apps.spreadsheet': 'Google Sheet',
  'application/vnd.google-apps.presentation': 'Google Slides',
  'application/json': 'JSON File',
  'text/csv': 'CSV File',
  'image/jpeg': 'JPEG Image',
  'image/png': 'PNG Image',
  'video/mp4': 'MP4 Video'
};

export default function GoogleDriveConnector({ 
  isOpen, 
  onClose, 
  onSave, 
  initialConfig,
  mode = 'create' 
}: GoogleDriveConnectorProps) {
  const [config, setConfig] = useState<GoogleDriveConfig>(
    initialConfig || { 
      action: 'list_files',
      parent_folder_id: 'root',
      max_results: 10
    }
  );
  const [authStatus, setAuthStatus] = useState<AuthStatus>({ is_authenticated: false });
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  useEffect(() => {
    if (isOpen) {
      checkAuthStatus();
    }
  }, [isOpen]);

  const checkAuthStatus = async () => {
    setIsCheckingAuth(true);
    try {
      const response = await fetch('/api/connectors/google_drive/auth/status');
      const data = await response.json();
      setAuthStatus(data);
    } catch (error) {
      console.error('Error checking auth status:', error);
      setAuthStatus({ is_authenticated: false, error: 'Failed to check authentication status' });
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleAuthenticate = async () => {
    setIsAuthenticating(true);
    try {
      const response = await fetch('/api/connectors/google_drive/auth/url');
      const data = await response.json();
      
      if (data.auth_url) {
        window.open(data.auth_url, 'google-auth', 'width=500,height=600');
        
        // Poll for authentication completion
        const pollAuth = setInterval(async () => {
          const statusResponse = await fetch('/api/connectors/google_drive/auth/status');
          const statusData = await statusResponse.json();
          
          if (statusData.is_authenticated) {
            setAuthStatus(statusData);
            clearInterval(pollAuth);
            setIsAuthenticating(false);
          }
        }, 2000);
        
        // Stop polling after 5 minutes
        setTimeout(() => {
          clearInterval(pollAuth);
          setIsAuthenticating(false);
        }, 300000);
      }
    } catch (error) {
      console.error('Error initiating authentication:', error);
      setIsAuthenticating(false);
    }
  };

  const handleConfigChange = (field: keyof GoogleDriveConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(config);
    onClose();
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'list_files': return <FolderOpen className="w-4 h-4" />;
      case 'create_folder': return <FolderOpen className="w-4 h-4" />;
      case 'upload_file': return <Upload className="w-4 h-4" />;
      case 'create_from_text': return <FileText className="w-4 h-4" />;
      case 'get_file_content': return <FileText className="w-4 h-4" />;
      case 'delete_file': return <AlertCircle className="w-4 h-4" />;
      case 'share_file': return <CheckCircle className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const renderActionSpecificFields = () => {
    switch (config.action) {
      case 'list_files':
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="query">Search Query (optional)</Label>
              <Input
                id="query"
                value={config.query || ''}
                onChange={(e) => handleConfigChange('query', e.target.value)}
                placeholder="e.g., name contains 'report'"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_results">Max Results</Label>
              <Input
                id="max_results"
                type="number"
                value={config.max_results || 10}
                onChange={(e) => handleConfigChange('max_results', parseInt(e.target.value))}
                min="1"
                max="100"
              />
            </div>
          </>
        );

      case 'create_folder':
        return (
          <div className="space-y-2">
            <Label htmlFor="folder_name">Folder Name *</Label>
            <Input
              id="folder_name"
              value={config.folder_name || ''}
              onChange={(e) => handleConfigChange('folder_name', e.target.value)}
              placeholder="Enter folder name"
              required
            />
          </div>
        );

      case 'upload_file':
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="file_path">File Path *</Label>
              <Input
                id="file_path"
                value={config.file_path || ''}
                onChange={(e) => handleConfigChange('file_path', e.target.value)}
                placeholder="Path to local file"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="file_name">File Name (optional)</Label>
              <Input
                id="file_name"
                value={config.file_name || ''}
                onChange={(e) => handleConfigChange('file_name', e.target.value)}
                placeholder="Override filename"
              />
            </div>
          </>
        );

      case 'create_from_text':
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="file_name">File Name *</Label>
              <Input
                id="file_name"
                value={config.file_name || ''}
                onChange={(e) => handleConfigChange('file_name', e.target.value)}
                placeholder="e.g., document.txt"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="text_content">Text Content *</Label>
              <textarea
                id="text_content"
                className="w-full min-h-[100px] p-2 border rounded-md"
                value={config.text_content || ''}
                onChange={(e) => handleConfigChange('text_content', e.target.value)}
                placeholder="Enter text content"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mime_type">File Type</Label>
              <Select
                value={config.mime_type || 'text/plain'}
                onValueChange={(value) => handleConfigChange('mime_type', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(MIME_TYPES).map(([mime, label]) => (
                    <SelectItem key={mime} value={mime}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        );

      case 'get_file_content':
      case 'delete_file':
        return (
          <div className="space-y-2">
            <Label htmlFor="file_id">File ID *</Label>
            <Input
              id="file_id"
              value={config.file_id || ''}
              onChange={(e) => handleConfigChange('file_id', e.target.value)}
              placeholder="Google Drive file ID"
              required
            />
          </div>
        );

      case 'share_file':
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="file_id">File ID *</Label>
              <Input
                id="file_id"
                value={config.file_id || ''}
                onChange={(e) => handleConfigChange('file_id', e.target.value)}
                placeholder="Google Drive file ID"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="share_type">Share Type</Label>
              <Select
                value={config.share_type || 'anyone'}
                onValueChange={(value) => handleConfigChange('share_type', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="anyone">Anyone with link</SelectItem>
                  <SelectItem value="domain">Domain</SelectItem>
                  <SelectItem value="user">Specific user</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Permission Role</Label>
              <Select
                value={config.role || 'reader'}
                onValueChange={(value) => handleConfigChange('role', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reader">Reader</SelectItem>
                  <SelectItem value="writer">Writer</SelectItem>
                  <SelectItem value="commenter">Commenter</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {config.share_type === 'user' && (
              <div className="space-y-2">
                <Label htmlFor="email">User Email *</Label>
                <Input
                  id="email"
                  type="email"
                  value={config.email || ''}
                  onChange={(e) => handleConfigChange('email', e.target.value)}
                  placeholder="user@example.com"
                  required
                />
              </div>
            )}
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <FolderOpen className="w-4 h-4 text-blue-600" />
            </div>
            {mode === 'edit' ? 'Edit' : 'Configure'} Google Drive Connector
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Authentication Status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Authentication Status</CardTitle>
            </CardHeader>
            <CardContent>
              {isCheckingAuth ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Checking authentication...</span>
                </div>
              ) : authStatus.is_authenticated ? (
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-green-700">
                    Authenticated as {authStatus.user_email}
                  </span>
                  <Badge variant="secondary" className="ml-auto">Connected</Badge>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-orange-500" />
                    <span className="text-sm text-orange-700">Not authenticated</span>
                    <Badge variant="outline" className="ml-auto">Disconnected</Badge>
                  </div>
                  <Button 
                    onClick={handleAuthenticate}
                    disabled={isAuthenticating}
                    size="sm"
                    className="w-full"
                  >
                    {isAuthenticating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Authenticating...
                      </>
                    ) : (
                      'Connect to Google Drive'
                    )}
                  </Button>
                </div>
              )}
              {authStatus.error && (
                <Alert className="mt-3">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>{authStatus.error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Action Configuration */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="action">Action *</Label>
              <Select
                value={config.action}
                onValueChange={(value) => handleConfigChange('action', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="list_files">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="w-4 h-4" />
                      List Files
                    </div>
                  </SelectItem>
                  <SelectItem value="create_folder">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="w-4 h-4" />
                      Create Folder
                    </div>
                  </SelectItem>
                  <SelectItem value="upload_file">
                    <div className="flex items-center gap-2">
                      <Upload className="w-4 h-4" />
                      Upload File
                    </div>
                  </SelectItem>
                  <SelectItem value="create_from_text">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Create Text File
                    </div>
                  </SelectItem>
                  <SelectItem value="get_file_content">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Get File Content
                    </div>
                  </SelectItem>
                  <SelectItem value="delete_file">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      Delete File
                    </div>
                  </SelectItem>
                  <SelectItem value="share_file">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Share File
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Common Fields */}
            <div className="space-y-2">
              <Label htmlFor="parent_folder_id">Parent Folder ID</Label>
              <Input
                id="parent_folder_id"
                value={config.parent_folder_id || 'root'}
                onChange={(e) => handleConfigChange('parent_folder_id', e.target.value)}
                placeholder="root (for Drive root folder)"
              />
              <p className="text-xs text-gray-500">
                Use 'root' for the main Drive folder, or provide a specific folder ID
              </p>
            </div>

            {config.description !== undefined && (
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Input
                  id="description"
                  value={config.description || ''}
                  onChange={(e) => handleConfigChange('description', e.target.value)}
                  placeholder="File or folder description"
                />
              </div>
            )}

            {/* Action-specific fields */}
            {renderActionSpecificFields()}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              onClick={handleSave}
              disabled={!authStatus.is_authenticated}
            >
              {mode === 'edit' ? 'Update' : 'Save'} Configuration
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}