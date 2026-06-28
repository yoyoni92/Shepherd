import { describe, it, expect } from 'vitest'
import { isRouteAllowed } from '@/lib/routeAccess'

describe('isRouteAllowed', () => {
  it('lets a system admin reach every route', () => {
    for (const p of ['/dashboard', '/companies', '/access', '/health', '/config', '/bot']) {
      expect(isRouteAllowed(p, 'admin')).toBe(true)
    }
  })

  it('denies a company_admin the system-only routes (incl. bot)', () => {
    for (const p of ['/companies', '/access', '/health', '/config', '/bot']) {
      expect(isRouteAllowed(p, 'company_admin')).toBe(false)
      expect(isRouteAllowed(p + '/sub', 'company_admin')).toBe(false)
    }
  })

  it('allows a company_admin the operational routes', () => {
    for (const p of ['/dashboard', '/vehicles', '/drivers', '/customers', '/events', '/attendance', '/accidents', '/upload']) {
      expect(isRouteAllowed(p, 'company_admin')).toBe(true)
    }
  })
})
