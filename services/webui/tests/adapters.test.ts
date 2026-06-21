import { describe, it, expect } from 'vitest'
import { toUiVehicle, toUiDriver, toUiCustomer } from '@/lib/adapters'
import type { VehicleRead, DriverRead, CustomerRead } from '@/lib/api/schemas'

describe('toUiVehicle', () => {
  it('maps the real DB fields', () => {
    const v: VehicleRead = {
      vehicle_id: 'v1', licensing_plate: '12-345-67', vehicle_type: 'truck', vendor: 'Toyota', model: 'Corolla',
      current_km: 84000, insurance_valid_to: '2026-09-02', license_valid_to: '2026-07-01',
      driver_id: 'd9', customer_id: 'c2', last_maintenance_date: '2026-04-12',
      next_maintenance_km: 90000, next_maintenance_type: 'service',
    }
    expect(toUiVehicle(v)).toEqual({
      id: 'v1', plate: '12-345-67', vehicleType: 'truck', make: 'Toyota', model: 'Corolla',
      driverId: 'd9', customerId: 'c2', currentKm: 84000, insurance: '2026-09-02', licenseValidTo: '2026-07-01',
      lastService: '2026-04-12', nextMaintenanceKm: 90000, nextMaintenanceType: 'service',
    })
  })

  it('falls back to nickname then dash for make and nulls absent fields', () => {
    expect(toUiVehicle({ vehicle_id: 'v', licensing_plate: 'p', nickname: 'Van' }).make).toBe('Van')
    const bare = toUiVehicle({ vehicle_id: 'v', licensing_plate: 'p' })
    expect(bare.make).toBe('—')
    expect(bare.driverId).toBeNull()
    expect(bare.currentKm).toBeNull()
    expect(bare.licenseValidTo).toBeNull()
  })
})

describe('toUiDriver', () => {
  it('maps fields, licence expiry, and translates status to on/off', () => {
    const d: DriverRead = { driver_id: 'd1', full_name: 'דנה לוי', phone_number: '050', license_number: 'IL-1', license_valid_to: '2027-03-01', status: 'active' }
    expect(toUiDriver(d)).toMatchObject({ id: 'd1', name: 'דנה לוי', phone: '050', license: 'IL-1', licExpiry: '2027-03-01', status: 'on' })
    expect(toUiDriver({ ...d, status: 'inactive' }).status).toBe('off')
  })

  it('dashes a missing licence number and nulls a missing expiry', () => {
    const ui = toUiDriver({ driver_id: 'd', full_name: 'n', phone_number: 'p', status: 'active' })
    expect(ui.license).toBe('—')
    expect(ui.licExpiry).toBeNull()
  })
})

describe('toUiCustomer', () => {
  it('maps fields and defaults status to active', () => {
    const c: CustomerRead = { customer_id: 'c1', full_name: 'אלקטרה', phone_number: '03-1', email: 'a@b.co', status: 'active' }
    expect(toUiCustomer(c)).toEqual({ id: 'c1', name: 'אלקטרה', phone: '03-1', email: 'a@b.co', status: 'active' })
    expect(toUiCustomer({ customer_id: 'c', full_name: 'n', status: 'inactive' }).status).toBe('inactive')
    expect(toUiCustomer({ customer_id: 'c', full_name: 'n' }).phone).toBeNull()
  })
})
