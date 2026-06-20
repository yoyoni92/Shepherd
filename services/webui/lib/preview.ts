// PREVIEW-ONLY domain — no backend yet (API_ALIGNMENT.md gap B2 attendance).
// These types + sample data let the Attendance section render the design while the
// backing endpoints are built. UI surfaces a "no API" banner so this is never mistaken for live data.

export interface AttendanceDay {
  day: number
  dateLabel: string
  weekday: string
  in: string
  out: string
  status: 'present' | 'late' | 'leave' | 'absent'
}

export interface Employee {
  id: number
  name: string
  role: string
  dept: string
}

export interface AttendanceMonth {
  monthKey: string
  label: string
  employees: Employee[]
  records: Record<string, AttendanceDay[]>
}

const EMPLOYEES: Employee[] = [
  { id: 1, name: 'דנה לוי', role: 'נהגת', dept: 'תפעול' },
  { id: 2, name: 'יוסי מזרחי', role: 'נהג', dept: 'תפעול' },
  { id: 3, name: 'נעם ברק', role: 'נהג', dept: 'תפעול' },
  { id: 4, name: 'מאיה גל', role: 'רכזת לוגיסטיקה', dept: 'לוגיסטיקה' },
  { id: 5, name: 'איתי שמש', role: 'נהג', dept: 'תפעול' },
  { id: 6, name: 'רונית אבני', role: 'מנהלת משרד', dept: 'מנהלה' },
  { id: 7, name: 'עומר כץ', role: 'טכנאי תחזוקה', dept: 'תחזוקה' },
]

const MONTH_META: Record<string, { label: string; cap: number; mi: number }> = {
  '2026-04': { label: 'אפריל 2026', cap: 30, mi: 0 },
  '2026-05': { label: 'מאי 2026', cap: 31, mi: 1 },
  '2026-06': { label: 'יוני 2026', cap: 19, mi: 2 },
}

export const PREVIEW_MONTHS = [
  { key: '2026-04', label: 'אפריל 2026' },
  { key: '2026-05', label: 'מאי 2026' },
  { key: '2026-06', label: 'יוני 2026' },
]

const WD = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
const pad = (n: number) => String(n).padStart(2, '0')
const m2t = (m: number) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`

/** Deterministic sample month (weekends skipped). */
export function buildSampleMonth(monthKey: string): AttendanceMonth {
  const meta = MONTH_META[monthKey] ?? { label: monthKey, cap: 28, mi: 0 }
  const records: Record<string, AttendanceDay[]> = {}
  for (const e of EMPLOYEES) {
    const recs: AttendanceDay[] = []
    for (let d = 1; d <= meta.cap; d++) {
      const dow = new Date(`${monthKey}-${pad(d)}T00:00:00`).getDay()
      if (dow === 5 || dow === 6) continue
      const seed = (e.id * 131 + d * 17 + meta.mi * 53) % 100
      let status: AttendanceDay['status'] = 'present'
      let inM = 480 + (seed % 13)
      const outM = 1018 + (seed % 25)
      if (seed % 23 === 0) status = 'leave'
      else if (seed % 19 === 0) status = 'absent'
      else if (seed % 9 === 0) {
        status = 'late'
        inM = 500 + (seed % 35)
      }
      const base = { day: d, dateLabel: `${pad(d)}/${monthKey.slice(5)}`, weekday: WD[dow] }
      recs.push(
        status === 'absent' || status === 'leave'
          ? { ...base, in: '', out: '', status }
          : { ...base, in: m2t(inM), out: m2t(outM), status },
      )
    }
    records[String(e.id)] = recs
  }
  return { monthKey, label: meta.label, employees: EMPLOYEES, records }
}
