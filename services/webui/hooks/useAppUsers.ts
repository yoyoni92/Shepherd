'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAppUsers, createAppUser, updateAppUser, deleteAppUser } from '@/lib/api/fleet'
import type { AppUserRead, AppUserCreate, AppUserUpdate } from '@/lib/api/schemas'

const KEY = ['app-users']

export function useAppUsers() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchAppUsers })
  const users: AppUserRead[] = query.data ?? []
  const invalidate = () => qc.invalidateQueries({ queryKey: KEY })

  const add = useMutation({ mutationFn: (u: AppUserCreate) => createAppUser(u), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: AppUserUpdate }) => updateAppUser(id, patch),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: (id: string) => deleteAppUser(id), onSuccess: invalidate })

  return {
    users,
    loading: query.isLoading,
    add: add.mutateAsync,
    update: update.mutate,
    remove: remove.mutate,
  }
}
