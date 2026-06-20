'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { sortItems } from '@/lib/domain'
import type { UiVehicle, VehicleCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { VehicleCard } from '@/components/VehicleCard'

type VKey = 'plate' | 'title' | 'insurance' | 'license' | 'km'

const FIELDS: { key: VKey; label: string }[] = [
  { key: 'plate', label: 'לוחית' },
  { key: 'title', label: 'דגם' },
  { key: 'insurance', label: 'ביטוח' },
  { key: 'license', label: 'רישוי' },
  { key: 'km', label: 'ק״מ' },
]

const accessor = (v: UiVehicle, key: VKey): string | number => {
  if (key === 'title') return `${v.make} ${v.model}`
  if (key === 'insurance') return v.insurance ?? ''
  if (key === 'license') return v.licenseValidTo ?? ''
  if (key === 'km') return v.currentKm ?? 0
  return v.plate
}

const NEW_VEHICLE: VehicleCreate = {
  licensing_plate: `NEW-${Date.now().toString().slice(-6)}`,
  vendor: 'רכב',
  model: 'חדש',
}

export default function VehiclesPage() {
  const { vehicles, add, remove } = useVehicles()
  const { drivers } = useDrivers()
  const driverById = Object.fromEntries(drivers.map((d) => [d.id, d.name]))
  const [sort, setSort] = useState<SortState<VKey>>({ key: 'plate', dir: 'asc' })
  const sorted = sortItems(vehicles, (v) => accessor(v, sort.key), sort.dir)

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <SortChips fields={FIELDS} sort={sort} onSort={(k) => setSort((s) => nextDir(s, k))} />
        <Button onClick={() => add(NEW_VEHICLE)}>
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
            onRemove={() => remove(v.id)}
          />
        ))}
      </div>
    </div>
  )
}
