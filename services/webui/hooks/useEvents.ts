'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchEvents } from '@/lib/api/fleet'

export function useEvents() {
  const query = useQuery({ queryKey: ['events'], queryFn: fetchEvents })
  return { events: query.data ?? [], loading: query.isLoading }
}
