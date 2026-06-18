'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SessionProvider } from 'next-auth/react'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1 } } }))
  return (
    <SessionProvider>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </SessionProvider>
  )
}
