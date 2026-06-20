'use client'
import Link from 'next/link'
import { Activity } from 'lucide-react'
import { useHealth } from '@/hooks/useHealth'
import { SERVICE_LABELS, summarizeHealth, downCount, type Overall } from '@/lib/health'
import { Card } from '@/components/ui/card'

const OVERALL: Record<Overall, { label: string; color: string }> = {
  ok: { label: 'כל השירותים פעילים', color: '#34d399' },
  degraded: { label: 'שירותים מסוימים מושבתים', color: '#fbbf24' },
  down: { label: 'תקלת שירותים', color: '#f87171' },
}

/** Compact dashboard strip: overall status + a dot per third-party service. */
export function HealthSummary() {
  const { services, loading } = useHealth()
  const overall = summarizeHealth(services)
  const meta = OVERALL[overall]
  const down = downCount(services)

  return (
    <Card className="rounded-[13px] mb-[22px]" style={{ padding: '14px 18px' }}>
      <div className="flex items-center gap-3 flex-wrap">
        <span className="flex items-center justify-center" style={{ width: 32, height: 32, borderRadius: 9, background: `${meta.color}1a`, color: meta.color }}>
          <Activity size={16} />
        </span>
        <div className="min-w-0">
          <div className="text-[13.5px] font-bold" style={{ color: meta.color }}>
            {loading && services.length === 0 ? 'בודק מצב שירותים…' : meta.label}
          </div>
          <div className="text-[11.5px] text-faint">
            {services.length > 0 ? `${services.length - down}/${services.length} פעילים` : 'מצב מערכת'}
          </div>
        </div>

        <div className="flex items-center gap-3.5 flex-wrap mr-1">
          {services.map((s) => {
            const color = s.status === 'up' ? '#34d399' : '#f87171'
            return (
              <span key={s.key} className="flex items-center gap-[6px]" title={s.status === 'up' ? 'פעיל' : 'מושבת'}>
                <span className="rounded-full" style={{ width: 8, height: 8, background: color, boxShadow: `0 0 0 3px ${color}22` }} />
                <span className="text-[12px] text-muted whitespace-nowrap">{SERVICE_LABELS[s.key] ?? s.key}</span>
              </span>
            )
          })}
        </div>

        <div className="flex-1" />
        <Link href="/health" className="text-[12px] text-accent font-semibold whitespace-nowrap">
          פרטים ←
        </Link>
      </div>
    </Card>
  )
}
