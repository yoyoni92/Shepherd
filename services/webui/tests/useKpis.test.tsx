import { renderHook, waitFor } from '@testing-library/react'
import { it, expect } from 'vitest'
import { useKpis } from '@/hooks/useKpis'
import { QueryClientWrapper } from './helpers'

// No /kpis endpoint: derived from the real vehicles/drivers/events/reports handlers.
it('T2b - useKpis derives kpis from the real lists', async () => {
  const { result } = renderHook(() => useKpis(), { wrapper: QueryClientWrapper })
  await waitFor(() => expect(result.current.data).toBeDefined())
  expect(result.current.data?.vehicles).toBe(3)
  expect(result.current.data?.activeDrivers).toBe(1) // d1 active, d2 inactive
  expect(result.current.data?.openEvents).toBe(2) // e1, e2 open; e3 resolved
  expect(result.current.data?.unpaidTickets).toBe(1) // r1 unpaid; r2 paid
})
