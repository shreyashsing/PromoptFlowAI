"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Mail, Send, Inbox, Archive, Tag, MessageSquare, FileText, Users } from 'lucide-react';

interface GmailConnectorProps {
  onSelect?: () => void;
  isSelected?: boolean;
}

const GmailConnector: React.FC<GmailConnectorProps> = ({ onSelect, isSelected = false }) => {
  const features = [
    { icon: Send, label: 'Send Emails', description: 'Send emails with attachments' },
    { icon: Inbox, label: 'Read Messages', description: 'Read and search emails' },
    { icon: MessageSquare, label: 'Reply & Forward', description: 'Reply to conversations' },
    { icon: FileText, label: 'Draft Management', description: 'Create and manage drafts' },
    { icon: Tag, label: 'Label Operations', description: 'Manage Gmail labels' },
    { icon: Archive, label: 'Thread Management', description: 'Handle email threads' },
    { icon: Users, label: 'Contact Management', description: 'Manage recipients' },
    { icon: Mail, label: 'Advanced Search', description: 'Search with Gmail syntax' }
  ];

  return (
    <Card 
      className={`cursor-pointer transition-all duration-200 hover:shadow-lg ${
        isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'
      }`}
      onClick={onSelect}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-100 rounded-lg">
            <Mail className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <CardTitle className="text-lg">Gmail Connector</CardTitle>
            <CardDescription>
              Complete Gmail integration with full email management capabilities
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary" className="bg-red-50 text-red-700 border-red-200">
            OAuth2
          </Badge>
          <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
            25 Actions
          </Badge>
          <Badge variant="secondary" className="bg-green-50 text-green-700 border-green-200">
            Full API
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {features.slice(0, 6).map((feature, index) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              <feature.icon className="h-4 w-4 text-gray-500" />
              <span className="text-gray-700">{feature.label}</span>
            </div>
          ))}
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs text-gray-500">
            Supports messages, drafts, labels, threads, and advanced Gmail operations
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default GmailConnector;