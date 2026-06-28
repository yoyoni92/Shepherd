// Jewish holiday notes for the attendance calendar. Computed offline from the Hebrew
// calendar via @hebcal/core (perpetual, Israeli schedule) - no network, no annual list.
import { HebrewCalendar, flags } from '@hebcal/core'

export type HolidayKind = 'chag' | 'erev' | 'fast' | 'minor'

export interface Holiday {
  day: number // day-of-month (1..31)
  dateLabel: string // 'DD/MM'
  name: string // Hebrew name, e.g. 'פסח א׳'
  kind: HolidayKind
}

const pad = (n: number) => String(n).padStart(2, '0')

// chag (melacha forbidden) > erev chag > fast > minor (Chol HaMoed, modern, festive).
function classify(eventFlags: number): HolidayKind {
  if (eventFlags & flags.EREV) return 'erev'
  if (eventFlags & flags.CHAG) return 'chag'
  if (eventFlags & (flags.MAJOR_FAST | flags.MINOR_FAST)) return 'fast'
  return 'minor'
}

const RANK: Record<HolidayKind, number> = { chag: 3, erev: 2, fast: 1, minor: 0 }

/** Holidays in a 'YYYY-MM' Gregorian month, one entry per day (most significant kept). */
export function monthHolidays(monthKey: string): Holiday[] {
  const [y, m] = monthKey.split('-').map(Number)
  const events = HebrewCalendar.calendar({
    year: y,
    month: m,
    isHebrewYear: false,
    il: true,
    sedrot: false,
    candlelighting: false,
    omer: false,
    noRoshChodesh: true,
  })
  const byDay = new Map<number, Holiday>()
  for (const ev of events) {
    const g = ev.getDate().greg()
    if (g.getFullYear() !== y || g.getMonth() + 1 !== m) continue // guard range edges
    const day = g.getDate()
    const hol: Holiday = {
      day,
      dateLabel: `${pad(day)}/${pad(m)}`,
      name: ev.render('he'),
      kind: classify(ev.getFlags()),
    }
    const prev = byDay.get(day)
    if (!prev || RANK[hol.kind] > RANK[prev.kind]) byDay.set(day, hol)
  }
  return [...byDay.values()].sort((a, b) => a.day - b.day)
}

/** Day-of-month -> holiday, for overlaying onto the attendance skeleton. */
export function holidayMap(monthKey: string): Map<number, Holiday> {
  return new Map(monthHolidays(monthKey).map((h) => [h.day, h]))
}
