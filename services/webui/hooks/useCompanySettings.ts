'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCompanySettings, updateCompanySettings } from '@/lib/api/fleet'
import type { CompanySettingsUpdate } from '@/lib/api/schemas'

// Per-company settings (Drive + feature flags). Fetched lazily when a company is selected.
export function useCompanySettings(companyId: string | null) {
  const qc = useQueryClient()
  const key = ['company-settings', companyId]
  const query = useQuery({
    queryKey: key,
    queryFn: () => fetchCompanySettings(companyId as string),
    enabled: !!companyId,
  })
  const save = useMutation({
    mutationFn: (patch: CompanySettingsUpdate) => updateCompanySettings(companyId as string, patch),
    onSuccess: (data) => qc.setQueryData(key, data),
  })

  return {
    settings: query.data,
    loading: query.isLoading,
    save: save.mutateAsync,
  }
}
