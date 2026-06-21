import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useVehicles } from '@/hooks/useVehicles'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useVehicles', () => {
  it('fetches and adapts the vehicle list', async () => {
    const { result } = renderHook(() => useVehicles(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.vehicles).toHaveLength(3))
    expect(result.current.vehicles[0].plate).toBe('12-345-67')
    expect(result.current.vehicles[0].make).toBe('Toyota')
  })

  it('posts a VehicleCreate on add', async () => {
    let posted = false
    server.use(
      http.post(`${FLEET}/vehicles`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ vehicle_id: 'v99', ...(await request.json() as object) }, { status: 201 })
      }),
    )
    const { result } = renderHook(() => useVehicles(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.vehicles).toHaveLength(3))
    act(() => result.current.add({ licensing_plate: 'NEW-1', vendor: 'רכב', model: 'חדש' }))
    await waitFor(() => expect(posted).toBe(true))
  })

  it('patches a vehicle on update', async () => {
    let patched: Record<string, unknown> | null = null
    server.use(
      http.patch(`${FLEET}/vehicles/:id`, async ({ params, request }) => {
        patched = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ vehicle_id: params.id, licensing_plate: '12-345-67', ...patched })
      }),
    )
    const { result } = renderHook(() => useVehicles(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.vehicles).toHaveLength(3))
    act(() => result.current.update({ id: 'v1', patch: { vehicle_type: 'truck', current_km: 99000 } }))
    await waitFor(() => expect(patched).toMatchObject({ vehicle_type: 'truck', current_km: 99000 }))
  })

  it('hits delete by UUID and rolls back on error', async () => {
    let hit = false
    server.use(
      http.delete(`${FLEET}/vehicles/:id`, ({ params }) => {
        hit = params.id === 'v3'
        return HttpResponse.json({}, { status: 500 })
      }),
    )
    const { result } = renderHook(() => useVehicles(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.vehicles).toHaveLength(3))
    act(() => result.current.remove('v3'))
    await waitFor(() => expect(hit).toBe(true))
    await waitFor(() => expect(result.current.vehicles.find((v) => v.id === 'v3')).toBeDefined())
  })
})
