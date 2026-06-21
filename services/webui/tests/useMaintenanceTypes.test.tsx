import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useMaintenanceTypes } from '@/hooks/useMaintenanceTypes'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useMaintenanceTypes', () => {
  it('lists the catalog and adapts it', async () => {
    const { result } = renderHook(() => useMaintenanceTypes(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.types.length).toBeGreaterThan(0))
    expect(result.current.types[0]).toMatchObject({ id: 'mt1', name: 'קטן ואז גדול', intervalKm: 10000 })
    expect(result.current.types[0].steps).toEqual(['קטן', 'גדול'])
  })

  it('creates, updates and deletes a type', async () => {
    let posted = false
    let patched = false
    let deleted = false
    server.use(
      http.post(`${FLEET}/maintenance-types`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ id: 'mt99', ...(await request.json() as object) }, { status: 201 })
      }),
      http.patch(`${FLEET}/maintenance-types/:id`, async ({ params, request }) => {
        patched = true
        return HttpResponse.json({ id: params.id, name: 'n', interval_km: 1, steps: ['x'], ...(await request.json() as object) })
      }),
      http.delete(`${FLEET}/maintenance-types/:id`, () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { result } = renderHook(() => useMaintenanceTypes(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.types.length).toBeGreaterThan(0))
    act(() => result.current.add({ name: 'חדש', interval_km: 9000, steps: ['א', 'ב'] }))
    await waitFor(() => expect(posted).toBe(true))
    act(() => result.current.update({ id: 'mt1', patch: { interval_km: 7000 } }))
    await waitFor(() => expect(patched).toBe(true))
    act(() => result.current.remove('mt2'))
    await waitFor(() => expect(deleted).toBe(true))
  })

  it('surfaces a 409 delete error message', async () => {
    server.use(
      http.delete(`${FLEET}/maintenance-types/:id`, () =>
        HttpResponse.json({ detail: '3 רכבים משתמשים בסוג טיפול זה' }, { status: 409 }),
      ),
    )
    const { result } = renderHook(() => useMaintenanceTypes(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.types.length).toBeGreaterThan(0))
    act(() => result.current.remove('mt1'))
    await waitFor(() => expect(result.current.removeError?.message).toContain('רכבים'))
  })
})
