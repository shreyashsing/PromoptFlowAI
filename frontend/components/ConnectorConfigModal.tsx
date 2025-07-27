'use client'

import { useState, useEffect } from 'react'
import { 
  Settings, 
  Key, 
  Code, 
  Save, 
  X, 
  AlertCircle,
  CheckCircle,
  Info
} from 'lucide-react'
import { WorkflowNode } from '@/lib/types'
import { getConnectorSchema } from '@/lib/connector-schemas'
import { supabase } from '@/lib/supabase'

interface ConnectorConfigModalProps {
  isOpen: boolean
  onClose: () => void
  node: WorkflowNode | null
  onSave: (nodeId: string, parameters: Record<string, any>) => Promise<void>
}

export default function ConnectorConfigModal({ 
  isOpen, 
  onClose, 
  node, 
  onSave 
}: ConnectorConfigModalProps) {
  const [parameters, setParameters] = useState<Record<string, any>>({})
  const [activeTab, setActiveTab] = useState('config')
  const [authStatus, setAuthStatus] = useState<'none' | 'required' | 'configured' | 'checking'>('none')
  const [parametersLoaded, setParametersLoaded] = useState(false)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [isSavingApiKey, setIsSavingApiKey] = useState(false)

  useEffect(() => {
    if (node) {
      // Debug: Log node data
      // console.log('ConnectorConfigModal - Node data:', { id: node.id, connector_name: node.connector_name, parameters: node.parameters })
      
      // Get schema and populate defaults if parameters are missing
      const schema = getConnectorSchema(node.connector_name)
      const nodeParameters = node.parameters || {}
      
      if (schema) {
        // Add default values for missing parameters
        const parametersWithDefaults = { ...nodeParameters }
        schema.parameters.forEach(param => {
          if (param.default !== undefined && !parametersWithDefaults[param.name]) {
            parametersWithDefaults[param.name] = param.default
          }
        })
        setParameters(parametersWithDefaults)
        // console.log('Parameters with defaults:', parametersWithDefaults)
      } else {
        setParameters(nodeParameters)
      }
      
      // Check auth status based on connector type and actual authentication
      checkAuthenticationStatus(node.connector_name)
      
      setParametersLoaded(true)
    }
  }, [node])

  // Check for pending OAuth refresh (user just came back from authentication)
  useEffect(() => {
    if (isOpen && node) {
      const pendingRefresh = localStorage.getItem('oauth_pending_refresh')
      if (pendingRefresh === 'true') {
        localStorage.removeItem('oauth_pending_refresh')
        // Wait a moment for any ongoing authentication to complete
        setTimeout(() => {
          checkAuthenticationStatus(node.connector_name)
        }, 1000)
      }
    }
  }, [isOpen, node])

  // Function to check authentication status for a connector
  const checkAuthenticationStatus = async (connectorName: string) => {
    if (connectorName === 'gmail_connector' || connectorName === 'perplexity_search' || connectorName === 'google_sheets') {
      setAuthStatus('checking')
      
      try {
        // Get current Supabase session
        const { data: { session } } = await supabase.auth.getSession()
        
        if (!session?.access_token) {
          setAuthStatus('required')
          return
        }
        
        const response = await fetch('/api/auth/tokens', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}`
          }
        })
        
        if (response.ok) {
          const authData = await response.json()
          
          // Check if this specific connector has valid authentication
          const hasAuthToken = authData.tokens && authData.tokens.some((token: any) => 
            token.connector_name === connectorName && 
            (token.token_type === 'oauth2' || token.token_type === 'api_key')
          )
          
          if (hasAuthToken) {
            setAuthStatus('configured')
          } else {
            setAuthStatus('required')
          }
        } else {
          setAuthStatus('required')
        }
      } catch (error) {
        console.error('Failed to check authentication status:', error)
        setAuthStatus('required')
      }
    } else {
      setAuthStatus('none')
    }
  }

  const handleSave = async () => {
    if (node) {
      try {
        await onSave(node.id, parameters)
        // Show success feedback
        console.log('Configuration saved successfully')
        onClose()
      } catch (error) {
        console.error('Failed to save configuration:', error)
        // Don't close modal if save failed
      }
    }
  }

  const updateParameter = (key: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleGoogleOAuth = async () => {
    if (!node) return
    
    setIsAuthenticating(true)
    try {
      // Get current Supabase session
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session?.access_token) {
        alert('Please sign in first to authenticate connectors.')
        setIsAuthenticating(false)
        return
      }
      
      // Get the current origin for redirect URI
      const redirectUri = `${window.location.origin}/auth/oauth/callback`
      
      // Initiate OAuth flow
      const response = await fetch('/api/auth/oauth/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          connector_name: node.connector_name,
          redirect_uri: redirectUri
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to initiate OAuth')
      }
      
      const data = await response.json()
      
      // Store state for verification
      localStorage.setItem('oauth_state', data.state)
      localStorage.setItem('oauth_connector', node.connector_name)
      
      // Redirect to Google OAuth
      window.location.href = data.authorization_url
      
    } catch (error) {
      console.error('OAuth initiation failed:', error)
      const serviceName = node.connector_name === 'gmail_connector' ? 'Gmail' : 'Google Sheets'
      alert(`Failed to start ${serviceName} authentication. Please try again.`)
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleSaveApiKey = async () => {
    if (!node || !apiKey.trim()) {
      alert('Please enter an API key')
      return
    }

    setIsSavingApiKey(true)
    try {
      // Get current Supabase session
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session?.access_token) {
        alert('Please log in to save API key')
        return
      }

      const response = await fetch('/api/auth/tokens', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          connector_name: node.connector_name,
          token_type: 'api_key',
          token_data: {
            api_key: apiKey
          }
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save API key')
      }

      alert('API key saved successfully!')
      setAuthStatus('configured')
      setApiKey('') // Clear the input after successful save
      
    } catch (error) {
      console.error('Failed to save API key:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      alert(`Failed to save API key: ${errorMessage}`)
    } finally {
      setIsSavingApiKey(false)
    }
  }

  const renderParameterField = (key: string, schema: any, value: any) => {
    // console.log(`renderParameterField - ${key}:`, value);
    const isRequired = schema.required?.includes(key)
    const fieldLabel = key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
    
    switch (schema.properties?.[key]?.type) {
      case 'string':
        if (schema.properties[key].enum) {
          return (
            <div key={key} className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                {fieldLabel}
                {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
              </label>
              <select 
                value={value || ''} 
                onChange={(e) => updateParameter(key, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
              >
                <option value="">Select {fieldLabel}</option>
                {schema.properties[key].enum.map((option: string) => (
                  <option key={option} value={option}>
                    {option.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </option>
                ))}
              </select>
              {schema.properties[key].description && (
                <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
              )}
            </div>
          )
        }
        
        if (key.includes('body') || key.includes('content') || key.includes('text')) {
          return (
            <div key={key} className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                {fieldLabel}
                {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
              </label>
              <textarea
                value={value || ''}
                onChange={(e) => updateParameter(key, e.target.value)}
                placeholder={schema.properties[key].description || `Enter ${fieldLabel}`}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[100px] resize-y text-gray-900 bg-white"
                style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
              />
              {schema.properties[key].description && (
                <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
              )}
            </div>
          )
        }
        
        return (
          <div key={key} className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              {fieldLabel}
              {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
            </label>
            <input
              type={key.includes('password') || key.includes('key') ? 'password' : 'text'}
              value={value || ''}
              onChange={(e) => updateParameter(key, e.target.value)}
              placeholder={schema.properties[key].description || `Enter ${fieldLabel}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
            />
            {schema.properties[key].description && (
              <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
            )}
          </div>
        )
        
      case 'number':
      case 'integer':
        return (
          <div key={key} className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              {fieldLabel}
              {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
            </label>
            <input
              type="number"
              value={value || ''}
              onChange={(e) => updateParameter(key, parseInt(e.target.value) || 0)}
              placeholder={schema.properties[key].description || `Enter ${fieldLabel}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
            />
            {schema.properties[key].description && (
              <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
            )}
          </div>
        )
        
      case 'boolean':
        return (
          <div key={key} className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              {fieldLabel}
              {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
            </label>
            <select 
              value={value?.toString() || 'false'} 
              onChange={(e) => updateParameter(key, e.target.value === 'true')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
            >
              <option value="true">True</option>
              <option value="false">False</option>
            </select>
            {schema.properties[key].description && (
              <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
            )}
          </div>
        )
        
      default:
        return (
          <div key={key} className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              {fieldLabel}
              {isRequired && <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Required</span>}
            </label>
            <input
              value={typeof value === 'string' ? value : JSON.stringify(value || '')}
              onChange={(e) => updateParameter(key, e.target.value)}
              placeholder={schema.properties[key]?.description || `Enter ${fieldLabel}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
            />
            {schema.properties[key]?.description && (
              <p className="text-xs text-gray-500">{schema.properties[key].description}</p>
            )}
          </div>
        )
    }
  }

  const convertSchemaToJsonSchema = (connectorName: string) => {
    const schema = getConnectorSchema(connectorName)
    if (!schema) return { type: 'object', properties: {}, required: [] }
    
    const properties: Record<string, any> = {}
    const required: string[] = []
    
    schema.parameters.forEach(param => {
      properties[param.name] = {
        type: param.type === 'textarea' ? 'string' : param.type,
        description: param.description,
        ...(param.options && { enum: param.options.map(opt => opt.value) }),
        ...(param.default !== undefined && { default: param.default })
      }
      
      if (param.required) {
        required.push(param.name)
      }
    })
    
    const result = {
      type: 'object',
      properties,
      required
    }
    
    // console.log(`Schema for ${connectorName}:`, result);
    return result;
  }

  if (!node) return null

  const schema = convertSchemaToJsonSchema(node.connector_name)
  const connectorTitle = node.connector_name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())

  if (!isOpen || !node) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <Settings className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{connectorTitle}</h2>
              <p className="text-sm text-gray-500">Configure connector parameters</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <div className="flex">
            {['config', 'auth', 'advanced'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600 bg-blue-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  {tab === 'config' && <Settings className="w-4 h-4" />}
                  {tab === 'auth' && (
                    <div className="relative">
                      <Key className="w-4 h-4" />
                      {authStatus === 'configured' && (
                        <CheckCircle className="w-3 h-3 text-green-600 absolute -top-1 -right-1 bg-white rounded-full" />
                      )}
                      {authStatus === 'required' && (
                        <AlertCircle className="w-3 h-3 text-orange-600 absolute -top-1 -right-1 bg-white rounded-full" />
                      )}
                      {authStatus === 'checking' && (
                        <div className="w-3 h-3 border border-blue-600 rounded-full animate-spin absolute -top-1 -right-1 bg-white" style={{borderTopColor: 'transparent'}}></div>
                      )}
                    </div>
                  )}
                  {tab === 'advanced' && <Code className="w-4 h-4" />}
                  {tab === 'config' && 'Configuration'}
                  {tab === 'auth' && 'Authentication'}
                  {tab === 'advanced' && 'Advanced'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {activeTab === 'config' && (
            <div className="space-y-4">
              {!parametersLoaded ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-500">Loading configuration...</p>
                </div>
              ) : Object.keys(schema.properties || {}).length > 0 ? (
                Object.keys(schema.properties || {}).map(key => {
                  // console.log(`Rendering field ${key} with value:`, parameters[key]);
                  return renderParameterField(key, schema, parameters[key]);
                })
              ) : (
                <div className="text-center py-12">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No configuration parameters available</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'auth' && (
            <div className="space-y-4">
              {authStatus === 'checking' && (
                <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
                  <div className="w-5 h-5 border-2 border-blue-600 rounded-full animate-spin" style={{borderTopColor: 'transparent'}}></div>
                  <span className="text-blue-800">Checking authentication status...</span>
                </div>
              )}
              
              {authStatus === 'configured' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <span className="text-green-800">Successfully authenticated</span>
                  </div>
                  
                  {node.connector_name === 'gmail_connector' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Your Gmail account is connected and ready to use for sending and receiving emails.
                      </p>
                      <div className="flex gap-2">
                        <button 
                          onClick={handleGoogleOAuth}
                          disabled={isAuthenticating}
                          className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 disabled:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                        >
                          <Key className="w-4 h-4" />
                          {isAuthenticating ? 'Reconnecting...' : 'Reconnect Account'}
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {node.connector_name === 'google_sheets' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Your Google Sheets account is connected and ready to use for reading and writing spreadsheets.
                      </p>
                      <div className="flex gap-2">
                        <button 
                          onClick={handleGoogleOAuth}
                          disabled={isAuthenticating}
                          className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 disabled:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                        >
                          <Key className="w-4 h-4" />
                          {isAuthenticating ? 'Reconnecting...' : 'Reconnect Account'}
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {node.connector_name === 'perplexity_search' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Your Perplexity API key is configured and ready to use.
                      </p>
                      <button className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2">
                        <Key className="w-4 h-4" />
                        Update API Key
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              {authStatus === 'none' && (
                <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-green-800">No authentication required</span>
                </div>
              )}
              
              {authStatus === 'required' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 bg-orange-50 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-orange-600" />
                    <span className="text-orange-800">Authentication required</span>
                  </div>
                  
                  {node.connector_name === 'gmail_connector' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Connect your Gmail account to send and receive emails.
                      </p>
                      <button 
                        onClick={handleGoogleOAuth}
                        disabled={isAuthenticating}
                        className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors flex items-center justify-center gap-2"
                      >
                        <Key className="w-4 h-4" />
                        {isAuthenticating ? 'Connecting...' : 'Connect Gmail Account'}
                      </button>
                    </div>
                  )}
                  
                  {node.connector_name === 'google_sheets' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Connect your Google account to read and write Google Sheets.
                      </p>
                      <button 
                        onClick={handleGoogleOAuth}
                        disabled={isAuthenticating}
                        className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:bg-green-400 transition-colors flex items-center justify-center gap-2"
                      >
                        <Key className="w-4 h-4" />
                        {isAuthenticating ? 'Connecting...' : 'Connect Google Sheets'}
                      </button>
                    </div>
                  )}
                  
                  {node.connector_name === 'perplexity_search' && (
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Enter your Perplexity API key to use search functionality.
                      </p>
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">API Key</label>
                        <input 
                          type="password" 
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          placeholder="Enter your Perplexity API key"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                          style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
                        />
                      </div>
                      <button 
                        onClick={handleSaveApiKey}
                        disabled={isSavingApiKey || !apiKey.trim()}
                        className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors flex items-center justify-center gap-2"
                      >
                        <Key className="w-4 h-4" />
                        {isSavingApiKey ? 'Saving...' : 'Save API Key'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Retry Attempts</label>
                <input 
                  type="number" 
                  defaultValue="3"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                  style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
                />
                <p className="text-xs text-gray-500">Number of retry attempts on failure</p>
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Timeout (seconds)</label>
                <input 
                  type="number" 
                  defaultValue="30"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                  style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
                />
                <p className="text-xs text-gray-500">Request timeout in seconds</p>
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Error Handling</label>
                <select 
                  defaultValue="continue"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                  style={{ color: '#111827 !important', backgroundColor: '#ffffff !important' }}
                >
                  <option value="continue">Continue on Error</option>
                  <option value="stop">Stop on Error</option>
                  <option value="retry">Retry on Error</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  )
}