'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useDrivers } from '@/hooks/useDrivers'
import { useVehicles } from '@/hooks/useVehicles'
import { useBotUsers } from '@/hooks/useBotManagement'
import { sortItems } from '@/lib/domain'
import { phoneIL, driverLicense } from '@/lib/validation'
import type { UiDriver, DriverCreate, DriverRead } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { DriverCard } from '@/components/DriverCard'
import { EntityFormModal, type FieldDef, type FormValues } from '@/components/EntityFormModal'

type DKey = 'name' | 'licExpiry' | 'vehicle' | 'status'

const FIELDS: { key: DKey; label: string }[] = [
  { key: 'name', label: 'שם' },
  { key: 'licExpiry', label: 'תוקף רישיון' },
  { key: 'vehicle', label: 'רכב' },
  { key: 'status', label: 'סטטוס' },
]

const accessor = (d: UiDriver, key: DKey, vehicleByDriver: Record<string, string>): string => {
  if (key === 'vehicle') return vehicleByDriver[d.id] ?? ''
  if (key === 'licExpiry') return d.licExpiry ?? ''
  return d[key]
}

const FORM_FIELDS: FieldDef[] = [
  { key: 'full_name', label: 'שם מלא', type: 'text', required: true },
  { key: 'phone_number', label: 'טלפון', type: 'tel', required: true, ltr: true, placeholder: '050-123-4567', validate: phoneIL },
  { key: 'license_number', label: 'מספר רישיון נהיגה', type: 'text', ltr: true, validate: driverLicense },
  { key: 'license_valid_to', label: 'תוקף רישיון', type: 'date' },
  { key: 'status', label: 'סטטוס', type: 'select', options: [{ value: 'active', label: 'פעיל' }, { value: 'inactive', label: 'לא פעיל' }] },
]

const editInitial = (d: UiDriver): FormValues => ({
  full_name: d.name,
  phone_number: d.phone,
  license_number: d.license === '—' ? '' : d.license,
  license_valid_to: d.licExpiry ?? '',
  status: d.status === 'on' ? 'active' : 'inactive',
})

function toPayload(values: FormValues): Partial<DriverRead> {
  const out: Record<string, unknown> = {}
  const put = (k: string, v: string) => v.trim() && (out[k] = v.trim())
  put('full_name', values.full_name)
  put('phone_number', values.phone_number)
  put('license_number', values.license_number)
  put('license_valid_to', values.license_valid_to)
  put('status', values.status)
  return out as Partial<DriverRead>
}

export default function DriversPage() {
  const { drivers, add, update, remove } = useDrivers()
  const { vehicles } = useVehicles()
  const { users: botUsers } = useBotUsers()
  const vehicleByDriver = Object.fromEntries(
    vehicles.filter((v) => v.driverId).map((v) => [v.driverId as string, v.plate]),
  )
  const [sort, setSort] = useState<SortState<DKey>>({ key: 'name', dir: 'asc' })
  const [form, setForm] = useState<{ mode: 'add' } | { mode: 'edit'; d: UiDriver } | null>(null)
  const sorted = sortItems(drivers, (d) => accessor(d, sort.key, vehicleByDriver), sort.dir)

  const onSubmit = (values: FormValues) => {
    const payload = toPayload(values)
    if (form?.mode === 'edit') update({ id: form.d.id, patch: payload })
    else add(payload as DriverCreate)
    setForm(null)
  }

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <SortChips fields={FIELDS} sort={sort} onSort={(k) => setSort((s) => nextDir(s, k))} />
        <Button onClick={() => setForm({ mode: 'add' })}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף נהג
        </Button>
      </div>

      <div className="grid gap-[15px]" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(310px,1fr))' }}>
        {sorted.map((d) => (
          <DriverCard
            key={d.id}
            d={d}
            vehiclePlate={vehicleByDriver[d.id]}
            botUsers={botUsers}
            onEdit={() => setForm({ mode: 'edit', d })}
            onRemove={() => remove(d.id)}
          />
        ))}
      </div>

      {form && (
        <EntityFormModal
          title={form.mode === 'add' ? 'הוספת נהג' : 'עריכת נהג'}
          fields={FORM_FIELDS}
          initial={form.mode === 'edit' ? editInitial(form.d) : undefined}
          submitLabel={form.mode === 'add' ? 'הוסף' : 'שמירה'}
          onSubmit={onSubmit}
          onClose={() => setForm(null)}
        />
      )}
    </div>
  )
}
