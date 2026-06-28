import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useAppUsers } from '@/hooks/useAppUsers'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useAppUsers', () => {
  it('lists app users (no password_hash leaks)', async () => {
    const { result } = renderHook(() => useAppUsers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.users.length).toBeGreaterThan(0))
    expect(result.current.users[0]).toMatchObject({
      user_id: 'au1',
      email: 'admin@shepherd.ai',
      role: 'admin',
      is_system_admin: true,
      phone_number: '+972500000000',
    })
    expect(result.current.users[1]).toMatchObject({ is_system_admin: false, phone_number: null })
    expect(Object.keys(result.current.users[0])).not.toContain('password_hash')
  })

  it('creates a system admin (no company, phone) with is_system_admin in the payload', async () => {
    let createdBody: Record<string, unknown> | null = null
    server.use(
      http.post(`${FLEET}/app-users`, async ({ request }) => {
        createdBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(
          { user_id: 'au100', is_active: true, created_at: '2026-06-26T00:00:00Z', ...createdBody },
          { status: 201 },
        )
      }),
    )
    const { result } = renderHook(() => useAppUsers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.users.length).toBeGreaterThan(0))
    await act(async () => {
      await result.current.add({
        email: 'sa@shepherd.ai',
        password: 'pw',
        role: 'admin',
        company_id: null,
        is_system_admin: true,
        phone_number: '+972511111111',
      })
    })
    await waitFor(() =>
      expect(createdBody).toMatchObject({
        role: 'admin',
        company_id: null,
        is_system_admin: true,
        phone_number: '+972511111111',
      }),
    )
  })

  it('creates a company_admin, resets password, toggles active and deletes', async () => {
    let createdBody: Record<string, unknown> | null = null
    let patchedBody: Record<string, unknown> | null = null
    let deleted = false
    server.use(
      http.post(`${FLEET}/app-users`, async ({ request }) => {
        createdBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ user_id: 'au99', is_active: true, is_system_admin: false, phone_number: null, created_at: '2026-06-26T00:00:00Z', ...createdBody }, { status: 201 })
      }),
      http.patch(`${FLEET}/app-users/:id`, async ({ params, request }) => {
        patchedBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ user_id: params.id, email: 'e@x.io', role: 'company_admin', company_id: 'co1', is_active: true, name: null, is_system_admin: false, phone_number: null, created_at: '2026-06-26T00:00:00Z', ...patchedBody })
      }),
      http.delete(`${FLEET}/app-users/:id`, () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { result } = renderHook(() => useAppUsers(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.users.length).toBeGreaterThan(0))
    await act(async () => {
      await result.current.add({ email: 'ca@co2.io', password: 'pw', role: 'company_admin', company_id: 'co1' })
    })
    await waitFor(() => expect(createdBody).toMatchObject({ role: 'company_admin', company_id: 'co1' }))
    act(() => result.current.update({ id: 'au2', patch: { password: 'newpw' } }))
    await waitFor(() => expect(patchedBody).toEqual({ password: 'newpw' }))
    act(() => result.current.update({ id: 'au2', patch: { is_active: false } }))
    await waitFor(() => expect(patchedBody).toEqual({ is_active: false }))
    act(() => result.current.remove('au2'))
    await waitFor(() => expect(deleted).toBe(true))
  })
})
