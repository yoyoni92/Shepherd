'use client'
import Link from 'next/link'
import { Truck, User, CheckSquare, FileText, Ticket, Wrench, type LucideIcon } from 'lucide-react'
import { useKpis } from '@/hooks/useKpis'
import { useMissions } from '@/hooks/useMissions'
import { useEvents } from '@/hooks/useEvents'
import { isOpen } from '@/lib/domain'
import { alertsFromEvents } from '@/lib/alerts'
import type { Kpis } from '@/lib/kpis'
import { Card } from '@/components/ui/card'
import { PRIORITY_META, MISSION_STATUS_META, ALERT_COLOR } from '@/components/meta'

type Trend = 'up' | 'down' | 'flat'

const TREND_STYLE: Record<Trend, React.CSSProperties> = {
  up: { color: '#34d399', background: 'rgba(52,211,153,.1)' },
  down: { color: '#f87171', background: 'rgba(248,113,113,.1)' },
  flat: { color: '#94a3b8', background: '#10131f' },
}

interface Tile {
  key: keyof Kpis
  label: string
  Icon: LucideIcon
  color: string
  bg: string
  trend: string
  trendType: Trend
}

const TILES: Tile[] = [
  { key: 'vehicles', label: 'סך רכבים בצי', Icon: Truck, color: '#60a5fa', bg: 'rgba(59,130,246,.12)', trend: '+2', trendType: 'up' },
  { key: 'activeDrivers', label: 'נהגים פעילים', Icon: User, color: '#34d399', bg: 'rgba(52,211,153,.12)', trend: 'יציב', trendType: 'flat' },
  { key: 'openEvents', label: 'משימות פתוחות', Icon: CheckSquare, color: '#a78bfa', bg: 'rgba(167,139,250,.12)', trend: '+3', trendType: 'up' },
  { key: 'docsExpiring30d', label: 'מסמכים פגי תוקף', Icon: FileText, color: '#fbbf24', bg: 'rgba(251,191,36,.12)', trend: '30 יום', trendType: 'down' },
  { key: 'unpaidTickets', label: 'דוחות לא שולמו', Icon: Ticket, color: '#f472b6', bg: 'rgba(244,114,182,.12)', trend: '₪1.2K', trendType: 'down' },
  { key: 'maintenanceDue', label: 'טיפולים נדרשים', Icon: Wrench, color: '#fb923c', bg: 'rgba(251,146,60,.12)', trend: 'דחוף', trendType: 'down' },
]

export default function DashboardPage() {
  const { data: kpis } = useKpis()
  const { missions } = useMissions()
  const { events } = useEvents()

  const alerts = alertsFromEvents(events)
  const topMissions = missions.filter(isOpen).slice(0, 4)

  return (
    <div className="animate-fade-up">
      <div className="grid gap-3.5 mb-[22px]" style={{ gridTemplateColumns: 'repeat(6,1fr)' }}>
        {TILES.map(({ key, label, Icon, color, bg, trend, trendType }) => (
          <Card key={key} className="rounded-[13px]" style={{ padding: '16px 16px 15px' }}>
            <div className="flex items-center justify-between mb-3">
              <div
                className="flex items-center justify-center"
                style={{ width: 34, height: 34, borderRadius: 9, background: bg, color }}
              >
                <Icon size={17} />
              </div>
              <span
                className="text-[11px] font-bold rounded-md"
                style={{ padding: '2px 7px', ...TREND_STYLE[trendType] }}
              >
                {trend}
              </span>
            </div>
            <div className="text-[30px] font-extrabold leading-none" style={{ letterSpacing: '-1px' }}>
              {kpis ? kpis[key] : '–'}
            </div>
            <div className="text-[12.5px] text-muted mt-[5px]">{label}</div>
          </Card>
        ))}
      </div>

      <div className="grid gap-[18px]" style={{ gridTemplateColumns: '1.3fr 1fr' }}>
        {/* Alerts */}
        <Card style={{ padding: '18px 20px' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[15px] font-bold">התראות פעילות</div>
            <span className="text-[11px] text-faint bg-panel2 border border-control rounded-full" style={{ padding: '3px 9px' }}>
              {alerts.length} פתוחות
            </span>
          </div>
          <div className="flex flex-col gap-2.5">
            {alerts.length === 0 && <div className="text-[13px] text-faint">אין התראות פעילות</div>}
            {alerts.map((a) => {
              const c = ALERT_COLOR[a.severity]
              return (
                <div
                  key={a.id}
                  className="flex items-center gap-[13px] bg-bg border border-line rounded-[11px]"
                  style={{ padding: '12px 13px' }}
                >
                  <span
                    className="rounded-full"
                    style={{ minWidth: 9, width: 9, height: 9, background: c, boxShadow: `0 0 0 3px ${c}22` }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13.5px] font-semibold">{a.title}</div>
                    <div className="text-[11.5px] text-faint">{a.meta}</div>
                  </div>
                  <span
                    className="text-[10.5px] font-bold rounded-md whitespace-nowrap"
                    style={{ color: c, background: `${c}1f`, padding: '3px 9px' }}
                  >
                    {a.tag}
                  </span>
                </div>
              )
            })}
          </div>
        </Card>

        {/* Urgent missions */}
        <Card style={{ padding: '18px 20px' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[15px] font-bold">
              משימות דחופות <span className="text-[10px] text-dim font-normal">דמו · ללא API</span>
            </div>
            <Link href="/missions" className="text-[12px] text-accent font-semibold">
              הצג הכל ←
            </Link>
          </div>
          <div className="flex flex-col gap-[11px]">
            {topMissions.length === 0 && <div className="text-[13px] text-faint">אין משימות פתוחות</div>}
            {topMissions.map((m) => (
              <div key={m.id} className="flex items-center gap-3">
                <span
                  className="rounded"
                  style={{ minWidth: 4, width: 4, height: 34, background: PRIORITY_META[m.priority].color }}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-[13.5px] font-semibold truncate">{m.title}</div>
                  <div className="text-[11.5px] text-faint">
                    {m.driver} · {m.due}
                  </div>
                </div>
                <span
                  className="text-[11.5px] font-bold rounded-md whitespace-nowrap"
                  style={{
                    color: MISSION_STATUS_META[m.status].color,
                    background: MISSION_STATUS_META[m.status].bg,
                    padding: '5px 11px',
                  }}
                >
                  {MISSION_STATUS_META[m.status].label}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
