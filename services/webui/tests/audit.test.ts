import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { postImpersonationAudit } from '@/lib/audit'

const FLEET = 'http://localhost:8000'

describe('postImpersonationAudit', () => {
  it('posts a system-admin caller (impersonator, NO company_id) + company_admin body', async () => {
    let caller: unknown
    let body: unknown
    server.use(
      http.post(`${FLEET}/sysadmin/impersonation-audit`, async ({ request }) => {
        caller = JSON.parse(request.headers.get('X-Caller-Context') ?? '{}')
        body = await request.json()
        return HttpResponse.json({ status: 'ok' }, { status: 201 })
      }),
    )

    await postImpersonationAudit({ operatorId: 'op1', companyId: 'co1', action: 'start', detail: 'enter' })

    // The audit context must be a company-less admin carrying the operator, or the
    // endpoint 403s (the act-as company_admin context can't reach /sysadmin/*).
    expect(caller).toEqual({ role: 'admin', impersonator: 'op1' })
    expect(body).toEqual({
      company_id: 'co1',
      effective_role: 'company_admin',
      action: 'start',
      detail: 'enter',
    })
  })

  it('omits detail when not provided', async () => {
    let body: Record<string, unknown> = {}
    server.use(
      http.post(`${FLEET}/sysadmin/impersonation-audit`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ status: 'ok' }, { status: 201 })
      }),
    )

    await postImpersonationAudit({ operatorId: 'op2', companyId: 'co2', action: 'write' })

    expect(body).toEqual({ company_id: 'co2', effective_role: 'company_admin', action: 'write' })
    expect('detail' in body).toBe(false)
  })
})
