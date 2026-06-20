'use client'
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react'
import type { EventRead } from '@/lib/api/schemas'
import { fmtDate } from '@/lib/domain'
import { EVENT_TYPE_LABEL, SEVERITY_META, EVENT_STATUS_META } from '@/components/meta'

const SEV_ICON = { critical: ShieldAlert, warning: AlertTriangle, info: Info } as const

export function EventRow({ e }: { e: EventRead }) {
  const sev = SEVERITY_META[e.severity] ?? SEVERITY_META.info
  const st = EVENT_STATUS_META[e.status] ?? EVENT_STATUS_META.open
  const Icon = SEV_ICON[e.severity as keyof typeof SEV_ICON] ?? Info

  return (
    <div
      className="flex items-stretch bg-panel border border-line rounded-[13px] overflow-hidden"
    >
      <div style={{ width: 5, minWidth: 5, background: sev.color }} />
      <div className="flex-1 flex items-center gap-4 min-w-0" style={{ padding: '14px 18px' }}>
        <div
          className="flex items-center justify-center shrink-0"
          style={{ width: 34, height: 34, borderRadius: 9, background: sev.bg, color: sev.color }}
        >
          <Icon size={17} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[14.5px] font-bold mb-1 truncate">{e.message}</div>
          <div className="flex items-center gap-3.5 flex-wrap text-[12px] text-faint">
            <span>{EVENT_TYPE_LABEL[e.event_type] ?? e.event_type}</span>
            <span className="ltr">{fmtDate(e.triggered_ts)}</span>
            {e.vehicle_id && <span className="ltr font-mono">{e.vehicle_id}</span>}
          </div>
        </div>
        <span
          className="text-[11px] font-extrabold rounded-md text-center whitespace-nowrap"
          style={{ color: sev.color, background: sev.bg, padding: '5px 11px', minWidth: 56 }}
        >
          {sev.label}
        </span>
        <span
          className="text-[11.5px] font-bold rounded-md whitespace-nowrap"
          style={{ color: st.color, background: st.bg, padding: '5px 11px' }}
        >
          {st.label}
        </span>
      </div>
    </div>
  )
}
