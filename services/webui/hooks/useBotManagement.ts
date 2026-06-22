'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBotUsers,
  updateBotUserRole,
  getBotInvites,
  createBotInvite,
  revokeBotInvite,
} from '@/lib/api/fleet'
import type { BotUserRead, BotInviteRead, BotInviteResponse } from '@/lib/api/schemas'

const USERS_KEY = ['bot-users']
const INVITES_KEY = ['bot-invites']

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

export function useBotInvites() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: INVITES_KEY, queryFn: getBotInvites })

  const createInvite = useMutation({
    mutationFn: (opts: { driverId?: string; role?: 'admin' | 'driver'; phoneNumber?: string }) => createBotInvite(opts),
    onSuccess: () => qc.invalidateQueries({ queryKey: INVITES_KEY }),
  })

  const revokeInvite = useMutation({
    mutationFn: (token: string) => revokeBotInvite(token),
    onMutate: async (token) => {
      await qc.cancelQueries({ queryKey: INVITES_KEY })
      const prev = qc.getQueryData<BotInviteRead[]>(INVITES_KEY)
      qc.setQueryData<BotInviteRead[]>(INVITES_KEY, (old) => old?.filter((i) => i.token !== token))
      return { prev }
    },
    onError: (_e, _token, ctx) => qc.setQueryData(INVITES_KEY, ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: INVITES_KEY }),
  })

  const invites: BotInviteRead[] = query.data ?? []

  return {
    invites,
    loading: query.isLoading,
    createInvite: createInvite.mutateAsync,
    revokeInvite: revokeInvite.mutate,
  }
}
