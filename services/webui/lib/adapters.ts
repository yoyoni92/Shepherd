import type {
  VehicleRead,
  DriverRead,
  CustomerRead,
  MaintenanceTypeRead,
  UiVehicle,
  UiDriver,
  UiCustomer,
  UiMaintenanceType,
} from './api/schemas'

/** VehicleRead -> card view model. `driverId` is resolved to a name in the vehicles page. */
export function toUiVehicle(v: VehicleRead): UiVehicle {
  return {
    id: v.vehicle_id,
    plate: v.licensing_plate,
    vehicleType: v.vehicle_type ?? null,
    make: v.vendor ?? v.nickname ?? '—',
    model: v.model ?? '',
    driverId: v.driver_id ?? null,
    customerId: v.customer_id ?? null,
    currentKm: v.current_km ?? null,
    insurance: v.insurance_valid_to ?? null,
    licenseValidTo: v.license_valid_to ?? null,
    lastService: v.last_maintenance_date ?? null,
    nextMaintenanceKm: v.next_maintenance_km ?? null,
    nextMaintenanceType: v.next_maintenance_type ?? null,
    maintenanceTypeId: v.maintenance_type_id ?? null,
    maintenanceTypeName: v.maintenance_type_name ?? null,
  }
}

/** MaintenanceTypeRead -> card/form view model. */
export function toUiMaintenanceType(m: MaintenanceTypeRead): UiMaintenanceType {
  return {
    id: m.id,
    name: m.name,
    description: m.description ?? null,
    intervalKm: m.interval_km,
    steps: m.steps,
  }
}

/** CustomerRead -> card view model. */
export function toUiCustomer(c: CustomerRead): UiCustomer {
  return {
    id: c.customer_id,
    name: c.full_name,
    phone: c.phone_number ?? null,
    email: c.email ?? null,
    status: c.status === 'inactive' ? 'inactive' : 'active',
  }
}

/** DriverRead -> card view model. licExpiry maps from license_valid_to (— when null). */
export function toUiDriver(d: DriverRead): UiDriver {
  return {
    id: d.driver_id,
    name: d.full_name,
    phone: d.phone_number,
    license: d.license_number ?? '—',
    licExpiry: d.license_valid_to ?? null,
    status: d.status === 'active' ? 'on' : 'off',
  }
}
