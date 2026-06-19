'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchVehicles, fetchDrivers, fetchEvents, fetchReports, fetchConfig } from '@/lib/api/fleet'
import { deriveKpis } from '@/lib/kpis'

// No `/kpis` endpoint: fetch the real lists in parallel and derive the six numbers.
export function useKpis() {
  return useQuery({
    queryKey: ['kpis'],
    queryFn: async () => {
      const [vehicles, drivers, events, reports, config] = await Promise.all([
        fetchVehicles(),
        fetchDrivers(),
        fetchEvents(),
        fetchReports(),
        fetchConfig(),
      ])
      return deriveKpis(vehicles, drivers, events, reports, {
        docs_expiry_warning_days: Number(config.docs_expiry_warning_days ?? 30),
      })
    },
    refetchInterval: 30_000,
  })
}
