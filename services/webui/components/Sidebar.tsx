'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOut } from 'next-auth/react'
import {
  LayoutDashboard,
  Truck,
  User,
  TriangleAlert,
  CalendarCheck,
  Settings,
  MessageSquare,
  LogOut,
  type LucideIcon,
} from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { useEvents } from '@/hooks/useEvents'
import { openCount } from '@/lib/events'

type NavItem = { href: string; label: string; Icon: LucideIcon; badge?: 'vehicles' | 'drivers' | 'events' }

const NAV: NavItem[] = [
  { href: '/dashboard', label: 'לוח בקרה', Icon: LayoutDashboard },
  { href: '/vehicles', label: 'רכבים', Icon: Truck, badge: 'vehicles' },
  { href: '/drivers', label: 'נהגים', Icon: User, badge: 'drivers' },
  { href: '/events', label: 'אירועים', Icon: TriangleAlert, badge: 'events' },
  { href: '/attendance', label: 'נוכחות', Icon: CalendarCheck },
  { href: '/config', label: 'הגדרות', Icon: Settings },
  { href: '/chat', label: 'צ׳אט ועוזר', Icon: MessageSquare },
]

export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const pathname = usePathname()
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const { events } = useEvents()
  const counts: Record<string, number> = {
    vehicles: vehicles.length,
    drivers: drivers.length,
    events: openCount(events),
  }

  return (
    <aside
      className="bg-raised border-l border-line flex flex-col sticky top-0 h-screen shrink-0 transition-[width] duration-200 ease-out"
      style={{ width: collapsed ? 74 : 244, minWidth: collapsed ? 74 : 244, padding: '16px 14px' }}
    >
      <div className="flex items-center gap-[11px] px-1.5 mb-3.5" style={{ height: 56 }}>
        <div
          className="flex items-center justify-center shrink-0"
          style={{
            width: 34,
            height: 34,
            borderRadius: 9,
            background: 'linear-gradient(135deg,#3b82f6,#1d4ed8)',
          }}
        >
          <Truck size={19} color="#fff" />
        </div>
        {!collapsed && (
          <div className="text-[15px] font-extrabold whitespace-nowrap">ניהול צי רכב</div>
        )}
      </div>

      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, Icon, badge }) => {
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
              {!collapsed && count != null && (
                <span
                  className="text-[11px] font-bold rounded-full text-center"
                  style={{
                    padding: '1px 8px',
                    minWidth: 20,
                    background: active ? 'rgba(255,255,255,.15)' : '#1a2030',
                    color: active ? '#fff' : '#94a3b8',
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
