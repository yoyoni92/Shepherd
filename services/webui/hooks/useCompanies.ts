'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCompanies, createCompany, updateCompany, deleteCompany } from '@/lib/api/fleet'
import type { CompanyRead, CompanyCreate, CompanyUpdate } from '@/lib/api/schemas'

const KEY = ['companies']

export function useCompanies() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchCompanies })
  const companies: CompanyRead[] = query.data ?? []
  const invalidate = () => qc.invalidateQueries({ queryKey: KEY })

  const add = useMutation({ mutationFn: (c: CompanyCreate) => createCompany(c), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: CompanyUpdate }) => updateCompany(id, patch),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: (id: string) => deleteCompany(id), onSuccess: invalidate })

  return {
    companies,
    loading: query.isLoading,
    add: add.mutateAsync,
    update: update.mutate,
    remove: remove.mutate,
  }
}
