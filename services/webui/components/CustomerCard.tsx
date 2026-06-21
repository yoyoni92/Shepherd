'use client'
import { Building2, Trash2, Pencil, Phone, Mail, Truck } from 'lucide-react'
import type { UiCustomer } from '@/lib/api/schemas'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const DASH = '—'

export function CustomerCard({
  c,
  vehicleCount,
  onEdit,
  onRemove,
}: {
  c: UiCustomer
  vehicleCount: number
  onEdit: () => void
  onRemove: () => void
}) {
  const active = c.status === 'active'
  const statusColor = active ? '#34d399' : '#64748b'

  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="flex items-center justify-center shrink-0 bg-panel2 border border-control text-accent"
            style={{ width: 44, height: 44, borderRadius: 11 }}
          >
            <Building2 size={22} />
          </div>
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">{c.name}</div>
            <div className="text-[12px] text-faint flex items-center gap-1.5">
              <Truck size={12} />
              {vehicleCount} רכבים
            </div>
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
          {active ? 'פעיל' : 'לא פעיל'}
        </span>
      </div>

      <div className="grid grid-cols-1 mb-3.5" style={{ gap: '9px' }}>
        <div className="flex items-center gap-2 text-[13px]">
          <Phone size={14} className="text-faint shrink-0" />
          <span className="ltr font-semibold">{c.phone ?? DASH}</span>
        </div>
        <div className="flex items-center gap-2 text-[13px]">
          <Mail size={14} className="text-faint shrink-0" />
          <span className="ltr font-semibold truncate">{c.email ?? DASH}</span>
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
