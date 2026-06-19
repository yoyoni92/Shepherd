'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useDrivers } from '@/hooks/useDrivers'
import { sortItems } from '@/lib/domain'
import type { UiDriver, DriverCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { DriverCard } from '@/components/DriverCard'

type DKey = 'name' | 'licExpiry' | 'vehicle' | 'status'

const FIELDS: { key: DKey; label: string }[] = [
  { key: 'name', label: 'שם' },
  { key: 'licExpiry', label: 'תוקף רישיון' },
  { key: 'vehicle', label: 'רכב' },
  { key: 'status', label: 'סטטוס' },
]

const accessor = (d: UiDriver, key: DKey): string | number => {
  if (key === 'licExpiry') return d.licExpiry ?? ''
  if (key === 'vehicle') return d.vehicle ?? ''
  return d[key]
}

const NEW_DRIVER: DriverCreate = {
  full_name: 'נהג חדש',
  phone_number: `050-000-${Date.now().toString().slice(-4)}`,
}

export default function DriversPage() {
  const { drivers, add, remove } = useDrivers()
  const [sort, setSort] = useState<SortState<DKey>>({ key: 'name', dir: 'asc' })
  const sorted = sortItems(drivers, (d) => accessor(d, sort.key), sort.dir)

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <SortChips fields={FIELDS} sort={sort} onSort={(k) => setSort((s) => nextDir(s, k))} />
        <Button onClick={() => add(NEW_DRIVER)}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף נהג
        </Button>
      </div>

      <div className="grid gap-[15px]" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(310px,1fr))' }}>
        {sorted.map((d) => (
          <DriverCard key={d.id} d={d} onRemove={() => remove(d.id)} />
        ))}
      </div>
    </div>
  )
}
