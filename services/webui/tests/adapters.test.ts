import { describe, it, expect } from 'vitest'
import { toUiVehicle, toUiDriver } from '@/lib/adapters'
import type { VehicleRead, DriverRead } from '@/lib/api/schemas'

describe('toUiVehicle', () => {
  it('maps real fields and nulls the gap fields', () => {
    const v: VehicleRead = {
      vehicle_id: 'v1', licensing_plate: '12-345-67', vendor: 'Toyota', model: 'Corolla',
      insurance_valid_to: '2026-09-02', last_maintenance_date: '2026-04-12',
    }
    const ui = toUiVehicle(v)
    expect(ui).toMatchObject({
      id: 'v1', plate: '12-345-67', make: 'Toyota', model: 'Corolla',
      insurance: '2026-09-02', lastService: '2026-04-12', status: 'active',
    })
    expect(ui.year).toBeNull()
    expect(ui.fuel).toBeNull()
    expect(ui.condition).toBeNull()
    expect(ui.driver).toBeNull()
  })

  it('falls back to nickname then dash for make', () => {
    expect(toUiVehicle({ vehicle_id: 'v', licensing_plate: 'p', nickname: 'Van' }).make).toBe('Van')
    expect(toUiVehicle({ vehicle_id: 'v', licensing_plate: 'p' }).make).toBe('—')
  })
})

describe('toUiDriver', () => {
  it('maps fields and translates status to on/off', () => {
    const d: DriverRead = { driver_id: 'd1', full_name: 'דנה לוי', phone_number: '050', license_number: 'IL-1', status: 'active' }
    expect(toUiDriver(d)).toMatchObject({ id: 'd1', name: 'דנה לוי', phone: '050', license: 'IL-1', status: 'on' })
    expect(toUiDriver({ ...d, status: 'inactive' }).status).toBe('off')
  })

  it('dashes a missing licence number', () => {
    expect(toUiDriver({ driver_id: 'd', full_name: 'n', phone_number: 'p', status: 'active' }).license).toBe('—')
  })
})
