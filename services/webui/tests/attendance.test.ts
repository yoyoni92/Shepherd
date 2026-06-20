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

const day = (over: Partial<AttendanceDay>): AttendanceDay => ({
  day: 1,
  dateLabel: '01/06',
  weekday: 'ראשון',
  in: '08:00',
  out: '17:00',
  status: 'present',
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
})

describe('month helpers', () => {
  it('monthLabel renders a Hebrew month + year', () => {
    expect(monthLabel('2026-06')).toBe('יוני 2026')
  })
  it('monthOptions returns the last N months, newest last', () => {
    const opts = monthOptions(3, new Date('2026-06-15T00:00:00'))
    expect(opts.map((o) => o.key)).toEqual(['2026-04', '2026-05', '2026-06'])
  })
  it('buildMonthSkeleton skips weekends and seeds each employee', () => {
    const month = buildMonthSkeleton('2026-06', [{ id: 'd1', name: 'A', role: 'נהג' }])
    expect(month.label).toBe('יוני 2026')
    const days = month.records['d1']
    expect(days.length).toBeGreaterThan(0)
    // no Friday/Saturday in the skeleton
    expect(days.every((d) => d.weekday !== 'שישי' && d.weekday !== 'שבת')).toBe(true)
  })
})
