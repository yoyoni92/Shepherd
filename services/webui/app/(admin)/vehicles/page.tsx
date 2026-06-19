'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { sortItems } from '@/lib/domain'
import type { UiVehicle, VehicleCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { VehicleCard } from '@/components/VehicleCard'

type VKey = 'plate' | 'title' | 'year' | 'condition' | 'insurance'

const FIELDS: { key: VKey; label: string }[] = [
  { key: 'plate', label: 'לוחית' },
  { key: 'title', label: 'דגם' },
  { key: 'year', label: 'שנה' },
  { key: 'condition', label: 'מצב' },
  { key: 'insurance', label: 'ביטוח' },
]

const accessor = (v: UiVehicle, key: VKey): string | number => {
  if (key === 'title') return `${v.make} ${v.model}`
  if (key === 'year') return v.year ?? 0
  if (key === 'condition') return v.condition ?? 0
  if (key === 'insurance') return v.insurance ?? ''
  return v.plate
}

const NEW_VEHICLE: VehicleCreate = {
  licensing_plate: `NEW-${Date.now().toString().slice(-6)}`,
  vendor: 'רכב',
  model: 'חדש',
}

export default function VehiclesPage() {
  const { vehicles, add, remove } = useVehicles()
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
          <VehicleCard key={v.id} v={v} onRemove={() => remove(v.id)} />
        ))}
      </div>
    </div>
  )
}
