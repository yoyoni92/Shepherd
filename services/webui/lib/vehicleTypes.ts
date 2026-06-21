// Vehicle type enum (mirrors db vehicle_type_enum) + Hebrew labels.
export const VEHICLE_TYPES = ['motorcycle', 'car', 'van', 'bus', 'truck'] as const
export type VehicleType = (typeof VEHICLE_TYPES)[number]

export const VEHICLE_TYPE_LABEL: Record<string, string> = {
  motorcycle: 'קטנוע',
  car: 'רכב פרטי',
  van: 'מסחרית/ואן',
  bus: 'אוטובוס',
  truck: 'משאית',
}

// Maintenance cycle (mirrors db maintenance_type_enum) + Hebrew labels.
export const MAINTENANCE_TYPES = ['1_small_then_1_big', '2_small_then_1_big'] as const
export type MaintenanceType = (typeof MAINTENANCE_TYPES)[number]

export const MAINTENANCE_TYPE_LABEL: Record<string, string> = {
  '1_small_then_1_big': 'קטן ואז גדול',
  '2_small_then_1_big': 'שניים קטנים ואז גדול',
}
