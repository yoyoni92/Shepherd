import { describe, it, expect } from 'vitest'
import { toUiVehicle, toUiDriver, toUiCustomer, toUiMaintenanceType, toUiAccident } from '@/lib/adapters'
import type { VehicleRead, DriverRead, CustomerRead, MaintenanceTypeRead, AccidentRead, UiVehicle, UiDriver } from '@/lib/api/schemas'

describe('toUiVehicle', () => {
  it('maps the real DB fields', () => {
    const v: VehicleRead = {
      vehicle_id: 'v1', licensing_plate: '12-345-67', vehicle_type: 'truck', vendor: 'Toyota', model: 'Corolla',
      current_km: 84000, insurance_valid_to: '2026-09-02', license_valid_to: '2026-07-01',
      driver_id: 'd9', customer_id: 'c2', last_maintenance_date: '2026-04-12',
      next_maintenance_km: 90000, next_maintenance_type: 'גדול',
      maintenance_type_id: 'mt1', maintenance_type_name: 'קטן ואז גדול',
    }
    expect(toUiVehicle(v)).toEqual({
      id: 'v1', plate: '12-345-67', vehicleType: 'truck', make: 'Toyota', model: 'Corolla',
      driverId: 'd9', customerId: 'c2', currentKm: 84000, insurance: '2026-09-02', licenseValidTo: '2026-07-01',
      lastService: '2026-04-12', nextMaintenanceKm: 90000, nextMaintenanceType: 'גדול',
      maintenanceTypeId: 'mt1', maintenanceTypeName: 'קטן ואז גדול',
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

describe('toUiMaintenanceType', () => {
  it('maps the catalog fields', () => {
    const m: MaintenanceTypeRead = { id: 'mt1', name: 'קטן ואז גדול', description: 'x', interval_km: 10000, steps: ['קטן', 'גדול'] }
    expect(toUiMaintenanceType(m)).toEqual({ id: 'mt1', name: 'קטן ואז גדול', description: 'x', intervalKm: 10000, steps: ['קטן', 'גדול'] })
    expect(toUiMaintenanceType({ id: 'm', name: 'n', interval_km: 5000, steps: ['א'] }).description).toBeNull()
  })
})

describe('toUiAccident', () => {
  const vehicleById: Record<string, UiVehicle> = {
    v1: { id: 'v1', plate: '12-345-67', vehicleType: 'car', make: 'Toyota', model: 'Corolla', driverId: 'd1', customerId: null, currentKm: null, insurance: null, licenseValidTo: null, lastService: null, nextMaintenanceKm: null, nextMaintenanceType: null, maintenanceTypeId: null, maintenanceTypeName: null },
  }
  const driverById: Record<string, UiDriver> = {
    d1: { id: 'd1', name: 'דנה לוי', phone: '050', license: 'IL-1', licExpiry: null, status: 'on' },
  }

  it('maps all fields with known vehicle and driver', () => {
    const a: AccidentRead = {
      accident_id: 'acc1', vehicle_id: 'v1', driver_id: 'd1',
      datetime: '2026-06-10T09:30:00', location: 'תל אביב', description: 'פגיעה קלה',
      another_driver_licensing_plate: '77-777-77', another_driver_phone_number: '054-111-2222', another_driver_id_number: '123456789',
      attachments: [{ attachment_id: 'att1', category: 'photo_our_vehicle', file_url: 's3://bucket/key.jpg', uploaded_ts: '2026-06-10T10:00:00' }],
    }
    expect(toUiAccident(a, vehicleById, driverById)).toEqual({
      id: 'acc1', vehicleId: 'v1', vehiclePlate: '12-345-67', vehicleMake: 'Toyota', vehicleModel: 'Corolla',
      driverId: 'd1', driverName: 'דנה לוי', datetime: '2026-06-10T09:30:00',
      location: 'תל אביב', description: 'פגיעה קלה',
      anotherDriverPlate: '77-777-77', anotherDriverPhone: '054-111-2222', anotherDriverIdNumber: '123456789',
      attachments: [{ id: 'att1', category: 'photo_our_vehicle', fileUrl: 's3://bucket/key.jpg', uploadedTs: '2026-06-10T10:00:00' }],
    })
  })

  it('falls back to hyphen for unknown vehicle and null for absent driver', () => {
    const a: AccidentRead = {
      accident_id: 'a2', vehicle_id: 'vX', driver_id: null,
      datetime: '2026-05-01T08:00:00', location: null, description: null,
      another_driver_licensing_plate: null, another_driver_phone_number: null, another_driver_id_number: null,
      attachments: [],
    }
    const ui = toUiAccident(a, {}, {})
    expect(ui.vehiclePlate).toBe('-')
    expect(ui.vehicleMake).toBe('-')
    expect(ui.vehicleModel).toBe('')
    expect(ui.driverName).toBeNull()
    expect(ui.attachments).toEqual([])
  })
})
