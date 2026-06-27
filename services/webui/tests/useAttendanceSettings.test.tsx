import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useAttendanceSettings } from '@/hooks/useAttendanceSettings'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useAttendanceSettings', () => {
  it('reads the company clock-in window', async () => {
    const { result } = renderHook(() => useAttendanceSettings(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.settings).toBeDefined())
    expect(result.current.settings).toEqual({ enabled: false, start: '07:00', end: '17:00' })
  })

  it('saves the window and caches the server response (no wiping refetch)', async () => {
    let body: Record<string, unknown> | null = null
    server.use(
      http.put(`${FLEET}/attendance/settings`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(body)
      }),
    )
    const { result } = renderHook(() => useAttendanceSettings(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.settings).toBeDefined())
    await act(async () => {
      await result.current.save({ enabled: true, start: '08:00', end: '18:00' })
    })
    expect(body).toEqual({ enabled: true, start: '08:00', end: '18:00' })
    await waitFor(() =>
      expect(result.current.settings).toEqual({ enabled: true, start: '08:00', end: '18:00' }),
    )
  })
})
