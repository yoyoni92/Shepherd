import type { VehicleRead, DriverRead, UiVehicle, UiDriver } from './api/schemas'

/** VehicleRead -> card view model. Gap fields (year/fuel/driver name/status/condition) are null. */
export function toUiVehicle(v: VehicleRead): UiVehicle {
  return {
    id: v.vehicle_id,
    plate: v.licensing_plate,
    make: v.vendor ?? v.nickname ?? '—',
    model: v.model ?? '',
    year: null,
    fuel: null,
    driver: null,
    status: 'active',
    lastService: v.last_maintenance_date ?? null,
    insurance: v.insurance_valid_to ?? null,
    condition: null,
  }
}

/** DriverRead -> card view model. licExpiry/vehicle have no source on the driver (gap C2). */
export function toUiDriver(d: DriverRead): UiDriver {
  return {
    id: d.driver_id,
    name: d.full_name,
    phone: d.phone_number,
    license: d.license_number ?? '—',
    licExpiry: null,
    vehicle: null,
    status: d.status === 'active' ? 'on' : 'off',
  }
}
