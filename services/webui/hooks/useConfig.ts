'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchConfig, updateConfig } from '@/lib/api/fleet'
import { z } from 'zod'

// ponytail: minimal Zod guard - rejects non-serialisable values before PUT
const valueSchema = z.union([z.string(), z.number(), z.boolean(), z.array(z.string())])

export function useConfig() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const mutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => {
      valueSchema.parse(value) // throws ZodError on bad shape (admin-gated validation)
      return updateConfig(key, value)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
  return {
    config: query.data,
    loading: query.isLoading,
    save: mutation.mutate,
    saving: mutation.isPending,
    saveError: mutation.error,
  }
}
