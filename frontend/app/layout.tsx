import './globals.css'
import type { Metadata } from 'next'

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
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}