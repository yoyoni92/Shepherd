import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useAttendance } from '@/hooks/useAttendance'
import { QueryClientWrapper } from './helpers'

// Employees are drivers; the month skeleton overlays records fetched from the Fleet API.
describe('useAttendance', () => {
  it('builds the month from drivers and overlays a stored record', async () => {
    const { result } = renderHook(() => useAttendance('2026-06'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.month.employees).toHaveLength(2))
    await waitFor(() => {
      const d = result.current.month.records['d1'].find((x) => x.day === 2)
      expect(d?.in).toBe('08:05')
      expect(d?.status).toBe('late')
    })
  })

  it('accepts a valid time edit', async () => {
    const { result } = renderHook(() => useAttendance('2026-06'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.month.employees).toHaveLength(2))
    const firstDay = result.current.month.records['d1'][0].day
    act(() => result.current.patchDay({ employeeId: 'd1', day: firstDay, patch: { in: '08:15' } }))
    expect(result.current.patchError).toBeNull()
  })

  it('rejects a malformed time string', async () => {
    const { result } = renderHook(() => useAttendance('2026-06'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.month.employees).toHaveLength(2))
    const firstDay = result.current.month.records['d1'][0].day
    act(() => result.current.patchDay({ employeeId: 'd1', day: firstDay, patch: { in: '99:99' } }))
    expect(result.current.patchError).toBeTruthy()
  })

  it('rejects an out-before-in edit', async () => {
    const { result } = renderHook(() => useAttendance('2026-06'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.month.employees).toHaveLength(2))
    const firstDay = result.current.month.records['d1'][0].day
    act(() => result.current.patchDay({ employeeId: 'd1', day: firstDay, patch: { in: '17:00', out: '01:00' } }))
    expect(result.current.patchError).toBeTruthy()
  })
})
