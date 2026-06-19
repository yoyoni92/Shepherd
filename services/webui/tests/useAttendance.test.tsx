import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useAttendance } from '@/hooks/useAttendance'

// Attendance has no backend (gap B2) — preview state held + validated in-memory.
describe('useAttendance (preview)', () => {
  it('builds a sample month with employees and records', () => {
    const { result } = renderHook(() => useAttendance('2026-06'))
    expect(result.current.available).toBe(false)
    expect(result.current.month.employees).toHaveLength(7)
    expect(result.current.month.label).toBe('יוני 2026')
  })

  it('applies a valid time edit to local state', () => {
    const { result } = renderHook(() => useAttendance('2026-06'))
    const firstDay = result.current.month.records['1'][0].day
    act(() => result.current.patchDay({ employeeId: 1, day: firstDay, patch: { in: '08:15' } }))
    expect(result.current.patchError).toBeNull()
    expect(result.current.month.records['1'][0].in).toBe('08:15')
  })

  it('rejects an out-before-in edit', () => {
    const { result } = renderHook(() => useAttendance('2026-06'))
    const firstDay = result.current.month.records['1'][0].day
    act(() => result.current.patchDay({ employeeId: 1, day: firstDay, patch: { out: '01:00' } }))
    expect(result.current.patchError).toBeTruthy()
  })

  it('rejects a malformed time string', () => {
    const { result } = renderHook(() => useAttendance('2026-06'))
    const firstDay = result.current.month.records['1'][0].day
    act(() => result.current.patchDay({ employeeId: 1, day: firstDay, patch: { in: '99:99' } }))
    expect(result.current.patchError).toBeTruthy()
  })
})
