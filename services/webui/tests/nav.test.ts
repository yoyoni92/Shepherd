import { describe, it, expect } from 'vitest'
import { filterByRole, filterNav, NAV } from '@/lib/nav'

const SAMPLE = [
  { href: '/dashboard' },
  { href: '/companies', allowedRoles: ['admin'] },
  { href: '/access', allowedRoles: ['admin'] },
  { href: '/bot', allowedRoles: undefined },
]

describe('filterByRole', () => {
  it('shows admin-only items to a system admin', () => {
    expect(filterByRole(SAMPLE, 'admin').map((i) => i.href)).toEqual(['/dashboard', '/companies', '/access', '/bot'])
  })

  it('hides admin-only items from a company_admin', () => {
    expect(filterByRole(SAMPLE, 'company_admin').map((i) => i.href)).toEqual(['/dashboard', '/bot'])
  })

  it('shows only unrestricted items when the role is unknown', () => {
    expect(filterByRole(SAMPLE, undefined).map((i) => i.href)).toEqual(['/dashboard', '/bot'])
  })
})

describe('filterNav (Feature 5: attendance feature flag)', () => {
  it('hides Attendance from a company_admin whose company has the flag off', () => {
    const hrefs = filterNav(NAV, 'company_admin', { attendance: false }).map((i) => i.href)
    expect(hrefs).not.toContain('/attendance')
    expect(hrefs).toContain('/dashboard') // unflagged items remain
  })

  it('hides Attendance from a company_admin with no feature flags', () => {
    const hrefs = filterNav(NAV, 'company_admin', undefined).map((i) => i.href)
    expect(hrefs).not.toContain('/attendance')
  })

  it('shows Attendance to a company_admin whose company has the flag on', () => {
    const hrefs = filterNav(NAV, 'company_admin', { attendance: true }).map((i) => i.href)
    expect(hrefs).toContain('/attendance')
  })

  it('hides Attendance from a system admin (Feature 7: operators do not run attendance)', () => {
    const off = filterNav(NAV, 'admin', { attendance: false }).map((i) => i.href)
    expect(off).not.toContain('/attendance')
    // Even if a flag leaks through, a system admin never sees the attendance item.
    const on = filterNav(NAV, 'admin', { attendance: true }).map((i) => i.href)
    expect(on).not.toContain('/attendance')
    expect(on).toContain('/companies') // system-only tabs remain
  })
})

describe('NAV top-level structure (Feature 4 consolidation)', () => {
  const hrefs = NAV.map((i) => i.href)

  it('keeps the parent tabs that absorb the nested sections', () => {
    expect(hrefs).toContain('/vehicles')
    expect(hrefs).toContain('/events')
  })

  it('drops maintenance-types, accidents and chat as top-level items', () => {
    expect(hrefs).not.toContain('/maintenance-types')
    expect(hrefs).not.toContain('/accidents')
    expect(hrefs).not.toContain('/chat')
    expect(hrefs).not.toContain('/assistant')
  })
})
