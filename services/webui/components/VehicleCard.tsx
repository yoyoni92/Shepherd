'use client'
import { Truck, Trash2, Pencil, Bike, Car, Bus, Caravan, type LucideIcon } from 'lucide-react'
import type { UiVehicle } from '@/lib/api/schemas'
import { daysTo, fmtDate } from '@/lib/domain'
import { VEHICLE_TYPE_LABEL } from '@/lib/vehicleTypes'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const DASH = '—'

// A distinct icon per vehicle type (falls back to a generic truck).
const TYPE_ICON: Record<string, LucideIcon> = {
  motorcycle: Bike,
  car: Car,
  van: Caravan,
  bus: Bus,
  truck: Truck,
}

export function VehicleCard({
  v,
  driverName,
  customerName,
  onEdit,
  onRemove,
}: {
  v: UiVehicle
  driverName?: string
  customerName?: string
  onEdit: () => void
  onRemove: () => void
}) {
  const insWarn = v.insurance != null && daysTo(v.insurance) < 30
  const licWarn = v.licenseValidTo != null && daysTo(v.licenseValidTo) < 30
  const nextMaint = [
    v.nextMaintenanceKm != null ? `${v.nextMaintenanceKm.toLocaleString()} ק״מ` : null,
    v.nextMaintenanceType,
  ]
    .filter(Boolean)
    .join(' · ')
  const TypeIcon = (v.vehicleType && TYPE_ICON[v.vehicleType]) || Truck

  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="flex items-center justify-center shrink-0 bg-panel2 border border-control text-accent"
            style={{ width: 44, height: 44, borderRadius: 11 }}
          >
            <TypeIcon size={22} />
          </div>
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">
              {v.make} {v.model}
            </div>
            <div className="text-[12px] text-faint">
              {[
                v.vehicleType ? VEHICLE_TYPE_LABEL[v.vehicleType] ?? v.vehicleType : null,
                v.currentKm != null ? `${v.currentKm.toLocaleString()} ק״מ` : null,
              ]
                .filter(Boolean)
                .join(' · ') || DASH}
            </div>
          </div>
        </div>
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
        <Field label="נהג משויך" value={driverName ?? DASH} />
        <Field label="לקוח" value={customerName ?? DASH} />
        <Field label="טיפול אחרון" value={v.lastService ? fmtDate(v.lastService) : DASH} ltr />
        <div>
          <div className="text-[11px] text-faint mb-0.5">תוקף ביטוח</div>
          <div className="text-[13px] font-semibold ltr" style={{ color: insWarn ? '#fbbf24' : 'var(--ink)' }}>
            {v.insurance ? fmtDate(v.insurance) : DASH}
          </div>
        </div>
        <div>
          <div className="text-[11px] text-faint mb-0.5">תוקף רישוי</div>
          <div className="text-[13px] font-semibold ltr" style={{ color: licWarn ? '#fbbf24' : 'var(--ink)' }}>
            {v.licenseValidTo ? fmtDate(v.licenseValidTo) : DASH}
          </div>
        </div>
        <Field label="טיפול הבא" value={nextMaint || DASH} />
        <Field label="סוג טיפול" value={v.maintenanceTypeName ?? DASH} />
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

function Field({
  label,
  value,
  ltr,
  className,
}: {
  label: string
  value: string
  ltr?: boolean
  className?: string
}) {
  return (
    <div className={className}>
      <div className="text-[11px] text-faint mb-0.5">{label}</div>
      <div className={`text-[13px] font-semibold${ltr ? ' ltr' : ''}`}>{value}</div>
    </div>
  )
}
