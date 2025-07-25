'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

import { supabase } from '../../../../lib/supabase'

export default function OAuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState('Processing authentication...')

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        console.log('Processing OAuth callback...')
        
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        if (error) {
          setStatus('error')
          setMessage(`Authentication failed: ${error}`)
          return
        }

        if (!code || !state) {
          setStatus('error')
          setMessage('Missing authorization code or state parameter')
          return
        }

        // Verify state parameter
        const storedState = localStorage.getItem('oauth_state')
        const connectorName = localStorage.getItem('oauth_connector')

        if (!storedState || storedState !== state) {
          setStatus('error')
          setMessage('Invalid state parameter - possible CSRF attack')
          return
        }

        if (!connectorName) {
          setStatus('error')
          setMessage('Missing connector information')
          return
        }

        // Get current Supabase session
        const { data: { session } } = await supabase.auth.getSession()
        
        // Prepare auth header
        const authHeader = session?.access_token 
          ? `Bearer ${session.access_token}`
          : 'Bearer dev-test-token' // Fallback for development
        
        if (!session?.access_token) {
          console.warn('No active Supabase session, using dev token for OAuth callback')
        }

        const response = await fetch('/api/auth/oauth/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader
          },
          body: JSON.stringify({
            code,
            state,
            connector_name: connectorName
          })
        })

        if (!response.ok) {
          const data = await response.json().catch(() => ({ error: 'Unknown error' }))
          throw new Error(`OAuth callback failed: ${data.detail || data.error || 'Unknown error'}`)
        }

        const data = await response.json()
        console.log('OAuth callback successful:', data)
        
        setStatus('success')
        setMessage('Authentication successful! You can now close this tab.')
        
        // Set flag to refresh authentication status when user returns to main app
        localStorage.setItem('oauth_pending_refresh', 'true')
        
        // Redirect to main app after a short delay
        setTimeout(() => {
          window.location.href = '/'
        }, 2000)
        
      } catch (error) {
        console.error('OAuth callback error:', error)
        setStatus('error')
        setMessage(`OAuth Error: ${error}`)
      }
    }

    handleOAuthCallback()
  }, [searchParams, router])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Processing Authentication</h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentication Successful!</h2>
              <p className="text-gray-600 mb-4">{message}</p>
              <p className="text-sm text-gray-500">Redirecting you back to the app...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentication Failed</h2>
              <p className="text-gray-600 mb-4">{message}</p>
              <button
                onClick={() => router.push('/')}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Return to App
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}