import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export function QueryClientWrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}
