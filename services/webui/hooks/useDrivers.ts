'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDrivers, createDriver, deleteDriver } from '@/lib/api/fleet'
import { toUiDriver } from '@/lib/adapters'
import type { DriverRead, DriverCreate, UiDriver } from '@/lib/api/schemas'

const KEY = ['drivers']

export function useDrivers() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchDrivers })

  const add = useMutation({
    mutationFn: (d: DriverCreate) => createDriver(d),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const remove = useMutation({
    mutationFn: (id: string) => deleteDriver(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<DriverRead[]>(KEY)
      qc.setQueryData<DriverRead[]>(KEY, (old) => old?.filter((d) => d.driver_id !== id))
      return { prev }
    },
    onError: (_e, _id, ctx) => qc.setQueryData(KEY, ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const drivers: UiDriver[] = (query.data ?? []).map(toUiDriver)

  return {
    drivers,
    loading: query.isLoading,
    add: add.mutate,
    remove: remove.mutate,
  }
}
