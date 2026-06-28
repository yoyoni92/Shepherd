import type { KpiDailyRead } from './api/schemas'

// VP-grade dashboard tiles, precomputed nightly into kpi_daily and read O(1).
// Each tile maps to one column; trends come free from comparing the latest two rows.
export const KPI_TILE_KEYS = [
  'fleetKm7d',
  'avgKmPerDriver',
  'maintCadence',
  'docsExpiring',
  'topCustomer',
] as const

export type KpiTileKey = (typeof KPI_TILE_KEYS)[number]
export type TrendDir = 'up' | 'down' | 'flat'

export interface KpiTile {
  key: KpiTileKey
  value: number | null
  delta: number | null
  trend: TrendDir | null
}

const COLUMN: Record<KpiTileKey, (r: KpiDailyRead) => number | null> = {
  fleetKm7d: (r) => r.total_km_7d,
  avgKmPerDriver: (r) => r.avg_km_per_driver_7d,
  maintCadence: (r) => r.avg_days_between_maintenance,
  docsExpiring: (r) => r.docs_expiring_count,
  topCustomer: (r) => r.top_customer_km,
}

const round1 = (n: number) => Math.round(n * 10) / 10

/**
 * Map the latest kpi_daily rows (newest first) to the six dashboard tiles.
 * Trend per tile = today vs yesterday; a single row yields no trend.
 */
export function deriveKpiTiles(rows: readonly KpiDailyRead[]): KpiTile[] {
  const [today, prev] = rows
  return KPI_TILE_KEYS.map((key) => {
    const get = COLUMN[key]
    const value = today ? get(today) : null
    let delta: number | null = null
    let trend: TrendDir | null = null
    if (today && prev) {
      delta = round1((get(today) ?? 0) - (get(prev) ?? 0))
      trend = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'
    }
    return { key, value, delta, trend }
  })
}
