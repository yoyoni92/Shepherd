'use client'
import { useState } from 'react'
import { Plus, AlertTriangle, X } from 'lucide-react'
import { useMaintenanceTypes } from '@/hooks/useMaintenanceTypes'
import { useVehicles } from '@/hooks/useVehicles'
import type { UiMaintenanceType, MaintenanceTypeCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { MaintenanceTypeCard } from '@/components/MaintenanceTypeCard'
import { MaintenanceTypeForm } from '@/components/MaintenanceTypeForm'

export default function MaintenanceTypesPage() {
  const { types, add, update, remove, removeError, clearRemoveError } = useMaintenanceTypes()
  const { vehicles } = useVehicles()
  const countById = vehicles.reduce<Record<string, number>>((acc, v) => {
    if (v.maintenanceTypeId) acc[v.maintenanceTypeId] = (acc[v.maintenanceTypeId] ?? 0) + 1
    return acc
  }, {})
  const [form, setForm] = useState<{ mode: 'add' } | { mode: 'edit'; m: UiMaintenanceType } | null>(null)

  const onSubmit = (payload: MaintenanceTypeCreate) => {
    if (form?.mode === 'edit') update({ id: form.m.id, patch: payload })
    else add(payload)
    setForm(null)
  }

  return (
    <div className="animate-fade-up">
      {removeError && (
        <div
          className="flex items-center gap-2.5 text-[13px] font-semibold rounded-[10px] mb-4"
          style={{ color: '#f87171', background: 'rgba(248,113,113,.1)', border: '1px solid rgba(248,113,113,.3)', padding: '10px 14px' }}
        >
          <AlertTriangle size={16} />
          <span className="flex-1">{removeError.message}</span>
          <button onClick={() => clearRemoveError()} aria-label="סגור" className="cursor-pointer">
            <X size={15} />
          </button>
        </div>
      )}

      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <div className="text-[13px] text-faint font-semibold">קטלוג סוגי הטיפול — לכל רכב משויך סוג טיפול</div>
        <Button onClick={() => setForm({ mode: 'add' })}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף סוג טיפול
        </Button>
      </div>

      <div className="grid gap-[15px]" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(330px,1fr))' }}>
        {types.map((m) => (
          <MaintenanceTypeCard
            key={m.id}
            m={m}
            vehicleCount={countById[m.id] ?? 0}
            onEdit={() => setForm({ mode: 'edit', m })}
            onRemove={() => remove(m.id)}
          />
        ))}
      </div>

      {form && (
        <MaintenanceTypeForm
          initial={form.mode === 'edit' ? form.m : undefined}
          onSubmit={onSubmit}
          onClose={() => setForm(null)}
        />
      )}
    </div>
  )
}
