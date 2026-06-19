import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useConfig } from '@/hooks/useConfig'
import { QueryClientWrapper } from './helpers'

describe('T6 - useConfig', () => {
  it('fetches config from Fleet API', async () => {
    const { result } = renderHook(() => useConfig(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.config).toBeDefined())
    expect(result.current.config?.docs_expiry_warning_days).toBe(30)
  })

  it('sets saveError when value fails Zod validation', async () => {
    // mutate() is fire-and-forget; Zod throws inside mutationFn -> surfaces in saveError
    const { result } = renderHook(() => useConfig(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.config).toBeDefined())
    act(() => { result.current.save({ key: 'x', value: null as unknown as string }) })
    await waitFor(() => expect(result.current.saveError).toBeDefined())
  })
})
