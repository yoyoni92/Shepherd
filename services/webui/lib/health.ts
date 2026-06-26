// System health: the 3rd-party services the console depends on. The browser can't reach the
// private hostnames, so /api/health pings them server-side and the UI renders the result.
export type ServiceStatus = 'up' | 'down'

export interface ServiceHealth {
  key: string
  status: ServiceStatus
  latencyMs: number | null
}

export const SERVICE_LABELS: Record<string, string> = {
  fleet: 'Fleet API',
}

export type Overall = 'ok' | 'degraded' | 'down'

/** Roll the per-service statuses up to one overall state. */
export function summarizeHealth(services: readonly ServiceHealth[]): Overall {
  if (services.length === 0) return 'down'
  const up = services.filter((s) => s.status === 'up').length
  if (up === services.length) return 'ok'
  if (up === 0) return 'down'
  return 'degraded'
}

export const downCount = (services: readonly ServiceHealth[]): number =>
  services.filter((s) => s.status === 'down').length
