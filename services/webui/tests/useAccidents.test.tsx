import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useAccidents } from '@/hooks/useAccidents'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useAccidents', () => {
  it('fetches and adapts the accidents list', async () => {
    const { result } = renderHook(() => useAccidents(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.accidents).toHaveLength(2))
    expect(result.current.accidents[0].vehiclePlate).toBe('12-345-67')
    expect(result.current.accidents[0].driverName).toBe('דנה לוי')
    expect(result.current.accidents[0].attachments).toHaveLength(1)
    expect(result.current.accidents[1].driverName).toBeNull()
  })

  it('posts an AccidentCreate on add', async () => {
    let posted = false
    server.use(
      http.post(`${FLEET}/accidents`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ accident_id: 'a99', ...(await request.json() as object) }, { status: 201 })
      }),
    )
    const { result } = renderHook(() => useAccidents(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.accidents).toHaveLength(2))
    act(() => result.current.add({ vehicle_id: 'v1', datetime: '2026-06-21T10:00:00', attachments: [] }))
    await waitFor(() => expect(posted).toBe(true))
  })
})
