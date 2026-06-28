'use client'
import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { readActAsClient } from '@/lib/actAs'
import { Route, Gauge, CalendarClock, FileText, Building2, type LucideIcon } from 'lucide-react'
import { useKpis } from '@/hooks/useKpis'
import { useCustomers } from '@/hooks/useCustomers'
import { useEvents } from '@/hooks/useEvents'
import { sortEvents } from '@/lib/events'
import { fmtDate } from '@/lib/domain'
import { alertsFromEvents } from '@/lib/alerts'
import { KPI_TILE_KEYS, type KpiTile, type KpiTileKey } from '@/lib/kpis'
import { Card } from '@/components/ui/card'
import { HealthSummary } from '@/components/HealthSummary'
import { EVENT_TYPE_LABEL, SEVERITY_META, ALERT_COLOR } from '@/components/meta'

interface TileMeta {
  label: string
  Icon: LucideIcon
  color: string
  bg: string
  goodWhenUp: boolean
  fmt: (v: number) => string
}

const KM = (v: number) => `${Math.round(v).toLocaleString()} ק״מ`
const INT = (v: number) => String(Math.round(v))
const DAYS = (v: number) => `${Math.round(v)} ימים`

const TILE_META: Record<KpiTileKey, TileMeta> = {
  fleetKm7d: { label: 'ק״מ השבוע', Icon: Route, color: '#60a5fa', bg: 'rgba(59,130,246,.12)', goodWhenUp: true, fmt: KM },
  avgKmPerDriver: { label: 'ממוצע ק״מ לנהג', Icon: Gauge, color: '#34d399', bg: 'rgba(52,211,153,.12)', goodWhenUp: true, fmt: KM },
  maintCadence: { label: 'ימים בין טיפולים', Icon: CalendarClock, color: '#a78bfa', bg: 'rgba(167,139,250,.12)', goodWhenUp: true, fmt: DAYS },
  docsExpiring: { label: 'מסמכים פגי תוקף', Icon: FileText, color: '#fbbf24', bg: 'rgba(251,191,36,.12)', goodWhenUp: false, fmt: INT },
  topCustomer: { label: 'לקוח מוביל בק״מ', Icon: Building2, color: '#f472b6', bg: 'rgba(244,114,182,.12)', goodWhenUp: true, fmt: KM },
}

function trendBadge(tile: KpiTile, goodWhenUp: boolean): { text: string; style: React.CSSProperties } {
  if (tile.trend == null) return { text: '—', style: { color: 'var(--muted)', background: 'var(--panel2)' } }
  if (tile.trend === 'flat') return { text: 'יציב', style: { color: 'var(--muted)', background: 'var(--panel2)' } }
  const good = (tile.trend === 'up') === goodWhenUp
  const color = good ? '#34d399' : '#f87171'
  const arrow = tile.trend === 'up' ? '▲' : '▼'
  return { text: `${arrow} ${Math.abs(tile.delta ?? 0).toLocaleString()}`, style: { color, background: `${color}1a` } }
}

export default function DashboardPage() {
  const { data } = useKpis()
  const { customerById } = useCustomers()
  const { events } = useEvents()

  const tiles = data?.tiles ?? KPI_TILE_KEYS.map((key) => ({ key, value: null, delta: null, trend: null }))
  const latest = data?.latest ?? null

  const alerts = alertsFromEvents(events)
  const recent = sortEvents(events).slice(0, 5)

  // System health is system-level: show it only to a system admin operating as
  // themselves (hidden for company admins and while acting-as a company).
  const { data: session } = useSession()
  const [actingAs, setActingAs] = useState(false)
  useEffect(() => setActingAs(!!readActAsClient()), [])
  const showHealth = session?.user?.role === 'admin' && !actingAs

  return (
    <div className="animate-fade-up">
      <div className="grid gap-3.5 mb-[22px]" style={{ gridTemplateColumns: 'repeat(6,1fr)' }}>
        {tiles.map((tile) => {
          const meta = TILE_META[tile.key]
          const badge = trendBadge(tile, meta.goodWhenUp)
          const isTopCustomer = tile.key === 'topCustomer'
          const vcount = latest?.top_customer_vehicle_count ?? null
          const customerName = latest?.top_customer_id ? (customerById[latest.top_customer_id] ?? '—') : '—'
          const sub =
            isTopCustomer && tile.value != null
              ? `${customerName}${vcount != null ? ` · ${vcount} רכבים` : ''}`
              : meta.label
          const flag = isTopCustomer && vcount != null && vcount <= 2
          return (
            <Card key={tile.key} className="rounded-[13px]" style={{ padding: '16px 16px 15px' }}>
              <div className="flex items-center justify-between mb-3">
                <div
                  className="flex items-center justify-center"
                  style={{ width: 34, height: 34, borderRadius: 9, background: meta.bg, color: meta.color }}
                >
                  <meta.Icon size={17} />
                </div>
                <span className="text-[11px] font-bold rounded-md" style={{ padding: '2px 7px', ...badge.style }}>
                  {badge.text}
                </span>
              </div>
              <div className="text-[30px] font-extrabold leading-none" style={{ letterSpacing: '-1px' }}>
                {tile.value != null ? meta.fmt(tile.value) : '–'}
              </div>
              <div className="text-[12.5px] mt-[5px] truncate" style={{ color: flag ? '#fbbf24' : '#94a3b8' }}>
                {sub}
              </div>
            </Card>
          )
        })}
      </div>

      {showHealth && <HealthSummary />}

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

        {/* Recent activity */}
        <Card style={{ padding: '18px 20px' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[15px] font-bold">פעילות אחרונה</div>
            <Link href="/events" className="text-[12px] text-accent font-semibold">
              הצג הכל ←
            </Link>
          </div>
          <div className="flex flex-col gap-[11px]">
            {recent.length === 0 && <div className="text-[13px] text-faint">אין משימות</div>}
            {recent.map((e) => {
              const sev = SEVERITY_META[e.severity] ?? SEVERITY_META.info
              return (
                <div key={e.event_id} className="flex items-center gap-3">
                  <span className="rounded" style={{ minWidth: 4, width: 4, height: 34, background: sev.color }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13.5px] font-semibold truncate">{e.message}</div>
                    <div className="text-[11.5px] text-faint">
                      {EVENT_TYPE_LABEL[e.event_type] ?? e.event_type} · <span className="ltr">{fmtDate(e.triggered_ts)}</span>
                    </div>
                  </div>
                  <span
                    className="text-[11.5px] font-bold rounded-md whitespace-nowrap"
                    style={{ color: sev.color, background: sev.bg, padding: '5px 11px' }}
                  >
                    {sev.label}
                  </span>
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}
