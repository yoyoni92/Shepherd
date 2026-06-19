'use client'
// Attendance has no backend yet (API_ALIGNMENT.md gap B2). Preview/sample data held in local
// state; edits validate + recompute in-memory so the design is fully interactive offline.
import { useEffect, useState } from 'react'
import { isValidTimeRange } from '@/lib/attendance'
import { buildSampleMonth, type AttendanceMonth, type AttendanceDay } from '@/lib/preview'

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/

type DayPatch = Partial<Pick<AttendanceDay, 'in' | 'out' | 'status'>>
interface PatchArgs {
  employeeId: number
  day: number
  patch: DayPatch
}

export function useAttendance(monthKey: string) {
  const [month, setMonth] = useState<AttendanceMonth>(() => buildSampleMonth(monthKey))
  const [patchError, setPatchError] = useState<Error | null>(null)

  useEffect(() => {
    setMonth(buildSampleMonth(monthKey))
  }, [monthKey])

  const patchDay = ({ employeeId, day, patch }: PatchArgs) => {
    setMonth((m) => {
      const eid = String(employeeId)
      const current = m.records[eid]?.find((d) => d.day === day)
      const merged = { ...current, ...patch } as AttendanceDay
      // Admin-gated validation: time format + out strictly after in (when both set).
      if (patch.in && !TIME_RE.test(patch.in)) {
        setPatchError(new Error('זמן כניסה לא תקין'))
        return m
      }
      if (patch.out && !TIME_RE.test(patch.out)) {
        setPatchError(new Error('זמן יציאה לא תקין'))
        return m
      }
      const worked = merged.status === 'present' || merged.status === 'late'
      if (worked && merged.in && merged.out && !isValidTimeRange(merged.in, merged.out)) {
        setPatchError(new Error('שעת יציאה חייבת להיות אחרי שעת כניסה'))
        return m
      }
      setPatchError(null)
      const days = m.records[eid]?.map((d) => (d.day === day ? merged : d)) ?? []
      return { ...m, records: { ...m.records, [eid]: days } }
    })
  }

  return { month, loading: false, patchDay, patchError, available: false }
}
