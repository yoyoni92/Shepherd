'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchKpis } from '@/lib/api/fleet'
import { computeKpis } from '@/lib/kpis'

export function useKpis() {
  return useQuery({
    queryKey: ['kpis'],
    queryFn: async () => computeKpis(await fetchKpis()),
    refetchInterval: 30_000,
  })
}
