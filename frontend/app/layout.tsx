import './globals.css'
import type { Metadata } from 'next'
import { AuthProvider } from '@/lib/auth-context'

export const metadata: Metadata = {
  title: 'PromptFlow AI',
  description: 'No-code AI automation platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}