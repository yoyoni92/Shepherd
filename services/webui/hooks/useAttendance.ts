'use client'
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDrivers } from '@/hooks/useDrivers'
import { useAttendanceSettings } from '@/hooks/useAttendanceSettings'
import { fetchAttendanceMonth, patchAttendanceDay } from '@/lib/api/fleet'
import {
  isValidTimeRange,
  buildMonthSkeleton,
  DEFAULT_WORK_DAYS,
  type AttendanceDay,
  type AttendanceStatus,
  type Employee,
  type WorkDayConfig,
} from '@/lib/attendance'
import { monthHolidays } from '@/lib/holidays'
import type { AttendanceRecordRead } from '@/lib/api/schemas'

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/

type DayPatch = Partial<Pick<AttendanceDay, 'in' | 'out' | 'status'>>
interface PatchArgs {
  employeeId: string
  day: number
  patch: DayPatch
}

type MutateVars = {
  driverId: string
  date: string
  body: { clock_in: string | null; clock_out: string | null; status: string }
}

/** Skeleton (weekday calendar) per employee, with stored records overlaid. */
function buildMonth(
  monthKey: string,
  employees: Employee[],
  records: readonly AttendanceRecordRead[],
  config: Partial<WorkDayConfig>,
) {
  const month = buildMonthSkeleton(monthKey, employees, config)
  for (const r of records) {
    const days = month.records[r.driver_id]
    if (!days) continue
    const day = days.find((d) => d.day === Number(r.work_date.slice(8, 10)))
    if (!day) continue
    day.in = r.clock_in ?? ''
    day.out = r.clock_out ?? ''
    day.status = r.status as AttendanceStatus
  }
  return month
}

export function useAttendance(monthKey: string) {
  const qc = useQueryClient()
  const { drivers } = useDrivers()
  const { settings } = useAttendanceSettings()
  const key = ['attendance', monthKey]
  const recordsQuery = useQuery({ queryKey: key, queryFn: () => fetchAttendanceMonth(monthKey) })
  const [patchError, setPatchError] = useState<Error | null>(null)

  const holidays = useMemo(() => monthHolidays(monthKey), [monthKey])
  const holidayMap = useMemo(() => new Map(holidays.map((h) => [h.day, h])), [holidays])
  const config: Partial<WorkDayConfig> = {
    workDays: settings?.work_days ?? [...DEFAULT_WORK_DAYS],
    chagWorking: settings?.chag_working ?? false,
    erevChagWorking: settings?.erev_chag_working ?? true,
    holidays: holidayMap,
  }

  const employees: Employee[] = drivers.map((d) => ({ id: d.id, name: d.name, role: 'נהג' }))
  const month = buildMonth(monthKey, employees, recordsQuery.data ?? [], config)

  const mutation = useMutation({
    mutationFn: ({ driverId, date, body }: MutateVars) => patchAttendanceDay(driverId, date, body),
    onMutate: async ({ driverId, date, body }) => {
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData<AttendanceRecordRead[]>(key)
      const next: AttendanceRecordRead = { driver_id: driverId, work_date: date, ...body }
      qc.setQueryData<AttendanceRecordRead[]>(key, (old) => {
        const rest = (old ?? []).filter((r) => !(r.driver_id === driverId && r.work_date === date))
        return [...rest, next]
      })
      return { prev }
    },
    onError: (_e, _v, ctx) => qc.setQueryData(key, ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  })

  const patchDay = ({ employeeId, day, patch }: PatchArgs) => {
    const current = month.records[employeeId]?.find((d) => d.day === day)
    const merged = { ...current, ...patch } as AttendanceDay
    // Admin-gated validation: time format + out strictly after in (when both set).
    if (patch.in && !TIME_RE.test(patch.in)) return setPatchError(new Error('זמן כניסה לא תקין'))
    if (patch.out && !TIME_RE.test(patch.out)) return setPatchError(new Error('זמן יציאה לא תקין'))
    const worked = merged.status === 'present' || merged.status === 'late'
    if (worked && merged.in && merged.out && !isValidTimeRange(merged.in, merged.out)) {
      return setPatchError(new Error('שעת יציאה חייבת להיות אחרי שעת כניסה'))
    }
    setPatchError(null)
    const date = `${monthKey}-${String(day).padStart(2, '0')}`
    mutation.mutate({
      driverId: employeeId,
      date,
      body: { clock_in: merged.in || null, clock_out: merged.out || null, status: merged.status },
    })
  }

  return { month, holidays, loading: recordsQuery.isLoading, patchDay, patchError }
}
