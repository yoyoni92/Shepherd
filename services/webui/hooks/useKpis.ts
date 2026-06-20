'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchKpiDaily } from '@/lib/api/fleet'
import { deriveKpiTiles } from '@/lib/kpis'

// Reads the latest 2 kpi_daily snapshots (precomputed nightly) → six tiles + trend arrows.
export function useKpis() {
  return useQuery({
    queryKey: ['kpi-daily'],
    queryFn: async () => {
      const rows = await fetchKpiDaily(2)
      return { tiles: deriveKpiTiles(rows), latest: rows[0] ?? null }
    },
    refetchInterval: 60_000,
  })
}
