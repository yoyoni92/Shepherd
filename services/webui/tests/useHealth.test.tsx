import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useHealth } from '@/hooks/useHealth'
import { summarizeHealth } from '@/lib/health'
import { QueryClientWrapper } from './helpers'

describe('useHealth', () => {
  it('fetches per-service status from the aggregator', async () => {
    const { result } = renderHook(() => useHealth(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.services.length).toBe(5))
    expect(result.current.services.find((s) => s.key === 'rag')?.status).toBe('down')
    expect(summarizeHealth(result.current.services)).toBe('degraded') // rag down, rest up
  })
})
