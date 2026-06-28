import { describe, it, expect } from 'vitest'
import {
  t2m,
  m2t,
  hoursFor,
  aggregate,
  employeeStatus,
  summarize,
  isValidTimeRange,
  buildCsv,
  monthLabel,
  monthOptions,
  buildMonthSkeleton,
  type AttendanceDay,
  type Employee,
} from '@/lib/attendance'
import type { Holiday } from '@/lib/holidays'

const hol = (day: number, kind: Holiday['kind'], name: string): Holiday => ({
  day,
  dateLabel: `${String(day).padStart(2, '0')}/06`,
  name,
  kind,
})

const day = (over: Partial<AttendanceDay>): AttendanceDay => ({
  day: 1,
  dateLabel: '01/06',
  weekday: 'ראשון',
  in: '08:00',
  out: '17:00',
  status: 'present',
  working: true,
  ...over,
})

describe('time helpers', () => {
  it('t2m parses HH:MM and rejects junk', () => {
    expect(t2m('08:30')).toBe(510)
    expect(Number.isNaN(t2m(''))).toBe(true)
    expect(Number.isNaN(t2m('abc'))).toBe(true)
  })
  it('m2t pads to HH:MM', () => {
    expect(m2t(510)).toBe('08:30')
    expect(m2t(65)).toBe('01:05')
  })
})

describe('hoursFor', () => {
  it('computes worked hours rounded to 0.1', () => {
    expect(hoursFor(day({ in: '08:00', out: '17:30' }))).toBe(9.5)
  })
  it('is zero for absences or missing times', () => {
    expect(hoursFor(day({ status: 'absent', in: '', out: '' }))).toBe(0)
    expect(hoursFor(day({ in: '', out: '' }))).toBe(0)
  })
})

describe('aggregate', () => {
  const records: AttendanceDay[] = [
    day({ day: 1, status: 'present', in: '08:00', out: '17:00' }),
    day({ day: 2, status: 'late', in: '09:00', out: '17:00' }),
    day({ day: 3, status: 'leave', in: '', out: '' }),
    day({ day: 4, status: 'absent', in: '', out: '' }),
  ]
  it('counts statuses and sums hours/averages', () => {
    const a = aggregate(records)
    expect(a).toMatchObject({ pres: 2, late: 1, leave: 1, absent: 1 })
    expect(a.hours).toBe(17) // 9 + 8
    expect(a.avgIn).toBe('08:30')
    expect(a.avgOut).toBe('17:00')
  })
  it('returns em-dash averages with no worked days', () => {
    const a = aggregate([day({ status: 'absent', in: '', out: '' })])
    expect(a.avgIn).toBe('—')
    expect(a.avgOut).toBe('—')
  })
})

describe('employeeStatus', () => {
  it('flags absence first, then repeated lateness, else ok', () => {
    expect(employeeStatus({ pres: 1, late: 0, leave: 0, absent: 1, hours: 0, avgIn: '—', avgOut: '—' })).toBe('absent')
    expect(employeeStatus({ pres: 1, late: 2, leave: 0, absent: 0, hours: 0, avgIn: '—', avgOut: '—' })).toBe('late')
    expect(employeeStatus({ pres: 1, late: 1, leave: 0, absent: 0, hours: 0, avgIn: '—', avgOut: '—' })).toBe('ok')
  })
})

describe('summarize', () => {
  const employees: Employee[] = [
    { id: '1', name: 'A', role: 'r' },
    { id: '2', name: 'B', role: 'r' },
  ]
  const records = {
    '1': [day({ in: '08:00', out: '16:00', status: 'late' })],
    '2': [day({ in: '08:00', out: '18:00' })],
  }
  it('totals hours, lates and per-employee average', () => {
    const s = summarize(employees, records)
    expect(s.empCount).toBe(2)
    expect(s.totalHours).toBe(18) // 8 + 10
    expect(s.totalLate).toBe(1)
    expect(s.avgPerEmp).toBe(9)
  })
  it('avoids divide-by-zero with no employees', () => {
    expect(summarize([], {}).avgPerEmp).toBe(0)
  })
})

describe('isValidTimeRange', () => {
  it('requires out strictly after in', () => {
    expect(isValidTimeRange('08:00', '17:00')).toBe(true)
    expect(isValidTimeRange('17:00', '08:00')).toBe(false)
    expect(isValidTimeRange('', '17:00')).toBe(false)
  })
})

