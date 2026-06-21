import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useDrivers } from '@/hooks/useDrivers'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useDrivers', () => {
  it('fetches and adapts the driver list (status -> on/off)', async () => {
    const { result } = renderHook(() => useDrivers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.drivers).toHaveLength(2))
    expect(result.current.drivers[0].status).toBe('on')
    expect(result.current.drivers[1].status).toBe('off')
  })

  it('posts a DriverCreate on add', async () => {
    let posted = false
    server.use(
      http.post(`${FLEET}/drivers`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ driver_id: 'd99', status: 'active', ...(await request.json() as object) }, { status: 201 })
      }),
    )
    const { result } = renderHook(() => useDrivers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.drivers).toHaveLength(2))
    act(() => result.current.add({ full_name: 'נהג חדש', phone_number: '050-0' }))
    await waitFor(() => expect(posted).toBe(true))
  })

  it('patches a driver on update', async () => {
    let patched: Record<string, unknown> | null = null
    server.use(
      http.patch(`${FLEET}/drivers/:id`, async ({ params, request }) => {
        patched = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ driver_id: params.id, full_name: 'n', phone_number: 'p', status: 'inactive', ...patched })
      }),
    )
    const { result } = renderHook(() => useDrivers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.drivers).toHaveLength(2))
    act(() => result.current.update({ id: 'd1', patch: { status: 'inactive' } }))
    await waitFor(() => expect(patched).toMatchObject({ status: 'inactive' }))
  })

  it('hits delete by UUID and rolls back on error', async () => {
    let hit = false
    server.use(
      http.delete(`${FLEET}/drivers/:id`, ({ params }) => {
        hit = params.id === 'd2'
        return HttpResponse.json({}, { status: 500 })
      }),
    )
    const { result } = renderHook(() => useDrivers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.drivers).toHaveLength(2))
    act(() => result.current.remove('d2'))
    await waitFor(() => expect(hit).toBe(true))
    await waitFor(() => expect(result.current.drivers.find((d) => d.id === 'd2')).toBeDefined())
  })
})
