import type { AttendanceDay, Employee } from './preview'

/** 'HH:MM' -> minutes since midnight; NaN for empty/invalid. */
export function t2m(t: string): number {
  if (!t || !/^\d{1,2}:\d{2}$/.test(t)) return NaN
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

/** minutes -> 'HH:MM'. */
export function m2t(min: number): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(Math.floor(min / 60))}:${p(min % 60)}`
}

const isWorked = (s: AttendanceDay['status']) => s === 'present' || s === 'late'

/** Hours worked for a single day (0 if not worked or times missing/invalid). */
export function hoursFor(day: AttendanceDay): number {
  if (!isWorked(day.status) || !day.in || !day.out) return 0
  const h = (t2m(day.out) - t2m(day.in)) / 60
  return h > 0 ? Math.round(h * 10) / 10 : 0
}

export interface DayAggregate {
  pres: number
  late: number
  leave: number
  absent: number
  hours: number
  avgIn: string
  avgOut: string
}

/** Per-employee monthly aggregate (pure). */
export function aggregate(records: readonly AttendanceDay[]): DayAggregate {
  let pres = 0,
    late = 0,
    leave = 0,
    absent = 0,
    hours = 0,
    inSum = 0,
    outSum = 0,
    n = 0
  for (const r of records) {
    if (isWorked(r.status)) pres++
    if (r.status === 'late') late++
    if (r.status === 'leave') leave++
    if (r.status === 'absent') absent++
    if (isWorked(r.status) && r.in && r.out) {
      const inM = t2m(r.in)
      const outM = t2m(r.out)
      if (outM - inM > 0) {
        hours += (outM - inM) / 60
        inSum += inM
        outSum += outM
        n++
      }
    }
  }
  return {
    pres,
    late,
    leave,
    absent,
    hours: Math.round(hours * 10) / 10,
    avgIn: n ? m2t(Math.round(inSum / n)) : '—',
    avgOut: n ? m2t(Math.round(outSum / n)) : '—',
  }
}

export type EmployeeStatus = 'ok' | 'late' | 'absent'

/** Row status: absent if any absence, late if >=2 lates, else ok. */
export function employeeStatus(a: DayAggregate): EmployeeStatus {
  if (a.absent > 0) return 'absent'
  if (a.late >= 2) return 'late'
  return 'ok'
}

export interface MonthSummary {
  empCount: number
  totalHours: number
  totalLate: number
  avgPerEmp: number
}

/** Whole-month KPI summary across employees. */
export function summarize(
  employees: readonly Employee[],
  records: Record<string, AttendanceDay[]>,
): MonthSummary {
  const aggs = employees.map((e) => aggregate(records[e.id] ?? []))
  const totalHours = Math.round(aggs.reduce((s, a) => s + a.hours, 0))
  const totalLate = aggs.reduce((s, a) => s + a.late, 0)
  const empCount = employees.length
  return {
    empCount,
    totalHours,
    totalLate,
    avgPerEmp: empCount ? Math.round(totalHours / empCount) : 0,
  }
}

/** True when both times parse and out is strictly after in. */
export function isValidTimeRange(inT: string, outT: string): boolean {
  const a = t2m(inT)
  const b = t2m(outT)
  return Number.isFinite(a) && Number.isFinite(b) && b > a
}

/** UTF-8 CSV body (no BOM) for the selected month. */
export function buildCsv(
  employees: readonly Employee[],
  records: Record<string, AttendanceDay[]>,
): string {
  const head = [
    'עובד',
    'תפקיד',
    'מחלקה',
    'ימי עבודה',
    'כניסה ממוצעת',
    'יציאה ממוצעת',
    'סך שעות',
    'איחורים',
  ]
  const lines = [head.join(',')]
  for (const e of employees) {
    const a = aggregate(records[e.id] ?? [])
    lines.push(
      [e.name, e.role, e.dept, a.pres, a.avgIn, a.avgOut, a.hours, a.late]
        .map((x) => `"${x}"`)
        .join(','),
    )
  }
  return lines.join('\n')
}
