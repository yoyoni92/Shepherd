'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useCustomers } from '@/hooks/useCustomers'
import { useVehicles } from '@/hooks/useVehicles'
import { sortItems } from '@/lib/domain'
import { phoneIL, email as emailGuard } from '@/lib/validation'
import type { UiCustomer, CustomerCreate, CustomerRead } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'
import { SortChips, nextDir, type SortState } from '@/components/SortChips'
import { CustomerCard } from '@/components/CustomerCard'
import { EntityFormModal, type FieldDef, type FormValues } from '@/components/EntityFormModal'

type CKey = 'name' | 'status'

const SORT_FIELDS: { key: CKey; label: string }[] = [
  { key: 'name', label: 'שם' },
  { key: 'status', label: 'סטטוס' },
]

const FORM_FIELDS: FieldDef[] = [
  { key: 'full_name', label: 'שם הלקוח', type: 'text', required: true },
  { key: 'phone_number', label: 'טלפון', type: 'tel', ltr: true, placeholder: '050-123-4567', validate: phoneIL },
  { key: 'email', label: 'דוא״ל', type: 'text', ltr: true, placeholder: 'name@company.co.il', validate: emailGuard },
  { key: 'status', label: 'סטטוס', type: 'select', options: [{ value: 'active', label: 'פעיל' }, { value: 'inactive', label: 'לא פעיל' }] },
]

const editInitial = (c: UiCustomer): FormValues => ({
  full_name: c.name,
  phone_number: c.phone ?? '',
  email: c.email ?? '',
  status: c.status,
})

function toPayload(values: FormValues): Partial<CustomerRead> {
  const out: Record<string, unknown> = {}
  const put = (k: string, v: string) => v.trim() && (out[k] = v.trim())
  put('full_name', values.full_name)
  put('phone_number', values.phone_number)
  put('email', values.email)
  put('status', values.status)
  return out as Partial<CustomerRead>
}

export default function CustomersPage() {
  const { customers, add, update, remove } = useCustomers()
  const { vehicles } = useVehicles()
  const countByCustomer = vehicles.reduce<Record<string, number>>((acc, v) => {
    if (v.customerId) acc[v.customerId] = (acc[v.customerId] ?? 0) + 1
    return acc
  }, {})
  const [sort, setSort] = useState<SortState<CKey>>({ key: 'name', dir: 'asc' })
  const [form, setForm] = useState<{ mode: 'add' } | { mode: 'edit'; c: UiCustomer } | null>(null)
  const sorted = sortItems(customers, (c) => c[sort.key], sort.dir)

  const onSubmit = (values: FormValues) => {
    const payload = toPayload(values)
    if (form?.mode === 'edit') update({ id: form.c.id, patch: payload })
    else add(payload as CustomerCreate)
    setForm(null)
  }

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <SortChips fields={SORT_FIELDS} sort={sort} onSort={(k) => setSort((s) => nextDir(s, k))} />
        <Button onClick={() => setForm({ mode: 'add' })}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף לקוח
        </Button>
      </div>

      <div className="grid gap-[15px]" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(310px,1fr))' }}>
        {sorted.map((c) => (
          <CustomerCard
            key={c.id}
            c={c}
            vehicleCount={countByCustomer[c.id] ?? 0}
            onEdit={() => setForm({ mode: 'edit', c })}
            onRemove={() => remove(c.id)}
          />
        ))}
      </div>

      {form && (
        <EntityFormModal
          title={form.mode === 'add' ? 'הוספת לקוח' : 'עריכת לקוח'}
          fields={FORM_FIELDS}
          initial={form.mode === 'edit' ? editInitial(form.c) : undefined}
          submitLabel={form.mode === 'add' ? 'הוסף' : 'שמירה'}
          onSubmit={onSubmit}
          onClose={() => setForm(null)}
        />
      )}
    </div>
  )
}
