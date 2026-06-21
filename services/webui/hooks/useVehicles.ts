'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchVehicles, createVehicle, updateVehicle, deleteVehicle } from '@/lib/api/fleet'
import { toUiVehicle } from '@/lib/adapters'
import type { VehicleRead, VehicleCreate, UiVehicle } from '@/lib/api/schemas'

const KEY = ['vehicles']

export function useVehicles() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchVehicles })

  const add = useMutation({
    mutationFn: (v: VehicleCreate) => createVehicle(v),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<VehicleCreate> }) => updateVehicle(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const remove = useMutation({
    mutationFn: (id: string) => deleteVehicle(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<VehicleRead[]>(KEY)
      qc.setQueryData<VehicleRead[]>(KEY, (old) => old?.filter((v) => v.vehicle_id !== id))
      return { prev }
    },
    onError: (_e, _id, ctx) => qc.setQueryData(KEY, ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const vehicles: UiVehicle[] = (query.data ?? []).map(toUiVehicle)

  return {
    vehicles,
    loading: query.isLoading,
    add: add.mutate,
    update: update.mutate,
    remove: remove.mutate,
  }
}
