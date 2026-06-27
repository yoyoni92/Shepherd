import {
  LayoutDashboard,
  Truck,
  User,
  Building2,
  TriangleAlert,
  CalendarCheck,
  Settings,
  Activity,
  Bot,
  Landmark,
  KeyRound,
  type LucideIcon,
} from 'lucide-react'

// `allowedRoles` gates visibility by session role (omitted = visible to all).
// `children` is kept (Feature 2 shape) for any future nested nav; Feature 4 nests
// maintenance-types/accidents as in-page tab strips rather than sidebar children.
export type NavItem = {
  href: string
  label: string
  Icon: LucideIcon
  badge?: 'vehicles' | 'drivers' | 'customers' | 'events'
  statusDot?: boolean
  allowedRoles?: string[]
  // Gated behind a company feature flag for company_admins; system admins always see it.
  featureFlag?: string
  children?: NavItem[]
}

// Feature 4 (nav consolidation): maintenance-types lives as a tab inside Vehicles,
// accidents as a tab inside Events, and the Chat/Assistant tab is removed entirely.
export const NAV: NavItem[] = [
  { href: '/dashboard', label: 'לוח בקרה', Icon: LayoutDashboard },
  { href: '/vehicles', label: 'רכבים', Icon: Truck, badge: 'vehicles' },
  { href: '/drivers', label: 'נהגים', Icon: User, badge: 'drivers' },
  { href: '/customers', label: 'לקוחות', Icon: Building2, badge: 'customers' },
  { href: '/events', label: 'משימות', Icon: TriangleAlert, badge: 'events' },
  { href: '/attendance', label: 'נוכחות', Icon: CalendarCheck, featureFlag: 'attendance' },
  { href: '/bot', label: 'ניהול בוט', Icon: Bot },
  { href: '/companies', label: 'חברות', Icon: Landmark, allowedRoles: ['admin'] },
  { href: '/access', label: 'משתמשי גישה', Icon: KeyRound, allowedRoles: ['admin'] },
  { href: '/config', label: 'הגדרות', Icon: Settings, allowedRoles: ['admin'] },
  { href: '/health', label: 'מצב מערכת', Icon: Activity, statusDot: true, allowedRoles: ['admin'] },
]

// Filters navigation items by the session role: an item with no `allowedRoles`
// is visible to everyone; otherwise the role must be listed.
export function filterByRole<T extends { allowedRoles?: string[] }>(items: T[], role?: string): T[] {
  return items.filter((item) => !item.allowedRoles || (role != null && item.allowedRoles.includes(role)))
}

// Full nav filter: role gating, then per-company feature flags. A flag-gated item is
// kept for a system admin (they manage every company) but hidden from a company_admin
// whose active company has the flag off (Feature 5: attendance is opt-in).
export function filterNav<T extends { allowedRoles?: string[]; featureFlag?: string }>(
  items: T[],
  role?: string,
  featureFlags?: Record<string, unknown>,
): T[] {
  return filterByRole(items, role).filter((item) => {
    if (!item.featureFlag) return true
    if (role === 'admin') return true
    return featureFlags?.[item.featureFlag] === true
  })
}
