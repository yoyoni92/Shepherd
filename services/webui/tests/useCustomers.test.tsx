import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useCustomers } from '@/hooks/useCustomers'
import { QueryClientWrapper } from './helpers'

describe('useCustomers', () => {
  it('builds an id -> name map from the real customers list', async () => {
    const { result } = renderHook(() => useCustomers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(Object.keys(result.current.customerById).length).toBeGreaterThan(0))
    expect(result.current.customerById['c1']).toBe('אלקטרה מערכות')
  })
})
