'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useAccidents } from '@/hooks/useAccidents'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { Button } from '@/components/ui/button'
import { AccidentCard } from '@/components/AccidentCard'
import { AccidentFormModal } from '@/components/AccidentFormModal'
import type { AccidentCreate } from '@/lib/api/schemas'

export default function AccidentsPage() {
  const { accidents, add, adding } = useAccidents()
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = (payload: AccidentCreate) => {
    add(payload)
    setShowForm(false)
  }

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <div />
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף תאונה
        </Button>
      </div>

      <div
        className="grid gap-[15px]"
        style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(330px,1fr))' }}
      >
        {accidents.map((a) => (
          <AccidentCard key={a.id} a={a} />
        ))}
      </div>

      {showForm && (
        <AccidentFormModal
          vehicles={vehicles}
          drivers={drivers}
          onSubmit={handleSubmit}
          onClose={() => setShowForm(false)}
          submitting={adding}
        />
      )}
    </div>
  )
}
