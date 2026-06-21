'use client'
import { Truck, Trash2, Pencil } from 'lucide-react'
import type { UiDriver } from '@/lib/api/schemas'
import { daysTo, fmtDate } from '@/lib/domain'
import { Avatar } from '@/components/Avatar'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const DASH = '—'

export function DriverCard({
  d,
  vehiclePlate,
  onEdit,
  onRemove,
}: {
  d: UiDriver
  vehiclePlate?: string
  onEdit: () => void
  onRemove: () => void
}) {
  const on = d.status === 'on'
  const licWarn = d.licExpiry != null && daysTo(d.licExpiry) < 30
  const statusColor = on ? '#34d399' : '#64748b'

  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-[15px]">
        <div className="flex items-center gap-[13px] min-w-0">
          <Avatar id={Number(d.id) || d.name.length} name={d.name} />
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">{d.name}</div>
            <div className="text-[12px] text-faint ltr">{d.phone}</div>
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1.5 text-[11.5px] font-bold rounded-md whitespace-nowrap"
          style={{
            color: statusColor,
            background: on ? 'rgba(52,211,153,.1)' : 'rgba(100,116,139,.1)',
            padding: '4px 10px',
          }}
        >
          <span className="rounded-full" style={{ width: 6, height: 6, background: statusColor }} />
          {on ? 'במשמרת' : 'לא פעיל'}
        </span>
      </div>

      <div className="grid grid-cols-2 mb-3.5" style={{ gap: '11px 14px' }}>
        <div>
          <div className="text-[11px] text-faint mb-0.5">מספר רישיון</div>
          <div className="text-[13px] font-semibold ltr">{d.license}</div>
        </div>
        <div>
          <div className="text-[11px] text-faint mb-0.5">תוקף רישיון</div>
          <div className="text-[13px] font-semibold ltr" style={{ color: licWarn ? '#fbbf24' : '#e2e8f0' }}>
            {d.licExpiry ? fmtDate(d.licExpiry) : DASH}
          </div>
        </div>
        <div className="col-span-2">
          <div className="text-[11px] text-faint mb-0.5">רכב משויך</div>
          <div className="flex items-center gap-2">
            <Truck size={15} color="#60a5fa" />
            <span className="text-[13px] font-semibold ltr">{vehiclePlate ?? DASH}</span>
          </div>
        </div>
      </div>

      <div className="flex gap-2 border-t border-line pt-3">
        <Button variant="secondary" size="sm" className="flex-1" onClick={onEdit}>
          <Pencil size={14} />
          עריכה
        </Button>
        <Button variant="danger" size="sm" onClick={onRemove}>
          <Trash2 size={14} />
          הסר
        </Button>
      </div>
    </Card>
  )
}
