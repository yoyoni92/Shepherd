import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useCustomers } from '@/hooks/useCustomers'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useCustomers', () => {
  it('builds the list + id->name map from the real customers', async () => {
    const { result } = renderHook(() => useCustomers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.customers.length).toBeGreaterThan(0))
    expect(result.current.customerById['c1']).toBe('אלקטרה מערכות')
    expect(result.current.customers[0]).toMatchObject({ id: 'c1', name: 'אלקטרה מערכות', status: 'active' })
  })

  it('creates, updates and deletes a customer', async () => {
    let posted = false
    let patched = false
    let deleted = false
    server.use(
      http.post(`${FLEET}/customers`, async ({ request }) => {
        posted = true
        return HttpResponse.json({ customer_id: 'c99', status: 'active', ...(await request.json() as object) }, { status: 201 })
      }),
      http.patch(`${FLEET}/customers/:id`, async ({ params, request }) => {
        patched = true
        return HttpResponse.json({ customer_id: params.id, full_name: 'n', status: 'active', ...(await request.json() as object) })
      }),
      http.delete(`${FLEET}/customers/:id`, () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { result } = renderHook(() => useCustomers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.customers.length).toBeGreaterThan(0))
    act(() => result.current.add({ full_name: 'לקוח חדש' }))
    await waitFor(() => expect(posted).toBe(true))
    act(() => result.current.update({ id: 'c1', patch: { email: 'x@y.co.il' } }))
    await waitFor(() => expect(patched).toBe(true))
    act(() => result.current.remove('c1'))
    await waitFor(() => expect(deleted).toBe(true))
  })
})
