'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { useCustomers } from '@/hooks/useCustomers'
import { useMaintenanceTypes } from '@/hooks/useMaintenanceTypes'
import { sortItems } from '@/lib/domain'
import { plate as plateGuard, nonNegInt } from '@/lib/validation'
import { VEHICLE_TYPES, VEHICLE_TYPE_LABEL } from '@/lib/vehicleTypes'
import type { UiVehicle, VehicleCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { VehicleCard } from '@/components/VehicleCard'
import { EntityFormModal, type FieldDef, type FormValues } from '@/components/EntityFormModal'
import { MaintenanceTypesPanel } from '@/components/MaintenanceTypesPanel'

type VKey = 'plate' | 'title' | 'insurance' | 'license' | 'km' | 'customer'

const FIELDS: { key: VKey; label: string }[] = [
  { key: 'plate', label: 'לוחית' },
  { key: 'title', label: 'דגם' },
  { key: 'customer', label: 'לקוח' },
  { key: 'insurance', label: 'ביטוח' },
  { key: 'license', label: 'רישוי' },
  { key: 'km', label: 'ק״מ' },
]

const accessor = (v: UiVehicle, key: VKey, customerById: Record<string, string>): string | number => {
  if (key === 'title') return `${v.make} ${v.model}`
  if (key === 'insurance') return v.insurance ?? ''
  if (key === 'license') return v.licenseValidTo ?? ''
  if (key === 'km') return v.currentKm ?? 0
  if (key === 'customer') return v.customerId ? (customerById[v.customerId] ?? '') : ''
  return v.plate
}

const formFields = (
  driverOpts: { value: string; label: string }[],
  customerOpts: { value: string; label: string }[],
  maintenanceOpts: { value: string; label: string }[],
): FieldDef[] => [
  { key: 'licensing_plate', label: 'מספר רישוי', type: 'text', required: true, ltr: true, placeholder: '12-345-67', validate: plateGuard },
  { key: 'vehicle_type', label: 'סוג רכב', type: 'select', required: true, options: VEHICLE_TYPES.map((t) => ({ value: t, label: VEHICLE_TYPE_LABEL[t] })) },
  { key: 'vendor', label: 'יצרן', type: 'text' },
  { key: 'model', label: 'דגם', type: 'text' },
  { key: 'current_km', label: 'ק״מ נוכחי', type: 'number', validate: nonNegInt },
  { key: 'maintenance_type_id', label: 'סוג טיפול', type: 'select', options: maintenanceOpts },
  { key: 'driver_id', label: 'נהג משויך', type: 'select', options: driverOpts },
  { key: 'customer_id', label: 'לקוח', type: 'select', options: customerOpts },
  { key: 'insurance_valid_to', label: 'תוקף ביטוח', type: 'date' },
  { key: 'license_valid_to', label: 'תוקף רישוי', type: 'date' },
]

const editInitial = (v: UiVehicle): FormValues => ({
  licensing_plate: v.plate,
  vehicle_type: v.vehicleType ?? '',
  vendor: v.make === '—' ? '' : v.make,
  model: v.model,
  current_km: v.currentKm != null ? String(v.currentKm) : '',
  maintenance_type_id: v.maintenanceTypeId ?? '',
  driver_id: v.driverId ?? '',
  customer_id: v.customerId ?? '',
  insurance_valid_to: v.insurance ?? '',
  license_valid_to: v.licenseValidTo ?? '',
})

// Only non-empty fields are sent (create applies defaults; edit leaves blanks unchanged).
function toPayload(values: FormValues): Partial<VehicleCreate> {
  const out: Record<string, unknown> = {}
  const put = (k: string, v: string) => v.trim() && (out[k] = v.trim())
  put('licensing_plate', values.licensing_plate)
  put('vehicle_type', values.vehicle_type)
  put('vendor', values.vendor)
  put('model', values.model)
  if (values.current_km.trim()) out.current_km = Number(values.current_km)
  put('maintenance_type_id', values.maintenance_type_id)
  put('driver_id', values.driver_id)
  put('customer_id', values.customer_id)
  put('insurance_valid_to', values.insurance_valid_to)
  put('license_valid_to', values.license_valid_to)
  return out as Partial<VehicleCreate>
}

export default function VehiclesPage() {
  const { vehicles, add, update, remove } = useVehicles()
  const { drivers } = useDrivers()
  const { customers } = useCustomers()
  const { types: maintenanceTypes } = useMaintenanceTypes()
  const driverById = Object.fromEntries(drivers.map((d) => [d.id, d.name]))
  const customerById = Object.fromEntries(customers.map((c) => [c.id, c.name]))
  const [sort, setSort] = useState<SortState<VKey>>({ key: 'plate', dir: 'asc' })
  const [form, setForm] = useState<{ mode: 'add' } | { mode: 'edit'; v: UiVehicle } | null>(null)
  const sorted = sortItems(vehicles, (v) => accessor(v, sort.key, customerById), sort.dir)

  const fields = formFields(
    drivers.map((d) => ({ value: d.id, label: d.name })),
    customers.map((c) => ({ value: c.id, label: c.name })),
    maintenanceTypes.map((m) => ({ value: m.id, label: m.name })),
  )

  const onSubmit = (values: FormValues) => {
    const payload = toPayload(values)
    if (form?.mode === 'edit') update({ id: form.v.id, patch: payload })
    else add(payload as VehicleCreate)
    setForm(null)
  }

  return (
    <Tabs defaultValue="vehicles" className="animate-fade-up">
      <TabsList className="mb-[18px]">
        <TabsTrigger value="vehicles">רכבים</TabsTrigger>
        <TabsTrigger value="maintenance-types">סוגי טיפול</TabsTrigger>
      </TabsList>

      <TabsContent value="vehicles">
        <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
          <SortChips fields={FIELDS} sort={sort} onSort={(k) => setSort((s) => nextDir(s, k))} />
          <Button onClick={() => setForm({ mode: 'add' })}>
            <Plus size={16} strokeWidth={2.4} />
            הוסף רכב
          </Button>
        </div>

        <div className="grid gap-[15px]" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(330px,1fr))' }}>
          {sorted.map((v) => (
            <VehicleCard
              key={v.id}
              v={v}
              driverName={v.driverId ? driverById[v.driverId] : undefined}
              customerName={v.customerId ? customerById[v.customerId] : undefined}
              onEdit={() => setForm({ mode: 'edit', v })}
              onRemove={() => remove(v.id)}
            />
          ))}
        </div>
      </TabsContent>

      <TabsContent value="maintenance-types">
        <MaintenanceTypesPanel />
      </TabsContent>

      {form && (
        <EntityFormModal
          title={form.mode === 'add' ? 'הוספת רכב' : 'עריכת רכב'}
          fields={fields}
          initial={form.mode === 'edit' ? editInitial(form.v) : undefined}
          submitLabel={form.mode === 'add' ? 'הוסף' : 'שמירה'}
          onSubmit={onSubmit}
          onClose={() => setForm(null)}
        />
      )}
    </Tabs>
  )
}