describe('buildCsv', () => {
  it('emits a header row and one line per employee', () => {
    const employees: Employee[] = [{ id: '1', name: 'דנה לוי', role: 'נהג' }]
    const records = { '1': [day({ in: '08:00', out: '17:00' })] }
    const csv = buildCsv(employees, records)
    const lines = csv.split('\n')
    expect(lines[0]).toContain('עובד')
    expect(lines[1]).toContain('דנה לוי')
    expect(lines).toHaveLength(2)
  })
  it('appends a חגים section when holidays are supplied', () => {
    const employees: Employee[] = [{ id: '1', name: 'דנה לוי', role: 'נהג' }]
    const records = { '1': [day({ in: '08:00', out: '17:00' })] }
    const csv = buildCsv(employees, records, [hol(7, 'chag', 'פסח א׳')])
    expect(csv).toContain('חגים ומועדים')
    expect(csv).toContain('פסח א׳')
    expect(csv).toContain('07/06')
  })
})

describe('month helpers', () => {
  it('monthLabel renders a Hebrew month + year', () => {
    expect(monthLabel('2026-06')).toBe('יוני 2026')
  })
  it('monthOptions returns the last N months, newest last', () => {
    const opts = monthOptions(3, new Date('2026-06-15T00:00:00'))
    expect(opts.map((o) => o.key)).toEqual(['2026-04', '2026-05', '2026-06'])
  })
  it('buildMonthSkeleton includes every day and seeds each employee', () => {
    const month = buildMonthSkeleton('2026-06', [{ id: 'd1', name: 'A', role: 'נהג' }])
    expect(month.label).toBe('יוני 2026')
    const days = month.records['d1']
    expect(days).toHaveLength(30) // June has 30 days; weekends are kept, not skipped
    // Saturdays are shown but marked as non-working rest days, labelled שבת.
    const sat = days.find((d) => d.weekday === 'שבת')
    expect(sat?.working).toBe(false)
    expect(sat).toMatchObject({ note: 'שבת', noteKind: 'rest' })
  })
})

describe('buildMonthSkeleton working-day rules', () => {
  const emp: Employee[] = [{ id: 'd1', name: 'A', role: 'נהג' }]
  const all = [0, 1, 2, 3, 4, 5, 6]
  const dayOf = (month: ReturnType<typeof buildMonthSkeleton>, d: number) =>
    month.records['d1'].find((x) => x.day === d)

  it('marks Saturday non-working by default but working when its weekday is enabled', () => {
    const off = buildMonthSkeleton('2026-06', emp) // default Sun-Thu
    expect(dayOf(off, 6)?.working).toBe(false) // 2026-06-06 is a Saturday
    const on = buildMonthSkeleton('2026-06', emp, { workDays: all })
    expect(dayOf(on, 6)?.working).toBe(true)
  })

  it('keeps חג days visible but non-working unless chagWorking is on', () => {
    const holidays = new Map([[10, hol(10, 'chag', 'פסח א׳')]])
    const off = buildMonthSkeleton('2026-06', emp, { workDays: all, chagWorking: false, holidays })
    expect(dayOf(off, 10)).toMatchObject({ working: false, note: 'פסח א׳', noteKind: 'chag' })
    const on = buildMonthSkeleton('2026-06', emp, { workDays: all, chagWorking: true, holidays })
    expect(dayOf(on, 10)).toMatchObject({ working: true, note: 'פסח א׳' })
  })

  it('keeps ערב חג working by default but non-working when erevChagWorking is off', () => {
    const holidays = new Map([[10, hol(10, 'erev', 'ערב פסח')]])
    const on = buildMonthSkeleton('2026-06', emp, { workDays: all, holidays })
    expect(dayOf(on, 10)).toMatchObject({ working: true, note: 'ערב פסח', noteKind: 'erev' })
    const off = buildMonthSkeleton('2026-06', emp, { workDays: all, erevChagWorking: false, holidays })
    expect(dayOf(off, 10)).toMatchObject({ working: false, note: 'ערב פסח' })
  })

  it('attaches a note to working days that fall on a fast or minor מועד', () => {
    const holidays = new Map([[10, hol(10, 'minor', 'חנוכה')]])
    const month = buildMonthSkeleton('2026-06', emp, { workDays: all, holidays })
    expect(dayOf(month, 10)).toMatchObject({ working: true, note: 'חנוכה', noteKind: 'minor' })
  })

  it('does not count rest days in the aggregate', () => {
    const month = buildMonthSkeleton('2026-06', emp) // Sun-Thu; weekends are rest
    const a = aggregate(month.records['d1'])
    const workingDays = month.records['d1'].filter((d) => d.working).length
    expect(a.pres).toBe(workingDays) // every working day defaults to 'present'
  })
})
