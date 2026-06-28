import { describe, it, expect } from 'vitest'
import { deriveKpiTiles, KPI_TILE_KEYS } from '@/lib/kpis'
import type { KpiDailyRead } from '@/lib/api/schemas'

const row = (over: Partial<KpiDailyRead> = {}): KpiDailyRead => ({
  snapshot_date: '2026-06-19',
  total_km_7d: 0,
  avg_km_per_driver_7d: 0,
  avg_days_between_maintenance: 0,
  docs_expiring_count: 0,
  top_customer_id: null,
  top_customer_km: 0,
  top_customer_vehicle_count: 0,
  computed_ts: '2026-06-19T03:00:00Z',
  ...over,
})

describe('deriveKpiTiles', () => {
  it('maps the tiles from the latest row', () => {
    const tiles = deriveKpiTiles([
      row({ total_km_7d: 1200, avg_km_per_driver_7d: 300, avg_days_between_maintenance: 45, docs_expiring_count: 2, top_customer_km: 800 }),
    ])
    expect(tiles.map((t) => t.key)).toEqual([...KPI_TILE_KEYS])
    expect(tiles.find((t) => t.key === 'fleetKm7d')?.value).toBe(1200)
    expect(tiles.find((t) => t.key === 'docsExpiring')?.value).toBe(2)
    expect(tiles.find((t) => t.key === 'topCustomer')?.value).toBe(800)
  })

  it('computes trend vs yesterday', () => {
    const tiles = deriveKpiTiles([
      row({ total_km_7d: 1200 }),
      row({ total_km_7d: 1000 }),
    ])
    const km = tiles.find((t) => t.key === 'fleetKm7d')!
    expect(km.delta).toBe(200)
    expect(km.trend).toBe('up')
  })

  it('has null trend with a single row', () => {
    const tiles = deriveKpiTiles([row({ total_km_7d: 500 })])
    expect(tiles[0].trend).toBeNull()
    expect(tiles[0].delta).toBeNull()
  })

  it('handles an empty list (no snapshots yet)', () => {
    const tiles = deriveKpiTiles([])
    expect(tiles).toHaveLength(KPI_TILE_KEYS.length)
    expect(tiles[0].value).toBeNull()
  })
})
