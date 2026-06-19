import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useEvents } from '@/hooks/useEvents'
import { QueryClientWrapper } from './helpers'

describe('useEvents', () => {
  it('fetches the real events list', async () => {
    const { result } = renderHook(() => useEvents(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.events.length).toBeGreaterThan(0))
    expect(result.current.events.some((e) => e.status === 'open')).toBe(true)
  })
})
