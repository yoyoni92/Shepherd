'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Menu, Search, Bell } from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { useEvents } from '@/hooks/useEvents'
import { useCompanies } from '@/hooks/useCompanies'
import { sortEvents, openCount } from '@/lib/events'
import { initials, fmtDate } from '@/lib/domain'
import { SEVERITY_META, EVENT_TYPE_LABEL } from '@/components/meta'
import { ThemeToggle } from '@/components/ThemeToggle'

function useTitle(): [string, string] {
  const pathname = usePathname() ?? ''
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const seg = pathname.split('/')[1] || 'dashboard'
  const map: Record<string, [string, string]> = {
    dashboard: ['לוח בקרה', 'סקירת מצב הצי בזמן אמת'],
    vehicles: ['רכבים', `${vehicles.length} רכבים בצי · ניהול וסינון`],
    drivers: ['נהגים', `${drivers.length} נהגים רשומים`],
    customers: ['לקוחות', 'ניהול לקוחות הצי'],
    events: ['משימות', 'משימות תפעוליות לפי חומרה'],
    attendance: ['נוכחות עובדים', 'דוח כניסה/יציאה חודשי'],
    'maintenance-types': ['סוגי טיפול', 'קטלוג מחזורי טיפול לרכבים'],
    config: ['הגדרות מערכת', 'עריכת ספי התראה ותחזוקה'],
    health: ['מצב מערכת', 'זמינות שירותי הצד השלישי בזמן אמת'],
    upload: ['העלאת מסמכים', 'ערוץ קליטה דרך הקונסולה'],
  }
  return map[seg] ?? ['ניהול צי רכב', '']
}

function getCookie(name: string): string {
  if (typeof document === 'undefined') return ''
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return m ? decodeURIComponent(m[1]) : ''
}

// System-admin company switcher: selecting a company sets the `active_company_id`
// cookie (cleared for "all"), which the Fleet proxy reads into X-Caller-Context.
function CompanySwitcher() {
  const router = useRouter()
  const { companies } = useCompanies()
  const [active, setActive] = useState(() => getCookie('active_company_id'))

  const onChange = (value: string) => {
    setActive(value === 'all' ? '' : value)
    document.cookie =
      value === 'all'
        ? 'active_company_id=; path=/; max-age=0; samesite=lax'
        : `active_company_id=${encodeURIComponent(value)}; path=/; max-age=31536000; samesite=lax`
    router.refresh()
  }

  return (
    <select
      aria-label="בחירת חברה פעילה"
      value={active || 'all'}
      onChange={(e) => onChange(e.target.value)}
      className="bg-bg border border-control rounded-[9px] text-[13px] text-ink outline-none focus:border-accent"
      style={{ padding: '9px 12px', maxWidth: 200 }}
    >
      <option value="all">כל החברות</option>
      {companies.map((c) => (
        <option key={c.company_id} value={c.company_id}>
          {c.name}
        </option>
      ))}
    </select>
  )
}

export function Topbar({ onToggle }: { onToggle: () => void }) {
  const [title, sub] = useTitle()
  const { data: session } = useSession()
  const { events } = useEvents()
  const [notifOpen, setNotifOpen] = useState(false)
  const role = session?.user?.role
  const name = session?.user?.name ?? 'אבי כהן'
  const roleLabel = role === 'company_admin' ? 'מנהל חברה' : 'מנהל מערכת'

  const open = sortEvents(events.filter((e) => e.status === 'open')).slice(0, 6)
  const openTotal = openCount(events)

  return (
    <header
      className="border-b border-line flex items-center gap-4 bg-raised shrink-0"
      style={{ height: 64, minHeight: 64, padding: '0 26px' }}
    >
      <button
        onClick={onToggle}
        aria-label="כווץ תפריט"
        className="bg-panel2 border border-control rounded-lg w-9 h-9 flex items-center justify-center text-muted cursor-pointer hover:text-ink"
      >
        <Menu size={17} />
      </button>
      <div>
        <div className="text-[17px] font-extrabold" style={{ letterSpacing: '-.2px' }}>
          {title}
        </div>
        <div className="text-[11.5px] text-faint">{sub}</div>
      </div>
      <div className="flex-1" />
      {role === 'admin' && <CompanySwitcher />}
      <div className="relative flex items-center">
        <Search size={15} className="absolute right-[11px] text-dim" />
        <input
          placeholder="חיפוש רכב, נהג, משימה…"
          className="bg-bg border border-control rounded-[9px] text-[13px] text-ink outline-none focus:border-accent"
          style={{ width: 230, padding: '9px 34px 9px 12px' }}
        />
      </div>

      <ThemeToggle />

      <div className="relative">
        <button
          aria-label="משימות פתוחות"
          onClick={() => setNotifOpen((o) => !o)}
          className="relative bg-panel2 border border-control rounded-lg w-9 h-9 flex items-center justify-center text-muted cursor-pointer hover:text-ink"
        >
          <Bell size={17} />
          {openTotal > 0 && (
            <span
              className="absolute bg-danger text-white text-[9px] font-bold rounded-lg flex items-center justify-center"
              style={{ top: -3, left: -3, minWidth: 15, height: 15, padding: '0 3px' }}
            >
              {openTotal}
            </span>
          )}
        </button>

        {notifOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setNotifOpen(false)} />
            <div
              className="absolute z-50 bg-panel border border-line rounded-[12px] overflow-hidden"
              style={{ top: 44, left: 0, width: 320, boxShadow: '0 18px 40px rgba(0,0,0,.4)' }}
            >
              <div className="flex items-center justify-between border-b border-line" style={{ padding: '11px 14px' }}>
                <div className="text-[13.5px] font-bold">משימות פתוחות</div>
                <span className="text-[11px] text-faint">{openTotal}</span>
              </div>
              <div className="max-h-[320px] overflow-y-auto">
                {open.length === 0 && <div className="text-[12.5px] text-faint" style={{ padding: '14px' }}>אין משימות פתוחות</div>}
                {open.map((e) => {
                  const sev = SEVERITY_META[e.severity] ?? SEVERITY_META.info
                  return (
                    <Link
                      key={e.event_id}
                      href="/events"
                      onClick={() => setNotifOpen(false)}
                      className="flex items-center gap-2.5 border-b border-divider hover:bg-panel2"
                      style={{ padding: '10px 14px' }}
                    >
                      <span className="rounded-full shrink-0" style={{ width: 8, height: 8, background: sev.color }} />
                      <div className="flex-1 min-w-0">
                        <div className="text-[12.5px] font-semibold truncate">{e.message}</div>
                        <div className="text-[11px] text-faint">
                          {EVENT_TYPE_LABEL[e.event_type] ?? e.event_type} · <span className="ltr">{fmtDate(e.triggered_ts)}</span>
                        </div>
                      </div>
                    </Link>
                  )
                })}
              </div>
              <Link
                href="/events"
                onClick={() => setNotifOpen(false)}
                className="block text-center text-[12px] text-accent font-semibold border-t border-line"
                style={{ padding: '10px' }}
              >
                הצג את כל המשימות ←
              </Link>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-2.5 pr-1.5 border-r border-line mr-0.5">
        <div
          className="flex items-center justify-center font-bold text-[13px] text-white"
          style={{ width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg,#6366f1,#4338ca)' }}
        >
          {initials(name)}
        </div>
        <div className="leading-[1.25]">
          <div className="text-[13px] font-bold">{name}</div>
          <div className="text-[11px] text-faint">{roleLabel}</div>
        </div>
      </div>
    </header>
  )
}
