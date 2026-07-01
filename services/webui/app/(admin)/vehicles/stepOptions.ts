import type { UiMaintenanceType } from '@/lib/api/schemas'

export const stepOptions = (types: UiMaintenanceType[], maintenanceTypeId: string) =>
  (types.find((t) => t.id === maintenanceTypeId)?.steps ?? []).map((s) => ({ value: s, label: s }))
