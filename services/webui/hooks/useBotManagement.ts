'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBotUsers,
  updateBotUserRole,
  getBotAuthorizations,
  createBotAuthorization,
  deleteBotAuthorization,
} from '@/lib/api/fleet'
import type { BotUserRead, BotAuthorizationRead } from '@/lib/api/schemas'

const USERS_KEY = ['bot-users']
const AUTHZ_KEY = ['bot-authorizations']

export function useBotUsers() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: USERS_KEY, queryFn: getBotUsers })

  const updateRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'admin' | 'driver' }) =>
      updateBotUserRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: USERS_KEY }),
  })

  const users: BotUserRead[] = query.data ?? []

  return {
    users,
    loading: query.isLoading,
    updateRole: updateRole.mutate,
  }
}

export function useBotAuthorizations() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: AUTHZ_KEY, queryFn: getBotAuthorizations })

  const createAuthorization = useMutation({
    mutationFn: (opts: { phoneNumber: string; role?: 'admin' | 'driver'; driverId?: string; expiresAt?: string }) =>
      createBotAuthorization(opts),
    onSuccess: () => qc.invalidateQueries({ queryKey: AUTHZ_KEY }),
  })

  const revokeAuthorization = useMutation({
    mutationFn: (id: string) => deleteBotAuthorization(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: AUTHZ_KEY })
      const prev = qc.getQueryData<BotAuthorizationRead[]>(AUTHZ_KEY)
      qc.setQueryData<BotAuthorizationRead[]>(AUTHZ_KEY, (old) => old?.filter((a) => a.id !== id))
      return { prev }
    },
    onError: (_e, _id, ctx) => qc.setQueryData(AUTHZ_KEY, ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: AUTHZ_KEY }),
  })

  const authorizations: BotAuthorizationRead[] = query.data ?? []

  return {
    authorizations,
    loading: query.isLoading,
    createAuthorization: createAuthorization.mutateAsync,
    revokeAuthorization: revokeAuthorization.mutate,
  }
}
