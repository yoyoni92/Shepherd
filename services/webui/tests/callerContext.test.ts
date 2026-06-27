import { describe, it, expect } from 'vitest'
import { buildCallerContext } from '@/lib/callerContext'

describe('buildCallerContext', () => {
  it('locks a company_admin to its own company_id (ignores the cookie)', () => {
    const ctx = JSON.parse(buildCallerContext({ role: 'company_admin', company_id: 'co1' }, 'co2'))
    expect(ctx).toEqual({ role: 'company_admin', company_id: 'co1' })
  })

  it('scopes a system admin to the active company from the switcher cookie', () => {
    const ctx = JSON.parse(buildCallerContext({ role: 'admin', company_id: null }, 'co5'))
    expect(ctx).toEqual({ role: 'admin', company_id: 'co5' })
  })

  it('omits company_id for a system admin when no company is selected', () => {
    expect(JSON.parse(buildCallerContext({ role: 'admin', company_id: null }, undefined))).toEqual({ role: 'admin' })
  })

  it('treats the "all" sentinel as cross-company (no company_id)', () => {
    expect(JSON.parse(buildCallerContext({ role: 'admin', company_id: null }, 'all'))).toEqual({ role: 'admin' })
  })
})
