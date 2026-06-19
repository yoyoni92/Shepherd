import { renderHook } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useMissions } from '@/hooks/useMissions'

// Missions have no backend (gap B1) — preview/sample data, priority-ordered.
describe('useMissions (preview)', () => {
  it('returns sample missions ordered by priority and flags no API', () => {
    const { result } = renderHook(() => useMissions())
    expect(result.current.available).toBe(false)
    expect(result.current.missions[0].priority).toBe('high')
    const order = result.current.missions.map((m) => m.priority)
    expect(order.indexOf('high')).toBeLessThan(order.indexOf('low'))
  })
})
