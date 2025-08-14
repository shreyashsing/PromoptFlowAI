'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Processing OAuth callback...');

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          setStatus('error');
          setMessage(`OAuth error: ${error}`);
          return;
        }

        if (!code || !state) {
          setStatus('error');
          setMessage('Missing required OAuth parameters');
          return;
        }

        // Get stored OAuth data
        const storedState = localStorage.getItem('oauth_state');
        const connectorName = localStorage.getItem('oauth_connector');

        if (!storedState || !connectorName) {
          setStatus('error');
          setMessage('OAuth session not found. Please try again.');
          return;
        }

        if (state !== storedState) {
          setStatus('error');
          setMessage('OAuth state mismatch. Please try again.');
          return;
        }

        // Get proper auth headers using Supabase session
        const { supabase } = await import('@/lib/supabase');
        const { data: { session } } = await supabase.auth.getSession();
        
        const headers: { [key: string]: string } = {
          'Content-Type': 'application/json'
        };
        
        if (session?.access_token) {
          headers['Authorization'] = `Bearer ${session.access_token}`;
        } else {
          throw new Error('No active authentication session. Please log in first.');
        }

        // Call backend OAuth callback endpoint
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/v1/auth/oauth/callback`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            code,
            state,
            connector_name: connectorName
          })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `OAuth callback failed: ${response.status}`);
        }

        const result = await response.json();
        
        setStatus('success');
        setMessage(`OAuth authentication successful for ${connectorName}! You can close this window.`);

        // Notify parent window of success
        if (window.opener) {
          window.opener.postMessage({ type: 'OAUTH_SUCCESS', connectorName }, window.location.origin);
        }

        // Clean up stored OAuth data
        localStorage.removeItem('oauth_state');
        localStorage.removeItem('oauth_connector');

        // Close the popup after a delay
        setTimeout(() => {
          if (window.opener) {
            window.close();
          }
        }, 3000);

      } catch (error) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setMessage(`OAuth callback failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        
        // Notify parent window of error
        if (window.opener) {
          window.opener.postMessage({ type: 'OAUTH_ERROR', error: error instanceof Error ? error.message : 'Unknown error' }, window.location.origin);
        }
      }
    };

    handleOAuthCallback();
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-8 max-w-md w-full mx-4">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Processing OAuth</h2>
              <p className="text-gray-300">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Authentication Successful!</h2>
              <p className="text-gray-300">{message}</p>
              <p className="text-sm text-gray-400 mt-2">This window will close automatically...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Authentication Failed</h2>
              <p className="text-gray-300">{message}</p>
              <button
                onClick={() => window.close()}
                className="mt-4 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                Close Window
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}