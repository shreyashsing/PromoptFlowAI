'use client'

import { useAuth } from '@/lib/auth-context'

export function AuthDebug() {
  const { user, session, loading } = useAuth()

  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 bg-black/80 text-white p-4 rounded-lg text-xs max-w-sm">
      <h3 className="font-bold mb-2">Auth Debug</h3>
      <div>Loading: {loading ? 'Yes' : 'No'}</div>
      <div>User: {user ? user.email : 'None'}</div>
      <div>Session: {session ? 'Active' : 'None'}</div>
      {user && (
        <div className="mt-2">
          <div>User ID: {user.id}</div>
          <div>Email Confirmed: {user.email_confirmed_at ? 'Yes' : 'No'}</div>
        </div>
      )}
    </div>
  )
}