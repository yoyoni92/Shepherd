import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { fetchVehicles, updateConfig, fetchAccidents, createAccident } from '@/lib/api/fleet'

const FLEET = process.env.NEXT_PUBLIC_FLEET_BASE ?? 'http://localhost:8000'

describe('API client error paths', () => {
  it('fetchVehicles throws on non-ok response', async () => {
    server.use(http.get(`${FLEET}/vehicles`, () => HttpResponse.json({}, { status: 500 })))
    await expect(fetchVehicles()).rejects.toThrow('Fleet API /vehicles: 500')
  })

  it('updateConfig throws on non-ok response', async () => {
    server.use(http.put(`${FLEET}/config/:key`, () => HttpResponse.json({}, { status: 403 })))
    await expect(updateConfig('x', 1)).rejects.toThrow('Fleet API PUT /config/x: 403')
  })

  it('fetchAccidents throws on non-ok response', async () => {
    server.use(http.get(`${FLEET}/accidents`, () => HttpResponse.json({}, { status: 500 })))
    await expect(fetchAccidents()).rejects.toThrow('Fleet API /accidents: 500')
  })

  it('createAccident throws on non-ok response', async () => {
    server.use(http.post(`${FLEET}/accidents`, () => HttpResponse.json({}, { status: 403 })))
    await expect(createAccident({ vehicle_id: 'v1', datetime: '2026-06-21T10:00:00', attachments: [] })).rejects.toThrow('Fleet API POST /accidents: 403')
  })
})
