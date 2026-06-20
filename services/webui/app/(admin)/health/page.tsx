'use client'
import { RefreshCw } from 'lucide-react'
import { useHealth } from '@/hooks/useHealth'
import { SERVICE_LABELS, summarizeHealth, type Overall, type ServiceHealth } from '@/lib/health'
import { Card } from '@/components/ui/card'

const DOT: Record<'up' | 'down', string> = { up: '#34d399', down: '#f87171' }

const OVERALL_META: Record<Overall, { label: string; color: string }> = {
  ok: { label: 'כל השירותים פעילים', color: '#34d399' },
  degraded: { label: 'חלק מהשירותים אינם זמינים', color: '#fbbf24' },
  down: { label: 'תקלה — שירותים לא זמינים', color: '#f87171' },
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export default function HealthPage() {
  const { services, checkedAt, loading, refetch } = useHealth()
  const overall = summarizeHealth(services)
  const meta = OVERALL_META[overall]

  return (
    <div className="animate-fade-up" style={{ maxWidth: 760 }}>
      <div className="flex items-center gap-3 mb-[18px] flex-wrap">
        <span
          className="inline-flex items-center gap-2 text-[13px] font-bold rounded-[10px]"
          style={{ color: meta.color, background: `${meta.color}1a`, border: `1px solid ${meta.color}33`, padding: '8px 14px' }}
        >
          <span className="rounded-full" style={{ width: 9, height: 9, background: meta.color, boxShadow: `0 0 0 3px ${meta.color}33` }} />
          {loading ? 'בודק…' : meta.label}
        </span>
        <div className="flex-1" />
        <span className="text-[12px] text-faint">נבדק לאחרונה: {fmtTime(checkedAt)}</span>
        <button
          onClick={() => refetch()}
          aria-label="רענן"
          className="flex items-center gap-[7px] bg-panel2 border border-control rounded-[9px] text-[13px] font-bold text-accent cursor-pointer hover:text-ink"
          style={{ padding: '9px 13px' }}
        >
          <RefreshCw size={14} />
          רענון
        </button>
      </div>

      <Card className="overflow-hidden">
        {services.length === 0 && (
          <div className="text-faint text-sm" style={{ padding: '16px 18px' }}>טוען מצב שירותים…</div>
        )}
        {services.map((s: ServiceHealth) => {
          const color = DOT[s.status]
          return (
            <div
              key={s.key}
              className="flex items-center gap-3 border-b border-divider"
              style={{ padding: '15px 18px' }}
            >
              <span
                className="rounded-full shrink-0"
                style={{ width: 11, height: 11, background: color, boxShadow: `0 0 0 4px ${color}22` }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-bold truncate">{SERVICE_LABELS[s.key] ?? s.key}</div>
                <div className="text-[11.5px] text-faint ltr">{s.key}</div>
              </div>
              <span className="text-[12px] text-faint ltr" style={{ minWidth: 60, textAlign: 'left' }}>
                {s.latencyMs != null ? `${s.latencyMs} ms` : '—'}
              </span>
              <span
                className="text-[11.5px] font-bold rounded-md whitespace-nowrap"
                style={{ color, background: `${color}1a`, padding: '4px 11px', minWidth: 56, textAlign: 'center' }}
              >
                {s.status === 'up' ? 'פעיל' : 'מושבת'}
              </span>
            </div>
          )
        })}
      </Card>

      <div className="text-[11.5px] text-dim mt-3">
        בדיקה צד-שרת מול נקודת ה־<span className="ltr font-mono">/health</span> של כל שירות · רענון אוטומטי כל 15 שניות
      </div>
    </div>
  )
}
