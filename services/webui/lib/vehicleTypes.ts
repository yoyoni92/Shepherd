// Vehicle type enum (mirrors db vehicle_type_enum) + Hebrew labels.
export const VEHICLE_TYPES = ['motorcycle', 'car', 'van', 'bus', 'truck'] as const
export type VehicleType = (typeof VEHICLE_TYPES)[number]

export const VEHICLE_TYPE_LABEL: Record<string, string> = {
  motorcycle: 'אופנוע',
  car: 'רכב פרטי',
  van: 'מסחרית/ואן',
  bus: 'אוטובוס',
  truck: 'משאית',
}
