'use client'
import { Truck, Trash2 } from 'lucide-react'
import type { UiVehicle } from '@/lib/api/schemas'
import { daysTo, fmtDate } from '@/lib/domain'
import { conditionColor } from '@/components/meta'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const DASH = '—'

export function VehicleCard({ v, onRemove }: { v: UiVehicle; onRemove: () => void }) {
  const active = v.status === 'active'
  const insWarn = v.insurance != null && daysTo(v.insurance) < 30
  const condC = v.condition != null ? conditionColor(v.condition) : '#64748b'
  const statusColor = active ? '#34d399' : '#64748b'
  const subtitle = [v.year != null ? `שנת ${v.year}` : null, v.fuel].filter(Boolean).join(' · ') || DASH

  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="flex items-center justify-center shrink-0 bg-panel2 border border-control text-accent"
            style={{ width: 44, height: 44, borderRadius: 11 }}
          >
            <Truck size={22} />
          </div>
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">
              {v.make} {v.model}
            </div>
            <div className="text-[12px] text-faint">{subtitle}</div>
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1.5 text-[11.5px] font-bold rounded-md whitespace-nowrap"
          style={{
            color: statusColor,
            background: active ? 'rgba(52,211,153,.1)' : 'rgba(100,116,139,.1)',
            padding: '4px 10px',
          }}
        >
          <span className="rounded-full" style={{ width: 6, height: 6, background: statusColor }} />
          {active ? 'פעיל' : 'מושבת'}
        </span>
      </div>

      <div
        className="inline-flex items-center gap-[7px] bg-bg border border-control rounded-lg mb-3.5 ltr"
        style={{ padding: '6px 11px' }}
      >
        <span className="rounded-sm" style={{ width: 13, height: 9, background: '#2563eb' }} />
        <span className="text-[14px] font-bold font-mono" style={{ letterSpacing: 2 }}>
          {v.plate}
        </span>
      </div>

      <div className="grid grid-cols-2 mb-3.5" style={{ gap: '11px 14px' }}>
        <Field label="נהג משויך" value={v.driver ?? DASH} />
        <Field label="טיפול אחרון" value={v.lastService ? fmtDate(v.lastService) : DASH} ltr />
        <div>
          <div className="text-[11px] text-faint mb-0.5">תוקף ביטוח</div>
          <div className="text-[13px] font-semibold ltr" style={{ color: insWarn ? '#fbbf24' : '#e2e8f0' }}>
            {v.insurance ? fmtDate(v.insurance) : DASH}
          </div>
        </div>
        <div>
          <div className="text-[11px] text-faint mb-1">מצב רכב</div>
          {v.condition != null ? (
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-line rounded-md overflow-hidden">
                <div className="h-full rounded-md" style={{ width: `${v.condition}%`, background: condC }} />
              </div>
              <span className="text-[12.5px] font-extrabold" style={{ color: condC, minWidth: 24 }}>
                {v.condition}
              </span>
            </div>
          ) : (
            <div className="text-[13px] font-semibold text-faint">{DASH}</div>
          )}
        </div>
      </div>

      <div className="flex gap-2 border-t border-line pt-3">
        <Button variant="secondary" size="sm" className="flex-1">
          פרטים
        </Button>
        <Button variant="danger" size="sm" onClick={onRemove}>
          <Trash2 size={14} />
          הסר
        </Button>
      </div>
    </Card>
  )
}

function Field({ label, value, ltr }: { label: string; value: string; ltr?: boolean }) {
  return (
    <div>
      <div className="text-[11px] text-faint mb-0.5">{label}</div>
      <div className={`text-[13px] font-semibold${ltr ? ' ltr' : ''}`}>{value}</div>
    </div>
  )
}
