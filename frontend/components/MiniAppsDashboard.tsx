'use client';

import React, { useState, useEffect } from 'react';
import { Play, Settings, Trash2, Plus, Bot, Loader2, Calendar, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { createClient } from '@/lib/supabase/client';

interface MiniApp {
  id: string;
  name: string;
  description: string;
  user_prompt: string;
  config: {
    input_fields: Array<{
      name: string;
      type: string;
      label: string;
      required: boolean;
    }>;
    ui_config: {
      theme: string;
      layout: string;
      submit_button_text: string;
      success_message: string;
    };
  };
  created_at: string;
}

interface ExecutionStep {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
}

export default function MiniAppsDashboard() {
  const [miniApps, setMiniApps] = useState<MiniApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [executingApp, setExecutingApp] = useState<string | null>(null);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [selectedApp, setSelectedApp] = useState<MiniApp | null>(null);
  const [formInputs, setFormInputs] = useState<Record<string, string>>({});
  const [showExecutionDialog, setShowExecutionDialog] = useState(false);
  const supabase = createClient();

  useEffect(() => {
    fetchMiniApps();
  }, []);

  const fetchMiniApps = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('No authentication session found');
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/ai-agent/mini-apps`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setMiniApps(data.mini_apps || []);
    } catch (error) {
      console.error('Error fetching mini-apps:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteMiniApp = async (appId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/ai-agent/mini-apps/${appId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        }
      });

      if (response.ok) {
        setMiniApps(prev => prev.filter(app => app.id !== appId));
      }
    } catch (error) {
      console.error('Error deleting mini-app:', error);
    }
  };

  const executeMiniApp = async (app: MiniApp) => {
    if (!formInputs || Object.keys(formInputs).length === 0) {
      alert('Please fill in all required fields');
      return;
    }

    setExecutingApp(app.id);
    setExecutionSteps([]);
    setShowExecutionDialog(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('No authentication session found');
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/ai-agent/execute-mini-app`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          mini_app_id: app.id,
          inputs: formInputs
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const step: ExecutionStep = JSON.parse(line.slice(6));
              setExecutionSteps(prev => [...prev, step]);
            } catch (e) {
              console.error('Error parsing execution step:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('Error executing mini-app:', error);
      setExecutionSteps(prev => [...prev, {
        id: 'error',
        type: 'error',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setExecutingApp(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAppTypeColor = (name: string) => {
    if (name.toLowerCase().includes('blog')) return 'bg-purple-100 text-purple-800';
    if (name.toLowerCase().includes('email')) return 'bg-blue-100 text-blue-800';
    if (name.toLowerCase().includes('data')) return 'bg-green-100 text-green-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
        <span className="ml-2 text-gray-600">Loading your automations...</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Automation Apps</h1>
          <p className="text-gray-600">Manage and run your AI-created automations</p>
        </div>
        <Button 
          onClick={() => window.location.href = '/ai-agent'}
          className="bg-purple-600 hover:bg-purple-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create New App
        </Button>
      </div>

      {/* Mini Apps Grid */}
      {miniApps.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <Bot className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No automation apps yet</h3>
            <p className="text-gray-600 mb-4">
              Create your first automation by describing what you want to automate
            </p>
            <Button 
              onClick={() => window.location.href = '/ai-agent'}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Your First App
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {miniApps.map((app) => (
            <Card key={app.id} className="hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{app.name}</CardTitle>
                    <Badge className={getAppTypeColor(app.name)}>
                      {app.config.input_fields.length} inputs
                    </Badge>
                  </div>
                  <div className="flex space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteMiniApp(app.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                <p className="text-sm text-gray-600 line-clamp-2">{app.description}</p>
                
                <div className="flex items-center text-xs text-gray-500">
                  <Calendar className="w-3 h-3 mr-1" />
                  {formatDate(app.created_at)}
                </div>

                <Dialog>
                  <DialogTrigger asChild>
                    <Button 
                      className="w-full bg-purple-600 hover:bg-purple-700"
                      onClick={() => {
                        setSelectedApp(app);
                        setFormInputs({});
                      }}
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Run Automation
                    </Button>
                  </DialogTrigger>
                  
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle>{app.name}</DialogTitle>
                    </DialogHeader>
                    
                    <div className="space-y-4">
                      <p className="text-sm text-gray-600">{app.description}</p>
                      
                      {app.config.input_fields.map((field, idx) => (
                        <div key={idx}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                          </label>
                          {field.type === 'textarea' ? (
                            <Textarea 
                              placeholder={`Enter ${field.label.toLowerCase()}`}
                              value={formInputs[field.name] || ''}
                              onChange={(e) => setFormInputs(prev => ({
                                ...prev,
                                [field.name]: e.target.value
                              }))}
                            />
                          ) : (
                            <Input 
                              type={field.type}
                              placeholder={`Enter ${field.label.toLowerCase()}`}
                              value={formInputs[field.name] || ''}
                              onChange={(e) => setFormInputs(prev => ({
                                ...prev,
                                [field.name]: e.target.value
                              }))}
                            />
                          )}
                        </div>
                      ))}
                      
                      <Button 
                        onClick={() => selectedApp && executeMiniApp(selectedApp)}
                        disabled={executingApp === app.id}
                        className="w-full bg-purple-600 hover:bg-purple-700"
                      >
                        {executingApp === app.id ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Running...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2" />
                            {app.config.ui_config.submit_button_text}
                          </>
                        )}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Execution Dialog */}
      <Dialog open={showExecutionDialog} onOpenChange={setShowExecutionDialog}>
        <DialogContent className="max-w-lg max-h-96 overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Execution Progress</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-3">
            {executionSteps.map((step, idx) => (
              <div key={step.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 mt-0.5">
                  {step.type === 'executing' ? (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  ) : step.type === 'completed' ? (
                    <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-white rounded-full" />
                    </div>
                  ) : (
                    <div className="w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-white rounded-full" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{step.title}</p>
                  <p className="text-sm text-gray-600">{step.description}</p>
                </div>
              </div>
            ))}
            
            {executingApp && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
                <span className="ml-2 text-gray-600">Running automation...</span>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
