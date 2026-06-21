'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCustomers, createCustomer, updateCustomer, deleteCustomer } from '@/lib/api/fleet'
import { toUiCustomer } from '@/lib/adapters'
import type { CustomerCreate, CustomerRead, UiCustomer } from '@/lib/api/schemas'

const KEY = ['customers']

export function useCustomers() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchCustomers })
  const data = query.data ?? []

  const customers: UiCustomer[] = data.map(toUiCustomer)
  const customerById = Object.fromEntries(data.map((c) => [c.customer_id, c.full_name]))

  const invalidate = () => qc.invalidateQueries({ queryKey: KEY })

  const add = useMutation({ mutationFn: (c: CustomerCreate) => createCustomer(c), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<CustomerRead> }) => updateCustomer(id, patch),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) => deleteCustomer(id),
    // delete cascades to vehicles.customer_id server-side → refresh vehicles too
    onSettled: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['vehicles'] })
    },
  })

  return {
    customers,
    customerById,
    loading: query.isLoading,
    add: add.mutate,
    update: update.mutate,
    remove: remove.mutate,
  }
}
