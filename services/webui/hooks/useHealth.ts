'use client'
import { useQuery } from '@tanstack/react-query'
import type { ServiceHealth } from '@/lib/health'

interface HealthResponse {
  services: ServiceHealth[]
  checkedAt: string
}

// Polls the server-side aggregator (app/api/health) every 15s.
export function useHealth() {
  const query = useQuery({
    queryKey: ['health'],
    queryFn: async (): Promise<HealthResponse> => {
      const res = await fetch('/api/health', { cache: 'no-store' })
      if (!res.ok) throw new Error(`health: ${res.status}`)
      return res.json()
    },
    refetchInterval: 15_000,
  })
  return {
    services: query.data?.services ?? [],
    checkedAt: query.data?.checkedAt ?? null,
    loading: query.isLoading,
    refetch: query.refetch,
  }
}
