'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchCustomers } from '@/lib/api/fleet'

// id -> name map, for resolving the KPI top-customer tile.
export function useCustomers() {
  const query = useQuery({ queryKey: ['customers'], queryFn: fetchCustomers })
  const customerById = Object.fromEntries((query.data ?? []).map((c) => [c.customer_id, c.full_name]))
  return { customerById, loading: query.isLoading }
}
