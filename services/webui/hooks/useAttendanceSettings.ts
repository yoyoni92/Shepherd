'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAttendanceSettings, updateAttendanceSettings } from '@/lib/api/fleet'
import type { AttendanceSettings } from '@/lib/api/schemas'

// Company-scoped attendance clock-in window (mirrors useCompanySettings). The page is
// only reachable when attendance is enabled for the company (flag-gated nav).
export function useAttendanceSettings() {
  const qc = useQueryClient()
  const key = ['attendance-settings']
  const query = useQuery({ queryKey: key, queryFn: fetchAttendanceSettings })
  const save = useMutation({
    mutationFn: (s: AttendanceSettings) => updateAttendanceSettings(s),
    onSuccess: (data) => qc.setQueryData(key, data),
  })

  return {
    settings: query.data,
    loading: query.isLoading,
    save: save.mutateAsync,
  }
}
