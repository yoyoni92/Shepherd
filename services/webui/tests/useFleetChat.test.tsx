import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useFleetChat } from '@/hooks/useFleetChat'

describe('T3 - useFleetChat', () => {
  it('sends message and receives agent response with citations', async () => {
    const { result } = renderHook(() => useFleetChat('test-session'))
    await act(async () => {
      await result.current.send('What is the status of vehicle 12-345-67?')
    })
    await waitFor(() => expect(result.current.messages).toHaveLength(2))
    expect(result.current.messages[0]).toMatchObject({ role: 'user', content: 'What is the status of vehicle 12-345-67?' })
    expect(result.current.messages[1]).toMatchObject({ role: 'assistant' })
    // Agent returns tools_used + RAG citations (gap D1 closed)
    expect(result.current.messages[1].tool_calls).toContain('fleet_api')
    expect(result.current.messages[1].citations).toContain('vehicle-profile-12-345-67')
  })

  it('clears loading after response arrives', async () => {
    const { result } = renderHook(() => useFleetChat('test-session'))
    await act(async () => { await result.current.send('question') })
    expect(result.current.loading).toBe(false)
  })
})
