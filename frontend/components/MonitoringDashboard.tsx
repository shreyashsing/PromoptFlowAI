"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Users,
  Zap,
  BarChart3,
  RefreshCw,
  Settings,
  Eye,
  AlertCircle,
  Info
} from 'lucide-react';

interface MonitoringDashboardProps {
  className?: string;
}

interface AlertData {
  id: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  category: string;
  timestamp: string;
  resolved: boolean;
  data?: any;
}

interface MetricsData {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time_ms: number;
  total_tool_executions: number;
  tool_usage_distribution: Record<string, number>;
  reasoning_step_distribution: Record<string, number>;
  error_distribution: Record<string, number>;
  user_activity_patterns: {
    peak_hours: string[];
    active_users: number;
    avg_session_duration_minutes: number;
  };
  performance_trends: {
    response_time_trend: string;
    success_rate_trend: string;
    tool_usage_trend: string;
  };
}

interface DashboardData {
  system_health: {
    status: string;
    timestamp: string;
    uptime: number;
    metrics: {
      error_rate: number;
      warning_rate: number;
      avg_response_time: number;
      active_connections: number;
    };
    issues: string[];
  };
  agent_metrics: MetricsData;
  active_alerts: AlertData[];
  recent_errors: Array<{
    logger: string;
    error_count: number;
    severity: string;
    timestamp: string;
  }>;
  performance_summary: {
    average_response_time_ms: number;
    error_rate_percent: number;
    uptime_hours: number;
    total_requests_processed: number;
    performance_grade: string;
  };
  tool_performance: Record<string, {
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    average_duration_ms: number;
    success_rate: number;
    common_errors: string[];
  }>;
  user_statistics: {
    total_active_users: number;
    new_users: number;
    returning_users: number;
    average_session_duration_minutes: number;
    total_sessions: number;
    most_active_hours: string[];
    user_satisfaction_score: number;
    feature_usage: Record<string, number>;
  };
  timestamp: string;
}

interface ReasoningTraceAnalysis {
  correlation_id: string;
  total_steps: number;
  successful_steps: number;
  failed_steps: number;
  total_duration_ms: number;
  average_step_duration_ms: number;
  tools_used: string[];
  reasoning_patterns: Record<string, any>;
  performance_issues: string[];
  recommendations: string[];
}

