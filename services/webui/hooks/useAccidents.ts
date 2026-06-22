'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAccidents, createAccident } from '@/lib/api/fleet'
import { toUiAccident } from '@/lib/adapters'
import { useVehicles } from './useVehicles'
import { useDrivers } from './useDrivers'
import type { UiAccident, AccidentCreate } from '@/lib/api/schemas'

const KEY = ['accidents']

export function useAccidents() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchAccidents })
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()

  const vehicleById = Object.fromEntries(vehicles.map((v) => [v.id, v]))
  const driverById = Object.fromEntries(drivers.map((d) => [d.id, d]))

  const add = useMutation({
    mutationFn: createAccident,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const accidents: UiAccident[] = (query.data ?? []).map((a) =>
    toUiAccident(a, vehicleById, driverById),
  )

  return {
    accidents,
    loading: query.isLoading,
    add: add.mutate,
    adding: add.isPending,
  }
}
