import { renderHook, waitFor } from '@testing-library/react'
import { it, expect } from 'vitest'
import { useKpis } from '@/hooks/useKpis'
import { QueryClientWrapper } from './helpers'

it('T2b - useKpis fetches and computes kpis', async () => {
  const { result } = renderHook(() => useKpis(), { wrapper: QueryClientWrapper })
  await waitFor(() => expect(result.current.data).toBeDefined())
  expect(result.current.data?.vehicles).toBe(42)
  expect(result.current.data?.activeDrivers).toBe(28)
  expect(result.current.data?.docsExpiring30d).toBe(7)
  expect(result.current.data?.unpaidTickets).toBe(3)
})
