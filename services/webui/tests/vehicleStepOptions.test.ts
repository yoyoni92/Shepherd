import { test, expect } from 'vitest'
import { stepOptions } from '@/app/(admin)/vehicles/page'
import type { UiMaintenanceType } from '@/lib/api/schemas'

const types: UiMaintenanceType[] = [
  { id: 'm1', name: 'A', description: null, intervalKm: 10000, intervalMonths: null, steps: ['small', 'big', 'huge'] },
]

test('stepOptions lists the selected cycle steps', () => {
  expect(stepOptions(types, 'm1').map((o) => o.value)).toEqual(['small', 'big', 'huge'])
})

test('stepOptions is empty when no maintenance type is selected', () => {
  expect(stepOptions(types, '')).toEqual([])
})
