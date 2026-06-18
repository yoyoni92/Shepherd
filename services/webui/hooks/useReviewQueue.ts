'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchReviewQueue, resolveReviewItem } from '@/lib/api/fleet'
import type { ReviewItem } from '@/lib/api/schemas'

export function useReviewQueue() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: ['review-queue'], queryFn: fetchReviewQueue })
  const mutation = useMutation({
    mutationFn: ({ id, action, payload }: { id: string; action: 'accept' | 'reject'; payload?: unknown }) =>
      resolveReviewItem(id, action, payload),
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: ['review-queue'] })
      const prev = qc.getQueryData<ReviewItem[]>(['review-queue'])
      qc.setQueryData<ReviewItem[]>(['review-queue'], old => old?.filter(item => item.id !== id))
      return { prev }
    },
    onError: (_err, _vars, ctx) => qc.setQueryData(['review-queue'], ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: ['review-queue'] }),
  })
  return {
    items: query.data ?? [],
    loading: query.isLoading,
    resolve: mutation.mutate,
  }
}
