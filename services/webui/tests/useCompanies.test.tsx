import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useCompanies } from '@/hooks/useCompanies'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useCompanies', () => {
  it('lists companies', async () => {
    const { result } = renderHook(() => useCompanies(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.companies.length).toBeGreaterThan(0))
    expect(result.current.companies[0]).toMatchObject({ company_id: 'co1', name: 'ברירת מחדל', is_active: true })
  })

  it('creates, toggles active and deletes a company', async () => {
    let posted = false
    let patched: Record<string, unknown> | null = null
    let deleted = false
    server.use(
      http.post(`${FLEET}/companies`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ company_id: 'co99', is_active: true, created_at: '2026-06-26T00:00:00Z', ...(await request.json() as object) }, { status: 201 })
      }),
      http.patch(`${FLEET}/companies/:id`, async ({ params, request }) => {
        patched = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ company_id: params.id, name: 'n', is_active: false, created_at: '2026-06-26T00:00:00Z', ...patched })
      }),
      http.delete(`${FLEET}/companies/:id`, () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { result } = renderHook(() => useCompanies(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.companies.length).toBeGreaterThan(0))
    await act(async () => { await result.current.add({ name: 'חדשה' }) })
    await waitFor(() => expect(posted).toBe(true))
    act(() => result.current.update({ id: 'co1', patch: { is_active: false } }))
    await waitFor(() => expect(patched).toEqual({ is_active: false }))
    act(() => result.current.remove('co2'))
    await waitFor(() => expect(deleted).toBe(true))
  })
})
