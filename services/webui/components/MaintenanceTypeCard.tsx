'use client'
import { Wrench, Trash2, Pencil, Truck } from 'lucide-react'
import type { UiMaintenanceType } from '@/lib/api/schemas'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function MaintenanceTypeCard({
  m,
  vehicleCount,
  onEdit,
  onRemove,
}: {
  m: UiMaintenanceType
  vehicleCount: number
  onEdit: () => void
  onRemove: () => void
}) {
  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="flex items-center justify-center shrink-0 bg-panel2 border border-control text-accent"
            style={{ width: 44, height: 44, borderRadius: 11 }}
          >
            <Wrench size={21} />
          </div>
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">{m.name}</div>
            <div className="text-[12px] text-faint flex items-center gap-1.5">
              <Truck size={12} />
              {vehicleCount} רכבים · כל {m.intervalKm.toLocaleString()} ק״מ
            </div>
          </div>
        </div>
      </div>

      {m.description && <div className="text-[12.5px] text-muted mb-3">{m.description}</div>}

      <div className="mb-3.5">
        <div className="text-[11px] text-faint mb-1.5">שלבי הטיפול</div>
        <div className="flex flex-wrap items-center gap-1.5">
          {m.steps.map((s, i) => (
            <span key={i} className="inline-flex items-center gap-1">
              <span
                className="text-[12px] font-semibold rounded-md"
                style={{ background: 'var(--chip)', border: '1px solid var(--control)', color: 'var(--accent)', padding: '3px 9px' }}
              >
                {s}
              </span>
              {i < m.steps.length - 1 && <span className="text-faint text-[12px]">←</span>}
            </span>
          ))}
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
