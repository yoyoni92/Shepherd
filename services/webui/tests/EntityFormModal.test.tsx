import { test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EntityFormModal, type FieldDef } from '@/components/EntityFormModal'

const fields: FieldDef[] = [
  { key: 'type', label: 'Type', type: 'select', options: [{ value: 't1', label: 'One' }] },
  {
    key: 'step',
    label: 'Step',
    type: 'select',
    options: (v) => (v.type === 't1' ? [{ value: 's1', label: 'Step A' }] : []),
  },
]

test('function-valued options resolve from live form values', () => {
  render(
    <EntityFormModal title="t" fields={fields} submitLabel="ok" onSubmit={() => {}} onClose={() => {}} />,
  )
  // Before selecting a type, the dependent select has no data option.
  expect(screen.queryByRole('option', { name: 'Step A' })).toBeNull()
  fireEvent.change(screen.getByLabelText('Type'), { target: { value: 't1' } })
  expect(screen.getByRole('option', { name: 'Step A' })).toBeInTheDocument()
})
