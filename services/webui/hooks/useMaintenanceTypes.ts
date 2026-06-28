'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchMaintenanceTypes,
  createMaintenanceType,
  updateMaintenanceType,
  deleteMaintenanceType,
} from '@/lib/api/fleet'
import { toUiMaintenanceType } from '@/lib/adapters'
import type { MaintenanceTypeCreate, UiMaintenanceType } from '@/lib/api/schemas'

const KEY = ['maintenance-types']

export function useMaintenanceTypes() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchMaintenanceTypes })
  const types: UiMaintenanceType[] = (query.data ?? []).map(toUiMaintenanceType)
  const invalidate = () => qc.invalidateQueries({ queryKey: KEY })

  const add = useMutation({ mutationFn: (m: MaintenanceTypeCreate) => createMaintenanceType(m), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<MaintenanceTypeCreate> }) => updateMaintenanceType(id, patch),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: (id: string) => deleteMaintenanceType(id), onSuccess: invalidate })

  return {
    types,
    loading: query.isLoading,
    add: add.mutate,
    update: update.mutate,
    remove: remove.mutate,
    removeError: remove.error as Error | null,
    clearRemoveError: remove.reset,
  }
}
