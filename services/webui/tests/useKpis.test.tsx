import { renderHook, waitFor } from '@testing-library/react'
import { it, expect } from 'vitest'
import { useKpis } from '@/hooks/useKpis'
import { QueryClientWrapper } from './helpers'

// Reads the latest 2 kpi_daily snapshots and maps them to six tiles + trends.
it('useKpis maps kpi_daily rows to six tiles with trends', async () => {
  const { result } = renderHook(() => useKpis(), { wrapper: QueryClientWrapper })
  await waitFor(() => expect(result.current.data).toBeDefined())

  const tiles = result.current.data!.tiles
  expect(tiles).toHaveLength(6)

  const km = tiles.find((t) => t.key === 'fleetKm7d')
  expect(km?.value).toBe(1200)
  expect(km?.trend).toBe('up') // 1200 today vs 1000 yesterday

  const due = tiles.find((t) => t.key === 'maintDue')
  expect(due?.value).toBe(2)
  expect(due?.trend).toBe('down') // 2 vs 4

  expect(result.current.data!.latest?.top_customer_id).toBe('c1')
})
