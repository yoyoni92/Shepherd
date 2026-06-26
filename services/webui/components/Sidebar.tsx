'use client'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { signOut } from 'next-auth/react'
import {
  LayoutDashboard,
  Truck,
  User,
  Building2,
  TriangleAlert,
  CalendarCheck,
  Wrench,
  Settings,
  Activity,
  LogOut,
  Bot,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { useCustomers } from '@/hooks/useCustomers'
import { useEvents } from '@/hooks/useEvents'
import { useAccidents } from '@/hooks/useAccidents'
import { useHealth } from '@/hooks/useHealth'
import { openCount } from '@/lib/events'
import { summarizeHealth, type Overall } from '@/lib/health'

type NavItem = { href: string; label: string; Icon: LucideIcon; badge?: 'vehicles' | 'drivers' | 'customers' | 'events' | 'accidents'; statusDot?: boolean }

const NAV: NavItem[] = [
  { href: '/dashboard', label: 'לוח בקרה', Icon: LayoutDashboard },
  { href: '/vehicles', label: 'רכבים', Icon: Truck, badge: 'vehicles' },
  { href: '/drivers', label: 'נהגים', Icon: User, badge: 'drivers' },
  { href: '/customers', label: 'לקוחות', Icon: Building2, badge: 'customers' },
  { href: '/events', label: 'משימות', Icon: TriangleAlert, badge: 'events' },
  { href: '/accidents', label: 'תאונות', Icon: ShieldAlert, badge: 'accidents' },
  { href: '/attendance', label: 'נוכחות', Icon: CalendarCheck },
  { href: '/bot', label: 'ניהול בוט', Icon: Bot },
  { href: '/maintenance-types', label: 'סוגי טיפול', Icon: Wrench },
  { href: '/config', label: 'הגדרות', Icon: Settings },
  { href: '/health', label: 'מצב מערכת', Icon: Activity, statusDot: true },
]

const HEALTH_DOT: Record<Overall, string> = { ok: '#34d399', degraded: '#fbbf24', down: '#f87171' }

export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const pathname = usePathname()
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const { customers } = useCustomers()
  const { events } = useEvents()
  const { accidents } = useAccidents()
  const { services } = useHealth()
  const healthColor = HEALTH_DOT[summarizeHealth(services)]
  const counts: Record<string, number> = {
    vehicles: vehicles.length,
    drivers: drivers.length,
    customers: customers.length,
    events: openCount(events),
    accidents: accidents.length,
  }

  return (
    <aside
      className="bg-raised border-l border-line flex flex-col sticky top-0 h-screen shrink-0 transition-[width] duration-200 ease-out"
      style={{ width: collapsed ? 74 : 244, minWidth: collapsed ? 74 : 244, padding: '16px 14px' }}
    >
      <div className="flex items-center justify-center px-1.5 mb-3.5" style={{ height: collapsed ? 56 : 'auto' }}>
        {collapsed ? (
          <div
            className="flex items-center justify-center shrink-0"
            style={{ width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg,#3b82f6,#1d4ed8)' }}
          >
            <Truck size={19} color="#fff" />
          </div>
        ) : (
          <Image src="/logo.png" alt="Shepherd" width={196} height={196} priority style={{ width: 196, height: 'auto', borderRadius: 12 }} />
        )}
      </div>

      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, Icon, badge, statusDot }) => {
          const active = pathname === href || pathname?.startsWith(href + '/')
          const count = badge ? counts[badge] : undefined
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className="flex items-center gap-3 w-full rounded-[10px] text-sm font-semibold cursor-pointer"
              style={{
                padding: '11px 12px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active ? 'linear-gradient(135deg,#3b82f6,#2563eb)' : 'transparent',
                color: active ? '#fff' : '#94a3b8',
                boxShadow: active ? '0 6px 16px rgba(59,130,246,.32)' : 'none',
              }}
            >
              <span className="flex items-center justify-center" style={{ minWidth: 20 }}>
                <Icon size={19} />
              </span>
              {!collapsed && <span className="flex-1 text-right whitespace-nowrap">{label}</span>}
              {!collapsed && statusDot && (
                <span
                  className="rounded-full"
                  style={{ width: 8, height: 8, background: healthColor, boxShadow: `0 0 0 3px ${healthColor}33` }}
                />
              )}
              {!collapsed && count != null && (
                <span
                  className="text-[11px] font-bold rounded-full text-center"
                  style={{
                    padding: '1px 8px',
                    minWidth: 20,
                    background: active ? 'rgba(255,255,255,.15)' : 'var(--line)',
                    color: active ? '#fff' : 'var(--muted)',
                  }}
                >
                  {count}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto pt-3.5 border-t border-line">
        <button
          onClick={() => signOut({ callbackUrl: '/' })}
          className="w-full flex items-center gap-[11px] bg-transparent border-0 text-faint rounded-[9px] cursor-pointer text-sm font-semibold hover:text-ink"
          style={{ padding: '10px 12px', justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          <span className="flex justify-center" style={{ minWidth: 20 }}>
            <LogOut size={18} />
          </span>
          {!collapsed && <span className="whitespace-nowrap">יציאה</span>}
        </button>
      </div>
    </aside>
  )
}