export default function MonitoringDashboard({ className }: MonitoringDashboardProps) {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<AlertData | null>(null);
  const [traceAnalysis, setTraceAnalysis] = useState<ReasoningTraceAnalysis | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/monitoring/dashboard`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
      }

      const data = await response.json();
      setDashboardData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
              const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/v1/monitoring/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to resolve alert');
      }

      // Refresh dashboard data
      await fetchDashboardData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve alert');
    }
  };

  const analyzeReasoningTrace = async (correlationId: string) => {
    try {
              const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/v1/monitoring/reasoning-trace/${correlationId}/analysis`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to analyze reasoning trace');
      }

      const analysis = await response.json();
      setTraceAnalysis(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze reasoning trace');
    }
  };

  useEffect(() => {
    fetchDashboardData();

    if (autoRefresh) {
      const interval = setInterval(fetchDashboardData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval, autoRefresh]);

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      case 'unhealthy': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'degraded': return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'unhealthy': return <AlertCircle className="h-5 w-5 text-red-600" />;
      default: return <Activity className="h-5 w-5 text-gray-600" />;
    }
  };

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case 'info': return 'bg-blue-100 text-blue-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'critical': return 'bg-red-200 text-red-900';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'info': return <Info className="h-4 w-4" />;
      case 'warning': return <AlertTriangle className="h-4 w-4" />;
      case 'error': return <AlertCircle className="h-4 w-4" />;
      case 'critical': return <AlertCircle className="h-4 w-4" />;
      default: return <Info className="h-4 w-4" />;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading monitoring dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className="m-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!dashboardData) {
    return (
      <Alert className="m-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>No dashboard data available</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">ReAct Agent Monitoring</h1>
          <p className="text-gray-600">
            Last updated: {new Date(dashboardData.timestamp).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchDashboardData}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className="h-4 w-4 mr-2" />
            Auto Refresh
          </Button>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            {getHealthStatusIcon(dashboardData.system_health.status)}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getHealthStatusColor(dashboardData.system_health.status)}`}>
              {dashboardData.system_health.status.toUpperCase()}
            </div>
            <p className="text-xs text-gray-600">
              Uptime: {formatUptime(dashboardData.system_health.uptime)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((dashboardData.agent_metrics.successful_requests / dashboardData.agent_metrics.total_requests) * 100).toFixed(1)}%
            </div>
            <Progress 
              value={(dashboardData.agent_metrics.successful_requests / dashboardData.agent_metrics.total_requests) * 100} 
              className="mt-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatDuration(dashboardData.agent_metrics.average_response_time_ms)}
            </div>
            <p className="text-xs text-gray-600">
              Grade: {dashboardData.performance_summary.performance_grade}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Users className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData.user_statistics.total_active_users}
            </div>
            <p className="text-xs text-gray-600">
              {dashboardData.user_statistics.total_sessions} sessions
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Active Alerts */}
      {dashboardData.active_alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2 text-yellow-600" />
              Active Alerts ({dashboardData.active_alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dashboardData.active_alerts.map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getAlertIcon(alert.level)}
                    <div>
                      <div className="font-medium">{alert.title}</div>
                      <div className="text-sm text-gray-600">{alert.message}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(alert.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className={getAlertLevelColor(alert.level)}>
                      {alert.level.toUpperCase()}
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => resolveAlert(alert.id)}
                    >
                      Resolve
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Metrics Tabs */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="tools">Tool Usage</TabsTrigger>
          <TabsTrigger value="users">User Activity</TabsTrigger>
          <TabsTrigger value="errors">Error Analysis</TabsTrigger>
          <TabsTrigger value="debugging">Debugging Tools</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Request Volume</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Total Requests</span>
                    <span className="font-bold">{dashboardData.agent_metrics.total_requests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Successful</span>
                    <span className="text-green-600 font-bold">{dashboardData.agent_metrics.successful_requests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Failed</span>
                    <span className="text-red-600 font-bold">{dashboardData.agent_metrics.failed_requests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tool Executions</span>
                    <span className="font-bold">{dashboardData.agent_metrics.total_tool_executions}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Performance Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span>Response Time</span>
                    <Badge variant={dashboardData.agent_metrics.performance_trends.response_time_trend === 'improving' ? 'default' : 'secondary'}>
                      {dashboardData.agent_metrics.performance_trends.response_time_trend}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Success Rate</span>
                    <Badge variant={dashboardData.agent_metrics.performance_trends.success_rate_trend === 'improving' ? 'default' : 'secondary'}>
                      {dashboardData.agent_metrics.performance_trends.success_rate_trend}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Tool Usage</span>
                    <Badge variant={dashboardData.agent_metrics.performance_trends.tool_usage_trend === 'increasing' ? 'default' : 'secondary'}>
                      {dashboardData.agent_metrics.performance_trends.tool_usage_trend}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="tools" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(dashboardData.tool_performance).map(([toolName, metrics]) => (
              <Card key={toolName}>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="h-4 w-4 mr-2" />
                    {toolName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Success Rate</span>
                      <span className={`font-bold ${metrics.success_rate > 0.9 ? 'text-green-600' : metrics.success_rate > 0.8 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {(metrics.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Duration</span>
                      <span className="font-bold">{formatDuration(metrics.average_duration_ms)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Executions</span>
                      <span className="font-bold">{metrics.total_executions}</span>
                    </div>
                    <Progress value={metrics.success_rate * 100} className="mt-2" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="users" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>User Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Active Users</span>
                    <span className="font-bold">{dashboardData.user_statistics.total_active_users}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>New Users</span>
                    <span className="text-green-600 font-bold">{dashboardData.user_statistics.new_users}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Returning Users</span>
                    <span className="text-blue-600 font-bold">{dashboardData.user_statistics.returning_users}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Session</span>
                    <span className="font-bold">{dashboardData.user_statistics.average_session_duration_minutes.toFixed(1)}m</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Peak Hours</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {dashboardData.user_statistics.most_active_hours.map((hour, index) => (
                    <Badge key={index} variant="outline" className="mr-1 mb-1">
                      {hour}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Feature Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(dashboardData.user_statistics.feature_usage).map(([feature, count]) => (
                    <div key={feature} className="flex justify-between">
                      <span className="text-sm">{feature.replace('_', ' ')}</span>
                      <span className="font-bold">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Error Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(dashboardData.agent_metrics.error_distribution).map(([errorType, count]) => (
                    <div key={errorType} className="flex justify-between items-center">
                      <span className="text-sm">{errorType.replace('_', ' ')}</span>
                      <Badge variant="destructive">{count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {dashboardData.recent_errors.map((error, index) => (
                    <div key={index} className="flex justify-between items-center p-2 border rounded">
                      <div>
                        <div className="text-sm font-medium">{error.logger}</div>
                        <div className="text-xs text-gray-600">
                          {new Date(error.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <Badge variant="destructive">{error.error_count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="debugging" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Eye className="h-5 w-5 mr-2" />
                Reasoning Trace Analysis
              </CardTitle>
              <CardDescription>
                Analyze specific reasoning traces for debugging and optimization
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Enter correlation ID..."
                    className="flex-1 px-3 py-2 border rounded-md"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const target = e.target as HTMLInputElement;
                        if (target.value.trim()) {
                          analyzeReasoningTrace(target.value.trim());
                        }
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      const input = document.querySelector('input[placeholder="Enter correlation ID..."]') as HTMLInputElement;
                      if (input?.value.trim()) {
                        analyzeReasoningTrace(input.value.trim());
                      }
                    }}
                  >
                    Analyze
                  </Button>
                </div>

                {traceAnalysis && (
                  <div className="border rounded-lg p-4 space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-600">Total Steps</div>
                        <div className="text-lg font-bold">{traceAnalysis.total_steps}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Success Rate</div>
                        <div className="text-lg font-bold text-green-600">
                          {((traceAnalysis.successful_steps / traceAnalysis.total_steps) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Duration</div>
                        <div className="text-lg font-bold">{formatDuration(traceAnalysis.total_duration_ms)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Tools Used</div>
                        <div className="text-lg font-bold">{traceAnalysis.tools_used.length}</div>
                      </div>
                    </div>

                    {traceAnalysis.performance_issues.length > 0 && (
                      <div>
                        <h4 className="font-medium text-red-600 mb-2">Performance Issues</h4>
                        <ul className="list-disc list-inside space-y-1">
                          {traceAnalysis.performance_issues.map((issue, index) => (
                            <li key={index} className="text-sm text-red-600">{issue}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {traceAnalysis.recommendations.length > 0 && (
                      <div>
                        <h4 className="font-medium text-blue-600 mb-2">Recommendations</h4>
                        <ul className="list-disc list-inside space-y-1">
                          {traceAnalysis.recommendations.map((rec, index) => (
                            <li key={index} className="text-sm text-blue-600">{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}